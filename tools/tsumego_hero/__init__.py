"""
Tsumego Hero puzzle downloader.

Downloads Go tsumego puzzles from tsumego.com.

Usage:
    python -m tools.tsumego_hero --help
    python -m tools.tsumego_hero --list-collections
    python -m tools.tsumego_hero --max-puzzles 100 --resume
"""

from .batching import (
    THERO_BATCH_SIZE,
    get_sgf_dir,
)
from .checkpoint import (
    THeroCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from .client import (
    PuzzleData,
    TsumegoHeroClient,
    TsumegoHeroClientError,
)
from .index import (
    load_puzzle_ids,
    rebuild_index,
    sort_index,
)
from .mappers import (
    difficulty_to_level,
    tags_to_yengo,
)
from .orchestrator import (
    DEFAULT_OUTPUT_DIR,
    DownloadConfig,
    DownloadStats,
    download_puzzles,
)

__all__ = [
    # Client
    "PuzzleData",
    "TsumegoHeroClient",
    "TsumegoHeroClientError",
    # Orchestrator
    "download_puzzles",
    "DownloadConfig",
    "DownloadStats",
    "DEFAULT_OUTPUT_DIR",
    # Checkpoint
    "THeroCheckpoint",
    "load_checkpoint",
    "save_checkpoint",
    # Batching
    "THERO_BATCH_SIZE",
    "get_sgf_dir",
    # Index
    "load_puzzle_ids",
    "sort_index",
    "rebuild_index",
    # Mappers
    "difficulty_to_level",
    "tags_to_yengo",
]
