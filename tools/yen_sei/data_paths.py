"""Timestamped artefact paths + auto-cleanup for yen-sei data dir.

Naming convention:
    {kind}_YYYYMMDDTHHMM.{ext}            timestamped artefact
    {kind}_latest.{ext}                   pointer copy (always = newest)

Per-stage artefacts (e.g., qualification, qualify_log) are kept to the
N most recent runs; older ones are deleted.

All paths produced by helpers in this module are POSIX-relative when
serialised. Use `to_posix_rel(p)` whenever a path is written into a
JSON/JSONL artefact.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from tools.yen_sei.config import DATA_DIR, PROJECT_ROOT

# Default keep-N for auto-cleanup
DEFAULT_KEEP = 3

# Timestamp format used in filenames: 12 chars, sortable, no separators in the time portion
TIMESTAMP_FMT = "%Y%m%dT%H%M"
# Match {kind}_{12-char-timestamp}.{ext}
_TIMESTAMP_PAT = re.compile(r"^(?P<kind>.+)_(?P<ts>\d{8}T\d{4})\.(?P<ext>[A-Za-z0-9]+)$")


def now_stamp() -> str:
    """UTC timestamp string used in artefact filenames."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)


def to_posix_rel(p: Path | str, root: Path = PROJECT_ROOT) -> str:
    """Return forward-slash, repo-relative path string. Falls back to absolute
    POSIX if the path is outside `root`."""
    pth = Path(p).resolve()
    try:
        return pth.relative_to(root.resolve()).as_posix()
    except ValueError:
        return pth.as_posix()


def from_posix_rel(rel: str, root: Path = PROJECT_ROOT) -> Path:
    """Resolve a stored POSIX-relative path back to an absolute Path."""
    p = Path(rel)
    if p.is_absolute():
        return p
    return (root / p).resolve()


def stamped_path(kind: str, ext: str, dirpath: Path = DATA_DIR, ts: str | None = None) -> Path:
    """Build path for a timestamped artefact: {dirpath}/{kind}_{ts}.{ext}."""
    return dirpath / f"{kind}_{ts or now_stamp()}.{ext}"


def latest_pointer(kind: str, ext: str, dirpath: Path = DATA_DIR) -> Path:
    """Path to the canonical 'latest' pointer for an artefact kind."""
    return dirpath / f"{kind}_latest.{ext}"


def list_runs(kind: str, ext: str, dirpath: Path = DATA_DIR) -> list[Path]:
    """Return all timestamped runs of `kind` sorted oldest -> newest."""
    if not dirpath.exists():
        return []
    out: list[tuple[str, Path]] = []
    for f in dirpath.iterdir():
        m = _TIMESTAMP_PAT.match(f.name)
        if m and m.group("kind") == kind and m.group("ext") == ext:
            out.append((m.group("ts"), f))
    out.sort(key=lambda x: x[0])
    return [p for _, p in out]


def resolve_latest(kind: str, ext: str, dirpath: Path = DATA_DIR) -> Path | None:
    """Return path to newest timestamped run, or None."""
    runs = list_runs(kind, ext, dirpath)
    return runs[-1] if runs else None


def cleanup_old(kind: str, ext: str, keep: int = DEFAULT_KEEP, dirpath: Path = DATA_DIR) -> list[Path]:
    """Delete all but the `keep` most recent timestamped runs of `kind`.
    Returns paths that were deleted."""
    runs = list_runs(kind, ext, dirpath)
    if len(runs) <= keep:
        return []
    victims = runs[: len(runs) - keep]
    for v in victims:
        try:
            v.unlink()
        except OSError:
            pass
    return victims


def write_with_pointer(
    kind: str,
    ext: str,
    content: str | bytes,
    dirpath: Path = DATA_DIR,
    keep: int = DEFAULT_KEEP,
    ts: str | None = None,
) -> tuple[Path, Path, list[Path]]:
    """Write `content` to a stamped path, refresh the *_latest pointer, prune old.

    Returns (stamped_path, latest_pointer_path, deleted_paths).
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    stamp = ts or now_stamp()
    target = stamped_path(kind, ext, dirpath, stamp)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")
    pointer = latest_pointer(kind, ext, dirpath)
    if pointer.exists() or pointer.is_symlink():
        try:
            pointer.unlink()
        except OSError:
            pass
    # Use a copy (not symlink) for Windows portability + simpler reads.
    pointer.write_bytes(target.read_bytes())
    deleted = cleanup_old(kind, ext, keep=keep, dirpath=dirpath)
    return target, pointer, deleted
