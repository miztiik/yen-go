"""Pydantic shape for ``inventory check --json`` (Theme 14a).

Theme 14a wire contract: the dashboard's Inventory health surface (Theme 14b)
renders this report, so any breaking change here must be coordinated with
``tools/yengo_dashboard/``.

The CLI's existing ``check_integrity()`` returns a free-form
``IntegrityResult`` dataclass with discrepancy strings; this module gives
operators a structured, machine-readable view with one row per issue.

Issue kinds (Theme 14a — initial set):
  * ``missing_file``: a publish-log entry references an SGF that no longer
    exists on disk.
  * ``orphan_file``: an SGF on disk has no publish-log entry.

``hash_mismatch`` (content drift) is intentionally deferred — detecting it
requires re-reading every SGF and rehashing, which is an O(N) disk cost the
metadata-only check above does not pay. A separate slice will add it behind
a ``--deep`` flag.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IssueKind = Literal["missing_file", "orphan_file"]


class IntegrityIssue(BaseModel):
    """One row in the integrity report. Fields populated depend on ``kind``.

    ``puzzle_id`` is the SGF basename without ``.sgf`` (matches GN suffix);
    ``path`` is the POSIX path relative to the publication root.
    """

    kind: IssueKind
    puzzle_id: str | None = Field(
        default=None,
        description="GN suffix / filename stem when known (missing_file, orphan_file).",
    )
    path: str = Field(
        ...,
        description="POSIX path relative to publication root, e.g. 'sgf/0001/abc.sgf'.",
    )


class IntegritySummary(BaseModel):
    """Counts per kind. Always present so the dashboard can render zero rows."""

    missing_file: int = Field(..., ge=0)
    orphan_file: int = Field(..., ge=0)


class IntegrityReport(BaseModel):
    """Structured ``inventory check --json`` output (Theme 14a).

    ``ok`` is true iff every category in ``summary`` is zero. The dashboard
    uses this single bit for the green/amber/rose health badge; per-issue
    rows drive the issue table.
    """

    ok: bool = Field(..., description="True iff no issues were detected.")
    issues: list[IntegrityIssue] = Field(default_factory=list)
    summary: IntegritySummary

    @classmethod
    def from_legacy_result(cls, result: object) -> "IntegrityReport":
        """Adapt the existing free-form ``IntegrityResult`` dataclass.

        The legacy result already enumerates orphan paths in two attributes
        (``orphan_entries`` = missing files; ``orphan_files`` = files with no
        log entry). We unpack those into typed rows so the wire contract is
        list-of-issues, not a string blob.
        """
        # Avoid importing the dataclass at module import time so this model
        # stays cheap to load (and never drags inventory deps into callers).
        missing_paths = list(getattr(result, "orphan_entries", []) or [])
        orphan_paths = list(getattr(result, "orphan_files", []) or [])
        issues: list[IntegrityIssue] = []
        for p in missing_paths:
            issues.append(
                IntegrityIssue(
                    kind="missing_file",
                    puzzle_id=_puzzle_id_from_path(p),
                    path=p,
                )
            )
        for p in orphan_paths:
            issues.append(
                IntegrityIssue(
                    kind="orphan_file",
                    puzzle_id=_puzzle_id_from_path(p),
                    path=p,
                )
            )
        summary = IntegritySummary(
            missing_file=len(missing_paths),
            orphan_file=len(orphan_paths),
        )
        return cls(
            ok=summary.missing_file == 0 and summary.orphan_file == 0,
            issues=issues,
            summary=summary,
        )


def _puzzle_id_from_path(rel_path: str) -> str | None:
    """Extract the GN suffix from a publication-root-relative path.

    ``sgf/0001/abc123def4567890.sgf`` → ``abc123def4567890``. Returns ``None``
    for paths that don't end in ``.sgf`` so the report is honest about what
    it can recover from a stray entry.
    """
    if not rel_path.endswith(".sgf"):
        return None
    stem = rel_path.rsplit("/", 1)[-1]
    return stem[:-4]
