"""
Configuration constants and paths for 101weiqi downloader.

All configurable paths and settings are defined here for easy modification.
"""

from pathlib import Path

from tools.core.paths import get_project_root

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

DEFAULT_OUTPUT_DIR = Path("external-sources/101weiqi")

SGF_SUBDIR = "sgf"
QDAY_SUBDIR = "qday"
LOGS_SUBDIR = "logs"

# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

DEFAULT_BATCH_SIZE = 1000

# ============================================================================
# SITE CONFIGURATION
# ============================================================================

BASE_URL = "https://www.101weiqi.com"

# URL patterns for different source modes
URL_DAILY = "/qday/{year}/{month}/{day}/{puzzle_num}/"
URL_PUZZLE = "/q/{puzzle_id}/"

# Daily puzzle count (fixed at 8)
DAILY_PUZZLE_COUNT = 8

# ============================================================================
# RATE LIMITING
# ============================================================================

DEFAULT_PUZZLE_DELAY = 60.0      # Between puzzle requests (seconds)
DELAY_JITTER_FACTOR = 0.33      # ±33% jitter (~40s to ~80s with 60s base)

DEFAULT_TIMEOUT = 30             # Request timeout (seconds)

# Retry / backoff
DEFAULT_MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 30.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX_SECONDS = 240.0

# HTTP status codes
HTTP_TOO_MANY_REQUESTS = 429
HTTP_NOT_FOUND = 404

# Probe: stop after this many consecutive 404s
CONSECUTIVE_FAILURE_LIMIT = 5

# Rate-limit detection: stop after this many consecutive extraction failures
# (applies in book mode where CONSECUTIVE_FAILURE_LIMIT only covers 404s)
CONSECUTIVE_EXTRACTION_FAILURE_LIMIT = 10

# Batch cooldown: pause for COOLDOWN_DURATION seconds every COOLDOWN_INTERVAL
# successful downloads to avoid triggering the site's CAPTCHA rate limiter.
# Live testing shows CAPTCHA triggers after ~2-3 rapid requests from same IP.
COOLDOWN_INTERVAL = 20       # downloads between cooldown pauses
COOLDOWN_DURATION = 60.0     # cooldown pause duration (seconds)

# ============================================================================
# VALIDATION
# ============================================================================

MIN_BOARD_SIZE = 5
MAX_BOARD_SIZE = 19
DEFAULT_MAX_SOLUTION_DEPTH = 30

# ============================================================================
# CHECKPOINT
# ============================================================================

CHECKPOINT_FILENAME = ".checkpoint.json"
CHECKPOINT_VERSION = "1.0.0"

# ============================================================================
# HTTP
# ============================================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) "
    "Gecko/20100101 Firefox/148.0"
)


# ============================================================================
# BROWSER CAPTURE RECEIVER
# ============================================================================

RECEIVER_HOST = "127.0.0.1"
RECEIVER_PORT = 8101
RECEIVER_MAX_BODY = 1024 * 1024  # 1 MB max POST body

# ============================================================================
# PATH HELPERS
# ============================================================================

def get_output_dir(custom_dir: Path | None = None) -> Path:
    """Get absolute output directory for 101weiqi downloads."""
    if custom_dir is not None:
        if custom_dir.is_absolute():
            return custom_dir
        return get_project_root() / custom_dir
    return get_project_root() / DEFAULT_OUTPUT_DIR


def get_sgf_dir(output_dir: Path) -> Path:
    """Get the SGF subdirectory."""
    return output_dir / SGF_SUBDIR


def get_qday_dir(output_dir: Path) -> Path:
    """Get the daily puzzles (qday) subdirectory."""
    return output_dir / QDAY_SUBDIR


def get_logs_dir(output_dir: Path) -> Path:
    """Get the logs subdirectory."""
    return output_dir / LOGS_SUBDIR
