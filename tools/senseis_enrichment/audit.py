"""Audit mode: build a decision ledger before any SGF writes.

Classifies every problem's mapping quality, position match, and solution
availability without modifying any files. Outputs a JSON ledger and
summary statistics.

Usage:
    python -m tools.senseis_enrichment --audit
    python -m tools.senseis_enrichment --audit --start 1 --end 50
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.core.sgf_parser import parse_sgf, read_sgf_file

from tools.senseis_enrichment.config import (
    SenseisConfig,
    load_config,
)
from tools.senseis_enrichment.fetcher import SenseisFetcher
from tools.senseis_enrichment.position_matcher import (
    canonical_position_hash,
    match_positions,
)

logger = logging.getLogger("senseis_enrichment.audit")

STANDARD_PREFIX = "XuanxuanQijingProblem"


# --- Match classifications ---

class MatchClass:
    EXACT = "exact_match"            # D4 hash match, identity transform
    ROTATED = "rotated_match"        # D4 hash match, non-identity rotation/reflection
    TRANSLATED = "translated_mismatch"  # D4 hash fails, positions at different board region
    NO_DIAGRAM = "no_diagram"        # No problem diagram SGF on Senseis page
    MISSING_LOCAL = "missing_local"  # Local file doesn't exist
    PARSE_ERROR = "parse_error"      # SGF parse failure


# --- Index classifications ---

class IndexClass:
    STANDARD = "standard"            # XuanxuanQijingProblemN where N matches
    ALIAS = "alias"                  # Non-standard page name (RTGProblem, Hikaru, etc.)
    NUMBER_MISMATCH = "number_mismatch"  # XuanxuanQijingProblemM where M != N
    COLLISION = "collision"          # Same page name used by another problem number
    MISSING = "missing"              # Not in index at all


@dataclass
class AuditEntry:
    """One row of the decision ledger."""

    problem_number: int
    local_file_exists: bool = False
    local_stone_count: int = 0
    local_player: str = ""

    # Index mapping
    index_page_name: str = ""
    index_class: str = ""
    index_flag: str = ""  # Human-readable note for anomalies

    # Problem page
    page_status: str = ""  # "ok", "404", "error", "skipped"
    title_english: str = ""
    title_chinese: str = ""
    difficulty: str = ""
    instruction: str = ""
    has_diagram_sgf: bool = False

    # Solution page
    solution_status: str = ""  # "ok", "404", "empty", "error", "skipped"
    diagram_count: int = 0
    total_commentary_chars: int = 0

    # Position matching
    match_class: str = ""
    match_transform: str = ""  # e.g. "rot=90,ref=True" or ""
    local_hash: str = ""
    senseis_hash: str = ""

    # Decision
    decision: str = ""  # "enrich", "enrich_number_fallback", "skip", "review"
    decision_reason: str = ""


@dataclass
class AuditReport:
    """Full audit output."""

    entries: list[AuditEntry] = field(default_factory=list)
    index_anomalies: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _classify_index_entry(
    n: int, index: dict[int, str], all_page_names: dict[str, list[int]]
) -> tuple[str, str, str]:
    """Classify a problem's index mapping.

    Returns: (page_name, index_class, flag_note)
    """
    if n not in index:
        return "", IndexClass.MISSING, "Not found in Senseis index"

    page_name = index[n]

    # Check for collision (same page_name used by multiple numbers)
    users = all_page_names.get(page_name, [])
    if len(users) > 1:
        others = [x for x in users if x != n]
        return page_name, IndexClass.COLLISION, f"Shares page with P{others}"

    # Check for non-standard page name
    if not page_name.startswith(STANDARD_PREFIX):
        return page_name, IndexClass.ALIAS, f"Alias: {page_name}"

    # Standard page name — check number matches
    suffix = page_name[len(STANDARD_PREFIX):]
    try:
        page_n = int(suffix)
        if page_n != n:
            return page_name, IndexClass.NUMBER_MISMATCH, f"Page says Problem {page_n}, mapped from N={n}"
    except ValueError:
        return page_name, IndexClass.ALIAS, f"Non-numeric suffix: {suffix}"

    return page_name, IndexClass.STANDARD, ""


def _classify_match(
    config: SenseisConfig,
    n: int,
    has_diagram_sgf: bool,
    diagram_sgf_url: str,
) -> tuple[str, str, str, str]:
    """Classify position match quality.

    Returns: (match_class, transform_str, local_hash, senseis_hash)
    """
    local_path = config.local_sgf_path(n)
    if not local_path.exists():
        return MatchClass.MISSING_LOCAL, "", "", ""

    try:
        local_content, _ = read_sgf_file(local_path)
        local_tree = parse_sgf(local_content)
    except Exception:
        return MatchClass.PARSE_ERROR, "", "", ""

    local_hash, _ = canonical_position_hash(
        local_tree.black_stones, local_tree.white_stones, local_tree.board_size
    )

    if not has_diagram_sgf or not diagram_sgf_url:
        return MatchClass.NO_DIAGRAM, "", local_hash, ""

    # Read cached diagram SGF
    filename = diagram_sgf_url.replace("/", "_")
    cache_file = config.diagram_cache_dir() / filename
    if not cache_file.exists():
        return MatchClass.NO_DIAGRAM, "", local_hash, ""

    sgf_content = cache_file.read_text(encoding="utf-8")
    result = match_positions(local_tree, sgf_content, n)

    if result.matched and result.transform:
        if result.transform.rotation == 0 and not result.transform.reflect:
            return MatchClass.EXACT, "identity", local_hash, result.senseis_hash
        else:
            t = result.transform
            return (
                MatchClass.ROTATED,
                f"rot={t.rotation},ref={t.reflect}",
                local_hash,
                result.senseis_hash,
            )
    else:
        return MatchClass.TRANSLATED, "", local_hash, result.senseis_hash


def _decide(entry: AuditEntry) -> tuple[str, str]:
    """Assign a decision based on all collected data."""
    if not entry.local_file_exists:
        return "skip", "No local file"

    if entry.index_class == IndexClass.MISSING:
        return "skip", "Not in Senseis index"

    if entry.index_class == IndexClass.COLLISION:
        return "review", f"Page collision: {entry.index_flag}"

    if entry.index_class == IndexClass.NUMBER_MISMATCH:
        return "review", f"Number mismatch: {entry.index_flag}"

    if entry.page_status != "ok":
        return "skip", f"Problem page: {entry.page_status}"

    if entry.match_class in (MatchClass.EXACT, MatchClass.ROTATED):
        if entry.solution_status == "ok" and entry.diagram_count > 0:
            return "enrich", f"D4 match ({entry.match_transform}), {entry.diagram_count} diagrams"
        else:
            return "enrich", f"D4 match ({entry.match_transform}), metadata only (no solution)"

    if entry.match_class == MatchClass.TRANSLATED:
        if entry.solution_status == "ok" and entry.diagram_count > 0:
            return "enrich_number_fallback", f"Translated position, {entry.diagram_count} diagrams"
        else:
            return "enrich_number_fallback", "Translated position, metadata only"

    if entry.match_class == MatchClass.NO_DIAGRAM:
        return "enrich_number_fallback", "No diagram SGF for matching, number-based only"

    return "review", f"Unhandled: match={entry.match_class}, page={entry.page_status}"


def run_audit(
    config: SenseisConfig | None = None,
    start: int = 1,
    end: int | None = None,
) -> AuditReport:
    """Run the full audit and produce a decision ledger.

    This fetches all pages (populating the cache) but writes NO SGF files.
    """
    if config is None:
        config = load_config()
    end = end or config.problem_count

    report = AuditReport()

    with SenseisFetcher(config) as fetcher:
        index = fetcher.fetch_index()
        if not index:
            logger.error("Failed to fetch index. Aborting audit.")
            return report

        # Build reverse map for collision detection
        from collections import defaultdict
        page_to_numbers: dict[str, list[int]] = defaultdict(list)
        for n, page in index.items():
            page_to_numbers[page].append(n)

        # Log index anomalies upfront
        for page, nums in page_to_numbers.items():
            if len(nums) > 1:
                anomaly = {"type": "collision", "page_name": page, "problem_numbers": nums}
                report.index_anomalies.append(anomaly)
                logger.warning("INDEX COLLISION: %s <- P%s", page, nums)

        for n_str, page in sorted(index.items(), key=lambda x: int(x[0])):
            n_int = int(n_str)
            if not page.startswith(STANDARD_PREFIX):
                report.index_anomalies.append({"type": "alias", "problem": n_int, "page_name": page})
            elif page.startswith(STANDARD_PREFIX):
                suffix = page[len(STANDARD_PREFIX):]
                try:
                    if int(suffix) != n_int:
                        report.index_anomalies.append({
                            "type": "number_mismatch",
                            "problem": n_int,
                            "page_name": page,
                            "page_number": int(suffix),
                        })
                except ValueError:
                    pass

        logger.info("Index: %d entries, %d anomalies", len(index), len(report.index_anomalies))
        logger.info("Auditing problems %d-%d", start, end)

        for n in range(start, end + 1):
            entry = AuditEntry(problem_number=n)

            # Local file
            local_path = config.local_sgf_path(n)
            entry.local_file_exists = local_path.exists()
            if entry.local_file_exists:
                try:
                    content, _ = read_sgf_file(local_path)
                    tree = parse_sgf(content)
                    entry.local_stone_count = len(tree.black_stones) + len(tree.white_stones)
                    entry.local_player = tree.player_to_move or ""
                except Exception:
                    pass

            # Index mapping
            entry.index_page_name, entry.index_class, entry.index_flag = (
                _classify_index_entry(n, index, page_to_numbers)
            )

            # Fetch problem page (uses cache)
            page_data = fetcher.fetch_problem_page(n, index)
            if page_data:
                entry.page_status = "ok"
                entry.title_english = page_data.title_english
                entry.title_chinese = page_data.title_chinese
                entry.difficulty = page_data.difficulty
                entry.instruction = page_data.instruction
                entry.has_diagram_sgf = bool(page_data.diagram_sgf_url)
            else:
                entry.page_status = "404"

            # Fetch solution page (uses cache)
            solution = fetcher.fetch_solution_page(n, index)
            if solution:
                entry.solution_status = solution.status
                entry.diagram_count = len(solution.diagrams)
                entry.total_commentary_chars = sum(
                    len(d.commentary) for d in solution.diagrams
                )
            else:
                entry.solution_status = "error"

            # Position matching (uses cached diagram SGFs)
            diagram_url = page_data.diagram_sgf_url if page_data else ""
            entry.match_class, entry.match_transform, entry.local_hash, entry.senseis_hash = (
                _classify_match(config, n, entry.has_diagram_sgf, diagram_url)
            )

            # Decision
            entry.decision, entry.decision_reason = _decide(entry)

            # Log progress
            flag = f" [{entry.index_flag}]" if entry.index_flag else ""
            logger.info(
                "  P%03d: %s | sol=%s(%d) | %s | -> %s%s",
                n,
                entry.match_class,
                entry.solution_status,
                entry.diagram_count,
                entry.decision,
                entry.decision_reason[:60],
                flag,
            )

            report.entries.append(entry)

    # Compute summary
    report.summary = _compute_summary(report)

    # Write outputs
    _write_report(report, config)

    return report


def _compute_summary(report: AuditReport) -> dict:
    """Compute aggregate statistics from entries."""
    total = len(report.entries)
    if total == 0:
        return {}

    by_match = {}
    by_decision = {}
    by_solution = {}
    by_index = {}

    for e in report.entries:
        by_match[e.match_class] = by_match.get(e.match_class, 0) + 1
        by_decision[e.decision] = by_decision.get(e.decision, 0) + 1
        by_solution[e.solution_status] = by_solution.get(e.solution_status, 0) + 1
        by_index[e.index_class] = by_index.get(e.index_class, 0) + 1

    has_title = sum(1 for e in report.entries if e.title_english)
    has_chinese = sum(1 for e in report.entries if e.title_chinese)
    has_difficulty = sum(1 for e in report.entries if e.difficulty)
    has_instruction = sum(1 for e in report.entries if e.instruction)
    has_commentary = sum(1 for e in report.entries if e.total_commentary_chars > 0)

    return {
        "total": total,
        "by_match_class": by_match,
        "by_decision": by_decision,
        "by_solution_status": by_solution,
        "by_index_class": by_index,
        "index_anomalies": len(report.index_anomalies),
        "metadata_coverage": {
            "title_english": has_title,
            "title_chinese": has_chinese,
            "difficulty": has_difficulty,
            "instruction": has_instruction,
            "has_commentary": has_commentary,
        },
    }


def _write_report(report: AuditReport, config: SenseisConfig) -> None:
    """Write the audit report to _working/{slug}/."""
    out_dir = config.working_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Full ledger (JSON)
    ledger_path = out_dir / "_audit_ledger.json"
    ledger_data = {
        "summary": report.summary,
        "index_anomalies": report.index_anomalies,
        "entries": [asdict(e) for e in report.entries],
    }
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger_data, f, indent=2, ensure_ascii=False)
    logger.info("Ledger written: %s", ledger_path)

    # Human-readable summary
    s = report.summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total problems: {s.get('total', 0)}")

    print("\nIndex classification:")
    for cls, count in sorted(s.get("by_index_class", {}).items()):
        print(f"  {cls:25s} {count:4d}")

    print("\nPosition match classification:")
    for cls, count in sorted(s.get("by_match_class", {}).items()):
        print(f"  {cls:25s} {count:4d}")

    print("\nSolution page status:")
    for cls, count in sorted(s.get("by_solution_status", {}).items()):
        print(f"  {cls:25s} {count:4d}")

    print("\nDecision breakdown:")
    for cls, count in sorted(s.get("by_decision", {}).items()):
        print(f"  {cls:30s} {count:4d}")

    cov = s.get("metadata_coverage", {})
    print("\nMetadata coverage:")
    for field_name, count in sorted(cov.items()):
        pct = count / s["total"] * 100 if s["total"] else 0
        print(f"  {field_name:25s} {count:4d} ({pct:.0f}%)")

    # List problems needing review
    review = [e for e in report.entries if e.decision == "review"]
    if review:
        print(f"\nPROBLEMS NEEDING REVIEW ({len(review)}):")
        for e in review:
            print(f"  P{e.problem_number:03d}: {e.decision_reason}")

    print(f"\nFull ledger: {out_dir / '_audit_ledger.json'}")
    print("=" * 60)
