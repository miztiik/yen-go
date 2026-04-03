"""
Exception hierarchy for the puzzle manager.

All exceptions inherit from PuzzleManagerError for easy catching.
"""

from typing import Any


class PuzzleManagerError(Exception):
    """Base exception for all puzzle manager errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


# Configuration Errors
class ConfigurationError(PuzzleManagerError):
    """Error loading or validating configuration."""


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file not found."""


class ConfigValidationError(ConfigurationError):
    """Configuration validation failed."""


# Path Errors
class PathError(PuzzleManagerError):
    """Error related to path resolution."""


class ProjectRootError(PathError):
    """Cannot detect project root directory."""


# Pipeline Errors
class PipelineError(PuzzleManagerError):
    """Error during pipeline execution."""


class StageError(PipelineError):
    """Error in a pipeline stage."""


class PrerequisiteError(PipelineError):
    """Pipeline prerequisites not met."""


class ResumeError(PipelineError):
    """Error resuming an interrupted run."""


# Adapter Errors
class AdapterError(PuzzleManagerError):
    """Error in a source adapter."""


class AdapterNotFoundError(AdapterError):
    """Requested adapter not found in registry."""


class AdapterConfigError(AdapterError):
    """Adapter configuration error."""


class FetchError(AdapterError):
    """Error fetching puzzles from source."""


# SGF Errors
class SGFError(PuzzleManagerError):
    """Error parsing or building SGF."""


class SGFParseError(SGFError):
    """Error parsing SGF content."""


class SGFValidationError(SGFError):
    """SGF content validation failed."""


class SGFBuildError(SGFError):
    """Error building SGF content."""


# State Errors
class StateError(PuzzleManagerError):
    """Error managing pipeline state."""


class StateLoadError(StateError):
    """Error loading state file."""


class StateSaveError(StateError):
    """Error saving state file."""


# Classification Errors
class ClassificationError(PuzzleManagerError):
    """Error classifying puzzle difficulty."""


# Tagging Errors
class TaggingError(PuzzleManagerError):
    """Error detecting puzzle techniques."""


class InvalidTagError(TaggingError):
    """Tag not in approved tag list."""


# Daily Generation Errors
class DailyGenerationError(PuzzleManagerError):
    """Error generating daily challenges."""


class InsufficientPuzzlesError(DailyGenerationError):
    """Not enough puzzles available for generation."""


# Cleanup Errors
class CleanupError(PuzzleManagerError):
    """Error during cleanup operations."""


class RetentionViolationError(CleanupError):
    """Attempted to clean files newer than minimum retention period."""
