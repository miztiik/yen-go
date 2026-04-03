#!/usr/bin/env python3
"""
Analyze TsumegoDragon download logs.

Usage:
    python scripts/tsumegodragon/analyze_logs.py
    python scripts/tsumegodragon/analyze_logs.py --failures
    python scripts/tsumegodragon/analyze_logs.py --summary
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_logs(logs_dir: Path) -> list[dict[str, Any]]:
    """Load all JSONL log files from directory."""
    events = []
    for log_file in sorted(logs_dir.glob("*.jsonl")):
        with log_file.open(encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def filter_by_event_type(events: list[dict], *event_types: str) -> list[dict]:
    """Filter events by type."""
    return [e for e in events if e.get("event_type") in event_types]


def filter_by_status(events: list[dict], status: str) -> list[dict]:
    """Filter events by status in data."""
    return [e for e in events if e.get("data", {}).get("status") == status]


def print_summary(events: list[dict]) -> None:
    """Print summary statistics."""
    # Count event types
    Counter(e.get("event_type") for e in events if e.get("event_type"))

    print("\n" + "="*60)
    print("LOG SUMMARY")
    print("="*60)

    # Run stats
    run_starts = filter_by_event_type(events, "run_start")
    run_ends = filter_by_event_type(events, "run_end")

    print(f"\nRuns: {len(run_starts)} started, {len(run_ends)} completed")

    # Puzzle stats
    saves = filter_by_event_type(events, "puzzle_save")
    skips = filter_by_event_type(events, "puzzle_skip")
    errors = filter_by_event_type(events, "puzzle_error")

    print("\nPuzzles:")
    print(f"  Saved:   {len(saves)}")
    print(f"  Skipped: {len(skips)}")
    print(f"  Errors:  {len(errors)}")

    # Batch stats
    batch_starts = filter_by_event_type(events, "batch_start")
    batch_ends = filter_by_event_type(events, "batch_end")

    print(f"\nBatches: {len(batch_starts)} started, {len(batch_ends)} completed")

    # API stats
    api_requests = filter_by_event_type(events, "api_request")
    api_errors = filter_by_event_type(events, "api_error")

    print(f"\nAPI: {len(api_requests)} requests, {len(api_errors)} errors")

    # Skip reasons
    if skips:
        skip_reasons = Counter(e.get("data", {}).get("reason", "unknown") for e in skips)
        print("\nSkip reasons:")
        for reason, count in skip_reasons.most_common():
            print(f"  {reason}: {count}")

    # Level distribution
    level_counts = Counter()
    for e in saves:
        level = e.get("data", {}).get("td_level")
        level_counts[level] = level_counts.get(level, 0) + 1

    if level_counts:
        print("\nSaved by level:")
        for level in sorted(level_counts.keys(), key=lambda x: (x is None, x)):
            print(f"  Level {level}: {level_counts[level]}")

    # Category distribution
    cat_counts = Counter(e.get("data", {}).get("category", "unknown") for e in saves)
    if cat_counts:
        print("\nSaved by category (top 10):")
        for cat, count in cat_counts.most_common(10):
            print(f"  {cat}: {count}")


def print_failures(events: list[dict]) -> None:
    """Print all failure events."""
    errors = filter_by_event_type(events, "puzzle_error", "api_error")
    skips = filter_by_event_type(events, "puzzle_skip")

    print("\n" + "="*60)
    print("FAILURES AND SKIPS")
    print("="*60)

    if errors:
        print(f"\n### ERRORS ({len(errors)}) ###\n")
        for e in errors:
            ts = e.get("timestamp", "?")[:19]
            et = e.get("event_type", "?")
            data = e.get("data", {})
            puzzle_id = data.get("puzzle_id", data.get("url", "?"))
            error = data.get("error", e.get("message", "?"))
            print(f"[{ts}] {et}: {puzzle_id}")
            print(f"  Error: {error}")
            print()
    else:
        print("\nNo errors found.")

    if skips:
        print(f"\n### SKIPPED ({len(skips)}) ###\n")
        # Group by reason
        by_reason: dict[str, list] = {}
        for e in skips:
            reason = e.get("data", {}).get("reason", "unknown")
            by_reason.setdefault(reason, []).append(e)

        for reason, items in sorted(by_reason.items(), key=lambda x: -len(x[1])):
            print(f"{reason}: {len(items)}")
            for e in items[:5]:  # Show first 5
                puzzle_id = e.get("data", {}).get("puzzle_id", "?")
                print(f"  - {puzzle_id}")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
            print()


def print_events(events: list[dict], event_type: str = None) -> None:
    """Print events in readable format."""
    if event_type:
        events = filter_by_event_type(events, event_type)

    for e in events:
        if not e.get("event_type"):
            continue
        ts = e.get("timestamp", "?")[:19]
        et = e.get("event_type", "?")
        msg = e.get("message", "")
        status = e.get("data", {}).get("status", "")
        print(f"[{ts}] {et:20} {status:8} {msg[:50]}")


def main():
    parser = argparse.ArgumentParser(description="Analyze TsumegoDragon download logs")
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("external-sources/tsumegodragon/logs"),
        help="Directory containing log files",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary statistics",
    )
    parser.add_argument(
        "--failures",
        action="store_true",
        help="Show failures and skips only",
    )
    parser.add_argument(
        "--event-type",
        type=str,
        help="Filter by event type (e.g., puzzle_save, puzzle_error)",
    )

    args = parser.parse_args()

    if not args.logs_dir.exists():
        print(f"Logs directory not found: {args.logs_dir}")
        return 1

    events = load_logs(args.logs_dir)
    print(f"Loaded {len(events)} log entries from {args.logs_dir}")

    if args.failures:
        print_failures(events)
    elif args.summary or not args.event_type:
        print_summary(events)

    if args.event_type:
        print(f"\n### Events: {args.event_type} ###\n")
        print_events(events, args.event_type)

    return 0


if __name__ == "__main__":
    exit(main())
