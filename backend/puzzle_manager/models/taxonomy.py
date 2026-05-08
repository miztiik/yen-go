"""Theme 5: read-only taxonomy inspection shapes.

`tags list --with-usage --json` and `levels list --with-usage --json`
return arrays of these entries. Both are validated by Pydantic so the
dashboard receives a stable contract.

`first_seen_run` / `last_seen_run` are reserved for a future enhancement
that scans the publish log; today they are emitted as ``None``. The
schema slot exists so future producers can fill it without a contract
change.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TagUsageEntry(BaseModel):
    tag: str = Field(description="Tag slug (canonical form).")
    name: str = Field(description="Human display name.")
    category: str = Field(description="Tag category from config (objective | tesuji | technique).")
    usage_count: int = Field(ge=0, description="Number of published puzzles carrying this tag.")
    aliases: list[str] = Field(default_factory=list, description="Known input aliases.")
    first_seen_run: str | None = Field(default=None, description="Reserved.")
    last_seen_run: str | None = Field(default=None, description="Reserved.")


class LevelUsageEntry(BaseModel):
    level: str = Field(description="Level slug (canonical form).")
    name: str = Field(description="Human display name.")
    id: int = Field(description="Numeric level id (110-230).")
    rank_min: str | None = Field(default=None, description="Lower rank bound (e.g. '20k').")
    rank_max: str | None = Field(default=None, description="Upper rank bound (e.g. '16k').")
    usage_count: int = Field(ge=0, description="Number of published puzzles at this level.")
    first_seen_run: str | None = Field(default=None, description="Reserved.")
    last_seen_run: str | None = Field(default=None, description="Reserved.")


class TaxonomyMutationPreview(BaseModel):
    """Theme 11: preview shape for ``tags rename | tags merge | levels rename``.

    All three mutation kinds produce the same shape so the cockpit can render
    them with one component. The CLI reports what *would* change without
    touching anything on disk; the apply path lands in a follow-up slice.
    """

    op: str = Field(description="Operation kind: tags-rename | tags-merge | levels-rename.")
    dry_run: bool = Field(description="Always true in V1 (apply path not yet implemented).")
    valid: bool = Field(description="True iff the proposed mutation passes pre-flight validation.")
    errors: list[str] = Field(default_factory=list, description="Validation failures.")
    sources: list[str] = Field(description="Source slugs the mutation would affect.")
    target: str = Field(description="Destination slug after rename / merge.")
    affected_puzzle_count: int = Field(ge=0, description="Sum of usage counts across sources.")
    config_changes: dict = Field(
        default_factory=dict,
        description="Summary of config edits the apply path would perform.",
    )
