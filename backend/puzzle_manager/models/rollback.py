"""
Rollback data models for atomic rollback operations.

Models for rollback transactions and audit trail.
PublishLogEntry and PublishLogFile are in models/publish_log.py (core models).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Literal

# Import core publish log models (used by rollback but not rollback-specific)
# Re-export for backward compatibility with rollback.py imports
from backend.puzzle_manager.models.publish_log import (  # noqa: F401
    PublishLogEntry,
    PublishLogFile,
)

# Lock is considered stale after 1 hour (per FR-027)
STALE_THRESHOLD = timedelta(hours=1)


class TransactionStatus(Enum):
    """Status of a rollback transaction."""

    PENDING = "pending"           # Created, not started
    IN_PROGRESS = "in_progress"   # Transaction started
    BACKING_UP = "backing_up"     # Creating backups
    DELETING = "deleting"         # Deleting files
    UPDATING_INDEXES = "updating_indexes"
    COMMITTED = "committed"       # Successfully committed
    COMPLETED = "completed"       # Success (alias)
    FAILED = "failed"             # Error during execution
    ROLLED_BACK = "rolled_back"   # Restored from backup


@dataclass
class RollbackTransaction:
    """Tracks state of an in-progress rollback for atomicity.

    Enables restore-on-failure by tracking:
    - Which files were backed up
    - Which files were deleted
    - Current status
    """

    transaction_id: str              # Unique ID (timestamp-UUID)
    started_at: datetime
    backup_dir: Path                 # yengo-puzzle-collections/.rollback-backup/{transaction_id}/
    status: TransactionStatus = TransactionStatus.PENDING

    # File tracking (used by TransactionManager)
    affected_files: list[str] = field(default_factory=list)
    affected_indexes: list[str] = field(default_factory=list)

    # Completion tracking
    completed_at: datetime | None = None
    error_message: str | None = None

    def can_restore(self) -> bool:
        """Check if restoration is possible."""
        return (
            self.status in (TransactionStatus.FAILED, TransactionStatus.DELETING)
            and len(self.affected_files) > 0
            and self.backup_dir.exists()
        )


@dataclass
class LockFileContent:
    """Contents of the .rollback.lock file.

    JSON format:
    {"operation_id": "rollback-xxx", "started_at": "2026-01-29T14:30:22", "pid": 12345}
    """

    operation_id: str
    started_at: str  # ISO format datetime string
    pid: int

    def is_stale(self, threshold: timedelta = STALE_THRESHOLD) -> bool:
        """Check if lock has expired (older than threshold)."""
        started = datetime.fromisoformat(self.started_at)
        return datetime.now(UTC) > started + threshold

    def is_owned_by_current_process(self) -> bool:
        """Check if this process owns the lock."""
        return self.pid == os.getpid()

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "operation_id": self.operation_id,
            "started_at": self.started_at,
            "pid": self.pid,
        })

    @classmethod
    def from_json(cls, data: str) -> LockFileContent:
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            operation_id=obj["operation_id"],
            started_at=obj["started_at"],
            pid=obj["pid"],
        )

    @classmethod
    def create_new(cls, operation_id: str) -> LockFileContent:
        """Create a new lock for current process."""
        return cls(
            operation_id=operation_id,
            started_at=datetime.now(UTC).isoformat(),
            pid=os.getpid(),
        )


@dataclass
class RollbackRequest:
    """Parameters for a rollback operation."""

    mode: Literal["by_run", "by_puzzles"]

    # One of these must be set based on mode
    run_id: str | None = None
    puzzle_ids: list[str] | None = None

    # Options
    dry_run: bool = False
    skip_confirmation: bool = False
    verify: bool = False

    def validate(self) -> list[str]:
        """Return list of validation errors."""
        errors = []
        if self.mode == "by_run" and not self.run_id:
            errors.append("run_id required for by_run mode")
        if self.mode == "by_puzzles" and not self.puzzle_ids:
            errors.append("puzzle_ids required for by_puzzles mode")
        if self.puzzle_ids and len(self.puzzle_ids) > 10000:
            errors.append("Maximum 10,000 puzzles per rollback (FR-065)")
        return errors


@dataclass
class RollbackResult:
    """Complete result of a rollback operation.

    Returned by RollbackManager methods.
    """

    # Outcome
    success: bool
    dry_run: bool = False

    # Statistics (simplified for CLI usage)
    puzzles_affected: int = 0
    files_deleted: int = 0
    indexes_updated: int = 0

    # Transaction tracking (T037 --verify support)
    transaction_id: str = ""

    # Verification (--verify flag)
    verified: bool = False
    verification_errors: list[str] = field(default_factory=list)

    # Inventory update status (Principal Staff Engineer Review)
    inventory_update_failed: bool = False
    inventory_update_error: str | None = None

    # Errors
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary for CLI output."""
        if self.dry_run:
            return f"DRY RUN: Would affect {self.puzzles_affected} puzzles ({self.files_deleted} files)"
        if self.success:
            return f"Removed {self.puzzles_affected} puzzles ({self.files_deleted} files)"
        return f"FAILED: {'; '.join(self.errors)}"


@dataclass
class AuditLogEntry:
    """Immutable record of a rollback operation.

    Stored in audit.jsonl in JSONL format.
    Used by AuditLogWriter for all rollback audit events.
    """

    timestamp: datetime
    action: str                  # e.g., "rollback_start", "rollback_complete", "rollback_failed"
    operator: str                # System user who ran command
    transaction_id: str          # Transaction ID for correlation
    target: str                  # What was targeted (e.g., "run_id:abc123")
    reason: str                  # Reason for rollback
    details: dict[str, Any]      # Additional details (files_deleted, errors, etc.)

    def to_jsonl(self) -> str:
        """Serialize to compact JSON line."""
        data = {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "operator": self.operator,
            "transaction_id": self.transaction_id,
            "target": self.target,
            "reason": self.reason,
            "details": self.details,
        }
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_jsonl(cls, line: str) -> AuditLogEntry:
        """Parse from JSON line."""
        data = json.loads(line.strip())
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action=data["action"],
            operator=data["operator"],
            transaction_id=data.get("transaction_id", ""),
            target=data.get("target", ""),
            reason=data.get("reason", ""),
            details=data.get("details", {}),
        )
