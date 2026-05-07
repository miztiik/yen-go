"""Pydantic shapes and aggregation for ``status --failures-summary``.

Theme 2a wire contract: the dashboard's Pipeline tab renders the grouped
JSON this CLI mode emits, so any breaking change here must be coordinated
with ``tools/yengo_dashboard/``.

The aggregation is pure (run-state JSONs in, summary out). It reads only
existing ``RunState.failures[]`` — no new persistence, no new event source.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.puzzle_manager.state.models import RunState


_SAMPLE_PUZZLE_LIMIT = 5
_SAMPLE_RUN_LIMIT = 5


class FailureGroup(BaseModel):
    """One aggregated failure mode across N recent runs.

    Groups are keyed by ``(stage, error_type)`` so two different stages
    raising the same exception class show up as distinct rows — the
    operator's first action is "go look at the right stage's log".
    """

    stage: str = Field(..., description="Pipeline stage where the failure occurred.")
    error_type: str = Field(..., description="Exception class name from RunState.failures[].")
    count: int = Field(..., ge=1, description="Number of failures with this stage+error_type.")
    sample_message: str = Field(
        ...,
        description=(
            "First non-empty error_message seen in the group. Truncated at 500 "
            "chars to keep the wire payload bounded."
        ),
    )
    sample_puzzle_ids: list[str] = Field(
        default_factory=list,
        description=f"Up to {_SAMPLE_PUZZLE_LIMIT} item_ids from the group (most-recent runs first).",
    )
    affected_runs: list[str] = Field(
        default_factory=list,
        description=f"Up to {_SAMPLE_RUN_LIMIT} run_ids that contain at least one failure of this kind.",
    )


def summarize_failures(runs: list["RunState"]) -> list[FailureGroup]:
    """Aggregate ``RunState.failures[]`` across runs into grouped digest rows.

    Groups by ``(stage, error_type)``. Within a group, ``count`` is the total
    number of failure records, ``sample_message`` is the first non-empty one,
    ``sample_puzzle_ids`` keeps up to ``_SAMPLE_PUZZLE_LIMIT`` item ids in
    insertion order, and ``affected_runs`` keeps up to ``_SAMPLE_RUN_LIMIT``
    distinct run ids in insertion order. Result is sorted by count descending,
    then ``stage``+``error_type`` for stable output across calls.
    """
    buckets: OrderedDict[tuple[str, str], dict] = OrderedDict()
    for run in runs:
        for fail in run.failures:
            key = (fail.stage, fail.error_type)
            bucket = buckets.get(key)
            if bucket is None:
                bucket = {
                    "count": 0,
                    "sample_message": "",
                    "puzzle_ids": [],
                    "puzzle_id_set": set(),
                    "runs": [],
                    "run_set": set(),
                }
                buckets[key] = bucket
            bucket["count"] += 1
            if not bucket["sample_message"] and fail.error_message:
                bucket["sample_message"] = fail.error_message[:500]
            if (
                fail.item_id
                and fail.item_id not in bucket["puzzle_id_set"]
                and len(bucket["puzzle_ids"]) < _SAMPLE_PUZZLE_LIMIT
            ):
                bucket["puzzle_ids"].append(fail.item_id)
                bucket["puzzle_id_set"].add(fail.item_id)
            if (
                run.run_id not in bucket["run_set"]
                and len(bucket["runs"]) < _SAMPLE_RUN_LIMIT
            ):
                bucket["runs"].append(run.run_id)
                bucket["run_set"].add(run.run_id)

    groups = [
        FailureGroup(
            stage=stage,
            error_type=err,
            count=b["count"],
            sample_message=b["sample_message"],
            sample_puzzle_ids=b["puzzle_ids"],
            affected_runs=b["runs"],
        )
        for (stage, err), b in buckets.items()
    ]
    groups.sort(key=lambda g: (-g.count, g.stage, g.error_type))
    return groups
