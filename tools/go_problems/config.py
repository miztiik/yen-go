"""
Configuration constants and paths for GoProblems downloader.

All configurable paths and settings are defined here for easy modification.
"""

from pathlib import Path

from tools.core.paths import get_project_root
from tools.core.paths import rel_path as to_relative_path

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

DEFAULT_OUTPUT_DIR = Path("external-sources/goproblems")

SGF_SUBDIR = "sgf"
LOGS_SUBDIR = "logs"

# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

DEFAULT_BATCH_SIZE = 1000

# ============================================================================
# API CONFIGURATION
# ============================================================================

GOPROBLEMS_API_BASE = "https://www.goproblems.com/api/v2"
GOPROBLEMS_COLLECTIONS_API_BASE = "https://www.goproblems.com/api"

# Rate limiting: delays between requests (seconds)
DEFAULT_PUZZLE_DELAY = 7.0
DELAY_JITTER_FACTOR = 0.5  # +/-50% jitter

# Request timeouts (seconds)
DEFAULT_TIMEOUT = 30

# Retry configuration
DEFAULT_MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 5.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX_SECONDS = 60.0

# HTTP status codes
HTTP_TOO_MANY_REQUESTS = 429
HTTP_NOT_FOUND = 404

# User-Agent header
USER_AGENT = "YenGo-PuzzleManager/1.0 (https://github.com/yengo)"

# ============================================================================
# FILTERING CONFIGURATION
# ============================================================================

DEFAULT_CANON_ONLY = True

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

DEFAULT_MAX_SOLUTION_DEPTH = 30

MIN_BOARD_SIZE = 5
MAX_BOARD_SIZE = 19

# ============================================================================
# CHECKPOINT CONFIGURATION
# ============================================================================

CHECKPOINT_FILENAME = ".checkpoint.json"
CHECKPOINT_VERSION = "1.0.0"


__all__ = [
    "get_project_root",
    "to_relative_path",
    "get_output_dir",
    "get_sgf_dir",
    "get_logs_dir",
    "GOPROBLEMS_COLLECTIONS_API_BASE",
]


def get_output_dir(custom_dir: Path | None = None) -> Path:
    """Get the output directory for GoProblems downloads.

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
