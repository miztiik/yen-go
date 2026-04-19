"""yen-sei CLI entry point.

Usage:
    python -m tools.yen_sei select [--dry-run]
    python -m tools.yen_sei ingest [--min-score 0.5] [--dry-run]
    python -m tools.yen_sei harvest
    python -m tools.yen_sei refine [--stats]
    python -m tools.yen_sei validate [--input path]
    python -m tools.yen_sei serve

Data isolation: ingest scans external-sources/, scores puzzles, and copies
qualified files into data/sources/ as a flat directory. All other stages
read only from data/. External-sources/ is never touched after ingest.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="yen-sei",
        description="Go Teaching Model SFT Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline stage to run")

    # select — scan and produce qualification report (LEGACY, v1)
    select_parser = subparsers.add_parser(
        "select", help="[v1 legacy] Scan all external-sources, score puzzles, produce report"
    )
    select_parser.add_argument(
        "--dry-run", action="store_true",
        help="Print report only, don't save files",
    )

    # qualify — v2 config-driven scan + tier classification (no copying)
    qualify_parser = subparsers.add_parser(
        "qualify",
        help="[v2] Scan all external-sources, classify each puzzle into Gold/Silver/Bronze/Drop "
             "per curation_config.json. Writes qualification_v2.jsonl + report. NO files copied.",
    )
    qualify_parser.add_argument("--config", type=str, help="Path to curation_config.json")
    qualify_parser.add_argument("--output-jsonl", type=str, help="Override JSONL output path")
    qualify_parser.add_argument("--output-report", type=str, help="Override report path")
    qualify_parser.add_argument(
        "--limit-per-source", type=int, default=None,
        help="Cap files per source (smoke testing only)",
    )
    qualify_parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of process workers (default: cpu_count - 1)",
    )
    qualify_parser.add_argument(
        "--path", type=str, default=None,
        help="Scan only this directory tree (e.g. external-sources/authors/SomeNewBook). "
             "Useful for evaluating a new author/folder without re-scanning 213K files.",
    )
    qualify_parser.add_argument(
        "--source", type=str, default=None,
        help="Override the source name (default: first segment under external-sources/). "
             "Only meaningful with --path.",
    )
    qualify_parser.add_argument(
        "--upsert", action="store_true",
        help="With --path, MERGE results into existing qualification_v2.jsonl by replacing "
             "rows with matching file_path. Without --upsert, the jsonl is overwritten.",
    )

    # sample — print N random puzzles from a tier
    sample_parser = subparsers.add_parser(
        "sample", help="[v2] Print N random puzzles from a tier (after qualify)"
    )
    sample_parser.add_argument("--tier", required=True, choices=["gold", "silver", "bronze", "drop"])
    sample_parser.add_argument("--source", default=None, help="Filter to one source (optional)")
    sample_parser.add_argument("--n", type=int, default=10, help="Number of samples")
    sample_parser.add_argument("--input", default=None, help="Path to qualification_v2.jsonl")

    # ingest — v2 tier-aware copy from qualification_v2.jsonl
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="[v2] Copy qualified SGFs into data/sources/ with tier-prefixed names "
             "(reads qualification_v2.jsonl from `qualify`).",
    )
    ingest_parser.add_argument("--config", type=str, help="Path to curation_config.json")
    ingest_parser.add_argument("--qualification", type=str, help="Path to qualification_v2.jsonl")
    ingest_parser.add_argument(
        "--tiers", type=str, default="gold,silver",
        help="Comma-separated tiers to ingest (default: gold,silver — bronze excluded as below SFT-quality bar)",
    )
    ingest_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be copied without copying",
    )
    ingest_parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip clearing data/sources/ before copying",
    )

    # harvest
    harvest_parser = subparsers.add_parser(
        "harvest", help="Extract comments from data/sources/ SGFs"
    )
    harvest_parser.add_argument("--output", type=str, help="Output JSONL path")

    # refine
    refine_parser = subparsers.add_parser("refine", help="Filter and format into SFT JSONL")
    refine_parser.add_argument("--input", type=str, help="Input raw JSONL path")
    refine_parser.add_argument("--output", type=str, help="Output SFT JSONL path")
    refine_parser.add_argument("--min-length", type=int, default=80, help="Min comment length")
    refine_parser.add_argument("--stats", action="store_true", help="Print statistics")
    refine_parser.add_argument("--config", type=str, help="Path to curation_config.json (for tier weights)")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate refined SFT output")
    validate_parser.add_argument("--input", type=str, help="Input SFT JSONL path")
    validate_parser.add_argument(
        "--max-failure-rate", type=float, default=0.05,
        help="Max allowed failure rate (default: 0.05)",
    )

    # eval_prep
    eval_prep_parser = subparsers.add_parser(
        "eval-prep",
        help="Build named eval test sets from qualification jsonl + curation_config.test_sets[]",
    )
    eval_prep_parser.add_argument("--qualification", type=str, help="Override qualification jsonl path")
    eval_prep_parser.add_argument("--config", type=str, help="Path to curation_config.json")
    eval_prep_parser.add_argument("--seed", type=int, default=42, help="Sampling seed")

    # serve
    subparsers.add_parser("serve", help="Launch monitoring GUI")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "select":
        from tools.yen_sei.selector import (
            DATA_DIR,
            generate_report,
            scan_all_sources,
        )
        import json
        import time

        print("YEN-SEI Puzzle Selector")
        print("Scanning all external sources...\n")
        start = time.time()
        results = scan_all_sources(verbose=True)
        elapsed = time.time() - start
        print(f"\nScan completed in {elapsed:.1f}s")

        report = generate_report(results)
        print("\n" + report)

        if not args.dry_run:
            report_path = DATA_DIR / "qualification_report.txt"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            print(f"\nReport saved to: {report_path}")

            json_path = DATA_DIR / "qualification_scores.json"
            json_data = {}
            for source, scores in results.items():
                json_data[source] = {
                    "total": len(scores),
                    "passed": sum(1 for s in scores if s.passes_gates),
                    "tier_a": sum(1 for s in scores if s.passes_gates and s.total_score >= 0.5),
                    "tier_b": sum(1 for s in scores if s.passes_gates and 0.3 <= s.total_score < 0.5),
                    "tier_c": sum(1 for s in scores if s.passes_gates and s.total_score < 0.3),
                }
            json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            print(f"Scores saved to: {json_path}")

    elif args.command == "ingest":
        from tools.yen_sei.stages.ingest import run_ingest

        tiers = tuple(t.strip() for t in args.tiers.split(",") if t.strip())
        run_ingest(
            qualification_jsonl=args.qualification,
            config_path=args.config,
            tiers=tiers,
            dry_run=args.dry_run,
            clean=not args.no_clean,
        )

    elif args.command == "qualify":
        from tools.yen_sei.stages.qualify import run_qualify

        run_qualify(
            config_path=args.config,
            output_jsonl=args.output_jsonl,
            output_report=args.output_report,
            limit_per_source=args.limit_per_source,
            workers=args.workers,
            scan_path=args.path,
            source_name=args.source,
            upsert=args.upsert,
        )

    elif args.command == "sample":
        from tools.yen_sei.stages.qualify import sample_tier

        sample_tier(
            tier=args.tier,
            source=args.source,
            n=args.n,
            jsonl_path=args.input,
        )

    elif args.command == "harvest":
        from tools.yen_sei.stages.harvest import run_harvest

        run_harvest(output_path=args.output)

    elif args.command == "refine":
        from tools.yen_sei.stages.refine import run_refine

        run_refine(
            input_path=args.input,
            output_path=args.output,
            min_length=args.min_length,
            show_stats=args.stats,
            config_path=args.config,
        )

    elif args.command == "validate":
        from tools.yen_sei.stages.validate import run_validate

        return run_validate(
            input_path=args.input,
            max_failure_rate=args.max_failure_rate,
        )

    elif args.command == "eval-prep":
        from tools.yen_sei.stages.eval_prep import run_eval_prep

        run_eval_prep(
            qualification_jsonl=args.qualification,
            config_path=args.config,
            seed=args.seed,
        )

    elif args.command == "serve":
        print("GUI server not yet implemented. See PLAN.md for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
