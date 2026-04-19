"""Post-enrichment evaluation system.

Validates enriched SGFs against source truth (solution cache + page cache).
Samples a configurable percentage, stratified by solution richness.
100% of the sampled problems must pass all required checks.

Supports position-mapped collections (e.g. Gokyo Shumyo) where Senseis
global numbers differ from local file numbers.

Usage:
    python -m tools.senseis_enrichment --config <config.json> --eval
    python -m tools.senseis_enrichment --config <config.json> --eval --eval-pct 50
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from tools.core.sgf_parser import SgfNode, parse_sgf, read_sgf_file

from tools.senseis_enrichment.config import SenseisConfig, load_config

logger = logging.getLogger("senseis_enrichment.eval")

# Strip B1/W2 style move references for fingerprinting
_MOVE_REF_RE = re.compile(r"\b[BW]\d+\b")


class EvalPair(NamedTuple):
    """Evaluation pair: local file number + Senseis cache number."""

    local_n: int
    senseis_n: int


def _load_eval_mapping(config: SenseisConfig) -> list[EvalPair] | None:
    """Load position mapping for eval. Returns None if not position-mapped."""
    mapping_path = config.working_dir() / "_position_mapping.json"
    if not mapping_path.exists():
        return None

    with open(mapping_path, encoding="utf-8") as f:
        data = json.load(f)

    if "mappings" not in data:
        return None

    return [
        EvalPair(local_n=m["local_n"], senseis_n=m["senseis_global"])
        for m in data["mappings"]
    ]


# --- Data structures ---


@dataclass
class CheckResult:
    """Result of a single evaluation check."""

    name: str
    status: str  # "pass", "fail", "skip"
    detail: str = ""


@dataclass
class ProblemEval:
    """Evaluation results for one problem."""

    problem_number: int
    checks: list[CheckResult] = field(default_factory=list)
    diagram_coverage_pct: float = -1.0  # -1 = not applicable

    @property
    def passed(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    @property
    def required_passed(self) -> bool:
        return all(
            c.status != "fail"
            for c in self.checks
            if c.name != "diagram_coverage"
        )


@dataclass
class EvalReport:
    """Full evaluation report."""

    collection: str
    total_problems: int
    sample_size: int
    sample_pct: float
    results: list[ProblemEval] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.required_passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.required_passed)

    @property
    def overall_pass(self) -> bool:
        return all(r.required_passed for r in self.results)


# --- Helpers ---


def _collect_all_comments(node: SgfNode, depth: int = 0) -> list[tuple[int, str]]:
    """Walk tree collecting (depth, comment) pairs from all nodes."""
    results: list[tuple[int, str]] = []
    if node.comment:
        results.append((depth, node.comment))
    for child in node.children:
        results.extend(_collect_all_comments(child, depth + 1))
    return results


def _count_move_nodes(node: SgfNode) -> int:
    """Count total move nodes in tree (excluding root)."""
    count = 0
    for child in node.children:
        if child.move:
            count += 1
        count += _count_move_nodes(child)
    return count


def _fingerprint(text: str) -> str:
    """Extract a stable fingerprint from commentary for matching.

    Strips move references (B1, W2), label references ('a', 'b', etc.),
    and bracketed numbers ([1], [2]) since these get transformed during
    enrichment. Returns lowercase words joined by spaces.
    """
    cleaned = _MOVE_REF_RE.sub("", text)
    # Strip single-letter label references
    cleaned = re.sub(r"'[a-z]'", "", cleaned)
    # Strip bracketed numbers (full-width or regular brackets)
    cleaned = re.sub(r"[\[\uff3b]\d+[\]\uff3d]", "", cleaned)
    words = cleaned.split()
    # Take first ~8 content words (skip very short words)
    content_words = [w.strip(".,;:!?()") for w in words if len(w) > 2]
    return " ".join(content_words[:8]).lower()


def _load_page_cache(cache_dir: Path, n: int) -> dict | None:
    """Load page cache JSON for problem n."""
    path = cache_dir / f"{n:04d}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_solution_cache(cache_dir: Path, n: int) -> dict | None:
    """Load solution cache JSON for problem n."""
    path = cache_dir / f"{n:04d}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _diagram_has_moves(sgf_content: str) -> bool:
    """Check if a diagram SGF actually contains move nodes (;B[..] or ;W[..])."""
    if not sgf_content:
        return False
    try:
        tree = parse_sgf(sgf_content)
        # Check if any child node has an actual move (not just label/property nodes)
        for child in tree.solution_tree.children:
            if child.move is not None:
                return True
        return False
    except Exception:
        return False


# --- Sampling ---


def select_eval_sample(
    config: SenseisConfig,
    solution_cache_dir: Path,
    sample_pct: float = 40.0,
    seed: int = 42,
    mapping: list[EvalPair] | None = None,
) -> list[EvalPair]:
    """Select problems for evaluation, stratified by solution richness.

    Buckets:
      Rich (3+ diagrams with commentary): sample 50%
      Medium (1-2 diagrams with commentary): sample 40%
      Metadata-only (no commentary): sample 25%

    When mapping is provided, iterates mapped entries (local_n/senseis_n pairs).
    Otherwise, assumes N<->N identity mapping (Xuan Xuan, Hatsuyo-ron).
    """
    rich: list[EvalPair] = []
    medium: list[EvalPair] = []
    metadata_only: list[EvalPair] = []

    # Build list of eval pairs
    if mapping is not None:
        pairs = mapping
    else:
        pairs = [EvalPair(n, n) for n in range(1, config.problem_count + 1)]

    for pair in pairs:
        sol = _load_solution_cache(solution_cache_dir, pair.senseis_n)
        if sol and sol.get("status") == "ok":
            diagrams_with_commentary = [
                d for d in sol.get("diagrams", [])
                if d.get("commentary", "").strip()
            ]
            count = len(diagrams_with_commentary)
            if count >= 3:
                rich.append(pair)
            elif count >= 1:
                medium.append(pair)
            else:
                metadata_only.append(pair)
        else:
            metadata_only.append(pair)

    rng = random.Random(seed)

    # Scale bucket sample rates to hit target overall percentage
    total = len(rich) + len(medium) + len(metadata_only)
    if total == 0:
        return []

    # Stratified sampling with higher rates for richer problems
    base = sample_pct / 100.0
    rich_rate = min(1.0, base * 1.3)
    medium_rate = base
    meta_rate = max(0.15, base * 0.65)

    sampled: set[EvalPair] = set()
    for bucket, rate in [(rich, rich_rate), (medium, medium_rate), (metadata_only, meta_rate)]:
        k = max(1, round(len(bucket) * rate)) if bucket else 0
        k = min(k, len(bucket))
        sampled.update(rng.sample(bucket, k))

    result = sorted(sampled, key=lambda p: p.senseis_n)
    logger.info(
        "Eval sample: %d/%d (%.1f%%) — rich=%d/%d, medium=%d/%d, meta=%d/%d",
        len(result), total, len(result) / total * 100,
        len([x for x in result if x in rich]), len(rich),
        len([x for x in result if x in medium]), len(medium),
        len([x for x in result if x in metadata_only]), len(metadata_only),
    )
    return result


# --- Per-problem evaluation ---


def evaluate_problem(
    pair: EvalPair,
    config: SenseisConfig,
    page_cache_dir: Path,
    solution_cache_dir: Path,
) -> ProblemEval:
    """Evaluate a single enriched problem against cache truth.

    Uses pair.local_n for file paths and pair.senseis_n for cache lookups.
    """
    local_n = pair.local_n
    senseis_n = pair.senseis_n
    result = ProblemEval(problem_number=local_n)

    original_path = config.local_sgf_path(local_n)
    enriched_path = config.enriched_sgf_path(local_n)

    # Load source data using Senseis number
    page_data = _load_page_cache(page_cache_dir, senseis_n)
    sol_data = _load_solution_cache(solution_cache_dir, senseis_n)

    # Load files
    if not enriched_path.exists():
        result.checks.append(CheckResult("file_exists", "fail", "Enriched file not found"))
        return result

    original_content = ""
    if original_path.exists():
        original_content, _ = read_sgf_file(original_path)

    enriched_content, _ = read_sgf_file(enriched_path)

    # --- Check 1: File modified ---
    if len(enriched_content) > len(original_content):
        result.checks.append(CheckResult("file_modified", "pass"))
    elif sol_data and sol_data.get("status") == "ok" and sol_data.get("diagrams"):
        # Has solution data but file didn't grow — something's wrong
        result.checks.append(CheckResult(
            "file_modified", "fail",
            f"original={len(original_content)}, enriched={len(enriched_content)} (has solution data)",
        ))
    else:
        # No solution data — file may not grow (metadata-only or already enriched)
        result.checks.append(CheckResult(
            "file_modified", "skip",
            f"No solution data, sizes: original={len(original_content)}, enriched={len(enriched_content)}",
        ))

    # Parse enriched SGF
    try:
        tree = parse_sgf(enriched_content)
    except Exception as e:
        result.checks.append(CheckResult("parse", "fail", f"Parse error: {e}"))
        return result

    # --- Check 2: Metadata (YG difficulty) ---
    if page_data and page_data.get("difficulty"):
        if tree.yengo_props and tree.yengo_props.level_slug:
            result.checks.append(CheckResult("metadata_yg", "pass"))
        else:
            result.checks.append(CheckResult(
                "metadata_yg", "fail",
                f"Cache has difficulty='{page_data['difficulty']}' but YG[] missing",
            ))
    else:
        result.checks.append(CheckResult("metadata_yg", "skip", "No difficulty in cache"))

    # --- Check 3: Root comment enriched ---
    if page_data and page_data.get("instruction"):
        instruction = page_data["instruction"].lower()
        if instruction in tree.root_comment.lower():
            result.checks.append(CheckResult("root_comment", "pass"))
        else:
            result.checks.append(CheckResult(
                "root_comment", "fail",
                f"Expected '{page_data['instruction']}' in root comment",
            ))
    else:
        result.checks.append(CheckResult("root_comment", "skip", "No instruction in cache"))

    # --- Checks 4-6: Solution commentary ---
    if not sol_data or sol_data.get("status") != "ok":
        result.checks.append(CheckResult("commentary_exists", "skip", "No solution data"))
        result.checks.append(CheckResult("commentary_text", "skip", "No solution data"))
        result.checks.append(CheckResult("move_nodes_added", "skip", "No solution data"))
        return result

    diagrams_with_commentary = [
        d for d in sol_data.get("diagrams", [])
        if d.get("commentary", "").strip()
    ]
    diagrams_with_moves = [
        d for d in sol_data.get("diagrams", [])
        if d.get("sgf_content", "").strip()
    ]

    if not diagrams_with_commentary and not diagrams_with_moves:
        result.checks.append(CheckResult("commentary_exists", "skip", "No commentary in diagrams"))
        result.checks.append(CheckResult("commentary_text", "skip", "No commentary in diagrams"))
        result.checks.append(CheckResult("move_nodes_added", "skip", "No diagrams with data"))
        return result

    # Collect all comments from enriched tree
    # Root comment is in tree.root_comment (separate from solution_tree)
    all_comments = _collect_all_comments(tree.solution_tree)
    non_root_comments = [c for d, c in all_comments if d > 0]
    # Include root comment in the full text for fingerprint matching
    all_comment_text = tree.root_comment + " " + " ".join(c for _, c in all_comments)

    # --- Check 4: Commentary exists on move nodes ---
    # Commentary may be on move nodes (when diagram has moves) or root (when no moves)
    if diagrams_with_commentary:
        has_enriched_commentary = bool(non_root_comments)
        if not has_enriched_commentary:
            # Check if root comment gained diagram commentary (for no-moves diagrams)
            for diag in diagrams_with_commentary:
                name = diag.get("diagram_name", "")
                if name and name in tree.root_comment:
                    has_enriched_commentary = True
                    break

        if has_enriched_commentary:
            result.checks.append(CheckResult("commentary_exists", "pass"))
        else:
            result.checks.append(CheckResult(
                "commentary_exists", "fail",
                f"{len(diagrams_with_commentary)} diagrams have commentary but no enriched comments found",
            ))
    else:
        result.checks.append(CheckResult("commentary_exists", "skip", "No commentary in diagrams"))

    # --- Check 5: Commentary text fingerprint matching ---
    if diagrams_with_commentary:
        matched = 0
        failure_details: list[str] = []
        for diag in diagrams_with_commentary:
            fp = _fingerprint(diag["commentary"])
            if not fp:
                matched += 1  # Empty fingerprint = trivial match
                continue
            if fp in all_comment_text.lower():
                matched += 1
            else:
                # Try individual words as fallback (commentary may be heavily transformed)
                fp_words = fp.split()
                word_hits = sum(1 for w in fp_words if w in all_comment_text.lower())
                if word_hits >= len(fp_words) * 0.6:
                    matched += 1
                else:
                    name = diag.get("diagram_name", "?")
                    failure_details.append(f"'{name}': fingerprint '{fp[:40]}' not found")

        coverage = matched / len(diagrams_with_commentary) * 100 if diagrams_with_commentary else 100
        result.diagram_coverage_pct = coverage

        if matched == len(diagrams_with_commentary):
            result.checks.append(CheckResult("commentary_text", "pass"))
        else:
            detail = f"{matched}/{len(diagrams_with_commentary)} matched"
            if failure_details:
                detail += "; " + "; ".join(failure_details[:3])
            result.checks.append(CheckResult("commentary_text", "fail", detail))
    else:
        result.checks.append(CheckResult("commentary_text", "skip", "No commentary"))

    # --- Check 6: Move nodes added (for position-only originals) ---
    # Only check if diagrams actually contain move sequences (not just stone setup)
    diagrams_with_actual_moves = [
        d for d in sol_data.get("diagrams", [])
        if _diagram_has_moves(d.get("sgf_content", ""))
    ]

    if diagrams_with_actual_moves:
        try:
            orig_tree = parse_sgf(original_content) if original_content else None
        except Exception:
            orig_tree = None

        orig_moves = _count_move_nodes(orig_tree.solution_tree) if orig_tree else 0
        enriched_moves = _count_move_nodes(tree.solution_tree)

        if orig_moves == 0:
            if enriched_moves > 0:
                result.checks.append(CheckResult(
                    "move_nodes_added", "pass",
                    f"0 -> {enriched_moves} move nodes",
                ))
            else:
                result.checks.append(CheckResult(
                    "move_nodes_added", "fail",
                    "Original has 0 moves, cache has diagrams, but enriched still has 0",
                ))
        else:
            result.checks.append(CheckResult(
                "move_nodes_added", "skip",
                f"Original already has {orig_moves} moves",
            ))
    else:
        result.checks.append(CheckResult("move_nodes_added", "skip", "No diagram moves"))

    return result


# --- Main eval runner ---


def run_eval(
    config: SenseisConfig | None = None,
    sample_pct: float = 40.0,
    start: int | None = None,
    end: int | None = None,
) -> EvalReport:
    """Run post-enrichment evaluation.

    Samples problems, validates each against cache truth, produces report.
    Automatically detects position-mapped collections and adjusts numbering.
    """
    if config is None:
        config = load_config()

    working = config.working_dir()
    page_cache_dir = working / "_page_cache"
    solution_cache_dir = working / "_solution_cache"

    if not solution_cache_dir.exists():
        logger.error("Solution cache not found: %s", solution_cache_dir)
        return EvalReport(
            collection=config.collection_slug,
            total_problems=config.problem_count,
            sample_size=0,
            sample_pct=0,
        )

    # Load position mapping if available
    mapping = _load_eval_mapping(config)
    if mapping:
        total_evaluable = len(mapping)
        logger.info("Position mapping loaded: %d mapped problems", total_evaluable)
    else:
        total_evaluable = config.problem_count

    # Select sample
    if start is not None or end is not None:
        # Explicit range — filter by senseis_n range
        s = start or 1
        e = end or config.problem_count
        if mapping:
            sample = [p for p in mapping if s <= p.senseis_n <= e]
        else:
            sample = [EvalPair(n, n) for n in range(s, e + 1)]
    else:
        sample = select_eval_sample(config, solution_cache_dir, sample_pct, mapping=mapping)

    report = EvalReport(
        collection=config.collection_slug,
        total_problems=total_evaluable,
        sample_size=len(sample),
        sample_pct=len(sample) / total_evaluable * 100 if total_evaluable else 0,
    )

    logger.info("Evaluating %d problems for %s", len(sample), config.collection_slug)

    for pair in sample:
        result = evaluate_problem(pair, config, page_cache_dir, solution_cache_dir)
        report.results.append(result)

        status = "PASS" if result.required_passed else "FAIL"
        failures = [c for c in result.checks if c.status == "fail"]
        if failures:
            details = ", ".join(f"{c.name}: {c.detail[:50]}" for c in failures)
            label = f"L{pair.local_n:03d}/S{pair.senseis_n:03d}" if pair.local_n != pair.senseis_n else f"P{pair.local_n:03d}"
            logger.info("  %s: %s — %s", label, status, details)
        else:
            label = f"L{pair.local_n:03d}/S{pair.senseis_n:03d}" if pair.local_n != pair.senseis_n else f"P{pair.local_n:03d}"
            logger.debug("  %s: %s", label, status)

    # Write report
    _write_report(report, config)
    _print_summary(report)

    return report


def _write_report(report: EvalReport, config: SenseisConfig) -> None:
    """Write JSON evaluation report."""
    out_dir = config.working_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate check stats
    check_stats: dict[str, dict[str, int]] = {}
    for r in report.results:
        for c in r.checks:
            if c.name not in check_stats:
                check_stats[c.name] = {"pass": 0, "fail": 0, "skip": 0}
            check_stats[c.name][c.status] += 1

    # Diagram coverage stats
    coverages = [r.diagram_coverage_pct for r in report.results if r.diagram_coverage_pct >= 0]

    report_data = {
        "collection": report.collection,
        "total_problems": report.total_problems,
        "sample_size": report.sample_size,
        "sample_pct": round(report.sample_pct, 1),
        "overall_pass": report.overall_pass,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "checks": check_stats,
        "diagram_coverage": {
            "mean_pct": round(sum(coverages) / len(coverages), 1) if coverages else 0,
            "min_pct": round(min(coverages), 1) if coverages else 0,
            "count": len(coverages),
        },
        "failures": [
            {
                "problem": r.problem_number,
                "failed_checks": [
                    {"name": c.name, "detail": c.detail}
                    for c in r.checks if c.status == "fail"
                ],
            }
            for r in report.results
            if not r.required_passed
        ],
    }

    path = out_dir / "_eval_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    logger.info("Eval report: %s", path)


def _print_summary(report: EvalReport) -> None:
    """Print human-readable eval summary."""
    print()
    print("=" * 60)
    print(f"ENRICHMENT EVAL: {report.collection}")
    print("=" * 60)
    print(f"Sample: {report.sample_size}/{report.total_problems} ({report.sample_pct:.1f}%)")
    print(f"Result: {'PASS' if report.overall_pass else 'FAIL'}")
    print(f"  Passed: {report.pass_count}/{report.sample_size}")
    print(f"  Failed: {report.fail_count}/{report.sample_size}")

    # Per-check breakdown
    check_stats: dict[str, dict[str, int]] = {}
    for r in report.results:
        for c in r.checks:
            if c.name not in check_stats:
                check_stats[c.name] = {"pass": 0, "fail": 0, "skip": 0}
            check_stats[c.name][c.status] += 1

    print("\nCheck breakdown:")
    for name in ["file_modified", "metadata_yg", "root_comment",
                  "commentary_exists", "commentary_text", "move_nodes_added"]:
        stats = check_stats.get(name, {"pass": 0, "fail": 0, "skip": 0})
        print(f"  {name:25s}  pass={stats['pass']:3d}  fail={stats['fail']:3d}  skip={stats['skip']:3d}")

    # Diagram coverage
    coverages = [r.diagram_coverage_pct for r in report.results if r.diagram_coverage_pct >= 0]
    if coverages:
        print(f"\nDiagram coverage: mean={sum(coverages)/len(coverages):.1f}%, "
              f"min={min(coverages):.1f}%, n={len(coverages)}")

    # List failures
    failures = [r for r in report.results if not r.required_passed]
    if failures:
        print(f"\nFAILED PROBLEMS ({len(failures)}):")
        for r in failures[:20]:
            failed_checks = [c for c in r.checks if c.status == "fail"]
            for c in failed_checks:
                print(f"  P{r.problem_number:03d}: [{c.name}] {c.detail[:70]}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")

    print("=" * 60)
