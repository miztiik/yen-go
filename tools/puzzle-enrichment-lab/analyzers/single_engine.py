"""Single-engine KataGo manager with config-driven visit escalation.

Runs one LocalEngine instance and optionally escalates analysis visits
when the result is uncertain.
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    from config import EnrichmentConfig
    from config.helpers import get_level_category
    from engine.config import EngineConfig
    from engine.local_subprocess import LocalEngine
    from models.analysis_request import AnalysisRequest
    from models.analysis_response import AnalysisResponse
except ImportError:
    from ..config import EnrichmentConfig
    from ..config.helpers import get_level_category
    from ..engine.config import EngineConfig
    from ..engine.local_subprocess import LocalEngine
    from ..models.analysis_request import AnalysisRequest
    from ..models.analysis_response import AnalysisResponse

logger = logging.getLogger(__name__)


def resolve_katago_config(katago_config: str, katago_path: str) -> str:
    """Resolve the KataGo analysis config path.

    If explicit config given, use it. Otherwise auto-detect
    tsumego_analysis.cfg next to the KataGo binary.
    """
    if katago_config:
        return katago_config
    katago_dir = Path(katago_path).parent
    candidate = katago_dir / "tsumego_analysis.cfg"
    if candidate.exists():
        logger.info("Auto-detected KataGo config: %s", candidate)
        return str(candidate)
    return ""


class SingleEngineManager:
    """Manages one KataGo engine process with optional visit escalation.

    Escalation policy is config-driven:
    - Base visits from analysis_defaults.default_max_visits
    - If uncertain (winrate in [low, high]) and enabled, retry at deep_enrich.visits
    """

    def __init__(
        self,
        config: EnrichmentConfig,
        *,
        katago_path: str = "",
        model_path: str = "",
        katago_config_path: str = "",
        engine: LocalEngine | None = None,
        mode_override: str | None = None,
    ) -> None:
        self._config = config
        self._katago_path = katago_path
        self._model_path = model_path
        self._katago_config_path = katago_config_path
        self._engine: LocalEngine | None = engine
        self._mode_override = mode_override
        self._mode = "quick_only" if mode_override == "quick_only" else "single"

        self._escalation_low = config.deep_enrich.escalation_winrate_low
        self._escalation_high = config.deep_enrich.escalation_winrate_high
        self._escalation_enabled = config.deep_enrich.escalate_to_referee and self._mode != "quick_only"
        self._total_visits_used: int = 0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def engine(self) -> LocalEngine | None:
        return self._engine

    @property
    def model_path(self) -> str:
        return self._model_path

    @property
    def total_visits_used(self) -> int:
        """Total KataGo visits consumed across all queries since last reset."""
        return self._total_visits_used

    def reset_visit_counter(self) -> None:
        """Reset the per-puzzle visit counter. Call before each puzzle."""
        self._total_visits_used = 0

    def model_label(self) -> str:
        if self._config.models is not None:
            return self._config.models.deep_enrich.arch
        return "single"

    def get_model_for_level(self, level_slug: str) -> str | None:
        """Return the resolved model filename for a puzzle's level, or None.

        Uses the ``model_by_category`` routing table in AiSolveConfig.
        Returns None when routing is inactive (empty dict or no ai_solve config).
        """
        ai_solve = self._config.ai_solve
        if ai_solve is None or not ai_solve.model_by_category:
            return None

        category = get_level_category(level_slug)
        model_name = ai_solve.model_by_category.get(category)
        if model_name is None:
            return None

        model_entry = getattr(self._config.models, model_name, None)
        if model_entry is None:
            logger.warning(
                "model_by_category maps '%s' -> '%s' but no such model in ModelsConfig",
                category,
                model_name,
            )
            return None
        return model_entry.filename

    def model_label_for_routing(self, level_slug: str) -> str:
        """Return the model label used for a given level slug.

        Returns the category-mapped model's arch label when routing is
        active, otherwise the default model label.
        """
        ai_solve = self._config.ai_solve
        if ai_solve is not None and ai_solve.model_by_category:
            category = get_level_category(level_slug)
            model_name = ai_solve.model_by_category.get(category)
            if model_name is not None:
                model_entry = getattr(self._config.models, model_name, None)
                if model_entry is not None:
                    return model_entry.arch
        return self.model_label()

    async def start(self) -> None:
        if self._engine is not None:
            return
        engine_config = self._make_engine_config(model_path=self._model_path)
        self._engine = LocalEngine(engine_config)
        await self._engine.start()
        logger.info("Single engine started")

    async def shutdown(self) -> None:
        if self._engine is not None:
            logger.info("Shutting down single engine")
            await self._engine.shutdown()
            self._engine = None
            logger.info("Single engine stopped")

    # Async context manager protocol (PEP 492) --------------------------

    async def __aenter__(self) -> SingleEngineManager:
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.shutdown()

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        if self._engine is None:
            raise RuntimeError("Engine not started")

        base_response = await self._engine.analyze(request)
        if not self._escalation_enabled:
            self._total_visits_used += base_response.total_visits
            return base_response

        if not self._should_escalate(base_response):
            self._total_visits_used += base_response.total_visits
            return base_response

        deep_visits = int(self._config.deep_enrich.visits)
        if request.max_visits >= deep_visits:
            self._total_visits_used += base_response.total_visits
            return base_response

        escalated_request = request.model_copy(update={"max_visits": deep_visits})
        logger.info(
            "Escalating single-engine analysis visits: %d -> %d",
            request.max_visits,
            deep_visits,
        )
        escalated_response = await self._engine.analyze(escalated_request)
        self._total_visits_used += escalated_response.total_visits
        return escalated_response

    def _should_escalate(self, response: AnalysisResponse) -> bool:
        return self._escalation_low <= response.root_winrate <= self._escalation_high

    def _make_engine_config(self, *, model_path: str = "") -> EngineConfig:
        return EngineConfig(
            katago_path=self._katago_path,
            model_path=model_path,
            config_path=self._katago_config_path,
            default_max_visits=self._config.analysis_defaults.default_max_visits,
            default_board_size=19,
            num_threads=2,
        )
