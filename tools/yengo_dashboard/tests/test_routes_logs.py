"""Tests for the Slice 5 stage-log endpoints.

Real-fixture style: write actual log files into a tmp .pm-runtime/logs and
spin up the FastAPI app pointed at that runtime dir. No mocks — these
endpoints are pure file reads and the safety checks (filename regex +
path-resolution) deserve real-disk verification.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools.yengo_dashboard.server.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seed_logs(runtime: Path) -> Path:
    logs = runtime / "logs"
    logs.mkdir(parents=True)
    (logs / "2026-05-06-ingest.log").write_text(
        "\n".join(f"line {i}" for i in range(1, 21)) + "\n",
        encoding="utf-8",
    )
    (logs / "2026-05-06-publish.log").write_text("only one line\n", encoding="utf-8")
    (logs / "2026-05-05-analyze.log").write_text("yesterday\n", encoding="utf-8")
    # A file the regex must reject — leading "../"-ish content as a name is
    # impossible at the FS level, so simulate the boundary by adding a
    # non-.log file that should not appear in the listing.
    (logs / "ignore-me.txt").write_text("not a log", encoding="utf-8")
    return logs


class TestStageFilesList:
    def test_empty_when_logs_dir_missing(self, tmp_path: Path) -> None:
        app = create_app(repo_root=REPO_ROOT, runtime_dir=tmp_path / "no-runtime")
        with TestClient(app) as client:
            resp = client.get("/api/logs/stage-files")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"files": [], "logs_dir": str((tmp_path / "no-runtime" / "logs")).replace("\\", "/")}

    def test_lists_log_files_newest_first_and_skips_non_log(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        _seed_logs(runtime)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/logs/stage-files")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        names = [f["name"] for f in body["files"]]
        # ignore-me.txt must be skipped (regex requires .log).
        assert "ignore-me.txt" not in names
        # Sorted by name descending: newer date prefixes first.
        assert names == [
            "2026-05-06-publish.log",
            "2026-05-06-ingest.log",
            "2026-05-05-analyze.log",
        ]
        # Each row carries size + mtime.
        for f in body["files"]:
            assert f["size_bytes"] >= 1
            assert "T" in f["mtime_iso"]


class TestStageFilesTail:
    def test_tail_returns_last_n_lines_with_truncation_flag(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        _seed_logs(runtime)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/logs/stage-files/2026-05-06-ingest.log?lines=5")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "2026-05-06-ingest.log"
        assert body["lines"] == ["line 16", "line 17", "line 18", "line 19", "line 20"]
        assert body["total_lines"] == 20
        assert body["truncated"] is True

    def test_tail_returns_all_lines_when_n_exceeds_file(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        _seed_logs(runtime)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/logs/stage-files/2026-05-06-publish.log?lines=100")
        assert resp.status_code == 200
        body = resp.json()
        assert body["lines"] == ["only one line"]
        assert body["truncated"] is False
        assert body["total_lines"] == 1

    @pytest.mark.parametrize(
        "bad_name",
        [
            "../etc/passwd",
            "../../secret.log",
            "no-extension",
            "file with space.log",
            ".hidden.log",  # leading dot is allowed by the regex but file doesn't exist
        ],
    )
    def test_unsafe_or_missing_names_404(self, tmp_path: Path, bad_name: str) -> None:
        runtime = tmp_path / "runtime"
        _seed_logs(runtime)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get(f"/api/logs/stage-files/{bad_name}")
        assert resp.status_code == 404, resp.text

    def test_tail_lines_param_is_clamped_by_validation(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        _seed_logs(runtime)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            # 100000 > _MAX_TAIL_LINES (5000) → 422 from FastAPI Query(le=...)
            resp = client.get("/api/logs/stage-files/2026-05-06-ingest.log?lines=100000")
        assert resp.status_code == 422
