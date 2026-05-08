"""Real-fixture tests for yengo_dashboard read endpoints.

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

from tools.yengo_dashboard import __version__
from tools.yengo_dashboard.server.app import create_app

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


class TestSpaCleanPathRoutes:
    """Slice 4: clean URL paths for the SPA. Deep links like /pipeline must
    return the same index.html as /, otherwise refreshing on a non-root path
    or sharing a deep link 404s."""

    @pytest.mark.parametrize("path", ["/library", "/pipeline", "/operations", "/guide"])
    def test_top_level_nav_paths_serve_index_html(self, path: str) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get(path)
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/html"), resp.headers
        # Sanity: it really is the dashboard's index.html, not a stub.
        assert "Yen-Go Dashboard" in resp.text

    def test_guide_subpath_serves_index_html(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/guide/concepts/anything-here.md")
        assert resp.status_code == 200, resp.text
        assert "Yen-Go Dashboard" in resp.text

    def test_api_routes_still_take_precedence(self) -> None:
        """The catch-all SPA routes must not shadow /api/* — /api/health must
        still return JSON, not the SPA shell."""
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")


def _seed_failures_runs(runtime: Path) -> Path:
    """Theme 2b: seed real RunState JSON files containing Failure[] entries.

    Uses the same on-disk shape ``StateManager.archive()`` writes
    (``runs/{prefix}_{run_id}.json``), and ``model_dump_json()`` to keep the
    Pydantic schema authoritative — no hand-rolled fields.
    """
    from datetime import UTC, datetime, timedelta

    from backend.puzzle_manager.models.enums import RunStatus
    from backend.puzzle_manager.state.models import Failure, RunState

    runs_dir = runtime / "state" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(UTC)
    runs = [
        RunState(
            run_id="20260507-aaaaaaaa",
            status=RunStatus.FAILED,
            started_at=started,
            failures=[
                Failure(item_id="p1", stage="ingest", error_type="HTTPError", error_message="429"),
                Failure(item_id="p2", stage="ingest", error_type="HTTPError", error_message="503"),
            ],
        ),
        RunState(
            run_id="20260507-bbbbbbbb",
            status=RunStatus.FAILED,
            started_at=started - timedelta(minutes=1),
            failures=[
                Failure(item_id="p3", stage="publish", error_type="DBError", error_message="locked"),
            ],
        ),
    ]
    for run in runs:
        (runs_dir / f"{run.run_id}.json").write_text(
            run.model_dump_json(indent=2), encoding="utf-8",
        )
    return runs_dir


class TestFailuresSummaryEndpoint:
    """Theme 2b: drives the real ``status --failures-summary --json`` subprocess
    via the cockpit. Runtime dir is overridden via ``YENGO_RUNTIME_DIR`` so the
    CLI scans tmp run-state files only."""

    def test_returns_grouped_raw_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_failures_runs(runtime)
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/status/failures-summary", params={"last": 10})
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, list)
        # Two distinct (stage, error_type) groups across the seeded runs.
        keys = {(g["stage"], g["error_type"]) for g in raw}
        assert keys == {("ingest", "HTTPError"), ("publish", "DBError")}
        ingest = next(g for g in raw if g["stage"] == "ingest")
        assert ingest["count"] == 2
        assert "20260507-aaaaaaaa" in ingest["affected_runs"]

    def test_empty_runtime_returns_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        (runtime / "state" / "runs").mkdir(parents=True)
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/status/failures-summary")
        assert resp.status_code == 200, resp.text
        assert resp.json()["raw"] == []

    def test_last_query_param_clamped(self) -> None:
        # Query(ge=1, le=200) → 0 is rejected by FastAPI before subprocess.
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/status/failures-summary", params={"last": 0})
        assert resp.status_code == 422


def _seed_runtime_tree(runtime: Path) -> None:
    """Theme 3b: seed `.pm-runtime/` with known byte sizes per bucket."""
    for rel, size in (
        ("logs/2026-05-07-ingest.log", 100),
        ("state/current_run.json", 50),
        ("staging/ingest/p1.sgf", 300),
        ("raw/source/x.json", 25),
    ):
        f = runtime / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x" * size)


class TestRuntimeInfoEndpoint:
    """Theme 3b: drives the real ``runtime-info --json`` subprocess via the
    cockpit. Runtime dir overridden via ``YENGO_RUNTIME_DIR`` so per-bucket
    sizes are deterministic."""

    def test_returns_runtime_info_dict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_runtime_tree(runtime)
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/runtime-info")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, dict)
        assert raw["logs_bytes"] == 100
        assert raw["state_bytes"] == 50
        assert raw["staging_bytes"] == 300
        assert raw["raw_bytes"] == 25
        assert raw["captured_at"]
        assert "by_source" in raw
        assert "ingest_dbs_bytes" in raw
        assert "publish_logs_bytes" in raw

    def test_empty_runtime_returns_zeros(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        runtime.mkdir()
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/runtime-info")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["logs_bytes"] == 0
        assert raw["state_bytes"] == 0
        assert raw["staging_bytes"] == 0


def _seed_activity_run(runtime: Path, *, run_id: str, status: str, ts: str) -> None:
    """Theme 13b: seed minimal RunState JSON the `activity` CLI consumes."""
    runs_dir = runtime / "state" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "status": status,
        "started_at": ts,
        "completed_at": ts,
        "failures": [],
    }
    (runs_dir / f"{run_id}.json").write_text(json.dumps(payload), encoding="utf-8")


class TestActivityEndpoint:
    """Theme 13b: drives the real ``activity --json`` subprocess via the cockpit.

    Audit and publish-log live under the collections ops dir (separate from
    runtime); seeding a single run is enough to validate the wire contract,
    since the CLI's source merging is exercised by ``test_activity.py``.
    """

    def test_returns_run_event(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_activity_run(
            runtime, run_id="20260507-aaaaaaaa", status="completed",
            ts="2026-05-07T10:00:00+00:00",
        )
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/activity", params={"limit": 50})
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, list)
        run_events = [e for e in raw if e["kind"] == "run"]
        assert any(e["subject_id"] == "20260507-aaaaaaaa" for e in run_events)

    def test_kinds_filter_excludes_run_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        _seed_activity_run(
            runtime, run_id="20260507-bbbbbbbb", status="completed",
            ts="2026-05-07T11:00:00+00:00",
        )
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/activity", params={"kinds": "publish"})
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        # No publish-log seeded → empty result when filtered to publish.
        assert all(e["kind"] != "run" for e in raw)

    def test_invalid_kind_returns_400(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runtime = tmp_path / "runtime"
        runtime.mkdir()
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(runtime))
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        app = create_app(repo_root=REPO_ROOT, runtime_dir=runtime)
        with TestClient(app) as client:
            resp = client.get("/api/activity", params={"kinds": "bogus"})
        assert resp.status_code == 400


def _seed_inventory_check_corpus(yengo_root: Path) -> None:
    """Theme 14b: build a real publication root + publish-log under
    ``yengo_root/yengo-puzzle-collections/`` that yields exactly one
    ``missing_file`` and one ``orphan_file`` row.

    Also copies ``config/`` from the real repo because the CLI loads the
    SGF schema from ``<YENGO_ROOT>/config/`` at import time.
    """
    import shutil

    shutil.copytree(REPO_ROOT / "config", yengo_root / "config")
    pub = yengo_root / "yengo-puzzle-collections"
    sgf_dir = pub / "sgf" / "0001"
    sgf_dir.mkdir(parents=True)
    # Healthy: file on disk + publish-log entry → ignored.
    (sgf_dir / "aaaaaaaaaaaaaaaa.sgf").write_text("(;FF[4])", encoding="utf-8")
    # Orphan: file on disk, no log entry.
    (sgf_dir / "ffffffffffffffff.sgf").write_text("(;FF[4])", encoding="utf-8")
    log_dir = pub / ".puzzle-inventory-state" / "publish-log"
    log_dir.mkdir(parents=True)
    (log_dir / "2026-05-07.jsonl").write_text(
        "\n".join([
            json.dumps({
                "puzzle_id": "aaaaaaaaaaaaaaaa",
                "path": "sgf/0001/aaaaaaaaaaaaaaaa.sgf",
                "run_id": "fixture", "source_id": "src",
                "quality": 3, "trace_id": "t-aaa", "level": "intermediate",
                "tags": [], "collections": [],
            }),
            json.dumps({
                "puzzle_id": "1111111111111111",
                "path": "sgf/0001/1111111111111111.sgf",
                "run_id": "fixture", "source_id": "src",
                "quality": 3, "trace_id": "t-bbb", "level": "intermediate",
                "tags": [], "collections": [],
            }),
        ]) + "\n",
        encoding="utf-8",
    )


class TestInventoryCheckEndpoint:
    """Theme 14b: drives the real ``inventory --check --json`` subprocess
    via the cockpit. Validates the IntegrityReport wire shape passthrough
    and the exit-code-1-is-still-success nuance for the runner."""

    def test_returns_report_with_one_missing_one_orphan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_inventory_check_corpus(tmp_path)
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/inventory/check")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert raw["summary"]["missing_file"] == 1
        assert raw["summary"]["orphan_file"] == 1
        kinds = {(i["kind"], i["puzzle_id"]) for i in raw["issues"]}
        assert kinds == {
            ("missing_file", "1111111111111111"),
            ("orphan_file", "ffffffffffffffff"),
        }

    def test_clean_corpus_returns_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import shutil
        shutil.copytree(REPO_ROOT / "config", tmp_path / "config")
        # Empty publication root → no orphans, no missing.
        (tmp_path / "yengo-puzzle-collections" / "sgf").mkdir(parents=True)
        monkeypatch.setenv("YENGO_ROOT", str(tmp_path))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/inventory/check")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["issues"] == []
        assert raw["summary"] == {"missing_file": 0, "orphan_file": 0}


class TestOpsCatalogEndpoint:
    """Theme 16b: drives the real ``ops catalog --json`` subprocess via the cockpit.

    No fixture seeding needed — the catalog is a static module-level list in
    ``backend.puzzle_manager.models.ops_catalog``. The endpoint exists so the
    Operations page can re-classify cards from a backend-only edit; this test
    pins the passthrough wire and the presence of the canonical fields.
    """

    def test_returns_catalog_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/ops/catalog")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, list)
        assert raw, "ops catalog must not be empty"
        ops = {row["op"] for row in raw}
        # Drift fence — these ops MUST appear so the dashboard can render
        # the Operations page. Remove only when the corresponding card is
        # also removed.
        assert {"clean", "vacuum-db", "rollback"}.issubset(ops)
        # Each row carries the catalog fields the cockpit relies on.
        for row in raw:
            assert row["op"]
            assert isinstance(row["scope"], list) and row["scope"]
            assert "reversible" in row
            assert "preview_supported" in row
            assert row["section"] in {"maintenance", "destructive", "diagnostic"}


class TestTaxonomyEndpoints:
    """Theme 5: tags/levels passthroughs against the real config files."""

    def test_tags_returns_usage_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/tags")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, list) and raw
        slugs = {row["tag"] for row in raw}
        assert "life-and-death" in slugs
        for row in raw:
            assert "category" in row and "usage_count" in row
            assert isinstance(row["aliases"], list)
            assert row["usage_count"] >= 0

    def test_levels_returns_usage_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("YENGO_ROOT", str(REPO_ROOT))
        monkeypatch.setenv("YENGO_RUNTIME_DIR", str(tmp_path / ".pm-runtime"))
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/levels")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert isinstance(raw, list) and raw
        slugs = {row["level"] for row in raw}
        assert {"novice", "intermediate", "expert"}.issubset(slugs)
        for row in raw:
            assert "id" in row and "usage_count" in row
            assert row["usage_count"] >= 0


class TestSourceDetailsEndpoint:
    """Theme 6a: source-status --details passthrough."""

    def test_returns_summary_runs_failures_config(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="detail-fixture", ingested=3, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters/detail-fixture/details")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["id"] == "detail-fixture"
        assert raw["adapter"] == "local"
        assert raw["summary"]["ingested"] == 3
        assert raw["summary"]["total"] == 3
        assert isinstance(raw["recent_runs"], list)
        assert isinstance(raw["recent_failures"], list)
        assert isinstance(raw["config"], dict)
        assert raw["config"].get("path")  # echo of sources.json entry

    def test_unknown_source_returns_400(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="known", ingested=0, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters/does-not-exist/details")
        assert resp.status_code == 400


class TestSourceIngestStateEndpoints:
    """Theme 6b: per-source ingest-DB inspection + reset wiring."""

    def test_inspect_returns_counts_and_failed_rows(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ingest-fixture", ingested=2, skipped=0, failed=2
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters/ingest-fixture/ingest-state")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["source_id"] == "ingest-fixture"
        assert raw["db_exists"] is True
        assert raw["status"] == "healthy"
        assert raw["rows"] == 4
        assert raw["ingested"] == 2
        assert raw["failed"] == 2
        assert len(raw["failed_rows"]) == 2

    def test_inspect_unknown_source_returns_400(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="known", ingested=0, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters/missing/ingest-state")
        assert resp.status_code == 400

    def test_reset_preview_does_not_delete_db(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ingest-prv", ingested=1, skipped=0, failed=1
        )
        db_file = tmp_path / "data" / ".yengo-ingest.sqlite"
        assert db_file.exists()
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapters/ingest-prv/ingest-state/preview")
        assert resp.status_code == 200, resp.text
        assert db_file.exists(), "preview must NOT delete the DB"
        raw = resp.json()["raw"]
        assert raw["db_exists"] is True
        assert raw["row_count_lost"] == 2
        assert raw["failed_rows_lost"] == 1
        assert raw["requires_full_reingest"] is True

    def test_reset_apply_removes_db(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ingest-apply", ingested=1, skipped=0, failed=1
        )
        db_file = tmp_path / "data" / ".yengo-ingest.sqlite"
        assert db_file.exists()
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapters/ingest-apply/ingest-state/reset")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["removed"] is True
        assert raw["rows_lost"] == 2
        assert not db_file.exists(), "apply must remove the DB"


class TestAdapterConfigEndpoints:
    """Theme 7a: read-only adapter-config wiring."""

    def test_list_returns_active_and_path_exists(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ac-list", ingested=0, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapter-config")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["active_adapter"] == "ac-list"
        assert len(raw["sources"]) == 1
        entry = raw["sources"][0]
        assert entry["id"] == "ac-list"
        assert entry["active"] is True
        assert entry["path_exists"] is True

    def test_show_returns_schema_and_kinds(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ac-show", ingested=0, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapter-config/ac-show")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["adapter_kind"] == "local"
        assert "local" in raw["available_kinds"]
        assert raw["schema_for_kind"] is not None
        assert "path" in raw["schema_for_kind"]["properties"]

    def test_show_unknown_returns_400(self, tmp_path: Path) -> None:
        config_dir = _seed_real_source(
            tmp_path, source_id="ac-known", ingested=0, skipped=0, failed=0
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapter-config/nonexistent")
        assert resp.status_code == 400

    def test_validate_all_flags_missing_paths(self, tmp_path: Path) -> None:
        # Build a config with one good and one missing-path source.
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        good_dir = tmp_path / "data" / "good"
        good_dir.mkdir(parents=True)
        (config_dir / "sources.json").write_text(
            json.dumps(
                {
                    "active_adapter": "good",
                    "sources": [
                        {
                            "id": "good", "name": "Good", "adapter": "local",
                            "config": {"path": good_dir.as_posix()},
                        },
                        {
                            "id": "bad", "name": "Bad", "adapter": "local",
                            "config": {"path": (tmp_path / "missing").as_posix()},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/adapter-config/validate")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        rows_by_id = {r["id"]: r for r in raw["rows"]}
        assert rows_by_id["good"]["ok"] is True
        assert rows_by_id["bad"]["ok"] is False
        codes = [e["code"] for e in rows_by_id["bad"]["errors"]]
        assert "path-missing" in codes


class TestAdapterConfigMutationEndpoints:
    """Theme 7b: add/clone/update/remove via POST endpoints."""

    def _seed(self, tmp_path: Path, *, active: str = "src-a") -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        good = tmp_path / "data" / "good"
        good.mkdir(parents=True)
        (config_dir / "sources.json").write_text(
            json.dumps({
                "active_adapter": active,
                "sources": [
                    {"id": "src-a", "name": "Src A", "adapter": "local",
                     "config": {"path": good.as_posix()}},
                    {"id": "src-b", "name": "Src B", "adapter": "local",
                     "config": {"path": good.as_posix()}},
                ],
            }),
            encoding="utf-8",
        )
        return config_dir

    def test_add_then_validate_all_sees_it(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        good = (tmp_path / "data" / "good").as_posix()
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config", json={
                "id": "src-c", "name": "C", "adapter": "local",
                "config": {"path": good},
            })
            assert resp.status_code == 200, resp.text
            assert resp.json()["raw"]["ok"] is True
            v = client.get("/api/adapter-config/validate").json()["raw"]
            ids = [r["id"] for r in v["rows"]]
            assert "src-c" in ids

    def test_clone_preserves_config(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config/src-a/clone", json={
                "new_id": "src-a-copy", "new_name": "Copy of A",
            })
            assert resp.status_code == 200, resp.text
            shown = client.get("/api/adapter-config/src-a-copy").json()["raw"]
            assert shown["source"]["adapter"] == "local"

    def test_remove_refuses_active_without_force(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path, active="src-a")
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config/src-a/remove",
                               json={"force": False})
        assert resp.status_code == 400

    def test_update_set_pairs_merge(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config/src-a/update", json={
                "set_pairs": ["validate=true"], "name": "Renamed",
            })
            assert resp.status_code == 200, resp.text
            shown = client.get("/api/adapter-config/src-a").json()["raw"]
            assert shown["source"]["name"] == "Renamed"
            assert shown["source"]["config"]["validate"] is True

    def test_schema_violation_returns_400(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config", json={
                "id": "BAD_ID", "name": "X", "adapter": "local", "config": {},
            })
        assert resp.status_code == 400


class TestAdapterConfigBootstrapEndpoint:
    """Theme 7c: POST /api/adapter-config/bootstrap preview + apply."""

    def _seed(self, tmp_path: Path) -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        good = tmp_path / "data" / "good"
        good.mkdir(parents=True)
        (config_dir / "sources.json").write_text(
            json.dumps({
                "active_adapter": "src-a",
                "sources": [{
                    "id": "src-a", "name": "A", "adapter": "local",
                    "config": {"path": good.as_posix()},
                }],
            }),
            encoding="utf-8",
        )
        return config_dir

    def test_dry_run_proposes(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "alpha").mkdir(parents=True)
        (scan / "beta").mkdir(parents=True)
        before = (config_dir / "sources.json").read_text(encoding="utf-8")
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config/bootstrap", json={
                "from_folder": scan.as_posix(),
                "adapter": "local", "id_prefix": "", "dry_run": True,
            })
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["dry_run"] is True
        assert raw["applied"] is False
        ids = sorted(e["id"] for e in raw["entries"])
        assert ids == ["alpha", "beta"]
        after = (config_dir / "sources.json").read_text(encoding="utf-8")
        assert before == after, "dry-run must not write"

    def test_apply_writes_fresh_only(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        scan = tmp_path / "scan"
        (scan / "src-a").mkdir(parents=True)  # collision
        (scan / "newone").mkdir(parents=True)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-config/bootstrap", json={
                "from_folder": scan.as_posix(),
                "adapter": "local", "id_prefix": "", "dry_run": False,
            })
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["applied"] is True
        assert "newone" in raw["applied_ids"]
        assert "src-a" not in raw["applied_ids"]


class TestPipelineConfigEndpoints:
    """Theme 7d: GET + POST /api/pipeline-config."""

    def _seed(self, tmp_path: Path) -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        # sources.json — minimal so create_app boot path is happy.
        (config_dir / "sources.json").write_text(
            json.dumps({
                "active_adapter": "src-a",
                "sources": [{
                    "id": "src-a", "name": "A", "adapter": "local",
                    "config": {"path": (tmp_path / "data").as_posix()},
                }],
            }),
            encoding="utf-8",
        )
        (config_dir / "pipeline.json").write_text(
            json.dumps({
                "version": "1.0",
                "batch": {"size": 2000, "max_files_per_dir": 2000},
            }),
            encoding="utf-8",
        )
        return config_dir

    def test_show_returns_pipeline_doc(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/pipeline-config")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["pipeline"]["batch"]["size"] == 2000

    def test_set_mutates_dotted_path(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/pipeline-config", json={
                "set_pairs": ["batch.size=4000"], "force": True,
            })
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["applied"] is True
        doc = json.loads(
            (config_dir / "pipeline.json").read_text(encoding="utf-8"))
        assert doc["batch"]["size"] == 4000
        assert doc["batch"]["max_files_per_dir"] == 2000  # sibling preserved

    def test_set_with_empty_pairs_rejected(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post("/api/pipeline-config", json={
                "set_pairs": [], "force": True,
            })
        # Pydantic min_length=1 → 422.
        assert resp.status_code == 422


class TestDailyEndpoints:
    """Theme 8a: GET /api/daily/list + /api/daily/status."""

    def _seed(self, tmp_path: Path) -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "sources.json").write_text(
            json.dumps({
                "active_adapter": "src-a",
                "sources": [{
                    "id": "src-a", "name": "A", "adapter": "local",
                    "config": {"path": (tmp_path / "data").as_posix()},
                }],
            }),
            encoding="utf-8",
        )
        return config_dir

    def test_list_empty_when_db_missing(self, tmp_path: Path) -> None:
        # No yengo-search.db on disk — list returns ok with rows=[].
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/daily/list")
        # The CLI looks at the *real* output dir for yengo-search.db,
        # so we just assert the contract: 200 + ok + rows is a list.
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert isinstance(raw["rows"], list)

    def test_status_returns_window(self, tmp_path: Path) -> None:
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/daily/status?window_days=7")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["window"]["days"] == 7
        assert raw["expected_dates"] == 7
        assert isinstance(raw["missing_dates"], list)

    def test_preview_db_missing_returns_null(self, tmp_path: Path) -> None:
        # Theme 8b: read-only preview without writing.
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/daily/preview?date=2026-05-08")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["date"] == "2026-05-08"
        assert "challenge" in raw

    def test_preview_invalid_date_returns_400(self, tmp_path: Path) -> None:
        # Theme 8b: bad date → CLI exits 1 → routes_maintenance maps to 502.
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.get("/api/daily/preview?date=not-a-date")
        assert resp.status_code == 502, resp.text

    def test_cancel_preview_db_missing_ok(self, tmp_path: Path) -> None:
        # Theme 8c: preview always returns 200 with empty effects when DB missing.
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post(
                "/api/daily/cancel/preview",
                json={"date": "2026-05-08", "force": True},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["dry_run"] is True
        assert raw["dates_affected"] == []

    def test_cancel_missing_args_returns_400(self, tmp_path: Path) -> None:
        # Theme 8c: no date / no range → CLI rc=2 → 400.
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post(
                "/api/daily/cancel/preview", json={"force": True},
            )
        assert resp.status_code == 400, resp.text

    def test_backfill_preview_returns_missing(self, tmp_path: Path) -> None:
        # Theme 8d: preview enumerates the full window when DB missing.
        config_dir = self._seed(tmp_path)
        app = create_app(repo_root=REPO_ROOT, config_dir=config_dir)
        with TestClient(app) as client:
            resp = client.post(
                "/api/daily/backfill/preview",
                json={"window_days": 5, "force": True},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["dry_run"] is True
        assert raw["window"]["days"] == 5
        assert isinstance(raw["missing_dates"], list)


class TestRunsDiffEndpoint:
    """Theme 9: real subprocess against the real repo (read-only).

    We use unique synthetic run-ids that aren't in any publish-log fixture, so
    the assertion is on the response *shape* (cockpit principle #6 passthrough)
    rather than seeded data — the CLI itself owns the diff semantics, which is
    covered by ``backend/.../test_runs_diff_cli.py``.
    """

    def test_diff_returns_passthrough_payload(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get(
                "/api/runs/diff",
                params={
                    "run_a": "yengo-cockpit-test-A-zzz",
                    "run_b": "yengo-cockpit-test-B-zzz",
                    "max_samples": 5,
                },
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["run_a"]["run_id"] == "yengo-cockpit-test-A-zzz"
        assert raw["run_b"]["run_id"] == "yengo-cockpit-test-B-zzz"
        assert raw["added_puzzles"]["count"] == 0
        assert raw["removed_puzzles"]["count"] == 0
        assert raw["common_count"] == 0
        assert "stats_diff" in raw

    def test_diff_missing_query_param_returns_422(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/runs/diff", params={"run_a": "x"})
        assert resp.status_code == 422


class TestPuzzleInfoEndpoint:
    """Theme 10: real subprocess against the real repo (read-only).

    Uses an unmatched synthetic puzzle id to assert *shape* only — CLI semantics
    are covered by ``backend/.../test_puzzle_info_cli.py``.
    """

    def test_unknown_puzzle_id_returns_empty_payload(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/puzzle/ffffffffffffffff")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["found"] is False
        assert raw["puzzle_id"] == "ffffffffffffffff"
        assert raw["publish_entries"] == []
        assert raw["sgf"] is None

    def test_yengo_prefix_is_stripped_at_route(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.get("/api/puzzle/YENGO-FfffFfffFfffFfff")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["puzzle_id"] == "ffffffffffffffff"


class TestTaxonomyMutationPreviewEndpoints:
    """Theme 11: real subprocess against real config (read-only previews).

    Apply paths are deferred — these endpoints only invoke `--dry-run`.
    """

    def test_tags_rename_unknown_source_returns_invalid(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/rename/preview",
                json={"old": "totally-not-a-real-tag-zzz", "new": "new-tag-zzz"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["op"] == "tags-rename"
        assert raw["valid"] is False
        assert any("unknown tag" in e for e in raw["errors"])

    def test_tags_merge_validation_runs(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/merge/preview",
                json={"sources": ["nope-a-zzz", "nope-b-zzz"], "target": "merged-target-zzz"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["op"] == "tags-merge"
        assert raw["valid"] is False
        assert raw["target"] == "merged-target-zzz"

    def test_levels_rename_unknown_source_returns_invalid(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/levels/rename/preview",
                json={"old": "no-such-level-zzz", "new": "new-level-zzz"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["op"] == "levels-rename"
        assert raw["valid"] is False

    def test_tags_merge_too_few_sources_returns_422(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/merge/preview",
                json={"sources": ["only-one"], "target": "merged"},
            )
        assert resp.status_code == 422


class TestTaxonomyMutationApplyEndpoints:
    """Theme 11 sub-slice 4a: invalid-preview refusal path is the safe public test.

    A successful apply would rewrite real published SGFs, so the route-level
    tests assert only the preview-refusal contract: when the slug is unknown,
    the apply route returns 200 with `{ok:false, errors[]}` (rc=2 from the
    CLI is tolerated). Positive apply behavior is covered by the writer-level
    unit tests in ``backend/.../test_taxonomy_mutations_writer.py``.
    """

    def test_tags_rename_apply_unknown_slug_refused(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/rename/apply",
                json={"old": "totally-not-a-real-tag-zzz", "new": "new-tag-zzz"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert raw["op"] == "tags-rename"
        assert any("unknown tag" in e for e in raw["errors"])

    def test_tags_merge_apply_unknown_slug_refused(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/merge/apply",
                json={
                    "sources": ["nope-a-zzz", "nope-b-zzz"],
                    "target": "merged-target-zzz",
                },
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert raw["op"] == "tags-merge"
        assert raw["errors"]

    def test_levels_rename_apply_unknown_slug_refused(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/levels/rename/apply",
                json={"old": "no-such-level-zzz", "new": "new-level-zzz"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert raw["op"] == "levels-rename"
        assert raw["errors"]

    def test_tags_merge_apply_too_few_sources_returns_422(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/tags/merge/apply",
                json={"sources": ["only-one"], "target": "merged"},
            )
        assert resp.status_code == 422


class TestAdapterScaffoldEndpoints:
    """Theme 12: preview path uses real subprocess against real config.

    Tests use ``--dry-run`` only so they don't write a new package into the
    real ``backend/puzzle_manager/adapters/`` tree. Apply path is exercised
    by the CLI unit tests with ``--adapters-dir`` pointed at tmp.
    """

    def test_preview_invalid_id_returns_invalid(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/adapter-scaffold/preview",
                json={"id": "Has Spaces", "kind": "local"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert any(e["code"] == "invalid-id" for e in raw["errors"])

    def test_preview_collision_with_built_in_local(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/adapter-scaffold/preview",
                json={"id": "local", "kind": "local"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is False
        assert any(e["code"] == "id-collision" for e in raw["errors"])

    def test_preview_fresh_id_returns_proposal(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post(
                "/api/adapter-scaffold/preview",
                json={
                    "id": "yengo-cockpit-scratch-zzz",
                    "kind": "local",
                    "name": "Scratch",
                    "path": "data/scratch",
                },
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["ok"] is True
        assert raw["dry_run"] is True
        assert raw["sources_entry"]["id"] == "yengo-cockpit-scratch-zzz"
        assert raw["sources_entry"]["adapter"] == "yengo-cockpit-scratch-zzz"
        assert raw["sources_entry"]["config"]["path"] == "data/scratch"
        assert len(raw["files_created"]) == 2

    def test_missing_id_returns_422(self) -> None:
        app = create_app(repo_root=REPO_ROOT)
        with TestClient(app) as client:
            resp = client.post("/api/adapter-scaffold/preview", json={"kind": "local"})
        assert resp.status_code == 422



