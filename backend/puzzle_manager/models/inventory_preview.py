"""Pydantic shape for ``inventory {rebuild,reconcile,fix} --dry-run --json`` (Theme 14c1).

Wire contract for the dashboard's Theme 14c Preview→Apply flow. Each
mutating inventory op shares this single shape so the modal can render
the same impact-summary table regardless of which op the operator chose.

The dry-run scans SGF files on disk to compute ``disk_total``, reads the
current ``inventory.json`` snapshot to compute ``snapshot_total_before``,
and reports the would-mutate flags WITHOUT actually rewriting anything.

Issue counters from ``IntegrityReport`` are intentionally NOT duplicated
here — callers should pair the preview with a separate ``inventory --check
--json`` call when they need per-issue rows. Conflating the two would
double the disk scan cost for no benefit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

InventoryOp = Literal["rebuild", "reconcile", "fix"]


class InventoryMutationPreview(BaseModel):
    """Impact summary for an inventory mutation that has NOT yet run.

    All counts are computed from the live filesystem at preview time;
    re-running the preview after publishing more puzzles will see a
    different ``disk_total``.
    """

    op: InventoryOp = Field(..., description="Which mutation was previewed.")
    snapshot_exists: bool = Field(
        ..., description="True iff inventory.json was present when previewed."
    )
    snapshot_total_before: int | None = Field(
        default=None,
        description=(
            "puzzles_total recorded in the current inventory.json, or null "
            "when no snapshot exists."
        ),
    )
    disk_total: int = Field(
        ...,
        ge=0,
        description=(
            "Number of .sgf files counted under ``yengo-puzzle-collections/sgf/``. "
            "Matches what the snapshot would record after applying."
        ),
    )
    delta: int = Field(
        ...,
        description=(
            "disk_total − snapshot_total_before. Positive means new puzzles "
            "would be reflected; negative means the snapshot is stale-high "
            "(e.g. files were removed). Equal to ``disk_total`` when no "
            "snapshot exists."
        ),
    )
    would_rewrite_snapshot: bool = Field(
        ...,
        description=(
            "True if applying the op would write a new inventory.json. "
            "``fix`` reports false when a pre-flight integrity check is "
            "already clean (the apply path no-ops in that case)."
        ),
    )
    would_rebuild_search_db: bool = Field(
        ...,
        description=(
            "True if applying the op would rebuild yengo-search.db. None of "
            "the inventory ops touch the search DB today — use ``vacuum-db`` "
            "for that. Kept on the wire for forward compatibility."
        ),
    )
    fix_skip_reason: str | None = Field(
        default=None,
        description=(
            "Populated only for ``op=fix`` when the current integrity check "
            "is clean — the apply path would short-circuit with this message."
        ),
    )


class InventoryMutationResult(BaseModel):
    """Wire shape for the *applied* mutation (Theme 14c2).

    Mirrors :class:`InventoryMutationPreview` so the dashboard's modal can
    render the same impact-summary table for both Preview and post-Apply
    states. The two are distinct types — never reuse the preview shape for
    the result, since callers need to distinguish ``executed=False`` (still
    a preview) from ``executed=True`` (audit entry written).
    """

    op: InventoryOp = Field(..., description="Which mutation was applied.")
    executed: bool = Field(
        default=True,
        description="Always true for results emitted by the apply path.",
    )
    snapshot_total_before: int | None = Field(
        default=None,
        description=(
            "puzzles_total recorded in inventory.json *before* the mutation. "
            "Null when no prior snapshot existed."
        ),
    )
    snapshot_total_after: int = Field(
        ...,
        ge=0,
        description="puzzles_total recorded in the rewritten inventory.json.",
    )
    delta: int = Field(
        ...,
        description="snapshot_total_after − snapshot_total_before (treats null before as 0).",
    )
    rewrote_snapshot: bool = Field(
        ...,
        description=(
            "True if a fresh inventory.json was written. ``fix`` reports false "
            "when the pre-flight integrity check was already clean."
        ),
    )
    rebuilt_search_db: bool = Field(
        ...,
        description=(
            "True if yengo-search.db was rebuilt. Today only ``rebuild`` does "
            "this; ``reconcile`` and ``fix`` leave the search DB alone."
        ),
    )
    audit_timestamp: str | None = Field(
        default=None,
        description=(
            "ISO 8601 timestamp recorded in audit.jsonl. Null when no audit "
            "row was written (e.g. ``fix`` skipped because already clean)."
        ),
    )
    fix_skip_reason: str | None = Field(
        default=None,
        description=(
            "Populated only for ``op=fix`` when the apply path short-circuited "
            "because the pre-flight integrity check was already clean."
        ),
    )
