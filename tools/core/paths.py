"""
Path utilities for download tools.

Provides consistent path handling across all tools:
- Project root detection
- Relative path formatting for logs
- POSIX path normalization for JSON/cross-platform
- Centralized path configuration

Mirrors backend/puzzle_manager/paths.py pattern.

Usage:
    from tools.core.paths import get_project_root, rel_path, to_posix_path

    # Get project root
    root = get_project_root()  # /path/to/yen-go

    # Format path for logging (relative to project root)
    log_path = rel_path(some_absolute_path)  # external-sources/ogs/...

    # Convert to POSIX format for JSON
    posix = to_posix_path(path)  # external-sources/ogs/sgf/batch-001/file.sgf
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

# .git is the definitive marker for project root
_ROOT_MARKER: Final[str] = ".git"

# Environment variable for project root override
_ROOT_ENV: Final[str] = "YENGO_ROOT"

# Default external sources directory name
_EXTERNAL_SOURCES_DIR: Final[str] = "external-sources"


class PathError(Exception):
    """Error resolving paths."""
    pass


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Detect project root directory.

    Checks in order:
    1. YENGO_ROOT environment variable
    2. Walk up from this file looking for .git directory

    Returns:
        Path to project root directory.

    Raises:
        PathError: If project root cannot be detected.
    """
    # 1. Check environment variable first
    if env_root := os.environ.get(_ROOT_ENV):
        root = Path(env_root).resolve()
        if root.exists():
            return root
        raise PathError(f"{_ROOT_ENV}={env_root} does not exist")

    # 2. Walk up from current file location looking for .git
    # tools/core/paths.py -> tools/core -> tools -> yen-go
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / _ROOT_MARKER).exists():
            return current
        current = current.parent

    raise PathError(
        "Cannot detect project root. "
        "Ensure you're running from within the yen-go repository, "
        f"or set {_ROOT_ENV} environment variable."
    )


def clear_cache() -> None:
    """Clear cached project root.

    Useful for testing when YENGO_ROOT changes.
    """
    get_project_root.cache_clear()


def rel_path(path: Path | str) -> str:
    """Format path as relative to project root for logging.

    Converts absolute paths to relative paths from project root for cleaner
    log output. Uses POSIX format (forward slashes) for consistency.

    Args:
        path: Path to format (can be absolute or relative).

    Returns:
        Relative path string from project root with forward slashes,
        or original string if the path is not under project root.

    Example:
        >>> rel_path(Path("/home/user/yen-go/external-sources/ogs/file.sgf"))
        'external-sources/ogs/file.sgf'
        >>> rel_path("external-sources/ogs/file.sgf")
        'external-sources/ogs/file.sgf'
    """
    if isinstance(path, str):
        path = Path(path)

    # Resolve to absolute for comparison
    path = path.resolve() if path.is_absolute() else path

    try:
        project_root = get_project_root()
        if path.is_absolute():
            relative = path.relative_to(project_root)
            return relative.as_posix()
        # Already relative, just normalize to POSIX
        return path.as_posix()
    except (ValueError, PathError):
        # Path is not under project root or can't detect root
        return str(path).replace("\\", "/")


def to_posix_path(path: Path | str, relative_to: Path = None) -> str:
    """Convert path to POSIX format (forward slashes) for JSON serialization.

    Args:
        path: Path object or string to normalize. Must not be None.
        relative_to: Optional base path to compute relative path from.

    Returns:
        String path with forward slashes only. Empty string if input is empty.

    Raises:
        TypeError: If path is None.
        ValueError: If relative_to is provided but path is not relative to it.

    Examples:
        >>> to_posix_path(Path("a/b/c"))
        'a/b/c'
        >>> to_posix_path("a\\\\b\\\\c")
        'a/b/c'
        >>> to_posix_path(Path("/root/sub/file"), relative_to=Path("/root"))
        'sub/file'
    """
    if path is None:
        raise TypeError("path cannot be None")

    if isinstance(path, str):
        if not path:
            return ""
        return path.replace("\\", "/")

    # Path object
    if relative_to is not None:
        path = path.relative_to(relative_to)  # Raises ValueError if not relative
    return path.as_posix()


def get_external_sources_dir(source_name: str = None) -> Path:
    """Get external sources directory.

    Args:
        source_name: Optional source subdirectory (e.g., "ogs", "tsumegodragon")

    Returns:
        Path to external-sources/ or external-sources/{source_name}/

    Example:
        >>> get_external_sources_dir()
        Path('/path/to/yen-go/external-sources')
        >>> get_external_sources_dir("ogs")
        Path('/path/to/yen-go/external-sources/ogs')
    """
    base = get_project_root() / _EXTERNAL_SOURCES_DIR
    if source_name:
        return base / source_name
    return base


# Tool-specific output directories (centralized configuration)
TOOL_OUTPUT_DIRS: Final[dict[str, str]] = {
    "ogs": "external-sources/ogs",
    "tsumegodragon": "external-sources/tsumegodragon",
    "t-dragon": "external-sources/tsumegodragon",  # Alias
    "go-problems": "external-sources/goproblems",
    "goproblems": "external-sources/goproblems",  # Alias
    "blacktoplay": "external-sources/blacktoplay",
    "btp": "external-sources/blacktoplay",  # Alias
}


def get_tool_output_dir(tool_name: str) -> Path:
    """Get output directory for a specific tool.

    Args:
        tool_name: Tool identifier (e.g., "ogs", "tsumegodragon")

    Returns:
        Absolute path to tool's output directory.

    Raises:
        KeyError: If tool_name is not registered.
    """
    if tool_name not in TOOL_OUTPUT_DIRS:
        raise KeyError(f"Unknown tool: {tool_name}. Known tools: {list(TOOL_OUTPUT_DIRS.keys())}")

    rel_dir = TOOL_OUTPUT_DIRS[tool_name]
    return get_project_root() / rel_dir
