"""
Core utilities for the puzzle manager.

This module provides SGF parsing, building, board simulation, and classification.
"""

from backend.puzzle_manager.core.atomic_write import (
    atomic_write_json,
    atomic_write_text,
)
from backend.puzzle_manager.core.board import Board
from backend.puzzle_manager.core.checkpoint import CHECKPOINT_SCHEMA_VERSION, AdapterCheckpoint
from backend.puzzle_manager.core.classifier import classify_difficulty
from backend.puzzle_manager.core.constants import (
    LEVEL_TO_SLUG,
    MAX_LEVEL,
    MIN_LEVEL,
    SLUG_TO_LEVEL,
    VALID_LEVEL_SLUGS,
    VALID_LEVEL_SLUGS_ORDERED,
    get_valid_level_slugs,
)
from backend.puzzle_manager.core.coordinates import point_to_sgf, sgf_to_point
from backend.puzzle_manager.core.fs_utils import (
    cleanup_processed_files,
    extract_level_from_path,
    is_directory_empty,
    remove_empty_directories,
)
from backend.puzzle_manager.core.http import HttpClient, calculate_backoff_with_jitter
from backend.puzzle_manager.core.move_alternation import (
    MoveAlternationAnalysis,
    MoveAlternationDetector,
    MoveAlternationResult,
)
from backend.puzzle_manager.core.primitives import Color, Move, Point
from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleData,
    PuzzleValidator,
    RejectionReason,
    ValidationConfig,
    ValidationResult,
    validate_puzzle,
)
from backend.puzzle_manager.core.schema import YENGO_SGF_VERSION
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode, YenGoProperties, parse_sgf
from backend.puzzle_manager.core.sgf_publisher import publish_sgf
from backend.puzzle_manager.core.sgf_utils import escape_sgf_value
from backend.puzzle_manager.core.tagger import detect_techniques
from backend.puzzle_manager.core.trace_utils import generate_trace_id
from backend.puzzle_manager.core.validation_stats import ValidationStatsCollector

__all__ = [
    # Primitives
    "Color",
    "Move",
    "Point",
    # Coordinates
    "sgf_to_point",
    "point_to_sgf",
    # Board
    "Board",
    # SGF Parsing
    "parse_sgf",
    "SGFGame",
    "SolutionNode",
    "YenGoProperties",
    # SGF Building
    "SGFBuilder",
    # SGF Publishing
    "publish_sgf",
    # Classification
    "classify_difficulty",
    # Tagging
    "detect_techniques",
    # HTTP
    "HttpClient",
    "calculate_backoff_with_jitter",
    # Schema
    "YENGO_SGF_VERSION",
    # Constants
    "SLUG_TO_LEVEL",
    "LEVEL_TO_SLUG",
    "VALID_LEVEL_SLUGS",
    "VALID_LEVEL_SLUGS_ORDERED",
    "MIN_LEVEL",
    "MAX_LEVEL",
    "get_valid_level_slugs",
    # SGF Utils
    "escape_sgf_value",
    # FS Utils
    "remove_empty_directories",
    "is_directory_empty",
    "cleanup_processed_files",
    "extract_level_from_path",
    # Puzzle Validation (Spec 108)
    "PuzzleValidator",
    "PuzzleData",
    "ValidationConfig",
    "ValidationResult",
    "RejectionReason",
    "validate_puzzle",
    # Validation Statistics (Spec 108)
    "ValidationStatsCollector",
    # Trace (Spec 110)
    "generate_trace_id",
    # Checkpoint (Spec 109)
    "AdapterCheckpoint",
    # Move Alternation (Spec 117)
    "MoveAlternationDetector",
    "MoveAlternationResult",
    "MoveAlternationAnalysis",
    # Atomic Write
    "atomic_write_text",
    "atomic_write_json",
]
