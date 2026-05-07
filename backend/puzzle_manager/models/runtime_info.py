"""Pydantic shape and aggregation for ``runtime-info`` (Theme 3a).

Theme 3a wire contract: the dashboard's System dialog and Operations / Clean
card render this digest, so any breaking change here must be coordinated with
``tools/yengo_dashboard/``.

The aggregation is pure: directory paths in, sizes out. It walks the file
system once and never imports adapters or pipeline modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RuntimeInfo(BaseModel):
    """Per-bucket on-disk byte totals for a `.pm-runtime/`-rooted layout.

    Buckets line up with the targets accepted by ``puzzle_manager clean``
    so the dashboard can display "this many bytes will be freed" estimates
    next to each Clean target option.
    """

    logs_bytes: int = Field(..., ge=0, description="Total bytes under .pm-runtime/logs/.")
    state_bytes: int = Field(..., ge=0, description="Total bytes under .pm-runtime/state/.")
    staging_bytes: int = Field(..., ge=0, description="Total bytes under .pm-runtime/staging/.")
    raw_bytes: int = Field(..., ge=0, description="Total bytes under .pm-runtime/raw/.")
    ingest_dbs_bytes: int = Field(
        ...,
        ge=0,
        description=(
            "Total bytes across every source's `.yengo-ingest.sqlite` file "
            "(plus its sqlite -wal/-shm sidecars)."
        ),
    )
    by_source: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-source ingest-DB byte total, keyed by source id. Sums to "
            "ingest_dbs_bytes."
        ),
    )
    publish_logs_bytes: int = Field(
        ...,
        ge=0,
        description="Total bytes in the publish-log dir (yengo-puzzle-collections/.../publish-log/).",
    )
    captured_at: str = Field(..., description="UTC ISO-8601 timestamp of the snapshot.")


def _dir_size_bytes(path: Path) -> int:
    """Sum every regular file under ``path`` (recursive). Missing dir → 0."""
    if not path.exists() or not path.is_dir():
        return 0
    total = 0
    for entry in path.rglob("*"):
        # Skip symlinks deliberately; they would either double-count or
        # follow into unrelated trees.
        try:
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
        except OSError:
            # Race with concurrent cleanup; skip silently.
            continue
    return total


_INGEST_DB_NAME = ".yengo-ingest.sqlite"
_INGEST_SIDECARS = (".yengo-ingest.sqlite-wal", ".yengo-ingest.sqlite-shm")


def _ingest_db_bytes(source_root: Path) -> int:
    """Sum the ingest DB plus its sqlite -wal/-shm sidecars at ``source_root``."""
    if not source_root.exists():
        return 0
    total = 0
    for name in (_INGEST_DB_NAME, *_INGEST_SIDECARS):
        f = source_root / name
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                continue
    return total


def compute_runtime_info(
    *,
    runtime_dir: Path,
    sources: list[tuple[str, Path | None]],
    publish_log_dir: Path,
) -> RuntimeInfo:
    """Walk the runtime tree once and return a :class:`RuntimeInfo` snapshot.

    Args:
        runtime_dir: ``.pm-runtime/`` (or whatever ``YENGO_RUNTIME_DIR`` points at).
        sources: ``[(source_id, source_root_or_None), ...]`` from sources.json.
            ``None`` roots are skipped (e.g. HTTP-only adapters with no local data).
        publish_log_dir: Path to ``yengo-puzzle-collections/.puzzle-inventory-state/publish-log/``.

    Returns:
        Populated :class:`RuntimeInfo`.
    """
    by_source: dict[str, int] = {}
    for source_id, root in sources:
        if root is None:
            continue
        size = _ingest_db_bytes(root)
        if size > 0:
            by_source[source_id] = size

    return RuntimeInfo(
        logs_bytes=_dir_size_bytes(runtime_dir / "logs"),
        state_bytes=_dir_size_bytes(runtime_dir / "state"),
        staging_bytes=_dir_size_bytes(runtime_dir / "staging"),
        raw_bytes=_dir_size_bytes(runtime_dir / "raw"),
        ingest_dbs_bytes=sum(by_source.values()),
        by_source=by_source,
        publish_logs_bytes=_dir_size_bytes(publish_log_dir),
        captured_at=datetime.now(UTC).isoformat(),
    )
