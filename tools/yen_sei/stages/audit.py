"""Pre-train data audit (IMPROVEMENT_PLAN.md §1.3 [P2-1]).

Reads a refined SFT JSONL file (typically ``data/refined/train.jsonl``)
and reports the data-quality signals that, if alarming, mean we should
NOT submit the run for fine-tuning.

Headline checks:

1. **CN→EN broken-English markers** — % rows whose assistant target
   contains 1+ MT-artefact tokens (`(completed)`, `obtain more more`,
   `won't work`, etc.). Threshold: >10% is a hard fail.
2. **Coordinate / ordinal-move leaks** — % rows whose target still
   contains coordinate references after normalization. The system
   prompt forbids these; any presence is a contradiction.
3. **Templated target dominance** — top-20 most duplicated assistant
   targets (by exact lowered text). One cluster >15% means we are
   training a template-copier.
4. **Length distribution** of `correct_comment` (parsed back via
   `parse_tagged_text`).
5. **Prompt↔target token overlap** — for every row, % of bigrams from
   user prompt that also appear in assistant target. High overlap is
   the prompt-leak signature from LESSONS.md §0 #2.

By default the audit only *reports*. With ``--strict`` it exits non-zero
when any of the hard-fail thresholds are breached, suitable for use as
a pre-training gate.

See also:
- [IMPROVEMENT_PLAN.md §1.3 [P2-1]](../IMPROVEMENT_PLAN.md)
- `tools/yen_sei/governance/text_normalizer.py` — the patterns audited.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.teaching_schema import parse_tagged_text
from tools.yen_sei.governance.text_normalizer import (
    broken_english_score,
    has_coordinate_leak,
)
from tools.yen_sei.telemetry.logger import setup_logger

logger = setup_logger(__name__)


# ── Thresholds (hard fails when --strict) ──────────────────────────────
THRESHOLD_BROKEN_EN_PCT = 10.0   # >10% rows with MT artefacts → fail
THRESHOLD_COORD_LEAK_PCT = 5.0   # >5% rows with surviving coords → fail
THRESHOLD_TEMPLATE_PCT = 15.0    # any cluster covering >15% of corpus → fail
THRESHOLD_PROMPT_LEAK_PCT = 30.0 # >30% bigram overlap on average → fail


@dataclass
class AuditReport:
    """Aggregated audit signals for one refined JSONL file."""

    total_rows: int = 0
    rows_with_broken_en: int = 0
    rows_with_coord_leak: int = 0
    rows_unparseable: int = 0
    correct_lengths: list[int] = field(default_factory=list)
    target_clusters: Counter[str] = field(default_factory=Counter)
    prompt_target_overlap_pct: list[float] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def add_failure(self, msg: str) -> None:
        self.failures.append(msg)

    @property
    def broken_en_pct(self) -> float:
        return _pct(self.rows_with_broken_en, self.total_rows)

    @property
    def coord_leak_pct(self) -> float:
        return _pct(self.rows_with_coord_leak, self.total_rows)

    @property
    def avg_prompt_target_overlap_pct(self) -> float:
        if not self.prompt_target_overlap_pct:
            return 0.0
        return sum(self.prompt_target_overlap_pct) / len(self.prompt_target_overlap_pct)

    @property
    def top_cluster_pct(self) -> float:
        if not self.target_clusters:
            return 0.0
        _, top_count = self.target_clusters.most_common(1)[0]
        return _pct(top_count, self.total_rows)


def _pct(n: int, total: int) -> float:
    return (100.0 * n / total) if total else 0.0


def _bigrams(text: str) -> set[tuple[str, str]]:
    tokens = text.lower().split()
    return {(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)}


def _bigram_overlap_pct(prompt: str, target: str) -> float:
    """% of prompt bigrams that also appear in target."""
    p_bigrams = _bigrams(prompt)
    if not p_bigrams:
        return 0.0
    t_bigrams = _bigrams(target)
    return 100.0 * len(p_bigrams & t_bigrams) / len(p_bigrams)


def audit_jsonl(path: Path) -> AuditReport:
    """Walk every row of an SFT JSONL and aggregate signals.

    Args:
        path: Path to a JSONL file in ChatML format
            (``{"messages": [{"role": ..., "content": ...}, ...]}``).

    Returns:
        Populated AuditReport. Caller decides whether to enforce
        thresholds.
    """
    report = AuditReport()

    if not path.exists():
        report.add_failure(f"File not found: {path}")
        return report

    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                messages = row.get("messages", [])
                user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
                asst_msg = next((m["content"] for m in messages if m["role"] == "assistant"), "")
            except (json.JSONDecodeError, KeyError, StopIteration):
                report.rows_unparseable += 1
                continue

            report.total_rows += 1

            if broken_english_score(asst_msg) >= 1:
                report.rows_with_broken_en += 1

            if has_coordinate_leak(asst_msg):
                report.rows_with_coord_leak += 1

            try:
                correct, _, _ = parse_tagged_text(asst_msg)
                report.correct_lengths.append(len(correct.strip()))
                report.target_clusters[correct.strip().lower()] += 1
            except ValueError:
                report.rows_unparseable += 1

            report.prompt_target_overlap_pct.append(
                _bigram_overlap_pct(user_msg, asst_msg)
            )

    return report


def format_report(report: AuditReport, *, top_clusters: int = 20) -> str:
    """Human-readable text report."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("YEN-SEI PRE-TRAIN DATA AUDIT")
    lines.append("=" * 60)
    lines.append(f"Total rows examined:        {report.total_rows}")
    lines.append(f"Unparseable rows:           {report.rows_unparseable}")
    lines.append("")
    lines.append("HEADLINE METRICS")
    lines.append(f"  Broken-English markers:   {report.rows_with_broken_en:>5} "
                 f"({report.broken_en_pct:5.1f}%)  threshold {THRESHOLD_BROKEN_EN_PCT}%")
    lines.append(f"  Coordinate leaks:         {report.rows_with_coord_leak:>5} "
                 f"({report.coord_leak_pct:5.1f}%)  threshold {THRESHOLD_COORD_LEAK_PCT}%")
    lines.append(f"  Top-cluster share:        {report.top_cluster_pct:5.1f}%        "
                 f"  threshold {THRESHOLD_TEMPLATE_PCT}%")
    lines.append(f"  Avg prompt<->target overlap: {report.avg_prompt_target_overlap_pct:5.1f}%       "
                 f"  threshold {THRESHOLD_PROMPT_LEAK_PCT}%")
    lines.append("")

    if report.correct_lengths:
        lengths = sorted(report.correct_lengths)
        n = len(lengths)
        lines.append("CORRECT_COMMENT LENGTH DISTRIBUTION (chars)")
        lines.append(f"  min:    {lengths[0]:>5}")
        lines.append(f"  p25:    {lengths[n // 4]:>5}")
        lines.append(f"  median: {lengths[n // 2]:>5}")
        lines.append(f"  p75:    {lengths[(3 * n) // 4]:>5}")
        lines.append(f"  max:    {lengths[-1]:>5}")
        lines.append(f"  mean:   {sum(lengths) / n:5.1f}")
        lines.append("")

    if report.target_clusters:
        lines.append(f"TOP {top_clusters} MOST-DUPLICATED ASSISTANT TARGETS")
        lines.append("(if any single cluster dominates, the model will memorize the template)")
        for text, count in report.target_clusters.most_common(top_clusters):
            preview = text[:80].replace("\n", " ")
            lines.append(f"  {count:>4}x  {preview}")
        lines.append("")

    if report.failures:
        lines.append("FAILURES")
        for f in report.failures:
            lines.append(f"  - {f}")
        lines.append("")

    return "\n".join(lines)


def evaluate_thresholds(report: AuditReport) -> list[str]:
    """Return list of threshold-breach messages (empty if all pass)."""
    breaches: list[str] = []
    if report.broken_en_pct > THRESHOLD_BROKEN_EN_PCT:
        breaches.append(
            f"broken_en_pct={report.broken_en_pct:.1f}% > "
            f"{THRESHOLD_BROKEN_EN_PCT}% (clean the CN→EN garbage)"
        )
    if report.coord_leak_pct > THRESHOLD_COORD_LEAK_PCT:
        breaches.append(
            f"coord_leak_pct={report.coord_leak_pct:.1f}% > "
            f"{THRESHOLD_COORD_LEAK_PCT}% (normalizer is letting coords through)"
        )
    if report.top_cluster_pct > THRESHOLD_TEMPLATE_PCT:
        breaches.append(
            f"top_cluster_pct={report.top_cluster_pct:.1f}% > "
            f"{THRESHOLD_TEMPLATE_PCT}% (one templated target dominates)"
        )
    if report.avg_prompt_target_overlap_pct > THRESHOLD_PROMPT_LEAK_PCT:
        breaches.append(
            f"avg_prompt_target_overlap={report.avg_prompt_target_overlap_pct:.1f}% > "
            f"{THRESHOLD_PROMPT_LEAK_PCT}% (prompt may be leaking the answer)"
        )
    return breaches


def run_audit(input_path: str | None = None, *, strict: bool = False) -> int:
    """CLI entry-point.

    Args:
        input_path: Path to refined JSONL. Defaults to ``data/refined/train.jsonl``.
        strict: If True, return non-zero exit code on threshold breaches.

    Returns:
        Exit code (0 = OK, 1 = threshold breach when strict).
    """
    from tools.yen_sei.config import TRAIN_JSONL

    path = Path(input_path) if input_path else TRAIN_JSONL
    logger.info("Auditing %s", path)
    report = audit_jsonl(path)
    print(format_report(report))

    breaches = evaluate_thresholds(report)
    if breaches:
        print("THRESHOLD BREACHES")
        for b in breaches:
            print(f"  - {b}")
        if strict:
            print("\nSTRICT MODE: refusing to proceed.")
            return 1
        print("\n(Run with --strict to fail the build on these.)")
    else:
        print("All thresholds OK.")

    return 0
