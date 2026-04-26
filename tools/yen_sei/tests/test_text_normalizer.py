"""Tests for tools.yen_sei.governance.text_normalizer.

Each test is one real noise pattern observed in the v2.2 SFT corpus
(see IMPROVEMENT_PLAN.md §0). Inputs are verbatim from train.jsonl /
val.jsonl samples.
"""

from __future__ import annotations

import pytest

from tools.yen_sei.governance.text_normalizer import (
    broken_english_score,
    has_coordinate_leak,
    normalize_section_body,
)


# ── Boilerplate stripping ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected_substr",
    [
        ("Correct! Black has formed two eyes and is alive.", "Black has formed two eyes"),
        ("Wrong: White can easily form two eyes now.", "White can easily form two eyes"),
        ("#Correct! Black is dead.", "Black is dead"),
        ("## Correct\n\nBlack advances his position.", "Black advances his position"),
        ("(;Correct) Black 1 placement is correct.", "placement is correct"),
        ("1 diagram (;Wrong) White 2 inevitable.", "inevitable"),
        ("diagram 2 (;Correct) Black 1 placement.", "placement"),
        ("reference 1. White can capture.", "White can capture"),
    ],
)
def test_strips_boilerplate_prefixes(raw: str, expected_substr: str) -> None:
    out = normalize_section_body(raw)
    assert expected_substr in out
    # No surviving correctness shouting
    assert "correct!" not in out.lower()
    assert "wrong:" not in out.lower()
    assert "(;" not in out


def test_markdown_arrow_block_is_unwrapped() -> None:
    raw = "Correct! #Correct!\n\n**-> Black has formed two eyes and is alive.**"
    out = normalize_section_body(raw)
    assert out == "Black has formed two eyes and is alive."


def test_trailing_verdict_stripped() -> None:
    raw = "It's too bad about the two stones, but you saved the right side and won by one point.RIGHT"
    out = normalize_section_body(raw)
    assert out.endswith("by one point.")
    assert "RIGHT" not in out


# ── CN→EN markers ───────────────────────────────────────────────────────


def test_cn_marker_completed_is_stripped() -> None:
    raw = "White cannot connect (completed) and dies."
    out = normalize_section_body(raw)
    assert "(completed)" not in out
    assert "White cannot connect" in out
    assert "and dies" in out


def test_cn_marker_question_stripped() -> None:
    raw = "self must capture connect-and-die (question)?"
    out = normalize_section_body(raw)
    assert "(question)" not in out


def test_broken_english_score_counts_markers() -> None:
    bad = "enter work to this, not can avoid (adverb marker) shape form ko fight"
    score = broken_english_score(bad)
    assert score >= 2  # at least "enter work" + "(adverb marker)"


def test_broken_english_score_clean_text_zero() -> None:
    good = "The atari captures White's cutting stone and the corner is alive."
    assert broken_english_score(good) == 0


# ── Coordinate / ordinal stripping ─────────────────────────────────────


def test_coord_hint_token_stripped() -> None:
    raw = "The first move is at {!cg}."
    out = normalize_section_body(raw)
    assert "{!cg}" not in out
    assert "{cg}" not in out


def test_ordinal_move_references_stripped() -> None:
    raw = "Black 1 placement is correct, White 2 connect."
    out = normalize_section_body(raw)
    assert "Black 1" not in out
    assert "White 2" not in out
    assert "placement is correct" in out
    assert "connect" in out


def test_western_coord_replaced() -> None:
    raw = "Play at D17 to capture the corner."
    out = normalize_section_body(raw)
    assert "D17" not in out
    assert "this point" in out


def test_western_coord_lowercase_replaced() -> None:
    raw = "Black cannot d19 placement, otherwise White e19 block."
    out = normalize_section_body(raw)
    assert "d19" not in out
    assert "e19" not in out
    assert "this point" in out


def test_at_coord_phrase_replaced() -> None:
    raw = "White stones at cd point connect through."
    out = normalize_section_body(raw)
    assert "at cd point" not in out
    assert "at the vital point" in out


def test_play_coord_phrase_replaced() -> None:
    raw = "Black should play cd to capture."
    out = normalize_section_body(raw)
    assert "play cd" not in out
    assert "play here" in out


def test_has_coordinate_leak_detects_remaining() -> None:
    assert has_coordinate_leak("Black 1 to 5 captures.")
    assert has_coordinate_leak("Play at D17.")
    assert has_coordinate_leak("Hint: {!cg}")
    assert not has_coordinate_leak("Play at the vital point to capture.")


# ── Whitespace + idempotence ───────────────────────────────────────────


def test_collapses_multiple_spaces() -> None:
    raw = "Black    is   alive.\n\n\n\nGood."
    out = normalize_section_body(raw)
    assert "    " not in out
    assert "\n\n\n" not in out


def test_idempotent_on_clean_input() -> None:
    clean = "The atari captures White's cutting stone."
    once = normalize_section_body(clean)
    twice = normalize_section_body(once)
    assert once == twice == clean


def test_idempotent_on_dirty_input() -> None:
    dirty = "Correct! #Correct!\n\n**-> Black 1 placement at {!cg} is correct.**"
    once = normalize_section_body(dirty)
    twice = normalize_section_body(once)
    assert once == twice


def test_returns_empty_when_only_noise() -> None:
    raw = "Correct!"
    assert normalize_section_body(raw) == ""


def test_returns_empty_for_empty_input() -> None:
    assert normalize_section_body("") == ""
    assert normalize_section_body("   \n\n  ") == ""


# ── Real verbatim samples from the corpus ──────────────────────────────


def test_real_sample_seki_diagram() -> None:
    # From train.jsonl
    raw = (
        "9 diagram ko \n\n White immediately make 3 block also come not and (completed)."
        "by Black 4 squeeze one move then play become ko contest, White Wrong."
    )
    out = normalize_section_body(raw)
    assert "(completed)" not in out
    # Ordinal moves stripped, but core teaching phrases survive
    assert "block" in out.lower()
    assert "squeeze" in out.lower()
    assert "ko" in out.lower()


def test_real_sample_alive_template() -> None:
    raw = (
        "Correct! #Correct!\n\n"
        "**-> Black has formed two eyes and is alive.**"
    )
    out = normalize_section_body(raw)
    assert out == "Black has formed two eyes and is alive."
