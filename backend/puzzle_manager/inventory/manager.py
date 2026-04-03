"""
Inventory Manager for Puzzle Collection Statistics.

This module provides the InventoryManager class for managing the puzzle
collection inventory file, including loading, saving, and updating statistics.

Uses atomic writes (tempfile + os.replace) for data integrity.
Uses advisory file locking (filelock) for concurrent access protection.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from filelock import FileLock

from backend.puzzle_manager.inventory.models import (
    AuditMetrics,
    CollectionStats,
    ComputedMetrics,
    InventoryUpdate,
    PuzzleCollectionInventory,
    StagesStats,
)
from backend.puzzle_manager.paths import get_ops_dir, get_project_root

logger = logging.getLogger(__name__)

# Constants
# Spec 107: Renamed from puzzle-collection-inventory.json
INVENTORY_FILENAME: Final[str] = "inventory.json"
# Spec 107: Moved to .puzzle-inventory-state/ directory
OPS_DIR: Final[str] = ".puzzle-inventory-state"
INVENTORY_DIR: Final[str] = "yengo-puzzle-collections"
CONFIG_DIR: Final[str] = "config"
SCHEMA_FILENAME: Final[str] = "puzzle-collection-inventory-schema.json"
LEVELS_FILENAME: Final[str] = "puzzle-levels.json"
QUALITY_FILENAME: Final[str] = "puzzle-quality.json"


def get_inventory_path(base_path: Path | None = None) -> Path:
    """Get the path to the inventory file.

    Args:
        base_path: Optional base path. Defaults to project root.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/inventory.json

    Spec 107: Inventory moved to ops dir for clear separation from content.
    """
    if base_path is not None:
        # For tests, use the provided base path directly
        return base_path / OPS_DIR / INVENTORY_FILENAME

    # Default: use the ops dir helper
    return get_ops_dir() / INVENTORY_FILENAME


def get_config_path(base_path: Path | None = None) -> Path:
    """Get the path to the config directory.

    Args:
        base_path: Optional base path. Defaults to project root.

    Returns:
        Path to config/ directory
    """
    root = base_path or get_project_root()
    return root / CONFIG_DIR


def load_level_slugs(config_path: Path | None = None) -> list[str]:
    """Load valid level slugs from puzzle-levels.json.

    Args:
        config_path: Optional path to config directory.

    Returns:
        List of valid level slugs in order.
    """
    config_dir = config_path or get_config_path()
    levels_file = config_dir / LEVELS_FILENAME

    with open(levels_file, encoding="utf-8") as f:
        config = json.load(f)

    return [level["slug"] for level in config["levels"]]


def load_quality_levels(config_path: Path | None = None) -> dict[str, str]:
    """Load quality level display names from puzzle-quality.json.

    Args:
        config_path: Optional path to config directory.

    Returns:
        Dict mapping quality level ("1"-"5") to display label.
    """
    config_dir = config_path or get_config_path()
    quality_file = config_dir / QUALITY_FILENAME

    with open(quality_file, encoding="utf-8") as f:
        config = json.load(f)

    # Map level key to display_label (levels is a dict with "1"-"5" keys)
    levels = config.get("levels", {})
    return {
        level_key: level_data.get("display_label", f"Level {level_key}")
        for level_key, level_data in levels.items()
    }


class InventoryManager:
    """
    Manages the puzzle collection inventory file.

    Provides methods for loading, saving, incrementing, and decrementing
    inventory statistics with atomic writes and file locking.
    """

    def __init__(
        self,
        inventory_path: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        """Initialize the InventoryManager.

        Args:
            inventory_path: Path to inventory file. Defaults to project root location.
            config_path: Path to config directory. Defaults to project root location.
        """
        self._inventory_path = inventory_path or get_inventory_path()
        self._config_path = config_path or get_config_path()
        self._lock_path = self._inventory_path.with_suffix(".lock")
        self._lock = FileLock(str(self._lock_path), timeout=30)
        self._inventory: PuzzleCollectionInventory | None = None
        self._level_slugs: list[str] | None = None

    @property
    def inventory_path(self) -> Path:
        """Get the path to the inventory file."""
        return self._inventory_path

    @property
    def level_slugs(self) -> list[str]:
        """Get valid level slugs, loading from config if needed."""
        if self._level_slugs is None:
            self._level_slugs = load_level_slugs(self._config_path)
        return self._level_slugs

    def exists(self) -> bool:
        """Check if the inventory file exists."""
        return self._inventory_path.exists()

    def load(self) -> PuzzleCollectionInventory:
        """Load inventory from file with file locking.

        Returns:
            PuzzleCollectionInventory instance.

        Raises:
            FileNotFoundError: If inventory file does not exist.
            json.JSONDecodeError: If file contains invalid JSON.
            ValidationError: If data fails Pydantic validation.
        """
        with self._lock:
            logger.debug("Loading inventory from %s", self._inventory_path)
            with open(self._inventory_path, encoding="utf-8") as f:
                data = json.load(f)

            self._inventory = PuzzleCollectionInventory.model_validate(data)
            return self._inventory

    def save(self, inventory: PuzzleCollectionInventory) -> None:
        """Save inventory to file atomically with file locking.

        Uses tempfile + os.replace pattern for atomic writes.
        Acquires file lock before write, releases after.

        Args:
            inventory: PuzzleCollectionInventory to save.
        """
        with self._lock:
            # Ensure directory exists
            self._inventory_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self._inventory_path.parent,
                delete=False,
                suffix=".tmp",
                encoding="utf-8",
            ) as f:
                json.dump(
                    inventory.model_dump(mode="json"),
                    f,
                    indent=2,
                    default=str,
                )
                temp_path = f.name

            # Atomic rename (works on POSIX and Windows NTFS)
            os.replace(temp_path, self._inventory_path)
            logger.debug("Saved inventory to %s", self._inventory_path)

            self._inventory = inventory

    def create_empty(self, run_id: str) -> PuzzleCollectionInventory:
        """Create a new empty inventory with all levels initialized to 0.

        Args:
            run_id: Run ID for the last_run_id field.

        Returns:
            New PuzzleCollectionInventory with defaults.
        """
        # Initialize by_puzzle_level with all valid levels at 0
        by_puzzle_level = dict.fromkeys(self.level_slugs, 0)

        # Initialize by_puzzle_quality with all quality levels (1-5) at 0
        by_puzzle_quality = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

        now = datetime.now(UTC)

        inventory = PuzzleCollectionInventory(
            schema_version="2.0",  # Current version with by_puzzle_quality
            collection=CollectionStats(
                by_puzzle_level=by_puzzle_level,
                by_puzzle_quality=by_puzzle_quality,
            ),
            stages=StagesStats(),
            metrics=ComputedMetrics(),
            audit=AuditMetrics(),
            last_updated=now,
            last_run_id=run_id,
        )

        logger.info("Created empty inventory with run_id=%s", run_id)
        return inventory

    def load_or_create(self, run_id: str) -> PuzzleCollectionInventory:
        """Load existing inventory or create new empty one.

        Args:
            run_id: Run ID for new inventory if created.

        Returns:
            PuzzleCollectionInventory (existing or new).
        """
        if self.exists():
            try:
                return self.load()
            except json.JSONDecodeError:
                logger.warning(
                    "Inventory file exists but is invalid/empty (JSON decode error). Recreating."
                )
                # Fall through to creation

        logger.info("Inventory file not found or invalid, creating new empty inventory")
        inventory = self.create_empty(run_id)
        self.save(inventory)
        return inventory

    def increment(
        self,
        update: InventoryUpdate,
        run_id: str,
    ) -> PuzzleCollectionInventory:
        """Apply an increment update to the inventory.

        Loads current inventory, applies update, saves atomically.

        Args:
            update: InventoryUpdate with increments to apply.
            run_id: Run ID for last_run_id field.

        Returns:
            Updated PuzzleCollectionInventory.
        """
        inventory = self.load_or_create(run_id)

        # Apply update to collection stats
        new_collection = update.apply_to(inventory.collection)

        # Update stages.publish.new
        new_stages = StagesStats(
            ingest=inventory.stages.ingest,
            analyze=inventory.stages.analyze,
            publish=inventory.stages.publish.model_copy(
                update={"new": inventory.stages.publish.new + update.puzzles_added}
            ),
        )

        # Compute error rates
        new_metrics = self._compute_metrics(new_stages, inventory.metrics)

        # Create updated inventory
        updated = inventory.model_copy(
            update={
                "collection": new_collection,
                "stages": new_stages,
                "metrics": new_metrics,
                "last_updated": datetime.now(UTC),
                "last_run_id": run_id,
            }
        )

        self.save(updated)
        logger.info(
            "Incremented inventory: +%d puzzles, total=%d",
            update.puzzles_added,
            updated.collection.total_puzzles,
        )
        return updated

    def decrement(
        self,
        puzzles_removed: int,
        level_decrements: dict[str, int],
        tag_decrements: dict[str, int],
        run_id: str,
        quality_decrements: dict[str, int] | None = None,
    ) -> PuzzleCollectionInventory:
        """Decrement inventory counts (for rollback).

        Floors all counts at zero to prevent negative values.
        Spec 102: Supports quality_decrements for by_puzzle_quality.

        Args:
            puzzles_removed: Number of puzzles to remove from total.
            level_decrements: Level -> count to decrement.
            tag_decrements: Tag -> count to decrement.
            run_id: Run ID for last_run_id field.
            quality_decrements: Quality level (1-5) -> count to decrement.

        Returns:
            Updated PuzzleCollectionInventory.
        """
        inventory = self.load_or_create(run_id)

        # Floor at zero for total
        new_total = max(0, inventory.collection.total_puzzles - puzzles_removed)
        if new_total != inventory.collection.total_puzzles - puzzles_removed:
            logger.warning(
                "Decrement would result in negative total, flooring at 0. "
                "Current: %d, Decrement: %d",
                inventory.collection.total_puzzles,
                puzzles_removed,
            )

        # Update level counts with floor at zero
        new_by_puzzle_level = inventory.collection.by_puzzle_level.copy()
        for level, decrement in level_decrements.items():
            current = new_by_puzzle_level.get(level, 0)
            new_val = max(0, current - decrement)
            if new_val != current - decrement:
                logger.warning(
                    "Level %s decrement would result in negative, flooring at 0. "
                    "Current: %d, Decrement: %d",
                    level,
                    current,
                    decrement,
                )
            new_by_puzzle_level[level] = new_val

        # Update tag counts with floor at zero
        new_by_tag = inventory.collection.by_tag.copy()
        for tag, decrement in tag_decrements.items():
            current = new_by_tag.get(tag, 0)
            new_val = max(0, current - decrement)
            if new_val != current - decrement:
                logger.warning(
                    "Tag %s decrement would result in negative, flooring at 0. "
                    "Current: %d, Decrement: %d",
                    tag,
                    current,
                    decrement,
                )
            new_by_tag[tag] = new_val

        # Update quality counts with floor at zero (Spec 102, T024)
        new_by_puzzle_quality = inventory.collection.by_puzzle_quality.copy()
        if quality_decrements:
            for quality_level, decrement in quality_decrements.items():
                current = new_by_puzzle_quality.get(quality_level, 0)
                new_val = max(0, current - decrement)
                if new_val != current - decrement:
                    logger.warning(
                        "Quality %s decrement would result in negative, flooring at 0. "
                        "Current: %d, Decrement: %d",
                        quality_level,
                        current,
                        decrement,
                    )
                new_by_puzzle_quality[quality_level] = new_val

        new_collection = inventory.collection.model_copy(
            update={
                "total_puzzles": new_total,
                "by_puzzle_level": new_by_puzzle_level,
                "by_tag": new_by_tag,
                "by_puzzle_quality": new_by_puzzle_quality,
            }
        )

        # Create updated inventory
        updated = inventory.model_copy(
            update={
                "collection": new_collection,
                "last_updated": datetime.now(UTC),
                "last_run_id": run_id,
            }
        )

        self.save(updated)
        logger.info(
            "Decremented inventory: -%d puzzles, total=%d",
            puzzles_removed,
            updated.collection.total_puzzles,
        )
        return updated

    def increment_rollback_audit(self, run_id: str) -> PuzzleCollectionInventory:
        """Increment rollback audit counter.

        Args:
            run_id: Run ID for last_run_id field.

        Returns:
            Updated PuzzleCollectionInventory.
        """
        inventory = self.load_or_create(run_id)

        now = datetime.now(UTC)
        new_audit = AuditMetrics(
            total_rollbacks=inventory.audit.total_rollbacks + 1,
            last_rollback_date=now,
        )

        updated = inventory.model_copy(
            update={
                "audit": new_audit,
                "last_updated": now,
                "last_run_id": run_id,
            }
        )

        self.save(updated)
        logger.info(
            "Incremented rollback audit: total_rollbacks=%d",
            updated.audit.total_rollbacks,
        )
        return updated

    def update_stage_metrics(
        self,
        stage: str,
        metrics: dict[str, int],
        run_id: str,
    ) -> PuzzleCollectionInventory:
        """Update stage-level metrics.

        Args:
            stage: Stage name ('ingest', 'analyze', 'publish').
            metrics: Metrics to update for the stage.
            run_id: Run ID for last_run_id field.

        Returns:
            Updated PuzzleCollectionInventory.
        """
        inventory = self.load_or_create(run_id)

        new_stages = inventory.stages.model_copy()

        if stage == "ingest":
            current = new_stages.ingest
            new_stages = new_stages.model_copy(
                update={
                    "ingest": current.model_copy(
                        update={
                            "attempted": current.attempted + metrics.get("attempted", 0),
                            "passed": current.passed + metrics.get("passed", 0),
                            "failed": current.failed + metrics.get("failed", 0),
                        }
                    )
                }
            )
        elif stage == "analyze":
            current = new_stages.analyze
            new_stages = new_stages.model_copy(
                update={
                    "analyze": current.model_copy(
                        update={
                            "enriched": current.enriched + metrics.get("enriched", 0),
                            "skipped": current.skipped + metrics.get("skipped", 0),
                        }
                    )
                }
            )
        elif stage == "publish":
            current = new_stages.publish
            new_stages = new_stages.model_copy(
                update={
                    "publish": current.model_copy(
                        update={
                            "new": current.new + metrics.get("new", 0),
                            "failed": current.failed + metrics.get("failed", 0),
                        }
                    )
                }
            )

        # Recompute error rates
        new_computed = self._compute_metrics(new_stages, inventory.metrics)

        # Update daily_publish_throughput with per-run count for publish stage
        if stage == "publish":
            new_computed = new_computed.model_copy(
                update={"daily_publish_throughput": metrics.get("new", 0)}
            )

        updated = inventory.model_copy(
            update={
                "stages": new_stages,
                "metrics": new_computed,
                "last_updated": datetime.now(UTC),
                "last_run_id": run_id,
            }
        )

        self.save(updated)
        logger.debug("Updated %s stage metrics", stage)
        return updated

    def _compute_metrics(
        self,
        stages: StagesStats,
        current_metrics: ComputedMetrics,
    ) -> ComputedMetrics:
        """Compute derived metrics from stage statistics.

        Args:
            stages: Current stage statistics.
            current_metrics: Current computed metrics (for daily_publish_throughput).

        Returns:
            Updated ComputedMetrics.
        """
        # Compute ingest error rate
        error_rate_ingest = 0.0
        if stages.ingest.attempted > 0:
            error_rate_ingest = round(
                stages.ingest.failed / stages.ingest.attempted,
                4,
            )

        # Publish error rate
        error_rate_publish = 0.0
        total_publish = stages.publish.new + stages.publish.failed
        if total_publish > 0:
            error_rate_publish = round(
                stages.publish.failed / total_publish,
                4,
            )

        return ComputedMetrics(
            daily_publish_throughput=current_metrics.daily_publish_throughput,
            error_rate_ingest=error_rate_ingest,
            error_rate_publish=error_rate_publish,
        )

    def validate_levels(self, by_puzzle_level: dict[str, int]) -> list[str]:
        """Validate level keys against puzzle-levels.json.

        Args:
            by_puzzle_level: Dictionary of level -> count.

        Returns:
            List of validation errors (empty if valid).
        """
        valid_slugs = set(self.level_slugs)
        errors = []

        for level in by_puzzle_level:
            if level not in valid_slugs:
                errors.append(f"Unknown level slug: {level}")

        return errors
