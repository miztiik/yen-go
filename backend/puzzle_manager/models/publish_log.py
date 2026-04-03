"""
Publish log data models.

Models for tracking published puzzles in JSONL format.
These are core models used by publish, rebuild, rollback, and CLI modules.

Design Note (Spec 102, Principal Staff Engineer Review):
- PublishLogEntry is a CORE model, not rollback-specific
- Placed here for proper Single Responsibility Principle (SRP)
- Used by: publish_log.py, stages/publish.py, inventory/rebuild.py, rollback.py, cli.py

Spec 107: Added tags field for rollback tag decrement support.
Spec 110: Added trace_id field for end-to-end provenance tracking.
Spec 138: Added level and collections fields for complete rollback index coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PublishLogEntry:
    """Immutable record of a puzzle publication.

    Stored as single JSON line in JSONL format:
    {"run_id":"20260129-abc12345","puzzle_id":"gp-12345","source_id":"goproblems","path":"sgf/beginner/batch-0001/gp-12345.sgf","tags":["life-and-death","corner"],"trace_id":"a1b2c3d4e5f67890"}

    Note: run_id format changed in schema v6 (spec-041):
    - New format: YYYYMMDD-xxxxxxxx (date prefix + 8 hex chars)
    - Legacy format: 12 hex chars (still accepted for backward compatibility)

    Field naming (spec 043):
    - puzzle_id: Matches FetchResult.puzzle_id, search_by_puzzle_id(), CLI args
    - source_id: Matches StageContext.source_id, adapter registry terminology

    Spec 102: Added quality field for quality breakdown tracking.
    Spec 107: Added tags field for rollback tag decrement support.
    Spec 110: Added trace_id field for end-to-end provenance tracking.
    Spec 138: Added level and collections fields so the publish log stores ALL
             index-relevant data, enabling surgical rollback of every affected index.

    Performance plan: All core fields are MANDATORY (clean-slate migration).
    No backward compatibility — publish log entries must include all metadata.
    This eliminates all fallback/scan paths in rebuild and rollback.
    """

    run_id: str        # Pipeline run ID (YYYYMMDD-xxxxxxxx or legacy 12-char hex)
    puzzle_id: str     # Unique puzzle ID (was: id)
    source_id: str     # Source adapter name (was: source)
    path: str          # Relative path from collections root
    quality: int       # Spec 102: Quality level (1-5) — MANDATORY
    trace_id: str      # Spec 110: Trace ID for end-to-end provenance — MANDATORY
    level: str         # Spec 138: Level slug for targeted rollback index updates — MANDATORY
    tags: tuple[str, ...] = field(default_factory=tuple)  # Spec 107: Tags for rollback support
    collections: tuple[str, ...] = field(default_factory=tuple)  # Spec 138: Collections for rollback

    def to_jsonl(self) -> str:
        """Serialize to compact JSON line (no trailing newline).

        All fields are always written — no conditional guards.
        Clean-slate migration: all fields are mandatory.
        """
        data: dict[str, str | int | list[str]] = {
            "run_id": self.run_id,
            "puzzle_id": self.puzzle_id,
            "source_id": self.source_id,
            "path": self.path,
            "quality": self.quality,
            "tags": list(self.tags),
            "trace_id": self.trace_id,
            "level": self.level,
            "collections": list(self.collections),
        }
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_jsonl(cls, line: str) -> PublishLogEntry:
        """Parse from JSON line.

        Clean-slate migration: core fields are mandatory (raises KeyError if missing).
        """
        data = json.loads(line.strip())
        tags_data = data["tags"]
        collections_data = data["collections"]
        return cls(
            run_id=data["run_id"],
            puzzle_id=data["puzzle_id"],
            source_id=data["source_id"],
            path=data["path"],
            quality=data["quality"],
            tags=tuple(tags_data) if tags_data else (),
            trace_id=data["trace_id"],
            level=data["level"],
            collections=tuple(collections_data) if collections_data else (),
        )


@dataclass
class PublishLogFile:
    """Metadata about a publish log file.

    Files are named by date: {YYYY-MM-DD}.jsonl
    """

    date: str          # YYYY-MM-DD format
    path: Path         # Absolute path to file
    entry_count: int   # Number of entries (lines)

    @property
    def filename(self) -> str:
        return f"{self.date}.jsonl"
