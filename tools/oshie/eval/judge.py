"""Layer C -- LLM-as-judge for qualitative assessment.

Uses the same llama.cpp endpoint (or a separate model) to score
teaching quality from a 9-dan professional Go teacher perspective.

Scores each of the 5 dimensions on a 0-5 scale and provides
concrete improvement suggestions.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from .llm_caller import LLMResponse, call_llm

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = (
    "You are a 9-dan professional Go teacher and pedagogy expert. "
    "You evaluate teaching comments generated for tsumego (Go puzzles). "
    "Score each dimension on a 0-5 scale where:\n"
    "  0 = completely wrong or missing\n"
    "  1 = present but mostly incorrect\n"
    "  2 = partially correct but shallow\n"
    "  3 = acceptable, meets minimum bar\n"
    "  4 = good, clear and helpful\n"
    "  5 = excellent, professional quality\n\n"
    "Respond with a JSON object:\n"
    '{"scores": {"go_correctness": N, "pedagogical_quality": N, '
    '"voice_compliance": N, "hint_progression": N, "completeness": N}, '
    '"reasoning": "...", "suggestions": ["...", "..."]}\n\n'
    "Scoring criteria:\n"
    "- go_correctness: Is the Go analysis accurate? Correct move identified? "
    "Wrong move consequences realistic?\n"
    "- pedagogical_quality: Does the teaching explain WHY, not just WHAT? "
    "Are board consequences concrete? Move sequences provided?\n"
    "- voice_compliance: Verb-forward style? Action--consequence pattern? "
    "No 'you should' phrases? Wrong comments under 15 words?\n"
    "- hint_progression: Tier 1 technique-only? Tier 2 reasoning without answer? "
    "Tier 3 has coordinate token?\n"
    "- completeness: All fields present? All wrong moves covered? "
    "Summary meaningful?\n\n"
    "Be specific in suggestions -- name the exact field and what to change."
)


@dataclass
class JudgeVerdict:
    """Result from the LLM judge."""
    dimension_scores: dict[str, float] = field(default_factory=dict)  # 0-5
    reasoning: str = ""
    suggestions: list[str] = field(default_factory=list)
    weighted_score: float = 0.0   # 0.0-1.0 (normalized from 0-5)
    elapsed_s: float = 0.0
    think_tokens: int = 0
    error: str = ""


def _build_judge_prompt(puzzle_info: dict, model_output: str) -> str:
    """Build the user prompt for the judge."""
    lines = [
        "Evaluate this teaching comment for the following Go puzzle:",
        "",
        f"Puzzle: {puzzle_info.get('name', 'unknown')}",
        f"Technique: {puzzle_info.get('technique', 'unknown')}",
        f"Difficulty: {puzzle_info.get('difficulty', 'unknown')}",
        f"Board: {puzzle_info.get('board_size', 19)}x{puzzle_info.get('board_size', 19)}",
        f"Correct move: {puzzle_info.get('correct_move_gtp', '?')} (SGF: {puzzle_info.get('correct_move_sgf', '?')})",
    ]

    wrong_moves = puzzle_info.get("wrong_moves", [])
    for i, wm in enumerate(wrong_moves):
        lines.append(f"Wrong move {i+1}: {wm.get('gtp', '?')} -- {wm.get('reason', '')}")

    lines.extend([
        "",
        "--- MODEL OUTPUT ---",
        model_output[:1500],
        "--- END ---",
        "",
        "Score each dimension 0-5 and provide specific improvement suggestions.",
    ])
    return "\n".join(lines)


def judge_response(
    puzzle_info: dict,
    model_output: str,
    endpoint: str = "http://127.0.0.1:8080",
    model: str = "gemma-4-26B-A4B-it-Q8_0.gguf",
    max_tokens: int = 8192,
) -> JudgeVerdict:
    """Run the LLM judge on a single model output.

    Args:
        puzzle_info: Dict with keys: name, technique, difficulty, board_size,
            correct_move_sgf, correct_move_gtp, wrong_moves.
        model_output: The raw LLM output to judge.
        endpoint: LLM server URL.
        model: Model name.
        max_tokens: Token budget for judge.

    Returns:
        JudgeVerdict with per-dimension scores and suggestions.
    """
    user_prompt = _build_judge_prompt(puzzle_info, model_output)

    resp: LLMResponse = call_llm(
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        endpoint=endpoint,
        model=model,
        max_tokens=max_tokens,
        temperature=0.3,  # lower temp for more consistent judging
    )

    if resp.finish_reason == "error":
        return JudgeVerdict(error=resp.error, elapsed_s=resp.elapsed_s)

    # Parse judge response
    try:
        obj = json.loads(resp.content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        m = re.search(r"\{.*\}", resp.content, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                return JudgeVerdict(
                    error=f"Judge output not valid JSON: {resp.content[:200]}",
                    elapsed_s=resp.elapsed_s,
                    think_tokens=resp.think_tokens,
                )
        else:
            return JudgeVerdict(
                error=f"No JSON in judge output: {resp.content[:200]}",
                elapsed_s=resp.elapsed_s,
                think_tokens=resp.think_tokens,
            )

    scores = obj.get("scores", {})
    # Normalize to 0-5 scale
    dim_scores = {}
    for dim in ["go_correctness", "pedagogical_quality", "voice_compliance",
                "hint_progression", "completeness"]:
        val = scores.get(dim, 0)
        dim_scores[dim] = float(val) if isinstance(val, (int, float)) else 0.0

    # Compute weighted score (normalized to 0-1)
    from .scorers import WEIGHTS
    weighted = sum(
        (dim_scores.get(dim, 0) / 5.0) * w
        for dim, w in WEIGHTS.items()
    )

    return JudgeVerdict(
        dimension_scores=dim_scores,
        reasoning=obj.get("reasoning", ""),
        suggestions=obj.get("suggestions", []),
        weighted_score=weighted,
        elapsed_s=resp.elapsed_s,
        think_tokens=resp.think_tokens,
    )


def to_dict(verdict: JudgeVerdict) -> dict:
    """Serialize a JudgeVerdict to JSON-compatible dict."""
    return asdict(verdict)
