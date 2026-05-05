"""Single-active-run subprocess controller for pm_cockpit.

Owns one ``subprocess.Popen`` at a time, a reader thread that drains stdout
+ stderr line-by-line, a tail ring buffer, and a fan-out to live SSE
subscriber queues. The actual HTTP / SSE routing lives in ``routes_run.py``;
this module is HTTP-agnostic so it can be unit-tested by spawning real
subprocesses directly.

Concurrency model
-----------------

The pipeline already enforces single-writer via its own config lock; the
cockpit's controller mirrors that by allowing only one active run at a time
across the whole process. ``start()`` raises ``RunBusyError`` if another
run is non-terminal.

Threading model
---------------

Subprocess stdout reading is blocking I/O, so a dedicated daemon thread
drains both ``stdout`` and ``stderr`` (via two reader threads merged into
one queue). The reader threads:

  - push lines into a bounded tail deque (most recent ``tail_size`` lines)
  - notify every active subscriber via ``loop.call_soon_threadsafe`` so the
    asyncio side wakes up cleanly without polling

When the process exits, the controller transitions to a terminal status,
records the exit code, and pushes a sentinel onto every subscriber queue so
SSE generators can complete cleanly.

Per principle #6, this controller does NOT interpret what the pipeline
prints. It captures bytes, attaches timestamps, and forwards. Any
classification ("did this run succeed?") comes from the exit code the OS
reports, not from text parsing.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


class RunBusyError(RuntimeError):
    """Raised when ``start()`` is called while another run is non-terminal."""


class NoSuchRunError(LookupError):
    """Raised when a handle does not match the active or last-known run."""


RunStatus = Literal["starting", "running", "completed", "failed", "cancelled"]
TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})


@dataclass
class LogLine:
    """One captured line. Ordering across stdout/stderr follows wall-clock arrival."""

    ts: str  # ISO-8601 UTC
    stream: Literal["stdout", "stderr"]
    text: str
    seq: int  # monotonic per-run sequence


@dataclass
class RunState:
    """Snapshot of a single run. The controller mutates a single live instance
    in place; consumers take ``.snapshot()`` to get a frozen copy.
    """

    handle: str
    command: list[str]
    cwd: str
    started_at: str
    status: RunStatus = "starting"
    pid: int | None = None
    exit_code: int | None = None
    completed_at: str | None = None
    line_count: int = 0
    cancel_requested: bool = False

    def snapshot(self) -> dict:
        return {
            "handle": self.handle,
            "command": list(self.command),
            "cwd": self.cwd,
            "started_at": self.started_at,
            "status": self.status,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "completed_at": self.completed_at,
            "line_count": self.line_count,
            "cancel_requested": self.cancel_requested,
        }


@dataclass
class _Subscriber:
    """Per-SSE-client queue + the loop that owns it."""

    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop
    # Set when the subscriber drops; the writer side checks before scheduling.
    closed: bool = False


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass
class RunController:
    """Owns at most one active subprocess; multiplexes its output to subscribers.

    Args:
        repo_root: Working directory for the subprocess.
        python_executable: Interpreter to invoke. Defaults to ``sys.executable``.
        tail_size: Maximum number of lines retained for late-joining subscribers.
        terminate_grace_s: Seconds to wait after ``terminate()`` before escalating
            to ``kill()``. Cancelled runs are reported with exit code ``-1`` only
            after the OS confirms the process is gone.
    """

    repo_root: Path
    python_executable: str = sys.executable
    tail_size: int = 1000
    terminate_grace_s: float = 5.0

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _active: RunState | None = field(default=None, init=False, repr=False)
    _proc: subprocess.Popen | None = field(default=None, init=False, repr=False)
    _tail: deque[LogLine] = field(default_factory=deque, init=False, repr=False)
    _subscribers: list[_Subscriber] = field(default_factory=list, init=False, repr=False)
    _seq: int = field(default=0, init=False, repr=False)
    _reader_threads: list[threading.Thread] = field(default_factory=list, init=False, repr=False)
    _wait_thread: threading.Thread | None = field(default=None, init=False, repr=False)

    # ---------------- public API ----------------

    def active(self) -> dict | None:
        """Return a snapshot of the active or last-known run, or None."""
        with self._lock:
            return self._active.snapshot() if self._active is not None else None

    def start(self, args: Iterable[str], *, env_extra: dict[str, str] | None = None) -> dict:
        """Spawn a new subprocess. ``args`` is appended to
        ``[python_executable, "-m", "backend.puzzle_manager"]``.

        Raises ``RunBusyError`` if a non-terminal run is already active.
        """
        cmd = [self.python_executable, "-u", "-m", "backend.puzzle_manager", *args]
        with self._lock:
            if self._active is not None and self._active.status not in TERMINAL_STATUSES:
                raise RunBusyError(
                    f"another run is {self._active.status}: handle={self._active.handle}"
                )
            handle = uuid.uuid4().hex[:16]
            state = RunState(
                handle=handle,
                command=cmd,
                cwd=str(self.repo_root),
                started_at=_utc_iso(),
            )
            # Reset ring buffer for the new run; existing subscribers (if any)
            # already received their terminal sentinel from the prior run's
            # _wait_loop, so they won't double-fire. We do NOT clear
            # self._subscribers here — that would silently drop subscribers
            # that registered before start() (a legal pattern: HTTP can
            # subscribe to "the next run" before POSTing /api/run).
            self._tail.clear()
            self._seq = 0
            self._active = state

        env = os.environ.copy()
        # Subprocess-side line buffering: the -u flag covers Python's own
        # stdout, but PYTHONUNBUFFERED is belt-and-braces for child imports
        # and any subprocesses they spawn.
        env["PYTHONUNBUFFERED"] = "1"
        # Force the child's stdout/stderr to encode as UTF-8 regardless of
        # the host console code page. Without this, a non-ASCII character
        # in CLI output crashes the child with UnicodeEncodeError on
        # Windows (cp1252) before the cockpit ever sees the bytes. This is
        # the root-cause fix; encoding="utf-8" / errors="replace" on the
        # cockpit side (above) only protects the parent's decode.
        env["PYTHONIOENCODING"] = "utf-8"
        existing_pp = env.get("PYTHONPATH", "")
        repo = str(self.repo_root)
        if repo not in existing_pp.split(os.pathsep):
            env["PYTHONPATH"] = (repo + os.pathsep + existing_pp) if existing_pp else repo
        if env_extra:
            env.update(env_extra)

        proc = subprocess.Popen(  # noqa: S603 — args list, no shell
            cmd,
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            # errors="replace" so a stray non-UTF-8 byte (e.g. an emoji on a
            # legacy Windows console) never crashes the cockpit's reader
            # threads with UnicodeDecodeError. The substituted U+FFFD is
            # visible in the log so authors notice and clean up.
            errors="replace",
            bufsize=1,  # line-buffered
        )
        with self._lock:
            self._proc = proc
            state.pid = proc.pid
            state.status = "running"

        # Spawn one reader per stream. They write into the same shared
        # buffer + subscriber list under self._lock.
        for stream_name, fh in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            t = threading.Thread(
                target=self._reader_loop,
                args=(stream_name, fh, state),
                name=f"runctl-{stream_name}-{handle}",
                daemon=True,
            )
            t.start()
            self._reader_threads.append(t)

        # Single waiter thread transitions the run to terminal once both
        # readers see EOF AND the process exits. We use proc.wait() because
        # it's the OS truth; readers may finish slightly before/after.
        self._wait_thread = threading.Thread(
            target=self._wait_loop,
            args=(proc, state, list(self._reader_threads)),
            name=f"runctl-wait-{handle}",
            daemon=True,
        )
        self._wait_thread.start()

        return state.snapshot()

    def cancel(self, handle: str) -> dict:
        """Signal the active run to terminate. No-op if already terminal.

        Raises ``NoSuchRunError`` if ``handle`` doesn't match the current run.
        """
        with self._lock:
            if self._active is None or self._active.handle != handle:
                raise NoSuchRunError(handle)
            state = self._active
            proc = self._proc
            if state.status in TERMINAL_STATUSES:
                return state.snapshot()
            state.cancel_requested = True

        # terminate() outside the lock — Popen handles its own concurrency
        # and we do not want to block subscribers.
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
            # Escalate after grace period in a side thread so cancel() returns
            # immediately. If the process is well-behaved it will exit fast and
            # the killer is a no-op.
            threading.Thread(
                target=self._kill_after_grace,
                args=(proc,),
                name=f"runctl-kill-{handle}",
                daemon=True,
            ).start()

        with self._lock:
            return state.snapshot()

    def tail(self, *, since_seq: int | None = None) -> list[LogLine]:
        """Return retained lines, optionally only those after ``since_seq``."""
        with self._lock:
            if since_seq is None:
                return list(self._tail)
            return [ln for ln in self._tail if ln.seq > since_seq]

    def subscribe(self, loop: asyncio.AbstractEventLoop) -> tuple[_Subscriber, list[LogLine]]:
        """Register a new subscriber. Returns (subscriber, tail_snapshot).

        If the active run is already terminal, the subscriber is enqueued the
        final status + end events immediately, so a late HTTP client always
        completes its SSE stream cleanly without hanging.

        The caller MUST call ``unsubscribe`` (or the subscriber will leak its
        queue — the controller never garbage-collects them).
        """
        sub = _Subscriber(queue=asyncio.Queue(), loop=loop)
        with self._lock:
            self._subscribers.append(sub)
            backlog = list(self._tail)
            terminal_snap: dict | None = None
            if self._active is not None and self._active.status in TERMINAL_STATUSES:
                terminal_snap = self._active.snapshot()
        if terminal_snap is not None:
            self._enqueue(sub, ("status", terminal_snap))
            self._enqueue(sub, ("end", None))
        return sub, backlog

    def unsubscribe(self, sub: _Subscriber) -> None:
        with self._lock:
            sub.closed = True
            try:
                self._subscribers.remove(sub)
            except ValueError:
                pass

    # ---------------- internals ----------------

    def _kill_after_grace(self, proc: subprocess.Popen) -> None:
        try:
            proc.wait(timeout=self.terminate_grace_s)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass

    def _reader_loop(
        self,
        stream_name: Literal["stdout", "stderr"],
        fh,
        state: RunState,
    ) -> None:
        # iter(fh.readline, "") yields until EOF; readline is blocking so the
        # thread sleeps when there's nothing to read.
        try:
            for raw in iter(fh.readline, ""):
                line = LogLine(
                    ts=_utc_iso(),
                    stream=stream_name,
                    text=raw.rstrip("\n"),
                    seq=0,  # placeholder, set under lock
                )
                self._publish_line(line, state)
        finally:
            try:
                fh.close()
            except Exception:
                pass

    def _publish_line(self, line: LogLine, state: RunState) -> None:
        """Append to tail, increment counters, fan out to subscribers."""
        with self._lock:
            self._seq += 1
            line.seq = self._seq
            self._tail.append(line)
            while len(self._tail) > self.tail_size:
                self._tail.popleft()
            state.line_count = self._seq
            subs = list(self._subscribers)
        for sub in subs:
            self._enqueue(sub, ("line", line))

    def _enqueue(self, sub: _Subscriber, item: tuple) -> None:
        if sub.closed:
            return
        try:
            sub.loop.call_soon_threadsafe(sub.queue.put_nowait, item)
        except RuntimeError:
            # Loop is closed (subscriber's request finished). Mark and drop.
            sub.closed = True

    def _wait_loop(
        self,
        proc: subprocess.Popen,
        state: RunState,
        readers: list[threading.Thread],
    ) -> None:
        # Block until the OS reports exit. proc.wait() is the source of truth
        # for the exit code; readers may have finished moments earlier or
        # later but exit_code is owned by Popen.
        rc = proc.wait()
        for t in readers:
            t.join(timeout=2.0)
        with self._lock:
            state.completed_at = _utc_iso()
            state.exit_code = rc
            if state.cancel_requested:
                state.status = "cancelled"
            elif rc == 0:
                state.status = "completed"
            else:
                state.status = "failed"
            subs = list(self._subscribers)
            terminal_snapshot = state.snapshot()
        for sub in subs:
            self._enqueue(sub, ("status", terminal_snapshot))
            self._enqueue(sub, ("end", None))
