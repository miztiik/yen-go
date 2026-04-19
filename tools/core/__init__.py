"""
Core utilities for download tools.

This package provides shared functionality across all download tools
(OGS, TsumegoDragon, etc.), inspired by backend/puzzle_manager/core/.

Modules:
    atomic_write: Cross-platform atomic file writes (temp + rename)
    batching: Batch directory management (batch-001, batch-002, etc.)
    checkpoint: Resume support with JSON checkpoint files
    chinese_translator: Chinese Go term translation (config/cn-en-dictionary.json)
    collection_matcher: Shared phrase matcher for collection name → slug resolution
    http: HTTP client with retry, rate limiting, backoff
    logging: Structured logging (console + JSON file)
    paths: Path utilities (project root, relative paths, POSIX normalization)
    rate_limit: Timestamp-based rate limiting (overlaps wait with processing)
    sgf_structural_checks: SGF structural validation (parseability, stones, moves, etc.)
    validation: Source-agnostic puzzle validation (board size, solution, etc.)

Design Principles:
    - DRY: Share common functionality, don't duplicate
    - KISS: Simple, focused modules
    - Configurable: Paths defined in one place
    - Testable: Use --dry-run, batch_size=1 for tests

Usage:
    from tools.core.atomic_write import atomic_write_json, atomic_write_text
    from tools.core.batching import get_batch_for_file, BatchInfo
    from tools.core.checkpoint import ToolCheckpoint, load_checkpoint, save_checkpoint
    from tools.core.chinese_translator import ChineseTranslator, get_chinese_translator, translate_chinese_text
    from tools.core.http import HttpClient, calculate_backoff_with_jitter
    from tools.core.logging import setup_logging, StructuredLogger, EventType
    from tools.core.paths import get_project_root, rel_path, to_posix_path
    from tools.core.rate_limit import RateLimiter, wait_with_jitter
    from tools.core.validation import validate_puzzle, validate_sgf_puzzle
"""

from tools.core.atomic_write import (
    atomic_write_json,
    atomic_write_text,
)
from tools.core.batching import (
    BATCH_STATE_SCHEMA_VERSION,
    DEFAULT_BATCH_SIZE,
    BatchInfo,
    BatchState,
    count_total_files,
    find_existing_batches,
    get_batch_for_file,
    get_batch_for_file_fast,
    get_batch_summary,
    get_current_batch,
)
from tools.core.checkpoint import (
    CHECKPOINT_FILENAME,
    CHECKPOINT_VERSION,
    ToolCheckpoint,
    checkpoint_exists,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from tools.core.chinese_translator import (
    ChineseTranslator,
    get_chinese_translator,
    translate_chinese_text,
)
from tools.core.chinese_translator import (
    TranslationError as ChineseTranslationError,
)
from tools.core.chinese_translator import (
    TranslationResult as ChineseTranslationResult,
)
from tools.core.http import (
    HttpClient,
    HttpError,
    RateLimitError,
    add_jitter,
    calculate_backoff_with_jitter,
)
from tools.core.logging import (
    EventType,
    StructuredLogger,
    format_duration,
    get_logger,
    setup_logging,
)
from tools.core.paths import (
    TOOL_OUTPUT_DIRS,
    get_external_sources_dir,
    get_project_root,
    get_tool_output_dir,
    rel_path,
    to_posix_path,
)
from tools.core.rate_limit import (
    RateLimiter,
    wait_with_jitter,
)
from tools.core.rate_limit import (
    add_jitter as rate_limit_add_jitter,  # Also available from http module
)
from tools.core.text_cleaner import (
    GO_TERMS,
    NON_LATIN_RE,
    # Comment cleaning
    clean_comment_text,
    # Collection name processing
    clean_name,
    extract_english_portion,
    generate_slug,
    infer_curator,
    infer_type,
    normalize_text,
    sanitize_for_training,
    strip_boilerplate,
    strip_cjk,
    strip_html,
    strip_urls,
)
from tools.core.sgf_structural_checks import (
    IssueCode,
    StructuralCheckResult,
    StructuralIssue,
    StructuralIssueSeverity,
    run_structural_checks,
)
from tools.core.go_teaching_constants import (
    EXPLANATION_KEYWORDS,
    GO_TECHNIQUE_PATTERN,
    GO_TECHNIQUES,
    MARKER_ONLY_PATTERNS,
)
from tools.core.teaching_schema import (
    TeachingComments,
    TeachingOutput,
    parse_teaching_output,
)
from tools.core.validation import (
    PuzzleValidationConfig,
    PuzzleValidationResult,
    count_solution_moves_in_sgf,
    count_stones_in_sgf,
    extract_board_size_from_sgf,
    validate_puzzle,
    validate_sgf_puzzle,
)

__all__ = [
    # paths
    "get_project_root",
    "rel_path",
    "to_posix_path",
    "get_external_sources_dir",
    "get_tool_output_dir",
    "TOOL_OUTPUT_DIRS",
    # atomic_write
    "atomic_write_json",
    "atomic_write_text",
    # batching
    "BatchInfo",
    "BatchState",
    "get_batch_for_file",
    "get_batch_for_file_fast",
    "get_current_batch",
    "find_existing_batches",
    "count_total_files",
    "get_batch_summary",
    "DEFAULT_BATCH_SIZE",
    "BATCH_STATE_SCHEMA_VERSION",
    # checkpoint
    "ToolCheckpoint",
    "load_checkpoint",
    "save_checkpoint",
    "clear_checkpoint",
    "checkpoint_exists",
    "CHECKPOINT_FILENAME",
    "CHECKPOINT_VERSION",
    # logging
    "setup_logging",
    "get_logger",
    "StructuredLogger",
    "EventType",
    "format_duration",
    # http
    "HttpClient",
    "HttpError",
    "RateLimitError",
    "calculate_backoff_with_jitter",
    "add_jitter",
    # rate_limit
    "RateLimiter",
    "wait_with_jitter",
    # sgf_structural_checks
    "IssueCode",
    "StructuralCheckResult",
    "StructuralIssue",
    "StructuralIssueSeverity",
    "run_structural_checks",
    # validation
    "PuzzleValidationResult",
    "PuzzleValidationConfig",
    "validate_puzzle",
    "validate_sgf_puzzle",
    "extract_board_size_from_sgf",
    "count_stones_in_sgf",
    "count_solution_moves_in_sgf",
    # text_cleaner - comment cleaning
    "clean_comment_text",
    "strip_html",
    "strip_urls",
    "strip_cjk",
    "strip_boilerplate",
    "normalize_text",
    # text_cleaner - collection name processing
    "clean_name",
    "generate_slug",
    "extract_english_portion",
    "infer_curator",
    "infer_type",
    "NON_LATIN_RE",
    "GO_TERMS",
    # chinese_translator
    "ChineseTranslator",
    "ChineseTranslationError",
    "ChineseTranslationResult",
    "get_chinese_translator",
    "translate_chinese_text",
    # go_teaching_constants
    "MARKER_ONLY_PATTERNS",
    "GO_TECHNIQUES",
    "GO_TECHNIQUE_PATTERN",
    "EXPLANATION_KEYWORDS",
    # teaching_schema
    "TeachingComments",
    "TeachingOutput",
    "parse_teaching_output",
]

