"""Tests for response_parser module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure agent package is importable
_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

from agent.response_parser import TeachingComments, TeachingOutput, parse_llm_response


class TestTeachingComments:
    def test_valid_comments(self):
        tc = TeachingComments(
            correct_comment="Net at D7 seals the group.",
            wrong_comments={"jb": "White lives in seki.", "be": "White escapes."},
            summary="Beginner net problem.",
        )
        assert tc.correct_comment == "Net at D7 seals the group."
        assert len(tc.wrong_comments) == 2
        assert tc.summary == "Beginner net problem."

    def test_defaults(self):
        tc = TeachingComments()
        assert tc.correct_comment == ""
        assert tc.wrong_comments == {}
        assert tc.summary == ""

    def test_wrong_comments_validation_warns_on_bad_key(self, caplog):
        """Non-SGF keys should trigger a warning but not raise."""
        tc = TeachingComments(
            wrong_comments={"J2": "Bad key format."},
        )
        assert "J2" in tc.wrong_comments
        assert any("Unexpected wrong_comments key" in r.message for r in caplog.records)


class TestTeachingOutput:
    def test_valid_full_output(self):
        data = {
            "teaching_comments": {
                "correct_comment": "Correct.",
                "wrong_comments": {"cd": "Wrong."},
                "summary": "Summary.",
            },
            "hints": [
                "This is a net problem.",
                "Seal the escape route.",
                "Key move at {!dg}.",
            ],
        }
        output = TeachingOutput.model_validate(data)
        assert output.teaching_comments.correct_comment == "Correct."
        assert len(output.hints) == 3
        assert "{!dg}" in output.hints[2]

    def test_empty_hints_allowed(self):
        data = {
            "teaching_comments": {
                "correct_comment": "Correct.",
                "wrong_comments": {},
                "summary": "",
            },
            "hints": [],
        }
        output = TeachingOutput.model_validate(data)
        assert output.hints == []

    def test_too_many_hints_rejected(self):
        data = {
            "teaching_comments": {"correct_comment": "OK"},
            "hints": ["a", "b", "c", "d"],  # max 3
        }
        with pytest.raises(Exception):
            TeachingOutput.model_validate(data)

    def test_model_dump_roundtrip(self):
        output = TeachingOutput(
            teaching_comments=TeachingComments(
                correct_comment="Test.",
                wrong_comments={"ab": "Fail."},
                summary="S.",
            ),
            hints=["H1", "H2", "H3"],
        )
        data = output.model_dump()
        restored = TeachingOutput.model_validate(data)
        assert restored.teaching_comments.correct_comment == "Test."
        assert restored.hints == ["H1", "H2", "H3"]


class TestParseLlmResponse:
    def test_valid_response(self):
        data = {
            "teaching_comments": {
                "correct_comment": "Good move.",
                "wrong_comments": {"cd": "Bad."},
                "summary": "Net problem.",
            },
            "hints": ["Net.", "Seal escape.", "At {!dg}."],
        }
        result = parse_llm_response(data)
        assert isinstance(result, TeachingOutput)
        assert result.teaching_comments.correct_comment == "Good move."

    def test_missing_teaching_comments_raises(self):
        with pytest.raises(Exception):
            parse_llm_response({"hints": ["a", "b", "c"]})

    def test_extra_fields_ignored(self):
        data = {
            "teaching_comments": {
                "correct_comment": "OK.",
                "wrong_comments": {},
                "summary": "",
            },
            "hints": [],
            "extra_field": "should be ignored",
        }
        result = parse_llm_response(data)
        assert result.teaching_comments.correct_comment == "OK."
