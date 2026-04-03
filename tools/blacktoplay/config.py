"""
Configuration constants and paths for BlackToPlay (BTP) downloader.

All configurable paths and settings are defined here for easy modification.
"""

from __future__ import annotations

from pathlib import Path

from tools.core.paths import get_project_root

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

# Base output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("external-sources/blacktoplay")

# Subdirectories
SGF_SUBDIR = "sgf"
LOGS_SUBDIR = "logs"

# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

# Maximum files per batch directory (batch-001, batch-002, etc.)
DEFAULT_BATCH_SIZE = 500

# ============================================================================
# API CONFIGURATION
# ============================================================================

# BTP base URL
BTP_BASE_URL = "https://blacktoplay.com"

# Endpoints (POST)
BTP_LOAD_DATA_URL = f"{BTP_BASE_URL}/php/public/load_data.php"
BTP_LOAD_LIST_URL = f"{BTP_BASE_URL}/php/public/load_list.php"

# Puzzle types: 0 = Classic, 1 = AI, 2 = Endgame
PUZZLE_TYPE_CLASSIC = 0
PUZZLE_TYPE_AI = 1
PUZZLE_TYPE_ENDGAME = 2

ALL_PUZZLE_TYPES = [PUZZLE_TYPE_CLASSIC, PUZZLE_TYPE_AI, PUZZLE_TYPE_ENDGAME]

PUZZLE_TYPE_NAMES = {
    PUZZLE_TYPE_CLASSIC: "classic",
    PUZZLE_TYPE_AI: "ai",
    PUZZLE_TYPE_ENDGAME: "endgame",
}

# Rate limiting: delays between requests (seconds)
DEFAULT_PUZZLE_DELAY = 1.0  # Between individual puzzle fetches
DELAY_JITTER_FACTOR = 0.3  # ±30% jitter

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

# Browser-like headers (BTP blocks non-browser requests)
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": BTP_BASE_URL,
    "Referer": f"{BTP_BASE_URL}/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

# ============================================================================
# MAPPING FILE PATHS (relative to tools/blacktoplay/)
# ============================================================================

_THIS_DIR = Path(__file__).parent

LEVEL_MAPPING_PATH = _THIS_DIR / "_local_level_mapping.json"
TAG_MAPPING_PATH = _THIS_DIR / "_local_tag_mapping.json"
COLLECTIONS_MAPPING_PATH = _THIS_DIR / "_local_collections_mapping.json"
INTENT_SIGNALS_PATH = _THIS_DIR / "intent_signals.json"

# Cached puzzle list (fallback when live API returns empty)
CACHED_LIST_PATH = _THIS_DIR / "research" / "btp-list-response.json"

# ============================================================================
# BOARD / SGF CONSTANTS
# ============================================================================

# Classic puzzles use 19×19 board with viewport
FULL_BOARD_SIZE = 19

# BTP source identifier for YenGo
SOURCE_ID = "blacktoplay"


# ============================================================================
# PATH HELPERS
# ============================================================================


def get_output_dir(custom_dir: Path | None = None) -> Path:
    """Get the output directory for BTP downloads.

    Args:
        custom_dir: Custom output directory (overrides default).

    Returns:
        Absolute path to output directory.
    """
    if custom_dir:
        return custom_dir.resolve()
    return get_project_root() / DEFAULT_OUTPUT_DIR


def get_sgf_dir(output_dir: Path | None = None) -> Path:
    """Get the SGF subdirectory."""
    base = output_dir or get_output_dir()
    return base / SGF_SUBDIR


def get_logs_dir(output_dir: Path | None = None) -> Path:
    """Get the logs subdirectory."""
    base = output_dir or get_output_dir()
    return base / LOGS_SUBDIR
