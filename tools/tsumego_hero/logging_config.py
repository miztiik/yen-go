"""
Logging configuration for Tsumego Hero downloader.

Subclasses tools.core.logging.StructuredLogger with TH-specific convenience methods.
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
    setup_logging as core_setup,
)


class StructuredLogger(CoreStructuredLogger):
    """Tsumego Hero-specific structured logger with convenience methods."""

    def run_start(
        self,
        max_puzzles: int = 0,
        resume: bool = False,
        output_dir: str = "",
        **kwargs,
    ) -> None:
        """Log TH run start."""
        super().run_start(
            output_dir=output_dir,
            max_items=max_puzzles,
            resume=resume,
            **kwargs,
        )

    def collection_start(self, set_id: str, name: str, count: int = 0) -> None:
        """Log collection fetch start."""
        self.event(
            EventType.PAGE_START,
            f"COLLECTION {name} (set_id={set_id}, {count} puzzles)",
            set_id=set_id,
            name=name,
            puzzle_count=count,
        )

    def collection_end(self, set_id: str, name: str, downloaded: int = 0) -> None:
        """Log collection completion."""
        self.event(
            EventType.PAGE_END,
            f"COLLECTION {name} done ({downloaded} downloaded)",
            set_id=set_id,
            name=name,
            downloaded=downloaded,
        )

    def puzzle_fetch(self, puzzle_id: int | str, url: str) -> None:
        """Log puzzle fetch with URL at INFO level."""
        self.event(
            EventType.ITEM_FETCH,
            f"GET {puzzle_id} {url}",
            puzzle_id=puzzle_id,
            url=url,
        )

    def puzzle_save(
        self,
        puzzle_id: int | str,
        path: str,
        downloaded: int = 0,
        skipped: int = 0,
        errors: int = 0,
    ) -> None:
        """Log puzzle saved with running totals."""
        self.item_save(
            item_id=str(puzzle_id),
            path=path,
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
        )

    def puzzle_skip(self, puzzle_id: int | str, reason: str) -> None:
        """Log puzzle skipped."""
        self.item_skip(item_id=str(puzzle_id), reason=reason)

    def puzzle_error(self, puzzle_id: int | str, error: str) -> bool:
        """Log puzzle error. Returns True if should fail-fast."""
        return self.item_error(item_id=str(puzzle_id), error=error)

    def puzzle_enrich(
        self,
        puzzle_id: int | str,
        level: str,
        tags: list[str],
        collections: list[str] | None = None,
        intent: str | None = None,
    ) -> None:
        """Log puzzle enrichment with YG/YT/YL/intent."""
        self.event(
            "puzzle_enrich",
            f"ENRICH {puzzle_id} level={level} tags={tags} coll={collections or []} intent={intent or ''}",
            puzzle_id=puzzle_id,
            level=level,
            tags=tags,
            collections=collections or [],
            intent=intent or "",
        )

    def collection_match(
        self,
        puzzle_id: int | str,
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
        puzzle_id: int | str,
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


def setup_logging(
    output_dir: Path,
    verbose: bool = False,
    log_to_file: bool = True,
    max_consecutive_errors: int = 10,
) -> StructuredLogger:
    """Set up Tsumego Hero logging.

    Args:
        output_dir: Directory for log files.
        verbose: Enable debug logging to console.
        log_to_file: Write JSON logs to file.
        max_consecutive_errors: Fail-fast threshold.

    Returns:
        StructuredLogger instance with TH convenience methods.
    """
    core_logger = core_setup(
        output_dir=output_dir,
        logger_name="tsumego_hero",
        verbose=verbose,
        log_to_file=log_to_file,
        log_suffix="tsumego-hero",
        max_consecutive_errors=max_consecutive_errors,
    )

    th_logger = StructuredLogger(core_logger.logger)
    th_logger.set_max_errors(max_consecutive_errors)
    return th_logger


def get_logger(name: str = "tsumego_hero") -> StructuredLogger:
    """Get existing TH logger by name."""
    return StructuredLogger(logging.getLogger(name))


__all__ = [
    "EventType",
    "StructuredLogger",
    "setup_logging",
    "get_logger",
]
