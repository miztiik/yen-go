"""Logging configuration for puzzle_intent module.

Extends tools.core.logging.StructuredLogger with intent-specific
convenience methods for structured event logging.
"""

from __future__ import annotations

import logging

from tools.core.logging import EventType, StructuredLogger


class IntentLogger(StructuredLogger):
    """Intent-specific structured logger.

    Extends core StructuredLogger with convenience methods for
    intent matching events.
    """

    def intent_match(
        self,
        objective_id: str,
        alias: str,
        confidence: float,
        match_tier: str,
    ) -> None:
        """Log successful intent match."""
        self.event(
            EventType.INTENT_MATCH,
            f"INTENT {match_tier} '{alias}' -> {objective_id} ({confidence:.3f})",
            objective_id=objective_id,
            match_tier=match_tier,
            confidence=confidence,
            alias=alias,
        )

    def intent_no_match(self, cleaned_text: str) -> None:
        """Log no intent match found."""
        truncated = cleaned_text[:80] if cleaned_text else "(empty)"
        self.event(
            EventType.INTENT_NO_MATCH,
            f"INTENT no_match text='{truncated}'",
            level=logging.DEBUG,
            cleaned_text=cleaned_text[:200],
        )

    def intent_model_load(self, model_name: str, load_time_sec: float) -> None:
        """Log semantic model loaded."""
        self.event(
            EventType.INTENT_MODEL_LOAD,
            f"INTENT model loaded: {model_name} ({load_time_sec:.1f}s)",
            model_name=model_name,
            load_time_sec=load_time_sec,
        )


def get_intent_logger(
    existing_logger: StructuredLogger | None = None,
) -> IntentLogger:
    """Get or create an IntentLogger.

    Args:
        existing_logger: Wrap an existing StructuredLogger.
            If None, creates a new one with 'puzzle_intent' name.

    Returns:
        IntentLogger instance.
    """
    if existing_logger is not None:
        return IntentLogger(existing_logger.logger)
    return IntentLogger(logging.getLogger("puzzle_intent"))
