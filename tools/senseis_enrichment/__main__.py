"""CLI entry point for Senseis enrichment tool.

Usage:
    # Audit mode: build decision ledger (no SGF writes)
    python -m tools.senseis_enrichment --audit

    # Audit a specific range
    python -m tools.senseis_enrichment --audit --start 1 --end 50

    # Full run (all 347 problems, resumes from checkpoint)
    python -m tools.senseis_enrichment

    # Specific range
    python -m tools.senseis_enrichment --start 1 --end 10

    # Dry run (fetch + match only, no merge)
    python -m tools.senseis_enrichment --dry-run

    # Reset checkpoint and start fresh
    python -m tools.senseis_enrichment --reset

    # Show current status
    python -m tools.senseis_enrichment --status
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from tools.core.checkpoint import clear_checkpoint, load_checkpoint
from tools.senseis_enrichment.config import SenseisConfig, load_config
from tools.senseis_enrichment.orchestrator import EnrichmentCheckpoint, run_enrichment


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet httpx unless verbose
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _show_status(config: SenseisConfig | None = None) -> None:
    """Display current checkpoint status."""
    if config is None:
        config = load_config()
    ckpt_dir = config.working_dir()
    checkpoint = load_checkpoint(ckpt_dir, EnrichmentCheckpoint)
    config = load_config()

    if checkpoint is None:
        print("No checkpoint found. Pipeline has not been run yet.")
        return

    print(f"Collection: {config.local_dir}")
    print(f"Total problems: {config.problem_count}")
    print(f"Last completed: {checkpoint.last_completed}/{config.problem_count}")
    print(f"Matched: {checkpoint.total_matched}")
    print(f"Enriched: {checkpoint.total_enriched}")
    print(f"Failed: {checkpoint.total_failed}")
    print(f"Skipped: {checkpoint.total_skipped}")
    if checkpoint.failed_problems:
        print(f"Failed problems: {checkpoint.failed_problems}")
    if checkpoint.skipped_problems:
        print(f"Skipped problems: {checkpoint.skipped_problems}")
    print(f"Last updated: {checkpoint.last_updated}")

    remaining = config.problem_count - checkpoint.last_completed
    if remaining > 0:
        print(f"\nRemaining: {remaining} problems")
        print("Run `python -m tools.senseis_enrichment` to continue.")
    else:
        print("\nAll problems processed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="senseis_enrichment",
        description="Enrich local SGF puzzles with Senseis Library metadata and commentary.",
    )
    parser.add_argument(
        "--start", type=int, default=None,
        help="First problem number (1-based, overrides checkpoint)",
    )
    parser.add_argument(
        "--end", type=int, default=None,
        help="Last problem number (inclusive)",
    )
    parser.add_argument(
        "--audit", action="store_true",
        help="Audit mode: classify all problems and output decision ledger (no SGF writes)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and match only, don't merge into SGFs",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear checkpoint and start from scratch",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current pipeline status and exit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config JSON file (defaults to senseis_config.json in tool dir)",
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="Delete solution cache before running (re-fetches solution pages with updated parser)",
    )
    parser.add_argument(
        "--eval", action="store_true",
        help="Evaluate enrichment quality against cache truth (post-enrichment validation)",
    )
    parser.add_argument(
        "--eval-pct", type=float, default=40.0,
        help="Percentage of problems to sample for eval (default: 40)",
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    if args.status:
        _show_status(config)
        return

    if args.refresh:
        solution_cache = config.working_dir() / "_solution_cache"
        if solution_cache.exists():
            count = sum(1 for _ in solution_cache.glob("*.json"))
            shutil.rmtree(solution_cache)
            print(f"Deleted solution cache ({count} files). Will re-fetch solution pages.")
        else:
            print("No solution cache to refresh.")

    if args.audit:
        from tools.senseis_enrichment.audit import run_audit
        run_audit(config=config, start=args.start or 1, end=args.end)
        return

    if args.eval:
        from tools.senseis_enrichment.eval import run_eval
        report = run_eval(
            config=config,
            sample_pct=args.eval_pct,
            start=args.start,
            end=args.end,
        )
        sys.exit(0 if report.overall_pass else 1)

    if args.reset:
        clear_checkpoint(config.working_dir())
        print("Checkpoint cleared. Will start from problem 1.")
        if not args.start and not args.end:
            return  # Just clearing, not running

    summary = run_enrichment(
        config=config,
        start=args.start,
        end=args.end,
        dry_run=args.dry_run,
    )

    # Exit code: 0 if no failures, 1 if any failed
    sys.exit(1 if summary["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
