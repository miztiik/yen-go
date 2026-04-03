"""Tests for keyword_matcher module (Tier 1.5)."""

import pytest

from tools.puzzle_intent.keyword_matcher import KeywordMatcher
from tools.puzzle_intent.models import MatchTier


class TestKeywordMatcher:
    @pytest.fixture
    def matcher(self):
        return KeywordMatcher()

    # --- Basic verb + side matches ---

    def test_black_escape(self, matcher):
        result = matcher.match("can black escape from this corner")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.ESCAPE"
        assert result.match_tier == MatchTier.KEYWORD
        assert result.confidence == 0.7

    def test_white_survive(self, matcher):
        result = matcher.match("white needs to survive this attack")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.LIVE"

    def test_black_connect(self, matcher):
        result = matcher.match("connect your black stones together")
        assert result is not None
        assert result.objective_id == "SHAPE.BLACK.CONNECT"

    def test_white_cut(self, matcher):
        result = matcher.match("white should try to cut here")
        assert result is not None
        assert result.objective_id == "SHAPE.WHITE.CUT"

    def test_black_play(self, matcher):
        result = matcher.match("it is time for black to play a move")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    # --- Destructive verb inversion ---

    def test_kill_white_inverts_to_black(self, matcher):
        result = matcher.match("try to kill the white group here")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.KILL"

    def test_capture_white_inverts_to_black(self, matcher):
        result = matcher.match("capture the white thing in the corner")
        assert result is not None
        assert result.objective_id == "CAPTURE.BLACK"

    def test_black_before_kill_is_actor(self, matcher):
        result = matcher.match("black should kill the group")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.KILL"

    # --- Sideless objectives ---

    def test_seki(self, matcher):
        result = matcher.match("the best result is seki")
        assert result is not None
        assert result.objective_id == "FIGHT.SEKI"

    def test_mutual_life(self, matcher):
        result = matcher.match("this is mutual life")
        assert result is not None
        assert result.objective_id == "FIGHT.SEKI"

    # --- No match cases ---

    def test_no_go_verb(self, matcher):
        result = matcher.match("the weather is nice today")
        assert result is None

    def test_verb_without_side(self, matcher):
        result = matcher.match("try to escape from the corner")
        assert result is None

    def test_empty_text(self, matcher):
        result = matcher.match("")
        assert result is None

    def test_side_without_verb(self, matcher):
        result = matcher.match("black is in the corner")
        assert result is None

    # --- Result metadata ---

    def test_matched_alias_is_none(self, matcher):
        """Keyword matches don't have a specific alias."""
        result = matcher.match("black needs to escape")
        assert result is not None
        assert result.matched_alias is None

    def test_cleaned_text_preserved(self, matcher):
        text = "can black escape from here"
        result = matcher.match(text, raw_text="Can Black escape from here?")
        assert result is not None
        assert result.cleaned_text == text
        assert result.raw_text == "Can Black escape from here?"

    def test_confidence_is_0_7(self, matcher):
        result = matcher.match("black needs to play here")
        assert result is not None
        assert result.confidence == 0.7
