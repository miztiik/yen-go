"""
Configuration module for the puzzle manager.

Provides ConfigLoader for loading and validating configuration.
"""

from backend.puzzle_manager.config.loader import ConfigLoader, get_config

__all__ = ["ConfigLoader", "get_config"]
