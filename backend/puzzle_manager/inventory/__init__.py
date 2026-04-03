"""
Puzzle Collection Inventory Module (v2.0).

Simplified rebuild-centric architecture. Stage metrics, computed metrics,
and audit trails removed from inventory model.

Main components:
- InventoryManager: Load, save, increment inventory data
- Models: Pydantic models for inventory structure
- CLI: Command-line interface for viewing/rebuilding inventory
"""

from backend.puzzle_manager.inventory.cli import (
    cmd_inventory,
    format_inventory_json,
    format_inventory_summary,
)
from backend.puzzle_manager.inventory.manager import InventoryManager
from backend.puzzle_manager.inventory.models import (
    CollectionStats,
    InventoryUpdate,
    PuzzleCollectionInventory,
)

__all__ = [
    # Core manager
    "InventoryManager",
    # CLI
    "cmd_inventory",
    "format_inventory_summary",
    "format_inventory_json",
    # Models
    "CollectionStats",
    "InventoryUpdate",
    "PuzzleCollectionInventory",
]
