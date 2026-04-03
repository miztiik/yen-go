"""Unified audit log for collection-mutating operations.

Records high-level operations (publish, cleanup, rollback) to audit.jsonl
as an append-only JSONL file in .puzzle-inventory-state/.

Each entry captures:
- What operation occurred (publish, cleanup)
- When it happened (ISO 8601 timestamp)
- Summary metrics (files published/deleted by category)
- Context (source, run_id, paths cleared)

The publish-log/ directory contains per-puzzle detail; audit.jsonl provides
the high-level operation journal.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("puzzle_manager.audit")


@dataclass
class AuditEntry:
    """Audit entry for collection-mutating operations.

    Supports multiple operation types (cleanup, publish) with
    operation-specific detail fields.

    Attributes:
        timestamp: ISO 8601 timestamp of the operation.
        operation: Operation type ("cleanup", "publish").
        target: What was affected (e.g., "puzzles-collection").
        details: Operation-specific metrics and context.
    """
    timestamp: str
    operation: str
    target: str
    details: dict[str, Any]


def write_audit_entry(
    audit_file: Path,
    operation: str,
    target: str,
    details: dict[str, Any],
) -> None:
    """Write an audit entry to the append-only audit log.

    Args:
        audit_file: Path to audit.jsonl file.
        operation: Operation type (e.g., "cleanup", "publish").
        target: What was affected (e.g., "puzzles-collection").
        details: Operation-specific metrics dict.
    """
    entry = AuditEntry(
        timestamp=datetime.now(UTC).isoformat(),
        operation=operation,
        target=target,
        details=details,
    )

    # Ensure parent directory exists
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")

    logger.info(
        "Wrote audit entry: operation=%s, target=%s, details=%s",
        operation, target, details,
    )
