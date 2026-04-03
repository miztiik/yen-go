"""
TravisGK adapter for importing puzzles from travisgk collection.

GitHub-based collection adapter.
"""

import logging

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import register_adapter
from backend.puzzle_manager.core.http import HttpClient
from backend.puzzle_manager.core.puzzle_validator import validate_sgf

logger = logging.getLogger("puzzle_manager.adapters.travisgk")


TRAVISGK_RAW_BASE = "https://raw.githubusercontent.com/travisgk/go-problems/main"


@register_adapter("travisgk")
class TravisGKAdapter:
    """Adapter for TravisGK go-problems collection.

    Fetches from GitHub repository.
    """

    def __init__(
        self,
        base_url: str = TRAVISGK_RAW_BASE,
        categories: list[str] | None = None,
        **kwargs,
    ):
        """Initialize adapter.

        Args:
            base_url: Base URL for raw GitHub content
            categories: Specific categories to import (e.g., ['life-death', 'tesuji'])
            **kwargs: Additional config options
        """
        self.base_url = base_url.rstrip("/")
        self.categories = categories or ["life-death", "tesuji", "joseki"]
        self.http = HttpClient()
        self._fetched_ids: set[str] = set()

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        return "TravisGK"

    @property
    def source_id(self) -> str:
        """Unique source identifier."""
        return "travisgk"

    def configure(self, config: dict) -> None:
        """Apply adapter-specific configuration.

        Args:
            config: Configuration dictionary from sources.json
        """
        if "base_url" in config:
            self.base_url = config["base_url"].rstrip("/")
        if "categories" in config:
            self.categories = config["categories"]

    def fetch(self, batch_size: int = 100):
        """Fetch puzzles from TravisGK collection.

        Yields:
            FetchResult for each puzzle
        """
        logger.info(f"Fetching from TravisGK (categories={self.categories})")

        count = 0
        for category in self.categories:
            if count >= batch_size:
                break

            try:
                # Try to fetch index for category
                index_url = f"{self.base_url}/{category}/index.txt"

                try:
                    response = self.http.get(index_url)
                    puzzle_files = response.text.strip().split("\n")
                except Exception:
                    # If no index, try numbered files
                    puzzle_files = [f"{i:03d}.sgf" for i in range(1, 101)]

                for filename in puzzle_files:
                    if count >= batch_size:
                        break

                    puzzle_id = f"travisgk-{category}-{filename.replace('.sgf', '')}"
                    if puzzle_id in self._fetched_ids:
                        continue

                    try:
                        sgf_url = f"{self.base_url}/{category}/{filename}"
                        response = self.http.get(sgf_url)

                        if response.status_code == 200:
                            # Validate SGF using centralized validator (spec 108)
                            validation_result = validate_sgf(response.text)
                            if not validation_result:
                                logger.debug(f"Skipping {puzzle_id}: {validation_result.rejection_reason}")
                                yield FetchResult.skipped(puzzle_id=puzzle_id, reason=validation_result.rejection_reason)
                                continue

                            self._fetched_ids.add(puzzle_id)
                            count += 1

                            yield FetchResult(
                                puzzle_id=puzzle_id,
                                sgf_content=response.text,
                                source="travisgk",
                                metadata={"category": category},
                            )

                    except Exception as e:
                        logger.debug(f"Failed to fetch {puzzle_id}: {e}")

            except Exception as e:
                logger.warning(f"Error processing category {category}: {e}")

        logger.info(f"TravisGK: fetched {count} puzzles")

    def is_available(self) -> bool:
        """Check if TravisGK repository is accessible."""
        try:
            response = self.http.get(f"{self.base_url}/README.md", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
