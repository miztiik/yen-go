"""Concurrency regression tests for ``book_state.save`` / ``book_lock``.

Background: under ThreadingHTTPServer, concurrent ``/capture``,
``/book/manifest``, and ``/book/discovery/progress`` handlers were
performing un-serialised load → mutate → save sequences against the
same ``book.json``. Two failure modes resulted:

1. Torn writes — both threads wrote to the SAME tmp filename
   (``book.json.tmp``), interleaved their bytes, and ``replace()``
   published a half-A / half-B file. The next ``load()`` raised
   ``UnicodeDecodeError`` mid-CJK and crashed every subsequent
   handler that touched the book until manual repair. Real-world
   trigger: book 201, 2026-04-30, byte 0xb4 at position 2,530,556.

2. Lost updates — both threads loaded the same state, mutated
   disjoint fields, both saved; second writer silently dropped the
   first writer's mutation.

The structural fix (this commit) introduces:

  - ``book_state.book_lock(book_dir)`` — per-book ``threading.Lock``
    held across the full RMW.
  - Unique tmp filename per (pid, thread) inside ``save()``.
  - ``load()`` quarantines corrupt files instead of raising.

These tests pin down all three behaviours.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from tools.weiqi101 import book_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(tmp_path: Path, book_id: int = 9200) -> Path:
    """Initialise a book dir with a minimal valid book.json."""
    book_dir = tmp_path / f"{book_id}-test"
    data = book_state.initialize(book_id, book_name="Concurrency Test")
    book_state.save(book_dir, data)
    return book_dir


# ---------------------------------------------------------------------------
# 1. Torn writes — concurrent saves never produce a corrupt file.
# ---------------------------------------------------------------------------

def test_concurrent_saves_never_tear_the_file(tmp_path: Path) -> None:
    """100 threads each running a full RMW under ``book_lock`` must end
    with a parseable file. Without per-thread tmp filenames AND the
    lock, this test reproduces the byte-0xb4 corruption.
    """
    book_dir = _seed(tmp_path)
    # Pre-seed with a moderately large CJK payload so a torn write is
    # likely to slice a multi-byte UTF-8 sequence.
    data = book_state.load(book_dir)
    data["chapters"] = [
        {
            "chapter_id": i,
            "chapter_number": i,
            "name": "测试章节" * 100,  # ~1.2 KB CJK per chapter
            "puzzle_ids": list(range(i * 100, i * 100 + 50)),
        }
        for i in range(50)
    ]
    book_state.save(book_dir, data)

    errors: list[BaseException] = []

    def writer(idx: int) -> None:
        try:
            for _ in range(5):
                with book_state.book_lock(book_dir):
                    state_data = book_state.load(book_dir)
                    state_data.setdefault("counters", {})[str(idx)] = (
                        state_data.get("counters", {}).get(str(idx), 0) + 1
                    )
                    book_state.save(book_dir, state_data)
        except BaseException as e:  # pragma: no cover - propagated below
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writer thread raised: {errors!r}"

    # File must be parseable JSON (no torn write).
    final = book_state.load(book_dir)
    assert final, "file must be loadable after concurrent writes"

    # And under the lock, every increment must have been preserved
    # (no lost updates).
    counters = final.get("counters", {})
    assert sorted(counters.keys(), key=int) == [str(i) for i in range(20)]
    assert all(v == 5 for v in counters.values()), (
        f"lost updates detected: {counters!r}"
    )


# ---------------------------------------------------------------------------
# 2. Unique tmp filenames — save() must not reuse the legacy shared
#    "book.json.tmp" name. (Two writers to the same tmp file produce
#    the byte-0xb4 corruption from the production trace; with unique
#    tmp names per (pid, thread) this whole class of bug is impossible
#    even if a future caller forgets ``book_lock``.)
# ---------------------------------------------------------------------------

def test_save_uses_unique_tmp_filename_per_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spy on ``Path.write_text`` to confirm save() never picks the
    legacy shared "book.json.tmp" name and that distinct threads pick
    distinct names. We hold the per-book lock around the writers so the
    OS-level concurrent-rename race (Windows EACCES) is out of scope —
    that race is the lock's job, not ``save()``'s.
    """
    book_dir = _seed(tmp_path)

    captured_tmp_names: list[str] = []
    original_write_text = Path.write_text

    def spy_write_text(self: Path, data: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self.name.startswith("book.json.") and self.name.endswith(".tmp"):
            captured_tmp_names.append(self.name)
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    def writer() -> None:
        for _ in range(3):
            with book_state.book_lock(book_dir):
                book_state.save(book_dir, {"book_id": 1, "marker": "x"})

    threads = [threading.Thread(target=writer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The canonical name must NEVER be the legacy shared "book.json.tmp".
    assert "book.json.tmp" not in captured_tmp_names, (
        "save() must not reuse the legacy shared tmp filename"
    )
    # Distinct threads must have produced distinct tmp names.
    distinct = set(captured_tmp_names)
    assert len(distinct) >= 4, (
        f"expected per-thread tmp names, got {captured_tmp_names!r}"
    )


# ---------------------------------------------------------------------------
# 3. Quarantine — a corrupt book.json must not crash load(); it must
#    be moved aside and an empty dict returned so callers can rebuild.
# ---------------------------------------------------------------------------

def test_load_quarantines_corrupt_utf8_file(tmp_path: Path) -> None:
    """Reproduces the production crash: write bytes that are valid up
    to a CJK character then truncated mid-sequence. ``load()`` must
    rotate the file aside and return ``{}`` rather than raise.
    """
    book_dir = tmp_path / "9300-corrupt"
    book_dir.mkdir()
    target = book_dir / book_state.BOOK_STATE_FILENAME
    # Valid JSON prefix, then a bare 0xb4 continuation byte (the exact
    # byte from the production trace).
    target.write_bytes(b'{"book_id": 9300, "name": "tear-here-\xb4"}')

    result = book_state.load(book_dir)

    assert result == {}, "corrupt file must yield empty dict, not raise"
    assert not target.exists(), "corrupt file must be quarantined"
    quarantined = list(book_dir.glob(f"{book_state.BOOK_STATE_FILENAME}.corrupt-*"))
    assert len(quarantined) == 1, (
        f"expected exactly one quarantine file, got {quarantined!r}"
    )


def test_load_swallows_json_decode_error_with_quarantine(
    tmp_path: Path,
) -> None:
    """``JSONDecodeError`` (e.g. truncated valid UTF-8) is also quarantined."""
    book_dir = tmp_path / "9301-bad-json"
    book_dir.mkdir()
    target = book_dir / book_state.BOOK_STATE_FILENAME
    target.write_text('{"book_id": 9301, "incomplete":', encoding="utf-8")

    result = book_state.load(book_dir)

    assert result == {}
    assert not target.exists()
    assert any(
        p.name.startswith(f"{book_state.BOOK_STATE_FILENAME}.corrupt-")
        for p in book_dir.iterdir()
    )


# ---------------------------------------------------------------------------
# 4. book_lock semantics — same dir serialises, different dirs don't.
# ---------------------------------------------------------------------------

def test_book_lock_serialises_same_dir(tmp_path: Path) -> None:
    """Two ``with book_lock(d):`` blocks against the same dir must not
    overlap; against different dirs they must run independently.
    """
    dir_a = _seed(tmp_path / "A", book_id=9400)
    dir_b = _seed(tmp_path / "B", book_id=9401)

    # Same-dir: second acquire blocks until first releases.
    lock_a1 = book_state._lock_for(dir_a)
    lock_a2 = book_state._lock_for(dir_a)
    assert lock_a1 is lock_a2, "same dir must yield the same lock object"

    # Different dirs: distinct locks.
    lock_b = book_state._lock_for(dir_b)
    assert lock_a1 is not lock_b, "different dirs must yield different locks"

    # Functional check: a writer holding dir_a's lock does not block
    # a writer working on dir_b.
    started_b = threading.Event()
    finished_b = threading.Event()

    with book_state.book_lock(dir_a):
        def b_worker() -> None:
            with book_state.book_lock(dir_b):
                started_b.set()
                book_state.save(dir_b, {"book_id": 9401, "n": 1})
                finished_b.set()

        t = threading.Thread(target=b_worker)
        t.start()
        # dir_b's worker should complete even while we hold dir_a.
        assert finished_b.wait(timeout=2.0), (
            "lock on dir_a must not block work on dir_b"
        )
        t.join(timeout=1.0)
