"""FastAPI app factory for yengo_dashboard.

Keep this file thin: dependency wiring only. Endpoint implementations live in
``routes_*.py`` modules.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tools.yengo_dashboard import __version__
from tools.yengo_dashboard.server.pipeline_runner import PipelineRunner
from tools.yengo_dashboard.server.routes_admin import build_admin_router
from tools.yengo_dashboard.server.routes_docs import build_docs_router
from tools.yengo_dashboard.server.routes_lock import build_lock_router
from tools.yengo_dashboard.server.routes_logs import build_logs_router
from tools.yengo_dashboard.server.routes_maintenance import build_maintenance_router
from tools.yengo_dashboard.server.routes_read import build_read_router
from tools.yengo_dashboard.server.routes_run import build_run_router
from tools.yengo_dashboard.server.run_controller import RunController
from tools.yengo_dashboard.server.state_reader import StateReader


def _default_repo_root() -> Path:
    """Repo root is three directories above this file (tools/yengo_dashboard/server/app.py)."""
    return Path(__file__).resolve().parents[3]


def _web_dir() -> Path:
    """Static UI assets directory (tools/yengo_dashboard/web/)."""
    return Path(__file__).resolve().parents[1] / "web"


def create_app(
    *,
    repo_root: Path | None = None,
    config_dir: Path | None = None,
    runtime_dir: Path | None = None,
    published_dir: Path | None = None,
    controller: RunController | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    Args:
        repo_root: Project root. Defaults to the repository this file lives in.
        config_dir: Optional puzzle_manager config directory. ``None`` means
            "let the CLI use its default".
        runtime_dir: Override of ``.pm-runtime`` (mirrors ``YENGO_RUNTIME_DIR``).
            Useful in tests; defaults to ``repo_root / ".pm-runtime"``.
        published_dir: Override of the published collection root. Defaults to
            ``repo_root / "yengo-puzzle-collections"``.
        controller: Inject a custom ``RunController`` (e.g. tests that point
            at a tmp fake-pipeline directory). Default: a controller rooted
            at ``repo_root`` that runs the real ``backend.puzzle_manager``.
    """
    started_at = time.monotonic()
    root = (repo_root or _default_repo_root()).resolve()
    runner = PipelineRunner(repo_root=root, config_dir=config_dir)
    state_reader = StateReader(
        repo_root=root,
        runtime_dir=runtime_dir,
        published_dir=published_dir,
    )
    run_controller = controller or RunController(repo_root=root)

    app = FastAPI(
        title="yengo_dashboard",
        version=__version__,
        description=(
            "Localhost browser UI over backend.puzzle_manager. "
            "Presentation layer only — all domain logic lives in the pipeline."
        ),
    )
    app.include_router(
        build_read_router(
            started_at=started_at,
            runner=runner,
            state_reader=state_reader,
        )
    )
    app.include_router(build_run_router(controller=run_controller, runner=runner))
    app.include_router(build_maintenance_router(controller=run_controller, runner=runner))
    app.include_router(build_lock_router(runner=runner))
    app.include_router(build_admin_router(runner=runner))
    app.include_router(build_logs_router(state_reader=state_reader))
    app.include_router(build_docs_router(repo_root=root))
    # Read-only mount of config/ so the JS can fetch puzzle-levels.json /
    # content-types.json directly (no Pydantic round-trip for static config).
    cfg_dir = root / "config"
    if cfg_dir.is_dir():
        app.mount("/config-static", StaticFiles(directory=str(cfg_dir)), name="config-static")
    # Static UI mounted last so /api/* routes take precedence. html=True makes
    # the directory serve index.html for "/", which is what we want.
    web = _web_dir()
    if web.is_dir():
        # Slice 4: clean URL paths for the SPA. The static mount only serves
        # index.html for "/"; deep links like /pipeline would 404. These
        # explicit routes hand back the same index.html so the JS router can
        # parse location.pathname on boot.
        index_path = web / "index.html"

        def _serve_index() -> FileResponse:
            return FileResponse(index_path)

        for nav in ("library", "pipeline", "operations", "logs", "guide"):
            app.add_api_route(f"/{nav}", _serve_index, methods=["GET"], include_in_schema=False)
        # Guide deep links: /guide/concepts/foo etc.
        app.add_api_route(
            "/guide/{rest:path}", _serve_index, methods=["GET"], include_in_schema=False,
        )
        app.mount("/", StaticFiles(directory=str(web), html=True), name="web")
    return app
