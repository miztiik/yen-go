"""Quick Cycle 1 analysis - show flagged/rejected puzzles with details."""

import json
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
OUTPUT = LAB / "output" / "cycle-1"

for coll in ["cho-elementary", "cho-intermediate", "cho-advanced"]:
    summary_path = OUTPUT / coll / "_summary.json"
    if not summary_path.exists():
        print(f"=== {coll}: NO DATA ===")
        continue

    data = json.loads(summary_path.read_text())
    print(f"\n=== {coll} ===")

    accepted = 0
    flagged = 0
    rejected = 0

    for p in data["puzzles"]:
        status = p["status"]
        if status == "accepted":
            accepted += 1
        elif status == "flagged":
            flagged += 1
            src = p["file"]
            flags = p.get("flags", [])
            rank_flag = [f for f in flags if f.startswith("rank:")]
            wr_flag = [f for f in flags if f.startswith("winrate:")]
            reason = [f for f in flags if f.startswith("reason:") or f == "winrate_rescue"]
            print(f"  FLAGGED: {src}  {reason}  {rank_flag}  {wr_flag}")
        else:
            rejected += 1
            src = p["file"]
            flags = p.get("flags", [])
            rank_flag = [f for f in flags if f.startswith("rank:")]
            wr_flag = [f for f in flags if f.startswith("winrate:")]
            reason = [f for f in flags if f.startswith("reason:")]
            print(f"  REJECTED: {src}  {reason}  {rank_flag}  {wr_flag}")

    print(f"  Totals: {accepted} accepted, {flagged} flagged, {rejected} rejected")
