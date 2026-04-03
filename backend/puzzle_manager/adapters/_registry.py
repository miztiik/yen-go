"""
Adapter registry with plugin-based discovery.

Provides decorator-based registration and auto-discovery of adapters.
Supports both flat files (adapter_name.py) and subdirectories (adapter_name/adapter.py).
"""

import importlib
import logging
import pkgutil
from pathlib import Path

from backend.puzzle_manager.adapters._base import BaseAdapter
from backend.puzzle_manager.exceptions import AdapterNotFoundError

logger = logging.getLogger("puzzle_manager.adapters")

# Global registry of adapter classes
_adapters: dict[str, type[BaseAdapter]] = {}


def register_adapter(name: str):
    """Decorator to register an adapter class.

    Usage:
        @register_adapter("my-adapter")
        class MyAdapter:
            ...

    Args:
        name: Unique adapter identifier.

    Returns:
        Decorator function.
    """
    def decorator(cls: type[BaseAdapter]) -> type[BaseAdapter]:
        if name in _adapters:
            logger.warning(f"Overwriting adapter registration: {name}")
        _adapters[name] = cls
        logger.debug(f"Registered adapter: {name}")
        return cls

    return decorator


def get_adapter(name: str) -> type[BaseAdapter]:
    """Get adapter class by name.

    Args:
        name: Adapter identifier.

    Returns:
        Adapter class (not instance).

    Raises:
        AdapterNotFoundError: If adapter not found.
    """
    # Ensure adapters are discovered
    discover_adapters()

    if name not in _adapters:
        available = ", ".join(sorted(_adapters.keys())) or "none"
        raise AdapterNotFoundError(
            f"Unknown adapter: {name}. Available: {available}",
            context={"adapter": name, "available": list(_adapters.keys())},
        )

    return _adapters[name]


def create_adapter(name: str, config: dict | None = None) -> BaseAdapter:
    """Create and configure an adapter instance.

    Args:
        name: Adapter identifier.
        config: Configuration dictionary.

    Returns:
        Configured adapter instance.
    """
    adapter_cls = get_adapter(name)
    adapter = adapter_cls()
    if config:
        adapter.configure(config)
    return adapter


def list_adapters() -> list[str]:
    """Get list of registered adapter names.

    Returns:
        Sorted list of adapter identifiers.
    """
    discover_adapters()
    return sorted(_adapters.keys())


def is_registered(name: str) -> bool:
    """Check if an adapter is registered.

    Args:
        name: Adapter identifier.

    Returns:
        True if adapter is registered.
    """
    discover_adapters()
    return name in _adapters


_discovered = False


def discover_adapters() -> None:
    """Auto-import all adapter modules to trigger registration.

    This finds and imports adapters from:
    1. Flat files: adapters/{name}.py (legacy, deprecated)
    2. Subdirectories: adapters/{name}/adapter.py (preferred)

    Non-adapter modules (starting with underscore: _base.py, _registry.py) are skipped.

    Discovery is intentionally quiet to avoid routine startup log noise.
    """
    global _discovered

    if _discovered:
        return

    try:
        from backend.puzzle_manager import adapters

        adapters_path = Path(adapters.__path__[0])

        for _, name, is_pkg in pkgutil.iter_modules(adapters.__path__):
            # Skip internal modules (underscore prefix) and __init__
            if name.startswith("_") or name == "__init__":
                continue

            try:
                if is_pkg:
                    # Subdirectory: import {name}/adapter.py
                    adapter_module = adapters_path / name / "adapter.py"
                    if adapter_module.exists():
                        importlib.import_module(f"backend.puzzle_manager.adapters.{name}.adapter")
                    else:
                        # Try importing the package's __init__.py
                        importlib.import_module(f"backend.puzzle_manager.adapters.{name}")
                else:
                    # Flat file: import {name}.py (legacy)
                    importlib.import_module(f"backend.puzzle_manager.adapters.{name}")
            except Exception as e:
                logger.warning(f"Failed to import adapter {name}: {e}")

        _discovered = True

    except Exception as e:
        logger.warning(f"Adapter discovery failed: {e}")


def reset_registry() -> None:
    """Reset the adapter registry.

    Useful for testing.
    """
    global _discovered
    _adapters.clear()
    _discovered = False
