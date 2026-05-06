"""Tests for ``puzzle_manager source-status --json`` machine-readable output.

Real fixtures, no mocks. Each test:
  1. Creates a tmp config dir with a real ``sources.json``.
  2. Creates a real ``.yengo-ingest.sqlite`` via ``SourceIngestDB`` with real
     upserts at known FileStatus values.
  3. Calls ``cmd_source_status`` directly with ``args.json=True``.
  4. Captures stdout via the ``capsys`` pytest fixture and parses the JSON.
  5. Asserts the named-bucket counts and the schema shape that
     ``tools/yengo_dashboard/`` will rely on (per principle #6: cockpit calls this
     command and trusts its bucket names; it never sees raw status integers).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from backend.puzzle_manager.cli import cmd_source_status
from backend.puzzle_manager.core.source_ingest_db import FileStatus, SourceIngestDB

pytestmark = pytest.mark.unit


def _write_sources_json(config_dir: Path, source_id: str, source_root: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_adapter": source_id,
        "sources": [
            {
                "id": source_id,
                "name": source_id,
                "adapter": "local",
                "config": {
                    "path": source_root.as_posix(),
                    "include_folders": [],
                    "exclude_folders": [],
                },
            }
        ],
    }
    (config_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")


def _seed_ingest_db(
    source_root: Path,
    *,
    source_id: str,
    ingested: int,
    skipped: int,
    failed: int,
) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    with SourceIngestDB.open(source_root, source_id=source_id, run_id="test-run") as db:
        i = 0
        for n, status in (
            (ingested, FileStatus.INGESTED),
            (skipped, FileStatus.SKIPPED),
            (failed, FileStatus.FAILED),
        ):
            for _ in range(n):
                db.upsert(
                    rel_path=f"file-{i:04d}.sgf",
                    content_hash=f"hash{i:012d}",
                    size_bytes=100 + i,
                    mtime_ns=1_700_000_000_000_000_000 + i,
                    status=status,
                )
                i += 1
        db.commit()


def _make_args(*, config_dir: Path, source: str | None) -> argparse.Namespace:
    return argparse.Namespace(config=config_dir, source=source, json=True)


class TestSourceStatusJson:
    def test_json_emits_named_buckets_for_single_source(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_root = tmp_path / "data"
        config_dir = tmp_path / "config"
        _write_sources_json(config_dir, source_id="my-src", source_root=source_root)
        _seed_ingest_db(
            source_root, source_id="my-src", ingested=7, skipped=3, failed=2
        )

        rc = cmd_source_status(_make_args(config_dir=config_dir, source=None))
        assert rc == 0

        captured = capsys.readouterr()
        assert captured.out.strip(), "JSON mode produced no stdout"
        payload = json.loads(captured.out)

        assert "sources" in payload, "JSON shape must be {sources: [...]}"
        assert isinstance(payload["sources"], list)
        assert len(payload["sources"]) == 1

        row = payload["sources"][0]
        assert row["id"] == "my-src"
        assert row["adapter"] == "local"
        assert row["db_exists"] is True
        assert row["ingested"] == 7
        assert row["skipped"] == 3
        assert row["failed"] == 2
        assert row["total"] == 12
        assert row["error"] is None
        for required in ("source_root", "db_path", "schema_version", "db_size_bytes", "db_mtime"):
            assert required in row, f"missing required field: {required}"

    def test_json_for_source_with_no_db_yet_emits_zero_counts(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_root = tmp_path / "fresh-source"
        source_root.mkdir(parents=True)  # exists, but no .yengo-ingest.sqlite
        config_dir = tmp_path / "config"
        _write_sources_json(config_dir, source_id="fresh", source_root=source_root)

        rc = cmd_source_status(_make_args(config_dir=config_dir, source="fresh"))
        assert rc == 0

        payload = json.loads(capsys.readouterr().out)
        assert len(payload["sources"]) == 1
        row = payload["sources"][0]
        assert row["id"] == "fresh"
        assert row["db_exists"] is False
        assert row["ingested"] == 0
        assert row["skipped"] == 0
        assert row["failed"] == 0
        assert row["total"] == 0
        assert row["schema_version"] is None

    def test_json_filtered_by_source_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_dir = tmp_path / "config"
        # Two sources sharing a config file, one of which we filter to.
        config_dir.mkdir(parents=True)
        src_a_root = tmp_path / "src-a"
        src_b_root = tmp_path / "src-b"
        payload = {
            "active_adapter": "src-a",
            "sources": [
                {
                    "id": "src-a", "name": "A", "adapter": "local",
                    "config": {"path": src_a_root.as_posix()},
                },
                {
                    "id": "src-b", "name": "B", "adapter": "local",
                    "config": {"path": src_b_root.as_posix()},
                },
            ],
        }
        (config_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")
        _seed_ingest_db(src_a_root, source_id="src-a", ingested=5, skipped=0, failed=0)
        _seed_ingest_db(src_b_root, source_id="src-b", ingested=1, skipped=1, failed=1)

        rc = cmd_source_status(_make_args(config_dir=config_dir, source="src-b"))
        assert rc == 0

        result = json.loads(capsys.readouterr().out)
        assert len(result["sources"]) == 1
        assert result["sources"][0]["id"] == "src-b"
        assert result["sources"][0]["total"] == 3
