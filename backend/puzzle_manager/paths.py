"""
Path resolution for the puzzle manager.

Detects project root and provides consistent path access.
Supports YENGO_ROOT environment variable override for project root.
Supports YENGO_RUNTIME_DIR environment variable override for runtime artifacts.

Note: Production path functions (get_output_dir, etc.) are for CLI use only.
Tests should pass explicit paths via tmp_path fixture for isolation.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

from backend.puzzle_manager.exceptions import ProjectRootError

# .git is the DEFINITIVE marker for project root (only exists at actual root)
# pyproject.toml exists in subpackages too, so it's not reliable alone
_ROOT_MARKER: Final[str] = ".git"

# Default runtime directory name (created at project root)
_RUNTIME_DIR_NAME: Final[str] = ".pm-runtime"

# Environment variable for runtime directory override
_RUNTIME_DIR_ENV: Final[str] = "YENGO_RUNTIME_DIR"


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Detect project root directory.

    Checks in order:
    1. YENGO_ROOT environment variable
    2. Walk up from this file looking for .git directory

    Returns:
        Path to project root directory.

    Raises:
        ProjectRootError: If project root cannot be detected.
    """
    # 1. Check environment variable first
    if env_root := os.environ.get("YENGO_ROOT"):
        root = Path(env_root).resolve()
        if root.exists():
            return root
        raise ProjectRootError(
            f"YENGO_ROOT={env_root} does not exist",
            context={"YENGO_ROOT": env_root},
        )

    # 2. Walk up from current file location looking for .git
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / _ROOT_MARKER).exists():
            return current
        current = current.parent

    raise ProjectRootError(
        "Cannot detect project root. "
        "Ensure you're running from within the yen-go repository, "
        "or set YENGO_ROOT environment variable.",
        context={"searched_from": str(Path(__file__).resolve().parent)},
    )


@lru_cache(maxsize=1)
def get_runtime_dir() -> Path:
    """Get runtime directory for logs, state, and staging files.

    This separates runtime artifacts from source code, following industry
    best practices (pip, npm, Docker, Kubernetes all do this).

    Resolution order:
    1. YENGO_RUNTIME_DIR environment variable (must be absolute path)
    2. Default: {project_root}/.pm-runtime/

    Returns:
        Path to runtime directory.

    Raises:
        ProjectRootError: If YENGO_RUNTIME_DIR is set but invalid.

    Note:
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    # 1. Check environment variable first
    if env_runtime := os.environ.get(_RUNTIME_DIR_ENV):
        runtime_path = Path(env_runtime)

        # Must be absolute path
        if not runtime_path.is_absolute():
            raise ProjectRootError(
                f"{_RUNTIME_DIR_ENV} must be an absolute path, got: {env_runtime}",
                context={_RUNTIME_DIR_ENV: env_runtime},
            )

        # If path exists, it must be a directory (not a file)
        if runtime_path.exists() and not runtime_path.is_dir():
            raise ProjectRootError(
                f"{_RUNTIME_DIR_ENV} exists but is not a directory: {env_runtime}",
                context={_RUNTIME_DIR_ENV: env_runtime},
            )

        return runtime_path.resolve()

    # 2. Default: .pm-runtime/ at project root
    return get_project_root() / _RUNTIME_DIR_NAME


def get_backend_dir() -> Path:
    """Get backend/puzzle_manager directory."""
    return get_project_root() / "backend" / "puzzle_manager"


def get_logs_dir() -> Path:
    """Get logs directory.

    Returns:
        Path to .pm-runtime/logs/ (or YENGO_RUNTIME_DIR/logs/ if set)

    Note:
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    return get_runtime_dir() / "logs"


def get_pm_state_dir() -> Path:
    """Get runtime state directory.

    Returns:
        Path to .pm-runtime/state/ (or YENGO_RUNTIME_DIR/state/ if set)

    Note:
        This is distinct from the state/ Python module.
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    return get_runtime_dir() / "state"


def get_pm_staging_dir() -> Path:
    """Get staging directory.

    Returns:
        Path to .pm-runtime/staging/ (or YENGO_RUNTIME_DIR/staging/ if set)

    Note:
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    return get_runtime_dir() / "staging"


def get_pm_raw_dir() -> Path:
    """Get raw landing zone directory for adapter API responses.

    Returns:
        Path to .pm-runtime/raw/ (or YENGO_RUNTIME_DIR/raw/ if set)

    Used by adapters to store raw API responses (JSON) before transformation.
    Each adapter creates its own subdirectory: raw/{adapter_name}/

    Note:
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    return get_runtime_dir() / "raw"


def get_config_dir() -> Path:
    """Get config directory (backend/puzzle_manager/config/)."""
    return get_backend_dir() / "config"


def get_global_config_dir() -> Path:
    """Get global config directory (config/ at project root).

    This is the source of truth for shared configs like tags.json.
    """
    return get_project_root() / "config"


def get_output_dir() -> Path:
    """Get output directory for published puzzles.

    Returns:
        Path to yengo-puzzle-collections/

    Note:
        For tests, pass explicit paths via tmp_path fixture.
        This function is for CLI entry point use only.
    """
    return get_project_root() / "yengo-puzzle-collections"


# Spec 107: Operational files directory name
_OPS_DIR_NAME: Final[str] = ".puzzle-inventory-state"


def get_ops_dir() -> Path:
    """Get operational files directory for inventory, audit, and publish logs.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/

    Spec 107: Separates operational metadata from content (sgf/, views/).

    Note:
        For tests, use output_dir / ".puzzle-inventory-state" instead.
        This function is for CLI entry point use only.
    """
    return get_output_dir() / _OPS_DIR_NAME


def get_inventory_file_path() -> Path:
    """Get path to the inventory JSON file.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/inventory.json

    Spec 107: Renamed from puzzle-collection-inventory.json and moved to ops dir.

    Note:
        For tests, use ops_dir / "inventory.json" instead.
        This function is for CLI entry point use only.
    """
    return get_ops_dir() / "inventory.json"


def get_audit_log_path() -> Path:
    """Get path to the audit log file.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/audit.jsonl

    Spec 107: Moved from collection root to ops dir.

    Note:
        For tests, use ops_dir / "audit.jsonl" instead.
        This function is for CLI entry point use only.
    """
    return get_ops_dir() / "audit.jsonl"


def to_posix_path(path: Path | str, relative_to: Path | None = None) -> str:
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
        >>> to_posix_path("")
        ''
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


def get_publish_log_dir() -> Path:
    """Get publish log directory for rollback tracking.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/publish-log/

    Spec 107: Moved to ops dir for clear separation of content vs operational files.

    Note:
        For tests, use ops_dir / "publish-log" instead.
        This function is for CLI entry point use only.
    """
    return get_ops_dir() / "publish-log"


def get_rollback_backup_dir() -> Path:
    """Get backup directory for atomic rollback operations.

    Returns:
        Path to yengo-puzzle-collections/.puzzle-inventory-state/rollback-backup/

    Spec 107: Moved to ops dir for clear separation of content vs operational files.

    Note:
        For tests, use ops_dir / "rollback-backup" instead.
        This function is for CLI entry point use only.
    """
    return get_ops_dir() / "rollback-backup"


def get_sgf_output_dir() -> Path:
    """Get SGF output directory.

    Returns:
        Path to yengo-puzzle-collections/sgf/

    Note:
        For tests, use runtime_paths.output_dir / "sgf" instead.
        This function is for CLI entry point use only.
    """
    return get_output_dir() / "sgf"


def get_views_dir() -> Path:
    """Get views output directory.

    Returns:
        Path to yengo-puzzle-collections/views/

    Note:
        For tests, use runtime_paths.output_dir / "views" instead.
        This function is for CLI entry point use only.
    """
    return get_output_dir() / "views"





def ensure_runtime_dirs() -> None:
    """Create runtime directories if they don't exist.

    Creates under .pm-runtime/ (or YENGO_RUNTIME_DIR if set):
    - staging/ingest/
    - staging/analyzed/
    - staging/failed/{ingest,analyze,publish}/
    - state/runs/
    - state/failures/
    - logs/

    Note:
        For tests, create directories under tmp_path instead.
        This function is for CLI entry point use only.
    """
    staging = get_pm_staging_dir()
    state = get_pm_state_dir()
    logs = get_logs_dir()

    # Staging directories
    (staging / "ingest").mkdir(parents=True, exist_ok=True)
    (staging / "analyzed").mkdir(parents=True, exist_ok=True)
    (staging / "failed" / "ingest").mkdir(parents=True, exist_ok=True)
    (staging / "failed" / "analyze").mkdir(parents=True, exist_ok=True)
    (staging / "failed" / "publish").mkdir(parents=True, exist_ok=True)

    # State directories
    (state / "runs").mkdir(parents=True, exist_ok=True)
    (state / "failures").mkdir(parents=True, exist_ok=True)

    # Logs directory
    logs.mkdir(parents=True, exist_ok=True)


def clear_cache() -> None:
    """Clear cached project root and runtime directory.

    Useful for testing when YENGO_ROOT or YENGO_RUNTIME_DIR changes.
    """
    get_project_root.cache_clear()
    get_runtime_dir.cache_clear()


def rel_path(path: Path) -> str:
    """Format path as relative to project root for logging.

    Converts absolute paths to relative paths from project root for cleaner
    log output. Falls back to absolute path if conversion fails.

    Args:
        path: Path to format (can be absolute or relative).

    Returns:
        Relative path string from project root, or original string if
        the path is not under project root.

    Example:
        >>> rel_path(Path("/home/user/yen-go/.pm-runtime/staging/ogs/file.sgf"))
        '.pm-runtime/staging/ogs/file.sgf'
    """
    try:
        return path.relative_to(get_project_root()).as_posix()
    except ValueError:
        return path.as_posix()
