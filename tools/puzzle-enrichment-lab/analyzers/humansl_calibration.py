"""HumanSL calibration module — feature-gated human strength profile.

When a HumanSL model is available, provides calibrated difficulty estimation
based on human-like play patterns instead of raw KataGo analysis.

Feature gate: enabled only when humansl_model_path is configured and
the model file exists on disk. Gracefully skipped otherwise.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import EnrichmentConfig
    from models.analysis_request import AnalysisRequest

logger = logging.getLogger(__name__)

_humansl_available_cache: dict[str, bool] = {}


def is_humansl_available(config: EnrichmentConfig) -> bool:
    """Check if HumanSL model is available and feature is enabled."""
    humansl_config = getattr(config, 'humansl', None)
    if humansl_config is None or not humansl_config.enabled:
        return False
    model_path = humansl_config.model_path
    if not model_path:
        return False
    if model_path in _humansl_available_cache:
        return _humansl_available_cache[model_path]
    result = os.path.exists(model_path)
    _humansl_available_cache[model_path] = result
    return result


def build_humansl_query(
    request: AnalysisRequest,
    config: EnrichmentConfig,
) -> dict | None:
    """Build a KataGo query with humanSLProfile parameter.

    Returns None if HumanSL is not available.
    """
    if not is_humansl_available(config):
        logger.debug("HumanSL model not available — skipping")
        return None

    payload = request.to_katago_json()
    payload["humanSLProfile"] = config.humansl.profile_name

    if config.humansl.humanSLCalibrateStrength is not None:
        payload["overrideSettings"] = payload.get("overrideSettings", {})
        payload["overrideSettings"]["humanSLCalibrateStrength"] = (
            config.humansl.humanSLCalibrateStrength
        )

    logger.info(
        "HumanSL query built: profile=%s, strength=%s",
        config.humansl.profile_name,
        config.humansl.humanSLCalibrateStrength,
    )
    return payload
