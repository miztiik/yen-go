"""
TsumegoDragon downloader package.

Downloads Go (Baduk) tsumego puzzles from TsumegoDragon.com with
robust rate limiting to avoid being blocked by the Bubble.io CDN.

Embeds YG (level) and YT (tag) properties directly in SGF files.
Uses structured JSON logging for programmatic analysis.

See docs/reference/adapters/ for adapter documentation.
"""

__version__ = "2.1.0"  # v2.1: structured JSON file logging

from .checkpoint import TDragonCheckpoint, load_checkpoint, save_checkpoint
from .client import TsumegoDragonClient
from .index import load_puzzle_ids, rebuild_index, sort_index
from .logging_config import EventType, get_logger, setup_logging
from .mappers import category_to_yt_tags, level_to_yg_slug, should_skip_category
from .models import DEFAULT_CATEGORIES, TDCategory, TDCategoryResponse, TDPuzzle, TDPuzzleResponse
from .orchestrator import DownloadConfig, DownloadStats, download_puzzles
from .storage import count_files_in_sgf_dir, save_puzzle

__all__ = [
    "TsumegoDragonClient",
    "TDCategory",
    "TDPuzzle",
    "TDCategoryResponse",
    "TDPuzzleResponse",
    "DEFAULT_CATEGORIES",
    "save_puzzle",
    "count_files_in_sgf_dir",
    "level_to_yg_slug",
    "category_to_yt_tags",
    "should_skip_category",
    "load_checkpoint",
    "save_checkpoint",
    "TDragonCheckpoint",
    "download_puzzles",
    "DownloadConfig",
    "DownloadStats",
    "load_puzzle_ids",
    "sort_index",
    "rebuild_index",
    "setup_logging",
    "get_logger",
    "EventType",
]
