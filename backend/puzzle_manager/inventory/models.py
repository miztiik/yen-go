"""
Pydantic models for Puzzle Collection Inventory.

Matches config/schemas/puzzle-collection-inventory-schema.json.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestMetrics(BaseModel):
    """Metrics for the INGEST stage."""

    attempted: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class AnalyzeMetrics(BaseModel):
    """Metrics for the ANALYZE stage."""

    enriched: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)


class PublishMetrics(BaseModel):
    """Metrics for the PUBLISH stage."""

    new: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class StagesStats(BaseModel):
    """Aggregate metrics across all pipeline stages."""

    ingest: IngestMetrics = Field(default_factory=IngestMetrics)
    analyze: AnalyzeMetrics = Field(default_factory=AnalyzeMetrics)
    publish: PublishMetrics = Field(default_factory=PublishMetrics)


class ComputedMetrics(BaseModel):
    """Computed metrics derived from stage statistics."""

    daily_publish_throughput: int = Field(default=0, ge=0)
    error_rate_ingest: float = Field(default=0.0, ge=0.0, le=1.0)
    error_rate_publish: float = Field(default=0.0, ge=0.0, le=1.0)


class AuditMetrics(BaseModel):
    """Audit metrics tracking rollback operations."""

    total_rollbacks: int = Field(default=0, ge=0)
    last_rollback_date: datetime | None = Field(default=None)


class CollectionStats(BaseModel):
    """
    Aggregate statistics for the puzzle collection.

    - total_puzzles: Count of all published puzzles
    - by_puzzle_level: Breakdown by difficulty level (slug -> count)
    - by_tag: Breakdown by technique tag (tag -> count)
    - by_puzzle_quality: Breakdown by quality level ("1"-"5" -> count)
      Quality levels from config/puzzle-quality.json:
        "1" = Unverified (no solution tree validation)
        "2" = Basic (minimal validation)
        "3" = Standard (verified solution tree)
        "4" = High (human reviewed)
        "5" = Premium (professional curated)
    """

    total_puzzles: int = Field(
        default=0,
        ge=0,
        description="Total number of published puzzles",
    )
    by_puzzle_level: dict[str, int] = Field(
        default_factory=dict,
        description="Puzzle count per level slug (from puzzle-levels.json)",
    )
    by_tag: dict[str, int] = Field(
        default_factory=dict,
        description="Puzzle count per tag (puzzles with multiple tags counted in each)",
    )
    by_puzzle_quality: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Puzzle count per quality level (1=Unverified through 5=Premium)",
    )


class PuzzleCollectionInventory(BaseModel):
    """Root model for inventory.json."""

    schema_version: str = Field(
        default="2.0",
        description="Schema version for migration support",
    )
    collection: CollectionStats = Field(
        default_factory=CollectionStats,
        description="Aggregate collection statistics",
    )
    stages: StagesStats = Field(
        default_factory=StagesStats,
        description="Aggregate metrics across pipeline stages",
    )
    metrics: ComputedMetrics = Field(
        default_factory=ComputedMetrics,
        description="Computed metrics derived from stage statistics",
    )
    audit: AuditMetrics = Field(
        default_factory=AuditMetrics,
        description="Audit metrics tracking rollback operations",
    )
    last_updated: datetime = Field(
        description="ISO 8601 timestamp of last update",
    )
    last_run_id: str = Field(
        description="Run ID of the operation that last modified this file",
    )


class InventoryUpdate(BaseModel):
    """
    Represents an incremental update to apply to the inventory.

    Used by publish stage to batch updates before atomic write.
    """

    puzzles_added: int = Field(default=0, ge=0)
    level_increments: dict[str, int] = Field(default_factory=dict)
    tag_increments: dict[str, int] = Field(default_factory=dict)
    quality_increments: dict[str, int] = Field(
        default_factory=dict,
        description="Quality level increments (key '1'-'5', value count)",
    )

    def apply_to(self, stats: CollectionStats) -> CollectionStats:
        """Apply this update to collection stats, returning new stats."""
        new_total = stats.total_puzzles + self.puzzles_added

        # Update level counts
        new_by_puzzle_level = stats.by_puzzle_level.copy()
        for level, count in self.level_increments.items():
            new_by_puzzle_level[level] = new_by_puzzle_level.get(level, 0) + count

        # Update tag counts
        new_by_tag = stats.by_tag.copy()
        for tag, count in self.tag_increments.items():
            new_by_tag[tag] = new_by_tag.get(tag, 0) + count

        # Update quality breakdown
        new_by_puzzle_quality = stats.by_puzzle_quality.copy()
        for quality_level, count in self.quality_increments.items():
            new_by_puzzle_quality[quality_level] = (
                new_by_puzzle_quality.get(quality_level, 0) + count
            )

        return CollectionStats(
            total_puzzles=new_total,
            by_puzzle_level=new_by_puzzle_level,
            by_tag=new_by_tag,
            by_puzzle_quality=new_by_puzzle_quality,
        )
