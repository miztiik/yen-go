"""
Configuration loader for the puzzle manager.

Loads and validates configuration from JSON files with auto-creation of defaults.
"""

import json
import logging
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.puzzle_manager.exceptions import (
    ConfigFileNotFoundError,
    ConfigurationError,
    ConfigValidationError,
)
from backend.puzzle_manager.models.config import (
    PipelineConfig,
    SourceConfig,
)
from backend.puzzle_manager.paths import get_config_dir, get_global_config_dir

logger = logging.getLogger("puzzle_manager.config")


# Default configuration content for auto-creation
DEFAULT_PIPELINE_CONFIG = {
    "version": "1.0",
    "batch": {"size": 2000, "max_files_per_dir": 2000},
    "retention": {"logs_days": 45, "state_days": 45, "failed_files_days": 45},
    "daily": {
        "standard_puzzle_count": 30,
        "timed_set_count": 3,
        "timed_puzzles_per_set": 50,
        "tag_puzzle_count": 50,
        "level_weights": {
            "novice": 0.35,
            "beginner": 0.30,
            "elementary": 0.20,
            "intermediate": 0.15,
        },
        "target_levels": [1, 2, 3, 4],
    },
    "output": {
        "root": "yengo-puzzle-collections",
        "sgf_path": "sgf/{batch}",
    },
}

DEFAULT_SOURCES_CONFIG = {
    "active_adapter": "local-imports",
    "sources": [
        {
            "id": "local-imports",
            "name": "Local Imports",
            "adapter": "local",
            "config": {
                "path": "external-sources/manual-imports",
                "include_folders": [],
                "exclude_folders": [],
                "resume": False,
                "validate": True,
                "move_processed_to": None
            },
        }
    ]
}


class ConfigLoader:
    """Loader for puzzle manager configuration files."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize config loader.

        Args:
            config_dir: Configuration directory. Uses default if not specified.
        """
        self.config_dir = config_dir or get_config_dir()

    def _ensure_config_exists(self, filename: str, default_content: dict[str, Any]) -> Path:
        """Ensure config file exists, creating with defaults if needed.

        Args:
            filename: Config filename.
            default_content: Default content to write if file doesn't exist.

        Returns:
            Path to config file.
        """
        config_path = self.config_dir / filename

        if not config_path.exists():
            logger.warning(
                f"Config file not found, creating with defaults: {config_path}"
            )
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=2)

        return config_path

    def _load_json(self, filename: str, default_content: dict[str, Any] | None = None) -> dict[str, Any]:
        """Load JSON config file.

        Args:
            filename: Config filename.
            default_content: Default content for auto-creation.

        Returns:
            Parsed JSON content.

        Raises:
            ConfigFileNotFoundError: If file doesn't exist and no default provided.
            ConfigurationError: If JSON is invalid.
        """
        config_path = self.config_dir / filename

        if not config_path.exists():
            if default_content is not None:
                config_path = self._ensure_config_exists(filename, default_content)
            else:
                raise ConfigFileNotFoundError(
                    f"Config file not found: {config_path}",
                    context={"path": str(config_path)},
                )

        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in {filename}: {e}",
                context={"path": str(config_path), "error": str(e)},
            ) from e

    def load_pipeline_config(self) -> PipelineConfig:
        """Load pipeline configuration.

        Returns:
            Validated PipelineConfig.

        Raises:
            ConfigValidationError: If validation fails.
        """
        data = self._load_json("pipeline.json", DEFAULT_PIPELINE_CONFIG)

        try:
            return PipelineConfig.model_validate(data)
        except Exception as e:
            raise ConfigValidationError(
                f"Invalid pipeline config: {e}",
                context={"error": str(e)},
            ) from e

    def load_sources(self) -> list[SourceConfig]:
        """Load source configurations.

        Returns:
            List of validated SourceConfig objects.

        Raises:
            ConfigValidationError: If validation fails.
        """
        data = self._load_json("sources.json", DEFAULT_SOURCES_CONFIG)

        try:
            sources = []
            for source_data in data.get("sources", []):
                sources.append(SourceConfig.model_validate(source_data))
            return sources
        except Exception as e:
            raise ConfigValidationError(
                f"Invalid sources config: {e}",
                context={"error": str(e)},
            ) from e

    def load_tags(self) -> dict[str, Any]:
        """Load tags configuration from global config/tags.json.

        Note: Tags are loaded from the GLOBAL config directory (project root/config/)
        as tags.json is the single source of truth shared across frontend and backend.

        Returns:
            Tags configuration dictionary.
        """
        global_tags_path = get_global_config_dir() / "tags.json"
        if not global_tags_path.exists():
            raise ConfigFileNotFoundError(
                f"Global tags.json not found at {global_tags_path}",
                context={"path": str(global_tags_path)},
            )

        with open(global_tags_path, encoding="utf-8") as f:
            return json.load(f)

    def load_levels(self) -> dict[str, Any]:
        """Load levels configuration from global config.

        Returns:
            Levels configuration dictionary.
        """
        global_levels_path = get_global_config_dir() / "puzzle-levels.json"
        if not global_levels_path.exists():
            raise ConfigFileNotFoundError(
                f"Global puzzle-levels.json not found at {global_levels_path}",
                context={"path": str(global_levels_path)},
            )

        with open(global_levels_path, encoding="utf-8") as f:
            return json.load(f)

    def get_active_adapter(self) -> str:
        """Get the ID of the currently active adapter.

        The active adapter is specified by the `active_adapter` key in sources.json.
        This is the default adapter used when --source is not specified in CLI commands.

        Returns:
            Adapter ID string (e.g., "ogs", "sanderland", "goproblems").

        Raises:
            ConfigValidationError: If active_adapter is not set or doesn't match any source.
        """
        data = self._load_json("sources.json", DEFAULT_SOURCES_CONFIG)

        active_adapter = data.get("active_adapter")
        if not active_adapter:
            raise ConfigValidationError(
                "No active_adapter specified in sources.json",
                context={"hint": "Add 'active_adapter' key to sources.json"},
            )

        # Validate that active_adapter matches a source ID
        source_ids = [s.get("id") for s in data.get("sources", [])]
        if active_adapter not in source_ids:
            raise ConfigValidationError(
                f"active_adapter '{active_adapter}' not found in sources",
                context={"valid_sources": source_ids},
            )

        return active_adapter

    def get_source_config(self, source_id: str) -> SourceConfig:
        """Get configuration for a specific source by ID.

        Args:
            source_id: The source ID to look up (e.g., "ogs", "sanderland").

        Returns:
            SourceConfig for the specified source.

        Raises:
            ConfigValidationError: If source_id is not found in sources.json.
        """
        sources = self.load_sources()

        for source in sources:
            if source.id == source_id:
                return source

        valid_ids = [s.id for s in sources]
        raise ConfigValidationError(
            f"Source '{source_id}' not found in sources.json",
            context={"valid_sources": valid_ids},
        )

    def get_available_sources(self) -> list[str]:
        """Get list of available source IDs.

        Returns:
            List of source ID strings from sources.json.
        """
        data = self._load_json("sources.json", DEFAULT_SOURCES_CONFIG)
        return [s.get("id") for s in data.get("sources", []) if s.get("id")]

    def get_tag_ids(self) -> list[str]:
        """Get list of approved tag IDs.

        Returns:
            List of tag ID strings.
        """
        tags_data = self.load_tags()
        # Global tags.json has tags as an object with tag IDs as keys
        tags_obj = tags_data.get("tags", {})
        if isinstance(tags_obj, dict):
            return list(tags_obj.keys())
        # Fallback for array format (legacy)
        return [tag["id"] for tag in tags_obj if isinstance(tag, dict)]

    def load_collections(self) -> dict[str, Any]:
        """Load collections configuration from global config/collections.json.

        Note: Collections are loaded from the GLOBAL config directory (project root/config/)
        as collections.json is the single source of truth shared across frontend and backend.

        Returns:
            Collections configuration dictionary with 'schema_version' and 'collections' keys.

        Raises:
            ConfigFileNotFoundError: If collections.json doesn't exist.
            ConfigurationError: If JSON is invalid.
        """
        global_collections_path = get_global_config_dir() / "collections.json"
        if not global_collections_path.exists():
            raise ConfigFileNotFoundError(
                f"Global collections.json not found at {global_collections_path}",
                context={"path": str(global_collections_path)},
            )

        with open(global_collections_path, encoding="utf-8") as f:
            return json.load(f)

    def get_collection_slugs(self) -> list[str]:
        """Get list of all valid collection slugs.

        Returns:
            List of collection slug strings.
        """
        data = self.load_collections()
        return [c["slug"] for c in data.get("collections", [])]

    def get_collection_aliases(self) -> dict[str, str]:
        """Build alias\u2192slug mapping from all collections.

        Returns a flat dictionary where:
        - Keys: alias strings (NFC-normalized, lowercased)
        - Values: parent collection slug

        Also includes each slug as a self-resolving entry.

        Returns:
            Dictionary mapping alias/slug \u2192 collection slug.

        Raises:
            ConfigValidationError: If any alias appears in more than one collection.
                Error message identifies both conflicting collections and the alias.
        """
        data = self.load_collections()
        alias_map: dict[str, str] = {}

        for c in data.get("collections", []):
            slug = c["slug"]
            # Add slug as self-resolving entry
            normalized_slug = unicodedata.normalize("NFC", slug).lower()
            alias_map[normalized_slug] = slug

            # Add declared aliases
            for alias in c.get("aliases", []):
                key = unicodedata.normalize("NFC", alias).lower()
                if key in alias_map and alias_map[key] != slug:
                    raise ConfigValidationError(
                        f"Alias '{alias}' conflicts: found in '{slug}' "
                        f"and '{alias_map[key]}'",
                        context={
                            "alias": alias,
                            "collection_1": alias_map[key],
                            "collection_2": slug,
                        },
                    )
                alias_map[key] = slug

        return alias_map

    def resolve_collection_alias(self, input_str: str) -> str | None:
        """Resolve an alias string to its collection slug.

        Args:
            input_str: Alias or slug to resolve.

        Returns:
            Collection slug if found, None otherwise.
            Slugs self-resolve (e.g., "gokyo-shumyo" \u2192 "gokyo-shumyo").
        """
        alias_map = self.get_collection_aliases()
        key = unicodedata.normalize("NFC", input_str).lower()
        return alias_map.get(key)
    def get_collection_level_hints(self) -> dict[str, str]:
        """Build slug→level_hint mapping from collections with level_hint field.

        Returns a flat dictionary where:
        - Keys: collection slug strings
        - Values: level slug strings (e.g., "novice", "intermediate")

        Only collections with a non-empty level_hint field are included.

        Returns:
            Dictionary mapping collection slug → level slug.
        """
        data = self.load_collections()
        level_hints: dict[str, str] = {}

        for c in data.get("collections", []):
            hint = c.get("level_hint")
            if hint:
                level_hints[c["slug"]] = hint

        return level_hints

class ConfigWriter:
    """Writer for puzzle manager configuration files (mutations only).

    Separated from ConfigLoader for Single Responsibility Principle compliance.
    ConfigLoader handles reading, ConfigWriter handles writing/mutations.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize config writer.

        Args:
            config_dir: Configuration directory. Uses default if not specified.
        """
        self.config_dir = config_dir or get_config_dir()

    def set_active_adapter(self, source_id: str | None, force: bool = False) -> bool:
        """Set the active adapter in sources.json.

        Updates the `active_adapter` field in sources.json to the specified source ID.
        If source_id is None or empty string, disables the active adapter.

        Args:
            source_id: The source ID to set as active (e.g., "ogs", "sanderland").
                      Pass None or "" to disable the active adapter.
            force: If True, bypass config_locked check (use with caution).

        Returns:
            True on success.

        Raises:
            ConfigValidationError: If source_id is not found in sources.json.
            ConfigurationError: If the config file cannot be written or is locked.
        """
        config_path = self.config_dir / "sources.json"

        # Load current config using ConfigLoader for validation
        loader = ConfigLoader(self.config_dir)
        data = loader._load_json("sources.json", DEFAULT_SOURCES_CONFIG)

        # Check if config is locked by a running pipeline
        from backend.puzzle_manager.pipeline.lock import check_pipeline_lock
        check_pipeline_lock(force=force)

        # Validate source_id exists (unless disabling)
        if source_id:
            source_ids = [s.get("id") for s in data.get("sources", [])]
            if source_id not in source_ids:
                raise ConfigValidationError(
                    f"Source '{source_id}' not found in sources.json",
                    context={"valid_sources": source_ids},
                )

        # Update active_adapter
        data["active_adapter"] = source_id if source_id else ""

        # Write back to file
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(
                f"Active adapter {'set to' if source_id else 'disabled:'} "
                f"{source_id or '(none)'}"
            )
            return True
        except OSError as e:
            raise ConfigurationError(
                f"Failed to write sources.json: {e}",
                context={"path": str(config_path), "error": str(e)},
            ) from e


@lru_cache(maxsize=1)
def get_config() -> PipelineConfig:
    """Get cached pipeline configuration.

    Returns:
        Validated PipelineConfig.
    """
    loader = ConfigLoader()
    return loader.load_pipeline_config()


def clear_config_cache() -> None:
    """Clear the cached configuration."""
    get_config.cache_clear()
