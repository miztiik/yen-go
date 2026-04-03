"""
Performance benchmark tests for inventory operations at scale.

Marked @pytest.mark.slow — excluded from default test runs.
Run with: pytest -m slow

These benchmarks verify that operations complete within generous time
thresholds to catch performance regressions.
"""

from pathlib import Path

import pytest

from backend.puzzle_manager.models.publish_log import PublishLogEntry

pytestmark = [pytest.mark.slow]


# ---- helpers ----

def _make_publish_log_entry(idx: int, date_str: str = "2026-01-15") -> PublishLogEntry:
    """Create a publish log entry with deterministic but varied metadata."""
    levels = ["novice", "beginner", "elementary", "intermediate",
              "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"]
    tags_pool = [("ladder",), ("ko",), ("life-and-death",), ("snapback",),
                 ("ladder", "ko"), ("life-and-death", "snapback")]
    return PublishLogEntry(
        run_id=f"bench-{idx // 500:04d}",
        puzzle_id=f"YENGO-{idx:016x}",
        source_id="benchmark",
        path=f"sgf/{idx // 100:04d}/{idx:016x}.sgf",
        quality=min(idx % 5, 3),
        trace_id=f"{idx:016x}",
        level=levels[idx % len(levels)],
        tags=tuple(tags_pool[idx % len(tags_pool)]),
        collections=(),
    )


def _write_publish_log(log_dir: Path, entries: list[PublishLogEntry]) -> None:
    """Write entries to publish log JSONL files using date-formatted names.

    PublishLogReader.list_dates() only recognizes YYYY-MM-DD.jsonl filenames.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    batch_size = 500
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        file_idx = i // batch_size
        # Use YYYY-MM-DD format so PublishLogReader.list_dates() finds them
        log_file = log_dir / f"2026-01-{15 + file_idx:02d}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            for entry in batch:
                f.write(entry.to_jsonl() + "\n")

