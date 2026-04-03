"""
Schema version and schema loading utilities.

Provides YENGO_SGF_VERSION loaded from config/schemas/sgf-properties.schema.json.
This is the SINGLE SOURCE OF TRUTH for SGF schema version.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Final

from backend.puzzle_manager.paths import get_global_config_dir


def _get_sgf_schema_path() -> Path:
    """Get path to the SGF properties schema."""
    return get_global_config_dir() / "schemas" / "sgf-properties.schema.json"


@lru_cache(maxsize=1)
def _load_sgf_schema_version() -> int:
    """Load SGF schema version from JSON schema file.

    Returns:
        Integer version number from schema.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        KeyError: If version field is missing.
    """
    schema_path = _get_sgf_schema_path()
    if not schema_path.exists():
        raise FileNotFoundError(f"SGF schema not found: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    version = schema.get("schema_version")
    if version is None:
        raise KeyError("Schema missing 'schema_version' field")

    return int(version)


# Current SGF schema version - loaded from config/schemas/sgf-properties.schema.json
# This ensures Single Source of Truth (per T070, Spec 036)
def get_yengo_sgf_version() -> int:
    """Get current YenGo SGF schema version.

    Returns:
        Integer version number (e.g., 5).
    """
    return _load_sgf_schema_version()


# Single source of truth — derived from config/schemas/sgf-properties.schema.json
YENGO_SGF_VERSION: Final[int] = get_yengo_sgf_version()


def get_schema_path(schema_name: str) -> Path:
    """Get path to a schema file in the global config directory.

    Args:
        schema_name: Name of the schema (without .json extension).

    Returns:
        Path to the schema file.
    """
    return get_global_config_dir() / "schemas" / f"{schema_name}.json"


def load_schema(schema_name: str) -> dict:
    """Load a JSON schema.

    Args:
        schema_name: Name of the schema (without .json extension).

    Returns:
        Schema dictionary.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
    """
    schema_path = get_schema_path(schema_name)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)
