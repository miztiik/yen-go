"""Task A.5.3: CLI entry point for the KataGo enrichment lab.

Provides an argparse-based CLI with subcommands:
  - enrich: Run full enrichment pipeline on a single SGF
    - --gui flag launches the visual enrichment lab GUI alongside enrichment
  - apply:  Apply enrichment results (JSON) to an SGF file
  - validate: Validate a puzzle's correct move (enrichment without SGF write)
  - batch:  Run enrichment + apply on all SGFs in a directory

Exit codes:
  0 = ACCEPTED (puzzle validated successfully)
  1 = ERROR or REJECTED (pipeline failure or invalid puzzle)
  2 = FLAGGED (puzzle needs human review)

Invocation:
  python tools/puzzle-enrichment-lab/cli.py enrich --sgf puzzle.sgf --output result.json --katago /path/to/katago
  python tools/puzzle-enrichment-lab/cli.py enrich --sgf puzzle.sgf --katago /path/to/katago --gui
  python tools/puzzle-enrichment-lab/cli.py enrich --sgf puzzle.sgf --output result.json --katago /path/to/katago --gui
  python tools/puzzle-enrichment-lab/cli.py apply --sgf puzzle.sgf --result result.json --output enriched.sgf
  python tools/puzzle-enrichment-lab/cli.py validate --sgf puzzle.sgf --katago /path/to/katago
  python tools/puzzle-enrichment-lab/cli.py batch --input-dir sgf_dir/ --output-dir output_dir/ --katago /path/to/katago
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

try:
    from analyzers.enrich_single import build_diagnostic_from_result, enrich_single_puzzle
    from analyzers.observability import BatchSummaryAccumulator, DisagreementSink
    from analyzers.result_builders import compute_config_hash
    from analyzers.sgf_enricher import enrich_sgf
    from analyzers.single_engine import SingleEngineManager, resolve_katago_config
    from config import load_enrichment_config
    from log_config import bootstrap, set_run_id
    from models.ai_analysis_result import AiAnalysisResult, generate_run_id
    from models.validation import ValidationStatus
except ImportError:
    from .analyzers.enrich_single import build_diagnostic_from_result, enrich_single_puzzle
    from .analyzers.observability import BatchSummaryAccumulator, DisagreementSink
    from .analyzers.result_builders import compute_config_hash
    from .analyzers.sgf_enricher import enrich_sgf
    from .analyzers.single_engine import SingleEngineManager, resolve_katago_config
    from .config import load_enrichment_config
    from .log_config import bootstrap, set_run_id
    from .models.ai_analysis_result import AiAnalysisResult, generate_run_id
    from .models.validation import ValidationStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_ACCEPTED = 0
EXIT_ERROR = 1
EXIT_FLAGGED = 2


def _status_to_exit_code(status: ValidationStatus) -> int:
    """Map ValidationStatus to CLI exit code."""
    if status == ValidationStatus.ACCEPTED:
        return EXIT_ACCEPTED
    elif status == ValidationStatus.FLAGGED:
        return EXIT_FLAGGED
    else:
        return EXIT_ERROR


def _emit_config_dump(config, run_id: str) -> None:
    """Emit full config as a structured log event once per run."""
    config_hash = compute_config_hash(config)
    logger.info(
        "config_dump",
        extra={
            "run_id": run_id,
            "config_hash": config_hash,
            "config": config.model_dump(mode="json", exclude_none=True),
        },
    )


# ---------------------------------------------------------------------------
# Subcommand: enrich
# ---------------------------------------------------------------------------

def _apply_cli_overrides(config, visits: int | None, symmetries: int | None) -> None:
    """Apply CLI visit/symmetry overrides to a loaded EnrichmentConfig in-place.

    Patches both deep_enrich and analysis_defaults so all code paths see the
    same visit count regardless of how they read the config.

    Args:
        config: EnrichmentConfig loaded by load_enrichment_config().
        visits: Override MCTS visit count, or None to keep config value.
        symmetries: Override root symmetries count, or None to keep config value.
    """
    if visits is not None:
        config.deep_enrich.visits = visits
        config.analysis_defaults.default_max_visits = visits
        logger.info("CLI override: visits=%d", visits)
    if symmetries is not None:
        config.deep_enrich.root_num_symmetries_to_sample = symmetries
        logger.info("CLI override: symmetries=%d", symmetries)


def _resolve_model_path(config) -> str:
    if config.models is None:
        raise RuntimeError(
            "models section missing from config/katago-enrichment.json. "
            "Model indirection is required."
        )
    return str((Path(__file__).resolve().parent / "models-data" / config.models.deep_enrich.filename).resolve())


def run_enrich(
    sgf_path: str,
    output_path: str,
    katago_path: str,
    quick_model_path: str = "",
    referee_model_path: str = "",
    config_path: str | None = None,
    katago_config_path: str = "",
    quick_only: bool = False,
    visits: int | None = None,
    symmetries: int | None = None,
    emit_sgf_path: str | None = None,
    run_id: str = "",
    debug_export: bool = False,
) -> int:
    """Run full enrichment pipeline on a single SGF file.

    Args:
        sgf_path: Path to input SGF file.
        output_path: Path to write JSON result.
        katago_path: Path to KataGo binary.
        config_path: Path to custom config JSON (optional).
        katago_config_path: Path to KataGo analysis config (auto-detected if empty).
        quick_only: Force quick_only mode (500 visits, 2 symmetries) regardless of deep_enrich.
        visits: Override MCTS visit count (overrides config deep_enrich.visits in config).
        symmetries: Override root symmetries (overrides config deep_enrich.root_num_symmetries_to_sample).

    Returns:
        Exit code: 0=accepted, 1=error, 2=flagged.
    """
    sgf_file = Path(sgf_path)
    if not sgf_file.exists():
        logger.error("SGF file not found: %s", sgf_path)
        return EXIT_ERROR

    sgf_text = sgf_file.read_text(encoding="utf-8")

    # Load config then apply any CLI overrides
    config = load_enrichment_config(
        Path(config_path) if config_path else None
    )
    _apply_cli_overrides(config, visits, symmetries)

    resolved_katago_config = resolve_katago_config(katago_config_path, katago_path)

    model_path = _resolve_model_path(config)

    engine_manager = SingleEngineManager(
        config,
        katago_path=katago_path,
        model_path=model_path,
        katago_config_path=resolved_katago_config,
        mode_override="quick_only" if quick_only else None,
    )

    start_time = time.monotonic()

    try:
        result = asyncio.run(_run_enrich_async(sgf_text, engine_manager, config, source_file=sgf_file.name, run_id=run_id))
    except Exception as e:
        logger.error("Enrichment failed: %s", e)
        return EXIT_ERROR

    elapsed = time.monotonic() - start_time
    logger.info(
        "Enrichment completed in %.2fs: status=%s, puzzle_id=%s",
        elapsed,
        result.validation.status.value if hasattr(result.validation.status, 'value') else result.validation.status,
        result.puzzle_id,
    )

    # Write result JSON (skipped when --gui is used without --output)
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    # Optional single-step SGF emission
    if emit_sgf_path:
        enriched_sgf = enrich_sgf(sgf_text, result)
        emit_path = Path(emit_sgf_path)
        emit_path.parent.mkdir(parents=True, exist_ok=True)
        emit_path.write_text(enriched_sgf, encoding="utf-8")
        logger.info("Wrote enriched SGF: %s", emit_path)

    # Debug artifact export (T41)
    if debug_export:
        try:
            from analyzers.debug_export import export_debug_artifact
            export_debug_artifact(result, run_id or "unknown")
        except Exception as e:
            logger.warning("Debug export failed: %s", e)

    return _status_to_exit_code(result.validation.status)


def run_apply(
    sgf_path: str,
    result_path: str,
    output_path: str,
) -> int:
    """Apply enrichment JSON to an SGF and write enriched SGF."""
    sgf_file = Path(sgf_path)
    result_file = Path(result_path)

    if not sgf_file.exists():
        logger.error("SGF file not found: %s", sgf_path)
        return EXIT_ERROR
    if not result_file.exists():
        logger.error("Result JSON not found: %s", result_path)
        return EXIT_ERROR

    try:
        sgf_text = sgf_file.read_text(encoding="utf-8")
        result_json = json.loads(result_file.read_text(encoding="utf-8"))
        result = AiAnalysisResult.model_validate(result_json)
        enriched_sgf = enrich_sgf(sgf_text, result)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(enriched_sgf, encoding="utf-8")
        logger.info("Applied enrichment: %s -> %s", sgf_file, output_file)
        return EXIT_ACCEPTED
    except Exception as e:
        logger.error("Apply failed: %s", e)
        return EXIT_ERROR


async def _run_enrich_async(
    sgf_text: str,
    engine_manager: SingleEngineManager,
    config,
    source_file: str = "",
    run_id: str = "",
) -> AiAnalysisResult:
    """Run enrichment with engine lifecycle management."""
    # Emit full config once at run level (not per-puzzle).
    _emit_config_dump(config, run_id)
    async with engine_manager:
        return await enrich_single_puzzle(sgf_text, engine_manager, config, source_file=source_file, run_id=run_id)


# ---------------------------------------------------------------------------
# Subcommand: validate
# ---------------------------------------------------------------------------

def run_validate(
    sgf_path: str,
    katago_path: str,
    quick_model_path: str = "",
    referee_model_path: str = "",
    config_path: str | None = None,
    katago_config_path: str = "",
    quick_only: bool = False,
    visits: int | None = None,
    symmetries: int | None = None,
) -> int:
    """Validate a puzzle's correct move (enrichment without writing SGF).

    Args:
        sgf_path: Path to input SGF file.
        katago_path: Path to KataGo binary.
        config_path: Path to custom config JSON (optional).
        visits: Override MCTS visit count (overrides config deep_enrich.visits in config).
        symmetries: Override root symmetries (overrides config deep_enrich.root_num_symmetries_to_sample).

    Returns:
        Exit code: 0=accepted, 1=rejected/error, 2=flagged.
    """
    sgf_file = Path(sgf_path)
    if not sgf_file.exists():
        logger.error("SGF file not found: %s", sgf_path)
        return EXIT_ERROR

    sgf_text = sgf_file.read_text(encoding="utf-8")

    config = load_enrichment_config(
        Path(config_path) if config_path else None
    )
    _apply_cli_overrides(config, visits, symmetries)

    model_path = _resolve_model_path(config)
    engine_manager = SingleEngineManager(
        config,
        katago_path=katago_path,
        model_path=model_path,
        katago_config_path=resolve_katago_config(katago_config_path, katago_path),
        mode_override="quick_only" if quick_only else None,
    )

    try:
        result = asyncio.run(_run_enrich_async(sgf_text, engine_manager, config, source_file=sgf_file.name))
    except Exception as e:
        logger.error("Validation failed: %s", e)
        return EXIT_ERROR

    status = result.validation.status
    logger.info(
        "Validation result: status=%s, puzzle_id=%s, flags=%s",
        status.value if hasattr(status, 'value') else status,
        result.puzzle_id,
        result.validation.flags,
    )

    return _status_to_exit_code(status)


# ---------------------------------------------------------------------------
# Subcommand: batch
# ---------------------------------------------------------------------------

def run_batch(
    input_dir: str,
    output_dir: str,
    katago_path: str,
    quick_model_path: str = "",
    referee_model_path: str = "",
    config_path: str | None = None,
    katago_config_path: str = "",
    quick_only: bool = False,
    visits: int | None = None,
    symmetries: int | None = None,
    num_puzzles: int | None = None,
) -> int:
    """Run enrichment + apply on all SGFs in a directory.

    Sequential processing — no concurrency. Each puzzle is enriched
    and applied independently. Failures are logged but processing
    continues for remaining files.

    Args:
        input_dir: Directory containing .sgf files.
        output_dir: Directory to write enriched .sgf and .json files.
        katago_path: Path to KataGo binary.
        config_path: Path to custom config JSON (optional).
        visits: Override MCTS visit count (overrides config deep_enrich.visits in config).
        symmetries: Override root symmetries (overrides config deep_enrich.root_num_symmetries_to_sample).
        num_puzzles: Stop after this many puzzles (None or 0 = process all).

    Returns:
        Exit code: 0=all accepted, 1=any rejected/error, 2=any flagged (no errors).
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sgf_files = sorted(input_path.glob("*.sgf"))
    if not sgf_files:
        logger.info("No .sgf files found in %s", input_dir)
        return EXIT_ACCEPTED

    if num_puzzles:
        logger.info("--num-puzzles %d: processing first %d of %d files", num_puzzles, min(num_puzzles, len(sgf_files)), len(sgf_files))
        sgf_files = sgf_files[:num_puzzles]

    config = load_enrichment_config(
        Path(config_path) if config_path else None
    )
    _apply_cli_overrides(config, visits, symmetries)

    model_path = _resolve_model_path(config)
    engine_manager = SingleEngineManager(
        config,
        katago_path=katago_path,
        model_path=model_path,
        katago_config_path=resolve_katago_config(katago_config_path, katago_path),
        mode_override="quick_only" if quick_only else None,
    )

    return asyncio.run(
        _run_batch_async(sgf_files, output_path, engine_manager, config)
    )


async def _run_batch_async(
    sgf_files: list[Path],
    output_path: Path,
    engine_manager: SingleEngineManager,
    config,
) -> int:
    """Run batch enrichment with engine lifecycle management."""
    run_id = generate_run_id()
    set_run_id(run_id)
    _batch_start_time = time.monotonic()
    logger.info("Batch run_id: %s (%d puzzles)", run_id, len(sgf_files))

    # Emit full config once at batch start (not per-puzzle).
    _emit_config_dump(config, run_id)

    # G-04: Initialize observability components
    accumulator = BatchSummaryAccumulator(batch_id=run_id)
    obs_config = getattr(config, "ai_solve", None)
    sink_path = None
    if obs_config and hasattr(obs_config, "observability"):
        sink_path = obs_config.observability.disagreement_sink_path
    disagreement_sink = DisagreementSink(
        sink_dir=sink_path or ".lab-runtime/logs/disagreements",
        run_id=run_id,
    ) if sink_path or (obs_config and obs_config.enabled) else None

    async with engine_manager:
        worst_code = EXIT_ACCEPTED
        total = len(sgf_files)
        batch_flagged_count = 0
        batch_error_count = 0

        for i, sgf_file in enumerate(sgf_files, 1):
            start_time = time.monotonic()
            logger.info("Processing [%d/%d]: %s", i, total, sgf_file.name)

            try:
                sgf_text = sgf_file.read_text(encoding="utf-8")
                result = await enrich_single_puzzle(sgf_text, engine_manager, config, source_file=sgf_file.name, run_id=run_id)

                # Write JSON result
                json_out = output_path / f"{sgf_file.stem}.json"
                json_out.write_text(
                    result.model_dump_json(indent=2), encoding="utf-8"
                )

                # Enrich and write SGF
                enriched_sgf = enrich_sgf(sgf_text, result)
                sgf_out = output_path / sgf_file.name
                sgf_out.write_text(enriched_sgf, encoding="utf-8")

                code = _status_to_exit_code(result.validation.status)
                elapsed = time.monotonic() - start_time
                logger.info(
                    "Completed [%d/%d] %s in %.2fs: status=%s",
                    i,
                    total,
                    sgf_file.name,
                    elapsed,
                    result.validation.status.value
                    if hasattr(result.validation.status, "value")
                    else result.validation.status,
                )

                # G-04: Record puzzle in observability accumulator
                # M-1 fix: use ac_level to determine path, not heuristic
                is_has_solution = result.ac_level in (1, 2) and result.human_solution_confidence is not None
                is_disagreement = (
                    result.ai_solution_validated is False
                    and result.human_solution_confidence is not None
                )
                _val_flags = (
                    result.validation.flags
                    if hasattr(result.validation, "flags")
                    else []
                )
                _tree_override = "tree_validation_override" in _val_flags
                _frame_imbalance = "frame_imbalance" in _val_flags
                accumulator.record_puzzle(
                    has_solution=is_has_solution,
                    ac_level=result.ac_level,
                    disagreement=is_disagreement,
                    queries_used=getattr(result, "queries_used", 0),
                    co_correct=getattr(result, "co_correct_detected", False),
                    truncated=getattr(result, "tree_truncated", False),
                    error=False,
                    collection=getattr(result, "collection", ""),
                    frame_imbalance=_frame_imbalance,
                    tree_validation_override=_tree_override,
                )

                # G10: Write per-puzzle diagnostic JSON
                try:
                    diag = build_diagnostic_from_result(result)
                    diag_dir = Path(__file__).resolve().parent / ".lab-runtime" / "diagnostics" / run_id
                    diag_dir.mkdir(parents=True, exist_ok=True)
                    diag_file = diag_dir / f"{result.puzzle_id or sgf_file.stem}.json"
                    diag_file.write_text(diag.model_dump_json(indent=2), encoding="utf-8")
                    accumulator.record_diagnostic(diag)
                except Exception as diag_err:
                    logger.debug("Diagnostic write failed for %s: %s", sgf_file.name, diag_err)

                # G-04: Write disagreement record if applicable
                if is_disagreement and disagreement_sink:
                    from models.solve_result import DisagreementRecord, HumanSolutionConfidence
                    # C-3 fix: use WEAK as fallback (PLAUSIBLE doesn't exist in enum)
                    try:
                        hsc = HumanSolutionConfidence(result.human_solution_confidence)
                    except (ValueError, KeyError):
                        hsc = HumanSolutionConfidence.WEAK
                    # S-3 fix: use actual AI vs human data instead of dummy values
                    ai_top_wr = 0.0
                    if hasattr(result, "ai_top_move_winrate"):
                        ai_top_wr = result.ai_top_move_winrate
                    human_wr = result.validation.correct_move_winrate
                    disagreement_sink.write(DisagreementRecord(
                        puzzle_id=result.puzzle_id,
                        run_id=run_id,
                        human_move_gtp=result.validation.correct_move_gtp,
                        ai_move_gtp=result.validation.katago_top_move_gtp,
                        human_winrate=human_wr,
                        ai_winrate=ai_top_wr if ai_top_wr > 0 else human_wr,
                        delta=ai_top_wr - human_wr if ai_top_wr > 0 else 0.0,
                        human_solution_confidence=hsc,
                        level_slug=getattr(result.difficulty, "suggested_level", ""),
                        collection=getattr(result, "collection", ""),
                    ))

            except Exception as e:
                logger.error("Failed [%d/%d] %s: %s", i, total, sgf_file.name, e)
                code = EXIT_ERROR
                # G-04: Record error in accumulator
                accumulator.record_puzzle(
                    has_solution=False,
                    ac_level=0,
                    error=True,
                )

            # Track worst exit code (ERROR > FLAGGED > ACCEPTED)
            if code > worst_code:
                worst_code = code
            if code == EXIT_FLAGGED:
                batch_flagged_count += 1
            elif code == EXIT_ERROR:
                batch_error_count += 1

        # Q15: Batch quality gate — warn if acceptance rate below threshold
        try:
            accepted_count = sum(
                1 for f in (output_path / f"{sf.stem}.json" for sf in sgf_files)
                if f.exists()
            )
            acceptance_rate = accepted_count / total if total > 0 else 0.0
            threshold = float(config.quality_gates.acceptance_threshold)
            if acceptance_rate < threshold:
                logger.warning(
                    "Batch quality gate: acceptance rate %.1f%% (%d/%d) "
                    "below threshold %.0f%%. Review flagged/failed puzzles.",
                    acceptance_rate * 100, accepted_count, total,
                    threshold * 100,
                )
            else:
                logger.info(
                    "Batch quality gate: acceptance rate %.1f%% (%d/%d) "
                    "meets threshold %.0f%%.",
                    acceptance_rate * 100, accepted_count, total,
                    threshold * 100,
                )
        except (TypeError, AttributeError, ValueError):
            pass  # Config may be a mock in tests

        # G-04: Emit batch summary and close disagreement sink
        try:
            obs_threshold = 0.20
            if obs_config and hasattr(obs_config, "observability"):
                obs_threshold = obs_config.observability.collection_warning_threshold
            accumulator.emit(warning_threshold=obs_threshold)
        except Exception as e:
            logger.warning("Failed to emit batch summary: %s", e)
        if disagreement_sink:
            disagreement_sink.close()

        return worst_code


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="enrichment-lab",
        description="KataGo puzzle enrichment pipeline CLI",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable DEBUG logging with full tracebacks",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Override log file directory (default: tools/puzzle-enrichment-lab/logs/)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common_args(sub: argparse.ArgumentParser) -> None:
        """Add shared engine-related arguments to a subparser (AD-7)."""
        sub.add_argument("--katago", required=True, help="Path to KataGo binary")
        sub.add_argument("--katago-config", default="", help="Path to KataGo analysis config (auto-detected if omitted)")
        sub.add_argument("--config", default=None, help="Path to custom config JSON")
        sub.add_argument(
            "--quick-only", action="store_true", default=False,
            help="Force quick_only mode: 500 visits, 2 symmetries, no referee escalation",
        )
        sub.add_argument(
            "--visits", type=int, default=None, metavar="N",
            help="Override MCTS visit count (default: from config)",
        )
        sub.add_argument(
            "--symmetries", type=int, default=None, metavar="N",
            help="Override root symmetries sampled (default: from config)",
        )

    # --- enrich ---
    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Run full enrichment pipeline on a single SGF",
    )
    enrich_parser.add_argument("--sgf", default=None, help="Path to input SGF file (required unless --gui, in which case SGF can be pasted/uploaded in the browser)")
    enrich_parser.add_argument("--output", default=None, help="Path to write JSON result (required unless --gui)")
    _add_common_args(enrich_parser)
    enrich_parser.add_argument("--quick-model", default="", help=argparse.SUPPRESS)
    enrich_parser.add_argument("--referee-model", default="", help=argparse.SUPPRESS)
    enrich_parser.add_argument(
        "--emit-sgf",
        default=None,
        help="Optional path to also emit enriched SGF in the same enrich run",
    )
    enrich_parser.add_argument(
        "--gui",
        action="store_true",
        default=False,
        help="Launch visual enrichment lab GUI alongside enrichment (opens browser)",
    )
    enrich_parser.add_argument(
        "--debug-export",
        action="store_true",
        default=False,
        help="Export debug artifacts (trap moves + detector matrix) to .lab-runtime/debug/",
    )
    enrich_parser.add_argument("--host", default="127.0.0.1", help="GUI bridge host (default: 127.0.0.1)")
    enrich_parser.add_argument("--port", type=int, default=8999, help="GUI bridge port (default: 8999)")

    # --- apply ---
    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply enrichment JSON to an SGF and write enriched SGF",
    )
    apply_parser.add_argument("--sgf", required=True, help="Path to input SGF file")
    apply_parser.add_argument("--result", required=True, help="Path to enrichment JSON result")
    apply_parser.add_argument("--output", required=True, help="Path to write enriched SGF")

    # --- validate ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a puzzle's correct move",
    )
    validate_parser.add_argument("--sgf", required=True, help="Path to input SGF file")
    _add_common_args(validate_parser)
    validate_parser.add_argument("--quick-model", default="", help=argparse.SUPPRESS)
    validate_parser.add_argument("--referee-model", default="", help=argparse.SUPPRESS)

    # --- batch ---
    batch_parser = subparsers.add_parser(
        "batch",
        help="Run enrichment + apply on all SGFs in a directory",
    )
    batch_parser.add_argument("--input-dir", required=True, help="Directory containing .sgf files")
    batch_parser.add_argument("--output-dir", default=None, help="Directory to write enriched files (default: from config paths.outputs_dir)")
    _add_common_args(batch_parser)
    batch_parser.add_argument("--quick-model", default="", help=argparse.SUPPRESS)
    batch_parser.add_argument("--referee-model", default="", help=argparse.SUPPRESS)
    batch_parser.add_argument(
        "--num-puzzles", type=int, default=None, metavar="N",
        help="Stop after processing N puzzles; 0 or omit to process all",
    )

    # --- calibrate ---
    calibrate_parser = subparsers.add_parser(
        "calibrate",
        help="Run sequential single-puzzle calibration (production workflow)",
    )
    _add_common_args(calibrate_parser)
    calibrate_parser.add_argument(
        "--input-dir", default=None,
        help="Directory with SGF files (overrides config fixture_dirs)",
    )
    calibrate_parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for results (default: from config)",
    )
    calibrate_parser.add_argument("--run-label", default="", help="Label for this calibration run")
    calibrate_parser.add_argument(
        "--sample-size", type=int, default=None,
        help="Puzzles per collection (overrides config calibration.sample_size)",
    )
    calibrate_parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for sampling (overrides config; implies deterministic mode)",
    )
    calibrate_parser.add_argument(
        "--restart-every-n", type=int, default=None,
        help="Restart engine every N puzzles (overrides config; 0=never)",
    )
    calibrate_parser.add_argument(
        "--num-puzzles", type=int, default=None, metavar="N",
        help="Stop after processing N puzzles; 0 or omit to process all",
    )

    return parser


# ---------------------------------------------------------------------------
# GUI-mode enrichment (subprocess bridge server per ADR D2)
# ---------------------------------------------------------------------------

def _run_enrich_with_gui(args: argparse.Namespace) -> int:
    """Launch the bridge server as a subprocess, run enrichment, then tear down.

    ADR D2 requires ``gui/`` to be launched as a subprocess so
    ``rm -rf gui/`` removes all GUI code with zero residual imports.
    """
    import atexit
    import signal
    import subprocess as sp
    import webbrowser

    bridge_script = Path(__file__).resolve().parent / "bridge.py"
    if not bridge_script.exists():
        logger.error("GUI bridge script not found: %s", bridge_script)
        return EXIT_ERROR

    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8999)
    katago_config = resolve_katago_config(getattr(args, "katago_config", "") or "", args.katago)
    config_arg = getattr(args, "config", None)

    cmd: list[str] = [
        sys.executable, str(bridge_script),
        "--katago", args.katago,
        "--host", host,
        "--port", str(port),
    ]
    if katago_config:
        cmd.extend(["--katago-config", katago_config])
    if config_arg:
        cmd.extend(["--config", config_arg])
    if getattr(args, "verbose", False):
        cmd.append("--verbose")
    log_dir = getattr(args, "log_dir", None)
    if log_dir:
        cmd.extend(["--log-dir", log_dir])

    logger.info("Starting GUI bridge subprocess: %s", " ".join(cmd))
    proc = sp.Popen(cmd)
    atexit.register(proc.terminate)

    # Propagate SIGTERM to the child (Unix only; harmless on Windows)
    def _sigterm_handler(signum: int, frame: object) -> None:
        proc.terminate()
        sys.exit(EXIT_ERROR)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sigterm_handler)

    url = f"http://{host}:{port}"
    logger.info("Enrichment lab GUI at %s", url)
    webbrowser.open(url)

    # Run headless enrichment pipeline only if --sgf was supplied.
    # Without --sgf the user will paste/upload SGF via the browser.
    if args.sgf:
        exit_code = run_enrich(
            sgf_path=args.sgf,
            output_path=args.output or "",
            katago_path=args.katago,
            config_path=args.config,
            katago_config_path=katago_config,
            quick_only=args.quick_only,
            visits=args.visits,
            symmetries=args.symmetries,
            emit_sgf_path=args.emit_sgf,
        )
    else:
        # GUI-only mode: keep bridge alive until Ctrl-C
        logger.info("GUI bridge running. Open %s in your browser. Press Ctrl-C to stop.", url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
        exit_code = EXIT_ACCEPTED

    # Tear down the bridge server
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except sp.TimeoutExpired:
        proc.kill()

    return exit_code


# ---------------------------------------------------------------------------
# Calibrate subcommand handler
# ---------------------------------------------------------------------------

def _run_calibrate(args: argparse.Namespace, run_id: str) -> int:
    """Handle ``calibrate`` subcommand.

    Delegates to ``scripts.run_calibration`` core logic, preserving
    the exact engine restart cadence from ``_run_all_puzzles()`` (MH-1).
    """
    import sys as _sys
    _lab_dir = Path(__file__).resolve().parent
    if str(_lab_dir) not in _sys.path:
        _sys.path.insert(0, str(_lab_dir))

    from scripts.run_calibration import (
        _resolve_fixture_sgfs,
        run_calibration,
    )

    config = load_enrichment_config(
        Path(args.config) if args.config else None,
    )
    _apply_cli_overrides(config, args.visits, args.symmetries)

    kconfig = resolve_katago_config(
        getattr(args, "katago_config", "") or "", args.katago,
    )

    # Resolve restart_every_n: CLI > config > 0
    restart_every_n = args.restart_every_n
    if restart_every_n is None:
        restart_every_n = config.calibration.restart_every_n if config.calibration else 0

    # Resolve SGF file list
    if args.input_dir:
        input_path = Path(args.input_dir)
        sgf_files = sorted(input_path.glob("*.sgf"))
        collection_name = input_path.name
    else:
        cal = config.calibration
        if not cal:
            logger.error("No calibration config and no --input-dir specified")
            return EXIT_ERROR
        if args.sample_size is not None:
            cal.sample_size = args.sample_size
        if args.seed is not None:
            cal.seed = args.seed
            cal.randomize_fixtures = False
        sgf_files = _resolve_fixture_sgfs(config)
        collection_name = "+".join(cal.fixture_dirs)

    if args.num_puzzles and args.num_puzzles > 0 and len(sgf_files) > args.num_puzzles:
        sgf_files = sgf_files[: args.num_puzzles]

    # Resolve output dir
    output_dir = args.output_dir
    if not output_dir:
        try:
            from config import resolve_path
            output_dir = str(resolve_path(config, "calibration_results_dir"))
        except Exception:
            output_dir = str(_lab_dir / ".lab-runtime" / "calibration-results")

    return run_calibration(
        sgf_files=sgf_files,
        output_dir=output_dir,
        run_label=args.run_label,
        collection_name=collection_name,
        katago_path=args.katago,
        katago_config=kconfig,
        quick_only=args.quick_only,
        restart_every_n=restart_every_n,
        run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate subcommand.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Centralised bootstrap: generate run_id, configure logging, set context.
    run_id = bootstrap(verbose=args.verbose, log_dir=args.log_dir)

    if args.command == "enrich":
        logger.info("Enrich run_id: %s", run_id)

        gui_mode = getattr(args, "gui", False)

        # --sgf is required unless --gui is used (browser paste/upload covers it)
        if not gui_mode and not args.sgf:
            parser.error("--sgf is required (unless --gui is used)")

        # --output is required unless --gui is used
        if not gui_mode and not args.output:
            parser.error("--output is required (unless --gui is used)")

        if gui_mode:
            return _run_enrich_with_gui(args)

        return run_enrich(
            sgf_path=args.sgf,
            output_path=args.output,
            katago_path=args.katago,
            config_path=args.config,
            katago_config_path=args.katago_config,
            quick_only=args.quick_only,
            visits=args.visits,
            symmetries=args.symmetries,
            emit_sgf_path=args.emit_sgf,
            run_id=run_id,
            debug_export=getattr(args, 'debug_export', False),
        )
    elif args.command == "apply":
        return run_apply(
            sgf_path=args.sgf,
            result_path=args.result,
            output_path=args.output,
        )
    elif args.command == "validate":
        return run_validate(
            sgf_path=args.sgf,
            katago_path=args.katago,
            config_path=args.config,
            katago_config_path=args.katago_config,
            quick_only=args.quick_only,
            visits=args.visits,
            symmetries=args.symmetries,
        )
    elif args.command == "batch":
        # Q10: Resolve default output dir from config if not specified
        batch_output_dir = args.output_dir
        if not batch_output_dir:
            try:
                from config import load_enrichment_config, resolve_path
                _batch_cfg = load_enrichment_config()
                batch_output_dir = str(resolve_path(_batch_cfg, "outputs_dir"))
            except Exception:
                _lab = Path(__file__).resolve().parent
                batch_output_dir = str(_lab / ".lab-runtime" / "outputs")
        return run_batch(
            input_dir=args.input_dir,
            output_dir=batch_output_dir,
            katago_path=args.katago,
            config_path=args.config,
            katago_config_path=args.katago_config,
            quick_only=args.quick_only,
            visits=args.visits,
            symmetries=args.symmetries,
            num_puzzles=args.num_puzzles,
        )
    elif args.command == "calibrate":
        return _run_calibrate(args, run_id)
    else:
        parser.print_help()
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
