"""Shared teaching output schema for Go puzzle explanations.

Canonical Pydantic models for the structured teaching output format used by
both the yen-sei SFT training pipeline and the llm-teaching-agent inference
pipeline. This module is the single source of truth for the contract.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


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
