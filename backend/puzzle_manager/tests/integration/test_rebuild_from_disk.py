"""Integration tests for rebuild_search_db_from_disk()."""

import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def sample_output_dir(tmp_path, monkeypatch):
    """Create a sample output directory with SGF files and config."""
    output_dir = tmp_path / "output"
    sgf_dir = output_dir / "sgf" / "0001"
    sgf_dir.mkdir(parents=True)

    # Create minimal SGF files with required properties
    sgfs = {
        "puzzleaaa11111": (
            "(;GM[1]FF[4]SZ[9]"
            "GN[YENGO-puzzleaaa11111]"
            "YV[13]YG[beginner]"
            "YT[life-and-death]"
            "YQ[q:2;rc:0;hc:0;ac:1]"
            "YX[d:1;r:2;s:3;u:1]"
            "AB[dd][de][ed]AW[ee][ef][fe]"
            ";B[df])"
        ),
        "puzzlebbb22222": (
            "(;GM[1]FF[4]SZ[9]"
            "GN[YENGO-puzzlebbb22222]"
            "YV[13]YG[elementary]"
            "YT[tesuji,ladder]"
            "YQ[q:3;rc:0;hc:0;ac:1]"
            "YX[d:2;r:3;s:5;u:2]"
            "AB[cc][cd][dc]AW[dd][de][ed]"
            ";B[ce])"
        ),
    }

    for name, content in sgfs.items():
        (sgf_dir / f"{name}.sgf").write_text(content, encoding="utf-8")

    # Point config dir to project root config
    import backend.puzzle_manager.paths as paths
    monkeypatch.setattr(
        paths, "get_global_config_dir",
        lambda: Path(r"c:\Users\kumarsnaveen\Downloads\NawiN\personal\gitrepos\yen-go\config")
    )
    monkeypatch.setattr(paths, "get_output_dir", lambda: output_dir)

    return output_dir


class TestRebuildSearchDbFromDisk:
    """Tests for rebuild_search_db_from_disk()."""

    def test_rebuilds_both_databases(self, sample_output_dir):
        """Rebuilds DB-1 and DB-2 from SGF files on disk."""
        from backend.puzzle_manager.inventory.reconcile import rebuild_search_db_from_disk

        count = rebuild_search_db_from_disk(sample_output_dir)
        assert count == 2

        # Verify DB-1 exists and has correct count
        db1_path = sample_output_dir / "yengo-search.db"
        assert db1_path.exists()
        conn = sqlite3.connect(str(db1_path))
        try:
            row = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()
            assert row[0] == 2
        finally:
            conn.close()

        # Verify DB-2 exists and has correct count
        db2_path = sample_output_dir / "yengo-content.db"
        assert db2_path.exists()
        conn = sqlite3.connect(str(db2_path))
        try:
            row = conn.execute("SELECT COUNT(*) FROM sgf_files").fetchone()
            assert row[0] == 2
        finally:
            conn.close()

        # Verify db-version.json exists
        version_path = sample_output_dir / "db-version.json"
        assert version_path.exists()
        version_data = json.loads(version_path.read_text())
        assert version_data["puzzle_count"] == 2

    def test_returns_zero_for_empty_dir(self, tmp_path, monkeypatch):
        """Returns 0 when no SGF files exist."""
        import backend.puzzle_manager.paths as paths
        monkeypatch.setattr(paths, "get_output_dir", lambda: tmp_path)

        from backend.puzzle_manager.inventory.reconcile import rebuild_search_db_from_disk
        count = rebuild_search_db_from_disk(tmp_path)
        assert count == 0

    def test_overwrites_existing_databases(self, sample_output_dir):
        """Rebuilds over existing DB files."""
        from backend.puzzle_manager.inventory.reconcile import rebuild_search_db_from_disk

        # Create stale DB-1 with wrong data
        db1_path = sample_output_dir / "yengo-search.db"
        db1_path.write_text("stale data")

        count = rebuild_search_db_from_disk(sample_output_dir)
        assert count == 2

        # Verify it's a valid SQLite DB now
        conn = sqlite3.connect(str(db1_path))
        try:
            row = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()
            assert row[0] == 2
        finally:
            conn.close()
