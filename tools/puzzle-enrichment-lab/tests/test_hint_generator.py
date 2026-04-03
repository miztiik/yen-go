"""Tests for hint_generator module (config-driven, T-12)."""

from __future__ import annotations

import pytest
from analyzers.hint_generator import (
    COORDINATE_TEMPLATES,
    HintOperationLog,
    InferenceConfidence,
    _generate_coordinate_hint,
    _generate_reasoning_hint,
    _gtp_to_sgf_token,
    _resolve_hint_text,
    format_yh_property,
    generate_hints,
    infer_technique_from_solution,
)
from config import clear_cache


@pytest.fixture(autouse=True)
def _clear_cfg():
    clear_cache()
    yield
    clear_cache()


# ---- Fixture helpers ----


def _make_analysis(
    *,
    correct_move_gtp: str = "C3",
    correct_move_policy: float = 0.3,
    correct_move_winrate: float = 0.95,
    solution_depth: int = 3,
    refutation_count: int = 2,
    pv: list[str] | None = None,
) -> dict:
    """Build a minimal AiAnalysisResult dict."""
    return {
        "validation": {
            "correct_move_gtp": correct_move_gtp,
            "correct_move_policy": correct_move_policy,
            "correct_move_winrate": correct_move_winrate,
            "status": "accepted",
            "pv": pv or [],
        },
        "refutations": [],
        "difficulty": {
            "solution_depth": solution_depth,
            "refutation_count": refutation_count,
        },
    }


# ---- Config-driven hint text (Tier 1) ----


class TestResolveHintText:
    """Verify hint_text resolution from config."""

    def test_canonical_tag_resolves(self):
        text = _resolve_hint_text("snapback")
        assert "snapback" in text.lower()

    def test_includes_japanese_term(self):
        text = _resolve_hint_text("snapback")
        assert "uttegaeshi" in text.lower()

    def test_all_28_tags_resolve(self):
        from config.teaching import load_teaching_comments_config
        cfg = load_teaching_comments_config()
        for slug in cfg.correct_move_comments:
            text = _resolve_hint_text(slug)
            assert text, f"No hint_text for {slug}"

    def test_unknown_tag_returns_empty(self):
        text = _resolve_hint_text("nonexistent-tag")
        assert text == ""  # No fallback, returns empty


class TestCoordinateTemplates:
    """Verify COORDINATE_TEMPLATES dictionary."""

    def test_has_default(self):
        assert "default" in COORDINATE_TEMPLATES

    def test_all_templates_contain_xy_token(self):
        for tag, template in COORDINATE_TEMPLATES.items():
            assert "{!xy}" in template, f"Template for '{tag}' missing {{!xy}} token"


# ---- GTP to SGF conversion ----


class TestGtpToSgfToken:
    """Test GTP → SGF coordinate conversion."""

    def test_a1_to_as(self):
        """A1 (bottom-left) → 'as' (col a, row s on 19x19)."""
        assert _gtp_to_sgf_token("A1") == "as"

    def test_t19_to_sa(self):
        """T19 (top-right) → 'sa' (col s, row a on 19x19)."""
        assert _gtp_to_sgf_token("T19") == "sa"

    def test_c7_to_cg(self):
        """C7 → 'cm' (col c=3, row 7→13 from top=m)."""
        # C=col 3→'c', row 7→19-7=12→chr(a+12)='m'
        assert _gtp_to_sgf_token("C7") == "cm"

    def test_j10_to_ij(self):
        """J10 (skips I, so J=col 9→'i'). Row 10→19-10=9→chr(a+9)='j'."""
        assert _gtp_to_sgf_token("J10") == "ij"

    def test_d4_to_dp(self):
        """D4 → col D=4→'d', row 4→19-4=15→chr(a+15)='p'."""
        assert _gtp_to_sgf_token("D4") == "dp"

    def test_pass_returns_question_marks(self):
        assert _gtp_to_sgf_token("pass") == "??"

    def test_empty_returns_question_marks(self):
        assert _gtp_to_sgf_token("") == "??"

    def test_invalid_returns_question_marks(self):
        assert _gtp_to_sgf_token("Z99") == "??"

    def test_lowercase_input(self):
        assert _gtp_to_sgf_token("c7") == "cm"


# ---- _generate_coordinate_hint ----


class TestGenerateCoordinateHint:
    """Test Tier 3 coordinate hint generation."""

    def test_snapback_template(self):
        hint = _generate_coordinate_hint("snapback", "C3")
        assert "snapback" in hint.lower()
        assert "{!cq}" in hint  # C=c, 3→19-3=16→q

    def test_ladder_template(self):
        hint = _generate_coordinate_hint("ladder", "D4")
        assert "ladder" in hint.lower()
        assert "{!dp}" in hint

    def test_default_template_for_unknown_tag(self):
        hint = _generate_coordinate_hint("unknown-tag", "C3")
        assert "first move" in hint.lower()
        assert "{!cq}" in hint

    def test_pass_move(self):
        hint = _generate_coordinate_hint("ko", "pass")
        assert "{!??}" in hint

    def test_empty_move(self):
        hint = _generate_coordinate_hint("ko", "")
        assert "{!??}" in hint


# ---- _generate_reasoning_hint ----


class TestGenerateReasoningHint:
    """Test Tier 2 reasoning hint generation."""

    def test_analysis_based_reasoning(self):
        analysis = _make_analysis(solution_depth=3, refutation_count=2)
        hint = _generate_reasoning_hint("ko", analysis, ["ko"])
        assert "3 moves" in hint
        assert "2 tempting" in hint

    def test_unknown_technique_uses_depth_fallback(self):
        analysis = _make_analysis(solution_depth=5, refutation_count=3)
        hint = _generate_reasoning_hint("zzz-unknown", analysis, ["zzz-unknown"])
        assert "5 moves" in hint
        assert "3 tempting" in hint

    def test_unknown_technique_single_refutation(self):
        analysis = _make_analysis(solution_depth=1, refutation_count=1)
        hint = _generate_reasoning_hint("zzz-unknown", analysis, ["zzz-unknown"])
        assert "1 move" in hint  # singular
        assert "1 tempting" in hint

    def test_secondary_tag_appended(self):
        analysis = _make_analysis()
        hint = _generate_reasoning_hint("snapback", analysis, ["snapback", "ko"])
        assert "also consider" in hint.lower()

    def test_no_secondary_tag(self):
        analysis = _make_analysis()
        hint = _generate_reasoning_hint("snapback", analysis, ["snapback"])
        assert "also consider" not in hint.lower()

    def test_fallback_with_zero_depth(self):
        analysis = _make_analysis(solution_depth=0, refutation_count=0)
        hint = _generate_reasoning_hint("zzz-unknown", analysis, ["zzz-unknown"])
        assert "read carefully" in hint.lower()

    def test_detection_evidence_not_leaked_to_tier2(self):
        """DetectionResult.evidence is developer-facing diagnostic text and
        must NOT appear as user-facing Tier 2 hint content."""
        from models.detection import DetectionResult

        analysis = _make_analysis(solution_depth=3, refutation_count=2)
        detection_results = [
            DetectionResult(
                detected=True,
                confidence=0.6,
                tag_slug="ladder",
                evidence="PV diagonal ratio 0.50 (board simulation inconclusive)",
            ),
        ]
        hint = _generate_reasoning_hint(
            "ladder", analysis, ["ladder"],
            detection_results=detection_results,
        )
        # Evidence string must NOT be the hint
        assert "PV diagonal ratio" not in hint
        assert "board simulation" not in hint
        # Should fall through to level-adaptive T16 template
        assert "3 moves" in hint or "reading" in hint.lower()

    def test_capture_race_evidence_not_leaked_to_tier2(self):
        """Capture-race detector evidence must also not leak."""
        from models.detection import DetectionResult

        analysis = _make_analysis(solution_depth=5, refutation_count=3)
        detection_results = [
            DetectionResult(
                detected=True,
                confidence=0.8,
                tag_slug="capture-race",
                evidence="2 adjacent race pair(s) found",
            ),
        ]
        hint = _generate_reasoning_hint(
            "capture-race", analysis, ["capture-race"],
            detection_results=detection_results,
        )
        assert "pair(s)" not in hint
        assert "adjacent race" not in hint
        # Should use T16 template instead
        assert "5 moves" in hint or "reading" in hint.lower()


# ---- generate_hints (integration) ----


class TestGenerateHints:
    """Integration tests for the full generate_hints pipeline."""

    def test_returns_exactly_3_hints(self):
        analysis = _make_analysis()
        hints = generate_hints(analysis, ["life-and-death"])
        assert len(hints) == 3

    def test_tier1_is_technique_hint(self):
        analysis = _make_analysis()
        hints = generate_hints(analysis, ["ko"])
        assert "ko" in hints[0].lower()

    def test_tier2_is_reasoning(self):
        analysis = _make_analysis()
        hints = generate_hints(analysis, ["ko"])
        # Tier 2 should be a reasoning explanation, not just the technique name
        assert len(hints[1]) > len(hints[0])

    def test_tier3_contains_coordinate_token(self):
        analysis = _make_analysis(correct_move_gtp="C3")
        hints = generate_hints(analysis, ["life-and-death"])
        assert "{!" in hints[2]

    def test_empty_tags_with_no_analysis_returns_empty_hints(self):
        """When no tags and analysis data is too weak for inference, return empty."""
        analysis = _make_analysis(solution_depth=0, refutation_count=0)
        hints = generate_hints(analysis, [])
        assert hints == ["", "", ""]

    def test_coordinate_correct_for_known_move(self):
        analysis = _make_analysis(correct_move_gtp="D4")
        # Use life-and-death (not in TIER3_TACTICAL_SUPPRESS_TAGS)
        hints = generate_hints(analysis, ["life-and-death"])
        assert "{!dp}" in hints[2]

    def test_all_hints_are_strings(self):
        analysis = _make_analysis()
        # Use life-and-death + ko (not in TIER3_TACTICAL_SUPPRESS_TAGS)
        hints = generate_hints(analysis, ["life-and-death", "ko"])
        for i, hint in enumerate(hints):
            assert isinstance(hint, str), f"Hint {i} is not a string"
            assert len(hint) > 0, f"Hint {i} is empty"


# ---- format_yh_property ----


class TestFormatYhProperty:
    """Test YH SGF property formatting."""

    def test_basic_pipe_delimited(self):
        hints = ["Hint one", "Hint two", "Hint three"]
        assert format_yh_property(hints) == "Hint one|Hint two|Hint three"

    def test_caps_at_3(self):
        hints = ["1", "2", "3", "4"]
        result = format_yh_property(hints)
        assert result == "1|2|3"

    def test_single_hint(self):
        assert format_yh_property(["Only one"]) == "Only one"

    def test_empty_list(self):
        assert format_yh_property([]) == ""

    def test_all_empty_hints_returns_empty(self):
        """YH[||] bug fix: ['', '', ''] should produce '' not '||'."""
        assert format_yh_property(["", "", ""]) == ""

    def test_whitespace_only_hints_filtered(self):
        assert format_yh_property(["  ", "\t", ""]) == ""

    def test_mixed_empty_and_real_hints(self):
        hints = ["Focus on corner", "", "The first move is at {!cg}"]
        result = format_yh_property(hints)
        assert result == "Focus on corner|The first move is at {!cg}"

    def test_preserves_coordinate_tokens(self):
        hints = ["Focus on corner", "Ladder pattern", "The first move is at {!cg}"]
        result = format_yh_property(hints)
        assert "{!cg}" in result

    def test_strips_pipe_from_content(self):
        """RC-1: Pipe inside a tier's text must be sanitized to prevent YH corruption."""
        hints = ["Ladder", "ladder chase | confirmed by PV", "{!cg}"]
        result = format_yh_property(hints)
        # Should have exactly 2 pipes (3 tiers), not 3 pipes (4 segments)
        assert result.count("|") == 2
        assert "ladder chase   confirmed by PV" in result


# ---------------------------------------------------------------------------
# Backend hint safety features (T22 → T28 green phase)
# Ported from backend enrichment/hints.py + solution_tagger.py
# ---------------------------------------------------------------------------


class TestAtariRelevanceGating:
    """Backend port: Don't suggest coordinate hints when correct move
    creates an irrelevant atari."""

    def test_atari_at_move_suppresses_coordinate_hint(self):
        """When correct move is an atari but atari is incidental to puzzle goal,
        Tier 3 coordinate hint should be suppressed entirely."""
        analysis = _make_analysis(correct_move_gtp="D4", solution_depth=5)
        analysis["atari_at_correct_move"] = True
        analysis["puzzle_objective"] = "capture-race"

        hints = generate_hints(analysis, ["capture-race"])

        assert len(hints) >= 3
        assert hints[2] == "", "Tier 3 should be suppressed for irrelevant atari"


class TestDepthGatedTier3:
    """Backend port: Only show coordinate hints when puzzle depth >= threshold."""

    def test_shallow_puzzle_no_coordinate_hint(self):
        """Depth 1 puzzle should NOT get a Tier 3 coordinate hint."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=1)
        hints = generate_hints(analysis, ["life-and-death"])
        assert len(hints) == 3
        assert not hints[2] or "{!" not in hints[2]

    def test_deep_puzzle_gets_coordinate_hint(self):
        """Depth 5 puzzle should get a Tier 3 coordinate hint."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=5)
        hints = generate_hints(analysis, ["life-and-death"])
        assert isinstance(hints, list)
        assert len(hints) == 3
        assert "{!" in hints[2]

    def test_depth_gated_flag_in_log(self):
        """When depth < threshold, operation log records depth_gated=True."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=1)
        result = generate_hints(analysis, ["life-and-death"], return_log=True)
        assert isinstance(result, tuple)
        hints, log = result
        assert log.tier3_depth_gated is True
        assert log.tier3_source == "depth_gated"


class TestSolutionAwareFallback:
    """Backend port: When technique detection fails, infer from solution shape."""

    def test_fallback_infers_technique_from_solution(self):
        """When no tags detected, solution shape analysis provides a hint."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=3)
        hints = generate_hints(analysis, [])
        assert len(hints) == 3
        assert hints[0]  # Tier 1 should have a fallback hint

    def test_fallback_confidence_level(self):
        """Fallback hints should produce at least some hint content."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=3)
        hints = generate_hints(analysis, [])
        assert any(h for h in hints if h)


class TestHintOperationLog:
    """Backend port: Each hint tier produces a structured operation log."""

    def test_operation_log_returned(self):
        """generate_hints returns operation log alongside hints when return_log=True."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=3)
        result = generate_hints(analysis, ["life-and-death"], return_log=True)
        assert isinstance(result, tuple) and len(result) == 2

    def test_operation_log_has_tier_entries(self):
        """Operation log should contain source info for each tier."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=3)
        result = generate_hints(analysis, ["life-and-death"], return_log=True)
        assert isinstance(result, tuple)
        _hints, log = result
        assert isinstance(log, HintOperationLog)
        assert log.tier1_source
        assert log.tier2_source
        assert log.tier3_source


class TestLibertyAnalysisHints:
    """Backend port: Liberty counting for capture-race and ko hints."""

    def test_capture_race_hint_mentions_liberties(self):
        """Capture-race hints should mention liberty advantage/disadvantage."""
        analysis = _make_analysis(correct_move_gtp="D4", solution_depth=4)
        analysis["liberty_info"] = {"attacker": 3, "defender": 2}
        hints = generate_hints(analysis, ["capture-race"])
        tier2 = hints[1] if len(hints) >= 2 else ""
        assert "libert" in tier2.lower()

    def test_ko_hint_mentions_ko_threat(self):
        """Ko situation hints should reference the ko fight context."""
        analysis = _make_analysis(correct_move_gtp="D4", solution_depth=3)
        analysis["liberty_info"] = {"attacker": 2, "defender": 2}
        hints = generate_hints(analysis, ["ko"])
        tier2 = hints[1] if len(hints) >= 2 else ""
        assert "libert" in tier2.lower() or "ko" in tier2.lower()


# ---------------------------------------------------------------------------
# T25: InferenceConfidence + infer_technique_from_solution unit tests
# ---------------------------------------------------------------------------


class TestInferTechniqueFromSolution:
    """Unit tests for the solution-aware inference function."""

    def test_refutations_with_depth_returns_high(self):
        analysis = _make_analysis(solution_depth=3, refutation_count=2)
        result = infer_technique_from_solution(analysis)
        assert result.confidence >= InferenceConfidence.HIGH
        assert result.tag == "life-and-death"

    def test_long_pv_returns_medium(self):
        analysis = _make_analysis(solution_depth=1, refutation_count=0, pv=["C3", "D4", "E5", "F6", "G7", "H8"])
        result = infer_technique_from_solution(analysis)
        assert result.confidence == InferenceConfidence.MEDIUM
        assert result.tag == "ko"

    def test_no_evidence_returns_low(self):
        analysis = _make_analysis(solution_depth=0, refutation_count=0)
        result = infer_technique_from_solution(analysis)
        assert result.confidence == InferenceConfidence.LOW
        assert result.tag is None


# ---------------------------------------------------------------------------
# T26: HintOperationLog unit tests
# ---------------------------------------------------------------------------


class TestHintOperationLogDataclass:
    """Unit tests for the HintOperationLog dataclass."""

    def test_defaults(self):
        log = HintOperationLog()
        assert log.tier1_source == ""
        assert log.tier3_depth_gated is False
        assert log.tier3_atari_suppressed is False
        assert log.inference_used is False

    def test_atari_suppression_recorded(self):
        analysis = _make_analysis(correct_move_gtp="D4", solution_depth=5)
        analysis["atari_at_correct_move"] = True
        _, log = generate_hints(analysis, ["capture-race"], return_log=True)
        assert log.tier3_atari_suppressed is True
        assert log.tier3_source == "suppressed_atari"

# ---------------------------------------------------------------------------
# RC-2: Tactical tag Tier 3 coordinate suppression
# ---------------------------------------------------------------------------


class TestTacticalTagTier3Suppression:
    """RC-2: Suppress coordinate hints for tags where the move IS the answer."""

    def test_net_tag_suppresses_coordinate(self):
        """Net puzzles should NOT reveal the first move coordinate."""
        analysis = _make_analysis(correct_move_gtp="P14", solution_depth=5)
        hints = generate_hints(analysis, ["net"])
        assert len(hints) == 3
        # Tier 3 should be empty — no coordinate revealed
        assert not hints[2] or "{!" not in hints[2]

    def test_ladder_tag_suppresses_coordinate(self):
        """Ladder puzzles should NOT reveal the first move coordinate."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=5)
        hints = generate_hints(analysis, ["ladder"])
        assert len(hints) == 3
        assert not hints[2] or "{!" not in hints[2]

    def test_snapback_tag_suppresses_coordinate(self):
        """Snapback puzzles should NOT reveal the first move coordinate."""
        analysis = _make_analysis(correct_move_gtp="D4", solution_depth=5)
        hints = generate_hints(analysis, ["snapback"])
        assert len(hints) == 3
        assert not hints[2] or "{!" not in hints[2]

    def test_throw_in_tag_suppresses_coordinate(self):
        analysis = _make_analysis(correct_move_gtp="E5", solution_depth=5)
        hints = generate_hints(analysis, ["throw-in"])
        assert len(hints) == 3
        assert not hints[2] or "{!" not in hints[2]

    def test_oiotoshi_tag_suppresses_coordinate(self):
        analysis = _make_analysis(correct_move_gtp="F6", solution_depth=5)
        hints = generate_hints(analysis, ["oiotoshi"])
        assert len(hints) == 3
        assert not hints[2] or "{!" not in hints[2]

    def test_life_and_death_still_gets_coordinate(self):
        """Non-tactical tags should still get coordinate hints at depth >= 3."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=5)
        hints = generate_hints(analysis, ["life-and-death"])
        assert len(hints) == 3
        assert "{!" in hints[2]

    def test_tactical_suppression_logged(self):
        """Operation log records tactical_suppressed source."""
        analysis = _make_analysis(correct_move_gtp="C3", solution_depth=5)
        _, log = generate_hints(analysis, ["net"], return_log=True)
        assert log.tier3_source == "tactical_suppressed"
        assert log.tier3_depth_gated is True

    def test_suppress_tags_constant_is_frozenset(self):
        """TIER3_TACTICAL_SUPPRESS_TAGS should be an immutable frozenset."""
        from analyzers.hint_generator import TIER3_TACTICAL_SUPPRESS_TAGS
        assert isinstance(TIER3_TACTICAL_SUPPRESS_TAGS, frozenset)
        assert "net" in TIER3_TACTICAL_SUPPRESS_TAGS
        assert "ladder" in TIER3_TACTICAL_SUPPRESS_TAGS


# --- Migrated from test_sprint2_fixes.py ---


@pytest.mark.unit
class TestGtpToSgfTokenBoardSize:
    """P0.3: _gtp_to_sgf_token must respect board_size parameter."""

    def test_19x19_a1_to_as(self):
        """19×19: A1 (bottom-left) → 'as'."""
        assert _gtp_to_sgf_token("A1", board_size=19) == "as"

    def test_19x19_t19_to_sa(self):
        """19×19: T19 (top-right) → 'sa'."""
        assert _gtp_to_sgf_token("T19", board_size=19) == "sa"

    def test_19x19_default_backward_compat(self):
        """Default (no board_size) still works for 19×19."""
        assert _gtp_to_sgf_token("C7") == "cm"

    def test_9x9_a1_to_ai(self):
        """9×9: A1 (bottom-left) → 'ai' (row i = 9th from top)."""
        # A1 on 9×9: col A=1→'a', row 1→chr(a+9-1)=chr(a+8)='i'
        assert _gtp_to_sgf_token("A1", board_size=9) == "ai"

    def test_9x9_a9_to_aa(self):
        """9×9: A9 (top-left) → 'aa' (row a = top)."""
        # A9 on 9×9: col A=1→'a', row 9→chr(a+9-9)=chr(a+0)='a'
        assert _gtp_to_sgf_token("A9", board_size=9) == "aa"

    def test_9x9_j9_to_ia(self):
        """9×9: J9 (top-right, J=col 9) → 'ia'."""
        # J on 9×9: col J=10-1=9→'i', row 9→chr(a+0)='a'
        assert _gtp_to_sgf_token("J9", board_size=9) == "ia"

    def test_9x9_e5_to_ee(self):
        """9×9: E5 (center) → 'ee'."""
        # E=col 5→'e', row 5→chr(a+9-5)=chr(a+4)='e'
        assert _gtp_to_sgf_token("E5", board_size=9) == "ee"

    def test_9x9_e2_to_eh(self):
        """9×9: E2 → 'eh' (the board_9x9.sgf correct move)."""
        # E=col 5→'e', row 2→chr(a+9-2)=chr(a+7)='h'
        assert _gtp_to_sgf_token("E2", board_size=9) == "eh"

    def test_13x13_a1_to_am(self):
        """13×13: A1 (bottom-left) → 'am'."""
        # A1 on 13×13: col A=1→'a', row 1→chr(a+13-1)=chr(a+12)='m'
        assert _gtp_to_sgf_token("A1", board_size=13) == "am"

    def test_13x13_n13_to_ma(self):
        """13×13: N13 (top-right, N=col 13) → 'ma'."""
        # N on 13×13: col N=14-1=13→'m' (skip I), row 13→chr(a+0)='a'
        assert _gtp_to_sgf_token("N13", board_size=13) == "ma"

    def test_13x13_g7_to_gg(self):
        """13×13: G7 (center-ish) → 'gg'."""
        # G=col 7→'g', row 7→chr(a+13-7)=chr(a+6)='g'
        assert _gtp_to_sgf_token("G7", board_size=13) == "gg"

    def test_9x9_vs_19x19_differ(self):
        """Same GTP coordinate produces DIFFERENT SGF on different board sizes.

        This is the actual bug P0.3 fixes — without board_size, A1 would
        always produce 'as' (19×19) even on a 9×9 board where 'as' is
        off-board (row 19 doesn't exist on 9×9).
        """
        sgf_9x9 = _gtp_to_sgf_token("A1", board_size=9)
        sgf_19x19 = _gtp_to_sgf_token("A1", board_size=19)
        assert sgf_9x9 != sgf_19x19, (
            f"A1 should differ between 9×9 ({sgf_9x9}) and 19×19 ({sgf_19x19})"
        )
        assert sgf_9x9 == "ai"
        assert sgf_19x19 == "as"


@pytest.mark.unit
class TestGenerateHintsBoardSize:
    """P0.3: generate_hints must accept and propagate board_size."""

    def _make_analysis(self, correct_move: str = "E2") -> dict:
        return {
            "validation": {
                "correct_move_gtp": correct_move,
                "correct_move_policy": 0.3,
                "correct_move_winrate": 0.95,
                "status": "accepted",
                "pv": [],
            },
            "refutations": [],
            "difficulty": {
                "solution_depth": 3,
                "refutation_count": 2,
            },
        }

    def test_9x9_hint_contains_correct_sgf_coord(self):
        """On 9×9, E2 → {!eh} (not {!er} which would be 19×19)."""
        analysis = self._make_analysis("E2")
        hints = generate_hints(analysis, ["life-and-death"], board_size=9)
        tier3 = hints[2]
        assert "{!eh}" in tier3, (
            f"Expected {{!eh}} for E2 on 9×9, got: {tier3}"
        )
        assert "{!er}" not in tier3, (
            f"19×19 coordinate {{!er}} should NOT appear for 9×9: {tier3}"
        )

    def test_19x19_hint_backward_compat(self):
        """Default board_size=19 produces same results as before."""
        analysis = self._make_analysis("C3")
        hints_default = generate_hints(analysis, ["life-and-death"])
        hints_explicit = generate_hints(analysis, ["life-and-death"], board_size=19)
        assert hints_default == hints_explicit

    def test_13x13_hint_correct(self):
        """On 13×13, G6 → {!gf} (not {!gn})."""
        # Verify the coordinate first
        assert _gtp_to_sgf_token("G6", board_size=13) == "gh"
        analysis = self._make_analysis("G6")
        hints = generate_hints(analysis, ["life-and-death"], board_size=13)
        tier3 = hints[2]
        assert "{!gh}" in tier3, (
            f"Expected {{!gh}} for G6 on 13×13, got: {tier3}"
        )
