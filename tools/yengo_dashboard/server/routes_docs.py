"""Read-only docs viewer endpoints for the Guide tab.

Serves a tree view of the project's ``docs/`` directory and the raw markdown
content of individual files. All paths are validated to stay within the docs
root — no traversal, no reads outside ``docs/``.

Per principle #6, the dashboard never interprets the markdown; it just
forwards bytes. Rendering happens client-side via marked.js.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse


def _build_tree(root: Path, rel: Path = Path()) -> dict | None:
    """Recursively build a {type, name, path, children?} tree of .md files.

    Returns None for empty directories so we can prune them.
    """
    full = root / rel
    if not full.exists():
        return None
    if full.is_file():
        if full.suffix.lower() == ".md":
            return {
                "type": "file",
                "name": full.name,
                "path": rel.as_posix(),
            }
        return None
    # directory
    children = []
    for child in sorted(full.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        # Skip hidden files / archives
        if child.name.startswith(".") or child.name in {"archive", "__pycache__"}:
            continue
        sub = _build_tree(root, rel / child.name)
        if sub is not None:
            children.append(sub)
    if not children:
        return None
    return {
        "type": "dir",
        "name": full.name if rel != Path() else "docs",
        "path": rel.as_posix(),
        "children": children,
    }


def build_docs_router(*, repo_root: Path) -> APIRouter:
    """Construct the /api/docs/* router.

    Args:
        repo_root: Repository root. ``docs/`` is resolved beneath this.
    """
    router = APIRouter(prefix="/api/docs", tags=["docs"])
    docs_root = (repo_root / "docs").resolve()

    @router.get("/tree")
    def tree(_request: Request) -> dict:
        if not docs_root.is_dir():
            return {"type": "dir", "name": "docs", "path": "", "children": []}
        return _build_tree(docs_root) or {
            "type": "dir",
            "name": "docs",
            "path": "",
            "children": [],
        }

    @router.get("/file", response_class=PlainTextResponse)
    def file(_request: Request, path: str = Query(..., min_length=1, max_length=512)) -> str:
        # Resolve and verify the requested path is under docs_root.
        # Reject absolute paths, ``..``, and any escape attempt.
        if path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            raise HTTPException(status_code=400, detail="invalid path")
        candidate = (docs_root / path).resolve()
        try:
            candidate.relative_to(docs_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="path outside docs/") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail=f"not found: {path}")
        if candidate.suffix.lower() != ".md":
            raise HTTPException(status_code=400, detail="only .md files are served")
        try:
            return candidate.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"read failed: {exc}") from exc

    return router
