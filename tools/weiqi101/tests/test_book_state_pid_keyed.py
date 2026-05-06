"""Tests for the pid-keyed positions[] invariant (schema v5).

These tests pin down the contract that ``pid`` is the natural key in
``book.json`` ``positions[]`` and that captured/external/pending status
follows the pid across upstream reorderings.

Regression background: prior to schema v5, the per-capture handler
matched by ``global_pos`` first and would silently rewrite the pid of
whatever entry sat at that pos. When 101weiqi reordered chapter pids
between two manifest POSTs, the browser's stale ``global_pos`` clobbered
an unrelated entry, leaving the captured pid duplicated in
``positions[]`` (one stale "pending", one wrongly-slotted "captured")
and the chapter completion counters wrong.

See ``/memories/repo/weiqi101-browser-capture.md`` for the broader
discovery / capture model these tests exercise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.weiqi101 import book_state


def _seed_state(book_id: int = 9100) -> dict:
    """Build a minimal book.json dict with two chapters."""
    data = book_state.initialize(book_id, book_name="Test")
    data["chapters"] = [
        book_state._normalize_chapter({
            "chapter_id": 100,
            "chapter_number": 1,
            "name": "A",
            "puzzle_ids": [11, 12, 13],
        }),
        book_state._normalize_chapter({
            "chapter_id": 101,
            "chapter_number": 2,
            "name": "B",
            "puzzle_ids": [21, 22, 23],
        }),
    ]
    data["positions"] = [
        {"pos": 1, "pid": 11, "chapter_number": 1, "chapter_position": 1, "status": "pending"},
        {"pos": 2, "pid": 12, "chapter_number": 1, "chapter_position": 2, "status": "pending"},
        {"pos": 3, "pid": 13, "chapter_number": 1, "chapter_position": 3, "status": "pending"},
        {"pos": 4, "pid": 21, "chapter_number": 2, "chapter_position": 1, "status": "pending"},
        {"pos": 5, "pid": 22, "chapter_number": 2, "chapter_position": 2, "status": "pending"},
        {"pos": 6, "pid": 23, "chapter_number": 2, "chapter_position": 3, "status": "pending"},
    ]
    return data


# ---------------------------------------------------------------------------
# dedupe_positions
# ---------------------------------------------------------------------------


class TestDedupePositions:
    def test_noop_on_unique_pids(self):
        data = _seed_state()
        removed = book_state.dedupe_positions(data)
        assert removed == 0
        assert len(data["positions"]) == 6

    def test_collapses_duplicate_keeping_higher_status(self):
        data = _seed_state()
        # Inject the exact corruption pattern observed in book 75592:
        # pid 12 appears twice — once stale "pending", once wrongly
        # slotted "captured" by the legacy pos-first matcher.
        data["positions"].append({
            "pos": 99, "pid": 12,
            "chapter_number": 1, "chapter_position": 99,
            "status": "captured", "file": "ch01_099_test_12.sgf",
        })
        removed = book_state.dedupe_positions(data)
        assert removed == 1
        survivors = [p for p in data["positions"] if p["pid"] == 12]
        assert len(survivors) == 1
        assert survivors[0]["status"] == "captured"
        assert survivors[0]["file"] == "ch01_099_test_12.sgf"

    def test_priority_external_over_pending(self):
        data = _seed_state()
        data["positions"].append({
            "pos": 50, "pid": 21,
            "chapter_number": 2, "chapter_position": 1,
            "status": "external", "ref": "qday/2024/01/foo.sgf",
        })
        book_state.dedupe_positions(data)
        survivor = next(p for p in data["positions"] if p["pid"] == 21)
        assert survivor["status"] == "external"
        assert survivor["ref"] == "qday/2024/01/foo.sgf"

    def test_priority_captured_over_external(self):
        data = _seed_state()
        # Mark the canonical entry external first.
        for p in data["positions"]:
            if p["pid"] == 22:
                p["status"] = "external"
                p["ref"] = "qday/2024/02/bar.sgf"
        # Then a duplicate captured entry arrives.
        data["positions"].append({
            "pos": 51, "pid": 22,
            "chapter_number": 2, "chapter_position": 2,
            "status": "captured", "file": "ch02_002_test_22.sgf",
        })
        book_state.dedupe_positions(data)
        survivor = next(p for p in data["positions"] if p["pid"] == 22)
        assert survivor["status"] == "captured"
        assert survivor["file"] == "ch02_002_test_22.sgf"


# ---------------------------------------------------------------------------
# apply_capture
# ---------------------------------------------------------------------------


class TestApplyCapture:
    def test_marks_existing_pid_captured(self):
        data = _seed_state()
        entry = book_state.apply_capture(
            data, pid=12, file="ch01_002_test_12.sgf",
            chapter_number=1, chapter_position=2, chapter_name="A",
        )
        assert entry is not None
        assert entry["status"] == "captured"
        assert entry["file"] == "ch01_002_test_12.sgf"
        # No duplicate.
        assert sum(1 for p in data["positions"] if p["pid"] == 12) == 1

    def test_does_not_overwrite_pid_on_pos_collision(self):
        """The legacy bug: a capture POST with stale global_pos=4 (pid 21)
        but actually for puzzle 12 must NOT rewrite the pid of the entry
        at pos=4. apply_capture is pid-keyed, so this is structurally
        impossible — we just assert the pid 21 entry is untouched.
        """
        data = _seed_state()
        # Simulate: capture for pid 12 arrives. apply_capture finds
        # entry by pid and ignores global_pos entirely.
        book_state.apply_capture(
            data, pid=12, file="ch01_002_test_12.sgf",
            chapter_number=1, chapter_position=2,
        )
        pid21 = next(p for p in data["positions"] if p["pid"] == 21)
        assert pid21["status"] == "pending"
        assert "file" not in pid21
        assert pid21["chapter_position"] == 1

    def test_appends_new_entry_for_unknown_pid(self):
        data = _seed_state()
        before = len(data["positions"])
        entry = book_state.apply_capture(
            data, pid=99999, file="ch01_099_test_99999.sgf",
            chapter_number=1, chapter_position=99, chapter_name="A",
        )
        assert entry is not None
        assert entry["pid"] == 99999
        assert entry["status"] == "captured"
        assert entry["pos"] == 7  # max(1..6) + 1
        assert len(data["positions"]) == before + 1

    def test_drops_ref_when_capturing(self):
        data = _seed_state()
        for p in data["positions"]:
            if p["pid"] == 13:
                p["status"] = "external"
                p["ref"] = "qday/2024/01/foo.sgf"
        book_state.apply_capture(
            data, pid=13, file="ch01_003_test_13.sgf",
        )
        entry = next(p for p in data["positions"] if p["pid"] == 13)
        assert entry["status"] == "captured"
        assert entry["file"] == "ch01_003_test_13.sgf"
        assert "ref" not in entry

    def test_preserves_chapter_context_when_already_set(self):
        """apply_capture must not overwrite chapter coords established by
        manifest discovery — manifest is the source of truth there."""
        data = _seed_state()
        book_state.apply_capture(
            data, pid=12, file="ch01_002_test_12.sgf",
            # Capture handler reports stale ch_pos 99, but manifest
            # already wrote 2.
            chapter_number=1, chapter_position=99, chapter_name="A",
        )
        entry = next(p for p in data["positions"] if p["pid"] == 12)
        assert entry["chapter_position"] == 2

    def test_invalid_pid_returns_none(self):
        data = _seed_state()
        assert book_state.apply_capture(data, pid="abc", file="x.sgf") is None


# ---------------------------------------------------------------------------
# carry_forward_capture_state
# ---------------------------------------------------------------------------


class TestCarryForwardCaptureState:
    def test_preserves_captured_when_manifest_rebuilds(self):
        data = _seed_state()
        # Capture pid 12.
        book_state.apply_capture(
            data, pid=12, file="ch01_002_test_12.sgf",
        )
        # Manifest rebuilds — fresh canonical positions list comes from
        # _generate_positions, which seeds from disk only. Simulate the
        # case where the rebuild missed the disk file (or chapter was
        # reordered): the new entry for pid 12 is "pending".
        new_positions = [
            {"pos": 1, "pid": 11, "chapter_number": 1, "chapter_position": 1, "status": "pending"},
            {"pos": 2, "pid": 12, "chapter_number": 1, "chapter_position": 2, "status": "pending"},
            {"pos": 3, "pid": 13, "chapter_number": 1, "chapter_position": 3, "status": "pending"},
        ]
        merged = book_state.carry_forward_capture_state(data, new_positions)
        pid12 = next(p for p in merged if p["pid"] == 12)
        assert pid12["status"] == "captured"
        assert pid12["file"] == "ch01_002_test_12.sgf"

    def test_preserves_external_ref_when_manifest_rebuilds(self):
        data = _seed_state()
        for p in data["positions"]:
            if p["pid"] == 23:
                p["status"] = "external"
                p["ref"] = "qday/2024/03/baz.sgf"
        new_positions = [
            {"pos": 1, "pid": 23, "chapter_number": 2, "chapter_position": 3, "status": "pending"},
        ]
        merged = book_state.carry_forward_capture_state(data, new_positions)
        assert merged[0]["status"] == "external"
        assert merged[0]["ref"] == "qday/2024/03/baz.sgf"

    def test_does_not_demote_captured_to_external(self):
        data = _seed_state()
        book_state.apply_capture(data, pid=12, file="ch01_002_test_12.sgf")
        # Rebuild seeds pid 12 as external (e.g. global index hit).
        new_positions = [
            {"pos": 2, "pid": 12, "chapter_number": 1, "chapter_position": 2,
             "status": "external", "ref": "qday/2024/01/foo.sgf"},
        ]
        merged = book_state.carry_forward_capture_state(data, new_positions)
        assert merged[0]["status"] == "captured"
        assert merged[0]["file"] == "ch01_002_test_12.sgf"

    def test_drops_pids_no_longer_in_chapters(self):
        """If upstream removed a pid from the chapter, the new positions
        list won't include it. We must not resurrect it from old state.
        """
        data = _seed_state()
        new_positions = [
            {"pos": 1, "pid": 11, "chapter_number": 1, "chapter_position": 1, "status": "pending"},
        ]
        merged = book_state.carry_forward_capture_state(data, new_positions)
        assert [p["pid"] for p in merged] == [11]


# ---------------------------------------------------------------------------
# Integration: stale-pos capture race (the original 75592 bug)
# ---------------------------------------------------------------------------


class TestStalePosCaptureRace:
    """End-to-end reproduction of the chapter-reordering corruption.

    Sequence:
      1. Initial manifest POST → positions[] has pid X at pos 314, ch_pos 16.
      2. Browser captures X, sends global_pos=314 (correct at the time).
      3. Upstream reorders chapter; manifest POST #2 → pid X now at
         pos 312, ch_pos 14. positions[] is rebuilt fresh.
      4. A delayed capture POST for pid X arrives with stale global_pos=314.

    Under the legacy pos-first matcher, step 4 would corrupt the entry
    at pos 314 (now pid Y) by silently rewriting its pid to X. Under the
    pid-keyed v5 design, step 4 finds pid X at its new pos (312) and
    leaves pid Y untouched.
    """

    def test_no_pid_corruption_on_stale_pos(self):
        data = _seed_state()
        # Step 2: capture pid 12 normally.
        book_state.apply_capture(data, pid=12, file="ch01_002_test_12.sgf")
        # Step 3: simulate upstream reorder — pid 12 now where pid 13 was.
        data["positions"] = [
            {"pos": 1, "pid": 11, "chapter_number": 1, "chapter_position": 1, "status": "pending"},
            {"pos": 2, "pid": 13, "chapter_number": 1, "chapter_position": 2, "status": "pending"},
            {"pos": 3, "pid": 12, "chapter_number": 1, "chapter_position": 3,
             "status": "captured", "file": "ch01_002_test_12.sgf"},
        ]
        # Step 4: delayed second capture for pid 12 arrives. Under the
        # new contract apply_capture finds pid 12 by pid (now at pos 3)
        # and updates that entry. Pid 13 at pos 2 is untouched.
        book_state.apply_capture(
            data, pid=12, file="ch01_003_test_12.sgf",
            chapter_number=1, chapter_position=3,
        )
        pid12 = [p for p in data["positions"] if p["pid"] == 12]
        pid13 = [p for p in data["positions"] if p["pid"] == 13]
        assert len(pid12) == 1
        assert len(pid13) == 1
        assert pid13[0]["status"] == "pending"
        assert "file" not in pid13[0]
        assert pid12[0]["status"] == "captured"


# ---------------------------------------------------------------------------
# reconcile_book_index — pid-first matching
# ---------------------------------------------------------------------------


class TestReconcilePidFirst:
    def test_matches_disk_files_by_pid(self, tmp_path: Path):
        from tools.weiqi101.receiver import reconcile_book_index

        book_dir = tmp_path / "books" / "9200-test"
        (book_dir / "sgf").mkdir(parents=True)
        # Write three SGFs on disk. Chapter mode filenames.
        for ch_pos, pid in [(1, 11), (2, 12), (3, 13)]:
            (book_dir / "sgf" / f"ch01_{ch_pos:03d}_test_{pid}.sgf").write_text(
                "(;FF[4]GM[1]SZ[19])", encoding="utf-8"
            )
        # Seed book.json with all entries pending.
        data = _seed_state(book_id=9200)
        book_state.save(book_dir, data)

        summary = reconcile_book_index(book_dir)
        assert summary["newly_captured"] == 3
        assert summary["already_correct"] == 0
        assert summary["orphan_files"] == 0
        assert summary["duplicates_removed"] == 0

        loaded = book_state.load(book_dir)
        captured = {p["pid"]: p for p in loaded["positions"] if p.get("status") == "captured"}
        assert set(captured) == {11, 12, 13}

    def test_collapses_legacy_duplicates(self, tmp_path: Path):
        """A book.json that was corrupted by the pre-v5 race must be
        cleaned up by reconcile."""
        from tools.weiqi101.receiver import reconcile_book_index

        book_dir = tmp_path / "books" / "9201-test"
        (book_dir / "sgf").mkdir(parents=True)
        (book_dir / "sgf" / "ch01_002_test_12.sgf").write_text(
            "(;FF[4]GM[1]SZ[19])", encoding="utf-8"
        )

        data = _seed_state(book_id=9201)
        # Inject the duplicate-pid corruption.
        data["positions"].append({
            "pos": 99, "pid": 12,
            "chapter_number": 1, "chapter_position": 99,
            "status": "captured", "file": "ch01_002_test_12.sgf",
        })
        book_state.save(book_dir, data)

        summary = reconcile_book_index(book_dir)
        assert summary["duplicates_removed"] >= 1

        loaded = book_state.load(book_dir)
        pid12_entries = [p for p in loaded["positions"] if p["pid"] == 12]
        assert len(pid12_entries) == 1
        assert pid12_entries[0]["status"] == "captured"

    def test_orphan_file_reported(self, tmp_path: Path):
        from tools.weiqi101.receiver import reconcile_book_index

        book_dir = tmp_path / "books" / "9202-test"
        (book_dir / "sgf").mkdir(parents=True)
        # File on disk for a pid not in the manifest.
        (book_dir / "sgf" / "ch99_001_unknown_99999.sgf").write_text(
            "(;FF[4]GM[1]SZ[19])", encoding="utf-8"
        )

        data = _seed_state(book_id=9202)
        book_state.save(book_dir, data)

        summary = reconcile_book_index(book_dir)
        assert summary["orphan_files"] == 1
        assert summary["newly_captured"] == 0
