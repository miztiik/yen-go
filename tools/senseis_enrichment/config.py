"""Configuration and path helpers for Senseis enrichment tool."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_TOOL_DIR = Path(__file__).parent
_PROJECT_ROOT = _TOOL_DIR.parent.parent  # yen-go/


@dataclass(frozen=True)
class SenseisConfig:
    """Loaded configuration from senseis_config.json."""

    collection_slug: str
    senseis_base_url: str
    index_page: str
    problem_count: int
    problem_page_pattern: str
    solution_page_pattern: str
    local_dir: str
    enriched_dir_suffix: str
    local_filename_pattern: str
    board_size: int
    aliases: dict[str, str]
    rate_limit_seconds: float
    rate_limit_jitter: float
    user_agent: str

    def problem_page_name(self, n: int) -> str:
        """Get the Senseis page name for problem N (handles aliases)."""
        alias = self.aliases.get(str(n))
        if alias:
            return alias
        # Extract page name from pattern (strip leading /?)
        pattern = self.problem_page_pattern.lstrip("/?")
        return pattern.replace("{N}", str(n))

    def problem_url(self, n: int) -> str:
        """Full URL for a problem page."""
        alias = self.aliases.get(str(n))
        if alias:
            return f"{self.senseis_base_url}/?{alias}"
        return self.senseis_base_url + self.problem_page_pattern.replace("{N}", str(n))

    def solution_url(self, n: int) -> str:
        """Full URL for a solution page."""
        alias = self.aliases.get(str(n))
        if alias:
            return f"{self.senseis_base_url}/?{alias}%2FSolution"
        return self.senseis_base_url + self.solution_page_pattern.replace("{N}", str(n))

    def local_sgf_path(self, n: int) -> Path:
        """Path to local SGF file for problem N."""
        filename = self.local_filename_pattern.replace("{N:04d}", f"{n:04d}")
        return _PROJECT_ROOT / self.local_dir / filename

    def enriched_dir(self) -> Path:
        """Path to the enriched output directory (sibling of local_dir)."""
        local = _PROJECT_ROOT / self.local_dir
        return local.parent / (local.name + self.enriched_dir_suffix)

    def enriched_sgf_path(self, n: int) -> Path:
        """Path to enriched SGF file for problem N."""
        filename = self.local_filename_pattern.replace("{N:04d}", f"{n:04d}")
        return self.enriched_dir() / filename

    def diagram_sgf_url(self, relative_path: str) -> str:
        """Full URL for a diagram SGF (e.g. 'diagrams/33/abc.sgf')."""
        return f"{self.senseis_base_url}/{relative_path}"

    def working_dir(self) -> Path:
        """Return the _working/{slug}/ cache directory."""
        return _TOOL_DIR / "_working" / self.collection_slug

    def page_cache_dir(self) -> Path:
        return self.working_dir() / "_page_cache"

    def solution_cache_dir(self) -> Path:
        return self.working_dir() / "_solution_cache"

    def diagram_cache_dir(self) -> Path:
        return self.working_dir() / "_diagram_sgfs"

    def index_cache_path(self) -> Path:
        return self.working_dir() / "_index_cache.json"

    def match_results_path(self) -> Path:
        return self.working_dir() / "_match_results.json"


# --- Free-standing path helpers (kept for backward compat, require slug) ---

def working_dir(slug: str = "") -> Path:
    """Return the _working/{slug}/ cache directory.

    If slug is empty, returns the bare _working/ (for migration only).
    """
    if slug:
        return _TOOL_DIR / "_working" / slug
    return _TOOL_DIR / "_working"


def page_cache_dir(slug: str = "") -> Path:
    return working_dir(slug) / "_page_cache"


def solution_cache_dir(slug: str = "") -> Path:
    return working_dir(slug) / "_solution_cache"


def diagram_cache_dir(slug: str = "") -> Path:
    return working_dir(slug) / "_diagram_sgfs"


def index_cache_path(slug: str = "") -> Path:
    return working_dir(slug) / "_index_cache.json"


def match_results_path(slug: str = "") -> Path:
    return working_dir(slug) / "_match_results.json"


def checkpoint_path(slug: str = "") -> Path:
    return working_dir(slug) / ".checkpoint.json"


# --- Loader ---

def load_config(config_path: Path | None = None) -> SenseisConfig:
    """Load configuration from a JSON config file.

    Args:
        config_path: Path to config JSON. Defaults to senseis_config.json
                     in the tool directory.
    """
    if config_path is None:
        config_path = _TOOL_DIR / "senseis_config.json"
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return SenseisConfig(**data)
