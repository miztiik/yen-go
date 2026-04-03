"""
SGF Enrichment Module.

Provides enrichment capabilities for puzzle SGF files:
- YH: Compact hints list (replaces YH1/YH2/YH3) with liberty analysis
- YC: Board region detection
- YK: Ko context classification
- YO: Move order flexibility detection
- YR: Refutation move extraction

Usage:
    from backend.puzzle_manager.core.enrichment import enrich_puzzle, EnrichmentConfig

    config = EnrichmentConfig(enable_hints=True, verbose=True)
    result = enrich_puzzle(game, config)

Constitution Compliance:
- Zero Runtime Backend: Enrichment runs at build time only
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.puzzle_manager.core.enrichment.config import (
    HINT_REASON_CODES,
    EnrichmentConfig,
    EnrichmentOperationLog,
    HintOperationLog,
)

if TYPE_CHECKING:
    from backend.puzzle_manager.core.sgf_parser import SGFGame

logger = logging.getLogger("enrichment")


@dataclass
class EnrichmentResult:
    """Result of enrichment processing.

    Contains all computed enrichment properties that should be
    injected into the SGF file.

    Hints use compact list format (DRY principle):
    - hints: list[str] contains only non-empty hints in pedagogical order
    - Replaces the old yh1/yh2/yh3 separate properties
    - Serializes to YH[hint1|hint2|...] format in SGF
    """

    # Hints (compact list format, replaces YH1/YH2/YH3)
    hints: list[str] = field(default_factory=list)

    # Board region (YC)
    region: str | None = None  # TL, TR, BL, BR, T, B, L, R, C, FULL

    # Ko context (YK)
    ko_context: str | None = None  # none, direct, approach

    # Move order flexibility (YO)
    move_order: str | None = None  # strict, flexible

    # Refutation moves (YR)
    refutations: str | None = None  # comma-separated SGF coords


def enrich_puzzle(
    game: SGFGame,
    config: EnrichmentConfig | None = None,
) -> EnrichmentResult:
    """Main entry point for puzzle enrichment with structured logging.

    Analyzes the puzzle and generates all enrichment properties.
    Logs each operation's success/failure/duration as JSON for diagnostics.

    Args:
        game: Parsed SGF game to enrich.
        config: Enrichment configuration. Uses defaults if None.

    Returns:
        EnrichmentResult with all computed properties.
    """
    import time
    from dataclasses import asdict

    if config is None:
        config = EnrichmentConfig()

    result = EnrichmentResult()

    # Initialize structured log
    puzzle_id = game.metadata.get("GN", "") if game.metadata else ""
    ops_log = EnrichmentOperationLog(puzzle_id=puzzle_id)
    start_total = time.perf_counter()

    # Import enrichers here to avoid circular imports
    from backend.puzzle_manager.core.enrichment.hints import HintGenerator
    from backend.puzzle_manager.core.enrichment.ko import detect_ko_context
    from backend.puzzle_manager.core.enrichment.move_order import detect_move_order
    from backend.puzzle_manager.core.enrichment.refutation import (
        extract_refutations,
        format_refutations,
    )
    from backend.puzzle_manager.core.enrichment.region import detect_region, region_to_sgf

    # Collect all stone positions
    all_stones = game.black_stones + game.white_stones

    # === YC: Board region ===
    region_log = {"status": "success", "value": None, "reason": None, "duration_ms": 0}
    start_region = time.perf_counter()
    if config.enable_region and all_stones:
        try:
            region = detect_region(
                stones=all_stones,
                board_size=game.board_size,
            )
            result.region = region_to_sgf(region)
            region_log["value"] = result.region
            if config.verbose:
                logger.debug(f"Detected region: {result.region}")
        except Exception as e:
            region_log["status"] = "failed"
            region_log["reason"] = str(e)
            logger.debug(f"Region detection failed: {e}")
    elif not all_stones:
        region_log["status"] = "skipped"
        region_log["reason"] = "no_stones"
    region_log["duration_ms"] = int((time.perf_counter() - start_region) * 1000)
    ops_log.enrichment_operations["region"] = region_log

    # === YH: Hints (compact list format) ===
    hint_log = HintOperationLog()
    start_hints = time.perf_counter()
    if config.enable_hints:
        try:
            hint_generator = HintGenerator(config)
            tags = game.yengo_props.tags if game.yengo_props else []

            # Generate hints in pedagogical order:
            # YH1 = Technique (name the concept)
            # YH2 = Reasoning (explain why + warn wrong approach)
            # YH3 = Coordinate (give the answer + technique outcome)
            yh1 = hint_generator.generate_technique_hint(tags, game)
            if yh1 and yh1.strip():
                hint_log.yh1_generated = True
                hint_log.yh1_value = yh1.strip()
            else:
                hint_log.yh1_reason = "no_matching_tags" if not tags else "generation_failed"

            # YH2 reasoning only emitted when YH1 technique exists —
            # reasoning without a named technique is pedagogically incoherent.
            if hint_log.yh1_generated:
                yh2 = hint_generator.generate_reasoning_hint(tags, game)
                if yh2 and yh2.strip():
                    hint_log.yh2_generated = True
                    hint_log.yh2_value = yh2.strip()
                else:
                    hint_log.yh2_reason = "no_matching_tags" if not tags else "no_matching_tags"
            else:
                hint_log.yh2_reason = "no_technique_hint"

            yh3 = hint_generator.generate_coordinate_hint(game, tags)
            if yh3 and yh3.strip():
                hint_log.yh3_generated = True
                hint_log.yh3_value = yh3.strip()
            else:
                hint_log.yh3_reason = "no_solution_tree" if not game.has_solution else "depth_gated_or_failed"

            # Collect non-empty hints into compact list (DRY principle)
            hints = []
            if hint_log.yh1_generated:
                hints.append(hint_log.yh1_value)
            if hint_log.yh2_generated:
                hints.append(hint_log.yh2_value)
            if hint_log.yh3_generated:
                hints.append(hint_log.yh3_value)

            # Last-resort fallback: if no hints generated but solution exists,
            # embed the correct move coordinate so every solvable puzzle has
            # at least one hint (bypasses depth gating).
            if not hints and game.has_solution:
                fallback = hint_generator._get_first_correct_move(game.solution_tree)
                if fallback:
                    coord = hint_generator._point_to_token(fallback)
                    fallback_hint = f"Play at {coord}."
                    hints.append(fallback_hint)
                    hint_log.yh3_generated = True
                    hint_log.yh3_value = fallback_hint
                    hint_log.yh3_reason = None  # clear previous reason

            result.hints = hints
            hint_log.final_hint_count = len(hints)

            # Determine status
            if len(hints) == 3:
                hint_log.status = "success"
            elif len(hints) > 0:
                hint_log.status = "partial"
            else:
                hint_log.status = "failed"

            if config.verbose:
                logger.debug(f"Generated {len(hints)} hints: {hints}")
        except Exception as e:
            hint_log.status = "failed"
            hint_log.errors = [str(e)]
            logger.exception(f"Hint generation failed: {e}")
    hint_log.duration_ms = int((time.perf_counter() - start_hints) * 1000)
    ops_log.enrichment_operations["hints"] = asdict(hint_log)

    # === YK: Ko context ===
    ko_log = {"status": "success", "value": None, "reason": None, "duration_ms": 0}
    start_ko = time.perf_counter()
    if config.enable_ko:
        try:
            ko_type = detect_ko_context(game)
            result.ko_context = ko_type.value if ko_type else "none"
            ko_log["value"] = result.ko_context
            if config.verbose:
                logger.debug(f"Detected ko context: {result.ko_context}")
        except Exception as e:
            ko_log["status"] = "failed"
            ko_log["reason"] = str(e)
            logger.debug(f"Ko detection failed: {e}")
    ko_log["duration_ms"] = int((time.perf_counter() - start_ko) * 1000)
    ops_log.enrichment_operations["ko"] = ko_log

    # === YO: Move order flexibility ===
    move_order_log = {"status": "success", "value": None, "reason": None, "duration_ms": 0}
    start_move_order = time.perf_counter()
    if config.enable_move_order and game.has_solution:
        try:
            flexibility = detect_move_order(game.solution_tree)
            # Only set if not strict (strict is default)
            if flexibility.value != "strict":
                result.move_order = flexibility.value
            move_order_log["value"] = flexibility.value
            if config.verbose:
                logger.debug(f"Detected move order: {flexibility.value}")
        except Exception as e:
            move_order_log["status"] = "failed"
            move_order_log["reason"] = str(e)
            logger.debug(f"Move order detection failed: {e}")
    elif not game.has_solution:
        move_order_log["status"] = "skipped"
        move_order_log["reason"] = "no_solution_tree"
    move_order_log["duration_ms"] = int((time.perf_counter() - start_move_order) * 1000)
    ops_log.enrichment_operations["move_order"] = move_order_log

    # === YR: Refutation moves ===
    refutation_log = {"status": "success", "value": None, "reason": None, "duration_ms": 0}
    start_refutation = time.perf_counter()
    if config.enable_refutation and game.has_solution:
        try:
            refutations = extract_refutations(game.solution_tree)
            result.refutations = format_refutations(refutations)
            refutation_log["value"] = result.refutations
            if config.verbose and result.refutations:
                logger.debug(f"Extracted refutations: {result.refutations}")
        except Exception as e:
            refutation_log["status"] = "failed"
            refutation_log["reason"] = str(e)
            logger.debug(f"Refutation extraction failed: {e}")
    elif not game.has_solution:
        refutation_log["status"] = "skipped"
        refutation_log["reason"] = "no_solution_tree"
    refutation_log["duration_ms"] = int((time.perf_counter() - start_refutation) * 1000)
    ops_log.enrichment_operations["refutation"] = refutation_log

    # === LOG SUMMARY ===
    ops_log.total_duration_ms = int((time.perf_counter() - start_total) * 1000)

    # Determine overall status
    statuses = [
        region_log["status"],
        hint_log.status,
        ko_log["status"],
        move_order_log["status"],
        refutation_log["status"],
    ]
    if all(s in ("success", "skipped") for s in statuses):
        ops_log.overall_status = "success"
    elif any(s == "failed" for s in statuses):
        ops_log.overall_status = "partial" if any(s == "success" for s in statuses) else "failed"
    else:
        ops_log.overall_status = "partial"

    # Log structured JSON at INFO level for batch analysis
    if config.verbose:
        logger.info(ops_log.to_json())

    return result


# Re-export public API
__all__ = [
    "EnrichmentConfig",
    "EnrichmentOperationLog",
    "EnrichmentResult",
    "HintOperationLog",
    "HINT_REASON_CODES",
    "enrich_puzzle",
]
