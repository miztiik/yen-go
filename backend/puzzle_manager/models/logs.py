"""Pydantic shapes for the ``logs`` subcommand JSON output.

The dashboard's Theme 4 search UI surfaces ``logs grep --json`` output
verbatim, so this schema is part of the dashboard wire contract. Any
breaking change here must be coordinated with ``tools/yengo_dashboard/``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LogsGrepHit(BaseModel):
    """One matching line returned by ``logs grep --json``.

    Stage logs under ``.pm-runtime/logs/`` are JSON-per-line; the ``ts``
    field is parsed from each line's JSON when possible. Lines that are
    not valid JSON (e.g., legacy or rotated chunks) still match — they
    just carry ``ts=None``.
    """

    file: str = Field(
        ...,
        description=(
            "Relative POSIX path of the matching log file (relative to the "
            "project root). Mirrors the project-wide path serialization rule."
        ),
    )
    line_no: int = Field(
        ..., ge=1, description="1-indexed line number within the file."
    )
    ts: str | None = Field(
        None,
        description=(
            "Timestamp string copied verbatim from the log line's JSON 'ts' "
            "field. None when the line is not a valid JSON object."
        ),
    )
    stream: str = Field(
        "stdout",
        description=(
            "Always 'stdout' for stage logs today. Reserved for future "
            "heterogeneous sources (e.g., separate stderr captures)."
        ),
    )
    text: str = Field(
        ..., description="Raw matching line, with no trailing newline."
    )
    context_before: list[str] = Field(
        default_factory=list,
        description="Up to 2 preceding raw lines, in file order.",
    )
    context_after: list[str] = Field(
        default_factory=list,
        description="Up to 2 following raw lines, in file order.",
    )
