"""
Pipeline execution lock for serializing pipeline and rollback operations.

Replaces config/lock.py (ConfigLock) with atomic O_CREAT|O_EXCL creation
and PID-alive crash recovery. Single serialization point for:
- Pipeline runs (coordinator.py)
- Rollback operations (rollback.py)
- Config modifications (loader.py — read-only guard)

Lock lifecycle:
    acquire() → O_CREAT|O_EXCL write {run_id, pid, hostname, acquired_at}
      if file exists: check PID alive → if dead: auto-recover
    ...pipeline/rollback runs...
    release() → delete lock file
"""

from __future__ import annotations

import atexit
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from backend.puzzle_manager.exceptions import PipelineError
from backend.puzzle_manager.paths import get_runtime_dir

logger = logging.getLogger("puzzle_manager.pipeline.lock")

_LOCK_FILENAME = "pipeline.lock"


class PipelineLockError(PipelineError):
    """Raised when the pipeline lock cannot be acquired."""
    pass


def _get_lock_path() -> Path:
    """Get path to pipeline lock file."""
    return get_runtime_dir() / _LOCK_FILENAME


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    if pid <= 0:
        return False
    try:
        # os.kill(pid, 0) doesn't kill — just checks existence
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True
    except OSError:
        return False


class PipelineLock:
    """Atomic pipeline execution lock with crash recovery.

    Uses os.open(O_CREAT | O_EXCL) for kernel-level atomic creation.
    Detects stale locks from crashed processes via PID-alive check.

    Usage:
        lock = PipelineLock(run_id="20260220-abc12345")
        lock.acquire()
        try:
            # ... pipeline or rollback runs ...
        finally:
            lock.release()
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or "unknown"
        self.lock_path = _get_lock_path()
        self._acquired = False

    def acquire(self, _retry: bool = False) -> None:
        """Acquire the pipeline lock atomically.

        If a stale lock exists (PID dead), auto-recovers by deleting it.

        Raises:
            PipelineLockError: If lock is held by a live process.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_info = {
            "run_id": self.run_id,
            "pid": os.getpid(),
            "hostname": os.environ.get(
                "COMPUTERNAME", os.environ.get("HOSTNAME", "unknown")
            ),
            "acquired_at": datetime.now(UTC).isoformat(),
        }
        lock_json = json.dumps(lock_info, indent=2)

        try:
            # Atomic create — fails if file exists
            fd = os.open(
                str(self.lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            os.write(fd, lock_json.encode("utf-8"))
            os.close(fd)
            self._acquired = True
            # Safety net: release on interpreter exit
            atexit.register(self._atexit_release)
            logger.info("Pipeline lock acquired: run_id=%s", self.run_id)
            return
        except FileExistsError:
            pass  # Lock file exists — check if stale

        # Lock exists — check if holder is still alive
        existing = self._read_lock_info()
        if existing is None:
            # Corrupt lock file — treat as stale (one retry only)
            if not _retry:
                logger.warning("Corrupt pipeline lock file, removing")
                self._force_remove()
                self.acquire(_retry=True)
                return
            raise PipelineLockError("Failed to acquire lock after removing corrupt lock file")

        holder_pid = existing.get("pid", 0)
        if _is_pid_alive(holder_pid):
            raise PipelineLockError(
                f"Pipeline already running: run_id={existing.get('run_id')}, "
                f"pid={holder_pid}, acquired_at={existing.get('acquired_at')}"
            )

        # Stale lock — holder process is dead, auto-recover (one retry only)
        if not _retry:
            logger.warning(
                "Stale pipeline lock detected (pid=%d dead), auto-recovering",
                holder_pid,
            )
            self._force_remove()
            self.acquire(_retry=True)
            return
        raise PipelineLockError("Failed to acquire lock after removing stale lock")

    def release(self) -> None:
        """Release the pipeline lock."""
        if not self._acquired:
            return
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.info("Pipeline lock released: run_id=%s", self.run_id)
        except OSError as e:
            logger.error("Failed to release pipeline lock: %s", e)
        finally:
            self._acquired = False

    def _atexit_release(self) -> None:
        """Release lock on interpreter exit (safety net)."""
        if self._acquired:
            try:
                self.release()
            except Exception:
                pass

    def _read_lock_info(self) -> dict | None:
        """Read current lock file info."""
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _force_remove(self) -> None:
        """Force-remove the lock file."""
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError as e:
            logger.error("Failed to remove stale lock: %s", e)

    @classmethod
    def is_locked(cls) -> bool:
        """Check if pipeline lock is currently held."""
        return _get_lock_path().exists()

    @classmethod
    def get_lock_info(cls) -> dict | None:
        """Get current lock info, or None if not locked."""
        lock_path = _get_lock_path()
        if not lock_path.exists():
            return None
        try:
            with open(lock_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @classmethod
    def force_release(cls) -> bool:
        """Force-release the pipeline lock (for CLI recovery).

        Returns:
            True if lock was released, False if no lock existed.
        """
        lock_path = _get_lock_path()
        if not lock_path.exists():
            return False
        try:
            lock_path.unlink()
            logger.info("Pipeline lock force-released")
            return True
        except OSError as e:
            raise PipelineLockError(f"Failed to force-release lock: {e}") from e

    def __enter__(self) -> PipelineLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


def check_pipeline_lock(force: bool = False) -> None:
    """Check if pipeline is locked before modifying config.

    Drop-in replacement for config/lock.py's check_config_lock().

    Args:
        force: If True, skip the lock check.

    Raises:
        PipelineLockError: If pipeline is locked and force is False.
    """
    if force:
        return

    if PipelineLock.is_locked():
        lock_info = PipelineLock.get_lock_info()
        raise PipelineLockError(
            f"Cannot modify config while pipeline is running. "
            f"Run: '{lock_info.get('run_id', 'unknown')}' "
            f"(PID {lock_info.get('pid')}). "
            f"Wait for completion or use --force to override."
        )
