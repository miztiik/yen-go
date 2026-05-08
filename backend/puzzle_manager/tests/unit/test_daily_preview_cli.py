"""Unit tests for ``daily-preview`` (Theme 8b)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.puzzle_manager.cli import cmd_daily_preview


@pytest.fixture
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr("backend.puzzle_manager.cli.get_output_dir",
                        lambda: out)
    return out


def _ns(**kw) -> argparse.Namespace:
    base = {"date": "2026-05-08", "json": True}
    base.update(kw)
    return argparse.Namespace(**base)


class TestDailyPreview:
    def test_db_missing_returns_null_challenge(
        self, output_dir: Path, capsys,
    ) -> None:
        rc = cmd_daily_preview(_ns())
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is True
        assert out["db_exists"] is False
        assert out["challenge"] is None
        assert out["date"] == "2026-05-08"

    def test_invalid_date_returns_1(
        self, output_dir: Path, capsys,
    ) -> None:
        rc = cmd_daily_preview(_ns(date="not-a-date"))
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is False
        assert "Invalid" in out["error"]

    def test_dry_run_emits_challenge_payload(
        self, output_dir: Path, capsys,
    ) -> None:
        # Seed any sentinel DB file (existence check passes).
        (output_dir / "yengo-search.db").write_bytes(b"")

        challenge = MagicMock()
        challenge.model_dump.return_value = {
            "date": "2026-05-08",
            "version": "2.2",
            "standard": {"total": 30, "technique_of_day": "ladder"},
        }
        result = MagicMock(challenges=[challenge], failures=[])

        with patch(
            "backend.puzzle_manager.cli.DailyGenerator"
        ) as gen_cls:
            instance = gen_cls.return_value
            instance.generate.return_value = result
            rc = cmd_daily_preview(_ns())

        assert rc == 0
        # Generator was constructed with dry_run=True (no DB writes).
        _, kwargs = gen_cls.call_args
        assert kwargs["dry_run"] is True
        out = json.loads(capsys.readouterr().out)
        assert out["challenge"]["standard"]["total"] == 30
        assert out["failures"] == []
