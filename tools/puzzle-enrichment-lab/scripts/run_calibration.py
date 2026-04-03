#!/usr/bin/env python3
"""Sequential single-puzzle calibration runner.

Enriches puzzles ONE AT A TIME (not batch), measuring individual timings.
This mirrors production behavior where the pipeline processes one puzzle
per invocation, not a batch of 10,000 simultaneously.

Config-driven: reads fixture_dirs, sample_size, seed, restart_every_n from
config/katago-enrichment.json ``calibration`` section. CLI args override.

Usage:
    # Config-driven (reads fixture_dirs from config, samples per config):
    python scripts/run_calibration.py --run-label "v1.27"

    # Override input directory (processes ALL SGFs in dir, ignores fixture_dirs):
    python scripts/run_calibration.py \\
        --input-dir tests/fixtures/calibration/cho-elementary \\
        --run-label "cycle-1"

    # Override sample size and seed:
    python scripts/run_calibration.py --sample-size 10 --seed 99

The output directory will contain:
    *.json          — Per-puzzle enrichment result
    *.sgf           — Enriched SGF
    _summary.json   — Aggregate timing + accuracy statistics
    _report.txt     — Human-readable ASCII report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

from analyzers.enrich_single import enrich_single_puzzle
from analyzers.sgf_enricher import enrich_sgf
from analyzers.single_engine import SingleEngineManager, resolve_katago_config
from config import EnrichmentConfig, load_enrichment_config
from log_config import bootstrap
from models.ai_analysis_result import generate_run_id

logger = logging.getLogger(__name__)

# Default paths relative to lab dir
_KATAGO_PATH = _LAB_DIR / "katago" / "katago.exe"
_KATAGO_CONFIG = _LAB_DIR / "katago" / "tsumego_analysis.cfg"
_FIXTURES_DIR = _LAB_DIR / "tests" / "fixtures" / "calibration"


def _resolve_model_paths() -> tuple[Path, Path]:
    """Lazily resolve model paths from config (D42 indirection)."""
    cfg = load_enrichment_config()
    if cfg.models is None:
        raise RuntimeError(
            "models section missing from config/katago-enrichment.json. "
            "Model name indirection is required (Plan 010, D42)."
        )
    quick = _LAB_DIR / "models-data" / cfg.models.quick.filename
    referee = _LAB_DIR / "models-data" / cfg.models.referee.filename
    return quick, referee


def _sample_sgfs(collection_dir: Path, n: int, seed: int) -> list[Path]:
    """Sample n SGF files from a collection directory, reproducibly.

    Same logic as test_calibration._sample_sgfs — sorted glob, seeded RNG sample.
    If n >= total files, returns all.
    """
    all_sgfs = sorted(collection_dir.glob("*.sgf"))
    if len(all_sgfs) <= n:
        return all_sgfs
    rng = random.Random(seed)
    return sorted(rng.sample(all_sgfs, n))


def _resolve_fixture_sgfs(config: EnrichmentConfig) -> list[Path]:
    """Resolve SGF files from config fixture_dirs + sample_size + seed.

    Reads calibration.fixture_dirs, calibration.sample_size, calibration.seed,
    and calibration.randomize_fixtures from config. Returns a flat list of
    sampled SGF paths across all fixture directories.
    """
    cal = config.calibration
    if not cal:
        return []

    fixture_dirs = cal.fixture_dirs
    sample_size = cal.sample_size

    # Determine seed: random mode (default) vs deterministic
    if cal.randomize_fixtures:
        seed = int(secrets.token_hex(4), 16)
        logger.info("Calibration seed: %d (randomized)", seed)
    else:
        seed = cal.seed if cal.seed is not None else 42
        logger.info("Calibration seed: %d (deterministic)", seed)

    sgf_files: list[Path] = []
    for dirname in fixture_dirs:
        fixture_dir = _FIXTURES_DIR / dirname
        if not fixture_dir.exists():
            logger.warning("Fixture directory not found: %s", fixture_dir)
            continue
        sampled = _sample_sgfs(fixture_dir, sample_size, seed)
        logger.info(
            "Sampled %d/%d SGFs from %s (seed=%d)",
            len(sampled), len(list(fixture_dir.glob("*.sgf"))), dirname, seed,
        )
        sgf_files.extend(sampled)

    return sgf_files


def _extract_model_label(model_path: str) -> str:
    """Extract a short architecture label from a KataGo model filename.

    Examples:
        'kata1-b18c384nbt-s9996604416-d4316597426.bin.gz' -> 'b18c384'
        'kata1-b28c512nbt-s12192929536-d5655876072.bin.gz' -> 'b28c512'
        ''  -> ''
    """
    if not model_path:
        return ""
    filename = Path(model_path).stem  # strips .gz
    filename = Path(filename).stem     # strips .bin
    parts = filename.split("-")
    if len(parts) >= 2:
        arch = parts[1]
        # Strip 'nbt' suffix if present (e.g. 'b18c384nbt' -> 'b18c384')
        if arch.endswith("nbt"):
            arch = arch[:-3]
        return arch
    return Path(model_path).name


async def _enrich_one_puzzle(
    sgf_file: Path,
    output_dir: Path,
    engine_manager: SingleEngineManager,
    config: EnrichmentConfig,
    run_id: str,
) -> dict:
    """Enrich a single puzzle using a shared, already-started engine manager.

    Returns a dict with timing and result metadata.
    """
    puzzle_result = {
        "file": sgf_file.name,
        "puzzle_id": "",
        "status": "error",
        "level": "",
        "level_id": 0,
        "refutation_count": 0,
        "flags": [],
        "engine_used": "",
        "time_enrich_s": 0.0,
        "phase_timings": {},
        "retry": False,
        "first_pass_status": "",
    }

    try:
        # Read and enrich
        sgf_text = sgf_file.read_text(encoding="utf-8")
        enrich_start = time.monotonic()
        result = await enrich_single_puzzle(
            sgf_text,
            engine_manager,
            config,
            source_file=sgf_file.name,
            run_id=run_id,
        )
        puzzle_result["time_enrich_s"] = round(time.monotonic() - enrich_start, 3)

        # Write JSON result
        json_out = output_dir / f"{sgf_file.stem}.json"
        json_out.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # Write enriched SGF
        enriched_sgf = enrich_sgf(sgf_text, result)
        sgf_out = output_dir / sgf_file.name
        sgf_out.write_text(enriched_sgf, encoding="utf-8")

        # Capture metrics
        puzzle_result["puzzle_id"] = result.puzzle_id
        puzzle_result["status"] = result.validation.status.value
        puzzle_result["level"] = result.difficulty.suggested_level
        puzzle_result["level_id"] = result.difficulty.suggested_level_id
        puzzle_result["refutation_count"] = len(result.refutations)
        puzzle_result["flags"] = result.validation.flags
        puzzle_result["engine_used"] = result.engine.model
        puzzle_result["phase_timings"] = result.phase_timings
        # Diagnostic fields for calibration analysis
        puzzle_result["raw_score"] = round(result.difficulty.composite_score, 2)
        puzzle_result["policy_prior"] = round(result.difficulty.policy_prior_correct, 4)
        puzzle_result["katago_agrees"] = result.validation.katago_agrees
        puzzle_result["solution_depth"] = result.difficulty.visits_to_solve

    except Exception as e:
        logger.error("Failed to enrich %s: %s", sgf_file.name, e)
        puzzle_result["flags"] = [f"error: {e}"]

    return puzzle_result


def _generate_ascii_report(
    results: list[dict],
    collection_name: str,
    run_label: str,
    run_id: str,
    total_elapsed: float,
) -> str:
    """Generate human-readable ASCII report for expert review.

    Format designed for Cho Chikun expert review: shows each puzzle's
    enrichment result in a compact table format.
    """
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"  ENRICHMENT CALIBRATION REPORT — {collection_name.upper()}")
    lines.append(f"  Run: {run_label} | ID: {run_id}")
    lines.append(f"  Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 80)
    lines.append("")

    # Summary stats
    total = len(results)
    accepted = sum(1 for r in results if r["status"] == "accepted")
    flagged = sum(1 for r in results if r["status"] == "flagged")
    rejected = sum(1 for r in results if r["status"] == "rejected")
    errors = sum(1 for r in results if r["status"] == "error")
    with_refutations = sum(1 for r in results if r["refutation_count"] > 0)

    acc_rate = accepted / total * 100 if total else 0
    ref_rate = with_refutations / total * 100 if total else 0

    levels = [r["level_id"] for r in results if r["level_id"] > 0]
    avg_level = sum(levels) / len(levels) if levels else 0
    level_slugs = [r["level"] for r in results if r["level"]]
    level_dist = {}
    for slug in level_slugs:
        level_dist[slug] = level_dist.get(slug, 0) + 1

    lines.append("  SUMMARY")
    lines.append("  " + "-" * 40)
    lines.append(f"  Total puzzles:      {total}")
    lines.append(f"  Accepted:           {accepted}/{total} ({acc_rate:.1f}%)")
    lines.append(f"  Flagged:            {flagged}")
    lines.append(f"  Rejected:           {rejected}")
    lines.append(f"  Errors:             {errors}")
    lines.append(f"  With refutations:   {with_refutations}/{total} ({ref_rate:.1f}%)")
    lines.append(f"  Avg level ID:       {avg_level:.0f}")
    lines.append(f"  Total time:         {total_elapsed:.1f}s")
    avg_time = total_elapsed / total if total else 0
    lines.append(f"  Avg per puzzle:     {avg_time:.1f}s")

    # Retry stats
    retried = [r for r in results if r.get("retry")]
    if retried:
        retry_accepted = sum(1 for r in retried if r["status"] == "accepted")
        lines.append("")
        lines.append("  RETRY RESULTS")
        lines.append("  " + "-" * 40)
        lines.append(f"  Retried:            {len(retried)}")
        lines.append(f"  Recovered:          {retry_accepted}/{len(retried)}")
        for r in retried:
            outcome = "RECOVERED" if r["status"] == "accepted" else r["status"]
            lines.append(f"    {r['file']:<30s} {r['first_pass_status']} -> {outcome}")

    lines.append("")

    # Level distribution
    lines.append("  DIFFICULTY DISTRIBUTION")
    lines.append("  " + "-" * 40)
    for slug in ["novice", "beginner", "elementary", "intermediate",
                 "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"]:
        count = level_dist.get(slug, 0)
        bar = "#" * count
        if count > 0:
            lines.append(f"  {slug:>20s}: {count:3d} {bar}")
    lines.append("")

    # Per-puzzle detail table
    lines.append("  PER-PUZZLE RESULTS")
    lines.append("  " + "-" * 90)
    header = f"  {'#':>3s} {'File':<30s} {'Status':<10s} {'Level':<18s} {'Score':>5s} {'Policy':>6s} {'Refs':>4s} {'Time':>6s} {'Flags'}"
    lines.append(header)
    lines.append("  " + "-" * 90)

    for i, r in enumerate(results, 1):
        flags_str = ", ".join(r["flags"][:2]) if r["flags"] else ""
        raw_score = r.get("raw_score", 0.0)
        policy = r.get("policy_prior", 0.0)
        retry_marker = " [R]" if r.get("retry") else ""
        line = (
            f"  {i:3d} {r['file']:<30s} {r['status']:<10s} "
            f"{r['level']:<18s} {raw_score:5.1f} {policy:6.4f} {r['refutation_count']:4d} "
            f"{r['time_enrich_s']:5.1f}s {flags_str}{retry_marker}"
        )
        lines.append(line)

    lines.append("")
    lines.append("  " + "=" * 76)

    # Timing breakdown
    lines.append("")
    lines.append("  TIMING BREAKDOWN")
    lines.append("  " + "-" * 40)
    total_enrich = sum(r["time_enrich_s"] for r in results)
    lines.append(f"  Enrichment (sum):    {total_enrich:.1f}s")
    lines.append(f"  Wall clock:          {total_elapsed:.1f}s")
    lines.append("")

    return "\n".join(lines)


async def _run_all_puzzles(
    sgf_files: list[Path],
    output_path: Path,
    config: EnrichmentConfig,
    katago: str,
    quick: str,
    referee: str,
    kconfig: str,
    run_id: str,
    *,
    retry_rejected: bool = True,
    retry_skip_refutation_threshold: int = 4,
    mode_override: str | None = None,
    restart_every_n: int = 0,
) -> list[dict]:
    """Start engines, enrich all puzzles sequentially, then shut down.

    Args:
        restart_every_n: Restart engine every N puzzles (0=never).
            Mitigates iGPU OpenCL driver crashes (0xC0000005) by
            giving the GPU a fresh context periodically.
    """

    model_path = str((_LAB_DIR / "models-data" / config.models.deep_enrich.filename).resolve())

    def _create_engine() -> SingleEngineManager:
        return SingleEngineManager(
            config,
            katago_path=katago,
            model_path=model_path,
            katago_config_path=kconfig,
            mode_override=mode_override,
        )

    engine_manager = _create_engine()

    results: list[dict] = []
    puzzles_since_restart = 0
    try:
        await engine_manager.start()

        quick_label = _extract_model_label(quick)
        print(f"\n  FIRST PASS ({quick_label or 'quick'})")
        if restart_every_n > 0:
            print(f"  Engine restart every {restart_every_n} puzzles (crash mitigation)")
        print(f"  {'-' * 50}")

        for i, sgf_file in enumerate(sgf_files, 1):
            # Engine restart check (before puzzle, not after — avoids
            # unnecessary restart after the last puzzle)
            if restart_every_n > 0 and puzzles_since_restart >= restart_every_n:
                logger.info("Restarting engine after %d puzzles", puzzles_since_restart)
                print(f"  [ENGINE RESTART after {puzzles_since_restart} puzzles] ... ", end="", flush=True)
                restart_start = time.monotonic()
                await engine_manager.shutdown()
                engine_manager = _create_engine()
                await engine_manager.start()
                restart_elapsed = time.monotonic() - restart_start
                puzzles_since_restart = 0
                print(f"ready ({restart_elapsed:.1f}s)")

            print(f"  [{i:3d}/{len(sgf_files)}] {sgf_file.name} ... ", end="", flush=True)

            result = await _enrich_one_puzzle(
                sgf_file=sgf_file,
                output_dir=output_path,
                engine_manager=engine_manager,
                config=config,
                run_id=run_id,
            )
            results.append(result)
            puzzles_since_restart += 1

            status = result["status"]
            refs = result["refutation_count"]
            t = result["time_enrich_s"]
            lvl = result["level"]
            rs = result.get("raw_score", 0.0)
            pp = result.get("policy_prior", 0.0)
            print(f"{status:<10s} {lvl:<18s} score={rs:5.1f} policy={pp:.4f} refs={refs} ({t:.1f}s)")

    finally:
        await engine_manager.shutdown()
    if retry_rejected and referee:
        logger.info("Retry pass disabled in single-engine mode; escalation is config-driven within one engine")
    return results


def run_calibration(
    sgf_files: list[Path],
    output_dir: str,
    run_label: str = "",
    collection_name: str = "",
    katago_path: str = "",
    quick_model: str = "",
    referee_model: str = "",
    katago_config: str = "",
    quick_only: bool = False,
    retry_rejected: bool = True,
    retry_skip_refutation_threshold: int = 4,
    restart_every_n: int = 0,
    run_id: str = "",
) -> int:
    """Run sequential single-puzzle calibration.

    Args:
        sgf_files: Pre-resolved list of SGF files to enrich.
        output_dir: Directory to write results.
        collection_name: Label for the collection (used in reports).
        quick_only: If True, only start quick engine.
        restart_every_n: Restart engine every N puzzles (0=never).
        run_id: Pipeline run identifier. Generated if not provided.

    Returns exit code: 0 if all accepted, 1 if any failed.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    katago = katago_path or str(_KATAGO_PATH)
    _quick_model_path, _referee_model_path = _resolve_model_paths()
    quick = quick_model or str(_quick_model_path)
    referee = "" if quick_only else (referee_model or str(_referee_model_path))
    kconfig = resolve_katago_config(katago_config, katago)

    if not collection_name:
        collection_name = "calibration"
    if not run_id:
        run_id = generate_run_id()
    if not run_label:
        run_label = run_id

    if not sgf_files:
        print("No SGF files to process")
        return 1

    # Derive mode label from model filenames instead of hardcoding
    quick_label = _extract_model_label(quick)
    referee_label = _extract_model_label(referee)
    if quick_only:
        mode_label = f"quick-only ({quick_label})"
    else:
        mode_label = f"dual ({quick_label}+{referee_label})"

    retry_label = ""
    if retry_rejected and referee:
        retry_label = f" | retry=on (skip >= {retry_skip_refutation_threshold} refs)"
    elif not retry_rejected:
        retry_label = " | retry=off"

    restart_label = f" | restart every {restart_every_n}" if restart_every_n > 0 else ""

    print(f"\n{'=' * 60}")
    print(f"  Calibration: {collection_name}")
    print(f"  Run: {run_label} | {len(sgf_files)} puzzles")
    print(f"  Mode: {mode_label}{retry_label}{restart_label}")
    print(f"  Quick model: {Path(quick).name}")
    if referee:
        print(f"  Referee model: {Path(referee).name}")
    print(f"{'=' * 60}")

    config = load_enrichment_config()
    wall_start = time.monotonic()

    # A2 fix: Pass explicit mode_override so deep_enrich doesn't silently
    # override --quick-only intent.
    calibration_mode: str | None = None
    if quick_only:
        calibration_mode = "quick_only"

    results = asyncio.run(
        _run_all_puzzles(
            sgf_files=sgf_files,
            output_path=output_path,
            config=config,
            katago=katago,
            quick=quick,
            referee=referee,
            kconfig=kconfig,
            run_id=run_id,
            retry_rejected=retry_rejected and bool(referee),
            retry_skip_refutation_threshold=retry_skip_refutation_threshold,
            mode_override=calibration_mode,
            restart_every_n=restart_every_n,
        )
    )

    total_elapsed = time.monotonic() - wall_start

    # Write summary JSON
    retried = [r for r in results if r.get("retry")]
    retry_accepted = sum(1 for r in retried if r["status"] == "accepted")

    summary = {
        "run_id": run_id,
        "run_label": run_label,
        "collection": collection_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "config_version": load_enrichment_config().version,
        "quick_model": Path(quick).name,
        "quick_label": quick_label,
        "referee_model": Path(referee).name if referee else "",
        "referee_label": referee_label,
        "mode": mode_label,
        "mode_override": calibration_mode,
        "retry_rejected": retry_rejected and bool(referee),
        "retry_skip_refutation_threshold": retry_skip_refutation_threshold,
        "total_puzzles": len(results),
        "accepted": sum(1 for r in results if r["status"] == "accepted"),
        "flagged": sum(1 for r in results if r["status"] == "flagged"),
        "rejected": sum(1 for r in results if r["status"] == "rejected"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "with_refutations": sum(1 for r in results if r["refutation_count"] > 0),
        "retry_count": len(retried),
        "retry_accepted": retry_accepted,
        "total_elapsed_s": round(total_elapsed, 2),
        "avg_per_puzzle_s": round(total_elapsed / len(results), 2) if results else 0,
        "puzzles": results,
    }

    summary_path = output_path / "_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write ASCII report
    report = _generate_ascii_report(
        results, collection_name, run_label, run_id, total_elapsed
    )
    report_path = output_path / "_report.txt"
    report_path.write_text(report, encoding="utf-8")

    print(f"\n{report}")
    print(f"  Summary: {summary_path}")
    print(f"  Report:  {report_path}")

    # Return 0 only if all accepted
    if summary["errors"] + summary["rejected"] > 0:
        return 1
    return 0


def main():
    """Standalone entry point (thin wrapper).

    Preferred invocation is ``python cli.py calibrate ...`` which uses
    the centralized bootstrap and argument parsing.  This entry point
    remains for backward compatibility with existing scripts.
    """
    parser = argparse.ArgumentParser(
        description="Sequential single-puzzle calibration runner. "
        "Reads fixture_dirs, sample_size, seed from config/katago-enrichment.json "
        "calibration section. CLI args override config values."
    )
    parser.add_argument(
        "--input-dir", default=None,
        help="Directory with SGF files (overrides config fixture_dirs). "
        "If not given, uses fixture_dirs + sample_size + seed from config.",
    )
    parser.add_argument("--output-dir", default=None, help="Output directory for results (default: from config paths.calibration_results_dir)")
    parser.add_argument("--run-label", default="", help="Label for this calibration run")
    parser.add_argument("--sample-size", type=int, default=None,
                        help="Puzzles per collection (overrides config calibration.sample_size)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for sampling (overrides config; implies deterministic mode)")
    parser.add_argument("--katago", default="", help="Path to KataGo binary")
    parser.add_argument("--quick-model", default="", help="Path to quick model")
    parser.add_argument("--referee-model", default="", help="Path to referee model")
    parser.add_argument("--katago-config", default="", help="Path to KataGo config")
    parser.add_argument("--quick-only", action="store_true",
                        help="Use only quick engine. Much faster for calibration.")
    parser.add_argument("--retry-rejected", action="store_true", default=True,
                        help="Retry rejected/flagged puzzles with referee engine (default: on)")
    parser.add_argument("--no-retry-rejected", action="store_false", dest="retry_rejected",
                        help="Disable retry of rejected/flagged puzzles")
    parser.add_argument("--retry-skip-refutations", type=int, default=4,
                        help="Skip retry if puzzle has >= N refutations (default: 4)")
    parser.add_argument("--restart-every-n", type=int, default=None,
                        help="Restart engine every N puzzles (overrides config; 0=never)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of puzzles (0 = all)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging")

    args = parser.parse_args()

    # Centralised bootstrap: generate run_id, configure logging, set context.
    run_id = bootstrap(verbose=args.verbose, console_format="human")

    # Load config for defaults
    config = load_enrichment_config()

    # Q10: Resolve default output dir from config if not specified
    if not args.output_dir:
        try:
            from config import resolve_path
            args.output_dir = str(resolve_path(config, "calibration_results_dir"))
        except Exception:
            args.output_dir = str(_LAB_DIR / ".lab-runtime" / "calibration-results")

    # Resolve restart_every_n: CLI > config > 0
    restart_every_n = args.restart_every_n
    if restart_every_n is None:
        restart_every_n = config.calibration.restart_every_n if config.calibration else 0

    # Resolve SGF file list
    if args.input_dir:
        # Explicit --input-dir: process all SGFs in that directory (original behavior)
        input_path = Path(args.input_dir)
        sgf_files = sorted(input_path.glob("*.sgf"))
        collection_name = input_path.name

        # Apply --limit if specified
        if args.limit > 0 and len(sgf_files) > args.limit:
            sgf_files = sgf_files[:args.limit]
    else:
        # Config-driven: read fixture_dirs + sample_size + seed from config
        cal = config.calibration
        if not cal:
            print("No calibration config and no --input-dir specified")
            sys.exit(1)

        # CLI overrides for sample_size and seed
        if args.sample_size is not None:
            cal.sample_size = args.sample_size
        if args.seed is not None:
            # Explicit --seed implies deterministic mode
            cal.seed = args.seed
            cal.randomize_fixtures = False

        sgf_files = _resolve_fixture_sgfs(config)
        collection_name = "+".join(cal.fixture_dirs)

        # Apply --limit if specified
        if args.limit > 0 and len(sgf_files) > args.limit:
            sgf_files = sgf_files[:args.limit]

    sys.exit(run_calibration(
        sgf_files=sgf_files,
        output_dir=args.output_dir,
        run_label=args.run_label,
        collection_name=collection_name,
        katago_path=args.katago,
        quick_model=args.quick_model,
        referee_model=args.referee_model,
        katago_config=args.katago_config,
        quick_only=args.quick_only,
        retry_rejected=args.retry_rejected,
        retry_skip_refutation_threshold=args.retry_skip_refutations,
        restart_every_n=restart_every_n,
        run_id=run_id,
    ))


if __name__ == "__main__":
    main()
