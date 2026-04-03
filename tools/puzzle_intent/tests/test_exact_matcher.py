"""Tests for exact_matcher module."""

import pytest

from tools.puzzle_intent.exact_matcher import ExactMatcher, _is_contiguous_subsequence, _tokenize
from tools.puzzle_intent.models import MatchTier


class TestTokenize:
    def test_simple_phrase(self):
        assert _tokenize("black to play") == ["black", "to", "play"]

    def test_strips_punctuation(self):
        assert _tokenize("black, to play!") == ["black", "to", "play"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_only_punctuation(self):
        assert _tokenize("...") == []


class TestIsContiguousSubsequence:
    def test_match_at_start(self):
        assert _is_contiguous_subsequence(
            ["black", "to", "play"],
            ["black", "to", "play", "and", "live"],
        )

    def test_match_at_end(self):
        assert _is_contiguous_subsequence(
            ["and", "live"],
            ["black", "to", "play", "and", "live"],
        )

    def test_no_match(self):
        assert not _is_contiguous_subsequence(
            ["white", "to", "play"],
            ["black", "to", "play"],
        )

    def test_empty_needle(self):
        assert not _is_contiguous_subsequence([], ["a", "b"])

    def test_needle_longer_than_haystack(self):
        assert not _is_contiguous_subsequence(["a", "b", "c"], ["a", "b"])


class TestExactMatcher:
    @pytest.fixture
    def matcher(self):
        return ExactMatcher()

    # --- Original 17 objectives ---

    def test_black_to_play(self, matcher):
        result = matcher.match("black to play", raw_text="Black to play")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"
        assert result.confidence == 1.0
        assert result.match_tier == MatchTier.EXACT

    def test_white_to_play(self, matcher):
        result = matcher.match("white to play")
        assert result is not None
        assert result.objective_id == "MOVE.WHITE.PLAY"

    def test_black_to_live(self, matcher):
        result = matcher.match("black to live")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.LIVE"

    def test_white_to_live(self, matcher):
        result = matcher.match("white to live")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.LIVE"

    def test_black_to_kill(self, matcher):
        result = matcher.match("black to kill")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.KILL"

    def test_kill_white(self, matcher):
        result = matcher.match("kill white")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.KILL"

    def test_kill_black(self, matcher):
        result = matcher.match("kill black")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.KILL"

    def test_black_to_capture(self, matcher):
        result = matcher.match("black to capture")
        assert result is not None
        assert result.objective_id == "CAPTURE.BLACK"

    def test_black_to_connect(self, matcher):
        result = matcher.match("black to connect")
        assert result is not None
        assert result.objective_id == "SHAPE.BLACK.CONNECT"

    def test_black_to_cut(self, matcher):
        result = matcher.match("black to cut")
        assert result is not None
        assert result.objective_id == "SHAPE.BLACK.CUT"

    def test_seki(self, matcher):
        result = matcher.match("seki")
        assert result is not None
        assert result.objective_id == "FIGHT.SEKI"

    def test_black_wins_ko(self, matcher):
        result = matcher.match("black wins ko")
        assert result is not None
        assert result.objective_id == "FIGHT.BLACK.WIN_KO"

    def test_black_wins_semeai(self, matcher):
        result = matcher.match("black wins semeai")
        assert result is not None
        assert result.objective_id == "FIGHT.BLACK.WIN_SEMEAI"

    # --- New v2.0 objectives ---

    def test_black_to_escape(self, matcher):
        result = matcher.match("black to escape")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.ESCAPE"

    def test_white_to_escape(self, matcher):
        result = matcher.match("white to escape")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.ESCAPE"

    def test_black_tesuji(self, matcher):
        result = matcher.match("black tesuji")
        assert result is not None
        assert result.objective_id == "TESUJI.BLACK"

    def test_find_tesuji_for_white(self, matcher):
        result = matcher.match("find the tesuji for white")
        assert result is not None
        assert result.objective_id == "TESUJI.WHITE"

    def test_black_endgame(self, matcher):
        result = matcher.match("black endgame")
        assert result is not None
        assert result.objective_id == "ENDGAME.BLACK"

    def test_white_yose(self, matcher):
        result = matcher.match("white yose")
        assert result is not None
        assert result.objective_id == "ENDGAME.WHITE"

    # --- Expanded aliases ---

    def test_black_first(self, matcher):
        result = matcher.match("black first")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_blacks_turn(self, matcher):
        result = matcher.match("black's turn")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_kurosaki_romanized(self, matcher):
        result = matcher.match("kurosaki")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_save_black(self, matcher):
        result = matcher.match("save black")
        assert result is not None
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.LIVE"

    def test_mutual_life(self, matcher):
        result = matcher.match("mutual life")
        assert result is not None
        assert result.objective_id == "FIGHT.SEKI"

    # --- Noise handling ---

    def test_substring_in_noise(self, matcher):
        result = matcher.match("welcome to the game of go black to play")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_no_match(self, matcher):
        result = matcher.match("random gibberish text")
        assert result is None

    def test_empty_text(self, matcher):
        result = matcher.match("")
        assert result is None

    def test_b_to_play(self, matcher):
        result = matcher.match("b to play")
        assert result is not None
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_w_to_play(self, matcher):
        result = matcher.match("w to play")
        assert result is not None
        assert result.objective_id == "MOVE.WHITE.PLAY"
