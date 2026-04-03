"""Puzzle Intent - Extract puzzle objectives from noisy SGF comment text.

Tiered matching strategy:
- Tier 1: Deterministic exact substring/token matching (fast, no dependencies)
- Tier 1.5: Keyword co-occurrence matching (regex, no dependencies)
- Tier 2: Sentence-transformer semantic similarity (fuzzy, requires sentence-transformers)

Usage:
    from tools.puzzle_intent import resolve_intent, IntentResult

    result = resolve_intent("Black to play and live")
    print(result.objective_id)       # "LIFE_AND_DEATH.BLACK.LIVE"
    print(result.objective.slug)     # "black-to-live"
    print(result.objective.name)     # "Black to Live"
    print(result.confidence)         # 1.0
    print(result.match_tier)         # MatchTier.EXACT

    # Deterministic-only mode (no ML dependency)
    result = resolve_intent(text, enable_semantic=False)

    # Batch processing
    from tools.puzzle_intent import resolve_intents_batch
    results = resolve_intents_batch(["black to live", "white to kill"])

Architecture:
    - Self-contained in tools/ (no backend imports)
    - Config source of truth: config/puzzle-objectives.json
    - Schema: config/schemas/puzzle-objectives.schema.json
    - Logging: extends tools.core.logging.StructuredLogger
"""

__version__ = "2.2.0"

from .config_loader import load_objectives
from .intent_resolver import IntentResolver, resolve_intent, resolve_intents_batch
from .keyword_matcher import KeywordMatcher
from .models import IntentResult, MatchTier, Objective, ObjectiveCategory
from .text_cleaner import clean_comment_text

__all__ = [
    "resolve_intent",
    "resolve_intents_batch",
    "IntentResolver",
    "KeywordMatcher",
    "IntentResult",
    "Objective",
    "MatchTier",
    "ObjectiveCategory",
    "clean_comment_text",
    "load_objectives",
]
