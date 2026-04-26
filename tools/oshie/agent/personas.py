"""Teacher persona loader.

Each persona is a markdown file in prompts/personas/. The persona prompt
is prepended to the system prompt to give the LLM a consistent teaching
voice. Personas can be added by dropping a new .md file — no code changes.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PERSONAS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "personas"


def list_personas() -> list[str]:
    """Return available persona names (filename stems)."""
    if not _PERSONAS_DIR.exists():
        return []
    return sorted(p.stem for p in _PERSONAS_DIR.glob("*.md"))


def load_persona(name: str) -> str:
    """Load a persona prompt by name.

    Args:
        name: Persona name (e.g. 'cho_chikun'). Maps to prompts/personas/{name}.md.

    Returns:
        The persona prompt text.

    Raises:
        FileNotFoundError: If the persona file does not exist.
    """
    path = _PERSONAS_DIR / f"{name}.md"
    if not path.exists():
        available = list_personas()
        raise FileNotFoundError(
            f"Persona '{name}' not found at {path}. "
            f"Available: {available}"
        )
    text = path.read_text(encoding="utf-8").strip()
    logger.info("Loaded persona '%s' (%d chars)", name, len(text))
    return text
