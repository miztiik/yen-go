from __future__ import annotations

import json
from pathlib import Path

from tools.weiqi101 import inventory


def _make_corpus(root: Path) -> None:
    """Synthetic corpus exercising every location + an inter-location dup.

    Layout:
      books/1-foo/sgf/ch01_001_slug_100.sgf   (pid 100, books-only)
      books/1-foo/sgf/ch01_002_slug_200.sgf   (pid 200, also in qday)
      books/2-bar/sgf/ch01_001_slug_300.sgf   (pid 300, also in books/1-foo)
      books/1-foo/sgf/ch01_003_slug_300.sgf   (pid 300 dup within books)
      qday/2018/03/15/4/20180315-4-200.sgf    (pid 200, dup with books)
      qday/2018/03/15/5/20180315-5-400.sgf    (pid 400, qday-only)
      sgf/batch-001/500.sgf                   (pid 500, sgf-only)
      sgf/batch-001/100.sgf                   (pid 100, dup with books)
      books/1-foo/sgf/junk-no-pid.sgf         (unparsable)
    """
    files = [
        "books/1-foo/sgf/ch01_001_slug_100.sgf",
        "books/1-foo/sgf/ch01_002_slug_200.sgf",
        "books/2-bar/sgf/ch01_001_slug_300.sgf",
        "books/1-foo/sgf/ch01_003_slug_300.sgf",
        "qday/2018/03/15/4/20180315-4-200.sgf",
        "qday/2018/03/15/5/20180315-5-400.sgf",
        "sgf/batch-001/500.sgf",
        "sgf/batch-001/100.sgf",
        "books/1-foo/sgf/junk-no-pid.sgf",
    ]
    for rel in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("(;FF[4]GM[1]SZ[19])", encoding="utf-8")


def test_scan_counts_and_overlap(tmp_path: Path):
    _make_corpus(tmp_path)
    payload = inventory.scan(tmp_path)
    inv = payload["inventory"]

    assert inv["schema_version"] == 1
    totals = inv["totals"]
    assert totals["files"] == 9
    assert totals["files_unparsable"] == 1
    # Unique pids: 100, 200, 300, 400, 500 = 5
    assert totals["unique_pids"] == 5
    # Parsed files = 8; duplicates = 8 - 5 = 3
    assert totals["duplicate_files"] == 3
    assert totals["overlap_pct"] == round(3 / 8 * 100.0, 2)


def test_unique_sgf_tiebreaker_books_over_qday_over_sgf(tmp_path: Path):
    _make_corpus(tmp_path)
    payload = inventory.scan(tmp_path)
    lines = payload["unique_sgf_lines"]

    # Header + 5 unique pids.
    assert lines[0].startswith("# unique-sgf v1")
    assert "tiebreak=books>qday>sgf" in lines[0]
    assert len(lines) == 1 + 5

    # Sorted by pid ascending.
    body = lines[1:]
    assert body[0].endswith("_100.sgf")  # pid 100 -> books wins over sgf
    assert "books/" in body[0]
    assert body[1].endswith("_200.sgf") or body[1].endswith("-200.sgf")
    assert "books/" in body[1]  # books wins over qday
    # pid 300 lives in two book dirs; lexicographic path tiebreak picks 1-foo.
    assert "books/1-foo" in body[2]
    # pid 400 is qday-only.
    assert "qday/" in body[3] and body[3].endswith("-400.sgf")
    # pid 500 is sgf-only.
    assert body[4] == "sgf/batch-001/500.sgf"


def test_per_location_stats(tmp_path: Path):
    _make_corpus(tmp_path)
    payload = inventory.scan(tmp_path)
    locs = payload["inventory"]["locations"]

    # Per-location ``files`` counts only files that yielded a pid;
    # the unparsable one is reported in ``totals.files_unparsable``.
    assert locs["books"]["files"] == 4
    assert locs["books"]["unique_pids"] == 3  # 100, 200, 300

    assert locs["qday"]["files"] == 2
    assert locs["qday"]["unique_pids"] == 2  # 200, 400

    assert locs["sgf"]["files"] == 2
    assert locs["sgf"]["unique_pids"] == 2  # 100, 500


def test_per_book_overlap(tmp_path: Path):
    _make_corpus(tmp_path)
    payload = inventory.scan(tmp_path)
    books = {b["dir"]: b for b in payload["inventory"]["books"]}

    # 1-foo holds {100, 200, 300}. All overlap with elsewhere
    #   100 -> sgf/, 200 -> qday/, 300 -> 2-bar.
    foo = books["1-foo"]
    assert foo["unique_pids"] == 3
    assert foo["overlap_with_corpus_pct"] == 100.0
    assert foo["novel_pct"] == 0.0
    assert foo["book_id"] == 1

    # 2-bar holds {300}, which overlaps with 1-foo.
    bar = books["2-bar"]
    assert bar["unique_pids"] == 1
    assert bar["overlap_with_corpus_pct"] == 100.0
    assert bar["book_id"] == 2


def test_write_outputs_round_trips(tmp_path: Path):
    _make_corpus(tmp_path)
    payload = inventory.scan(tmp_path)
    inventory.write_outputs(payload, tmp_path)

    inv_path = inventory.inventory_path(tmp_path)
    uniq_path = inventory.unique_sgf_path(tmp_path)
    assert inv_path.exists()
    assert uniq_path.exists()

    inv_loaded = json.loads(inv_path.read_text(encoding="utf-8"))
    assert inv_loaded["totals"]["unique_pids"] == 5

    lines = uniq_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# unique-sgf v1")
    # File count should equal header + unique pids.
    assert len(lines) == 1 + 5


def test_load_inventory_returns_none_when_missing(tmp_path: Path):
    assert inventory.load_inventory(tmp_path) is None


def test_refresh_blocking_writes_artifacts(tmp_path: Path):
    _make_corpus(tmp_path)
    inv = inventory.refresh_blocking(tmp_path)
    assert inv["totals"]["unique_pids"] == 5
    assert inventory.inventory_path(tmp_path).exists()
    assert inventory.unique_sgf_path(tmp_path).exists()


def test_skip_unparsable_files(tmp_path: Path):
    # No SGFs at all -> empty but valid inventory.
    payload = inventory.scan(tmp_path)
    inv = payload["inventory"]
    assert inv["totals"]["files"] == 0
    assert inv["totals"]["unique_pids"] == 0
    assert inv["totals"]["overlap_pct"] == 0.0
