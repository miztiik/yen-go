"""Shared logging utilities for YenGo project.

Provides centralized logging configuration that reads from config/logging.json.
Used by both puzzle_manager and tools to ensure all logs go to a single location.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def get_repo_root() -> Path:
    """Find the repository root by looking for config/logging.json.
    
    Walks up the directory tree from this file's location until it finds
    the config directory with logging.json.
    
    Returns:
        Path to repository root
        
    Raises:
        FileNotFoundError: If repo root cannot be determined
    """
    current = Path(__file__).resolve().parent
    
    # Walk up to find config/logging.json
    for _ in range(10):  # Max 10 levels up
        if (current / "config" / "logging.json").exists():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    raise FileNotFoundError(
        "Could not find repository root (config/logging.json not found)"
    )


def load_logging_config() -> dict[str, Any]:
    """Load logging configuration from config/logging.json.
    
    Returns:
        Dictionary with logging configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    repo_root = get_repo_root()
    config_path = repo_root / "config" / "logging.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Logging config not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_log_directory(component: str = "puzzle_manager") -> Path:
    """Get the log directory for a component.
    
    Args:
        component: Component name - "puzzle_manager" or tool name like "101weiqi"
        
    Returns:
        Absolute path to log directory
    """
    repo_root = get_repo_root()
    config = load_logging_config()
    
    log_root = repo_root / config.get("log_root", "logs")
    subdirs = config.get("subdirectories", {})
    
    # Check if component is puzzle_manager
    if component == "puzzle_manager":
        subdir = subdirs.get("puzzle_manager", "puzzle_manager")
        return log_root / subdir
    
    # For tools, put under tools subdirectory
    tools_subdir = subdirs.get("tools", "tools")
    return log_root / tools_subdir / component


def setup_shared_logging(
    component: str,
    logger_name: str | None = None,
    level: str | None = None,
    console: bool = True,
    file_logging: bool = True,
    use_rotation: bool = True,
    log_filename: str | None = None,
    run_id: str | None = None,
) -> logging.Logger:
    """Set up logging for any YenGo component.
    
    Reads configuration from config/logging.json and creates appropriate
    handlers for console and file output.
    
    Args:
        component: Component name (e.g., "puzzle_manager", "101weiqi", "gotools")
        logger_name: Name for the logger (defaults to component name)
        level: Log level override (uses config default if not specified)
        console: Enable console logging
        file_logging: Enable file logging
        use_rotation: Use rotating file handler
        log_filename: Custom log filename (without .log extension)
        run_id: Optional run ID for unique log filenames
        
    Returns:
        Configured logger instance
    """
    config = load_logging_config()
    
    # Determine log level
    log_level = level or config.get("default_level", "INFO")
    
    # Get logger
    name = logger_name or component
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()  # Clear any existing handlers
    
    # Create formatter
    fmt = config.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    date_fmt = config.get("date_format", "%Y-%m-%d %H:%M:%S")
    formatter = logging.Formatter(fmt, datefmt=date_fmt)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_logging:
        log_dir = get_log_directory(component)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        rotation_config = config.get("rotation", {})
        
        if use_rotation and rotation_config.get("enabled", True):
            # Determine filename
            if log_filename:
                filename = f"{log_filename}.log"
            else:
                filename = f"{component}.log"
            
            log_file = log_dir / filename
            
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when=rotation_config.get("when", "midnight"),
                backupCount=rotation_config.get("backup_count", 45),
                encoding="utf-8",
            )
        else:
            # Use timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if run_id:
                filename = f"run_{timestamp}_{run_id[:8]}.log"
            elif log_filename:
                filename = f"{log_filename}_{timestamp}.log"
            else:
                filename = f"{component}_{timestamp}.log"
            
            log_file = log_dir / filename
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.debug(f"Log file: {log_file}")
    
    return logger


def setup_tool_logging(
    tool_name: str,
    verbose: bool = False,
    run_id: str | None = None,
) -> logging.Logger:
    """Convenience function for tool scripts.
    
    Sets up logging with a unique timestamped log file for each run.
    
    Args:
        tool_name: Name of the tool (e.g., "101weiqi", "gotools")
        verbose: Enable DEBUG level output
        run_id: Optional run ID for log filename
        
    Returns:
        Configured logger instance
    """
    level = "DEBUG" if verbose else "INFO"
    
    return setup_shared_logging(
        component=tool_name,
        logger_name=f"{tool_name}_ingestor",
        level=level,
        use_rotation=False,  # Tools use timestamped files per run
        run_id=run_id,
    )
