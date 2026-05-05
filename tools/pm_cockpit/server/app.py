"""FastAPI app factory for pm_cockpit.

Keep this file thin: dependency wiring only. Endpoint implementations live in
``routes_*.py`` modules.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tools.pm_cockpit import __version__
from tools.pm_cockpit.server.pipeline_runner import PipelineRunner
from tools.pm_cockpit.server.routes_admin import build_admin_router
from tools.pm_cockpit.server.routes_lock import build_lock_router
from tools.pm_cockpit.server.routes_maintenance import build_maintenance_router
from tools.pm_cockpit.server.routes_read import build_read_router
from tools.pm_cockpit.server.routes_run import build_run_router
from tools.pm_cockpit.server.run_controller import RunController
from tools.pm_cockpit.server.state_reader import StateReader


def _default_repo_root() -> Path:
    """Repo root is three directories above this file (tools/pm_cockpit/server/app.py)."""
    return Path(__file__).resolve().parents[3]


def _web_dir() -> Path:
    """Static UI assets directory (tools/pm_cockpit/web/)."""
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
        title="pm_cockpit",
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
    app.include_router(build_run_router(controller=run_controller))
    app.include_router(build_maintenance_router(controller=run_controller))
    app.include_router(build_lock_router(runner=runner))
    app.include_router(build_admin_router(runner=runner))
    # Read-only mount of config/ so the JS can fetch puzzle-levels.json /
    # content-types.json directly (no Pydantic round-trip for static config).
    cfg_dir = root / "config"
    if cfg_dir.is_dir():
        app.mount("/config-static", StaticFiles(directory=str(cfg_dir)), name="config-static")
    # Static UI mounted last so /api/* routes take precedence. html=True makes
    # the directory serve index.html for "/", which is what we want.
    web = _web_dir()
    if web.is_dir():
        app.mount("/", StaticFiles(directory=str(web), html=True), name="web")
    return app
