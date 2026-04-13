"""Configuration for Harada tsumego archive crawler."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.paths import get_project_root


@dataclass(frozen=True)
class CollectionConfig:
    """Immutable configuration loaded from harada_config.json."""

    collection_name: str
    collection_slug: str
    description: str
    author: str

    wayback_base: str
    original_base: str
    index_url: str
    index_wayback_timestamp: str

    year_range: tuple[int, int]
    year_page_pattern: str
    estimated_total_problems: int

    levels: tuple[str, ...]

    rate_limit_seconds: float
    rate_limit_jitter: float
    request_timeout: int
    max_retries: int
    user_agent: str

    working_dir_rel: str
    page_cache_rel: str
    image_dir_rel: str
    catalog_filename: str

    # --- Computed paths ---

    def working_dir(self) -> Path:
        return get_project_root() / self.working_dir_rel

    def page_cache_dir(self) -> Path:
        return self.working_dir() / self.page_cache_rel

    def image_dir(self) -> Path:
        return self.working_dir() / self.image_dir_rel

    def catalog_path(self) -> Path:
        return self.working_dir() / self.catalog_filename

    def logs_dir(self) -> Path:
        return self.working_dir() / "logs"

    # --- URL construction ---

    def wayback_url(self, original_url: str, timestamp: str = "") -> str:
        """Construct Wayback Machine URL with if_ (no toolbar) mode."""
        ts = timestamp or self.index_wayback_timestamp
        return f"{self.wayback_base}/{ts}if_/{original_url}"

    def year_page_original_url(self, year: int) -> str:
        page = self.year_page_pattern.replace("{year}", str(year))
        return f"{self.original_base}/past/{page}"

    def years(self) -> range:
        return range(self.year_range[0], self.year_range[1] + 1)


def load_config(config_path: Path | None = None) -> CollectionConfig:
    """Load configuration from JSON file."""
    if config_path is None:
        config_path = Path(__file__).parent / "harada_config.json"

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    return CollectionConfig(
        collection_name=data["collection_name"],
        collection_slug=data["collection_slug"],
        description=data["description"],
        author=data["author"],
        wayback_base=data["wayback_base"],
        original_base=data["original_base"],
        index_url=data["index_url"],
        index_wayback_timestamp=data["index_wayback_timestamp"],
        year_range=tuple(data["year_range"]),
        year_page_pattern=data["year_page_pattern"],
        estimated_total_problems=data["estimated_total_problems"],
        levels=tuple(data["levels"]),
        rate_limit_seconds=data["rate_limit_seconds"],
        rate_limit_jitter=data["rate_limit_jitter"],
        request_timeout=data["request_timeout"],
        max_retries=data["max_retries"],
        user_agent=data["user_agent"],
        working_dir_rel=data["working_dir"],
        page_cache_rel=data["page_cache_dir"],
        image_dir_rel=data["image_dir"],
        catalog_filename=data["catalog_filename"],
    )
