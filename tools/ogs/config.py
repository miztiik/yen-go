"""
Configuration constants and paths for OGS downloader.

All configurable paths and settings are defined here for easy modification.
"""

from pathlib import Path

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

# Base output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("external-sources/ogs")

# Subdirectories
SGF_SUBDIR = "sgf"
LOGS_SUBDIR = "logs"

# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

# Maximum files per batch directory (batch-001, batch-002, etc.)
DEFAULT_BATCH_SIZE = 1000

# ============================================================================
# API CONFIGURATION
# ============================================================================

# OGS API base URL
OGS_API_BASE = "https://online-go.com/api/v1"

# Default page size for pagination (OGS allows up to 50)
DEFAULT_PAGE_SIZE = 50

# Rate limiting: delays between requests (seconds)
DEFAULT_PAGE_DELAY = 5      # Between pagination requests
DEFAULT_PUZZLE_DELAY = 10    # Between puzzle detail fetches
DELAY_JITTER_FACTOR = 0.5      # ±50% jitter

# Request timeouts (seconds)
DEFAULT_TIMEOUT = 30

# Retry configuration
DEFAULT_MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 30.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX_SECONDS = 240.0

# HTTP status codes
HTTP_TOO_MANY_REQUESTS = 429
HTTP_NOT_FOUND = 404

# User-Agent header
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

# Maximum move tree depth (puzzle solution moves)
# 12 = ~6 moves per side, suitable for beginner/intermediate
# Increase for advanced/dan puzzles
DEFAULT_MAX_MOVE_TREE_DEPTH = 20  # Higher limit for external sources

# Minimum/maximum board sizes
MIN_BOARD_SIZE = 5
MAX_BOARD_SIZE = 19

# ============================================================================
# CHECKPOINT CONFIGURATION
# ============================================================================

CHECKPOINT_FILENAME = ".checkpoint.json"
CHECKPOINT_VERSION = "1.0.0"

# Import shared path utilities from tools.core
from tools.core.paths import get_project_root
from tools.core.paths import rel_path as to_relative_path  # Alias for backward compat

# Re-export for backward compatibility
__all__ = [
    "get_project_root",
    "to_relative_path",
    "get_output_dir",
    "get_sgf_dir",
    "get_logs_dir",
]


def get_output_dir(custom_dir: Path | None = None) -> Path:
    """Get the output directory for OGS downloads.

    Args:
        custom_dir: Custom output directory (overrides default)

    Returns:
        Absolute path to output directory
    """
    if custom_dir is not None:
        if custom_dir.is_absolute():
            return custom_dir
        return get_project_root() / custom_dir
    return get_project_root() / DEFAULT_OUTPUT_DIR


def get_sgf_dir(output_dir: Path) -> Path:
    """Get the SGF subdirectory.

    Args:
        output_dir: Base output directory

    Returns:
        Path to sgf/ subdirectory
    """
    return output_dir / SGF_SUBDIR


def get_logs_dir(output_dir: Path) -> Path:
    """Get the logs subdirectory.

    Args:
        output_dir: Base output directory

    Returns:
        Path to logs/ subdirectory
    """
    return output_dir / LOGS_SUBDIR
