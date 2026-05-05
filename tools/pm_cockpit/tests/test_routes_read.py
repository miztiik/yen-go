"""Real-fixture tests for pm_cockpit read endpoints.

These spin up the FastAPI app via ``TestClient`` and, for ``/api/adapters``,
drive the real ``python -m backend.puzzle_manager source-status --json``
subprocess against a temp config + real ``.yengo-ingest.sqlite`` seeded via
the real ``SourceIngestDB``. ``/api/inventory`` and ``/api/runs`` use real
on-disk fixtures: a tmp ``yengo-search.db`` built with the live publisher
schema, and tmp run-state JSON files written in the same shape the pipeline
emits. No mocks — per PLAN.md §0.4.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from backend.puzzle_manager.core.source_ingest_db import FileStatus, SourceIngestDB
from fastapi.testclient import TestClient

from tools.pm_cockpit import __version__
from tools.pm_cockpit.server.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seed_real_source(
    tmp_path: Path,
    *,
    source_id: str = "fixture-src",
    ingested: int = 4,
    skipped: int = 1,
    failed: int = 1,
) -> Path:
    """Build a tmp config dir + real seeded ingest DB. Returns the config dir."""
    source_root = tmp_path / "data"
    source_root.mkdir(parents=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "sources.json").write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    with SourceIngestDB.open(source_root, source_id=source_id, run_id="fixture-run") as db:
        i = 0
        for n, status in (
            (ingested, FileStatus.INGESTED),
            (skipped, FileStatus.SKIPPED),
            (failed, FileStatus.FAILED),
        ):
            for _ in range(n):
                db.upsert(
                    rel_path=f"f-{i:03d}.sgf",
                    content_hash=f"hash{i:012d}",
                    size_bytes=200 + i,
                    mtime_ns=1_700_000_000_000_000_000 + i,
                    status=status,
                )
                i += 1
        db.commit()
    return config_dir


def _seed_real_search_db(published_dir: Path) -> Path:
    """Build a real ``yengo-search.db`` with a minimal subset of the production
    schema and a handful of rows. Schema columns mirror the live DB
    (verified against ``yengo-puzzle-collections/yengo-search.db``).
    """
    published_dir.mkdir(parents=True, exist_ok=True)
    db_path = published_dir / "yengo-search.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE puzzles (
                content_hash TEXT PRIMARY KEY,
                batch TEXT,
                level_id INTEGER,
                quality INTEGER,
                content_type INTEGER,
                cx_depth INTEGER,
                cx_refutations INTEGER,
                cx_solution_len INTEGER,
                cx_unique_resp INTEGER
            );
            CREATE TABLE collections (
                slug TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                puzzle_count INTEGER
            );
            CREATE TABLE daily_schedule (
                date TEXT PRIMARY KEY,
                version INTEGER,
                generated_at TEXT,
                technique TEXT,
                attrs TEXT
            );
            """
        )
        rows = [
            ("a" * 16, "0001", 110, 3, 1, 5, 12, 3, 2),
            ("b" * 16, "0001", 110, 4, 1, 6, 14, 4, 2),
            ("c" * 16, "0001", 150, 2, 2, 3, 8, 2, 1),
            ("d" * 16, "0001", 150, 5, 3, 7, 16, 5, 3),
        ]
        conn.executemany(
            "INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?,?)", rows
        )
        conn.executemany(
            "INSERT INTO collections VALUES (?,?,?,?)",
            [
                ("col-a", "Col A", "lnd", 2),
                ("col-b", "Col B", "shape", 2),
            ],
        )
        conn.execute(
            "INSERT INTO daily_schedule VALUES (?,?,?,?,?)",
            ("2026-01-01", 1, "2026-01-01T00:00:00Z", "ladder", "{}"),
        )
        conn.commit()
    # Write the inventory snapshot the cockpit reads (the cockpit no longer
    # opens the DB directly; see backend.puzzle_manager.inventory.snapshot).
    from backend.puzzle_manager.inventory.snapshot import (
        write_inventory_snapshot,
    )
    write_inventory_snapshot(published_dir)
    return db_path


def _seed_real_runs(runtime_dir: Path, *, count: int = 3) -> Path:
    """Write ``count`` run-state JSON files into ``runtime_dir/state/runs/``.

    Filenames use the same ``YYYYMMDD-HHMMSS_run-id.json`` convention the
    pipeline uses, so directory ordering is chronological.
    """
    runs_dir = runtime_dir / "state" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        run_id = f"20260101-fixture{i:02d}"
        state = {
            "run_id": run_id,
            "status": "completed" if i < count - 1 else "failed",
            "started_at": f"2026-01-01T00:0{i}:00Z",
            "completed_at": f"2026-01-01T00:0{i}:30Z",
            "stages": [
                {
                    "name": "ingest",
                    "status": "completed",
                    "started_at": f"2026-01-01T00:0{i}:00Z",
                    "completed_at": f"2026-01-01T00:0{i}:10Z",
                    "processed_count": 10 + i,
                    "failed_count": i,
                    "skipped_count": 0,
                    "last_batch_id": None,
                },
                {
                    "name": "analyze",
                    "status": "skipped",
                    "started_at": None,
                    "completed_at": None,
                    "processed_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "last_batch_id": None,
                },
            ],
            "failures": [{"reason": "x"}] * i,
            "config_snapshot": {"version": "1.0"},  # heavy field, must be stripped
            "batches": list(range(100)),  # heavy, must be stripped
        }
        path = runs_dir / f"2026010{i}-00000{i}_{run_id}.json"
        path.write_text(json.dumps(state), encoding="utf-8")
    return runs_dir


class TestHealthEndpoint:
    def test_returns_ok_with_version_and_uptime(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["version"] == __version__
        assert isinstance(body["uptime_s"], (int, float))
        assert body["uptime_s"] >= 0.0


class TestAdaptersEndpoint:
    @pytest.mark.slow
    def test_returns_real_named_buckets_from_real_subprocess(
        self, tmp_path: Path
    ) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="cockpit-fixture", ingested=4, skipped=1, failed=1
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "sources" in body
        assert len(body["sources"]) == 1

        row = body["sources"][0]
        assert row["id"] == "cockpit-fixture"
        assert row["adapter"] == "local"
        assert row["db_exists"] is True
        assert row["ingested"] == 4
        assert row["skipped"] == 1
        assert row["failed"] == 1
        assert row["total"] == 6
        assert row["error"] is None


class TestInventoryEndpoint:
    def test_returns_zero_counts_when_db_missing(self, tmp_path: Path) -> None:
        # published_dir exists but contains no yengo-search.db
        app = create_app(
            repo_root=REPO_ROOT,
            published_dir=tmp_path / "empty-published",
        )
        with TestClient(app) as client:
            resp = client.get("/api/inventory")
        assert resp.status_code == 200
        body = resp.json()
        assert body["db_exists"] is False
        assert body["snapshot_exists"] is False
        assert body["advice"] is not None  # nudge to run vacuum-db
        assert body["puzzles_total"] == 0
        assert body["collections_total"] == 0
        assert body["daily_schedule_total"] == 0
        assert body["by_level_id"] == {}
        assert body["by_content_type"] == {}

    def test_returns_zero_counts_when_db_present_but_snapshot_missing(
        self, tmp_path: Path
    ) -> None:
        """G2 architectural guarantee: cockpit never opens yengo-search.db.

        Even when the SQLite DB is present, if no inventory.json snapshot
        has been written the cockpit reports zeros + advice — it MUST NOT
        fall back to opening the DB (Windows file-lock contention).
        """
        published = tmp_path / "published"
        published.mkdir()
        (published / "yengo-search.db").write_bytes(b"\x00")  # any non-empty bytes
        app = create_app(repo_root=REPO_ROOT, published_dir=published)
        with TestClient(app) as client:
            resp = client.get("/api/inventory")
        assert resp.status_code == 200
        body = resp.json()
        assert body["db_exists"] is True  # cheap stat
        assert body["snapshot_exists"] is False
        assert body["advice"] is not None
        assert body["puzzles_total"] == 0  # no SQLite read happened

    def test_returns_real_counts_from_real_sqlite(self, tmp_path: Path) -> None:
        published = tmp_path / "published"
        _seed_real_search_db(published)
        app = create_app(repo_root=REPO_ROOT, published_dir=published)
        with TestClient(app) as client:
            resp = client.get("/api/inventory")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["db_exists"] is True
        assert body["puzzles_total"] == 4
        assert body["collections_total"] == 2
        assert body["daily_schedule_total"] == 1
        # 2 puzzles at level 110, 2 at level 150
        assert body["by_level_id"] == {"110": 2, "150": 2}
        # 2 type=1 (curated), 1 type=2 (practice), 1 type=3 (training)
        assert body["by_content_type"] == {"1": 2, "2": 1, "3": 1}
        # Phase B additions: collection-by-category from the seed (lnd, shape).
        assert body["by_collection_category"] == {"lnd": 1, "shape": 1}
        # No db-version.json in this fixture, so both fields are None.
        assert body["schema_version"] is None
        assert body["db_version"] is None

    def test_surfaces_schema_and_db_version_from_db_version_json(
        self, tmp_path: Path
    ) -> None:
        published = tmp_path / "published"
        _seed_real_search_db(published)
        (published / "db-version.json").write_text(
            json.dumps({
                "schema_version": 2,
                "db_version": "20260503-d29f42f0",
                "puzzle_count": 4,
                "generated_at": "2026-05-03T00:00:00Z",
            }),
            encoding="utf-8",
        )
        # Re-snapshot now that db-version.json exists, so inventory.json
        # carries the version fields (the seed fn snapshotted before).
        from backend.puzzle_manager.inventory.snapshot import (
            write_inventory_snapshot,
        )
        write_inventory_snapshot(published)
        app = create_app(repo_root=REPO_ROOT, published_dir=published)
        with TestClient(app) as client:
            resp = client.get("/api/inventory")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["schema_version"] == 2
        assert body["db_version"] == "20260503-d29f42f0"

    def test_config_static_mount_serves_puzzle_levels_json(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/config-static/puzzle-levels.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "levels" in data
        assert isinstance(data["levels"], list)
        assert len(data["levels"]) >= 1


class TestRunsEndpoint:
    def test_returns_empty_when_runs_dir_missing(self, tmp_path: Path) -> None:
        app = create_app(
            repo_root=REPO_ROOT,
            runtime_dir=tmp_path / "no-runtime",
        )
        with TestClient(app) as client:
            resp = client.get("/api/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"runs": [], "total": 0}

    def test_returns_real_runs_newest_first_with_heavy_fields_stripped(
        self, tmp_path: Path
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_real_runs(runtime, count=3)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/runs")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 3
        assert len(body["runs"]) == 3
        # Newest first: filename prefix sort, descending
        assert body["runs"][0]["run_id"] == "20260101-fixture02"
        assert body["runs"][2]["run_id"] == "20260101-fixture00"
        # Heavy fields not present in the response model
        first = body["runs"][0]
        assert "batches" not in first
        assert "config_snapshot" not in first
        assert "failures" not in first
        # Stage projection survived
        assert first["stages"][0]["name"] == "ingest"
        assert first["stages"][0]["processed_count"] == 12
        assert first["failure_count"] == 2
        assert first["state_file"].endswith(".json")

    def test_limit_param_caps_results_but_total_reflects_disk(
        self, tmp_path: Path
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_real_runs(runtime, count=3)
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/runs?limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["runs"]) == 1
        assert body["runs"][0]["run_id"] == "20260101-fixture02"

    def test_skips_corrupt_state_file_silently(self, tmp_path: Path) -> None:
        runtime = tmp_path / "runtime"
        runs_dir = runtime / "state" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "20260101-000000_good.json").write_text(
            json.dumps(
                {
                    "run_id": "good",
                    "status": "completed",
                    "started_at": None,
                    "completed_at": None,
                    "stages": [],
                    "failures": [],
                }
            ),
            encoding="utf-8",
        )
        (runs_dir / "20260101-000001_broken.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/runs")
        assert resp.status_code == 200
        body = resp.json()
        # total counts both files on disk; runs list skips the broken one
        assert body["total"] == 2
        assert len(body["runs"]) == 1
        assert body["runs"][0]["run_id"] == "good"
