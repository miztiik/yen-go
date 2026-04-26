"""Run history tracker -- append-only log for tracking performance over time.

Each eval run appends one record to runs/history.jsonl with:
- Prompt version, change summary, timestamp
- Weighted score, per-dimension averages
- Timing and token metrics
- Puzzle set hash (to detect repetition)

This enables plotting score progression across prompt iterations.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_RUNS_DIR = Path(__file__).resolve().parent / "runs"
_HISTORY_FILE = _RUNS_DIR / "history.jsonl"


@dataclass
class RunRecord:
    """One row in the history log."""
    run_id: str                        # timestamp-based ID
    timestamp: str                     # ISO 8601
    prompt_version: str
    change_summary: str                # what changed vs previous version
    n_puzzles: int
    puzzle_set_hash: str               # SHA256 of sorted puzzle IDs
    weighted_avg: float                # 0.0-1.0
    dimension_avgs: dict[str, float]   # per-dimension averages
    pass_rate: float                   # % scoring >= 0.6
    empty_content_count: int
    avg_think_tokens: float
    avg_content_tokens: float
    avg_elapsed_s: float
    total_elapsed_s: float
    judge_weighted_avg: float | None = None  # Layer C score if available
    judge_dimension_avgs: dict[str, float] = field(default_factory=dict)


def compute_puzzle_set_hash(puzzle_ids: list[str]) -> str:
    """Deterministic hash of the puzzle set for repetition detection."""
    combined = ",".join(sorted(puzzle_ids))
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def append_record(record: RunRecord) -> Path:
    """Append a run record to history.jsonl. Returns the history file path."""
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with _HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    logger.info("Appended run %s to %s", record.run_id, _HISTORY_FILE)
    return _HISTORY_FILE


def load_history() -> list[RunRecord]:
    """Load all run records from history.jsonl."""
    if not _HISTORY_FILE.exists():
        return []
    records = []
    with _HISTORY_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                records.append(RunRecord(**{
                    k: v for k, v in d.items()
                    if k in RunRecord.__dataclass_fields__
                }))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Skipping malformed history line: %s", e)
    return records


def get_previous_puzzle_hashes() -> set[str]:
    """Get all puzzle set hashes from history to detect repetition."""
    records = load_history()
    return {r.puzzle_set_hash for r in records}


def get_previous_puzzle_ids() -> set[str]:
    """Get all individual puzzle IDs from previous runs.

    Reads from the detailed run JSON files (not just history.jsonl).
    """
    ids: set[str] = set()
    if not _RUNS_DIR.exists():
        return ids
    for json_file in _RUNS_DIR.glob("*.json"):
        if json_file.name == "history.jsonl":
            continue
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            for result in data.get("results", []):
                pid = result.get("puzzle_id", "")
                if pid:
                    ids.add(pid)
        except (json.JSONDecodeError, OSError):
            continue
    return ids


def print_history_table(records: list[RunRecord] | None = None) -> None:
    """Print a formatted history table to stdout."""
    if records is None:
        records = load_history()
    if not records:
        print("No run history found.")
        return

    print("\n" + "=" * 100)
    print("RUN HISTORY")
    print("=" * 100)
    header = (
        f"{'Run ID':<20} {'Prompt':>8} {'N':>4} {'Weighted':>8} "
        f"{'Pass%':>6} {'Think':>7} {'Out':>5} {'Time':>6} {'Change Summary'}"
    )
    print(header)
    print("-" * 100)

    for r in records:
        print(
            f"{r.run_id:<20} {r.prompt_version:>8} {r.n_puzzles:>4} "
            f"{r.weighted_avg:>8.3f} {r.pass_rate:>5.1f}% "
            f"{r.avg_think_tokens:>7.0f} {r.avg_content_tokens:>5.0f} "
            f"{r.total_elapsed_s:>5.0f}s {r.change_summary[:40]}"
        )

    # Show dimension trend for last 3 runs
    if len(records) >= 2:
        print("\n--- DIMENSION TREND (last 3 runs) ---")
        recent = records[-3:]
        dims = sorted(recent[0].dimension_avgs.keys())
        header = f"{'Dimension':<25}" + "".join(f"{r.prompt_version:>10}" for r in recent)
        print(header)
        for dim in dims:
            vals = "".join(f"{r.dimension_avgs.get(dim, 0):>10.3f}" for r in recent)
            # Arrow showing direction
            if len(recent) >= 2:
                prev = recent[-2].dimension_avgs.get(dim, 0)
                curr = recent[-1].dimension_avgs.get(dim, 0)
                arrow = " ^" if curr > prev + 0.01 else (" v" if curr < prev - 0.01 else " =")
            else:
                arrow = ""
            print(f"{dim:<25}{vals}{arrow}")


def generate_run_id() -> str:
    """Generate a timestamp-based run ID."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
