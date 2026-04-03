"""
Kisvadim adapter for importing puzzles from kisvadim-goproblems collection.

Local collection adapter for pre-downloaded SGF files.
"""

import logging
from pathlib import Path

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import register_adapter
from backend.puzzle_manager.core.puzzle_validator import validate_sgf
from backend.puzzle_manager.paths import get_project_root, rel_path

logger = logging.getLogger("puzzle_manager.adapters.kisvadim")


@register_adapter("kisvadim")
class KisvadimAdapter:
    """Adapter for Kisvadim goproblems collection.

    Reads from external-sources/kisvadim-goproblems/ directory.
    """

    def __init__(
        self,
        source_dir: str | None = None,
        **kwargs,
    ):
        """Initialize adapter.

        Args:
            source_dir: Path to kisvadim collection (default: external-sources/kisvadim-goproblems)
            **kwargs: Additional config options
        """
        if source_dir:
            self.source_dir = Path(source_dir)
        else:
            self.source_dir = get_project_root() / "external-sources" / "kisvadim-goproblems"

        self._processed_ids: set[str] = set()

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        return "Kisvadim GoProblems"

    @property
    def source_id(self) -> str:
        """Unique source identifier."""
        return "kisvadim"

    def configure(self, config: dict) -> None:
        """Apply adapter-specific configuration.

        Args:
            config: Configuration dictionary from sources.json
        """
        if "source_dir" in config:
            self.source_dir = Path(config["source_dir"])

    def fetch(self, batch_size: int = 100):
        """Fetch puzzles from kisvadim collection.

        Yields:
            FetchResult for each puzzle
        """
        if not self.source_dir.exists():
            logger.warning(f"Kisvadim directory not found: {rel_path(self.source_dir)}")
            yield FetchResult.failed(
                puzzle_id="kisvadim-init",
                error=f"Directory not found: {rel_path(self.source_dir)}",
            )
            return

        count = 0
        for sgf_path in sorted(self.source_dir.rglob("*.sgf")):
            if count >= batch_size:
                break

            puzzle_id = self._generate_id(sgf_path)
            if puzzle_id in self._processed_ids:
                continue

            try:
                content = sgf_path.read_text(encoding="utf-8")

                # Validate SGF using centralized validator (spec 108)
                validation_result = validate_sgf(content)
                if not validation_result:
                    logger.debug(f"Skipping {puzzle_id}: {validation_result.rejection_reason}")
                    yield FetchResult.skipped(puzzle_id=puzzle_id, reason=validation_result.rejection_reason)
                    continue

                self._processed_ids.add(puzzle_id)
                count += 1

                # Extract level from directory structure if available
                self._extract_level(sgf_path)

                yield FetchResult.success(
                    puzzle_id=puzzle_id,
                    sgf_content=content,
                    source_link=str(sgf_path),
                )

            except Exception as e:
                logger.debug(f"Error reading {rel_path(sgf_path)}: {e}")
                yield FetchResult.failed(
                    puzzle_id=puzzle_id,
                    error=str(e),
                )

        logger.info(f"Kisvadim: fetched {count} puzzles")

    def is_available(self) -> bool:
        """Check if kisvadim collection exists."""
        return self.source_dir.exists() and any(self.source_dir.rglob("*.sgf"))

    def _generate_id(self, path: Path) -> str:
        """Generate unique ID from file path."""
        rel_path = path.relative_to(self.source_dir)
        parts = list(rel_path.parts)
        if parts:
            parts[-1] = parts[-1].replace(".sgf", "")
        return f"kisvadim-{'-'.join(parts)}"

    def _extract_level(self, path: Path) -> str | None:
        """Try to extract difficulty level from path."""
        path_str = str(path).lower()

        level_keywords = {
            "beginner": "beginner",
            "easy": "beginner",
            "intermediate": "intermediate",
            "medium": "intermediate",
            "advanced": "advanced",
            "hard": "advanced",
            "expert": "expert",
            "dan": "advanced",
            "kyu": "intermediate",
        }

        for keyword, level in level_keywords.items():
            if keyword in path_str:
                return level

        return None
