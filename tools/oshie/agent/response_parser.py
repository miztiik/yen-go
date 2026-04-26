"""Response parser — validates and normalizes LLM JSON output.

Ensures the LLM response matches the expected teaching output contract
and is compatible with the enrichment pipeline's AiAnalysisResult fields.

Schema definitions live in tools.core.teaching_schema (single source of truth).
"""

from __future__ import annotations

from typing import Any

from tools.core.teaching_schema import (
    TeachingComments,
    TeachingOutput,
    parse_teaching_output,
)

# Re-export for backward compatibility
__all__ = ["TeachingComments", "TeachingOutput", "parse_llm_response"]


def parse_llm_response(data: dict[str, Any]) -> TeachingOutput:
    """Parse and validate an LLM response dict into a TeachingOutput.

    Args:
        data: Raw dict from LLM JSON response.

    Returns:
        Validated TeachingOutput.

    Raises:
        pydantic.ValidationError: If the response doesn't match the schema.
    """
    return parse_teaching_output(data)
