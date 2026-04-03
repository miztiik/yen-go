"""Unit tests for vacuum-db CLI command guard logic."""

import argparse
from pathlib import Path
from unittest.mock import patch

from backend.puzzle_manager.cli import cmd_vacuum_db


def _make_args(*, rebuild: bool = False, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(rebuild=rebuild, dry_run=dry_run)


class TestVacuumDbGuard:
    """Tests for the content-DB guard in cmd_vacuum_db."""

    def test_no_content_db_no_rebuild_returns_early(self, tmp_path: Path, capsys):
        """vacuum-db (no --rebuild) returns 0 when content DB missing."""
        with patch(
            "backend.puzzle_manager.paths.get_output_dir", return_value=tmp_path
        ):
            rc = cmd_vacuum_db(_make_args(rebuild=False))

        assert rc == 0
        assert "nothing to vacuum" in capsys.readouterr().out.lower()

    @patch("backend.puzzle_manager.inventory.reconcile.rebuild_search_db_from_disk", return_value=42)
    def test_no_content_db_with_rebuild_proceeds(
        self, mock_rebuild, tmp_path: Path, capsys
    ):
        """vacuum-db --rebuild proceeds even when content DB missing."""
        # Create sgf dir with one file so hash scanning works
        sgf_dir = tmp_path / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "abc123.sgf").write_text("(;FF[4])")

        with patch(
            "backend.puzzle_manager.paths.get_output_dir", return_value=tmp_path
        ):
            rc = cmd_vacuum_db(_make_args(rebuild=True))

        assert rc == 0
        mock_rebuild.assert_called_once_with(tmp_path)
        out = capsys.readouterr().out
        assert "42 puzzles indexed" in out

    @patch("backend.puzzle_manager.inventory.reconcile.rebuild_search_db_from_disk", return_value=5)
    def test_no_content_db_rebuild_dry_run(
        self, mock_rebuild, tmp_path: Path, capsys
    ):
        """vacuum-db --rebuild --dry-run shows preview without content DB."""
        sgf_dir = tmp_path / "sgf" / "0001"
        sgf_dir.mkdir(parents=True)
        (sgf_dir / "abc123.sgf").write_text("(;FF[4])")

        with patch(
            "backend.puzzle_manager.paths.get_output_dir", return_value=tmp_path
        ):
            rc = cmd_vacuum_db(_make_args(rebuild=True, dry_run=True))

        assert rc == 0
        mock_rebuild.assert_not_called()
        out = capsys.readouterr().out
        assert "Would rebuild" in out
        assert "1 SGF files" in out

    @patch("backend.puzzle_manager.core.content_db.vacuum_orphans", return_value=3)
    def test_with_content_db_vacuums_normally(
        self, mock_vacuum, tmp_path: Path, capsys
    ):
        """vacuum-db works normally when content DB exists."""
        # Create content DB file
        (tmp_path / "yengo-content.db").write_bytes(b"")

        with patch(
            "backend.puzzle_manager.paths.get_output_dir", return_value=tmp_path
        ):
            rc = cmd_vacuum_db(_make_args(rebuild=False))

        assert rc == 0
        mock_vacuum.assert_called_once()
        assert "Removed 3 orphaned" in capsys.readouterr().out

    @patch("backend.puzzle_manager.inventory.reconcile.rebuild_search_db_from_disk", return_value=10)
    @patch("backend.puzzle_manager.core.content_db.vacuum_orphans", return_value=2)
    def test_with_content_db_vacuum_then_rebuild(
        self, mock_vacuum, mock_rebuild, tmp_path: Path, capsys
    ):
        """vacuum-db --rebuild: vacuums first, then rebuilds."""
        (tmp_path / "yengo-content.db").write_bytes(b"")

        with patch(
            "backend.puzzle_manager.paths.get_output_dir", return_value=tmp_path
        ):
            rc = cmd_vacuum_db(_make_args(rebuild=True))

        assert rc == 0
        mock_vacuum.assert_called_once()
        mock_rebuild.assert_called_once_with(tmp_path)
        out = capsys.readouterr().out
        assert "Removed 2 orphaned" in out
        assert "10 puzzles indexed" in out
