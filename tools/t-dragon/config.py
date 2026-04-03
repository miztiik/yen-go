"""
Centralized configuration for TsumegoDragon downloader.

All tool-specific constants, defaults, and path utilities.
"""

from __future__ import annotations

from pathlib import Path

from tools.core.paths import get_project_root, rel_path

# Source identifier for YS[] property
SOURCE_ID = "td"

# Tool display name
TOOL_NAME = "TsumegoDragon Downloader"

# Default output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("external-sources/tsumegodragon")

# Default batch size (files per batch directory)
DEFAULT_BATCH_SIZE = 500

# Default request delay (seconds)
DEFAULT_REQUEST_DELAY = 15.0


def get_output_dir() -> Path:
    """Get default output directory as absolute path."""
    return get_project_root() / DEFAULT_OUTPUT_DIR


def get_sgf_dir(output_dir: Path) -> Path:
    """Get sgf/ subdirectory."""
    return output_dir / "sgf"


def to_relative_path(path: Path) -> str:
    """Format path for display (project-root-relative POSIX)."""
    return rel_path(path)


# Category-to-intent static mapping for C[] resolution.
# T-Dragon puzzles don't have description text, so we derive intent
# from the category slug. Player to move is always Black on T-Dragon.
CATEGORY_TO_INTENT: dict[str, str] = {
    "capture": "Black to capture",
    "ladder": "Black to capture using a ladder",
    "net": "Black to capture using a net",
    "loopko": "Black to win the ko",
    "snapback": "Black to capture using snapback",
    "bamboo-snapback": "Black to capture using snapback",
    "making-eyes": "Black to make eyes and live",
    "taking-eyes": "Black to destroy eyes and kill",
    "corner-life--death": "Black to live or kill in the corner",
    "throw-in-tactic": "Black to use throw-in",
    "capture-race": "Black to win the capturing race",
    "liberty-shortage": "Black to exploit shortage of liberties",
    "connecting": "Black to connect",
    "disconnect": "Black to cut",
    "double-threatatari": "Black to play double atari",
    "mutual-life": "Black to achieve seki",
    "three-point-eye": "Black to determine the status of a three-point eye shape",
    "four-point-eye": "Black to determine the status of a four-point eye shape",
    "five-point-eye": "Black to determine the status of a five-point eye shape",
    "six-point-eye": "Black to determine the status of a six-point eye shape",
    "nine-space-eye": "Black to determine the status of a large eye shape",
    "connect--die": "Black to determine the best strategy",
    "bonus-liberty": "Black to exploit shortage of liberties",
    "squeeze-tactic": "Black to use squeeze",
    "vital-wedge": "Black to find the vital point",
    "shape": "Black to find the best shape move",
    "endgame-yose": "Black to find the best endgame move",
    "opening-basics": "Black to find the best opening move",
    "false-eye": "Black to create or exploit a false eye",
    "discovered-cut": "Black to cut",
    "corner-pattern": "Black to live or kill in the corner",
    "endgame-traps": "Black to find the endgame tesuji",
    "eye-vs-no-eye": "Black to win the capturing race",
}
