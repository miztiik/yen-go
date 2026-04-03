"""
Tag normalization for OGS puzzle types.

Maps OGS puzzle_type values to YenGo standard tags.
Ported from backend/puzzle_manager/adapters/ogs/adapter.py.

OGS puzzle types map to approved tags in config/tags.json v6.0:
- life_and_death → life-and-death
- tesuji → tesuji
- fuseki → fuseki (opening patterns)
- joseki → joseki (corner patterns)
- endgame → endgame (yose)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("ogs.tags")


# OGS puzzle_type to YenGo tag mapping
# All mapped tags MUST exist in config/tags.json v6.0
OGS_TYPE_TO_TAG = {
    "life_and_death": "life-and-death",
    "tesuji": "tesuji",
    "fuseki": "fuseki",
    "joseki": "joseki",
    "endgame": "endgame",
    # Fallbacks for edge cases
    "best_move": None,  # Too generic — let tagger detect
    "elementary": None,  # Not a technique
    "unknown": None,  # Unclassified
}


class TagMapper:
    """Maps OGS puzzle types to YenGo standard tags."""

    def __init__(self, tags_path: Path | None = None):
        """Initialize tag mapper.

        Args:
            tags_path: Path to tags.json. If None, uses default config location.
        """
        self._tags: dict[str, dict] = {}
        self._aliases: dict[str, str] = {}  # alias -> canonical tag

        if tags_path is None:
            tags_path = self._get_default_tags_path()

        self._load_tags(tags_path)

    def _get_default_tags_path(self) -> Path:
        """Get default path to tags.json."""
        # tools/ogs/tags.py -> config/tags.json
        return Path(__file__).parent.parent.parent / "config" / "tags.json"

    def _load_tags(self, tags_path: Path) -> None:
        """Load tags from tags.json."""
        if not tags_path.exists():
            logger.warning(f"Tags file not found: {tags_path}")
            return

        try:
            with open(tags_path, encoding="utf-8") as f:
                data = json.load(f)

            self._tags = data.get("tags", {})

            # Build alias lookup
            for tag_id, tag_data in self._tags.items():
                # Add the tag ID itself
                self._aliases[tag_id.lower()] = tag_id
                self._aliases[tag_id.replace("-", "_").lower()] = tag_id
                self._aliases[tag_id.replace("-", " ").lower()] = tag_id

                # Add aliases
                for alias in tag_data.get("aliases", []):
                    self._aliases[alias.lower()] = tag_id

            logger.debug(f"Loaded {len(self._tags)} tags with {len(self._aliases)} aliases")

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load tags.json: {e}")

    def map_puzzle_type(self, puzzle_type: str) -> str | None:
        """Map OGS puzzle_type to YenGo tag.

        Args:
            puzzle_type: OGS puzzle type (e.g., "life_and_death", "tesuji")

        Returns:
            YenGo tag ID (e.g., "life-and-death", "tesuji") or None if no match
        """
        if not puzzle_type:
            return None

        # First check explicit mapping
        if puzzle_type in OGS_TYPE_TO_TAG:
            return OGS_TYPE_TO_TAG[puzzle_type]

        # Fallback: convert underscores to hyphens (tesuji remains tesuji)
        normalized = puzzle_type.lower().replace("_", "-")

        # Verify it's a valid tag in our system
        if normalized in self._aliases or normalized.replace("-", "_") in self._aliases:
            return normalized

        return None

    def format_yt_property(self, tags: list[str]) -> str:
        """Format tags as SGF YT[] property.

        Args:
            tags: List of tag IDs

        Returns:
            SGF property string like "YT[tag1,tag2]" or empty string
        """
        if not tags:
            return ""

        # Sort and deduplicate
        unique_tags = sorted(set(tags))
        return f"YT[{','.join(unique_tags)}]"


# Global singleton instance
_mapper: TagMapper | None = None


def get_tag_mapper() -> TagMapper:
    """Get the global TagMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = TagMapper()
    return _mapper


def map_puzzle_type_to_tag(puzzle_type: str) -> str | None:
    """Convenience function to map puzzle type to tag.

    Args:
        puzzle_type: OGS puzzle type

    Returns:
        YenGo tag ID or None
    """
    return get_tag_mapper().map_puzzle_type(puzzle_type)
