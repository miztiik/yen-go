#!/usr/bin/env python3
"""
Analyze puzzle duplication across OGS collections.

Reads the collections-sorted.jsonl file and produces a markdown report
showing overlap statistics and storage strategy recommendations.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_collections(jsonl_path: Path) -> tuple[dict, list[dict]]:
    """Load metadata and collections from JSONL file."""
    metadata = None
    collections = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("type") == "metadata":
                metadata = obj
            elif obj.get("type") == "collection":
                collections.append(obj)
    return metadata, collections


def analyze(collections: list[dict]) -> dict:
    """Compute duplication and distribution statistics."""
    # puzzle_id -> list of collection IDs it appears in
    puzzle_to_collections: dict[int, list[int]] = defaultdict(list)
    # collection stats
    collection_stats = []

    for coll in collections:
        cid = coll["id"]
        puzzles = coll.get("puzzles", [])
        for pid in puzzles:
            puzzle_to_collections[pid].append(cid)
        collection_stats.append({
            "id": cid,
            "name": coll["name"],
            "puzzle_count": len(puzzles),
            "sort_rank": coll.get("sort_rank", 0),
            "priority_score": coll.get("priority_score", 0),
            "quality_tier": coll.get("quality_tier", "unknown"),
            "rating": coll.get("bayesian_rating", 0),
            "solve_rate": coll.get("solve_rate", 0),
        })

    # How many collections each puzzle appears in
    membership_counts = Counter(len(colls) for colls in puzzle_to_collections.values())

    # Which puzzles are duplicated (in >1 collection)
    duplicated = {pid: colls for pid, colls in puzzle_to_collections.items() if len(colls) > 1}

    # Total slots = sum of all collection sizes (with duplication)
    total_slots = sum(len(coll.get("puzzles", [])) for coll in collections)
    unique_puzzles = len(puzzle_to_collections)

    # Per-tier breakdown
    tier_stats = defaultdict(lambda: {"count": 0, "puzzles": 0, "unique": set()})
    for coll in collections:
        tier = coll.get("quality_tier", "unknown")
        tier_stats[tier]["count"] += 1
        tier_stats[tier]["puzzles"] += len(coll.get("puzzles", []))
        for pid in coll.get("puzzles", []):
            tier_stats[tier]["unique"].add(pid)

    # Size distribution of collections
    sizes = [len(coll.get("puzzles", [])) for coll in collections]
    size_buckets = Counter()
    for s in sizes:
        if s <= 10:
            size_buckets["1-10"] += 1
        elif s <= 50:
            size_buckets["11-50"] += 1
        elif s <= 100:
            size_buckets["51-100"] += 1
        elif s <= 200:
            size_buckets["101-200"] += 1
        elif s <= 500:
            size_buckets["201-500"] += 1
        elif s <= 1000:
            size_buckets["501-1000"] += 1
        else:
            size_buckets["1000+"] += 1

    # Cross-collection overlap pairs (which pairs of collections share the most puzzles)
    # Only compute for collections with overlapping puzzles
    collection_overlap_pairs = defaultdict(int)
    for pid, colls in puzzle_to_collections.items():
        if len(colls) > 1:
            colls_sorted = sorted(colls)
            for i in range(len(colls_sorted)):
                for j in range(i + 1, len(colls_sorted)):
                    collection_overlap_pairs[(colls_sorted[i], colls_sorted[j])] += 1

    # Top overlapping pairs
    top_overlaps = sorted(collection_overlap_pairs.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "total_collections": len(collections),
        "total_slots": total_slots,
        "unique_puzzles": unique_puzzles,
        "duplication_ratio": total_slots / unique_puzzles if unique_puzzles else 0,
        "membership_counts": dict(sorted(membership_counts.items())),
        "duplicated_count": len(duplicated),
        "duplicated_pct": len(duplicated) / unique_puzzles * 100 if unique_puzzles else 0,
        "tier_stats": {
            k: {"count": v["count"], "puzzles": v["puzzles"], "unique": len(v["unique"])}
            for k, v in tier_stats.items()
        },
        "size_buckets": size_buckets,
        "collection_stats": collection_stats,
        "top_overlaps": top_overlaps,
        "puzzle_to_collections": puzzle_to_collections,
    }


def compute_storage_scenarios(stats: dict, collections: list[dict]) -> list[dict]:
    """Compute storage requirements for different strategies."""
    coll_by_id = {c["id"]: c for c in collections}
    puzzle_to_colls = stats["puzzle_to_collections"]

    # --- Scenario A: Flat (current) - store each unique file once in batches ---
    unique = stats["unique_puzzles"]

    # --- Scenario B: Collection-based with full duplication ---
    total_slots = stats["total_slots"]

    # --- Scenario C: Collection-based with symlinks/references ---
    # Each puzzle stored once physically, additional appearances are references
    # Calculate: how many physical + how many references
    physical = unique
    references = total_slots - unique

    # --- Scenario D: Primary collection assignment (no duplication) ---
    # Assign each puzzle to its highest-priority collection only
    primary_assignment = {}
    for pid, colls in puzzle_to_colls.items():
        # Sort by priority (lower sort_rank = higher priority)
        best_coll = min(colls, key=lambda cid: coll_by_id.get(cid, {}).get("sort_rank", 9999))
        primary_assignment[pid] = best_coll

    # Count how many puzzles each collection would have under primary assignment
    primary_counts = Counter(primary_assignment.values())

    # Collections that would be empty or very small under primary assignment
    empty_or_small = []
    for coll in collections:
        cid = coll["id"]
        original = len(coll.get("puzzles", []))
        assigned = primary_counts.get(cid, 0)
        if assigned < original * 0.5:  # lost more than half
            empty_or_small.append({
                "id": cid,
                "name": coll["name"],
                "original": original,
                "assigned": assigned,
                "lost_pct": (1 - assigned / original) * 100 if original else 0,
            })

    # --- Scenario E: Tier-based filtering + primary assignment ---
    # Only keep premier + curated collections, then do primary assignment
    kept_tiers = {"premier", "curated"}
    kept_colls = [c for c in collections if c.get("quality_tier") in kept_tiers]
    kept_ids = {c["id"] for c in kept_colls}
    tier_puzzle_to_colls = defaultdict(list)
    for pid, colls in puzzle_to_colls.items():
        filtered = [c for c in colls if c in kept_ids]
        if filtered:
            tier_puzzle_to_colls[pid] = filtered

    tier_unique = len(tier_puzzle_to_colls)
    tier_total = sum(len(c.get("puzzles", [])) for c in kept_colls)

    tier_primary = {}
    for pid, colls in tier_puzzle_to_colls.items():
        best = min(colls, key=lambda cid: coll_by_id.get(cid, {}).get("sort_rank", 9999))
        tier_primary[pid] = best

    return [
        {
            "name": "A: Flat batches (current)",
            "description": "All unique puzzles in batch-NNN/ directories, no collection structure",
            "files": unique,
            "duplication": 0,
            "preserves_collections": False,
        },
        {
            "name": "B: Full collection duplication",
            "description": "Copy each puzzle into every collection it belongs to",
            "files": total_slots,
            "duplication": total_slots - unique,
            "preserves_collections": True,
        },
        {
            "name": "C: Collection dirs + shared pool",
            "description": "Physical files in shared pool, collection manifests reference them",
            "files": unique,
            "duplication": 0,
            "preserves_collections": True,
            "extra": f"{references} references in manifests",
        },
        {
            "name": "D: Primary collection assignment",
            "description": "Each puzzle belongs to its highest-priority collection only",
            "files": unique,
            "duplication": 0,
            "preserves_collections": True,
            "extra": f"{len(empty_or_small)} collections lose >50% of puzzles",
        },
        {
            "name": "E: Tier filter (premier+curated) + primary",
            "description": "Keep only premier+curated tiers, then assign each to best collection",
            "files": tier_unique,
            "duplication": 0,
            "preserves_collections": True,
            "extra": f"Drops {unique - tier_unique} puzzles from lower tiers",
        },
    ], empty_or_small


def generate_report(
    metadata: dict,
    collections: list[dict],
    stats: dict,
    scenarios: list[dict],
    losers: list[dict],
) -> str:
    """Generate the markdown report."""
    lines = []
    a = lines.append

    a("# OGS Collection Overlap & Storage Analysis")
    a("")
    a(f"**Generated from**: `{Path(metadata.get('source', 'unknown')).name if metadata else 'unknown'}`")
    a(f"**Total collections**: {stats['total_collections']}")
    a(f"**Total puzzle slots** (sum of all collection sizes): {stats['total_slots']:,}")
    a(f"**Unique puzzles**: {stats['unique_puzzles']:,}")
    a(f"**Duplication ratio**: {stats['duplication_ratio']:.3f}x")
    a(f"**SGF index**: ~51,996 files across 52 batches")
    a("")

    # --- Section 1: Duplication Summary ---
    a("## 1. Duplication Summary")
    a("")
    a("How many collections does each puzzle appear in?")
    a("")
    a("| Appearances | Puzzle Count | % of Total |")
    a("|:-----------:|:------------:|:----------:|")
    for n_colls, count in sorted(stats["membership_counts"].items()):
        pct = count / stats["unique_puzzles"] * 100
        a(f"| {n_colls} | {count:,} | {pct:.1f}% |")
    a("")
    a(f"**Duplicated puzzles** (in ≥2 collections): **{stats['duplicated_count']:,}** ({stats['duplicated_pct']:.1f}% of unique)")
    a(f"**Extra file copies needed** if storing per-collection: **{stats['total_slots'] - stats['unique_puzzles']:,}**")
    a("")

    # --- Section 2: Tier Breakdown ---
    a("## 2. Quality Tier Breakdown")
    a("")
    a("| Tier | Collections | Total Slots | Unique Puzzles | Overlap |")
    a("|------|:-----------:|:-----------:|:--------------:|:-------:|")
    for tier in ["premier", "curated", "community", "unvetted"]:
        ts = stats["tier_stats"].get(tier, {"count": 0, "puzzles": 0, "unique": 0})
        overlap = ts["puzzles"] - ts["unique"]
        a(f"| {tier} | {ts['count']} | {ts['puzzles']:,} | {ts['unique']:,} | {overlap:,} |")
    a("")

    # --- Section 3: Collection Size Distribution ---
    a("## 3. Collection Size Distribution")
    a("")
    a("| Size Range | Count |")
    a("|:----------:|:-----:|")
    for bucket in ["1-10", "11-50", "51-100", "101-200", "201-500", "501-1000", "1000+"]:
        a(f"| {bucket} | {stats['size_buckets'].get(bucket, 0)} |")
    a("")

    # --- Section 4: Top Overlapping Collection Pairs ---
    a("## 4. Top 20 Overlapping Collection Pairs")
    a("")
    a("Collections that share the most puzzles with each other:")
    a("")
    a("| Rank | Collection A | Collection B | Shared Puzzles |")
    a("|:----:|:-------------|:-------------|:--------------:|")
    coll_by_id = {c["id"]: c["name"] for c in collections}
    for i, ((cid_a, cid_b), shared) in enumerate(stats["top_overlaps"], 1):
        name_a = coll_by_id.get(cid_a, str(cid_a))[:50]
        name_b = coll_by_id.get(cid_b, str(cid_b))[:50]
        a(f"| {i} | {name_a} | {name_b} | {shared} |")
    a("")

    # --- Section 5: Small & Low-Priority Collections ---
    a("## 5. Small Collections (≤10 puzzles)")
    a("")
    small = [c for c in stats["collection_stats"] if c["puzzle_count"] <= 10]
    a(f"**{len(small)}** collections have ≤10 puzzles.")
    a("")
    if small:
        a("| Rank | Name | Puzzles | Priority | Tier | Rating |")
        a("|:----:|:-----|:-------:|:--------:|:----:|:------:|")
        for c in small[:30]:
            a(f"| {c['sort_rank']} | {c['name'][:55]} | {c['puzzle_count']} | {c['priority_score']:.3f} | {c['quality_tier']} | {c['rating']:.2f} |")
        if len(small) > 30:
            a(f"| ... | *({len(small) - 30} more)* | | | | |")
    a("")

    # --- Section 6: Storage Strategy Comparison ---
    a("## 6. Storage Strategy Comparison")
    a("")
    a("| Strategy | Files on Disk | Extra Copies | Collection Structure | Notes |")
    a("|:---------|:------------:|:------------:|:--------------------:|:------|")
    for sc in scenarios:
        extra = sc.get("extra", "—")
        coll = "✅" if sc["preserves_collections"] else "❌"
        a(f"| **{sc['name']}** | {sc['files']:,} | {sc['duplication']:,} | {coll} | {extra} |")
    a("")

    # --- Section 7: Recommendations ---
    a("## 7. Recommendations")
    a("")
    a("### Option 1: Collection Manifests + Shared Pool (Recommended)")
    a("")
    a("```")
    a("ogs/")
    a("├── sgf/                          # Shared physical files (no change)")
    a("│   ├── batch-001/")
    a("│   │   ├── 2.sgf")
    a("│   │   └── ...")
    a("│   └── batch-052/")
    a("├── collections/")
    a("│   ├── index.json                # Master collection list")
    a("│   ├── cho-chikun-elementary/")
    a("│   │   └── manifest.json         # {puzzles: [\"batch-001/10600.sgf\", ...]}")
    a("│   ├── frans-library/")
    a("│   │   └── manifest.json")
    a("│   └── ...")
    a("```")
    a("")
    a("**Pros**: Zero duplication, full collection metadata preserved, easy to filter by tier.")
    a("**Cons**: Requires a lookup step to find physical files.")
    a("")
    a("### Option 2: Tier-Gated Primary Assignment")
    a("")
    a("1. **Keep only premier + curated** tiers (the top ~969 collections)")
    a("2. **Assign each puzzle to its highest-priority collection** only")
    a("3. Store files under `collections/{slug}/{puzzle_id}.sgf`")
    a("")
    a("**Pros**: Clean 1:1 mapping, no duplication, drops low-quality content.")
    a("**Cons**: Some collections lose puzzles that were shared; ~{0} puzzles in lower tiers dropped entirely.".format(
        stats["unique_puzzles"] - sum(
            1 for pid, colls in stats["puzzle_to_collections"].items()
            if any(
                c.get("quality_tier") in {"premier", "curated"}
                for c in collections
                if c["id"] in colls
            )
        )
    ))
    a("")
    a("### Option 3: Hybrid — Physical Collection Dirs + Dedup via Content Hash")
    a("")
    a("1. Store files physically under `collections/{slug}/` directories")
    a("2. At publish time, dedup via content hashing (your existing YENGO GN pipeline)")
    a("3. The publish pipeline already handles dedup — so duplication at source is harmless")
    a("")
    a("**Pros**: Simplest mental model, your existing pipeline handles the hard part.")
    a("**Cons**: ~{0:,} extra files on disk (storage cost is minimal for SGF).".format(
        stats["total_slots"] - stats["unique_puzzles"]
    ))
    a("")

    # --- Section 8: Verdict ---
    a("## 8. Verdict & Bottom Line")
    a("")
    a(f"With **{stats['duplication_ratio']:.2f}x** duplication ratio and only "
      f"**{stats['duplicated_pct']:.1f}%** of puzzles appearing in multiple collections, "
      f"the overlap is **moderate**.")
    a("")
    a("The extra copies would be ~{0:,} files — each SGF is ~1-5KB, so that's ~{1:.0f} MB max. "
      "**Storage is not the concern; organizational clarity is.**".format(
        stats["total_slots"] - stats["unique_puzzles"],
        (stats["total_slots"] - stats["unique_puzzles"]) * 5 / 1024,
    ))
    a("")
    a("**Recommended approach**: **Option 1 (Manifests)** for the source repository, "
      "because your publish pipeline already deduplicates via content hash. "
      "The collections are a *logical* grouping, not a *physical* one. "
      "Keep the shared SGF pool as-is and add collection manifests that reference into it.")
    a("")

    # --- Section 9: Collections losing most under primary assignment ---
    a("## 9. Collections Most Affected by Primary-Only Assignment")
    a("")
    a("These collections would lose >50% of their puzzles if each puzzle is assigned to only its highest-priority collection:")
    a("")
    if losers:
        a("| Collection | Original | Kept | Lost % |")
        a("|:-----------|:--------:|:----:|:------:|")
        for c in sorted(losers, key=lambda x: x["lost_pct"], reverse=True)[:25]:
            a(f"| {c['name'][:55]} | {c['original']} | {c['assigned']} | {c['lost_pct']:.0f}% |")
    else:
        a("*(none — all collections keep >50% of their puzzles)*")
    a("")

    return "\n".join(lines)


def main():
    script_dir = Path(__file__).parent
    jsonl_path = script_dir / "20260211-203516-collections-sorted.jsonl"

    if not jsonl_path.exists():
        print(f"ERROR: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading collections from {jsonl_path.name}...")
    metadata, collections = load_collections(jsonl_path)
    print(f"  Loaded {len(collections)} collections")

    print("Analyzing overlap...")
    stats = analyze(collections)

    print("Computing storage scenarios...")
    scenarios, losers = compute_storage_scenarios(stats, collections)

    print("Generating report...")
    report = generate_report(metadata, collections, stats, scenarios, losers)

    output_path = script_dir / "collection-overlap-analysis.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to {output_path.name}")

    # Print key stats to console
    print(f"\n--- Key Stats ---")
    print(f"Total collections: {stats['total_collections']}")
    print(f"Unique puzzles:    {stats['unique_puzzles']:,}")
    print(f"Total slots:       {stats['total_slots']:,}")
    print(f"Duplication ratio: {stats['duplication_ratio']:.3f}x")
    print(f"Duplicated puzzles: {stats['duplicated_count']:,} ({stats['duplicated_pct']:.1f}%)")


if __name__ == "__main__":
    main()
