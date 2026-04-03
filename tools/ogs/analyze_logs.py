#!/usr/bin/env python3
"""
Analyze OGS download logs.

Usage:
    python -m tools.ogs.analyze_logs
    python -m tools.ogs.analyze_logs --failures
    python -m tools.ogs.analyze_logs --summary
    python -m tools.ogs.analyze_logs --event-type puzzle_save
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


def print_summary(events: list[dict]) -> None:
    """Print summary statistics."""
    print("\n" + "="*60)
    print("OGS DOWNLOAD LOG SUMMARY")
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

    # Calculate success rate
    total_processed = len(saves) + len(skips) + len(errors)
    if total_processed > 0:
        success_rate = (len(saves) / total_processed) * 100
        print(f"  Success Rate: {success_rate:.1f}%")

    # Page stats
    page_starts = filter_by_event_type(events, "page_start")
    print(f"\nPages processed: {len(page_starts)}")

    # Checkpoint stats
    checkpoint_saves = filter_by_event_type(events, "checkpoint_save")
    print(f"Checkpoints saved: {len(checkpoint_saves)}")

    # API stats
    rate_limits = filter_by_event_type(events, "api_rate_limit")
    print(f"\nRate limit delays: {len(rate_limits)}")

    # Skip reasons
    if skips:
        skip_reasons = Counter(e.get("data", {}).get("reason", "unknown") for e in skips)
        print("\nSkip reasons:")
        for reason, count in skip_reasons.most_common():
            print(f"  {reason}: {count}")

    # Batch distribution
    batch_counts = Counter(e.get("data", {}).get("batch_num") for e in saves)
    if batch_counts:
        print("\nSaved by batch:")
        for batch_num in sorted(batch_counts.keys(), key=lambda x: x or 0):
            print(f"  batch-{batch_num:03d}: {batch_counts[batch_num]}")

    # Last run summary
    if run_ends:
        last_run = run_ends[-1]
        data = last_run.get("data", {})
        print("\nLast run:")
        print(f"  Downloaded: {data.get('downloaded', 'N/A')}")
        print(f"  Skipped: {data.get('skipped', 'N/A')}")
        print(f"  Errors: {data.get('errors', 'N/A')}")
        print(f"  Duration: {data.get('duration_sec', 'N/A'):.1f}s")


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
            puzzle_id = data.get("puzzle_id", "?")
            error = data.get("error", e.get("message", "?"))
            print(f"[{ts}] {et}: puzzle {puzzle_id}")
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
                print(f"  - puzzle {puzzle_id}")
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
        data = e.get("data", {})
        puzzle_id = data.get("puzzle_id", "")
        print(f"[{ts}] {et:20} {str(puzzle_id):8} {msg[:50]}")


def main():
    parser = argparse.ArgumentParser(description="Analyze OGS download logs")
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("external-sources/ogs/logs"),
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
