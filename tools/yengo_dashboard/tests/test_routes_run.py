"""Real-fixture TestClient tests for /api/run* and SSE.

We cannot drive ``python -m backend.puzzle_manager run`` in a unit test
without consequences — the real pipeline writes to ``.pm-runtime/`` and
``yengo-puzzle-collections/``. Instead we mount a custom ``RunController``
whose ``repo_root`` is a tmp directory containing a *fake*
``backend/puzzle_manager`` package. The cockpit code path is identical
(real subprocess, real Popen, real reader threads, real SSE), only the
target binary is a tiny print-and-exit shim.

This is the same pattern as ``test_run_controller.py`` — see
``_make_fake_pipeline_repo``.
"""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools.yengo_dashboard.server.app import create_app
from tools.yengo_dashboard.server.run_controller import RunController, TERMINAL_STATUSES

REAL_REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_fake_pipeline_repo(tmp_path: Path) -> Path:
    """Build a tmp 'repo' whose ``backend/puzzle_manager`` package is a tiny
    shim that mimics the subset of CLI shapes the cockpit cares about.

    Modes:
      - ``run [args...]``  → prints 5 lines including a fake run-id, exits 0
      - ``run --dry-run``  → prints "dry" then exits 0
      - ``run --fail``     → prints then exits 7
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
            if cmd == "run":
                if "--fail" in argv:
                    print("starting fail run", flush=True)
                    print("error: oh no", file=sys.stderr, flush=True)
                    sys.exit(7)
                print("starting run", flush=True)
                print("source: " + (argv[argv.index("--source")+1] if "--source" in argv else "default"), flush=True)
                print("stage: " + (argv[argv.index("--stage")+1] if "--stage" in argv else "all"), flush=True)
                if "--dry-run" in argv:
                    print("dry-run mode", flush=True)
                print("done", flush=True)
                sys.exit(0)
            print("unknown subcommand", file=sys.stderr, flush=True)
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


class TestActiveAndStart:
    def test_active_returns_null_before_any_run(self, tmp_path: Path) -> None:
        client, _ = _make_test_app(tmp_path)
        with client:
            resp = client.get("/api/run/active")
        assert resp.status_code == 200
        assert resp.json() == {"active": None}

    def test_post_run_starts_subprocess_and_completes(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/run", json={"source": "fixture-src"})
            assert resp.status_code == 202, resp.text
            snap = resp.json()
            assert snap["status"] in {"starting", "running", "completed"}
            assert "run" in snap["command"]
            assert "--source" in snap["command"]
            handle = snap["handle"]

            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

            active_resp = client.get("/api/run/active")
            assert active_resp.status_code == 200
            active = active_resp.json()["active"]
            assert active["handle"] == handle
            assert active["status"] == "completed"
            assert active["exit_code"] == 0
            assert active["line_count"] >= 4

    def test_post_run_with_dry_run_passes_flag_through(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/run", json={"dry_run": True})
            assert resp.status_code == 202
            snap = resp.json()
            assert "--dry-run" in snap["command"]
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_409_when_run_already_active(self, tmp_path: Path) -> None:
        # Make the first run a long-sleeping process so we have a window.
        # We rebuild the shim to add a "sleep" mode for this test.
        fake_repo = _make_fake_pipeline_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            textwrap.dedent(
                """
                import sys, time
                if sys.argv[1:2] == ["run"]:
                    print("started, sleeping", flush=True)
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
            r1 = client.post("/api/run", json={})
            assert r1.status_code == 202
            handle = r1.json()["handle"]
            try:
                _wait_until(lambda: controller.active()["line_count"] >= 1)
                r2 = client.post("/api/run", json={})
                assert r2.status_code == 409
                assert "another run" in r2.json()["detail"]
            finally:
                client.post(f"/api/run/{handle}/cancel")
                _wait_until(
                    lambda: controller.active()["status"] in TERMINAL_STATUSES,
                    timeout=10.0,
                )


class TestCancel:
    def test_cancel_unknown_handle_returns_404(self, tmp_path: Path) -> None:
        client, _ = _make_test_app(tmp_path)
        with client:
            resp = client.post("/api/run/nope/cancel")
        assert resp.status_code == 404

    def test_cancel_running_run_marks_cancelled(self, tmp_path: Path) -> None:
        fake_repo = _make_fake_pipeline_repo(tmp_path)
        (fake_repo / "backend" / "puzzle_manager" / "__main__.py").write_text(
            textwrap.dedent(
                """
                import sys, time
                if sys.argv[1:2] == ["run"]:
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
            r1 = client.post("/api/run", json={})
            handle = r1.json()["handle"]
            _wait_until(lambda: controller.active()["line_count"] >= 1)
            r2 = client.post(f"/api/run/{handle}/cancel")
            assert r2.status_code == 202
            assert r2.json()["cancel_requested"] is True
            _wait_until(
                lambda: controller.active()["status"] in TERMINAL_STATUSES,
                timeout=10.0,
            )
            assert controller.active()["status"] == "cancelled"


class TestSSE:
    def test_sse_streams_lines_then_status_then_end(self, tmp_path: Path) -> None:
        client, controller = _make_test_app(tmp_path)
        with client:
            r1 = client.post("/api/run", json={})
            assert r1.status_code == 202
            handle = r1.json()["handle"]
            _wait_until(
                lambda: controller.active()["status"] in TERMINAL_STATUSES,
                timeout=8.0,
            )
            # Subscribe AFTER terminal: late-subscriber path replays backlog
            # and immediately emits status + end. This is the deterministic
            # assertion path; the live-stream path is exercised by the
            # underlying RunController tests.
            with client.stream("GET", f"/api/run/{handle}/events") as resp:
                assert resp.status_code == 200
                assert resp.headers["content-type"].startswith("text/event-stream")
                events = _parse_sse(resp.iter_lines(), max_events=20, deadline_s=5.0)
        kinds = [ev["event"] for ev in events]
        assert "line" in kinds
        assert "status" in kinds
        assert "end" in kinds
        # The last event must be "end"
        assert kinds[-1] == "end"
        # At least one "line" carries one of the printed strings
        line_texts = [ev["data"]["text"] for ev in events if ev["event"] == "line"]
        assert any("starting run" in t or "done" in t for t in line_texts)

    def test_sse_404_when_handle_does_not_match_active(self, tmp_path: Path) -> None:
        client, _ = _make_test_app(tmp_path)
        with client:
            resp = client.get("/api/run/nope/events")
        assert resp.status_code == 404


def _parse_sse(line_iter, *, max_events: int, deadline_s: float) -> list[dict]:
    """Parse SSE frames from a synchronous line iterator. Stops at ``end`` or
    when ``max_events`` is reached. ``deadline_s`` guards against hangs."""
    import json as _json
    out: list[dict] = []
    current_event = None
    current_data_lines: list[str] = []
    start = time.monotonic()
    for raw in line_iter:
        if time.monotonic() - start > deadline_s:
            break
        line = raw if isinstance(raw, str) else raw.decode("utf-8")
        if line == "":
            if current_event is not None:
                data_str = "\n".join(current_data_lines)
                try:
                    data = _json.loads(data_str) if data_str else {}
                except _json.JSONDecodeError:
                    data = {"_raw": data_str}
                out.append({"event": current_event, "data": data})
                if current_event == "end":
                    break
                if len(out) >= max_events:
                    break
            current_event = None
            current_data_lines = []
            continue
        if line.startswith(":"):
            continue  # SSE comment / keepalive
        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: "):
            current_data_lines.append(line[len("data: "):])
    return out
