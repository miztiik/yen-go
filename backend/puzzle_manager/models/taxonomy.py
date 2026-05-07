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
