"""Real-subprocess tests for ``RunController``.

These tests spawn actual ``python`` subprocesses (no mocks). We use small,
deterministic Python scripts so the tests are fast (<1s each) and don't depend
on the puzzle_manager pipeline being in any particular state.

Per PLAN.md §0.4: no mocks. The whole point of this controller is correct
subprocess plumbing — mocked tests would prove nothing about the wire
behavior.
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
import time
from pathlib import Path

import pytest

from tools.yengo_dashboard.server.run_controller import (
    NoSuchRunError,
    RunBusyError,
    RunController,
    TERMINAL_STATUSES,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _wait_until(predicate, timeout: float = 5.0, interval: float = 0.02) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"predicate not satisfied within {timeout}s")


def _make_controller_with_arbitrary_python(tmp_path: Path) -> tuple[RunController, Path]:
    """A controller that runs ``python <script.py>`` instead of ``python -m
    backend.puzzle_manager``. We do this by handing it a tiny shim module so
    the standard ``args`` list still resolves to ``-m <module>`` semantics.

    Implementation: create a fake package directory and prepend it to
    PYTHONPATH so ``-m runctl_test_target`` works. The controller's command
    template is hard-wired to ``-m backend.puzzle_manager``, so for unit
    tests we shadow that module with a fake one of the same name living
    inside ``tmp_path``.
    """
    pkg = tmp_path / "backend" / "puzzle_manager"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    # __main__.py reads the first arg to choose behavior
    (pkg / "__main__.py").write_text(
        textwrap.dedent(
            """
            import sys, time
            mode = sys.argv[1] if len(sys.argv) > 1 else "echo"
            if mode == "echo":
                # Print 3 lines on stdout, 1 on stderr, then exit 0
                print("alpha", flush=True)
                print("beta", flush=True)
                print("warn-line", file=sys.stderr, flush=True)
                print("gamma", flush=True)
                sys.exit(0)
            elif mode == "fail":
                print("about to fail", flush=True)
                sys.exit(7)
            elif mode == "sleep":
                # Print one line then sleep so we can cancel it
                print("sleeping", flush=True)
                try:
                    time.sleep(30)
                except KeyboardInterrupt:
                    print("interrupted", flush=True)
                    sys.exit(130)
                sys.exit(0)
            elif mode == "many":
                n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
                for i in range(n):
                    print(f"line-{i:04d}", flush=True)
                sys.exit(0)
            else:
                print(f"unknown mode {mode!r}", file=sys.stderr, flush=True)
                sys.exit(2)
            """
        ).strip(),
        encoding="utf-8",
    )
    return RunController(repo_root=tmp_path), tmp_path


# ---------------- happy path ----------------


class TestStartAndCapture:
    def test_captures_stdout_and_stderr_then_terminates_completed(
        self, tmp_path: Path
    ) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        snap = controller.start(["echo"])
        assert snap["status"] == "running"
        assert snap["pid"] is not None
        handle = snap["handle"]

        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        final = controller.active()
        assert final["handle"] == handle
        assert final["status"] == "completed"
        assert final["exit_code"] == 0
        assert final["completed_at"] is not None
        assert final["cancel_requested"] is False

        lines = controller.tail()
        texts = [(ln.stream, ln.text) for ln in lines]
        # stdout and stderr both captured; ordering across streams is
        # arrival-order so we don't assert the absolute interleaving, only
        # that all expected lines are present.
        assert ("stdout", "alpha") in texts
        assert ("stdout", "beta") in texts
        assert ("stdout", "gamma") in texts
        assert ("stderr", "warn-line") in texts
        # seq numbers are monotonically increasing
        seqs = [ln.seq for ln in lines]
        assert seqs == sorted(seqs)
        assert final["line_count"] == len(lines)

    def test_nonzero_exit_marks_run_failed(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["fail"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        final = controller.active()
        assert final["status"] == "failed"
        assert final["exit_code"] == 7


class TestBusyGuard:
    def test_second_start_while_first_running_raises(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["sleep"])
        try:
            with pytest.raises(RunBusyError):
                controller.start(["echo"])
        finally:
            handle = controller.active()["handle"]
            controller.cancel(handle)
            _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

    def test_can_start_after_previous_terminal(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["echo"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        # Second start should succeed and reset the tail.
        controller.start(["echo"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        # Tail belongs to the new run, not the old one
        assert controller.active()["status"] == "completed"


class TestCancel:
    def test_cancel_running_run_marks_cancelled(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        snap = controller.start(["sleep"])
        handle = snap["handle"]
        # Wait until at least the initial "sleeping" line lands, so we know
        # the child is past startup.
        _wait_until(lambda: controller.active()["line_count"] >= 1, timeout=3.0)
        controller.cancel(handle)
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES, timeout=10.0)
        final = controller.active()
        assert final["status"] == "cancelled"
        assert final["cancel_requested"] is True
        # exit_code is non-zero (signal-killed), exact value is platform-specific
        assert final["exit_code"] is not None
        assert final["exit_code"] != 0

    def test_cancel_unknown_handle_raises(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["echo"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        with pytest.raises(NoSuchRunError):
            controller.cancel("not-a-real-handle")

    def test_cancel_after_terminal_is_idempotent(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        snap = controller.start(["echo"])
        handle = snap["handle"]
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        # No raise; returns the snapshot unchanged.
        result = controller.cancel(handle)
        assert result["status"] == "completed"


class TestTailRingBuffer:
    def test_tail_truncates_to_configured_size(self, tmp_path: Path) -> None:
        pkg_root = tmp_path
        controller, _ = _make_controller_with_arbitrary_python(pkg_root)
        # Override tail size on the existing controller
        small = RunController(repo_root=pkg_root, tail_size=10)
        small.start(["many", "100"])
        _wait_until(lambda: small.active()["status"] in TERMINAL_STATUSES, timeout=5.0)
        retained = small.tail()
        assert len(retained) == 10
        # We kept the *most recent* 10
        assert retained[0].text == "line-0090"
        assert retained[-1].text == "line-0099"
        # But total line_count reflects all 100 produced
        assert small.active()["line_count"] == 100

    def test_since_seq_filters(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["echo"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)
        all_lines = controller.tail()
        if len(all_lines) < 2:
            pytest.skip("expected >=2 lines from echo fixture")
        cutoff = all_lines[1].seq
        rest = controller.tail(since_seq=cutoff)
        assert all(ln.seq > cutoff for ln in rest)
        assert len(rest) == len(all_lines) - 2


class TestSubscribeDelivery:
    def test_subscriber_receives_lines_and_terminal_event(self, tmp_path: Path) -> None:
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)

        async def consume() -> tuple[list, dict | None, bool]:
            loop = asyncio.get_running_loop()
            sub, backlog = controller.subscribe(loop)
            # Start AFTER subscribing so we don't race the reader threads
            controller.start(["echo"])
            collected_lines = []
            status_snapshot: dict | None = None
            ended = False
            try:
                while True:
                    kind, payload = await asyncio.wait_for(sub.queue.get(), timeout=5.0)
                    if kind == "line":
                        collected_lines.append(payload)
                    elif kind == "status":
                        status_snapshot = payload
                    elif kind == "end":
                        ended = True
                        break
            finally:
                controller.unsubscribe(sub)
            return collected_lines, status_snapshot, ended

        lines, status_snap, ended = asyncio.run(consume())
        assert ended
        assert status_snap is not None
        assert status_snap["status"] == "completed"
        texts = [ln.text for ln in lines]
        # All four lines (3 stdout + 1 stderr) must arrive
        assert "alpha" in texts
        assert "beta" in texts
        assert "gamma" in texts
        assert "warn-line" in texts

    def test_late_subscriber_to_terminal_run_gets_immediate_end(
        self, tmp_path: Path
    ) -> None:
        """A subscriber that arrives after the run is already terminal must
        still receive a status + end pair so its SSE stream completes."""
        controller, _ = _make_controller_with_arbitrary_python(tmp_path)
        controller.start(["echo"])
        _wait_until(lambda: controller.active()["status"] in TERMINAL_STATUSES)

        async def consume() -> tuple[dict | None, bool]:
            loop = asyncio.get_running_loop()
            sub, backlog = controller.subscribe(loop)
            assert backlog, "expected backlog to contain captured lines"
            status_snapshot: dict | None = None
            ended = False
            try:
                while True:
                    kind, payload = await asyncio.wait_for(sub.queue.get(), timeout=2.0)
                    if kind == "status":
                        status_snapshot = payload
                    elif kind == "end":
                        ended = True
                        break
            finally:
                controller.unsubscribe(sub)
            return status_snapshot, ended

        status_snap, ended = asyncio.run(consume())
        assert ended
        assert status_snap is not None
        assert status_snap["status"] == "completed"


# ---------------- real puzzle_manager smoke (slow) ----------------


class TestAgainstRealPipeline:
    @pytest.mark.slow
    def test_validate_subprocess_runs_to_completion_against_real_repo(self) -> None:
        """Drives the real `python -m backend.puzzle_manager validate` —
        a read-only command that exercises the full controller against the
        actual pipeline binary. No state is mutated."""
        controller = RunController(repo_root=REPO_ROOT)
        controller.start(["validate"])
        _wait_until(
            lambda: controller.active()["status"] in TERMINAL_STATUSES,
            timeout=30.0,
        )
        final = controller.active()
        # validate may exit 0 or non-zero depending on repo state; what we
        # care about here is that the controller observed a clean lifecycle,
        # captured at least one line, and recorded a real exit code.
        assert final["status"] in {"completed", "failed"}
        assert final["exit_code"] is not None
        assert final["line_count"] >= 1
        assert final["completed_at"] is not None
