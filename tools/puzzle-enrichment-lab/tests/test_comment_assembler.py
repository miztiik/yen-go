"""Tests for analyzers.comment_assembler — assembly engine unit tests.

Covers:
- Correct comment composition (Layer 1 + Layer 2)
- 15-word cap enforcement
- Overflow strategy (signal replaces mechanism)
- V1 fallback (no signal, no technique)
- Exact 15 words (boundary)
- Parenthetical term counting (RC-4)
- Vital move comment assembly
- Wrong-move comment assembly
- Token substitution ({!xy}, {alias})
- Delta annotations on wrong-move comments
"""

from __future__ import annotations

import pytest
from analyzers.comment_assembler import (
    _count_words,
    _substitute_tokens,
    assemble_correct_comment,
    assemble_vital_comment,
    assemble_wrong_comment,
)
from config.teaching import (
    AssemblyRules,
    DeltaAnnotation,
    TeachingCommentEntry,
    TeachingCommentsConfig,
    WrongMoveComments,
    WrongMoveTemplate,
)

# --- Fixture: minimal config ---

def _make_config(
    max_words: int = 15,
    composition: str = "{technique_phrase} \u2014 {signal_phrase}.",
) -> TeachingCommentsConfig:
    """Build a minimal TeachingCommentsConfig for testing."""
    return TeachingCommentsConfig(
        version="2.0",
        correct_move_comments={
            "snapback": TeachingCommentEntry(
                comment="Snapback (uttegaeshi) \u2014 allow the capture, then recapture the larger group.",
                technique_phrase="Snapback (uttegaeshi)",
                vital_move_comment="Now recapture \u2014 the snapback completes.",
                hint_text="Snapback (uttegaeshi)",
                min_confidence="HIGH",
            ),
        },
        wrong_move_comments=WrongMoveComments(
            templates=[
                WrongMoveTemplate(condition="immediate_capture", comment="This stone is captured immediately."),
                WrongMoveTemplate(condition="opponent_escapes", comment="Opponent escapes at {!xy}."),
                WrongMoveTemplate(condition="shape_death_alias", comment="This creates a {alias} \u2014 unconditionally dead."),
                WrongMoveTemplate(condition="almost_correct", comment="Close, but not the best move."),
                WrongMoveTemplate(condition="default", comment="Wrong. The opponent has a strong response."),
            ],
            delta_annotations={
                "significant_loss": DeltaAnnotation(threshold=0.5, template="Loses approximately {delta_pct}% of the position."),
                "moderate_loss": DeltaAnnotation(threshold=0.2, template="Results in a significant disadvantage."),
            },
        ),
        assembly_rules=AssemblyRules(
            composition=composition,
            max_words=max_words,
        ),
    )


# --- _count_words tests ---

class TestCountWords:
    def test_simple_words(self):
        assert _count_words("one two three") == 3

    def test_parenthetical_counts_as_one(self):
        """RC-4: (uttegaeshi) = 1 word."""
        assert _count_words("Snapback (uttegaeshi)") == 2

    def test_multiple_parentheticals(self):
        # "Ko PAREN fight PAREN" = 4 words
        assert _count_words("Ko (k\u014d) fight (ik\u014d)") == 4

    def test_empty_string(self):
        assert _count_words("") == 0

    def test_single_parenthetical_only(self):
        assert _count_words("(uttegaeshi)") == 1

    def test_em_dash_is_a_word(self):
        """Em dash \u2014 is glued to adjacent words if no space."""
        # "Snapback \u2014 vital" = 3 tokens
        assert _count_words("Snapback \u2014 vital") == 3


# --- _substitute_tokens tests ---

class TestSubstituteTokens:
    def test_coord_substitution(self):
        result = _substitute_tokens("vital point {!xy}", coord="cg")
        assert result == "vital point {!cg}"

    def test_alias_substitution(self):
        result = _substitute_tokens("This creates a {alias}.", alias="bent-four")
        assert result == "This creates a bent-four."

    def test_both_tokens(self):
        result = _substitute_tokens("{alias} at {!xy}", coord="dd", alias="crane's nest")
        assert result == "crane's nest at {!dd}"

    def test_no_tokens(self):
        result = _substitute_tokens("Simple text.", coord="ab", alias="x")
        assert result == "Simple text."

    def test_empty_coord_preserves_token(self):
        result = _substitute_tokens("vital point {!xy}")
        assert result == "vital point {!xy}"


# --- assemble_correct_comment tests ---

class TestAssembleCorrectComment:
    def test_basic_composition(self):
        """Layer 1 + Layer 2 within 15-word cap."""
        cfg = _make_config(max_words=15)
        result = assemble_correct_comment(
            technique_phrase="Snapback (uttegaeshi)",
            signal_phrase="vital point {!cg}",
            v1_comment="V1 fallback",
            config=cfg,
        )
        # "Snapback (uttegaeshi) \u2014 vital point {!cg}."
        assert "Snapback" in result
        assert "vital point" in result
        assert result.endswith(".")

    def test_v1_fallback_no_signal(self):
        """No signal → V1 fallback."""
        cfg = _make_config()
        result = assemble_correct_comment(
            technique_phrase="Snapback (uttegaeshi)",
            signal_phrase="",
            v1_comment="V1 fallback comment.",
            config=cfg,
        )
        assert result == "V1 fallback comment."

    def test_v1_fallback_no_technique(self):
        """No technique → V1 fallback."""
        cfg = _make_config()
        result = assemble_correct_comment(
            technique_phrase="",
            signal_phrase="vital point {!cg}",
            v1_comment="V1 fallback comment.",
            config=cfg,
        )
        assert result == "V1 fallback comment."

    def test_v1_fallback_both_empty(self):
        cfg = _make_config()
        result = assemble_correct_comment(
            technique_phrase="",
            signal_phrase="",
            v1_comment="V1 fallback.",
            config=cfg,
        )
        assert result == "V1 fallback."

    def test_exact_15_words(self):
        """Boundary: exactly 15 words should pass."""
        cfg = _make_config(max_words=15)
        # technique_phrase = "Snapback (uttegaeshi)" → 2 words (RC-4)
        # signal = "one two three four five six seven eight nine ten eleven" → 11 words
        # "{technique_phrase} \u2014 {signal_phrase}." → 2 + 1(\u2014) + 11 + punct = 14 words
        # Let's craft exactly 15
        signal = "one two three four five six seven eight nine ten eleven twelve"
        result = assemble_correct_comment(
            technique_phrase="Snapback (uttegaeshi)",
            signal_phrase=signal,
            v1_comment="V1",
            config=cfg,
        )
        # "Snapback (uttegaeshi) \u2014 one two three four five six seven eight nine ten eleven twelve."
        # Count: 2 + 1 + 12 = 15
        assert _count_words(result) == 15

    def test_overflow_triggers_shorter_form(self):
        """Over 15 words triggers overflow strategy."""
        cfg = _make_config(max_words=5)
        result = assemble_correct_comment(
            technique_phrase="Snapback (uttegaeshi)",
            signal_phrase="vital point at coordinate cg on the board somewhere far away",
            v1_comment="V1 simple.",
            config=cfg,
        )
        # Should degrade gracefully — eventually V1 fallback if nothing fits
        assert _count_words(result) <= 5 or result == "V1 simple."

    def test_parenthetical_not_double_counted(self):
        """RC-4: parenthetical Japanese term counts as 1 word in cap check."""
        cfg = _make_config(max_words=6)
        # "Life & Death (shikatsu) \u2014 vital point."
        # Without RC-4: 6 tokens. With RC-4: "Life & Death PAREN \u2014 vital point." = 6 words
        result = assemble_correct_comment(
            technique_phrase="Life & Death (shikatsu)",
            signal_phrase="vital point",
            v1_comment="V1",
            config=cfg,
        )
        # "Life & Death (shikatsu) \u2014 vital point." → 6 words with RC-4
        assert _count_words(result) <= 6


# --- assemble_vital_comment tests ---

class TestAssembleVitalComment:
    def test_vital_without_signal(self):
        result = assemble_vital_comment(
            vital_move_comment="Now recapture \u2014 the snapback completes.",
            signal_phrase="",
        )
        assert result == "Now recapture \u2014 the snapback completes."

    def test_vital_with_signal(self):
        cfg = _make_config(max_words=15)
        result = assemble_vital_comment(
            vital_move_comment="The vital point \u2014 this decides the group's fate",
            signal_phrase="decisive at {!cg}",
            config=cfg,
        )
        assert "decisive at" in result

    def test_vital_overflow_returns_base(self):
        cfg = _make_config(max_words=3)
        result = assemble_vital_comment(
            vital_move_comment="Short vital comment",
            signal_phrase="long signal that exceeds the word limit significantly",
            config=cfg,
        )
        assert result == "Short vital comment"

    def test_empty_vital_returns_empty(self):
        result = assemble_vital_comment("", "signal")
        assert result == ""


# --- assemble_wrong_comment tests ---

class TestAssembleWrongComment:
    def test_immediate_capture(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="immediate_capture",
            config=cfg,
        )
        assert result == "This stone is captured immediately."

    def test_opponent_escapes_with_coord(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="opponent_escapes",
            coord="cg",
            config=cfg,
        )
        assert result == "Opponent escapes at {!cg}."

    def test_shape_death_alias(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="shape_death_alias",
            alias="bent-four",
            config=cfg,
        )
        assert "bent-four" in result
        assert "unconditionally dead" in result

    def test_default_condition(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="default",
            config=cfg,
        )
        assert result == "Wrong. The opponent has a strong response."

    def test_unknown_condition_falls_to_default(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="nonexistent_condition",
            config=cfg,
        )
        assert result == "Wrong. The opponent has a strong response."

    def test_delta_significant_loss(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="default",
            delta=0.6,
            config=cfg,
        )
        assert "Loses approximately 60%" in result

    def test_delta_moderate_loss(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="default",
            delta=0.3,
            config=cfg,
        )
        assert "significant disadvantage" in result

    def test_delta_below_threshold_no_annotation(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="default",
            delta=0.1,
            config=cfg,
        )
        assert "Loses" not in result
        assert "disadvantage" not in result
        assert result == "Wrong. The opponent has a strong response."

    def test_negative_delta_uses_absolute(self):
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="default",
            delta=-0.7,
            config=cfg,
        )
        assert "Loses approximately 70%" in result

    def test_almost_correct_template(self):
        """T13a/F23: assemble_wrong_comment(condition='almost_correct') produces 'Close' text."""
        cfg = _make_config()
        result = assemble_wrong_comment(
            condition="almost_correct",
            coord="",
            config=cfg,
        )
        assert "Close" in result
        assert "not the best move" in result
        # No coordinate should appear — defense-in-depth against spoilers
        assert "{!" not in result


# --- PI-10: Opponent-response assembly tests ---

class TestOpponentResponseAssembly:
    """PI-10: Verify opponent-response phrase is appended/suppressed correctly."""

    # The 5 enabled conditions per config/teaching-comments.json
    ACTIVE_CONDITIONS = [
        "immediate_capture",
        "capturing_race_lost",
        "self_atari",
        "wrong_direction",
        "default",
    ]

    # The 7 suppressed conditions (not in enabled_conditions list)
    SUPPRESSED_CONDITIONS = [
        "opponent_escapes",
        "opponent_lives",
        "opponent_takes_vital",
        "opponent_reduces_liberties",
        "shape_death_alias",
        "ko_involved",
        "almost_correct",
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize("condition", [
        "immediate_capture",
        "capturing_race_lost",
        "self_atari",
        "wrong_direction",
        "default",
    ])
    def test_active_conditions_produce_opponent_response(self, condition: str) -> None:
        """For each active condition, opponent move coordinate appears in result."""
        cfg = _make_config(max_words=30)  # generous limit to avoid truncation
        result = assemble_wrong_comment(
            condition=condition,
            opponent_move="de",
            opponent_color="White",
            use_opponent_policy=True,
            config=cfg,
        )
        # The opponent-response template substitutes {!opponent_move} → {!de}
        assert "{!de}" in result or "de" in result.lower()

    @pytest.mark.unit
    @pytest.mark.parametrize("condition", [
        "opponent_escapes",
        "opponent_lives",
        "opponent_takes_vital",
        "opponent_reduces_liberties",
        "shape_death_alias",
        "ko_involved",
        "almost_correct",
    ])
    def test_suppressed_conditions_no_opponent_response(self, condition: str) -> None:
        """For suppressed conditions, opponent-response is NOT appended."""
        cfg = _make_config(max_words=30)
        result = assemble_wrong_comment(
            condition=condition,
            opponent_move="de",
            opponent_color="White",
            use_opponent_policy=True,
            config=cfg,
        )
        # "White {!de}" pattern should NOT appear
        assert "White {!de}" not in result
        assert "White de" not in result

    @pytest.mark.unit
    def test_conditional_dash_rule(self) -> None:
        """When wrong-move template has em-dash, opponent-response omits its dash."""
        # shape_death_alias template: "Creates {alias} — unconditionally dead."
        # BUT shape_death_alias is suppressed, so use a config with it enabled.
        # Instead test with a condition whose template has em-dash in config.
        # We'll call _assemble_opponent_response directly.
        from analyzers.comment_assembler import _assemble_opponent_response

        # Provide a wrong_move_comment that already has an em-dash
        wrong_comment_with_dash = "Creates bent-four \u2014 unconditionally dead."
        opp_templates = {
            "enabled_conditions": ["shape_death_alias"],
            "templates": [
                {"condition": "shape_death_alias", "template": "{opponent_color} {!opponent_move} \u2014 punishes."},
            ],
        }
        result = _assemble_opponent_response(
            condition="shape_death_alias",
            opponent_move="de",
            opponent_color="White",
            wrong_move_comment=wrong_comment_with_dash,
            opponent_templates=opp_templates,
        )
        # The dash should be removed from the response due to conditional dash rule
        assert "\u2014" not in result
        # But the response itself should still be present
        assert "White" in result
        assert "{!de}" in result

    @pytest.mark.unit
    def test_feature_gate_disabled(self) -> None:
        """When use_opponent_policy=False, no opponent-response appended."""
        cfg = _make_config(max_words=30)
        result = assemble_wrong_comment(
            condition="immediate_capture",
            opponent_move="de",
            opponent_color="White",
            use_opponent_policy=False,
            config=cfg,
        )
        # No opponent response present
        assert "White" not in result
        assert "{!de}" not in result

    @pytest.mark.unit
    @pytest.mark.parametrize("condition", [
        "immediate_capture",
        "capturing_race_lost",
        "self_atari",
        "wrong_direction",
        "default",
    ])
    def test_combined_word_count_under_15(self, condition: str) -> None:
        """For all active conditions, combined result <= 15 words."""
        cfg = _make_config(max_words=15)
        result = assemble_wrong_comment(
            condition=condition,
            opponent_move="de",
            opponent_color="White",
            use_opponent_policy=True,
            config=cfg,
        )
        assert _count_words(result) <= 15

    @pytest.mark.unit
    def test_vp3_no_forbidden_starts(self) -> None:
        """Wrong-move templates in config must not start with forbidden words."""
        from config.teaching import load_raw_teaching_config

        raw = load_raw_teaching_config()
        forbidden_starts = raw.get("voice_constraints", {}).get("forbidden_starts", [])
        assert len(forbidden_starts) > 0, "Expected forbidden_starts in config"

        templates = raw.get("wrong_move_comments", {}).get("templates", [])
        for t in templates:
            comment = t.get("comment", "")
            for prefix in forbidden_starts:
                assert not comment.startswith(prefix), (
                    f"Template for '{t.get('condition')}' starts with "
                    f"forbidden prefix '{prefix}': {comment!r}"
                )
