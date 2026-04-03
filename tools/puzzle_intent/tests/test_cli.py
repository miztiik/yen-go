"""Tests for puzzle_intent CLI (__main__.py) and to_dict()."""

import json
import subprocess
import sys

from tools.puzzle_intent.intent_resolver import resolve_intent
from tools.puzzle_intent.models import IntentResult


class TestIntentResultToDict:
    def test_to_dict_keys(self):
        result = resolve_intent("Black to play", enable_semantic=False)
        d = result.to_dict()
        expected_keys = {
            "objective_id",
            "slug",
            "name",
            "matched_alias",
            "confidence",
            "match_tier",
            "matched",
            "cleaned_text",
            "raw_text",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_json_serializable(self):
        result = resolve_intent("Black to play", enable_semantic=False)
        # Should not raise
        serialized = json.dumps(result.to_dict())
        assert isinstance(serialized, str)

    def test_to_dict_match_tier_is_string(self):
        result = resolve_intent("Black to play", enable_semantic=False)
        d = result.to_dict()
        assert isinstance(d["match_tier"], str)
        assert d["match_tier"] == "exact"

    def test_to_dict_no_match(self):
        result = IntentResult.no_match(raw_text="gibberish", cleaned_text="gibberish")
        d = result.to_dict()
        assert d["objective_id"] is None
        assert d["slug"] is None
        assert d["name"] is None
        assert d["confidence"] == 0.0
        assert d["match_tier"] == "none"
        assert d["matched"] is False

    def test_to_dict_slug_and_name_present(self):
        result = resolve_intent("Black to play", enable_semantic=False)
        d = result.to_dict()
        assert d["slug"] == "black-to-play"
        assert d["name"] == "Black to Play"


class TestCLI:
    """Tests for python -m tools.puzzle_intent CLI."""

    def _run_cli(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "tools.puzzle_intent", *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            input=stdin,
            timeout=30,
        )

    def test_help_exits_cleanly(self):
        result = self._run_cli("--help")
        assert result.returncode == 0
        assert "Resolve puzzle objectives" in result.stdout

    def test_exact_match_returns_json(self):
        result = self._run_cli("--no-semantic", "Black to play")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["objective_id"] == "MOVE.BLACK.PLAY"
        assert data["slug"] == "black-to-play"
        assert data["name"] == "Black to Play"
        assert data["match_tier"] == "exact"
        assert data["confidence"] == 1.0
        assert data["matched"] is True

    def test_no_match_exit_code_1(self):
        result = self._run_cli("--no-semantic", "completely irrelevant gibberish text")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["objective_id"] is None
        assert data["matched"] is False

    def test_no_semantic_flag(self):
        result = self._run_cli("--no-semantic", "White to live")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["objective_id"] == "LIFE_AND_DEATH.WHITE.LIVE"
        assert data["match_tier"] == "exact"

    def test_stdin_input(self):
        result = self._run_cli("--no-semantic", stdin="Black to play")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["objective_id"] == "MOVE.BLACK.PLAY"

    def test_empty_text_error(self):
        result = self._run_cli("--no-semantic", "")
        assert result.returncode != 0

    def test_output_is_valid_json(self):
        result = self._run_cli("--no-semantic", "black to capture")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)
        assert "objective_id" in data
        assert "confidence" in data

    def test_file_flag_reads_utf8(self, tmp_path):
        f = tmp_path / "comment.txt"
        f.write_text("黒先 生き：Black to live", encoding="utf-8")
        result = self._run_cli("--no-semantic", "--file", str(f))
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["objective_id"] == "LIFE_AND_DEATH.BLACK.LIVE"

    def test_file_flag_with_double_quotes(self, tmp_path):
        f = tmp_path / "quotes.txt"
        f.write_text(
            'YouTube channel "Amigo\'s Go". Black to play',
            encoding="utf-8",
        )
        result = self._run_cli("--no-semantic", "--file", str(f))
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["objective_id"] == "MOVE.BLACK.PLAY"

    def test_file_flag_missing_file(self):
        result = self._run_cli("--no-semantic", "--file", "nonexistent.txt")
        assert result.returncode != 0

    def test_text_and_file_conflict(self, tmp_path):
        f = tmp_path / "conflict.txt"
        f.write_text("Black to play", encoding="utf-8")
        result = self._run_cli("--no-semantic", "--file", str(f), "Black to play")
        assert result.returncode != 0

    def test_help_mentions_file_flag(self):
        result = self._run_cli("--help")
        assert "--file" in result.stdout

    def test_help_mentions_rebuild_embeddings(self):
        result = self._run_cli("--help")
        assert "--rebuild-embeddings" in result.stdout
