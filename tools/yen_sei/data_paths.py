"""Timestamped artefact paths + auto-cleanup for yen-sei data dir.

Naming convention:
    YYYYMMDDHHMMSS_{kind}.{ext}                  timestamped artefact
    YYYYMMDDHHMMSS_{kind}_latest.{ext}           latest pointer copy (always = newest)

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

# Timestamp format used in filenames: numeric-only, lexicographically sortable.
TIMESTAMP_FMT = "%Y%m%d%H%M%S"
_STAMP_RE = re.compile(r"^\d{14}$")
_STAMP_12_RE = re.compile(r"^\d{12}$")
_LEGACY_STAMP_RE = re.compile(r"^\d{8}T\d{4}$")


def now_stamp() -> str:
    """UTC timestamp string used in artefact filenames."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)


def _normalize_stamp(stamp: str) -> str:
    """Normalize accepted stamp formats to 14-digit numeric form.

    Accepted forms:
      - YYYYMMDDHHMMSS (preferred)
      - YYYYMMDDHHMM   (seconds assumed 00)
      - YYYYMMDDTHHMM  (legacy; seconds assumed 00)
    """
    if _STAMP_RE.fullmatch(stamp):
        return stamp
    if _STAMP_12_RE.fullmatch(stamp):
        return f"{stamp}00"
    if _LEGACY_STAMP_RE.fullmatch(stamp):
        return f"{stamp.replace('T', '')}00"
    raise ValueError(f"Invalid timestamp format: {stamp}")


def _extract_prefixed_stamp(name: str) -> tuple[str, str] | None:
    """Return (stamp14, rest) for names shaped like '<stamp14>_<rest>'"""
    if "_" not in name:
        return None
    stamp, rest = name.split("_", 1)
    if not _STAMP_RE.fullmatch(stamp):
        return None
    return stamp, rest


def _extract_legacy_suffix_stamp(name: str, kind: str, ext: str) -> str | None:
    """Extract stamp from legacy '<kind>_<stamp>.<ext>' filenames."""
    prefix = f"{kind}_"
    suffix = f".{ext}"
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    stamp = name[len(prefix):-len(suffix)]
    if not _LEGACY_STAMP_RE.fullmatch(stamp):
        return None
    return _normalize_stamp(stamp)


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
    """Build path for a timestamped artefact: {dirpath}/{ts}_{kind}.{ext}."""
    stamp = _normalize_stamp(ts) if ts else now_stamp()
    return dirpath / f"{stamp}_{kind}.{ext}"


def legacy_latest_pointer(kind: str, ext: str, dirpath: Path = DATA_DIR) -> Path:
    """Legacy pointer path retained for backward-read compatibility."""
    return dirpath / f"{kind}_latest.{ext}"


def latest_pointer(
    kind: str,
    ext: str,
    dirpath: Path = DATA_DIR,
    ts: str | None = None,
) -> Path:
    """Path to the timestamp-prefixed latest pointer for an artefact kind.

    If `ts` is omitted, returns the newest existing latest-pointer path if found,
    otherwise falls back to the legacy static pointer path.
    """
    if ts is None:
        existing = resolve_latest_pointer(kind, ext, dirpath)
        return existing if existing is not None else legacy_latest_pointer(kind, ext, dirpath)
    stamp = _normalize_stamp(ts)
    return dirpath / f"{stamp}_{kind}_latest.{ext}"


def list_runs(kind: str, ext: str, dirpath: Path = DATA_DIR) -> list[Path]:
    """Return all timestamped runs of `kind` sorted oldest -> newest.

    Supports both current prefix format and legacy suffix format.
    """
    if not dirpath.exists():
        return []
    out: list[tuple[str, Path]] = []
    for f in dirpath.iterdir():
        prefixed = _extract_prefixed_stamp(f.name)
        if prefixed is not None:
            stamp, rest = prefixed
            if rest == f"{kind}.{ext}":
                out.append((stamp, f))
                continue

        legacy_stamp = _extract_legacy_suffix_stamp(f.name, kind, ext)
        if legacy_stamp is not None:
            out.append((legacy_stamp, f))

    out.sort(key=lambda x: (x[0], x[1].name))
    return [p for _, p in out]


def list_latest_pointers(kind: str, ext: str, dirpath: Path = DATA_DIR) -> list[Path]:
    """Return all timestamp-prefixed latest-pointer files sorted oldest -> newest."""
    return list_runs(f"{kind}_latest", ext, dirpath)


def resolve_latest(kind: str, ext: str, dirpath: Path = DATA_DIR) -> Path | None:
    """Return path to newest timestamped run, or None."""
    runs = list_runs(kind, ext, dirpath)
    return runs[-1] if runs else None


def resolve_latest_pointer(kind: str, ext: str, dirpath: Path = DATA_DIR) -> Path | None:
    """Return newest latest-pointer path (timestamp-prefixed), with legacy fallback."""
    pointers = list_latest_pointers(kind, ext, dirpath)
    if pointers:
        return pointers[-1]
    legacy = legacy_latest_pointer(kind, ext, dirpath)
    return legacy if legacy.exists() else None


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


def cleanup_old_latest_pointers(
    kind: str,
    ext: str,
    keep: int = DEFAULT_KEEP,
    dirpath: Path = DATA_DIR,
) -> list[Path]:
    """Delete all but the `keep` most recent timestamped latest pointers."""
    return cleanup_old(f"{kind}_latest", ext, keep=keep, dirpath=dirpath)


def write_with_pointer(
    kind: str,
    ext: str,
    content: str | bytes,
    dirpath: Path = DATA_DIR,
    keep: int = DEFAULT_KEEP,
    ts: str | None = None,
) -> tuple[Path, Path, list[Path]]:
    """Write `content` to a stamped path, refresh latest pointer, prune old.

    Returns (stamped_path, latest_pointer_path, deleted_paths).
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    stamp = ts or now_stamp()
    target = stamped_path(kind, ext, dirpath, stamp)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")
    pointer = latest_pointer(kind, ext, dirpath, ts=stamp)
    # Use a copy (not symlink) for Windows portability + simpler reads.
    pointer.write_bytes(target.read_bytes())
    deleted = cleanup_old(kind, ext, keep=keep, dirpath=dirpath)
    deleted += cleanup_old_latest_pointers(kind, ext, keep=keep, dirpath=dirpath)
    legacy_ptr = legacy_latest_pointer(kind, ext, dirpath)
    if legacy_ptr.exists() or legacy_ptr.is_symlink():
        try:
            legacy_ptr.unlink()
        except OSError:
            pass
    return target, pointer, deleted
