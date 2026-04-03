"""
Adapter module for puzzle sources.

Provides BaseAdapter protocol and adapter registry for plugin-based source integration.

Directory Structure:
    adapters/
    ├── _base.py          # BaseAdapter and ResumableAdapter protocols
    ├── _registry.py      # Adapter registration and discovery
    ├── __init__.py       # This file
    ├── {adapter_name}/   # Adapter packages follow same pattern
    │   ├── __init__.py
    │   └── adapter.py
    ...
"""

from backend.puzzle_manager.adapters._base import BaseAdapter, FetchResult, ResumableAdapter
from backend.puzzle_manager.adapters._registry import (
    create_adapter,
    discover_adapters,
    get_adapter,
    list_adapters,
    register_adapter,
)
from backend.puzzle_manager.adapters.kisvadim import KisvadimAdapter

# Import all adapter implementations to register them
from backend.puzzle_manager.adapters.local import LocalAdapter
from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter
from backend.puzzle_manager.adapters.travisgk import TravisGKAdapter

__all__ = [
    # Protocols
    "BaseAdapter",
    "ResumableAdapter",
    "FetchResult",
    # Registry functions
    "register_adapter",
    "get_adapter",
    "list_adapters",
    "discover_adapters",
    "create_adapter",
    # Adapter implementations
    "LocalAdapter",
    "SanderlandAdapter",
    "TravisGKAdapter",
    "KisvadimAdapter",
]
