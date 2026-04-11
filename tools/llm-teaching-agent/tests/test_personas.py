"""Tests for personas module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure agent package is importable
_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

from agent.personas import list_personas, load_persona


class TestListPersonas:
    def test_returns_list(self):
        result = list_personas()
        assert isinstance(result, list)

    def test_contains_expected_personas(self):
        result = list_personas()
        assert "cho_chikun" in result
        assert "lee_sedol" in result
        assert "generic_teacher" in result

    def test_sorted_alphabetically(self):
        result = list_personas()
        assert result == sorted(result)


class TestLoadPersona:
    def test_load_cho_chikun(self):
        text = load_persona("cho_chikun")
        assert "Cho Chikun" in text
        assert len(text) > 50

    def test_load_lee_sedol(self):
        text = load_persona("lee_sedol")
        assert "Lee Sedol" in text

    def test_load_generic_teacher(self):
        text = load_persona("generic_teacher")
        assert "teacher" in text.lower() or "Go" in text

    def test_missing_persona_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_persona("nonexistent_persona_xyz")

    def test_missing_persona_lists_available(self):
        with pytest.raises(FileNotFoundError, match="cho_chikun"):
            load_persona("nonexistent_persona_xyz")

    def test_persona_text_is_stripped(self):
        """Loaded persona text should not have leading/trailing whitespace."""
        text = load_persona("generic_teacher")
        assert text == text.strip()
