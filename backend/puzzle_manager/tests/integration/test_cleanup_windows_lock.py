"""Windows-only: ``clear_index_state`` must survive a transient file lock.

The cockpit (``tools/pm_cockpit``) reads ``yengo-search.db`` over a SQLite
read-only URI. On Windows, even after the connection's context manager
exits, the OS may still report the file as locked for a few milliseconds
while the SQLite finalizer releases its handle. Issuing ``Path.unlink()``
in that window raises ``PermissionError [WinError 32]`` and crashes
``puzzle_manager clean``.

The cleanup helper ``_unlink_with_retry`` is responsible for absorbing
that transient — these tests assert the contract.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from backend.puzzle_manager.pipeline.cleanup import (
    _unlink_with_retry,
    clear_index_state,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-specific file-lock semantics",
)


def _make_locked_db(path: Path) -> sqlite3.Connection:
    """Create a real SQLite DB at ``path`` and return an open RO connection."""
    with sqlite3.connect(path) as setup:
        setup.execute("CREATE TABLE t (x INTEGER)")
        setup.commit()
    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


class TestUnlinkWithRetry:
    def test_unlinks_immediately_when_no_lock(self, tmp_path: Path) -> None:
        f = tmp_path / "free.bin"
        f.write_bytes(b"x")
        _unlink_with_retry(f)
        assert not f.exists()

    def test_succeeds_after_lock_released_mid_retry(self, tmp_path: Path) -> None:
        # Lock the file, then release on the second attempt by closing the
        # connection from the retry loop's gc.collect() pass.
        db = tmp_path / "locked.db"
        conn = _make_locked_db(db)
        # Drop our reference so gc.collect() inside the retry can finalize it.
        del conn
        _unlink_with_retry(db, attempts=3)
        assert not db.exists()

    def test_raises_permission_error_when_lock_never_releases(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "stuck.db"
        held = _make_locked_db(db)  # noqa: F841 — keep alive across retries
        with pytest.raises(PermissionError):
            _unlink_with_retry(db, attempts=2)
        held.close()


class TestClearIndexStateUnderLock:
    def test_clear_index_state_succeeds_after_ro_reader_drops_handle(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "published"
        out.mkdir()
        (out / "db-version.json").write_text("{}", encoding="utf-8")

        # Build the DB and explicitly close the writer — `with sqlite3.connect()`
        # commits/rollbacks but does NOT close (PEP 249 ambiguity).
        db_path = out / "yengo-search.db"
        setup = sqlite3.connect(db_path)
        try:
            setup.execute("CREATE TABLE t (x INTEGER)")
            setup.commit()
        finally:
            setup.close()

        # Simulate the cockpit pattern: open RO, then let it go out of scope.
        # This is the exact scenario `state_reader.read_inventory()` hits.
        uri = f"file:{db_path.as_posix()}?mode=ro"
        ro = sqlite3.connect(uri, uri=True)
        ro.execute("SELECT 1").fetchone()
        del ro

        cleaned = clear_index_state(out)
        assert cleaned is True
        assert not db_path.exists()
        assert not (out / "db-version.json").exists()
