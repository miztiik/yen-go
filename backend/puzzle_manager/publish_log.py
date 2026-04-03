"""
Publish log for tracking puzzle publications.

Provides JSONL-based logging for rollback capability (Spec 036).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.puzzle_manager.models.publish_log import PublishLogEntry, PublishLogFile

logger = logging.getLogger("puzzle_manager.publish_log")


class PublishLogWriter:
    """Writes publish log entries to JSONL files.

    Files are organized by date: {YYYY-MM-DD}.jsonl
    Each line is a JSON object with run_id, id, source, path.

    Usage:
        writer = PublishLogWriter(log_dir=ops_dir / "publish-log")
        writer.write(entry)
        writer.write_batch(entries)

    Note:
        Spec 107: publish-log is under .puzzle-inventory-state/ (ops_dir)
    """

    def __init__(self, log_dir: Path) -> None:
        """Initialize writer.

        Args:
            log_dir: Publish log directory (REQUIRED)
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, date: datetime | None = None) -> Path:
        """Get log file path for a date.

        Args:
            date: Date for log file (default: today)

        Returns:
            Path to JSONL file.
        """
        if date is None:
            date = datetime.now(UTC)
        filename = date.strftime("%Y-%m-%d") + ".jsonl"
        return self.log_dir / filename

    def write(self, entry: PublishLogEntry) -> None:
        """Write a single entry to the log.

        Flushes to OS immediately to minimize crash-consistency window.

        Args:
            entry: Publish log entry to write.
        """
        now = datetime.now(UTC)
        log_path = self._get_log_path(now)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry.to_jsonl() + "\n")
            f.flush()
        logger.debug(f"Wrote publish log entry: {entry.puzzle_id}")

    def write_batch(self, entries: list[PublishLogEntry]) -> int:
        """Write multiple entries to the log.

        Args:
            entries: List of entries to write.

        Returns:
            Number of entries written.
        """
        if not entries:
            return 0

        now = datetime.now(UTC)
        log_path = self._get_log_path(now)
        with open(log_path, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.to_jsonl() + "\n")

        logger.info(f"Wrote {len(entries)} publish log entries")
        return len(entries)


class PublishLogReader:
    """Reads and searches publish log files.

    Provides methods for listing dates, reading entries, and searching
    by run_id, puzzle_id, or source.

    Usage:
        reader = PublishLogReader(log_dir=ops_dir / "publish-log")
        for entry in reader.search_by_run_id("a1b2c3d4e5f6"):
            print(entry.path)

    Note:
        Spec 107: publish-log is under .puzzle-inventory-state/ (ops_dir)
    """

    def __init__(self, log_dir: Path) -> None:
        """Initialize reader.

        Args:
            log_dir: Publish log directory (REQUIRED)
        """
        self.log_dir = log_dir

    def list_dates(self) -> list[str]:
        """List all dates with log files.

        Returns:
            Sorted list of date strings (YYYY-MM-DD).
        """
        if not self.log_dir.exists():
            return []

        dates = []
        for path in self.log_dir.glob("*.jsonl"):
            # Skip audit log
            if path.name == "rollback-audit.jsonl":
                continue
            # Extract date from filename
            date_str = path.stem  # "2026-01-29"
            if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
                dates.append(date_str)

        return sorted(dates)

    def list_files(self) -> list[PublishLogFile]:
        """List all log files with metadata.

        Returns:
            List of PublishLogFile objects.
        """
        files = []
        for date_str in self.list_dates():
            path = self.log_dir / f"{date_str}.jsonl"
            entry_count = sum(1 for _ in open(path, encoding="utf-8"))
            files.append(PublishLogFile(
                date=date_str,
                path=path,
                entry_count=entry_count,
            ))
        return files

    def read_date(self, date: str) -> Iterator[PublishLogEntry]:
        """Read all entries for a specific date.

        Skips corrupted/truncated JSONL lines with a warning instead of
        aborting the entire read. This makes the publish log self-healing
        after crashes that may truncate the last written line.

        Args:
            date: Date string in YYYY-MM-DD format.

        Yields:
            PublishLogEntry objects.
        """
        log_path = self.log_dir / f"{date}.jsonl"
        if not log_path.exists():
            return

        with open(log_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield PublishLogEntry.from_jsonl(line)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(
                        "Skipping corrupted publish log entry in %s line %d: %s",
                        log_path.name, line_num, e,
                    )
                    continue

    def read_all(self) -> Iterator[PublishLogEntry]:
        """Read all entries from all dates.

        Yields:
            PublishLogEntry objects in chronological order.
        """
        for date_str in self.list_dates():
            yield from self.read_date(date_str)

    def _scan_lines_with_needle(
        self,
        needle: str,
        field: str,
        value: str,
        *,
        first_only: bool = False,
    ) -> list[PublishLogEntry]:
        """Scan all JSONL files with a string pre-filter before JSON parsing.

        Checks ``needle in raw_line`` to skip most JSON deserialization,
        then verifies the parsed field matches exactly.  The needle is
        format-agnostic (works with both compact and pretty-printed JSON).

        Args:
            needle: Substring to check in raw line (e.g. '"p1"').
            field: Field name to verify after parsing.
            value: Expected field value.
            first_only: Stop after first match.

        Returns:
            List of matching entries.
        """
        results: list[PublishLogEntry] = []
        for date_str in self.list_dates():
            log_path = self.log_dir / f"{date_str}.jsonl"
            if not log_path.exists():
                continue
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    if needle not in line:
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = PublishLogEntry.from_jsonl(line)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
                    if getattr(entry, field) == value:
                        results.append(entry)
                        if first_only:
                            return results
        return results

    def search_by_run_id(self, run_id: str) -> list[PublishLogEntry]:
        """Find all entries for a pipeline run.

        Uses string pre-filter to avoid deserializing non-matching lines.

        Args:
            run_id: Pipeline run ID to search for.

        Returns:
            List of matching entries.
        """
        needle = f'"{run_id}"'
        return self._scan_lines_with_needle(needle, "run_id", run_id)

    def search_by_puzzle_id(self, puzzle_id: str) -> PublishLogEntry | None:
        """Find entry for a specific puzzle.

        Uses string pre-filtered scan over JSONL files.

        Args:
            puzzle_id: Puzzle ID to search for.

        Returns:
            Matching entry or None.
        """
        needle = f'"{puzzle_id}"'
        results = self._scan_lines_with_needle(
            needle, "puzzle_id", puzzle_id, first_only=True,
        )
        return results[0] if results else None

    def search_by_source(self, source: str) -> list[PublishLogEntry]:
        """Find all entries from a source adapter.

        Uses string pre-filter to avoid deserializing non-matching lines.

        Args:
            source: Source adapter name.

        Returns:
            List of matching entries.
        """
        needle = f'"{source}"'
        return self._scan_lines_with_needle(needle, "source_id", source)

    def find_by_trace_id(self, trace_id: str) -> PublishLogEntry | None:
        """Find entry by trace ID.

        Uses string pre-filtered scan over JSONL files.

        Args:
            trace_id: Trace ID to search for.

        Returns:
            Matching entry or None.
        """
        needle = f'"{trace_id}"'
        results = self._scan_lines_with_needle(
            needle, "trace_id", trace_id, first_only=True,
        )
        return results[0] if results else None

    def search_by_date_range(
        self,
        start_date: str,
        end_date: str,
    ) -> list[PublishLogEntry]:
        """Find all entries in a date range.

        Args:
            start_date: Start date (YYYY-MM-DD, inclusive).
            end_date: End date (YYYY-MM-DD, inclusive).

        Returns:
            List of matching entries.
        """
        results: list[PublishLogEntry] = []
        for date_str in self.list_dates():
            if start_date <= date_str <= end_date:
                results.extend(self.read_date(date_str))
        return results



    def get_run_ids(self) -> set[str]:
        """Get all unique run IDs in the logs.

        Returns:
            Set of run ID strings.
        """
        run_ids = set()
        for entry in self.read_all():
            run_ids.add(entry.run_id)
        return run_ids

    def count_entries(self) -> int:
        """Count total entries across all log files.

        Returns:
            Total entry count.
        """
        return sum(f.entry_count for f in self.list_files())

    def cleanup_old_logs(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Delete publish logs older than retention period (T045).

        IMPORTANT: This method NEVER deletes the audit log (FR-052).
        The audit log (audit.jsonl) is preserved indefinitely.

        Args:
            retention_days: Number of days to retain logs (default: 90)
            dry_run: If True, preview without deleting

        Returns:
            Dictionary with counts: {"deleted": N, "preserved": M, "skipped_audit": 1}
        """
        if not self.log_dir.exists():
            return {"deleted": 0, "preserved": 0, "skipped_audit": 0}

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        deleted = 0
        preserved = 0
        skipped_audit = 0

        for path in self.log_dir.glob("*.jsonl"):
            # NEVER delete audit log (FR-052)
            if path.name in ("audit.jsonl", "rollback-audit.jsonl"):
                skipped_audit += 1
                logger.info(f"Preserving audit log: {path.name}")
                continue

            # Extract date from filename
            date_str = path.stem
            if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
                # Not a date-formatted file, skip
                preserved += 1
                continue

            # Check if older than cutoff
            if date_str < cutoff_str:
                if dry_run:
                    logger.info(f"Would delete: {path.name}")
                else:
                    path.unlink()
                    logger.info(f"Deleted old log: {path.name}")
                deleted += 1
            else:
                preserved += 1

        return {
            "deleted": deleted,
            "preserved": preserved,
            "skipped_audit": skipped_audit,
        }
