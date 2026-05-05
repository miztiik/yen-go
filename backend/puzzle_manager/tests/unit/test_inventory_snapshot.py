"""Unit tests for the inventory snapshot writer (G2).

The snapshot is the contract between the pipeline (writer) and presentation
tools like pm_cockpit (reader). These tests pin the JSON shape so a
schema drift breaks fast in CI rather than silently flipping the cockpit
into a "snapshot missing" advisory state.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.puzzle_manager.inventory.snapshot import (
    INVENTORY_SNAPSHOT_FILENAME,
    write_inventory_snapshot,
)


def _seed_db(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    db = output_dir / "yengo-search.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE puzzles (
                content_hash TEXT PRIMARY KEY, batch TEXT,
                level_id INTEGER, quality INTEGER, content_type INTEGER,
                cx_depth INTEGER, cx_refutations INTEGER,
                cx_solution_len INTEGER, cx_unique_resp INTEGER
            );
            CREATE TABLE collections (
                slug TEXT PRIMARY KEY, name TEXT,
                category TEXT, puzzle_count INTEGER
            );
            CREATE TABLE daily_schedule (
                date TEXT PRIMARY KEY, version INTEGER,
                generated_at TEXT, technique TEXT, attrs TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("a" * 16, "0001", 110, 3, 1, 5, 12, 3, 2),
                ("b" * 16, "0001", 110, 4, 1, 6, 14, 4, 2),
                ("c" * 16, "0001", 150, 2, 2, 3, 8, 2, 1),
            ],
        )
        conn.executemany(
            "INSERT INTO collections VALUES (?,?,?,?)",
            [
                ("col-a", "Col A", "lnd", 2),
                ("col-b", "Col B", "shape", 1),
                ("col-c", "Col C", None, 0),  # exercises 'uncategorised' bucket
            ],
        )
        conn.execute(
            "INSERT INTO daily_schedule VALUES (?,?,?,?,?)",
            ("2026-05-05", 1, "2026-05-05T00:00:00Z", "ladder", "{}"),
        )
        conn.commit()
    return db


@pytest.mark.unit
def test_returns_none_when_no_db(tmp_path: Path) -> None:
    assert write_inventory_snapshot(tmp_path) is None
    assert not (tmp_path / INVENTORY_SNAPSHOT_FILENAME).exists()


@pytest.mark.unit
def test_writes_snapshot_with_expected_shape(tmp_path: Path) -> None:
    _seed_db(tmp_path)
    out = write_inventory_snapshot(tmp_path)
    assert out is not None
    assert out.name == INVENTORY_SNAPSHOT_FILENAME
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["puzzles_total"] == 3
    assert payload["collections_total"] == 3
    assert payload["daily_schedule_total"] == 1
    assert payload["by_level_id"] == {"110": 2, "150": 1}
    assert payload["by_content_type"] == {"1": 2, "2": 1}
    assert payload["by_collection_category"] == {
        "lnd": 1, "shape": 1, "uncategorised": 1
    }
    assert payload["schema_version"] is None  # no db-version.json yet
    assert payload["db_version"] is None


@pytest.mark.unit
def test_includes_db_version_when_file_present(tmp_path: Path) -> None:
    _seed_db(tmp_path)
    (tmp_path / "db-version.json").write_text(
        json.dumps({"schema_version": 2, "db_version": "20260505-abc"}),
        encoding="utf-8",
    )
    out = write_inventory_snapshot(tmp_path)
    assert out is not None
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["db_version"] == "20260505-abc"


@pytest.mark.unit
def test_write_is_atomic_via_tmp_then_replace(tmp_path: Path) -> None:
    """Pre-existing inventory.json is replaced atomically; no .tmp left behind."""
    _seed_db(tmp_path)
    snapshot = tmp_path / INVENTORY_SNAPSHOT_FILENAME
    snapshot.write_text('{"puzzles_total": 999}', encoding="utf-8")  # stale

    write_inventory_snapshot(tmp_path)

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["puzzles_total"] == 3  # overwritten with current count
    assert not (tmp_path / "inventory.json.tmp").exists()
