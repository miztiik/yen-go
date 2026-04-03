#!/usr/bin/env python3
"""Regenerate technique-benchmark-reference.json from live KataGo enrichment.

Re-derives expected calibration values by enriching each technique fixture
through the full pipeline. Updates the JSON reference file that
test_technique_calibration.py loads at import time.

Usage:
    # Diff mode — show what would change, don't write
    python scripts/regenerate_benchmark_reference.py --dry-run

    # Write mode — update the JSON file in place
    python scripts/regenerate_benchmark_reference.py

Requires: KataGo binary + model in tools/puzzle-enrichment-lab/{katago,models-data}/
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
_TESTS = _LAB / "tests"
_FIXTURES = _TESTS / "fixtures"

# Ensure lab root is on sys.path for imports
sys.path.insert(0, str(_LAB))
sys.path.insert(0, str(_TESTS))

from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path

REFERENCE_PATH = _FIXTURES / "technique-benchmark-reference.json"


def _best_model() -> Path:
    """Return the best available model (prefer test_fast b10, fallback to test_smallest b6)."""
    fast = model_path("test_fast")
    if fast.exists():
        return fast
    return model_path("test_smallest")


async def _enrich_fixture(fixture_name: str, engine_manager, config) -> dict:
    """Enrich a single fixture and return a summary dict."""
    from analyzers.enrich_single import enrich_single_puzzle

    sgf_path = _FIXTURES / fixture_name
    assert sgf_path.exists(), f"Fixture not found: {sgf_path}"
    sgf_text = sgf_path.read_text(encoding="utf-8")

    result = await enrich_single_puzzle(
        sgf_text=sgf_text,
        engine_manager=engine_manager,
        config=config,
        source_file=fixture_name,
        run_id="regen-benchmark-reference",
    )

    return {
        "correct_move_gtp": result.validation.correct_move_gtp,
        "technique_tags": sorted(result.technique_tags) if result.technique_tags else [],
        "level_id": result.difficulty.suggested_level_id,
        "refutation_count": len(result.refutations) if result.refutations else 0,
        "has_teaching_comments": bool(
            result.teaching_comments and len(result.teaching_comments) > 0
        ),
    }


async def _run_all(reference: dict) -> dict[str, dict]:
    """Enrich all technique fixtures and return results keyed by slug."""
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
        katago_path=str(KATAGO_PATH),
        model_path=str(_best_model()),
        katago_config_path=str(TSUMEGO_CFG),
        mode_override="quick_only",
    )
    await manager.start()

    results = {}
    techniques = reference["techniques"]
    try:
        for slug, entry in techniques.items():
            print(f"  Enriching {slug} ({entry['fixture']})...", flush=True)
            results[slug] = await _enrich_fixture(
                entry["fixture"], manager, config
            )
    finally:
        await manager.shutdown()

    return results


def _diff_entry(slug: str, current: dict, enriched: dict) -> list[str]:
    """Compare current reference entry with enriched result, return diff lines."""
    diffs = []

    if current["correct_move_gtp"] != enriched["correct_move_gtp"]:
        diffs.append(
            f"  correct_move_gtp: {current['correct_move_gtp']} → {enriched['correct_move_gtp']}"
        )

    cur_tags = set(current["expected_tags"])
    new_tags = set(enriched["technique_tags"])
    if not cur_tags.issubset(new_tags):
        missing = cur_tags - new_tags
        diffs.append(f"  expected_tags missing: {sorted(missing)}")
    extra = new_tags - cur_tags
    if extra:
        diffs.append(f"  new tags detected: {sorted(extra)}")

    level_id = enriched["level_id"]
    if not (current["min_level_id"] <= level_id <= current["max_level_id"]):
        diffs.append(
            f"  level_id: {level_id} outside [{current['min_level_id']}, {current['max_level_id']}]"
        )

    if enriched["refutation_count"] < current["min_refutations"]:
        diffs.append(
            f"  refutations: {enriched['refutation_count']} < min {current['min_refutations']}"
        )

    return diffs


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Regenerate technique-benchmark-reference.json"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show diffs without writing the file",
    )
    args = parser.parse_args()

    # Validate prerequisites
    if not KATAGO_PATH.exists():
        print(f"ERROR: KataGo binary not found: {KATAGO_PATH}", file=sys.stderr)
        return 1
    if not _best_model().exists():
        print("ERROR: No KataGo model files found", file=sys.stderr)
        return 1
    if not REFERENCE_PATH.exists():
        print(f"ERROR: Reference file not found: {REFERENCE_PATH}", file=sys.stderr)
        return 1

    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    techniques = reference["techniques"]

    print(f"Enriching {len(techniques)} technique fixtures...")
    enriched = asyncio.run(_run_all(reference))

    # Compute diffs
    has_diffs = False
    for slug in techniques:
        if slug not in enriched:
            print(f"  SKIP {slug} (enrichment failed)")
            continue
        diffs = _diff_entry(slug, techniques[slug], enriched[slug])
        if diffs:
            has_diffs = True
            print(f"\n{slug}:")
            for d in diffs:
                print(d)

    if not has_diffs:
        print("\nNo differences found — reference file is up to date.")
        return 0

    if args.dry_run:
        print("\n--dry-run: no changes written.")
        return 0

    # Write updated reference
    reference["_metadata"]["last_updated"] = date.today().isoformat()
    REFERENCE_PATH.write_text(
        json.dumps(reference, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nUpdated: {REFERENCE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
