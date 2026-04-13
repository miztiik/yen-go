"""Dry-run enrichment report for Xuan Xuan Qi Jing.

Reads the audit ledger + solution cache to simulate what enrichment
would produce for all 347 puzzles WITHOUT modifying any files.
Outputs a detailed report to _working/xuanxuan-qijing/_dry_run_report.md
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Ensure repo root on sys.path
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

WORKING_DIR = _SCRIPT_DIR / "_working" / "xuanxuan-qijing"
LEDGER_PATH = WORKING_DIR / "_audit_ledger.json"
SOL_CACHE_DIR = WORKING_DIR / "_solution_cache"
PAGE_CACHE_DIR = WORKING_DIR / "_page_cache"

ORIG_DIR = _REPO_ROOT / "external-sources" / "kisvadim-goproblems" / "TSUMEGO CLASSIC - Xuan Xuan Qi Jing"
ENRICHED_DIR = _REPO_ROOT / "external-sources" / "kisvadim-goproblems" / "TSUMEGO CLASSIC - Xuan Xuan Qi Jing-enriched"


def load_ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def load_solution_cache(n: int) -> dict | None:
    path = SOL_CACHE_DIR / f"{n:04d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def load_page_cache(n: int) -> dict | None:
    path = PAGE_CACHE_DIR / f"{n:04d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def analyze_entry(entry: dict) -> dict:
    """Analyze a single audit ledger entry for enrichment potential."""
    n = entry["problem_number"]
    result = {
        "problem_number": n,
        "local_file_exists": entry.get("local_file_exists", False),
        "decision": entry.get("decision", ""),
        "match_class": entry.get("match_class", ""),
        "solution_status": entry.get("solution_status", ""),
        "diagram_count": entry.get("diagram_count", 0),
        "total_commentary_chars": entry.get("total_commentary_chars", 0),
        # What would be added
        "will_add_root_comment": False,
        "will_add_solution_commentary": False,
        "will_set_difficulty": False,
        "will_set_title": False,
        "root_comment_parts": [],
        "solution_diagrams_with_text": 0,
        "issues": [],
        "category": "unknown",
    }

    if not entry.get("local_file_exists"):
        result["issues"].append("Local file missing")
        result["category"] = "skip_no_file"
        return result

    decision = entry.get("decision", "")
    if decision == "review":
        result["issues"].append(f"Flagged for manual review: {entry.get('decision_reason', '')}")
        result["category"] = "needs_review"
        return result

    # Check page data enrichments
    page_status = entry.get("page_status", "")
    if page_status != "ok":
        result["issues"].append(f"Page fetch failed: {page_status}")
    else:
        # Title
        title_eng = entry.get("title_english", "")
        if title_eng and title_eng != "See also":  # "See also" is a parser artifact
            result["will_set_title"] = True
            result["root_comment_parts"].append(f"Title: {title_eng}")

        # Difficulty
        difficulty = entry.get("difficulty", "")
        if difficulty and difficulty.lower() in ("advanced", "expert"):
            result["will_set_difficulty"] = True
            result["root_comment_parts"].append(f"Difficulty: {difficulty}")

        # Instruction
        instruction = entry.get("instruction", "")
        if instruction:
            result["will_add_root_comment"] = True
            result["root_comment_parts"].append(f"Instruction: {instruction}")

    # Check solution data enrichments
    sol_status = entry.get("solution_status", "")
    if sol_status == "ok":
        diagram_count = entry.get("diagram_count", 0)
        commentary_chars = entry.get("total_commentary_chars", 0)
        if diagram_count > 0 and commentary_chars > 0:
            # Load actual solution cache to count diagrams with commentary
            sol_data = load_solution_cache(n)
            diagrams_with_text = 0
            if sol_data and "diagrams" in sol_data:
                for diag in sol_data["diagrams"]:
                    if diag.get("commentary", "").strip():
                        diagrams_with_text += 1
            result["solution_diagrams_with_text"] = diagrams_with_text
            if diagrams_with_text > 0:
                result["will_add_solution_commentary"] = True
        elif diagram_count > 0 and commentary_chars == 0:
            result["issues"].append(f"Has {diagram_count} diagrams but no commentary text")
    elif sol_status == "404":
        result["issues"].append("Solution page 404 (no solution on Senseis)")
    elif sol_status == "empty":
        result["issues"].append("Solution page empty")

    # Match quality issues
    match_class = entry.get("match_class", "")
    if match_class == "translated_mismatch" and decision == "enrich_number_fallback":
        result["issues"].append(
            "Position mismatch — using number-based fallback "
            "(commentary coordinates may be wrong if board is reflected/rotated)"
        )

    # Categorize
    has_commentary = result["will_add_solution_commentary"]
    has_metadata = result["will_add_root_comment"] or result["will_set_title"]
    has_difficulty = result["will_set_difficulty"]

    if has_commentary and has_metadata:
        result["category"] = "full_enrichment"
    elif has_commentary:
        result["category"] = "commentary_only"
    elif has_metadata:
        result["category"] = "metadata_only"
    elif has_difficulty:
        result["category"] = "difficulty_only"
    else:
        result["category"] = "no_enrichment"

    return result


def generate_report(ledger: dict, analyses: list[dict]) -> str:
    """Generate the markdown report."""
    summary = ledger["summary"]
    lines: list[str] = []

    lines.append("# Xuan Xuan Qi Jing — Senseis Enrichment Dry-Run Report")
    lines.append(f"\n**Date**: 2026-04-09")
    lines.append(f"**Source**: `external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - Xuan Xuan Qi Jing`")
    lines.append(f"**Total puzzles**: {summary['total']}")
    lines.append(f"**Already enriched**: 4 (checkpoint at problem 4)")
    lines.append(f"**Remaining**: {summary['total'] - 4}")
    lines.append("")

    # --- High-level summary ---
    lines.append("## Executive Summary")
    lines.append("")

    cat_counts = Counter(a["category"] for a in analyses)
    will_commentary = sum(1 for a in analyses if a["will_add_solution_commentary"])
    will_metadata = sum(1 for a in analyses if a["will_add_root_comment"] or a["will_set_title"])
    will_difficulty = sum(1 for a in analyses if a["will_set_difficulty"])
    has_issues = sum(1 for a in analyses if a["issues"])

    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Puzzles gaining **solution commentary** (new move-node comments) | **{will_commentary}** |")
    lines.append(f"| Puzzles gaining **root comment metadata** (title, instruction) | **{will_metadata}** |")
    lines.append(f"| Puzzles gaining **difficulty tag** (YG) | **{will_difficulty}** |")
    lines.append(f"| Puzzles with **issues/warnings** | **{has_issues}** |")
    lines.append(f"| Puzzles with **no enrichment possible** | **{cat_counts.get('no_enrichment', 0)}** |")
    lines.append("")

    # --- Category breakdown ---
    lines.append("## Enrichment Categories")
    lines.append("")
    cat_labels = {
        "full_enrichment": "Full enrichment (commentary + metadata)",
        "commentary_only": "Solution commentary only",
        "metadata_only": "Metadata only (title/instruction, no commentary)",
        "difficulty_only": "Difficulty tag only",
        "no_enrichment": "No enrichment possible",
        "needs_review": "Needs manual review",
        "skip_no_file": "Local file missing",
    }
    lines.append("| Category | Count | % |")
    lines.append("|----------|-------|---|")
    for cat in ["full_enrichment", "commentary_only", "metadata_only", "difficulty_only", "no_enrichment", "needs_review", "skip_no_file"]:
        count = cat_counts.get(cat, 0)
        pct = f"{count / len(analyses) * 100:.1f}%"
        lines.append(f"| {cat_labels.get(cat, cat)} | {count} | {pct} |")
    lines.append("")

    # --- Position matching quality ---
    lines.append("## Position Matching Quality")
    lines.append("")
    lines.append("| Match Class | Count | Description |")
    lines.append("|-------------|-------|-------------|")
    for cls, count in sorted(summary["by_match_class"].items(), key=lambda x: -x[1]):
        desc = {
            "exact_match": "Identical position hash (identity transform)",
            "rotated_match": "Match after D4 rotation/reflection",
            "translated_mismatch": "Position differs — number-based fallback used",
        }.get(cls, cls)
        lines.append(f"| {cls} | {count} | {desc} |")
    lines.append("")

    # --- Solution availability ---
    lines.append("## Solution Data Availability")
    lines.append("")
    lines.append("| Status | Count | Description |")
    lines.append("|--------|-------|-------------|")
    for status, count in sorted(summary["by_solution_status"].items(), key=lambda x: -x[1]):
        desc = {
            "ok": "Solution page found with diagram(s)",
            "404": "No solution page on Senseis Library",
            "empty": "Solution page exists but has no diagrams",
        }.get(status, status)
        lines.append(f"| {status} | {count} | {desc} |")
    lines.append("")

    # Commentary volume stats
    commentary_chars = [a["total_commentary_chars"] for a in analyses if a["total_commentary_chars"] > 0]
    diagram_counts = [a["solution_diagrams_with_text"] for a in analyses if a["solution_diagrams_with_text"] > 0]
    if commentary_chars:
        lines.append("### Commentary Volume")
        lines.append("")
        lines.append(f"- Puzzles with any commentary: **{len(commentary_chars)}**")
        lines.append(f"- Total commentary characters: **{sum(commentary_chars):,}**")
        lines.append(f"- Average per puzzle (when present): **{sum(commentary_chars) // len(commentary_chars):,} chars**")
        lines.append(f"- Min: {min(commentary_chars)} chars, Max: {max(commentary_chars):,} chars")
        if diagram_counts:
            lines.append(f"- Average diagrams with commentary per puzzle: **{sum(diagram_counts) / len(diagram_counts):.1f}**")
        lines.append("")

    # --- Metadata coverage ---
    lines.append("## Metadata Coverage (from Senseis)")
    lines.append("")
    mc = summary["metadata_coverage"]
    lines.append("| Field | Puzzles with data | % |")
    lines.append("|-------|-------------------|---|")
    for field_name, readable in [
        ("title_english", "English title"),
        ("title_chinese", "Chinese title"),
        ("difficulty", "Difficulty rating"),
        ("instruction", "Play instruction (e.g. 'Black to play')"),
        ("has_commentary", "Has solution commentary"),
    ]:
        count = mc.get(field_name, 0)
        pct = f"{count / summary['total'] * 100:.1f}%"
        lines.append(f"| {readable} | {count} | {pct} |")
    lines.append("")

    # --- Issues detail ---
    lines.append("## Issues & Warnings")
    lines.append("")

    issue_counter: Counter = Counter()
    for a in analyses:
        for issue in a["issues"]:
            # Normalize for counting
            key = issue.split("—")[0].strip() if "—" in issue else issue.split(":")[0].strip() if ":" in issue else issue
            issue_counter[key] += 1

    lines.append("### Issue Summary")
    lines.append("")
    lines.append("| Issue | Count |")
    lines.append("|-------|-------|")
    for issue, count in issue_counter.most_common():
        lines.append(f"| {issue} | {count} |")
    lines.append("")

    # Detailed list of problems needing review
    review_problems = [a for a in analyses if a["category"] == "needs_review"]
    if review_problems:
        lines.append("### Problems Needing Manual Review")
        lines.append("")
        for a in review_problems:
            lines.append(f"- **Problem {a['problem_number']}**: {'; '.join(a['issues'])}")
        lines.append("")

    # Problems with coordinate mismatch risk
    mismatch_problems = [a for a in analyses if a["match_class"] == "translated_mismatch" and a["will_add_solution_commentary"]]
    if mismatch_problems:
        lines.append("### Coordinate Risk: Position Mismatch + Commentary")
        lines.append("")
        lines.append("These puzzles have **translated positions** (hash mismatch) AND solution commentary.")
        lines.append("Commentary coordinates may point to wrong squares if the board orientation differs.")
        lines.append("")
        lines.append("| Problem | Diagrams | Commentary chars | Decision |")
        lines.append("|---------|----------|-----------------|----------|")
        for a in mismatch_problems:
            lines.append(f"| {a['problem_number']:04d} | {a['solution_diagrams_with_text']} | {a['total_commentary_chars']} | {a['decision']} |")
        lines.append("")

    # Problems with 404 solutions
    no_sol = [a for a in analyses if a["solution_status"] == "404"]
    if no_sol:
        lines.append("### Puzzles Without Solution Pages (404)")
        lines.append("")
        lines.append(f"**{len(no_sol)} puzzles** have no solution page on Senseis Library.")
        lines.append("These will receive metadata (title/instruction/difficulty) but NO solution commentary.")
        lines.append("")
        # Group into ranges for readability
        nums = sorted(a["problem_number"] for a in no_sol)
        ranges = []
        start = nums[0]
        prev = nums[0]
        for n in nums[1:]:
            if n == prev + 1:
                prev = n
            else:
                ranges.append((start, prev))
                start = prev = n
        ranges.append((start, prev))
        range_strs = []
        for s, e in ranges:
            if s == e:
                range_strs.append(str(s))
            else:
                range_strs.append(f"{s}-{e}")
        lines.append(f"Problem numbers: {', '.join(range_strs)}")
        lines.append("")

    # --- Per-puzzle detail table (top enrichment candidates) ---
    lines.append("## Top Enrichment Candidates (by commentary volume)")
    lines.append("")
    lines.append("Top 30 puzzles by commentary character count:")
    lines.append("")
    lines.append("| # | Problem | Match | Diagrams | Commentary | Title |")
    lines.append("|---|---------|-------|----------|------------|-------|")
    top = sorted(analyses, key=lambda a: a["total_commentary_chars"], reverse=True)[:30]
    for i, a in enumerate(top, 1):
        title = ""
        entry = next((e for e in ledger["entries"] if e["problem_number"] == a["problem_number"]), None)
        if entry:
            title = entry.get("title_english", "")[:40]
        lines.append(
            f"| {i} | {a['problem_number']:04d} | {a['match_class']} | "
            f"{a['solution_diagrams_with_text']} | {a['total_commentary_chars']} chars | {title} |"
        )
    lines.append("")

    # --- Difficulty distribution ---
    lines.append("## Difficulty Distribution")
    lines.append("")
    diff_counter: Counter = Counter()
    for entry in ledger["entries"]:
        diff = entry.get("difficulty", "Unknown")
        diff_counter[diff] += 1
    lines.append("| Difficulty | Count |")
    lines.append("|-----------|-------|")
    for diff, count in diff_counter.most_common():
        lines.append(f"| {diff} | {count} |")
    lines.append("")

    # --- Recommendation ---
    lines.append("## Recommendation")
    lines.append("")

    safe_count = sum(1 for a in analyses if a["match_class"] in ("exact_match", "rotated_match") and a["will_add_solution_commentary"])
    fallback_count = len(mismatch_problems)
    lines.append(f"- **{safe_count}** puzzles can be safely enriched (exact/rotated match + commentary)")
    lines.append(f"- **{fallback_count}** puzzles use number-based fallback with commentary (coordinate risk)")
    lines.append(f"- **{len(no_sol)}** puzzles will get metadata only (no solution on Senseis)")
    lines.append(f"- **{len(review_problems)}** puzzles need manual review before enrichment")
    lines.append("")
    lines.append("### Suggested Execution Plan")
    lines.append("")
    lines.append("1. Run enrichment for exact/rotated matches first (safe batch)")
    lines.append("2. Review the number-fallback puzzles for coordinate correctness")
    lines.append("3. Run remaining enrichment after review")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Loading audit ledger...")
    ledger = load_ledger()
    entries = ledger["entries"]
    print(f"  {len(entries)} entries loaded")

    print("Analyzing enrichment potential...")
    analyses = []
    for entry in entries:
        analysis = analyze_entry(entry)
        analyses.append(analysis)

    print("Generating report...")
    report = generate_report(ledger, analyses)

    # Write report
    report_path = WORKING_DIR / "_dry_run_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {report_path}")

    # Also write a JSON summary for machine consumption
    json_summary = {
        "total_puzzles": len(analyses),
        "already_enriched": 4,
        "remaining": len(analyses) - 4,
        "will_add_commentary": sum(1 for a in analyses if a["will_add_solution_commentary"]),
        "will_add_metadata": sum(1 for a in analyses if a["will_add_root_comment"] or a["will_set_title"]),
        "will_set_difficulty": sum(1 for a in analyses if a["will_set_difficulty"]),
        "has_issues": sum(1 for a in analyses if a["issues"]),
        "categories": dict(Counter(a["category"] for a in analyses)),
        "by_match_and_commentary": {
            "exact_match_with_commentary": sum(1 for a in analyses if a["match_class"] == "exact_match" and a["will_add_solution_commentary"]),
            "rotated_match_with_commentary": sum(1 for a in analyses if a["match_class"] == "rotated_match" and a["will_add_solution_commentary"]),
            "translated_mismatch_with_commentary": sum(1 for a in analyses if a["match_class"] == "translated_mismatch" and a["will_add_solution_commentary"]),
        },
        "problems_needing_review": [a["problem_number"] for a in analyses if a["category"] == "needs_review"],
        "problems_with_404_solution": [a["problem_number"] for a in analyses if a["solution_status"] == "404"],
    }
    json_path = WORKING_DIR / "_dry_run_summary.json"
    json_path.write_text(json.dumps(json_summary, indent=2), encoding="utf-8")
    print(f"JSON summary written to: {json_path}")

    # Print key numbers
    print(f"\n{'='*60}")
    print(f"  ENRICHMENT DRY-RUN SUMMARY")
    print(f"{'='*60}")
    print(f"  Total puzzles:                 {len(analyses)}")
    print(f"  Will gain solution commentary: {json_summary['will_add_commentary']}")
    print(f"  Will gain metadata:            {json_summary['will_add_metadata']}")
    print(f"  Will gain difficulty tag:       {json_summary['will_set_difficulty']}")
    print(f"  Have issues/warnings:          {json_summary['has_issues']}")
    print(f"  Safe to enrich (exact/rot):    {json_summary['by_match_and_commentary']['exact_match_with_commentary'] + json_summary['by_match_and_commentary']['rotated_match_with_commentary']}")
    print(f"  Coordinate risk (fallback):    {json_summary['by_match_and_commentary']['translated_mismatch_with_commentary']}")
    print(f"  Needs manual review:           {len(json_summary['problems_needing_review'])}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
