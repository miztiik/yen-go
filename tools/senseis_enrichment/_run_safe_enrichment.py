"""Run enrichment ONLY for exact_match and rotated_match puzzles.

Skips translated_mismatch and review problems. Uses cached page/solution
data from the audit phase — no network requests needed.

Usage:
    python -m tools.senseis_enrichment._run_safe_enrichment
    python -m tools.senseis_enrichment._run_safe_enrichment --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from tools.senseis_enrichment.config import SenseisConfig, load_config
from tools.senseis_enrichment.merger import merge_problem, prepare_enriched_directory
from tools.senseis_enrichment.models import (
    MatchResult,
    PositionTransform,
    SenseisPageData,
    SenseisSolutionData,
)

logger = logging.getLogger("senseis_enrichment.safe_enrichment")

SAFE_MATCH_CLASSES = {"exact_match", "rotated_match"}
SAFE_DECISIONS = {"enrich"}  # excludes enrich_number_fallback and review


def _parse_transform(match_transform: str) -> PositionTransform | None:
    """Parse audit ledger transform string like 'rot=0,ref=True' or 'identity'."""
    if not match_transform or match_transform == "identity":
        return PositionTransform(rotation=0, reflect=False)

    m = re.match(r"rot=(\d+),ref=(True|False)", match_transform)
    if m:
        return PositionTransform(
            rotation=int(m.group(1)),
            reflect=m.group(2) == "True",
        )
    return None


def _load_cached_page(config: SenseisConfig, n: int) -> SenseisPageData | None:
    path = config.working_dir() / "_page_cache" / f"{n:04d}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SenseisPageData.from_dict(data)


def _load_cached_solution(config: SenseisConfig, n: int) -> SenseisSolutionData | None:
    path = config.working_dir() / "_solution_cache" / f"{n:04d}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SenseisSolutionData.from_dict(data)


def _load_ledger(config: SenseisConfig) -> dict:
    path = config.working_dir() / "_audit_ledger.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run(dry_run: bool = False) -> dict:
    config = load_config()
    ledger = _load_ledger(config)
    entries = ledger["entries"]

    # Filter to safe enrichment candidates
    safe_entries = [
        e for e in entries
        if e.get("match_class") in SAFE_MATCH_CLASSES
        and e.get("decision") in SAFE_DECISIONS
        and e.get("local_file_exists", False)
    ]

    logger.info(
        "Safe enrichment: %d/%d puzzles (exact_match + rotated_match with 'enrich' decision)",
        len(safe_entries), len(entries),
    )

    if not dry_run:
        prepare_enriched_directory(config)

    enriched = 0
    failed = 0
    skipped = 0
    failed_problems: list[int] = []
    results: list[dict] = []

    for entry in safe_entries:
        n = entry["problem_number"]
        match_class = entry["match_class"]
        transform_str = entry.get("match_transform", "")
        sol_status = entry.get("solution_status", "")

        # Reconstruct MatchResult from ledger
        transform = _parse_transform(transform_str)
        match_result = MatchResult(
            problem_number=n,
            matched=True,
            transform=transform,
            local_hash=entry.get("local_hash", ""),
            senseis_hash=entry.get("senseis_hash", ""),
            detail=f"D4 match ({transform_str})",
        )

        # Load cached data
        page_data = _load_cached_page(config, n)
        solution_data = _load_cached_solution(config, n)

        diag_count = len(solution_data.diagrams) if solution_data else 0
        commentary_diags = sum(1 for d in (solution_data.diagrams if solution_data else []) if d.commentary.strip())

        if dry_run:
            results.append({
                "problem": n,
                "match_class": match_class,
                "transform": transform_str,
                "sol_status": sol_status,
                "diagrams": diag_count,
                "commentary_diagrams": commentary_diags,
                "has_page": page_data is not None,
            })
            enriched += 1
            continue

        # Actually merge
        logger.info("--- P%d: %s (%s), %d diagrams ---", n, match_class, transform_str, diag_count)
        try:
            success = merge_problem(config, n, page_data, solution_data, match_result)
            if success:
                enriched += 1
                results.append({"problem": n, "status": "ok"})
            else:
                failed += 1
                failed_problems.append(n)
                results.append({"problem": n, "status": "failed"})
        except Exception as e:
            logger.error("P%d: exception during merge: %s", n, e)
            failed += 1
            failed_problems.append(n)
            results.append({"problem": n, "status": "error", "error": str(e)})

    summary = {
        "mode": "dry-run" if dry_run else "enrichment",
        "total_candidates": len(safe_entries),
        "enriched": enriched,
        "failed": failed,
        "skipped": skipped,
        "failed_problems": failed_problems,
    }

    # Save results
    results_path = config.working_dir() / "_safe_enrichment_results.json"
    results_path.write_text(
        json.dumps({"summary": summary, "details": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run safe enrichment (exact/rotated matches only)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be done without merging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    summary = run(dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"  SAFE ENRICHMENT {'DRY-RUN ' if args.dry_run else ''}RESULTS")
    print(f"{'='*60}")
    print(f"  Candidates (exact/rotated match): {summary['total_candidates']}")
    print(f"  Enriched:  {summary['enriched']}")
    print(f"  Failed:    {summary['failed']}")
    if summary['failed_problems']:
        print(f"  Failed problems: {summary['failed_problems']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
