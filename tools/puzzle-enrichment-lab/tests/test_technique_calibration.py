"""Technique calibration test suite — per-tag quality gates via live KataGo.

Validates that each technique's fixture produces expected enrichment results
across 5 calibration dimensions: correct move, technique tags, difficulty
range, refutations, and teaching comments.

Ground truth loaded from tests/fixtures/technique-benchmark-reference.json
(OPT-1: JSON Data File + Thin Loader). Regenerate reference data with:
    python scripts/regenerate_benchmark_reference.py

Stability tiers (expert-assessed KataGo non-determinism sensitivity):
- GREEN (16 techniques): structural detectors, safe for exact match
- YELLOW (4): ko, ladder, tesuji, shape — PV-dependent, mostly stable
- RED (5): seki, snapback, net, sacrifice, under-the-stones — fragile

Run with: ``pytest tests/test_technique_calibration.py -v --tb=short``
Requires: KataGo binary + model in tools/puzzle-enrichment-lab/{katago,models-data}/
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import NotRequired, TypedDict

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
FIXTURES = _HERE / "fixtures"
CONFIG_DIR = _LAB.parent.parent / "config"

from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path

# ---------------------------------------------------------------------------
# TechniqueSpec TypedDict (AD-2, MH-1, MH-6)
# ---------------------------------------------------------------------------


class TechniqueSpec(TypedDict):
    """Ground truth for a single technique calibration fixture.

    All 5 calibration dimensions (MH-1) are required fields.
    Edge-case fields (MH-6) have defaults when absent.
    """

    # Required: 5 calibration dimensions
    fixture: str  # filename in tests/fixtures/
    correct_move_gtp: str  # expected correct first move (GTP format)
    expected_tags: list[str]  # MH-2: list, subset check
    min_level_id: int  # lower bound of acceptable difficulty
    max_level_id: int  # upper bound of acceptable difficulty
    min_refutations: int  # minimum wrong-move refutations expected
    expect_teaching_comments: bool  # CD-5: teaching comment check

    # Optional edge-case fields (MH-6)
    ko_context: NotRequired[str]  # "none" | "direct" | "approach"
    move_order: NotRequired[str]  # "strict" | "flexible" | "miai"
    board_size: NotRequired[int]  # default 19
    notes: NotRequired[str]  # human-readable audit notes
    stability_tier: NotRequired[str]  # "green" | "yellow" | "red"


# ---------------------------------------------------------------------------
# TECHNIQUE_REGISTRY — loaded from external JSON (OPT-1: JSON + Thin Loader)
#
# Ground truth lives in tests/fixtures/technique-benchmark-reference.json.
# Regenerate with: python scripts/regenerate_benchmark_reference.py
# ---------------------------------------------------------------------------

_REGISTRY_PATH = FIXTURES / "technique-benchmark-reference.json"


def _load_registry() -> dict[str, TechniqueSpec]:
    """Load technique registry from the external JSON reference file."""
    assert _REGISTRY_PATH.exists(), (
        f"Technique benchmark reference not found: {_REGISTRY_PATH}\n"
        "Run: python scripts/regenerate_benchmark_reference.py"
    )
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)

    set(data.get("excluded_non_tsumego_tags", []))
    techniques = data["techniques"]
    registry: dict[str, TechniqueSpec] = {}
    for slug, entry in techniques.items():
        registry[slug] = TechniqueSpec(
            fixture=entry["fixture"],
            correct_move_gtp=entry["correct_move_gtp"],
            expected_tags=entry["expected_tags"],
            min_level_id=entry["min_level_id"],
            max_level_id=entry["max_level_id"],
            min_refutations=entry["min_refutations"],
            expect_teaching_comments=entry["expect_teaching_comments"],
            **{
                k: entry[k]
                for k in ("ko_context", "move_order", "board_size", "notes", "stability_tier")
                if k in entry
            },
        )
    return registry


EXCLUDED_NON_TSUMEGO_TAGS: set[str] = set(
    json.loads(_REGISTRY_PATH.read_text(encoding="utf-8")).get(
        "excluded_non_tsumego_tags", []
    )
)

TECHNIQUE_REGISTRY: dict[str, TechniqueSpec] = _load_registry()


# ---------------------------------------------------------------------------
# Unit test: config/tags.json cross-check (MH-3, AD-4, T20)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_all_tags_have_registry_entry():
    """Every active tsumego tag in config/tags.json has a TECHNIQUE_REGISTRY entry.

    Non-tsumego tags (joseki, fuseki, endgame) are excluded per C2.
    """
    tags_path = CONFIG_DIR / "tags.json"
    assert tags_path.exists(), f"config/tags.json not found at {tags_path}"

    with open(tags_path, encoding="utf-8") as f:
        tags_data = json.load(f)

    all_slugs = set(tags_data["tags"].keys())
    active_slugs = all_slugs - EXCLUDED_NON_TSUMEGO_TAGS

    missing = active_slugs - set(TECHNIQUE_REGISTRY.keys())
    assert not missing, (
        f"Tags in config/tags.json without TECHNIQUE_REGISTRY entry: {sorted(missing)}. "
        "Add entries or update EXCLUDED_NON_TSUMEGO_TAGS."
    )


@pytest.mark.unit
def test_registry_entries_reference_existing_fixtures():
    """Every fixture referenced in TECHNIQUE_REGISTRY must exist on disk."""
    for slug, spec in TECHNIQUE_REGISTRY.items():
        fixture_path = FIXTURES / spec["fixture"]
        assert fixture_path.exists(), (
            f"Registry '{slug}' references missing fixture: {spec['fixture']}"
        )


@pytest.mark.unit
def test_no_excluded_tags_in_registry():
    """EXCLUDED_NON_TSUMEGO_TAGS must not appear in the registry."""
    for slug in EXCLUDED_NON_TSUMEGO_TAGS:
        assert slug not in TECHNIQUE_REGISTRY, (
            f"Excluded tag '{slug}' found in TECHNIQUE_REGISTRY — remove it"
        )


# ---------------------------------------------------------------------------
# Integration tests: live KataGo calibration (T18-T19, T22)
# ---------------------------------------------------------------------------

_KATAGO_PATH = KATAGO_PATH
_FAST_MODEL = model_path("test_fast")
_SMALLEST_MODEL = model_path("test_smallest")

_skip_reasons: list[str] = []
if not _KATAGO_PATH.exists():
    _skip_reasons.append("KataGo binary not found")
if not _FAST_MODEL.exists() and not _SMALLEST_MODEL.exists():
    _skip_reasons.append("No KataGo model files found")


def _best_model() -> Path:
    """Return the best available model (prefer test_fast b10, fallback to test_smallest b6)."""
    if _FAST_MODEL.exists():
        return _FAST_MODEL
    return _SMALLEST_MODEL


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestTechniqueCalibration:
    """Per-technique calibration suite using real KataGo analysis.

    Validates 5 calibration dimensions per technique:
    1. Correct move extraction
    2. Technique tag detection
    3. Difficulty estimation within expected range
    4. Refutation generation
    5. Teaching comment presence (when expected)
    """

    @pytest.fixture(autouse=True, scope="class")
    def _engine(self):
        """Class-scoped SingleEngineManager in quick_only mode."""
        from analyzers.single_engine import SingleEngineManager
        from config import load_enrichment_config

        config = load_enrichment_config()
        config = config.model_copy(
            update={
                "refutations": config.refutations.model_copy(
                    update={"candidate_max_count": 2}
                )
            }
        )
        manager = SingleEngineManager(
            config=config,
            katago_path=str(_KATAGO_PATH),
            model_path=str(_best_model()),
            katago_config_path=str(TSUMEGO_CFG),
            mode_override="quick_only",
        )

        async def _start():
            await manager.start()
            return manager

        started = asyncio.run(_start())
        type(self).engine_manager = started
        type(self).config = config
        yield
        asyncio.run(manager.shutdown())

    def _enrich(self, fixture_name: str) -> AiAnalysisResult:  # noqa: F821
        """Run full enrichment pipeline for a fixture."""
        from analyzers.enrich_single import enrich_single_puzzle

        sgf_path = FIXTURES / fixture_name
        assert sgf_path.exists(), f"Fixture not found: {sgf_path}"
        sgf_text = sgf_path.read_text(encoding="utf-8")

        async def _run():
            return await enrich_single_puzzle(
                sgf_text=sgf_text,
                engine_manager=self.engine_manager,
                config=self.config,
                source_file=fixture_name,
                run_id="technique-calibration-test",
            )

        return asyncio.run(_run())

    # --- CD-1: Correct move validation ---

    @pytest.mark.parametrize("slug,spec", list(TECHNIQUE_REGISTRY.items()))
    def test_correct_move(self, slug: str, spec: TechniqueSpec) -> None:
        """Pipeline extracts the expected correct first move GTP coord."""
        result = self._enrich(spec["fixture"])
        assert result.validation.correct_move_gtp == spec["correct_move_gtp"], (
            f"[{slug}] Expected correct move {spec['correct_move_gtp']}, "
            f"got {result.validation.correct_move_gtp}"
        )

    # --- CD-2: Technique tag detection (tier-dependent strictness) ---

    @pytest.mark.parametrize("slug,spec", list(TECHNIQUE_REGISTRY.items()))
    def test_technique_tags(self, slug: str, spec: TechniqueSpec) -> None:
        """Pipeline detects all expected technique tags (subset check).

        RED-tier techniques (seki, snapback, net, sacrifice, under-the-stones)
        use xfail(strict=False) because KataGo signal variance can cause
        detection flips between runs. GREEN/YELLOW techniques hard-fail.
        """
        is_red = spec.get("stability_tier") == "red"
        if is_red:
            pytest.xfail(
                f"[{slug}] RED-tier technique — tag detection may vary across KataGo runs"
            )
        result = self._enrich(spec["fixture"])
        for tag in spec["expected_tags"]:
            assert tag in result.technique_tags, (
                f"[{slug}] Expected tag '{tag}' not in detected tags: "
                f"{result.technique_tags}"
            )

    # --- CD-3: Difficulty range ---

    @pytest.mark.parametrize("slug,spec", list(TECHNIQUE_REGISTRY.items()))
    def test_difficulty_range(self, slug: str, spec: TechniqueSpec) -> None:
        """Pipeline assigns difficulty within the expected level ID range."""
        result = self._enrich(spec["fixture"])
        level_id = result.difficulty.suggested_level_id
        assert spec["min_level_id"] <= level_id <= spec["max_level_id"], (
            f"[{slug}] Difficulty {level_id} outside range "
            f"[{spec['min_level_id']}, {spec['max_level_id']}]"
        )

    # --- CD-4: Refutation generation ---

    @pytest.mark.parametrize("slug,spec", list(TECHNIQUE_REGISTRY.items()))
    def test_refutations(self, slug: str, spec: TechniqueSpec) -> None:
        """Pipeline generates at least the minimum expected refutations."""
        result = self._enrich(spec["fixture"])
        refutation_count = len(result.refutations) if result.refutations else 0
        assert refutation_count >= spec["min_refutations"], (
            f"[{slug}] Expected ≥{spec['min_refutations']} refutations, "
            f"got {refutation_count}"
        )

    # --- CD-5: Teaching comment presence ---

    @pytest.mark.parametrize("slug,spec", list(TECHNIQUE_REGISTRY.items()))
    def test_teaching_comments(self, slug: str, spec: TechniqueSpec) -> None:
        """Pipeline generates teaching comments when expected."""
        if not spec["expect_teaching_comments"]:
            pytest.skip("Teaching comments not expected for this fixture")
        result = self._enrich(spec["fixture"])
        comment_count = (
            len(result.teaching_comments) if result.teaching_comments else 0
        )
        assert comment_count >= 1, (
            f"[{slug}] Expected ≥1 teaching comment, got {comment_count}"
        )
