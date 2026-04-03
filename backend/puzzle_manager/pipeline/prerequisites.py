"""
Prerequisites check for pipeline execution.

Verifies system state before pipeline runs.
"""

import logging
from pathlib import Path

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.paths import (
    get_backend_dir,
    get_project_root,
)

logger = logging.getLogger("puzzle_manager.pipeline.prerequisites")


def check_prerequisites(
    staging_dir: Path,
    state_dir: Path,
    output_dir: Path,
) -> list[str]:
    """Check all prerequisites for pipeline execution.

    Args:
        staging_dir: Staging directory
        state_dir: State directory
        output_dir: Output directory

    Returns:
        List of error messages (empty if all prerequisites pass)
    """
    errors: list[str] = []

    # Check project structure
    errors.extend(_check_project_structure())

    # Check configuration
    errors.extend(_check_configuration())

    # Check write permissions
    errors.extend(_check_write_permissions(staging_dir, state_dir, output_dir))

    if errors:
        logger.warning(f"Prerequisites check failed: {len(errors)} errors")
    else:
        logger.info("Prerequisites check passed")

    return errors


def _check_project_structure() -> list[str]:
    """Check project directory structure exists."""
    errors = []

    root = get_project_root()
    if not root.exists():
        errors.append(f"Project root not found: {root}")
        return errors  # Can't continue without root

    backend_dir = get_backend_dir()
    if not backend_dir.exists():
        errors.append(f"Backend directory not found: {backend_dir}")

    return errors


def _check_configuration() -> list[str]:
    """Check configuration files exist and are valid."""
    errors = []

    try:
        loader = ConfigLoader()

        # Try to load main config
        config = loader.load_pipeline_config()

        # Check required config values
        if config.batch.size < 1:
            errors.append(f"Invalid batch size: {config.batch.size}")

        if config.retention.days < 1:
            errors.append(f"Invalid retention days: {config.retention.days}")

    except Exception as e:
        errors.append(f"Configuration error: {e}")

    return errors


def _check_write_permissions(
    staging_dir: Path,
    state_dir: Path,
    output_dir: Path,
) -> list[str]:
    """Check write permissions for required directories.

    Args:
        staging_dir: Staging directory
        state_dir: State directory
        output_dir: Output directory
    """
    errors = []

    directories = [
        staging_dir,
        state_dir,
        output_dir,
    ]

    for directory in directories:
        try:
            # Ensure directory exists
            directory.mkdir(parents=True, exist_ok=True)

            # Try to write a test file
            test_file = directory / ".write_test"
            test_file.write_text("test")
            test_file.unlink()

        except PermissionError:
            errors.append(f"No write permission: {directory}")
        except Exception as e:
            errors.append(f"Directory error for {directory}: {e}")

    return errors


def check_source_availability() -> dict[str, bool]:
    """Check availability of configured sources.

    Returns:
        Dict of source_id -> availability status
    """
    from backend.puzzle_manager.adapters._registry import create_adapter
    from backend.puzzle_manager.config.loader import ConfigLoader

    loader = ConfigLoader()
    sources = [s for s in loader.load_sources() if getattr(s, 'enabled', True)]

    status = {}
    for source in sources:
        try:
            adapter = create_adapter(source.adapter, source.config.model_dump())
            # Check if adapter can reach source
            status[source.id] = adapter.is_available()
        except Exception as e:
            logger.debug(f"Source {source.id} not available: {e}")
            status[source.id] = False

    return status
