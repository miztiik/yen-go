"""Tests for intent_resolver module (end-to-end)."""

import pytest

from tools.puzzle_intent.intent_resolver import (
    IntentResolver,
    resolve_intent,
    resolve_intents_batch,
)
from tools.puzzle_intent.models import IntentResult, MatchTier


class TestIntentResolver:
    @pytest.fixture
    def resolver(self):
        return IntentResolver(enable_semantic=False)

    def test_exact_match_from_raw_text(self, resolver):
        result = resolver.resolve("Black to play")
        assert result.matched is True
        assert result.objective_id == "MOVE.BLACK.PLAY"
        assert result.objective.slug == "black-to-play"
        assert result.objective.name == "Black to Play"
        assert result.match_tier == MatchTier.EXACT
        assert result.confidence == 1.0

    def test_cjk_noise_cleaned(self, resolver):
        result = resolver.resolve("黒先 white to live")
        assert result.matched is True
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.LIVE"

    def test_html_noise_cleaned(self, resolver):
        result = resolver.resolve("<h1>Puzzle</h1> black to kill")
        assert result.matched is True
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.KILL"

    def test_preamble_with_objective(self, resolver):
        result = resolver.resolve("Welcome to the game of go, black to play")
        assert result.matched is True
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_kill_black(self, resolver):
        result = resolver.resolve("kill black")
        assert result.matched is True
        assert result.objective_id == "LIFE_AND_DEATH.WHITE.KILL"

    def test_seki(self, resolver):
        result = resolver.resolve("This is seki")
        assert result.matched is True
        assert result.objective_id == "FIGHT.SEKI"
        assert result.objective.slug == "make-seki"
        assert result.objective.name == "Make Seki"

    def test_escape(self, resolver):
        result = resolver.resolve("black to escape")
        assert result.matched is True
        assert result.objective_id == "LIFE_AND_DEATH.BLACK.ESCAPE"

    def test_tesuji(self, resolver):
        result = resolver.resolve("find the tesuji for black")
        assert result.matched is True
        assert result.objective_id == "TESUJI.BLACK"

    def test_endgame(self, resolver):
        result = resolver.resolve("white yose")
        assert result.matched is True
        assert result.objective_id == "ENDGAME.WHITE"
        assert result.objective.slug == "white-endgame"
        assert result.objective.name == "White Endgame (Yose)"

    def test_no_match(self, resolver):
        result = resolver.resolve("random gibberish with no go terms")
        assert result.matched is False
        assert result.match_tier == MatchTier.NONE
        assert result.confidence == 0.0

    def test_empty_text(self, resolver):
        result = resolver.resolve("")
        assert result.matched is False

    def test_whitespace_only(self, resolver):
        result = resolver.resolve("   ")
        assert result.matched is False

    def test_raw_text_preserved(self, resolver):
        raw = "黒先 Black to play"
        result = resolver.resolve(raw)
        assert result.raw_text == raw

    def test_cleaned_text_in_result(self, resolver):
        result = resolver.resolve("黒先 Black to play")
        assert result.cleaned_text == "black to play"

    def test_resolve_batch(self, resolver):
        results = resolver.resolve_batch([
            "black to play",
            "white to live",
            "random text",
            "black to escape",
        ])
        assert len(results) == 4
        assert results[0].objective_id == "MOVE.BLACK.PLAY"
        assert results[1].objective_id == "LIFE_AND_DEATH.WHITE.LIVE"
        assert results[2].matched is False
        assert results[3].objective_id == "LIFE_AND_DEATH.BLACK.ESCAPE"


class TestModuleLevelFunctions:
    def test_resolve_intent(self):
        result = resolve_intent("black to play", enable_semantic=False)
        assert result.objective_id == "MOVE.BLACK.PLAY"

    def test_resolve_intents_batch(self):
        results = resolve_intents_batch(
            ["black to play", "white to kill"],
            enable_semantic=False,
        )
        assert len(results) == 2
        assert results[0].objective_id == "MOVE.BLACK.PLAY"
        assert results[1].objective_id == "LIFE_AND_DEATH.WHITE.KILL"


class TestIntentResultModel:
    def test_no_match_factory(self):
        result = IntentResult.no_match(raw_text="test", cleaned_text="test")
        assert result.matched is False
        assert result.objective_id is None
        assert result.confidence == 0.0
        assert result.match_tier == MatchTier.NONE

    def test_matched_property(self):
        result = IntentResult(
            objective_id="MOVE.BLACK.PLAY",
            objective=None,
            matched_alias="black to play",
            confidence=1.0,
            match_tier=MatchTier.EXACT,
            cleaned_text="black to play",
            raw_text="Black to play",
        )
        assert result.matched is True
