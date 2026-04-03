#!/usr/bin/env python3
"""
Investigate missing puzzle IDs in BTP downloads.

This utility:
1. Scans actual downloaded SGF files on disk
2. Parses the JSONL log to extract downloaded puzzle IDs
3. Loads the cached puzzle list to see what SHOULD exist
4. Compares all three sources and finds discrepancies
5. Samples random missing IDs and probes the API

Usage:
    python -m tools.blacktoplay.temp.investigate_missing

Output goes to tools/blacktoplay/temp/ - does NOT touch external-sources.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

# Path configuration
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # tools/blacktoplay/temp -> yen-go
LOG_DIR = PROJECT_ROOT / "external-sources/blacktoplay/logs/logs"
SGF_DIR = PROJECT_ROOT / "external-sources/blacktoplay/sgf"
CACHED_LIST = PROJECT_ROOT / "tools/blacktoplay/research/btp-list-response.json"
OUTPUT_DIR = Path(__file__).parent


def find_latest_log() -> Path | None:
    """Find the most recent JSONL log file."""
    if not LOG_DIR.exists():
        return None
    logs = sorted(LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def extract_puzzle_ids_from_disk(sgf_dir: Path) -> set[str]:
    """Scan actual SGF files and extract puzzle IDs."""
    puzzle_ids: set[str] = set()

    # Pattern to match btp-XXXXXX.sgf (numeric or alphanumeric)
    pattern = re.compile(r"btp-([A-Za-z0-9]+)\.sgf")

    for batch_dir in sgf_dir.iterdir():
        if not batch_dir.is_dir():
            continue
        for sgf_file in batch_dir.glob("btp-*.sgf"):
            match = pattern.match(sgf_file.name)
            if match:
                puzzle_ids.add(match.group(1))

    return puzzle_ids


def extract_puzzle_ids_from_log(log_path: Path) -> set[str]:
    """Extract puzzle IDs from JSONL log."""
    puzzle_ids: set[str] = set()

    # Pattern to match btp-XXXXXX.sgf
    pattern = re.compile(r"btp-([A-Za-z0-9]+)\.sgf")

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                msg = entry.get("message", "")
                match = pattern.search(msg)
                if match:
                    puzzle_ids.add(match.group(1))
            except json.JSONDecodeError:
                continue

    return puzzle_ids


def load_cached_puzzle_list(cache_path: Path) -> dict[str, list[dict]]:
    """Load cached puzzle list, grouped by type."""
    if not cache_path.exists():
        return {}

    with open(cache_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    # Group by type
    by_type: dict[str, list[dict]] = {"0": [], "1": [], "2": []}
    for entry in data.get("list", []):
        t = entry.get("type", "0")
        if t in by_type:
            by_type[t].append(entry)

    return by_type


def get_expected_ids(cached_list: dict[str, list[dict]], puzzle_types: list[str] | None = None) -> set[str]:
    """Get all expected puzzle IDs from cached list."""
    if puzzle_types is None:
        puzzle_types = ["0", "1", "2"]

    ids: set[str] = set()
    for t in puzzle_types:
        for entry in cached_list.get(t, []):
            ids.add(entry["id"])
    return ids


def probe_puzzle(puzzle_id: str) -> dict:
    """Probe BTP API for a specific puzzle ID.

    Returns dict with status and details.
    """
    url = "https://blacktoplay.com/php/public/load_data.php"

    try:
        response = httpx.post(
            url,
            data={"id": puzzle_id, "db": "0", "vid": "yengo", "rating": "1500"},
            headers={
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://blacktoplay.com",
                "Referer": "https://blacktoplay.com/",
            },
            timeout=10.0,
        )

        if response.status_code != 200:
            return {
                "id": puzzle_id,
                "status": "http_error",
                "code": response.status_code,
            }

        # Check for empty response
        if not response.text.strip():
            return {
                "id": puzzle_id,
                "status": "empty_response",
            }

        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "id": puzzle_id,
                "status": "invalid_json",
                "raw": response.text[:100],
            }

        # Check if puzzle exists
        if not data:
            return {
                "id": puzzle_id,
                "status": "empty_json",
            }

        # Check for error in response
        if "error" in data or data.get("status") == "error":
            return {
                "id": puzzle_id,
                "status": "api_error",
                "message": data.get("message", data.get("error", "unknown")),
            }

        # Puzzle exists
        return {
            "id": puzzle_id,
            "status": "exists",
            "board_size": data.get("board_size"),
            "viewport_size": data.get("viewport_size"),
            "rating": data.get("rating"),
            "nodes_count": len(data.get("nodes", [])),
            "type": data.get("type"),
        }

    except httpx.TimeoutException:
        return {
            "id": puzzle_id,
            "status": "timeout",
        }
    except Exception as e:
        return {
            "id": puzzle_id,
            "status": "error",
            "message": str(e),
        }


def main():
    """Compare disk files, log entries, and cached puzzle list."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("BTP DOWNLOAD COMPARISON: Disk vs Log vs Cache")
    print("=" * 70)

    # Step 1: Scan SGF files on disk
    print("\n[1] Scanning SGF files on disk...")
    disk_ids = extract_puzzle_ids_from_disk(SGF_DIR)
    print(f"    Found {len(disk_ids)} SGF files")

    # Step 2: Parse latest log
    print("\n[2] Finding and parsing latest log...")
    log_file = find_latest_log()
    if log_file:
        print(f"    Log: {log_file.name}")
        log_ids = extract_puzzle_ids_from_log(log_file)
        print(f"    Found {len(log_ids)} logged puzzle entries")
    else:
        print("    WARNING: No log files found")
        log_ids = set()

    # Step 3: Load cached puzzle list
    print("\n[3] Loading cached puzzle list...")
    cached_list = load_cached_puzzle_list(CACHED_LIST)
    if cached_list:
        cache_ids = get_expected_ids(cached_list)
        print(f"    Found {len(cache_ids)} puzzles in cache")
        print(f"    By type: classic={len(cached_list.get('0', []))}, "
              f"AI={len(cached_list.get('1', []))}, "
              f"endgame={len(cached_list.get('2', []))}")
    else:
        print("    WARNING: Cache file not found")
        cache_ids = set()

    # Step 4: Compare sets
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    # Key comparisons
    in_cache_not_on_disk = cache_ids - disk_ids
    on_disk_not_in_cache = disk_ids - cache_ids
    in_log_not_on_disk = log_ids - disk_ids
    on_disk_not_in_log = disk_ids - log_ids if log_ids else set()

    print(f"\n  Total in cache:                {len(cache_ids):>5}")
    print(f"  Total on disk:                 {len(disk_ids):>5}")
    print(f"  Total in log:                  {len(log_ids):>5}")

    print(f"\n  In cache but NOT on disk:      {len(in_cache_not_on_disk):>5}  <- MISSING (need download)")
    print(f"  On disk but NOT in cache:      {len(on_disk_not_in_cache):>5}  <- EXTRA (orphaned files)")
    print(f"  In log but NOT on disk:        {len(in_log_not_on_disk):>5}  <- FAILED (download issues)")
    print(f"  On disk but NOT in log:        {len(on_disk_not_in_log):>5}  <- UNLOGGED (manual imports?)")

    # Coverage
    if cache_ids:
        coverage = len(disk_ids & cache_ids) / len(cache_ids) * 100
        print(f"\n  Download coverage:             {coverage:.1f}%")

    # Save detailed reports
    def save_id_list(filename: str, ids: set[str], header: str) -> None:
        filepath = OUTPUT_DIR / filename
        sorted_ids = sorted(ids)
        with open(filepath, "w") as f:
            f.write(f"# {header}\n")
            f.write(f"# Generated: {json.dumps(str(Path(__file__).name))}\n")
            f.write(f"# Count: {len(ids)}\n\n")
            for pid in sorted_ids:
                f.write(f"{pid}\n")
        print(f"    Saved: {filename} ({len(ids)} entries)")

    print(f"\n[4] Saving reports to {OUTPUT_DIR.name}/...")
    save_id_list("missing_from_disk.txt", in_cache_not_on_disk, "Puzzles in cache but not downloaded")
    save_id_list("orphaned_on_disk.txt", on_disk_not_in_cache, "Puzzles on disk but not in cache")
    save_id_list("failed_downloads.txt", in_log_not_on_disk, "Puzzles in log but not on disk")

    # Save combined summary as JSON
    summary = {
        "disk_count": len(disk_ids),
        "log_count": len(log_ids),
        "cache_count": len(cache_ids),
        "missing_from_disk": len(in_cache_not_on_disk),
        "orphaned_on_disk": len(on_disk_not_in_cache),
        "failed_downloads": len(in_log_not_on_disk),
        "unlogged": len(on_disk_not_in_log),
        "coverage_pct": round(len(disk_ids & cache_ids) / len(cache_ids) * 100, 2) if cache_ids else 0,
    }
    summary_file = OUTPUT_DIR / "comparison_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print("    Saved: comparison_summary.json")

    # Step 5: Optional - probe a sample of missing IDs
    if in_cache_not_on_disk:
        print(f"\n[5] Probing sample of {min(5, len(in_cache_not_on_disk))} missing puzzles...")
        sample = list(in_cache_not_on_disk)[:5]

        probe_results = []
        for puzzle_id in sample:
            print(f"    Probing {puzzle_id}...", end=" ", flush=True)
            result = probe_puzzle(puzzle_id)
            probe_results.append(result)

            if result["status"] == "exists":
                print(f"EXISTS (board={result.get('board_size')}, nodes={result.get('nodes_count')})")
            else:
                print(f"{result['status'].upper()}")

        probe_file = OUTPUT_DIR / "probe_results.json"
        with open(probe_file, "w") as f:
            json.dump(probe_results, f, indent=2)
        print("    Saved: probe_results.json")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
