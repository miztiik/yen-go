"""Parse stage — SGF parsing and metadata extraction.

Extracts from enrich_single.py Steps 1-2 (parse SGF, extract metadata,
puzzle_id fallback, correct first move extraction).

Error policy: FAIL_FAST (can't continue without parsed SGF).
"""

from __future__ import annotations

import logging

try:
    from core.tsumego_analysis import (
        extract_correct_first_move,
        extract_position,
        parse_sgf,
    )

    from analyzers.config_lookup import (
        extract_metadata as _extract_metadata,
    )
    from analyzers.stages.protocols import (
        EnrichmentStage,
        ErrorPolicy,
        PipelineContext,
        SgfMetadata,
    )
except ImportError:
    from ...core.tsumego_analysis import (
        extract_correct_first_move,
        extract_position,
        parse_sgf,
    )
    from ..config_lookup import (
        extract_metadata as _extract_metadata,
    )
    from ..stages.protocols import (
        ErrorPolicy,
        PipelineContext,
        SgfMetadata,
    )

logger = logging.getLogger(__name__)


class ParseStage:
    """Parse SGF and extract metadata, position, and correct first move."""

    @property
    def name(self) -> str:
        return "parse_sgf"

    @property
    def error_policy(self) -> ErrorPolicy:
        return ErrorPolicy.FAIL_FAST

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        # Step 1: Parse SGF
        if ctx.notify_fn is not None:
            await ctx.notify_fn("parse_sgf", {"step": 1, "label": "Parse SGF"})

        root = parse_sgf(ctx.sgf_text)
        ctx.root = root

        # Extract metadata
        raw_metadata = _extract_metadata(root)
        ctx.metadata = SgfMetadata(
            puzzle_id=raw_metadata["puzzle_id"],
            tags=raw_metadata["tags"],
            corner=raw_metadata["corner"],
            move_order=raw_metadata["move_order"],
            ko_type=raw_metadata["ko_type"],
            collection=raw_metadata["collection"],
        )

        # Fallback: if GN property is absent, use source filename as puzzle_id
        if not ctx.metadata.puzzle_id and ctx.source_file:
            from pathlib import Path as _Path
            ctx.metadata.puzzle_id = _Path(ctx.source_file).stem
            logger.info(
                "GN property absent — using source filename as puzzle_id: %s",
                ctx.metadata.puzzle_id,
            )

        logger.info(
            "parse_sgf",
            extra={
                "stage": "parse_sgf",
                "board_size": root.get("SZ", "?"),
                "tags": ctx.metadata.tags, "corner": ctx.metadata.corner,
                "ko": ctx.metadata.ko_type,
                "sgf_length": len(ctx.sgf_text),
            },
        )
        logger.info("original_sgf: %s", ctx.sgf_text.strip())

        # Step 2: Extract correct first move and position
        if ctx.notify_fn is not None:
            await ctx.notify_fn("extract_solution", {"puzzle_id": ctx.metadata.puzzle_id})

        ctx.correct_move_sgf = extract_correct_first_move(root)
        ctx.position = extract_position(root)

        logger.info(
            "extract_solution",
            extra={
                "stage": "parse_sgf",
                "correct_move_sgf": ctx.correct_move_sgf or "<none>",
                "has_solution": ctx.correct_move_sgf is not None,
            },
        )

        return ctx
