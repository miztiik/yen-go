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
from tools.yengo_dashboard.server.run_controller import RunController, TERMINAL_STATUSES

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
