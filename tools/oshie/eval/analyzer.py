"""Prompt improvement analyzer -- the "prompt engineer" sub-agent.

Analyzes failures across an eval run and generates concrete prompt
edit suggestions. Groups by weakest dimension, identifies patterns,
and proposes specific changes to the system prompt.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from .llm_caller import LLMResponse, call_llm
from .scorers import WEIGHTS, EvalResult

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM_PROMPT = (
    "You are an expert prompt engineer specializing in LLM instruction tuning "
    "for structured JSON output. You analyze evaluation results from a Go (Baduk) "
    "teaching comment generator and suggest concrete system prompt improvements.\n\n"
    "Your suggestions must be:\n"
    "1. Specific -- name the exact rule number or section to change\n"
    "2. Actionable -- provide the actual text to add/modify/remove\n"
    "3. Prioritized -- high/medium/low based on impact on scores\n"
    "4. Justified -- explain which failures the change addresses\n\n"
    "Respond with a JSON object:\n"
    '{"suggestions": [{"target": "system_prompt|user_template", '
    '"change_type": "add_rule|add_example|rephrase|remove", '
    '"description": "...", "priority": "high|medium|low", '
    '"proposed_text": "..."}], '
    '"analysis_summary": "..."}\n\n'
    "Focus on the weakest dimensions first. "
    "Do not suggest changes that would break the JSON output format."
)


@dataclass
class PromptSuggestion:
    """A concrete suggestion for improving the prompt."""
    target: str          # "system_prompt" | "user_template"
    change_type: str     # "add_rule" | "add_example" | "rephrase" | "remove"
    description: str
    priority: str        # "high" | "medium" | "low"
    proposed_text: str = ""


@dataclass
class AnalysisReport:
    """Report from the prompt analyzer."""
    suggestions: list[PromptSuggestion] = field(default_factory=list)
    analysis_summary: str = ""
    weakest_dimensions: list[str] = field(default_factory=list)
    pattern_groups: dict[str, list[str]] = field(default_factory=dict)
    elapsed_s: float = 0.0
    error: str = ""


def _summarize_results(results: list[EvalResult]) -> str:
    """Build a concise summary of eval results for the analyzer."""
    lines = [
        f"Eval run: {len(results)} puzzles",
        "",
        "=== DIMENSION AVERAGES ===",
    ]

    # Compute per-dimension averages
    dim_totals: dict[str, list[float]] = {}
    for r in results:
        for d in r.dimensions:
            if d.name not in dim_totals:
                dim_totals[d.name] = []
            dim_totals[d.name].append(d.score)

    dim_avgs: dict[str, float] = {}
    for name, scores in sorted(dim_totals.items()):
        avg = sum(scores) / len(scores) if scores else 0
        dim_avgs[name] = avg
        lines.append(f"  {name}: {avg:.2f} (weight: {WEIGHTS.get(name, 0):.2f})")

    # Weighted total
    weighted_avg = sum(r.weighted_total for r in results) / len(results) if results else 0
    lines.append(f"\n  WEIGHTED TOTAL: {weighted_avg:.3f}")

    # Identify weakest dimensions
    sorted_dims = sorted(dim_avgs.items(), key=lambda x: x[1])
    weakest = [name for name, _ in sorted_dims[:2]]
    lines.append(f"\n  WEAKEST: {', '.join(weakest)}")

    # Per-puzzle breakdown (failures only)
    lines.append("\n=== FAILURES (weighted < 0.5) ===")
    failures = [r for r in results if r.weighted_total < 0.5]
    for r in failures[:10]:
        lines.append(f"\n  {r.puzzle_name} ({r.technique}, {r.difficulty}): {r.weighted_total:.3f}")
        for d in r.dimensions:
            if d.score < 0.5:
                lines.append(f"    {d.name}: {d.score:.2f} -- {d.details}")

    # Pattern grouping: which dimensions fail most often by technique
    lines.append("\n=== FAILURE PATTERNS BY TECHNIQUE ===")
    tech_failures: dict[str, dict[str, int]] = {}
    for r in results:
        for d in r.dimensions:
            if d.score < 0.5:
                key = r.technique
                if key not in tech_failures:
                    tech_failures[key] = {}
                tech_failures[key][d.name] = tech_failures[key].get(d.name, 0) + 1

    for tech, dims in sorted(tech_failures.items()):
        dim_strs = [f"{name}:{count}" for name, count in sorted(dims.items(), key=lambda x: -x[1])]
        lines.append(f"  {tech}: {', '.join(dim_strs)}")

    return "\n".join(lines)


def analyze_run(
    results: list[EvalResult],
    current_prompt: str,
    endpoint: str = "http://127.0.0.1:8080",
    model: str = "gemma-4-26B-A4B-it-Q8_0.gguf",
    max_tokens: int = 8192,
) -> AnalysisReport:
    """Analyze eval results and suggest prompt improvements.

    Args:
        results: List of EvalResult from the eval run.
        current_prompt: The system prompt text that was used.
        endpoint: LLM server URL for the analyzer agent.
        model: Model name.
        max_tokens: Token budget.

    Returns:
        AnalysisReport with prioritized suggestions.
    """
    if not results:
        return AnalysisReport(error="No results to analyze")

    summary = _summarize_results(results)

    user_prompt = (
        "Analyze these Go teaching comment evaluation results and suggest "
        "improvements to the system prompt.\n\n"
        "=== CURRENT SYSTEM PROMPT ===\n"
        f"{current_prompt}\n"
        "=== END SYSTEM PROMPT ===\n\n"
        f"{summary}\n\n"
        "Suggest 3-5 specific changes to improve the weakest dimensions. "
        "Provide the actual text to add or modify."
    )

    resp: LLMResponse = call_llm(
        system_prompt=ANALYZER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        endpoint=endpoint,
        model=model,
        max_tokens=max_tokens,
        temperature=0.4,
    )

    if resp.finish_reason == "error":
        return AnalysisReport(error=resp.error, elapsed_s=resp.elapsed_s)

    # Parse response
    import re
    try:
        obj = json.loads(resp.content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", resp.content, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                return AnalysisReport(
                    error=f"Analyzer output not valid JSON: {resp.content[:200]}",
                    elapsed_s=resp.elapsed_s,
                )
        else:
            return AnalysisReport(
                error=f"No JSON in analyzer output: {resp.content[:200]}",
                elapsed_s=resp.elapsed_s,
            )

    suggestions = []
    for s in obj.get("suggestions", []):
        suggestions.append(PromptSuggestion(
            target=s.get("target", "system_prompt"),
            change_type=s.get("change_type", "rephrase"),
            description=s.get("description", ""),
            priority=s.get("priority", "medium"),
            proposed_text=s.get("proposed_text", ""),
        ))

    # Compute weakest dimensions from results
    dim_avgs: dict[str, float] = {}
    for r in results:
        for d in r.dimensions:
            if d.name not in dim_avgs:
                dim_avgs[d.name] = 0.0
            dim_avgs[d.name] += d.score
    for name in dim_avgs:
        dim_avgs[name] /= len(results)
    weakest = sorted(dim_avgs, key=lambda x: dim_avgs[x])[:2]

    return AnalysisReport(
        suggestions=suggestions,
        analysis_summary=obj.get("analysis_summary", ""),
        weakest_dimensions=weakest,
        elapsed_s=resp.elapsed_s,
    )


def to_dict(report: AnalysisReport) -> dict:
    """Serialize an AnalysisReport to JSON-compatible dict."""
    return asdict(report)
