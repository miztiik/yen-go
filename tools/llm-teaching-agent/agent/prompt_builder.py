"""Prompt builder — constructs LLM prompts from teaching_signals payload.

Reads the teaching_signals v2 payload from an enrichment JSON file and
builds structured prompts for the LLM to generate teaching comments and hints.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_template(name: str) -> str:
    """Load a prompt template by name from prompts/ directory."""
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt(persona_text: str) -> str:
    """Build the full system prompt from persona + base system prompt.

    Args:
        persona_text: The persona-specific prompt text.

    Returns:
        Combined system prompt.
    """
    base = load_template("system_prompt")
    return f"{persona_text}\n\n---\n\n{base}"


def build_user_prompt(enrichment_data: dict) -> str:
    """Build the user prompt from an enrichment JSON result.

    Extracts teaching_signals, technique_tags, difficulty, and goal
    from the AiAnalysisResult and formats them for the LLM.

    Args:
        enrichment_data: The full AiAnalysisResult dict (from JSON file).

    Returns:
        Formatted user prompt string.
    """
    teaching_signals = enrichment_data.get("teaching_signals", {})
    if not teaching_signals:
        raise ValueError("No teaching_signals found in enrichment data")

    template = load_template("teaching_comment")

    # Build the data section
    context = teaching_signals.get("context", {})
    correct_move = teaching_signals.get("correct_move", {})
    position = teaching_signals.get("position", {})
    wrong_moves = teaching_signals.get("wrong_moves", [])

    data_section = json.dumps(
        {
            "teaching_signals": teaching_signals,
            "puzzle_id": enrichment_data.get("puzzle_id", ""),
            "validation_status": enrichment_data.get("validation", {}).get("status", ""),
        },
        indent=2,
    )

    # Summary for the LLM
    technique_tags = context.get("technique_tags", [])
    difficulty = context.get("difficulty_level", "unknown")
    goal = context.get("goal", "unknown")
    board_size = position.get("board_size", 19)
    correct_gtp = correct_move.get("move_gtp", "?")
    correct_sgf = correct_move.get("move_sgf", "?")
    num_wrong = len(wrong_moves)

    summary = (
        f"Puzzle: {difficulty}-level {goal} problem on {board_size}x{board_size} board.\n"
        f"Techniques: {', '.join(technique_tags) if technique_tags else 'unclassified'}.\n"
        f"Correct move: {correct_gtp} (SGF: {correct_sgf}).\n"
        f"Wrong moves to explain: {num_wrong}.\n"
    )

    return f"{template}\n\n## Puzzle Summary\n\n{summary}\n\n## Raw Data\n\n```json\n{data_section}\n```"
