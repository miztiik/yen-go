"""
Logging configuration for TsumegoDragon downloader.

Uses tools.core.logging for base functionality with t-dragon-specific convenience methods.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tools.core.logging import (
    EventType,
)
from tools.core.logging import (
    StructuredLogger as CoreStructuredLogger,
)
from tools.core.logging import (
    setup_logging as core_setup_logging,
)

# Re-export EventType for backwards compatibility
__all__ = ["EventType", "StructuredLogger", "setup_logging", "get_logger"]


class StructuredLogger(CoreStructuredLogger):
    """TsumegoDragon-specific structured logger with convenience methods.

    Extends core StructuredLogger with t-dragon-specific event methods.
    """

    # t-dragon-specific convenience methods

    def run_start(
        self,
        max_puzzles: int = 0,
        resume: bool = False,
        output_dir: str = "",
        categories: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Log t-dragon run start."""
        super().run_start(
            output_dir=output_dir,
            max_items=max_puzzles,
            resume=resume,
            categories=categories or [],
            **kwargs,
        )

    def category_start(self, category: str, level: int) -> None:
        """Log category fetch start."""
        self.event(
            EventType.PAGE_START,
            f"CATEGORY {category} level={level}",
            category=category,
            difficulty=level,
        )

    def category_end(self, category: str, count: int) -> None:
        """Log category completion."""
        self.event(
            EventType.PAGE_END,
            f"CATEGORY {category} done count={count}",
            category=category,
            puzzle_count=count,
        )

    def puzzle_fetch(self, puzzle_id: str, url: str, category: str = "") -> None:
        """Log puzzle fetch with URL at INFO level."""
        desc = f" ({category})" if category else ""
        self.event(
            EventType.ITEM_FETCH,
            f"GET {puzzle_id}{desc} {url}",
            puzzle_id=puzzle_id,
            url=url,
            category=category,
        )

    def page_start(self, page_num: int, total_pages: int, url: str = "") -> None:
        """Log page/batch start."""
        url_info = f" {url}" if url else ""
        self.event(
            EventType.PAGE_START,
            f"PAGE {page_num}/{total_pages}{url_info}",
            page=page_num,
            total_pages=total_pages,
            url=url,
        )

    def page_fetch(self, page_num: int, url: str, count: int) -> None:
        """Log page fetch with URL and result count."""
        self.event(
            EventType.PAGE_FETCH,
            f"FETCH page {page_num} ({count} items) {url}",
            page=page_num,
            url=url,
            count=count,
        )

    def puzzle_enrich(self, puzzle_id: str, level: str, tags: list[str]) -> None:
        """Log puzzle enrichment."""
        self.event(
            "puzzle_enrich",
            f"ENRICH {puzzle_id} level={level} tags={tags}",
            puzzle_id=puzzle_id,
            puzzle_level=level,
            tags=tags,
        )

    def collection_match(
        self,
        puzzle_id: str,
        source_name: str,
        matched_slug: str | None,
    ) -> None:
        """Log collection resolution result (YL)."""
        status = "matched" if matched_slug else "no_match"
        self.event(
            "collection_match",
            f"COLLECTION {puzzle_id} '{source_name}' -> {matched_slug or 'NONE'}",
            puzzle_id=puzzle_id,
            source_name=source_name,
            matched_slug=matched_slug,
            status=status,
        )

    def intent_match(
        self,
        puzzle_id: str,
        description_snippet: str,
        matched_slug: str | None,
        confidence: float = 0.0,
        tier: str = "",
    ) -> None:
        """Log intent resolution result (C[])."""
        status = "matched" if matched_slug else "no_match"
        snippet = description_snippet[:30] if description_snippet else ""
        self.event(
            "intent_match",
            f"INTENT {puzzle_id} '{snippet}...' -> {matched_slug or 'NONE'} (conf={confidence:.2f}, tier={tier})",
            puzzle_id=puzzle_id,
            description_snippet=description_snippet[:50] if description_snippet else "",
            matched_slug=matched_slug,
            confidence=confidence,
            tier=tier,
            status=status,
        )

    def puzzle_save(
        self,
        puzzle_id: str,
        path: str,
        downloaded: int = 0,
        skipped: int = 0,
        errors: int = 0,
        **kwargs,
    ) -> None:
        """Log puzzle saved."""
        self.item_save(
            item_id=puzzle_id,
            path=path,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
            **kwargs,
        )

    def puzzle_skip(self, puzzle_id: str, reason: str) -> None:
        """Log puzzle skipped."""
        self.item_skip(item_id=puzzle_id, reason=reason)

    def puzzle_error(self, puzzle_id: str, error: str) -> bool:
        """Log puzzle error. Returns True if should fail-fast."""
        return self.item_error(item_id=puzzle_id, error=error)

    def checkpoint_load(self, cursor: int, downloaded: int) -> None:
        """Log checkpoint loaded (t-dragon uses cursor, not page)."""
        super().checkpoint_load(downloaded=downloaded, page=cursor)

    def checkpoint_save(self, cursor: int, downloaded: int) -> None:
        """Log checkpoint saved (t-dragon uses cursor, not page)."""
        super().checkpoint_save(downloaded=downloaded, page=cursor)

    def api_response(self, count: int, remaining: int = 0) -> None:
        """Log API response with result count."""
        self.event(
            EventType.API_REQUEST,
            f"RESPONSE count={count} remaining={remaining}",
            count=count,
            remaining=remaining,
        )


def setup_logging(
    output_dir: Path,
    verbose: bool = False,
    log_to_file: bool = True,
    max_consecutive_errors: int = 10,
) -> StructuredLogger:
    """Set up TsumegoDragon logging.

    Args:
        output_dir: Directory for log files.
        verbose: Enable debug logging to console.
        log_to_file: Write JSON logs to file.
        max_consecutive_errors: Fail-fast threshold.

    Returns:
        StructuredLogger instance with t-dragon methods.
    """
    core_logger = core_setup_logging(
        output_dir=output_dir,
        logger_name="tsumegodragon",
        verbose=verbose,
        log_to_file=log_to_file,
        log_suffix="tdragon",  # Produces: 20260205-143022-tdragon.jsonl
        max_consecutive_errors=max_consecutive_errors,
    )

    tdragon_logger = StructuredLogger(core_logger.logger)
    tdragon_logger.set_max_errors(max_consecutive_errors)
    return tdragon_logger


def get_logger(name: str = "tsumegodragon") -> StructuredLogger:
    """Get existing t-dragon logger by name."""
    return StructuredLogger(logging.getLogger(name))
