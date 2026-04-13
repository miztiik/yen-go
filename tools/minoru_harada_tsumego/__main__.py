"""CLI entry point for Harada tsumego archive tool.

Usage:
    python -m tools.minoru_harada_tsumego discover [--dry-run]
    python -m tools.minoru_harada_tsumego download [--dry-run] [--limit N]
    python -m tools.minoru_harada_tsumego recognize --image FILE
    python -m tools.minoru_harada_tsumego recognize --all [--limit N] [--output-dir DIR]
    python -m tools.minoru_harada_tsumego status
    python -m tools.minoru_harada_tsumego clean [--year YYYY] [--wipe]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.core.logging import setup_logging
from tools.minoru_harada_tsumego.config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harada_tsumego",
        description="Crawl and catalog Harada tsumego archive from Wayback Machine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # discover
    discover_parser = subparsers.add_parser(
        "discover",
        help="Crawl index and year pages to build puzzle catalog",
    )
    discover_parser.add_argument("--dry-run", action="store_true", help="Preview without fetching")
    discover_parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")

    # download
    download_parser = subparsers.add_parser(
        "download",
        help="Download problem/answer pages and images",
    )
    download_parser.add_argument("--dry-run", action="store_true", help="Preview without downloading")
    download_parser.add_argument("--limit", type=int, default=0, help="Limit number of puzzles to process")
    download_parser.add_argument(
        "--retry-only", action="store_true",
        help="Skip fully completed puzzles; only process pending/failed",
    )
    download_parser.add_argument(
        "--year", type=int, default=None,
        help="Only process puzzles from this year (e.g. --year 1996)",
    )
    download_parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")

    # recognize
    recognize_parser = subparsers.add_parser(
        "recognize",
        help="Recognise board positions from downloaded images",
    )
    recognize_parser.add_argument(
        "--image", type=str, help="Single image path to recognise",
    )
    recognize_parser.add_argument(
        "--all", action="store_true", dest="batch",
        help="Process all downloaded problem images",
    )
    recognize_parser.add_argument(
        "--output-dir", type=str, help="Write SGF files to this directory",
    )
    recognize_parser.add_argument(
        "--limit", type=int, default=0, help="Max images to process in batch mode",
    )

    # build
    build_parser = subparsers.add_parser(
        "build",
        help="Build SGFs with solution trees from problem/answer image pairs",
    )
    build_parser.add_argument(
        "--puzzle", type=int, help="Single puzzle number to build",
    )
    build_parser.add_argument(
        "--level", type=str, choices=["elementary", "intermediate"],
        help="Build only the specified level",
    )
    build_parser.add_argument(
        "--all", action="store_true", dest="build_all",
        help="Process all puzzles with downloaded images",
    )
    build_parser.add_argument(
        "--output-dir", type=str, help="Write SGF files to this directory",
    )
    build_parser.add_argument(
        "--limit", type=int, default=0, help="Max puzzles to process in batch mode",
    )

    # status
    subparsers.add_parser("status", help="Show catalog status")

    # clean
    clean_parser = subparsers.add_parser(
        "clean",
        help="Delete downloaded images and reset download state",
    )
    clean_parser.add_argument(
        "--year", type=int, default=None,
        help="Only clean images for this year (e.g. --year 1996)",
    )
    clean_parser.add_argument(
        "--wipe", action="store_true",
        help="Also delete catalog and checkpoints (full reset)",
    )

    # eval — evaluate digit detection accuracy
    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluate digit detection accuracy against ground truth",
    )
    eval_parser.add_argument(
        "--compare", action="store_true",
        help="Show comparison table of all evaluation runs",
    )
    eval_parser.add_argument(
        "--run-id", type=str, default=None,
        help="Custom run ID for this evaluation (auto-generated if omitted)",
    )
    eval_parser.add_argument(
        "--no-save", action="store_true",
        help="Run evaluation but don't save results to eval_results.json",
    )
    eval_parser.add_argument(
        "--cv", action="store_true",
        help="Run leave-one-image-out cross-validation (honest accuracy)",
    )
    eval_parser.add_argument(
        "--holdout", action="store_true",
        help="Evaluate only holdout images using production templates",
    )

    # reparse — re-extract text from cached pages using updated parser
    subparsers.add_parser(
        "reparse",
        help="Re-extract answer text from cached HTML pages (refreshes catalog)",
    )

    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "status":
        from tools.minoru_harada_tsumego.orchestrator import show_status
        show_status(config)
        return 0

    if args.command == "clean":
        from tools.minoru_harada_tsumego.orchestrator import clean_downloads
        clean_downloads(config, year=args.year, keep_catalog=not args.wipe)
        return 0

    if args.command == "recognize":
        return _cmd_recognize(config, args)

    if args.command == "build":
        return _cmd_build(config, args)

    if args.command == "eval":
        return _cmd_eval(config, args)

    if args.command == "reparse":
        return _cmd_reparse(config)

    # Ensure working directory exists
    config.working_dir().mkdir(parents=True, exist_ok=True)

    verbose = getattr(args, "verbose", False)
    logger = setup_logging(
        config.working_dir(),
        "harada_tsumego",
        verbose=verbose,
        log_suffix="harada",
    )

    if args.command == "discover":
        from tools.minoru_harada_tsumego.orchestrator import run_discover
        catalog = run_discover(config, logger, dry_run=args.dry_run)
        print(f"\nDiscovered {len(catalog.puzzles)} puzzles across {len(catalog.years)} years")
        return 0

    elif args.command == "download":
        from tools.minoru_harada_tsumego.orchestrator import run_download
        catalog = run_download(
            config, logger,
            dry_run=args.dry_run,
            limit=args.limit,
            retry_only=args.retry_only,
            year=args.year,
        )
        catalog.update_stats()
        print(f"\nDownloaded {catalog.total_images_downloaded} images for {catalog.total_puzzles_discovered} puzzles")
        return 0

    return 1


def _cmd_recognize(config: object, args: argparse.Namespace) -> int:
    """Handle the 'recognize' subcommand."""
    from tools.core.image_to_board import (
        format_position,
        recognize_position,
    )
    from tools.minoru_harada_tsumego.sgf_converter import position_to_sgf

    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    if args.image:
        # --- Single-image mode ---
        pos = recognize_position(args.image)
        print(format_position(pos))

        if output_dir:
            sgf = position_to_sgf(pos, comment=f"Harada tsumego")
            out_path = output_dir / (Path(args.image).stem + ".sgf")
            out_path.write_text(sgf, encoding="utf-8")
            print(f"\nSGF → {out_path}")
        return 0

    if args.batch:
        # --- Batch mode: all downloaded problem images ---
        return _batch_recognize(config, output_dir, limit=args.limit)

    print("Specify --image FILE or --all for batch processing.", file=sys.stderr)
    return 1


def _cmd_build(config: object, args: argparse.Namespace) -> int:
    """Handle the 'build' subcommand — build SGFs with solution trees."""
    from tools.minoru_harada_tsumego.models import Catalog
    from tools.minoru_harada_tsumego.sgf_tree_builder import build_puzzle_sgf

    catalog_path = config.catalog_path()
    if not catalog_path.exists():
        print("No catalog found. Run 'discover' and 'download' first.", file=sys.stderr)
        return 1

    with open(catalog_path, encoding="utf-8") as f:
        catalog = Catalog.from_dict(json.load(f))

    image_dir = config.working_dir()
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    levels = [args.level] if args.level else ["elementary", "intermediate"]

    # --- Single puzzle mode ---
    if args.puzzle:
        entry = catalog.get_puzzle(args.puzzle)
        if not entry:
            print(f"Puzzle #{args.puzzle} not found in catalog.", file=sys.stderr)
            return 1

        for level in levels:
            result = build_puzzle_sgf(entry, level, image_dir)
            if result.error:
                print(f"  [{level}] ERROR: {result.error}", file=sys.stderr)
                continue
            print(f"Puzzle #{result.puzzle_number} ({result.level}):")
            print(f"  Correct moves: {result.correct_move_count}")
            print(f"  Wrong branches: {result.wrong_branch_count}")
            print(f"  Variations: {result.variation_branch_count}")
            if output_dir:
                level_tag = "e" if level == "elementary" else "m"
                out_name = f"harada_{entry.problem_number:04d}_{level_tag}.sgf"
                out_path = output_dir / out_name
                out_path.write_text(result.sgf, encoding="utf-8")
                print(f"  SGF → {out_path}")
            else:
                print(f"  SGF:\n{result.sgf}")
        return 0

    # --- Batch mode ---
    if not args.build_all:
        print("Specify --puzzle N or --all for batch processing.", file=sys.stderr)
        return 1

    built = 0
    errors = 0
    gated = 0
    with_solution_tree = 0
    setup_only = 0
    warnings_count = 0
    error_details: list[dict] = []
    gated_details: list[dict] = []
    validation_issues: list[dict] = []
    seq = 0

    for entry in catalog.puzzles:
        if args.limit and built >= args.limit:
            break
        if entry.downloaded_count() == 0:
            continue
        for level in levels:
            result = build_puzzle_sgf(entry, level, image_dir)
            if result.error:
                # Distinguish validation-gated from build errors
                if result.validation_warnings:
                    gated += 1
                    gated_details.append({
                        "puzzle": entry.problem_number,
                        "level": level,
                        "warnings": result.validation_warnings,
                        "error": result.error,
                    })
                else:
                    errors += 1
                    error_details.append({
                        "puzzle": entry.problem_number,
                        "level": level,
                        "error": result.error,
                    })
                continue
            if result.sgf:
                built += 1
                if result.correct_move_count > 0:
                    with_solution_tree += 1
                else:
                    setup_only += 1
                if result.validation_warnings:
                    warnings_count += 1
                    validation_issues.append({
                        "puzzle": entry.problem_number,
                        "level": level,
                        "warnings": result.validation_warnings,
                    })
                if output_dir:
                    seq += 1
                    level_tag = "e" if level == "elementary" else "m"
                    out_name = f"harada_{entry.problem_number:04d}_{level_tag}_{seq:03d}.sgf"
                    out_path = output_dir / out_name
                    out_path.write_text(result.sgf, encoding="utf-8")

    # --- Aggregate warning types ---
    from collections import Counter
    warning_types: Counter[str] = Counter()
    for issue in validation_issues:
        for w in issue["warnings"]:
            # Normalize indexed warnings (e.g. EMPTY_WRONG_BRANCH_0 -> EMPTY_WRONG_BRANCH)
            base = w.rsplit("_", 1)[0] if w[-1].isdigit() else w
            warning_types[base] += 1

    # --- Write build-status.json ---
    import datetime
    status_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": {
            "total_puzzles_in_catalog": len(catalog.puzzles),
            "puzzles_with_images": sum(1 for p in catalog.puzzles if p.downloaded_count() > 0),
            "sgfs_built": built,
            "with_solution_tree": with_solution_tree,
            "setup_only": setup_only,
            "gated_critical": gated,
            "errors": errors,
            "validation_warnings": warnings_count,
        },
        "warning_summary": dict(warning_types.most_common()),
        "error_details": error_details,
        "gated_details": gated_details,
        "validation_details": validation_issues,
    }
    status_path = config.working_dir() / "build-status.json"
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)

    print(f"Built {built} SGFs ({with_solution_tree} with moves, {setup_only} setup-only)")
    if gated:
        print(f"Gated (critical validation): {gated}")
    if errors:
        print(f"Build errors: {errors}")
    if warnings_count:
        print(f"Validation warnings: {warnings_count} SGFs")
        for wtype, count in warning_types.most_common():
            print(f"  {wtype}: {count}")
    print(f"Status -> {status_path}")
    if output_dir:
        print(f"Output -> {output_dir}")
    return 0


def _cmd_eval(config: object, args: argparse.Namespace) -> int:
    """Handle the 'eval' subcommand — evaluate digit detection accuracy."""
    from tools.minoru_harada_tsumego.eval_digit_detection import (
        run_eval,
        log_run,
        show_comparison,
        show_detail,
    )

    working_dir = config.working_dir()
    gt_path = working_dir / "ground_truth.json"
    results_path = working_dir / "eval_results.json"

    if args.compare:
        show_comparison(results_path)
        return 0

    if not gt_path.exists():
        print(f"Ground truth not found: {gt_path}", file=sys.stderr)
        return 1

    # --- Cross-validation mode ---
    if args.cv:
        from tools.minoru_harada_tsumego.eval_digit_detection import (
            run_eval_cv,
            show_cv_detail,
        )
        print("Running leave-one-image-out cross-validation...")
        cv_result = run_eval_cv(gt_path, working_dir)
        show_cv_detail(cv_result)
        return 0

    # --- Holdout-only mode ---
    if args.holdout:
        import json as _json
        with open(gt_path, encoding="utf-8") as f:
            gt_data = _json.load(f)
        holdout_ids = {
            img["id"] for img in gt_data["images"]
            if img.get("group") == "holdout"
        }
        if not holdout_ids:
            print("No holdout images found in ground truth.", file=sys.stderr)
            return 1
        print(f"Running holdout evaluation ({len(holdout_ids)} images)...")
        result = run_eval(gt_path, working_dir, image_filter=holdout_ids)
        show_detail(result, label="Holdout")
        return 0

    # --- Standard resubstitution eval ---
    print("Running digit detection evaluation...")
    result = run_eval(gt_path, working_dir)
    show_detail(result)

    if not args.no_save:
        run_id = log_run(result, results_path, run_id=args.run_id)
        print(f"\nSaved as: {run_id}")
        print(f"Results -> {results_path}")

    return 0


def _cmd_reparse(config: object) -> int:
    """Re-extract answer text from cached HTML pages using the current parser.

    This allows fixing comment text without re-downloading pages.
    Reads each puzzle's cached answer page, re-runs parse_answer_page(),
    and updates the catalog with cleaned text.
    """
    import hashlib
    from tools.minoru_harada_tsumego.models import Catalog
    from tools.minoru_harada_tsumego.parsers import parse_answer_page
    from tools.core.atomic_write import atomic_write_json

    catalog_path = config.catalog_path()
    if not catalog_path.exists():
        print("No catalog found.", file=sys.stderr)
        return 1

    with open(catalog_path, encoding="utf-8") as f:
        catalog = Catalog.from_dict(json.load(f))

    cache_dir = config.page_cache_dir()
    updated = 0
    skipped = 0

    for puzzle in catalog.puzzles:
        if not puzzle.answer_page_cached or not puzzle.answer_page_url:
            skipped += 1
            continue

        # Reconstruct the wayback URL used during download to find the cache file
        ts = puzzle.answer_wayback_ts or config.index_wayback_timestamp
        wayback_url = f"https://web.archive.org/web/{ts}if_/{puzzle.answer_page_url}"
        cache_key = hashlib.sha256(wayback_url.encode()).hexdigest()[:16] + ".html"
        cache_file = cache_dir / cache_key

        if not cache_file.exists():
            skipped += 1
            continue

        html = cache_file.read_text(encoding="utf-8")
        if "404 NOT FOUND" in html:
            skipped += 1
            continue

        _, texts = parse_answer_page(html, puzzle.problem_number)

        old_elem = puzzle.elementary_answer_text
        old_inter = puzzle.intermediate_answer_text
        puzzle.elementary_answer_text = texts.get("elementary_answer", "")
        puzzle.intermediate_answer_text = texts.get("intermediate_answer", "")

        if puzzle.elementary_answer_text != old_elem or puzzle.intermediate_answer_text != old_inter:
            updated += 1

    catalog.update_stats()
    atomic_write_json(catalog_path, catalog.to_dict())

    print(f"Reparsed {len(catalog.puzzles)} puzzles: {updated} updated, {skipped} skipped")
    return 0


def _batch_recognize(config: object, output_dir: Path | None, limit: int) -> int:
    """Process all downloaded images from the catalog."""
    from tools.minoru_harada_tsumego.models import Catalog
    from tools.core.image_to_board import (
        format_position,
        recognize_position,
    )
    from tools.minoru_harada_tsumego.sgf_converter import position_to_sgf

    catalog_path = config.catalog_path()
    if not catalog_path.exists():
        print("No catalog found. Run 'discover' and 'download' first.", file=sys.stderr)
        return 1

    with open(catalog_path, encoding="utf-8") as f:
        catalog = Catalog.from_dict(json.load(f))

    image_dir = config.working_dir()
    processed = 0
    sgf_count = 0

    for puzzle in catalog.puzzles:
        if limit and processed >= limit:
            break
        for img_info in puzzle.images:
            if not img_info.downloaded:
                continue
            if img_info.image_type not in ("problem",):
                continue

            fpath = image_dir / img_info.local_path
            if not fpath.exists():
                continue

            pos = recognize_position(fpath)
            print(format_position(pos))
            print()

            if output_dir:
                level_tag = "e" if img_info.level == "elementary" else "m"
                sgf = position_to_sgf(
                    pos,
                    comment=f"Harada #{puzzle.problem_number} ({img_info.level})",
                )
                out_name = f"harada_{puzzle.problem_number:04d}_{level_tag}.sgf"
                out_path = output_dir / out_name
                out_path.write_text(sgf, encoding="utf-8")
                sgf_count += 1

            processed += 1
            if limit and processed >= limit:
                break

    print(f"Processed {processed} images")
    if sgf_count:
        print(f"Generated {sgf_count} SGF files in {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
