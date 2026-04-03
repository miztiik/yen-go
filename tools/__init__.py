"""
Tools for Yen-Go project.

This package contains download tools and core utilities for
importing puzzles from external sources.

Structure:
    core/       - Shared utilities (paths, batching, checkpoint, logging, http)
    ogs/        - OGS (Online-Go.com) downloader
    t-dragon/   - TsumegoDragon downloader

Usage:
    from tools.core import get_project_root, rel_path, to_posix_path

ARCHITECTURE BOUNDARY - DO NOT IMPORT FROM backend.*
=====================================================
Tools in this package MUST NOT import from backend.puzzle_manager.*.
These are separate codebases with different responsibilities:

  - tools/     = External source ingestors (download from web)
  - backend/   = Pipeline processing (ingest → analyze → publish)

Use tools.core.* for shared utilities:
  - tools.core.paths:      get_project_root, rel_path, to_posix_path
  - tools.core.http:       HttpClient, calculate_backoff_with_jitter
  - tools.core.logging:    setup_logging, StructuredLogger, EventType
  - tools.core.batching:   get_batch_for_file, BatchInfo
  - tools.core.checkpoint: ToolCheckpoint, load_checkpoint, save_checkpoint

If tools.core is missing functionality that exists in backend.puzzle_manager.core,
COPY the implementation to tools.core - do not import across the boundary.
"""

from tools.core import (
    get_project_root,
    rel_path,
    to_posix_path,
)

__all__ = [
    "get_project_root",
    "rel_path",
    "to_posix_path",
]
