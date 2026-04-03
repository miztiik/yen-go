"""Comment assembly engine — composes Layer 1 + Layer 2 into final comments.

Handles:
- Composition of technique_phrase (Layer 1) and signal_phrase (Layer 2)
- 15-word cap enforcement
- Overflow strategy: signal replaces mechanism suffix (GOV-C4)
- V1 fallback: no signal → emit V1 comment verbatim
- Vital move assembly
- Wrong-move assembly with token substitution
- Parenthetical counting: (term) = 1 word (RC-4)
"""

from __future__ import annotations

import logging
import re

from config.teaching import (
    TeachingCommentsConfig,
    load_raw_teaching_config,
    load_teaching_comments_config,
)

logger = logging.getLogger(__name__)


def _count_words(text: str) -> int:
    """Count words with parenthetical-as-one-word rule (RC-4).

    Parenthetical Japanese terms count as 1 word:
    - "(uttegaeshi)" → 1 word
    - "Snapback (uttegaeshi)" → 2 words
    """
    # Replace parenthetical terms with a single token
    collapsed = re.sub(r"\([^)]+\)", "PAREN", text)
    return len(collapsed.split())


def _substitute_tokens(
    template: str,
    coord: str = "",
    alias: str = "",
) -> str:
    """Replace {!xy} and {alias} tokens in template text."""
    result = template
    if coord:
        result = result.replace("{!xy}", "{!" + coord + "}")
    if alias:
        result = result.replace("{alias}", alias)
    return result


def assemble_correct_comment(
    technique_phrase: str,
    signal_phrase: str,
    v1_comment: str,
    config: TeachingCommentsConfig | None = None,
    instinct_phrase: str = "",
) -> str:
    """Assemble a correct-move comment from technique and signal layers.

    Args:
        technique_phrase: Layer 1 technique name (e.g. "Snapback (uttegaeshi)").
        signal_phrase: Layer 2 signal text (e.g. "vital point {!cg}").
        v1_comment: V1 fallback comment to use when no signal is available.
        config: Optional config override; loaded from file if None.
        instinct_phrase: Optional Layer 0 instinct phrase (T17: 3-layer).

    Returns:
        Assembled comment string.
    """
    if config is None:
        config = load_teaching_comments_config()

    # T17: 3-layer composition — prepend instinct phrase
    if instinct_phrase:
        technique_phrase = f"{instinct_phrase}: {technique_phrase}"

    # V1 fallback: no signal or empty technique
    if not signal_phrase or not technique_phrase:
        return v1_comment

    rules = config.assembly_rules
    composed = rules.composition.replace(
        "{technique_phrase}", technique_phrase
    ).replace(
        "{signal_phrase}", signal_phrase
    )

    word_count = _count_words(composed)

    if word_count <= rules.max_words:
        return composed

    # Overflow: signal replaces mechanism suffix (GOV-C4)
    # Use just: "{technique_phrase} — {signal_phrase}." but shorter
    # Strip mechanism from technique_phrase (text after " — ")
    short = f"{technique_phrase} — {signal_phrase}."
    if _count_words(short) <= rules.max_words:
        return short

    # Final fallback: signal only
    signal_only = f"{signal_phrase.rstrip('.')}."
    if _count_words(signal_only) <= rules.max_words:
        return signal_only

    # Last resort: V1 fallback
    return v1_comment


def assemble_vital_comment(
    vital_move_comment: str,
    signal_phrase: str,
    config: TeachingCommentsConfig | None = None,
) -> str:
    """Assemble a vital-move comment.

    Args:
        vital_move_comment: The vital move template from config.
        signal_phrase: Optional signal phrase to compose with.
        config: Optional config override.

    Returns:
        Assembled vital move comment, or empty string if no content.
    """
    if not vital_move_comment:
        return ""

    if not signal_phrase:
        return vital_move_comment

    if config is None:
        config = load_teaching_comments_config()

    composed = f"{vital_move_comment.rstrip('.')} — {signal_phrase}."
    if _count_words(composed) <= config.assembly_rules.max_words:
        return composed

    # Overflow: use vital_move_comment alone
    return vital_move_comment


def _assemble_opponent_response(
    condition: str,
    opponent_move: str,
    opponent_color: str,
    wrong_move_comment: str,
    opponent_templates: dict | None = None,
) -> str:
    """Assemble opponent-response phrase for wrong-move comments (PI-10).

    Args:
        condition: Classified wrong-move condition.
        opponent_move: SGF coordinate of opponent's refutation move.
        opponent_color: "Black" or "White".
        wrong_move_comment: The assembled wrong-move comment (for dash rule).
        opponent_templates: Optional override; loaded from JSON if None.

    Returns:
        Opponent-response phrase, or empty string if condition not enabled.
    """
    if not opponent_move:
        return ""

    if opponent_templates is None:
        raw = load_raw_teaching_config()
        opponent_templates = raw.get("opponent_response_templates", {})

    enabled = opponent_templates.get("enabled_conditions", [])
    if condition not in enabled:
        return ""

    templates = opponent_templates.get("templates", [])
    template_map = {t["condition"]: t["template"] for t in templates}

    template = template_map.get(condition, template_map.get("default", ""))
    if not template:
        return ""

    # Substitute tokens
    result = template.replace("{opponent_color}", opponent_color)
    result = result.replace("{!opponent_move}", "{!" + opponent_move + "}")

    # Conditional dash rule: if wrong_move_comment has em-dash, omit dash from response
    if "\u2014" in wrong_move_comment:
        result = result.replace(" \u2014 ", " ")

    return result


def assemble_wrong_comment(
    condition: str,
    coord: str = "",
    alias: str = "",
    delta: float = 0.0,
    config: TeachingCommentsConfig | None = None,
    opponent_move: str = "",
    opponent_color: str = "",
    use_opponent_policy: bool = False,
) -> str:
    """Assemble a wrong-move comment from classified condition.

    Args:
        condition: The classified condition (e.g. "immediate_capture").
        coord: SGF coordinate for {!xy} substitution.
        alias: Alias name for {alias} substitution.
        delta: Winrate delta for delta annotations.
        config: Optional config override.
        opponent_move: SGF coordinate of opponent's PV[0] response.
        opponent_color: "Black" or "White".
        use_opponent_policy: PI-10 feature gate.

    Returns:
        Assembled wrong-move comment.
    """
    if config is None:
        config = load_teaching_comments_config()

    wm = config.wrong_move_comments
    templates = {t.condition: t.comment for t in wm.templates}

    template = templates.get(condition, templates.get("default", "Wrong."))
    comment = _substitute_tokens(template, coord=coord, alias=alias)

    # Delta annotations — skip for almost_correct (no raw engine data in user-facing text)
    if condition != "almost_correct":
        abs_delta = abs(delta)
        da = wm.delta_annotations
        if abs_delta > da["significant_loss"].threshold:
            annotation = da["significant_loss"].template.replace(
                "{delta_pct}", f"{abs_delta * 100:.0f}"
            )
            comment = f"{comment} {annotation}"
        elif abs_delta > da["moderate_loss"].threshold:
            comment = f"{comment} {da['moderate_loss'].template}"

    # PI-10: Append opponent-response phrase
    if use_opponent_policy and opponent_move:
        opp_phrase = _assemble_opponent_response(
            condition=condition,
            opponent_move=opponent_move,
            opponent_color=opponent_color,
            wrong_move_comment=comment,
        )
        if opp_phrase:
            combined = f"{comment} {opp_phrase}"
            if _count_words(combined) <= config.assembly_rules.max_words:
                comment = combined

    return comment
