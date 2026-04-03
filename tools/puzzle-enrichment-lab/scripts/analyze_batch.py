"""Analyze Phase R batch results."""
import json
import os
from collections import Counter

for label, folder in [("INTERMEDIATE", "phase-r-intermediate"), ("ADVANCED", "phase-r-advanced")]:
    full_path = os.path.join(os.path.dirname(__file__), folder)
    levels = []
    statuses = Counter()
    scores = []
    ref_types = Counter()
    curated_counts = []
    details = []

    for f in sorted(os.listdir(full_path)):
        if not f.endswith(".json"):
            continue
        data = json.load(open(os.path.join(full_path, f)))
        status = data.get("status_label", "unknown")
        statuses[status] += 1
        diff = data.get("difficulty", {})
        level = diff.get("suggested_level", "unknown")
        score = diff.get("composite_score", 0)
        depth = diff.get("solution_depth", 0)
        branches = diff.get("branch_count", 0)
        candidates = diff.get("local_candidate_count", 0)
        refs_count = diff.get("refutation_count", 0)
        levels.append(level)
        scores.append(score)
        details.append({
            "name": f.replace(".json", ""),
            "level": level,
            "score": score,
            "depth": depth,
            "branches": branches,
            "candidates": candidates,
            "refs": refs_count,
            "status": status,
        })

        refs = data.get("refutations", [])
        for r in refs:
            ref_types[r.get("refutation_type", "unknown")] += 1
        curated = sum(1 for r in refs if r.get("refutation_type") == "curated")
        curated_counts.append(curated)

    level_dist = Counter(levels)
    print(f"\n{'='*80}")
    print(f"  {label} COLLECTION (Cho Chikun Life & Death)")
    print(f"{'='*80}")
    print(f"  Status:  {dict(statuses)}")
    print("  Levels:")
    for lv in ["novice", "beginner", "elementary", "intermediate", "upper-intermediate", "advanced", "low-dan", "high-dan", "expert"]:
        if lv in level_dist:
            bar = "#" * level_dist[lv]
            print(f"    {lv:22s} {level_dist[lv]:2d}  {bar}")
    print(f"  Scores:  min={min(scores):.1f}  max={max(scores):.1f}  avg={sum(scores)/len(scores):.1f}")
    print(f"  Refs:    {dict(ref_types)}  (avg curated/puzzle: {sum(curated_counts)/len(curated_counts):.1f})")

    print(f"\n  {'Puzzle':<12} {'Level':<22} {'Score':>5} {'Depth':>5} {'Br':>3} {'Cand':>4} {'Refs':>4} {'Status':<10}")
    print(f"  {'-'*72}")
    for d in details:
        print(f"  {d['name']:<12} {d['level']:<22} {d['score']:5.0f} {d['depth']:5d} {d['branches']:3d} {d['candidates']:4d} {d['refs']:4d} {d['status']:<10}")
