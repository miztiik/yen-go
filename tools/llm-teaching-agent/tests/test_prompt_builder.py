"""Tests for prompt_builder module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure agent package is importable
_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

from agent.prompt_builder import build_system_prompt, build_user_prompt, load_template

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestLoadTemplate:
    def test_loads_system_prompt(self):
        text = load_template("system_prompt")
        assert "teaching comments" in text.lower() or "Go" in text

    def test_loads_teaching_comment(self):
        text = load_template("teaching_comment")
        assert "wrong move" in text.lower() or "correct move" in text.lower()

    def test_missing_template_raises(self):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_template_xyz")


class TestBuildSystemPrompt:
    def test_combines_persona_and_base(self):
        persona = "You are a test persona."
        result = build_system_prompt(persona)
        assert "You are a test persona." in result
        # Should also include base system prompt content
        assert "JSON" in result or "json" in result

    def test_separator_between_persona_and_base(self):
        persona = "Persona text here."
        result = build_system_prompt(persona)
        assert "---" in result


class TestBuildUserPrompt:
    @pytest.fixture
    def sample_enrichment(self):
        path = _FIXTURES / "sample_enrichment.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_includes_teaching_signals(self, sample_enrichment):
        result = build_user_prompt(sample_enrichment)
        assert "teaching_signals" in result

    def test_includes_puzzle_summary(self, sample_enrichment):
        result = build_user_prompt(sample_enrichment)
        assert "beginner" in result.lower()
        assert "D7" in result

    def test_includes_technique_tags(self, sample_enrichment):
        result = build_user_prompt(sample_enrichment)
        assert "net" in result

    def test_includes_wrong_move_count(self, sample_enrichment):
        result = build_user_prompt(sample_enrichment)
        assert "2" in result  # 2 wrong moves

    def test_raises_without_teaching_signals(self):
        with pytest.raises(ValueError, match="No teaching_signals"):
            build_user_prompt({"puzzle_id": "test"})

    def test_raises_with_empty_teaching_signals(self):
        with pytest.raises(ValueError, match="No teaching_signals"):
            build_user_prompt({"teaching_signals": {}})

    def test_includes_raw_json(self, sample_enrichment):
        result = build_user_prompt(sample_enrichment)
        assert "```json" in result
