"""Pure-passthrough reads of pipeline state files.

Per principle #6, the cockpit may read SQLite/JSON state as raw data — without
re-deriving meaning. This module owns the *file paths* (which directories
contain what) and the JSON shapes the backend writes. It MUST NOT:

  - parse SGF
  - compute hashes
  - join across tables to invent new domain views
  - reformat status enums into "friendlier" strings
  - **open yengo-search.db** — the cockpit reads ``inventory.json`` (a
    backend-written snapshot) instead, to keep file handles out of the
    presentation layer (Windows file-lock contention with vacuum/rollback).

If the UI ever needs anything that requires interpretation, the rule is "add
a CLI subcommand or read-only query method to puzzle_manager first."

Path conventions are documented in the root ``CLAUDE.md`` (SQLite Query
Architecture and Runtime Directories).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class StateReader:
    """Reads cockpit-facing state files (inventory snapshot + run JSON).

    Args:
        repo_root: Repository root. The reader resolves all paths relative to
            this directory.
        runtime_dir: Override of the pipeline runtime root (matches
            ``YENGO_RUNTIME_DIR`` semantics). Defaults to ``repo_root /
            ".pm-runtime"``.
        published_dir: Override of the published collection root. Defaults to
            ``repo_root / "yengo-puzzle-collections"``.
    """

    repo_root: Path
    runtime_dir: Path | None = None
    published_dir: Path | None = None

    def _runtime(self) -> Path:
        return self.runtime_dir or (self.repo_root / ".pm-runtime")

    def _published(self) -> Path:
        return self.published_dir or (self.repo_root / "yengo-puzzle-collections")

    def _search_db_path(self) -> Path:
        return self._published() / "yengo-search.db"

    def _inventory_snapshot_path(self) -> Path:
        return self._published() / "inventory.json"

    def _runs_dir(self) -> Path:
        return self._runtime() / "state" / "runs"

    def _rel_posix(self, p: Path) -> str:
        try:
            return PurePosixPath(p.relative_to(self.repo_root).as_posix()).as_posix()
        except ValueError:
            # Path lives outside repo_root (test fixtures, custom YENGO_RUNTIME_DIR).
            # Fall back to the absolute POSIX form so the UI still has something
            # to display, even though it won't be reproducible across machines.
            return PurePosixPath(p.as_posix()).as_posix()

    def read_inventory(self) -> dict:
        """Return the published inventory snapshot.

        Reads ``yengo-puzzle-collections/inventory.json`` — a JSON file the
        backend rewrites atomically after every publish/vacuum/rollback. The
        cockpit never opens ``yengo-search.db`` directly; that file is owned
        by the pipeline and Windows file-lock contention with vacuum/clean
        was the original motivation for this snapshot pattern.

        When the snapshot does not exist (fresh checkout, never-published
        repo, or pre-snapshot pipeline version), returns zeros plus
        ``snapshot_exists=False`` and an ``advice`` string telling the UI to
        prompt the operator to run vacuum-db. The DB existence flag is still
        reported (cheap stat) so the operator can tell "no data" from "data
        present but unsnapshotted".
        """
        snapshot = self._inventory_snapshot_path()
        db = self._search_db_path()
        empty = {
            "db_path": self._rel_posix(db),
            "db_exists": db.exists(),
            "snapshot_exists": False,
            "snapshot_path": self._rel_posix(snapshot),
            "advice": (
                "Run 'puzzle_manager vacuum-db' (or any publish) to "
                "generate inventory.json."
            ),
            "puzzles_total": 0,
            "collections_total": 0,
            "daily_schedule_total": 0,
            "by_level_id": {},
            "by_content_type": {},
            "by_collection_category": {},
            "schema_version": None,
            "db_version": None,
        }
        if not snapshot.exists():
            return empty
        try:
            data = json.loads(snapshot.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Truncated mid-write or hand-edited garbage: degrade to empty
            # rather than 500 the endpoint. Next snapshot write will heal.
            return empty
        return {
            "db_path": self._rel_posix(db),
            "db_exists": db.exists(),
            "snapshot_exists": True,
            "snapshot_path": self._rel_posix(snapshot),
            "advice": None,
            "puzzles_total": int(data.get("puzzles_total", 0)),
            "collections_total": int(data.get("collections_total", 0)),
            "daily_schedule_total": int(data.get("daily_schedule_total", 0)),
            "by_level_id": dict(data.get("by_level_id") or {}),
            "by_content_type": dict(data.get("by_content_type") or {}),
            "by_collection_category": dict(data.get("by_collection_category") or {}),
            "schema_version": data.get("schema_version"),
            "db_version": data.get("db_version"),
        }

    def read_runs(self, *, limit: int | None = 50) -> dict:
        """Return summarised run state files, newest first.

        Filenames sort lexicographically by start time (the
        ``YYYYMMDD-HHMMSS`` prefix), so the directory listing is the natural
        chronological order. Heavy fields (``batches``, ``file_results``,
        ``config_snapshot``) are stripped — the list view never needs them.
        """
        runs_dir = self._runs_dir()
        if not runs_dir.exists():
            return {"runs": [], "total": 0}
        files = sorted(runs_dir.glob("*.json"), reverse=True)
        total = len(files)
        if limit is not None and limit >= 0:
            files = files[:limit]
        summaries: list[dict] = []
        for f in files:
            try:
                state = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # A truncated file mid-write or a stale partial. Skip it from
                # the list rather than 500-ing the whole endpoint; the next
                # poll will pick it up once the writer finishes.
                continue
            stages = []
            for s in state.get("stages") or []:
                stages.append(
                    {
                        "name": s.get("name", ""),
                        "status": s.get("status", ""),
                        "started_at": s.get("started_at"),
                        "completed_at": s.get("completed_at"),
                        "processed_count": int(s.get("processed_count") or 0),
                        "failed_count": int(s.get("failed_count") or 0),
                        "skipped_count": int(s.get("skipped_count") or 0),
                    }
                )
            summaries.append(
                {
                    "run_id": state.get("run_id", ""),
                    "status": state.get("status", ""),
                    "started_at": state.get("started_at"),
                    "completed_at": state.get("completed_at"),
                    "stages": stages,
                    "failure_count": len(state.get("failures") or []),
                    "state_file": self._rel_posix(f),
                }
            )
        return {"runs": summaries, "total": total}
