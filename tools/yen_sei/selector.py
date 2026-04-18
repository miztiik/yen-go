"""Expert-informed puzzle selector for yen-sei SFT training data.

Selection criteria designed with Go professional personas (Cho Chikun, Lee Sedol):
- Cho Chikun: pedagogical clarity, correct/wrong contrast, consequence explanations
- Lee Sedol: reading depth, shape recognition, 'almost right' moves

Scans ALL external-sources, scores each puzzle, produces a qualification report,
and copies only qualified puzzles into data/sources/.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.go_teaching_constants import (
    EXPLANATION_KEYWORDS,
    GO_TECHNIQUE_PATTERN,
    GO_TECHNIQUES,
    MARKER_ONLY_PATTERNS,
)
from tools.yen_sei.config import DATA_DIR, EXT_ROOT, SELECTION_MIN_SCORE, SOURCES_DIR


@dataclass
class PuzzleScore:
    """Score breakdown for a single puzzle."""
    file_path: str
    source: str
    board_size: int = 19
    stone_count: int = 0
    variation_count: int = 0
    comment_quality: str = "none"
    has_technique: bool = False
    has_tags: bool = False
    has_level: bool = False
    techniques_found: list[str] = field(default_factory=list)
    longest_comment_len: int = 0
    total_comment_chars: int = 0
    # Computed
    passes_gates: bool = False
    total_score: float = 0.0
    gate_failures: list[str] = field(default_factory=list)


def extract_sgf_props(content: str) -> dict:
    """Extract key properties from raw SGF text."""
    props: dict = {}

    # Board size
    m = re.search(r"SZ\[(\d+)\]", content)
    props["board_size"] = int(m.group(1)) if m else 19

    # Player to move
    m = re.search(r"PL\[([BW])\]", content)
    props["player"] = m.group(1) if m else "?"

    # Stone counts (count individual coordinates within AB[xx][yy] sequences)
    ab_stones = re.findall(r"AB(?:\[[a-s]{2}\])+", content)
    props["black_count"] = sum(s.count("[") for s in ab_stones)
    aw_stones = re.findall(r"AW(?:\[[a-s]{2}\])+", content)
    props["white_count"] = sum(s.count("[") for s in aw_stones)
    props["total_stones"] = props["black_count"] + props["white_count"]

    # Variation count (number of distinct paths)
    props["variation_count"] = content.count("(;")

    # Tags
    m = re.search(r"YT\[([^\]]+)\]", content)
    props["tags"] = m.group(1).split(",") if m else []

    # Level
    m = re.search(r"YG\[([^\]]+)\]", content)
    props["level"] = m.group(1) if m else ""

    # Collection
    m = re.search(r"YL\[([^\]]+)\]", content)
    props["collection"] = m.group(1) if m else ""

    # Extract ALL comments
    comments = []
    for cm in re.finditer(r"C\[((?:[^\\\]]|\\.)*)\]", content):
        text = cm.group(1).replace("\\]", "]").replace("\\\\", "\\")
        comments.append(text)
    props["comments"] = comments

    return props


def classify_comment_quality(comments: list[str]) -> str:
    """Classify the teaching quality of comments."""
    if not comments:
        return "none"

    non_marker = [c for c in comments if c.strip().lower() not in MARKER_ONLY_PATTERNS]
    if not non_marker:
        return "marker"

    max_len = max(len(c) for c in non_marker)
    has_technique = any(GO_TECHNIQUE_PATTERN.search(c) for c in non_marker)
    has_explanation = any(
        any(kw in c.lower() for kw in EXPLANATION_KEYWORDS)
        for c in non_marker
    )

    if max_len >= 150 and (has_technique or has_explanation):
        return "rich-teaching"
    if max_len >= 80 and (has_technique or has_explanation):
        return "teaching"
    if max_len >= 80:
        return "moderate"
    if max_len >= 40:
        return "brief"
    return "intent"


def score_puzzle(file_path: Path, source: str) -> PuzzleScore:
    """Score a single puzzle against expert criteria."""
    ps = PuzzleScore(file_path=str(file_path), source=source)

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        ps.gate_failures.append("unreadable")
        return ps

    props = extract_sgf_props(content)
    ps.board_size = props["board_size"]
    ps.stone_count = props["total_stones"]
    ps.variation_count = props["variation_count"]
    ps.has_tags = bool(props["tags"])
    ps.has_level = bool(props["level"])

    # Comment analysis
    ps.comment_quality = classify_comment_quality(props["comments"])
    non_marker = [c for c in props["comments"] if c.strip().lower() not in MARKERS]
    ps.longest_comment_len = max((len(c) for c in non_marker), default=0)
    ps.total_comment_chars = sum(len(c) for c in props["comments"])

    # Technique identification
    techniques = set()
    for c in props["comments"]:
        for m in GO_TECHNIQUE_PATTERN.finditer(c):
            techniques.add(m.group(1).lower())
    # Also check tags
    for tag in props["tags"]:
        tag_lower = tag.strip().lower().replace("-", " ")
        if tag_lower in GO_TECHNIQUES:
            techniques.add(tag_lower)
    ps.techniques_found = sorted(techniques)
    ps.has_technique = bool(techniques)

    # ── Hard gates ──
    # Gate 1: Must have variations (correct vs wrong paths)
    if ps.variation_count < 2:
        ps.gate_failures.append("no_variations")

    # Gate 2: Must have comments beyond pure markers
    if ps.comment_quality in ("none", "marker"):
        ps.gate_failures.append("no_teaching_comments")

    # Gate 3: Valid board size
    if ps.board_size not in (5, 6, 7, 9, 13, 19):
        ps.gate_failures.append("invalid_board_size")

    # Gate 4: Minimum stone count
    if ps.stone_count < 4:
        ps.gate_failures.append("too_few_stones")

    ps.passes_gates = len(ps.gate_failures) == 0

    if not ps.passes_gates:
        ps.total_score = 0.0
        return ps

    # ── Weighted scoring (only for puzzles passing gates) ──

    # Comment quality (40%)
    quality_scores = {
        "rich-teaching": 1.0,
        "teaching": 0.8,
        "moderate": 0.5,
        "brief": 0.3,
        "intent": 0.1,
    }
    comment_score = quality_scores.get(ps.comment_quality, 0.0)

    # Technique identification (25%)
    technique_score = min(len(ps.techniques_found) / 3.0, 1.0)

    # Stone density (15%) — sweet spot is 8-60
    if 8 <= ps.stone_count <= 60:
        density_score = 1.0
    elif ps.stone_count < 8:
        density_score = ps.stone_count / 8.0
    else:
        density_score = max(0.3, 1.0 - (ps.stone_count - 60) / 100.0)

    # Reading depth (10%) — more variations = deeper reading
    depth_score = min(ps.variation_count / 8.0, 1.0)

    # Metadata presence (10%)
    meta_score = 0.0
    if ps.has_tags:
        meta_score += 0.5
    if ps.has_level:
        meta_score += 0.5

    ps.total_score = (
        0.40 * comment_score
        + 0.25 * technique_score
        + 0.15 * density_score
        + 0.10 * depth_score
        + 0.10 * meta_score
    )

    return ps


def scan_all_sources(verbose: bool = True) -> dict[str, list[PuzzleScore]]:
    """Scan all external-source directories and score every puzzle."""
    results: dict[str, list[PuzzleScore]] = {}

    for source_dir in sorted(EXT_ROOT.iterdir()):
        if not source_dir.is_dir():
            continue
        name = source_dir.name
        sgf_files = sorted(source_dir.rglob("*.sgf"))
        if not sgf_files:
            if verbose:
                print(f"  {name}: 0 SGFs (skipped)")
            continue

        if verbose:
            print(f"  Scanning {name}: {len(sgf_files)} SGFs...", end="", flush=True)

        scores = []
        for sgf_path in sgf_files:
            scores.append(score_puzzle(sgf_path, name))

        results[name] = scores
        passed = sum(1 for s in scores if s.passes_gates)
        if verbose:
            print(f" {passed}/{len(scores)} passed gates")

    return results


def generate_report(results: dict[str, list[PuzzleScore]]) -> str:
    """Generate a detailed qualification report."""
    lines: list[str] = []
    lines.append("=" * 90)
    lines.append("YEN-SEI PUZZLE QUALIFICATION REPORT")
    lines.append("Selection criteria: Cho Chikun + Lee Sedol expert consultation")
    lines.append("=" * 90)

    # Summary
    total_sgfs = sum(len(v) for v in results.values())
    total_passed = sum(sum(1 for s in v if s.passes_gates) for v in results.values())
    lines.append(f"\nTotal SGFs scanned: {total_sgfs:,}")
    lines.append(f"Total passing gates: {total_passed:,} ({total_passed / total_sgfs * 100:.1f}%)")

    # Gate failure breakdown
    all_failures: Counter[str] = Counter()
    for scores in results.values():
        for s in scores:
            for f in s.gate_failures:
                all_failures[f] += 1
    lines.append(f"\nGate failures (across all sources):")
    for failure, count in all_failures.most_common():
        lines.append(f"  {failure}: {count:,}")

    # Per-source table
    lines.append(f"\n{'Source':<28} {'Total':>7} {'Passed':>7} {'Rate':>6} {'Avg Score':>10} {'Top Quality':>12}")
    lines.append("-" * 80)

    source_summaries = []
    for name in sorted(results.keys()):
        scores = results[name]
        passed = [s for s in scores if s.passes_gates]
        rate = len(passed) / len(scores) * 100 if scores else 0
        avg_score = sum(s.total_score for s in passed) / len(passed) if passed else 0
        # Top quality tier
        quality_dist = Counter(s.comment_quality for s in passed)
        top = quality_dist.most_common(1)[0][0] if quality_dist else "n/a"
        source_summaries.append((name, len(scores), len(passed), rate, avg_score, top))
        lines.append(f"{name:<28} {len(scores):>7} {len(passed):>7} {rate:>5.1f}% {avg_score:>10.3f} {top:>12}")

    # Score distribution for passed puzzles
    lines.append(f"\n\nSCORE DISTRIBUTION (passed puzzles only)")
    lines.append("-" * 50)
    all_passed = [s for scores in results.values() for s in scores if s.passes_gates]
    if all_passed:
        brackets = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
        for lo, hi in brackets:
            count = sum(1 for s in all_passed if lo <= s.total_score < hi)
            bar = "#" * (count // max(1, len(all_passed) // 50))
            lines.append(f"  {lo:.1f}-{hi:.1f}: {count:>6} {bar}")

    # Technique coverage
    lines.append(f"\n\nTECHNIQUE COVERAGE (in passed puzzles)")
    lines.append("-" * 50)
    tech_counter: Counter[str] = Counter()
    for s in all_passed:
        for t in s.techniques_found:
            tech_counter[t] += 1
    for tech, count in tech_counter.most_common(20):
        lines.append(f"  {tech:<25} {count:>6}")

    # Per-source detail
    lines.append(f"\n\n{'=' * 90}")
    lines.append("PER-SOURCE DETAIL")
    lines.append("=" * 90)

    for name in sorted(results.keys()):
        scores = results[name]
        passed = [s for s in scores if s.passes_gates]
        if not passed:
            lines.append(f"\n{name}: 0 passed — EXCLUDED")
            failures = Counter(f for s in scores for f in s.gate_failures)
            if failures:
                lines.append(f"  Failure reasons: {dict(failures.most_common())}")
            continue

        lines.append(f"\n{name}: {len(passed)}/{len(scores)} passed")
        quality = Counter(s.comment_quality for s in passed)
        lines.append(f"  Quality: {dict(quality.most_common())}")
        avg = sum(s.total_score for s in passed) / len(passed)
        top5 = sorted(passed, key=lambda s: s.total_score, reverse=True)[:5]
        lines.append(f"  Avg score: {avg:.3f}")
        lines.append(f"  Top 5 puzzles:")
        for s in top5:
            fname = Path(s.file_path).name
            techs = ", ".join(s.techniques_found[:3]) if s.techniques_found else "none"
            lines.append(f"    {fname} score={s.total_score:.3f} quality={s.comment_quality} techniques=[{techs}] stones={s.stone_count}")

    # Recommendation tiers
    lines.append(f"\n\n{'=' * 90}")
    lines.append("RECOMMENDATIONS")
    lines.append("=" * 90)

    tier_a = []  # score >= 0.5
    tier_b = []  # score >= 0.3
    tier_c = []  # passed gates but score < 0.3

    for s in all_passed:
        if s.total_score >= 0.5:
            tier_a.append(s)
        elif s.total_score >= 0.3:
            tier_b.append(s)
        else:
            tier_c.append(s)

    lines.append(f"\nTier A (score >= 0.5, high-quality teaching): {len(tier_a):,} puzzles")
    lines.append(f"Tier B (score >= 0.3, usable with augmentation): {len(tier_b):,} puzzles")
    lines.append(f"Tier C (score < 0.3, passed gates but thin): {len(tier_c):,} puzzles")

    # Source breakdown per tier
    tier_a_by_source = Counter(s.source for s in tier_a)
    tier_b_by_source = Counter(s.source for s in tier_b)
    lines.append(f"\nTier A by source: {dict(tier_a_by_source.most_common())}")
    lines.append(f"Tier B by source: {dict(tier_b_by_source.most_common())}")

    lines.append(f"\nSuggested action:")
    lines.append(f"  1. Copy Tier A ({len(tier_a):,} puzzles) — these are our SFT gold")
    lines.append(f"  2. Copy Tier B ({len(tier_b):,} puzzles) — augment with synthetic comments from Tier 1 model")
    lines.append(f"  3. Skip Tier C — too thin for training value")
    lines.append(f"  Total to copy: {len(tier_a) + len(tier_b):,} puzzles")

    return "\n".join(lines)


def copy_qualified(
    results: dict[str, list[PuzzleScore]],
    min_score: float = SELECTION_MIN_SCORE,
) -> dict[str, int]:
    """Copy qualified puzzles into a flat data/sources/ directory.

    Files are named {source}__{original_name}.sgf for provenance tracking.
    The double-underscore separator avoids ambiguity with source names
    that contain underscores (e.g., goproblems_difficulty_based).
    """
    copied: dict[str, int] = defaultdict(int)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    for source_name, scores in results.items():
        qualified = [s for s in scores if s.passes_gates and s.total_score >= min_score]
        if not qualified:
            continue

        for ps in qualified:
            src = Path(ps.file_path)
            dst = SOURCES_DIR / f"{source_name}__{src.name}"
            shutil.copy2(src, dst)
            copied[source_name] += 1

    return dict(copied)


if __name__ == "__main__":
    import sys
    import time

    print("YEN-SEI Puzzle Selector")
    print("Scanning all external sources...\n")

    start = time.time()
    results = scan_all_sources(verbose=True)
    elapsed = time.time() - start
    print(f"\nScan completed in {elapsed:.1f}s")

    report = generate_report(results)
    print("\n" + report)

    # Save report
    report_path = DATA_DIR / "qualification_report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    # Save detailed JSON for programmatic use
    json_path = DATA_DIR / "qualification_scores.json"
    json_data = {}
    for source, scores in results.items():
        json_data[source] = {
            "total": len(scores),
            "passed": sum(1 for s in scores if s.passes_gates),
            "tier_a": sum(1 for s in scores if s.passes_gates and s.total_score >= 0.5),
            "tier_b": sum(1 for s in scores if s.passes_gates and 0.3 <= s.total_score < 0.5),
            "tier_c": sum(1 for s in scores if s.passes_gates and s.total_score < 0.3),
        }
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
    print(f"Scores saved to: {json_path}")

    if "--copy" in sys.argv:
        min_score = SELECTION_MIN_SCORE
        for arg in sys.argv:
            if arg.startswith("--min-score="):
                min_score = float(arg.split("=")[1])
        print(f"\nCopying qualified puzzles (min_score={min_score})...")
        copied = copy_qualified(results, min_score=min_score)
        total = sum(copied.values())
        print(f"Copied {total:,} puzzles:")
        for src, count in sorted(copied.items(), key=lambda x: x[1], reverse=True):
            print(f"  {src}: {count:,}")
    else:
        print("\nDry run — no files copied. Use --copy to copy qualified puzzles.")
