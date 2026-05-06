"""Tests for chapter skip-state machinery (Option 3 / schema v5).

Covers:
- ``mark_skip`` / ``clear_skip`` happy paths and missing-chapter cases
- ``record_empty_attempt`` cooldown guard (no double-bump in same window)
- ``record_empty_attempt`` auto-flip to ``skip_status="auto_empty"``
- ``merge_discovery_state`` preserves server-managed skip fields when
  the userscript posts a fresh chapter list (which does not include them)
- ``chapter_skip_states`` projection shape
"""

from __future__ import annotations

import pytest

from tools.weiqi101 import book_state


def _make_state(chapters):
    data = book_state.initialize(book_id=999, book_name="Test Book")
    data["chapters"] = [book_state._normalize_chapter(c) for c in chapters]
    return data


def test_normalize_chapter_adds_skip_slots():
    ch = book_state._normalize_chapter({"chapter_id": 1, "chapter_number": 1})
    assert ch["skip_status"] is None
    assert ch["skip_reason"] is None
    assert ch["skip_marked_at"] is None
    assert ch["empty_attempts"] == 0
    assert ch["last_attempt_at"] is None


def test_normalize_chapter_drops_puzzle_positions_by_default(monkeypatch):
    monkeypatch.delenv(book_state.PUZZLE_POSITIONS_ENV_VAR, raising=False)
    ch = book_state._normalize_chapter({
        "chapter_id": 42,
        "chapter_number": 7,
        "puzzle_positions": {"101": 1, "102": 2},
    })

    assert "puzzle_positions" not in ch


def test_normalize_chapter_preserves_puzzle_positions_when_toggle_enabled(monkeypatch):
    monkeypatch.setenv(book_state.PUZZLE_POSITIONS_ENV_VAR, "1")
    ch = book_state._normalize_chapter({
        "chapter_id": 42,
        "chapter_number": 7,
        "puzzle_positions": {"102": 2, "101": 1},
    })

    assert ch["puzzle_positions"] == {"101": 1, "102": 2}


def test_normalize_chapter_keeps_pending_before_puzzle_positions_and_puzzle_ids_last(monkeypatch):
    monkeypatch.setenv(book_state.PUZZLE_POSITIONS_ENV_VAR, "1")
    data = book_state.initialize(book_id=999, book_name="Test Book")
    data["chapters"] = [
        {
            "chapter_id": 42,
            "chapter_number": 7,
            "name": "Example",
            "site_chapter_number": 7,
            "puzzle_ids": [101, 102],
            "puzzle_positions": {"101": 1, "102": 2},
            "scraped_pages": [1],
            "declared_count": 2,
            "total": 2,
            "captured": 1,
            "external": 0,
            "pending": 1,
            "custom_flag": True,
        },
    ]
    serialized = book_state._serialize(data)
    chapter_line = next(
        line.strip()
        for line in serialized.splitlines()
        if '"chapter_id": 42' in line
    )

    assert '"pending": 1' in chapter_line
    assert '"puzzle_positions": {"101": 1, "102": 2}' in chapter_line
    assert chapter_line.endswith('"puzzle_ids": [101, 102]}')
    assert chapter_line.index('"pending": 1') < chapter_line.index('"puzzle_positions": {"101": 1, "102": 2}')
    assert chapter_line.index('"pending": 1') < chapter_line.index('"puzzle_ids": [101, 102]')
    assert chapter_line.index('"custom_flag": true') < chapter_line.index('"puzzle_ids": [101, 102]')


def test_mark_and_clear_skip_by_chapter_id():
    data = _make_state([{"chapter_id": 42, "chapter_number": 5, "name": "x"}])
    ch = book_state.mark_skip(
        data, chapter_id=42, status="manual", reason="broken on site",
    )
    assert ch is not None
    assert ch["skip_status"] == "manual"
    assert ch["skip_reason"] == "broken on site"
    assert ch["skip_marked_at"] is not None

    cleared = book_state.clear_skip(data, chapter_id=42)
    assert cleared is not None
    assert cleared["skip_status"] is None
    assert cleared["empty_attempts"] == 0


def test_mark_skip_by_chapter_number():
    data = _make_state([{"chapter_id": 10, "chapter_number": 3}])
    ch = book_state.mark_skip(data, chapter_number=3, status="manual")
    assert ch is not None and ch["chapter_id"] == 10


def test_mark_skip_invalid_status_raises():
    data = _make_state([{"chapter_id": 1, "chapter_number": 1}])
    with pytest.raises(ValueError):
        book_state.mark_skip(data, chapter_id=1, status="not-a-real-status")


def test_mark_skip_missing_chapter_returns_none():
    data = _make_state([{"chapter_id": 1, "chapter_number": 1}])
    assert book_state.mark_skip(data, chapter_id=99, status="manual") is None
    assert book_state.clear_skip(data, chapter_id=99) is None


def test_record_empty_attempt_cooldown_blocks_double_bump():
    """Two attempts within the cooldown window should count as one."""
    data = _make_state([{"chapter_id": 1, "chapter_number": 1}])
    ch1, just1 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=60,
    )
    assert ch1["empty_attempts"] == 1
    assert just1 is False

    # Second call immediately after \u2014 inside the 60s cooldown.
    ch2, just2 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=60,
    )
    assert ch2["empty_attempts"] == 1, "cooldown must suppress the bump"
    assert just2 is False


def test_record_empty_attempt_flips_to_auto_empty_at_threshold():
    """3rd post-cooldown attempt should auto-flag the chapter."""
    data = _make_state([{"chapter_id": 1, "chapter_number": 1}])

    # Use cooldown_seconds=0 so each call increments unconditionally.
    ch, j1 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=0,
    )
    assert (ch["empty_attempts"], j1) == (1, False)
    assert ch["skip_status"] is None

    ch, j2 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=0,
    )
    assert (ch["empty_attempts"], j2) == (2, False)
    assert ch["skip_status"] is None

    ch, j3 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=0,
    )
    assert ch["empty_attempts"] == 3
    assert j3 is True, "transition to auto_empty must surface to caller"
    assert ch["skip_status"] == "auto_empty"
    assert ch["skip_marked_at"] is not None
    assert "auto" in (ch["skip_reason"] or "")

    # A subsequent attempt must NOT re-trigger the just_skipped flag.
    ch, j4 = book_state.record_empty_attempt(
        data, chapter_id=1, threshold=3, cooldown_seconds=0,
    )
    assert j4 is False
    assert ch["skip_status"] == "auto_empty"


def test_record_empty_attempt_missing_chapter():
    data = _make_state([{"chapter_id": 1, "chapter_number": 1}])
    ch, just = book_state.record_empty_attempt(data, chapter_id=99)
    assert ch is None and just is False


def test_chapter_skip_states_projection():
    data = _make_state([
        {"chapter_id": 1, "chapter_number": 1},
        {"chapter_id": 2, "chapter_number": 2},
    ])
    book_state.mark_skip(data, chapter_id=2, status="manual", reason="x")
    states = book_state.chapter_skip_states(data)
    assert len(states) == 2
    by_id = {s["chapter_id"]: s for s in states}
    assert by_id[1]["skip_status"] is None
    assert by_id[2]["skip_status"] == "manual"
    assert by_id[2]["skip_reason"] == "x"
    # Projection must include empty_attempts so the userscript can show it.
    assert "empty_attempts" in by_id[1]


def test_merge_discovery_state_preserves_server_skip_fields():
    """When userscript posts a fresh chapter list, server-managed skip
    fields (skip_status, skip_reason, empty_attempts, last_attempt_at)
    must be preserved \u2014 the client never sees them so it can't echo
    them back, and a naive overwrite would silently un-skip a chapter.
    """
    prior = book_state.initialize(book_id=42, book_name="Book")
    prior["chapters"] = [
        book_state._normalize_chapter({
            "chapter_id": 7,
            "chapter_number": 18,
            "puzzle_ids": [],
        }),
    ]
    book_state.mark_skip(prior, chapter_id=7, status="auto_empty", reason="r")
    prior["chapters"][0]["empty_attempts"] = 5
    prior["chapters"][0]["last_attempt_at"] = "2026-04-24T10:00:00Z"

    # Userscript posts the same chapter list with NO skip fields and
    # an updated puzzle_ids list (simulating a fresh discovery sweep).
    discovery_state = {
        "book_id": 42,
        "book_name": "Book",
        "phase": "chapter_puzzles",
        "current_chapter_idx": 0,
        "current_page": 1,
        "chapters": [
            {
                "chapter_id": 7,
                "chapter_number": 18,
                "puzzle_ids": [101, 102],  # fresh data from client
            },
        ],
    }

    merged = book_state.merge_discovery_state(prior, discovery_state)
    ch = merged["chapters"][0]
    assert ch["puzzle_ids"] == [101, 102], "client data must still flow through"
    assert ch["skip_status"] == "auto_empty"
    assert ch["skip_reason"] == "r"
    assert ch["empty_attempts"] == 5
    assert ch["last_attempt_at"] == "2026-04-24T10:00:00Z"


def test_schema_version_bumped_to_5():
    assert book_state.SCHEMA_VERSION == 5
    fresh = book_state.initialize(book_id=1, book_name="x")
    assert fresh["schema_version"] == 5
