"""Real-fixture TestClient tests for /api/clean, /api/rollback, /api/vacuum-db.

Same pattern as ``test_routes_run.py``: a tmp ``backend/puzzle_manager``
package shim that mimics the maintenance subcommands the cockpit cares
about. We inject a custom ``RunController`` whose ``repo_root`` points at
the shim so the cockpit code path is identical (real subprocess, real
Popen, real reader threads, real argv translation), but no real
``.pm-runtime/`` or ``yengo-puzzle-collections/`` is touched.
"""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tools.yengo_dashboard.server.app import create_app
from tools.yengo_dashboard.server.run_controller import TERMINAL_STATUSES, RunController

REAL_REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_fake_pipeline_repo(tmp_path: Path) -> Path:
    """Build a tmp 'repo' whose ``backend/puzzle_manager`` package handles
    the maintenance subcommands by echoing the argv it received. Tests then
    assert against ``snap.command`` (which the cockpit captures verbatim).

    Modes:
      - ``clean [...]``     → prints "clean " + args, exits 0
      - ``rollback [...]``  → prints "rollback " + args, exits 0
      - ``vacuum-db [...]`` → prints "vacuum " + args, exits 0
      - anything else       → exit 2
    """
    pkg = tmp_path / "backend" / "puzzle_manager"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__main__.py").write_text(
        textwrap.dedent(
            """
            import sys
            argv = sys.argv[1:]
            cmd = argv[0] if argv else "help"
            if cmd in ("clean", "rollback", "vacuum-db"):
                print(f"{cmd}-start", flush=True)
                print("argv: " + " ".join(argv[1:]), flush=True)
                print(f"{cmd}-done", flush=True)
                sys.exit(0)
            print(f"unknown subcommand {cmd!r}", file=sys.stderr, flush=True)
            sys.exit(2)
            """
        ).strip(),
        encoding="utf-8",
    )
    return tmp_path


def _make_test_app(tmp_path: Path) -> tuple[TestClient, RunController]:
    fake_repo = _make_fake_pipeline_repo(tmp_path)
    controller = RunController(repo_root=fake_repo)
    app = create_app(repo_root=REAL_REPO_ROOT, controller=controller)
    return TestClient(app), controller


def _wait_until(predicate, timeout: float = 8.0, interval: float = 0.05) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"predicate not satisfied within {timeout}s")


# ---------------- clean ----------------


class TestClean:
    def test_default_clean_passes_no_extra_flags(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/clean", json={})
            assert resp.status_code == 202, resp.text
            snap = resp.json()
            assert snap["command"][-1] == "clean"
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
            final = controller.active()
            assert final["status"] == "completed"
            assert final["exit_code"] == 0

    def test_target_and_retention_flags_threaded_through(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/clean",
                json={"target": "logs", "retention_days": 7},
            )
            assert resp.status_code == 202
            cmd = resp.json()["command"]
            assert "--target" in cmd and cmd[cmd.index("--target") + 1] == "logs"
            assert "--retention-days" in cmd and cmd[cmd.index("--retention-days") + 1] == "7"
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_dry_run_explicit_value_forwarded(self, tmp_path: Path) -> None:
        # The CLI accepts --dry-run [BOOL]. The cockpit forwards it as a
        # discrete "true"/"false" string so the operator's intent is
        # preserved (None means "let the CLI decide").
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/clean",
                json={"target": "puzzles-collection", "dry_run": False},
            )
            cmd = resp.json()["command"]
            assert "--dry-run" in cmd
            assert cmd[cmd.index("--dry-run") + 1] == "false"
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_clean_busy_returns_409_when_run_active(self, tmp_path: Path) -> None:
        # Override the shim to sleep so there's a window for a second call.
        fake_repo = _make_fake_pipeline_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            textwrap.dedent(
                """
                import sys, time
                if sys.argv[1:2] == ["clean"]:
                    print("started", flush=True)
                    try: time.sleep(30)
                    except KeyboardInterrupt: pass
                    sys.exit(0)
                sys.exit(2)
                """
            ).strip(),
            encoding="utf-8",
        )
        controller = RunController(repo_root=fake_repo)
        app = create_app(repo_root=REAL_REPO_ROOT, controller=controller)
        with TestClient(app) as client:
            r1 = client.post("/api/clean", json={})
            assert r1.status_code == 202
            handle = r1.json()["handle"]
            try:
                _wait_until(lambda: controller.active()["line_count"] >= 1)
                r2 = client.post("/api/clean", json={})
                assert r2.status_code == 409
            finally:
                client.post(f"/api/run/{handle}/cancel")
                _wait_until(
                    lambda: controller.active()["status"] in TERMINAL_STATUSES,
                    timeout=10.0,
                )


# ---------------- rollback ----------------


class TestRollback:
    def test_run_id_path_forwards_required_flags(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/rollback",
                json={"run_id": "20260505-deadbeef", "reason": "test cleanup"},
            )
            assert resp.status_code == 202, resp.text
            cmd = resp.json()["command"]
            assert "--run-id" in cmd and cmd[cmd.index("--run-id") + 1] == "20260505-deadbeef"
            assert "--reason" in cmd and cmd[cmd.index("--reason") + 1] == "test cleanup"
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_puzzle_ids_field_rejected_as_extra_or_ignored(self, tmp_path: Path) -> None:
        """Per Theme 17, the rollback contract no longer accepts puzzle_ids.
        The CLI never implemented per-puzzle rollback (RollbackManager only
        had ``rollback_by_run``); the prior --puzzle-id surface was a dead
        argparse arm. Sending the field today must NOT smuggle a
        --puzzle-id flag back into the CLI invocation."""
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/rollback",
                json={
                    "run_id": "20260505-deadbeef",
                    "puzzle_ids": ["abc123def4567890"],
                    "reason": "regression guard",
                },
            )
            # Either Pydantic rejects unknown fields (422) or it silently
            # drops them (202). Both are acceptable; the load-bearing
            # assertion is that --puzzle-id never reaches the CLI.
            assert resp.status_code in (202, 422), resp.text
            if resp.status_code == 202:
                cmd = resp.json()["command"]
                assert "--puzzle-id" not in cmd
                assert "--run-id" in cmd
                _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_missing_run_id_returns_422(self, tmp_path: Path) -> None:
        # run_id is a required field on RollbackRequest (Theme 17).
        client, _ = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/rollback", json={"reason": "x"})
        assert resp.status_code == 422

    def test_empty_reason_returns_422(self, tmp_path: Path) -> None:
        # The cockpit refuses an empty reason at the schema layer; the audit
        # trail requirement is non-negotiable.
        client, _ = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/rollback",
                json={"run_id": "abc", "reason": ""},
            )
        assert resp.status_code == 422


# ---------------- vacuum-db ----------------


class TestVacuumDb:
    def test_default_invocation(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/vacuum-db", json={})
            assert resp.status_code == 202, resp.text
            cmd = resp.json()["command"]
            assert cmd[-1] == "vacuum-db"
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_rebuild_and_dry_run_flags(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post(
                "/api/vacuum-db",
                json={"rebuild": True, "dry_run": True},
            )
            cmd = resp.json()["command"]
            assert "--rebuild" in cmd
            assert "--dry-run" in cmd
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)


# ---------------- mutual exclusion via shared RunController ----------------


class TestSerializationAcrossSubcommands:
    def test_rollback_returns_409_while_clean_running(self, tmp_path: Path) -> None:
        """The cockpit's single-active-run guard is shared across all
        mutating subcommands, not just ``run``. This is the safety property
        that prevents 'clean while rolling back' footguns."""
        fake_repo = _make_fake_pipeline_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            textwrap.dedent(
                """
                import sys, time
                cmd = sys.argv[1] if len(sys.argv) > 1 else ""
                if cmd in ("clean", "rollback", "vacuum-db"):
                    print(f"{cmd} started", flush=True)
                    try: time.sleep(30)
                    except KeyboardInterrupt: pass
                    sys.exit(0)
                sys.exit(2)
                """
            ).strip(),
            encoding="utf-8",
        )
        controller = RunController(repo_root=fake_repo)
        app = create_app(repo_root=REAL_REPO_ROOT, controller=controller)
        with TestClient(app) as client:
            r1 = client.post("/api/clean", json={})
            assert r1.status_code == 202
            handle = r1.json()["handle"]
            try:
                _wait_until(lambda: controller.active()["line_count"] >= 1)
                r2 = client.post(
                    "/api/rollback",
                    json={"run_id": "abc", "reason": "x"},
                )
                assert r2.status_code == 409
                r3 = client.post("/api/vacuum-db", json={})
                assert r3.status_code == 409
            finally:
                client.post(f"/api/run/{handle}/cancel")
                _wait_until(
                    lambda: controller.active()["status"] in TERMINAL_STATUSES,
                    timeout=10.0,
                )


# ---------------- preview endpoints (Theme 1d) ----------------
#
# Preview endpoints flow through ``PipelineRunner`` (subprocess + JSON
# parse), not ``RunController``. The fake-repo shim therefore needs to
# emit valid CleanPreview/RollbackPreview/VacuumDbPreview JSON when the
# CLI is invoked with ``--dry-run --json``. The runner is rooted at the
# fake repo (``create_app(repo_root=fake_repo)``) so the subprocess path
# is real but no actual pipeline state is touched.


def _make_fake_preview_repo(tmp_path: Path) -> Path:
    """Build a tmp 'repo' whose ``__main__`` emits valid preview JSON.

    Each subcommand recognises ``--dry-run --json`` and writes a stable
    payload that matches the corresponding ``CleanPreview`` /
    ``RollbackPreview`` / ``VacuumDbPreview`` shape. Anything else exits 2
    so a misrouted invocation surfaces immediately.
    """
    pkg = tmp_path / "backend" / "puzzle_manager"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__main__.py").write_text(
        textwrap.dedent(
            """
            import json
            import sys

            argv = sys.argv[1:]
            cmd = argv[0] if argv else ""
            rest = argv[1:]
            is_dry = "--dry-run" in rest
            is_json = "--json" in rest

            def _val(flag, default=None):
                if flag in rest:
                    i = rest.index(flag)
                    if i + 1 < len(rest):
                        return rest[i + 1]
                return default

            if cmd == "clean" and is_dry and is_json:
                target = _val("--target")
                retention = int(_val("--retention-days") or 45)
                payload = {
                    "target": target,
                    "retention_days": retention,
                    "would_delete": [
                        {"path": ".pm-runtime/logs/old.log", "bytes": 123}
                    ],
                    "total_files": 1,
                    "total_bytes": 123,
                    "errors": [],
                }
                print(json.dumps(payload))
                sys.exit(0)

            if cmd == "rollback" and is_dry and is_json:
                run_id = _val("--run-id") or ""
                payload = {
                    "affected_puzzles": ["abc123def4567890"],
                    "affected_runs": [run_id],
                    "puzzles_affected": 1,
                    "reversible": False,
                    "errors": [],
                }
                print(json.dumps(payload))
                sys.exit(0)

            if cmd == "vacuum-db" and is_dry and is_json:
                rebuild = "--rebuild" in rest
                payload = {
                    "orphan_rows": 3,
                    "on_disk_files": 42,
                    "freed_bytes_estimate": 12288,
                    "rebuild": rebuild,
                    "has_content_db": True,
                }
                print(json.dumps(payload))
                sys.exit(0)

            print(f"unexpected argv: {argv!r}", file=sys.stderr)
            sys.exit(2)
            """
        ).strip(),
        encoding="utf-8",
    )
    return tmp_path


def _make_preview_test_app(tmp_path: Path) -> TestClient:
    """Build a TestClient whose runner points at a preview-emitting shim."""
    fake_repo = _make_fake_preview_repo(tmp_path)
    # Controller still uses the same fake repo so nothing else breaks if a
    # preview test accidentally hits a mutating route.
    controller = RunController(repo_root=fake_repo)
    app = create_app(repo_root=fake_repo, controller=controller)
    return TestClient(app)


class TestCleanPreview:
    def test_default_invocation_returns_raw_payload(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get("/api/clean/preview")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "raw" in body
        raw = body["raw"]
        assert raw["target"] is None
        assert raw["retention_days"] == 45
        assert raw["total_files"] == 1
        assert raw["would_delete"][0]["path"].endswith("old.log")

    def test_target_and_retention_flow_through(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get(
                "/api/clean/preview",
                params={"target": "logs", "retention_days": 7},
            )
        assert resp.status_code == 200
        raw = resp.json()["raw"]
        assert raw["target"] == "logs"
        assert raw["retention_days"] == 7

    def test_cli_failure_maps_to_502(self, tmp_path: Path) -> None:
        # Replace shim to fail clean/--dry-run/--json deterministically.
        fake_repo = _make_fake_preview_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            "import sys\nprint('boom', file=sys.stderr)\nsys.exit(1)\n",
            encoding="utf-8",
        )
        controller = RunController(repo_root=fake_repo)
        app = create_app(repo_root=fake_repo, controller=controller)
        with TestClient(app) as client:
            resp = client.get("/api/clean/preview")
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["returncode"] == 1
        assert "boom" in detail["stderr"]


class TestRollbackPreview:
    def test_run_id_required(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get("/api/rollback/preview")
        assert resp.status_code == 422

    def test_run_id_threads_through(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get(
                "/api/rollback/preview",
                params={"run_id": "20260505-deadbeef"},
            )
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["affected_runs"] == ["20260505-deadbeef"]
        assert raw["puzzles_affected"] == 1
        assert raw["reversible"] is False

    def test_explicit_reason_overrides_default(self, tmp_path: Path) -> None:
        # The cockpit supplies "preview-only" when the operator hasn't
        # entered a reason yet; an explicit reason must override it.
        # Augment the shim to fail loudly if --reason is missing and to
        # echo the value back through affected_runs.
        fake_repo = _make_fake_preview_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            textwrap.dedent(
                """
                import json, sys
                argv = sys.argv[1:]
                if argv[:1] == ["rollback"] and "--reason" not in argv:
                    print("missing --reason", file=sys.stderr)
                    sys.exit(2)
                i = argv.index("--reason")
                reason = argv[i + 1]
                print(json.dumps({
                    "affected_puzzles": [],
                    "affected_runs": [reason],
                    "puzzles_affected": 0,
                    "reversible": False,
                    "errors": [],
                }))
                sys.exit(0)
                """
            ).strip(),
            encoding="utf-8",
        )
        controller = RunController(repo_root=fake_repo)
        app = create_app(repo_root=fake_repo, controller=controller)
        with TestClient(app) as client:
            resp = client.get(
                "/api/rollback/preview",
                params={"run_id": "abc", "reason": "operator-supplied"},
            )
        assert resp.status_code == 200
        raw = resp.json()["raw"]
        assert raw["affected_runs"] == ["operator-supplied"]


class TestVacuumDbPreview:
    def test_default_invocation(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get("/api/vacuum-db/preview")
        assert resp.status_code == 200, resp.text
        raw = resp.json()["raw"]
        assert raw["orphan_rows"] == 3
        assert raw["on_disk_files"] == 42
        assert raw["rebuild"] is False
        assert raw["has_content_db"] is True

    def test_rebuild_flag_threads_through(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            resp = client.get(
                "/api/vacuum-db/preview", params={"rebuild": True}
            )
        assert resp.status_code == 200
        assert resp.json()["raw"]["rebuild"] is True


class TestPreviewIsIdempotent:
    """Preview endpoints are GET so they MUST be safe to retry without
    side effects. This is asserted indirectly by checking the runner is
    re-entrant — repeated calls return identical payloads."""

    def test_repeated_calls_return_same_payload(self, tmp_path: Path) -> None:
        client = _make_preview_test_app(tmp_path)
        with client:
            r1 = client.get("/api/clean/preview")
            r2 = client.get("/api/clean/preview")
        assert r1.status_code == r2.status_code == 200
        assert r1.json() == r2.json()
