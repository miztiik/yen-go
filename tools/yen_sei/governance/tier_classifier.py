"""Apply CurationConfig tier rules to TeachingSignals → assign tier."""

from __future__ import annotations

from .config_loader import CurationConfig, TierRule
from .teaching_signal import TeachingSignals


def _passes_structural(s: TeachingSignals, rule: TierRule) -> bool:
    """Structural path: counts wrong-move teaching from SGF tree branches."""
    return (
        s.correct_explanation_chars >= rule.min_correct_explanation_chars
        and s.wrong_explanation_chars >= rule.min_wrong_explanation_chars
        and s.explanation_node_count >= rule.min_explanation_node_count
        and s.causal_phrase_count >= rule.min_causal_phrases
        and s.english_word_ratio >= rule.min_english_word_ratio
        and s.technique_mentions >= rule.min_technique_mentions
    )


def _passes_prose(s: TeachingSignals, rule: TierRule) -> bool:
    """Prose path: wrong-move teaching counted from in-prose refutation phrases.

    Symmetric to the prose_fallback hard gate (Lesson #13). Recognises classic-book
    style where wrong-move analysis lives inside one big C[] comment instead of in
    tree branches. None means the tier has no prose escape (e.g. bronze).
    """
    pp = rule.prose_path
    if pp is None:
        return False
    return (
        s.correct_explanation_chars >= pp.min_correct_explanation_chars
        and s.refutation_phrase_count >= pp.min_refutation_phrase_count
        and s.causal_phrase_count >= pp.min_causal_phrases
        and s.technique_mentions >= pp.min_technique_mentions
        and s.english_word_ratio >= pp.min_english_word_ratio
    )


def _passes_tier(s: TeachingSignals, rule: TierRule) -> bool:
    """A tier passes if EITHER the structural OR prose path is satisfied."""
    return _passes_structural(s, rule) or _passes_prose(s, rule)


def classify(signals: TeachingSignals, cfg: CurationConfig) -> str:
    """Return 'gold' | 'silver' | 'bronze' | 'drop'.

    Rules:
    1. Hard-gate failures → drop.
    2. Walk tier_rules in order (gold → silver → bronze); first match wins.
    3. Apply per-source tier_cap (e.g. gotools is capped at 'drop').
    """
    if signals.gate_failures:
        return "drop"
    if not signals.is_english:
        return "drop"

    tier = "drop"
    for rule in cfg.tier_rules:
        if _passes_tier(signals, rule):
            tier = rule.name
            break

    # Apply per-source cap
    return cfg.cap_tier(tier, signals.source)
