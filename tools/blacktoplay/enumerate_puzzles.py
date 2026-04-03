"""Enumerate all BTP puzzles by type and verify counts.

Parses TODO/btp-list-response.json and breaks down puzzles by:
- type (0=classic, 1=AI, 2=endgame)
- category (A-O)
- rating distribution

Usage: python -m tools.blacktoplay.enumerate_puzzles
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

LOCAL_LIST = Path("TODO/btp-list-response.json")

TYPE_NAMES = {"0": "Classic", "1": "AI", "2": "Endgame"}

CATEGORY_NAMES = {
    "A": "attachments",
    "B": "basics",
    "C": "capturing",
    "D": "endgame",
    "E": "eyes",
    "F": "ko",
    "G": "placements",
    "H": "reductions",
    "I": "sacrifice",
    "J": "seki",
    "K": "semeai",
    "L": "shape",
    "M": "shortage",
    "N": "tactics",
    "O": "vital-point",
}

# BTP rating -> rank conversion: rank = 21 - round(rating / 100)
RANK_LABELS = {
    21: "21k (rating 0)",
    20: "20k (rating ~100)",
    19: "19k (rating ~200)",
    18: "18k (rating ~300)",
    17: "17k (rating ~400)",
    16: "16k (rating ~500)",
    15: "15k (rating ~600)",
    14: "14k (rating ~700)",
    13: "13k (rating ~800)",
    12: "12k (rating ~900)",
    11: "11k (rating ~1000)",
    10: "10k (rating ~1100)",
    9: "9k (rating ~1200)",
    8: "8k (rating ~1300)",
    7: "7k (rating ~1400)",
    6: "6k (rating ~1500)",
    5: "5k (rating ~1600)",
    4: "4k (rating ~1700)",
    3: "3k (rating ~1800)",
    2: "2k (rating ~1900)",
    1: "1k (rating ~2000)",
    0: "1d+ (rating ~2100+)",
}


def rating_to_rank(rating: int | str) -> int:
    """Convert BTP rating to rank number (21k=21, 1k=1, 1d+=0)."""
    rank = 21 - round(int(rating) / 100)
    return max(0, rank)


def load_puzzles() -> list[dict]:
    """Load puzzle list from local JSON cache."""
    with open(LOCAL_LIST, encoding="utf-8-sig") as f:
        data = json.load(f)
    return data["list"]


def enumerate_by_type(puzzles: list[dict]) -> dict[int, list[dict]]:
    """Group puzzles by type."""
    by_type: dict[int, list[dict]] = defaultdict(list)
    for p in puzzles:
        by_type[p["type"]].append(p)
    return dict(by_type)


def print_type_summary(by_type: dict[int, list[dict]]) -> None:
    """Print summary table by type."""
    print("=" * 60)
    print("PUZZLE COUNT BY TYPE")
    print("=" * 60)
    total = 0
    for t in sorted(by_type.keys()):
        name = TYPE_NAMES.get(t, f"Unknown({t})")
        count = len(by_type[t])
        total += count
        print(f"  Type {t} ({name:>8s}): {count:>5d}")
    print(f"  {'TOTAL':>20s}: {total:>5d}")
    print()


def print_category_breakdown(puzzles: list[dict], type_name: str) -> None:
    """Print category distribution for a set of puzzles."""
    cat_counter: Counter[str] = Counter()
    no_cat_count = 0
    for p in puzzles:
        cats = p.get("categories", "")
        if not cats:
            no_cat_count += 1
        else:
            for c in cats:
                cat_counter[c] += 1

    print(f"  Categories ({type_name}):")
    for cat in sorted(cat_counter.keys()):
        name = CATEGORY_NAMES.get(cat, f"unknown-{cat}")
        print(f"    {cat} ({name:>12s}): {cat_counter[cat]:>5d}")
    if no_cat_count:
        print(f"    {'(no category)':>16s}: {no_cat_count:>5d}")
    print()


def print_rating_distribution(puzzles: list[dict], type_name: str) -> None:
    """Print rating distribution for a set of puzzles."""
    rank_counter: Counter[int] = Counter()
    for p in puzzles:
        rating = p.get("rating", 0)
        rank = rating_to_rank(rating)
        rank_counter[rank] += 1

    print(f"  Rating distribution ({type_name}):")
    for rank in sorted(rank_counter.keys(), reverse=True):
        label = RANK_LABELS.get(rank, f"rank-{rank}")
        bar = "#" * (rank_counter[rank] // 10)
        print(f"    {label:>22s}: {rank_counter[rank]:>5d}  {bar}")
    print()


def print_id_samples(puzzles: list[dict], type_name: str, n: int = 5) -> None:
    """Print first and last N puzzle IDs for a type."""
    ids = [p["id"] for p in puzzles]
    print(f"  Sample IDs ({type_name}): first {n}: {ids[:n]}")
    print(f"  {'':>22s}  last {n}: {ids[-n:]}")
    print()


def check_id_uniqueness(puzzles: list[dict]) -> None:
    """Verify all puzzle IDs are unique."""
    ids = [p["id"] for p in puzzles]
    unique = set(ids)
    if len(ids) == len(unique):
        print(f"ID uniqueness: OK (all {len(ids)} IDs are unique)")
    else:
        dupes = [pid for pid, count in Counter(ids).items() if count > 1]
        print(f"ID uniqueness: FAIL ({len(ids) - len(unique)} duplicates)")
        print(f"  Duplicated IDs: {dupes[:20]}")
    print()


def check_id_patterns(by_type: dict[int, list[dict]]) -> None:
    """Analyze ID patterns by type."""
    print("ID PATTERN ANALYSIS")
    print("-" * 60)
    for t in sorted(by_type.keys()):
        name = TYPE_NAMES.get(t, f"Unknown({t})")
        ids = [p["id"] for p in by_type[t]]
        numeric = [pid for pid in ids if pid.isdigit()]
        alpha = [pid for pid in ids if not pid.isdigit()]
        print(f"  Type {t} ({name}):")
        print(f"    Numeric IDs: {len(numeric)}")
        print(f"    Alphanumeric IDs: {len(alpha)}")
        if numeric:
            nums = sorted(int(x) for x in numeric)
            print(f"    Numeric range: {nums[0]} - {nums[-1]}")
        if alpha:
            print(f"    Alpha sample: {alpha[:5]}")
        print()


def write_full_listing(by_type: dict[int, list[dict]]) -> None:
    """Write full puzzle listing to JSON."""
    output_dir = Path("tools/blacktoplay/verification_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    listing = {}
    for t in sorted(by_type.keys()):
        name = TYPE_NAMES.get(t, f"Unknown({t})").lower()
        entries = []
        for p in by_type[t]:
            entries.append({
                "id": p["id"],
                "rating": p.get("rating", 0),
                "categories": p.get("categories", ""),
                "tags": p.get("tags", ""),
            })
        listing[name] = {
            "count": len(entries),
            "puzzles": entries,
        }
    listing["total"] = sum(len(by_type[t]) for t in by_type)

    out_path = output_dir / "puzzle_enumeration.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(listing, f, indent=2)
    print(f"Full listing written to {out_path}")


def main() -> int:
    print(f"Loading puzzle list from: {LOCAL_LIST}")
    puzzles = load_puzzles()
    print(f"Loaded {len(puzzles)} puzzles\n")

    by_type = enumerate_by_type(puzzles)

    print_type_summary(by_type)
    check_id_uniqueness(puzzles)
    check_id_patterns(by_type)

    for t in sorted(by_type.keys()):
        name = TYPE_NAMES.get(t, f"Unknown({t})")
        print(f"\n{'=' * 60}")
        print(f"TYPE {t}: {name} ({len(by_type[t])} puzzles)")
        print(f"{'=' * 60}")
        print_category_breakdown(by_type[t], name)
        print_rating_distribution(by_type[t], name)
        print_id_samples(by_type[t], name)

    write_full_listing(by_type)
    return 0


if __name__ == "__main__":
    sys.exit(main())
