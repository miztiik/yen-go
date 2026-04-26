"""Shared teaching output schema for Go puzzle explanations.

Canonical Pydantic models for the structured teaching output format used by
both the yen-sei SFT training pipeline and the oshie inference
pipeline. This module is the single source of truth for the contract.

Two output formats:
  1. JSON (original) — used by oshie for API compatibility
  2. Tagged text (v3) — used by yen-sei SFT training for small model reliability
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ── Tagged text delimiters (v3 SFT format) ─────────────────────────────
# These triple-dash delimiters never appear in Go teaching prose.
_CORRECT_DELIM = "---CORRECT---"
_WRONG_DELIM = "---WRONG---"
_HINT_DELIM = "---HINT---"

# Regex to split on any delimiter line (captures the delimiter type)
_SECTION_RE = re.compile(
    r"^---(CORRECT|WRONG|HINT)---$",
    re.MULTILINE,
)


class TeachingComments(BaseModel):
    """Teaching comment structure matching AiAnalysisResult."""

    correct_comment: str = Field(
        default="",
        description="Teaching explanation for the correct first move.",
    )
    wrong_comments: dict[str, str] = Field(
        default_factory=dict,
        description="SGF coord -> explanation for each wrong move.",
    )
    summary: str = Field(
        default="",
        description="One-line puzzle summary.",
    )

    @field_validator("wrong_comments")
    @classmethod
    def validate_wrong_comments(cls, v: dict[str, str]) -> dict[str, str]:
        """Ensure wrong comment keys are valid SGF coordinates."""
        for key in v:
            if not key.isalpha() or len(key) != 2:
                logger.warning("Unexpected wrong_comments key: %s", key)
        return v


class TeachingOutput(BaseModel):
    """Validated teaching output from the LLM.

    Fields match the AiAnalysisResult.teaching_comments and hints shapes
    for drop-in compatibility with the existing SGF enricher.
    """

    teaching_comments: TeachingComments
    hints: list[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=3,
        description="3-tier progressive hints. Tier 1=technique, Tier 2=reasoning, Tier 3=coordinate.",
    )


def parse_teaching_output(data: dict[str, Any]) -> TeachingOutput:
    """Parse and validate a dict against the teaching output schema.

    Args:
        data: Raw dict (e.g., from LLM JSON response or refine stage output).

    Returns:
        Validated TeachingOutput.

    Raises:
        pydantic.ValidationError: If the data doesn't match the schema.
    """
    return TeachingOutput.model_validate(data)


# ── Tagged text format (v3 SFT) ────────────────────────────────────────
# Line-oriented format for small model fine-tuning. No JSON, no nesting.
#
# Example:
#   ---CORRECT---
#   The atari captures White's cutting stone.
#   ---WRONG---
#   Direct capture fails — White has a counter-atari.
#   ---WRONG---
#   Approaching from outside lets White make two eyes.
#   ---HINT---
#   Net (geta)
#   ---HINT---
#   Look at White's liberty shortage on the right side


def format_tagged_text(
    correct_comment: str,
    wrong_comments: dict[str, str],
    hints: list[str],
) -> str:
    """Format teaching content as tagged text for SFT training.

    Args:
        correct_comment: Why the correct move works.
        wrong_comments: SGF coord → explanation for each wrong move.
            Coordinate keys are **dropped** — only prose is emitted.
        hints: Up to 2 hints (technique name, reasoning). Coordinate
            hints ({!xy}) must NOT be included — those are computed.

    Returns:
        Tagged text string with ``---CORRECT---``, ``---WRONG---``,
        ``---HINT---`` delimiters.
    """
    parts: list[str] = []

    parts.append(_CORRECT_DELIM)
    parts.append(correct_comment.strip())

    for explanation in wrong_comments.values():
        text = explanation.strip()
        if text:
            parts.append(_WRONG_DELIM)
            parts.append(text)

    for hint in hints[:2]:
        text = hint.strip()
        if text:
            parts.append(_HINT_DELIM)
            parts.append(text)

    return "\n".join(parts)


def parse_tagged_text(text: str) -> tuple[str, list[str], list[str]]:
    """Parse tagged text back into structured fields.

    Args:
        text: Tagged text with ``---CORRECT---``, ``---WRONG---``,
            ``---HINT---`` delimiters.

    Returns:
        Tuple of ``(correct_comment, wrong_comments, hints)`` where
        ``wrong_comments`` is a flat list (no coordinate keys) and
        ``hints`` contains 0-2 entries.

    Raises:
        ValueError: If no ``---CORRECT---`` section is found.
    """
    # Split on delimiter lines, keeping the delimiter type as a token
    tokens = _SECTION_RE.split(text)

    correct_comment = ""
    wrong_comments: list[str] = []
    hints: list[str] = []

    i = 0
    while i < len(tokens):
        token = tokens[i].strip()
        if token == "CORRECT" and i + 1 < len(tokens):
            correct_comment = tokens[i + 1].strip()
            i += 2
        elif token == "WRONG" and i + 1 < len(tokens):
            content = tokens[i + 1].strip()
            if content:
                wrong_comments.append(content)
            i += 2
        elif token == "HINT" and i + 1 < len(tokens):
            content = tokens[i + 1].strip()
            if content:
                hints.append(content)
            i += 2
        else:
            i += 1

    if not correct_comment:
        raise ValueError("No ---CORRECT--- section found in tagged text")

    return correct_comment, wrong_comments, hints
