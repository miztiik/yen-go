"""FastAPI bridge server for the Enrichment Lab GUI.

Exposes enrichment-lab Python services to the web-katrain frontend via HTTP.
Endpoints:
  POST /api/analyze  - Interactive KataGo analysis on a board position
  POST /api/enrich   - Run full pipeline with SSE progress events
  POST /api/cancel   - Cancel a running enrichment
  GET  /api/health   - Engine status
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure enrichment-lab root is importable
_lab_root = Path(__file__).resolve().parent
if str(_lab_root) not in sys.path:
    sys.path.insert(0, str(_lab_root))

from analyzers.single_engine import SingleEngineManager
from bridge_config_utils import apply_config_overrides
from config import load_enrichment_config
from models.analysis_request import AnalysisRequest
from models.position import Color, Position, Stone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Log handler that forwards records to an asyncio.Queue as SSE "log" events
# ---------------------------------------------------------------------------

class _QueueLogHandler(logging.Handler):
    """Captures Python log records and enqueues them as SSE 'log' events.

    Installed per-enrichment so the GUI log panel mirrors the console output.
    Only forwards records from puzzle-enrichment-lab modules (analyzers, engine,
    models, etc.) to avoid noisy framework logs.
    """

    _LAB_PREFIXES = ("analyzers.", "engine.", "models.", "bridge", "config", "log_config")

    def __init__(self, queue: asyncio.Queue[tuple[str, dict]]) -> None:
        super().__init__(level=logging.INFO)
        self._queue = queue
        self._loop: asyncio.AbstractEventLoop | None = None

    def emit(self, record: logging.LogRecord) -> None:
        # Filter to lab-relevant modules only
        if not record.name.startswith(self._LAB_PREFIXES) and record.name != "__main__":
            return
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            payload = {"level": record.levelname, "msg": msg}
            # Queue.put_nowait is thread-safe for asyncio queues when called
            # from the same event loop thread (which logging handlers are).
            self._queue.put_nowait(("log", payload))
        except Exception:
            pass  # never let logging handler failures propagate


# ---------------------------------------------------------------------------
# Lifecycle: clean up engine + running tasks on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Eagerly start engine in background so health polls report status
    startup_task = asyncio.create_task(_eager_engine_start())
    yield
    # Shutdown: cancel engine startup if still in progress
    if not startup_task.done():
        startup_task.cancel()
        try:
            await startup_task
        except (asyncio.CancelledError, Exception):
            pass
    # Shutdown: cancel any running enrichment task
    global _enrichment_task, _engine_manager
    if _enrichment_task is not None and not _enrichment_task.done():
        _enrichment_task.cancel()
        try:
            await _enrichment_task
        except (asyncio.CancelledError, Exception):
            pass
        _enrichment_task = None
    # Shutdown: stop the engine process
    if _engine_manager is not None:
        try:
            await _engine_manager.shutdown()
        except Exception:
            pass
        _engine_manager = None
    logger.info("Bridge server shut down cleanly.")


app = FastAPI(title="Enrichment Lab Bridge", version="0.1.0", lifespan=_lifespan)

# ---------------------------------------------------------------------------
# Singleton engine manager
# ---------------------------------------------------------------------------

_engine_manager: SingleEngineManager | None = None
_engine_starting: bool = False
_engine_lock = asyncio.Lock()
_enrichment_task: asyncio.Task[Any] | None = None

# CLI overrides (set from __main__ subprocess entry point)
_cli_katago_path: str | None = None
_cli_katago_config: str = ""
_cli_model_path: str = ""
_cli_config_path: str | None = None


async def get_engine() -> SingleEngineManager:
    global _engine_manager, _engine_starting
    if _engine_manager is not None:
        return _engine_manager
    async with _engine_lock:
        if _engine_manager is not None:
            return _engine_manager  # started by another coroutine while waiting
        _engine_starting = True
        try:
            config = load_enrichment_config(
                Path(_cli_config_path) if _cli_config_path else None
            )
            kwargs: dict[str, Any] = {}
            if _cli_katago_path:
                kwargs["katago_path"] = _cli_katago_path
            if _cli_katago_config:
                kwargs["katago_config_path"] = _cli_katago_config
            if _cli_model_path:
                kwargs["model_path"] = _cli_model_path
            elif config.models is not None:
                kwargs["model_path"] = str((Path(__file__).resolve().parent / "models-data" / config.models.deep_enrich.filename).resolve())
            mgr = SingleEngineManager(config, **kwargs)
            await mgr.start()
            _engine_manager = mgr
        finally:
            _engine_starting = False
    return _engine_manager


async def _eager_engine_start() -> None:
    """Start the engine at server boot so health polls report progress."""
    try:
        await get_engine()
        logger.info("Engine ready (eager start)")
    except Exception as exc:
        logger.warning("Eager engine start failed: %s (will retry on first request)", exc)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class MoveItem(BaseModel):
    x: int
    y: int
    player: str  # "black" | "white"


class AnalyzeRequest(BaseModel):
    board: list[list[str | None]]  # 2D array: "black", "white", or null
    currentPlayer: str = "black"
    moveHistory: list[MoveItem] = Field(default_factory=list)
    komi: float = 6.5
    rules: str = "chinese"
    visits: int | None = None
    maxTimeMs: int | None = None
    topK: int | None = None
    analysisPvLen: int | None = None
    includeMovesOwnership: bool = False
    ownershipMode: str = "root"


class EnrichRequest(BaseModel):
    sgf: str
    config_overrides: dict | None = None


# ---------------------------------------------------------------------------
# Helpers: convert browser board state → KataGo AnalysisRequest
# ---------------------------------------------------------------------------

def _board_to_stones(board: list[list[str | None]]) -> list[Stone]:
    stones: list[Stone] = []
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if cell == "black":
                stones.append(Stone(color=Color.BLACK, x=x, y=y))
            elif cell == "white":
                stones.append(Stone(color=Color.WHITE, x=x, y=y))
    return stones


def _player_str_to_color(p: str) -> Color:
    return Color.BLACK if p.lower() == "black" else Color.WHITE


GTP_COLUMNS = "ABCDEFGHJKLMNOPQRST"


def _gtp_to_xy(gtp: str, board_size: int) -> tuple[int, int]:
    col = GTP_COLUMNS.index(gtp[0].upper())
    row = board_size - int(gtp[1:])
    return col, row


def _response_to_js(response: Any, board_size: int) -> dict:
    """Convert AnalysisResponse to the JS BridgeAnalyzeResponse shape."""
    moves = []
    top_score = 0.0
    for i, mi in enumerate(response.move_infos):
        x, y = _gtp_to_xy(mi.move, board_size) if mi.move.upper() != "PASS" else (-1, -1)
        winrate_lost = 0.0
        if i > 0:
            winrate_lost = response.move_infos[0].winrate - mi.winrate
        score_lost = 0.0
        if i == 0:
            top_score = mi.score_lead
        else:
            score_lost = abs(top_score - mi.score_lead)

        # Flatten 2D ownership to 1D for JS
        flat_own: list[float] | None = None
        if mi.ownership:
            flat_own = []
            for row in mi.ownership:
                flat_own.extend(row)

        moves.append({
            "x": x,
            "y": y,
            "winRate": mi.winrate,
            "winRateLost": winrate_lost,
            "scoreLead": mi.score_lead,
            "scoreSelfplay": mi.score_lead,
            "scoreStdev": 0.0,
            "visits": mi.visits,
            "pointsLost": score_lost,
            "relativePointsLost": score_lost,
            "order": i,
            "prior": mi.policy_prior,
            "pv": mi.pv,
            "ownership": flat_own,
        })

    # Build flat ownership and policy arrays
    ownership_flat = [0.0] * (board_size * board_size)
    ownership_stdev = [0.0] * (board_size * board_size)
    policy_flat = [-1.0] * (board_size * board_size + 1)

    return {
        "rootWinRate": response.root_winrate,
        "rootScoreLead": response.root_score,
        "rootScoreSelfplay": response.root_score,
        "rootScoreStdev": 0.0,
        "rootVisits": response.total_visits,
        "ownership": ownership_flat,
        "ownershipStdev": ownership_stdev,
        "policy": policy_flat,
        "moves": moves,
    }


# ---------------------------------------------------------------------------
# POST /api/analyze - Interactive analysis
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze_position(req: AnalyzeRequest):
    global _engine_manager
    try:
        engine = await get_engine()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Engine startup failed")
        raise HTTPException(status_code=503, detail=f"Engine startup failed: {exc}") from exc

    board_size = len(req.board)
    stones = _board_to_stones(req.board)
    player = _player_str_to_color(req.currentPlayer)

    position = Position(
        board_size=board_size,
        stones=stones,
        player_to_move=player,
        komi=req.komi,
    )

    visits = req.visits or 200
    analysis_req = AnalysisRequest(
        position=position,
        max_visits=visits,
        include_ownership=True,
        include_pv=True,
        include_policy=True,
        rules=req.rules,
    )

    try:
        response = await engine.analyze(analysis_req)
    except RuntimeError as exc:
        if "exited" in str(exc):
            # Engine crashed -- clear singleton so next request restarts it
            _engine_manager = None
            logger.warning("Engine died during analysis; cleared for restart: %s", exc)
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    logger.info(
        "Bridge analysis: %d candidates, root_winrate=%.3f, total_visits=%d",
        len(response.move_infos), response.root_winrate, response.total_visits,
    )

    return _response_to_js(response, board_size)


# ---------------------------------------------------------------------------
# POST /api/enrich - Pipeline with SSE progress
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL = 5  # seconds (ADR D13)


@app.post("/api/enrich")
async def enrich_puzzle(req: EnrichRequest):
    global _enrichment_task

    # Cancel any running enrichment (ADR D12)
    if _enrichment_task and not _enrichment_task.done():
        _enrichment_task.cancel()
        try:
            await _enrichment_task
        except (asyncio.CancelledError, Exception):
            pass

    engine = await get_engine()

    # Validate config overrides *before* starting the SSE stream so that
    # Pydantic ValidationError can surface as a 422 HTTP response (C-4).
    config = load_enrichment_config(
        Path(_cli_config_path) if _cli_config_path else None
    )
    if req.config_overrides:
        from pydantic import ValidationError
        try:
            config = apply_config_overrides(config, req.config_overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    async def event_generator():
        from analyzers.enrich_single import enrich_single_puzzle

        stage_queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

        async def on_progress(stage: str, payload: dict) -> None:
            await stage_queue.put((stage, payload))
            # Yield to the event loop so the response generator can
            # read the event and flush it to the client immediately,
            # rather than batching all events until the pipeline ends.
            await asyncio.sleep(0)

        # Bridge Python log records into the SSE stream so the GUI
        # log panel shows the same detail as the console.
        log_handler = _QueueLogHandler(stage_queue)
        logging.getLogger().addHandler(log_handler)

        async def run_pipeline():
            try:
                result = await enrich_single_puzzle(
                    req.sgf, engine, progress_cb=on_progress, config=config,
                )
                await stage_queue.put(("complete", result.model_dump()))
            except asyncio.CancelledError:
                await stage_queue.put(("cancelled", {}))
            except Exception as e:
                await stage_queue.put(("error", {"message": str(e)}))
            finally:
                logging.getLogger().removeHandler(log_handler)
                await stage_queue.put(("__done__", {}))

        global _enrichment_task
        _enrichment_task = asyncio.create_task(run_pipeline())

        time.monotonic()
        while True:
            try:
                stage, payload = await asyncio.wait_for(
                    stage_queue.get(), timeout=HEARTBEAT_INTERVAL,
                )
                if stage == "__done__":
                    break
                yield f"event: {stage}\ndata: {json.dumps(payload, default=str)}\n\n"
                time.monotonic()
            except TimeoutError:
                yield "event: heartbeat\ndata: {}\n\n"
                time.monotonic()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /api/cancel - Cancel enrichment
# ---------------------------------------------------------------------------

@app.post("/api/cancel")
async def cancel_enrichment():
    global _enrichment_task
    if _enrichment_task and not _enrichment_task.done():
        _enrichment_task.cancel()
        return {"status": "cancelled"}
    return {"status": "no_task"}


# ---------------------------------------------------------------------------
# GET /api/health - Engine status
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    if _engine_manager is None:
        status = "starting" if _engine_starting else "not_started"
        return {"status": status, "backend": None, "modelName": None}
    return {
        "status": "ready",
        "backend": "python-bridge",
        "modelName": _engine_manager.model_label(),
    }


# ---------------------------------------------------------------------------
# GET /api/config - Current enrichment config
# ---------------------------------------------------------------------------

@app.get("/api/config")
async def get_config():
    config = load_enrichment_config(
        Path(_cli_config_path) if _cli_config_path else None
    )
    return config.model_dump()


# ---------------------------------------------------------------------------
# Static file serving for GUI (OPT-1R: single origin, zero CORS)
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles

_gui_dir = _lab_root / "gui"
if _gui_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_gui_dir), html=True), name="gui")


# ---------------------------------------------------------------------------
# Standalone entry point (subprocess mode per ADR D2)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    import uvicorn

    _cli = argparse.ArgumentParser(description="Enrichment Lab Bridge Server")
    _cli.add_argument("--katago", default=None, help="Path to KataGo binary")
    _cli.add_argument("--katago-config", default="", help="Path to KataGo analysis config")
    _cli.add_argument("--model", default="", help="Path to KataGo model .bin.gz file")
    _cli.add_argument("--config", default=None, help="Path to custom config JSON")
    _cli.add_argument("--host", default="127.0.0.1", help="Host to bind")
    _cli.add_argument("--port", type=int, default=8999, help="Port to bind")
    _cli.add_argument("--verbose", action="store_true", help="Enable DEBUG-level logging")
    _cli.add_argument("--log-dir", default=None, help="Override log file directory")
    _cli_args = _cli.parse_args()

    # Store CLI overrides so get_engine() can use them
    _cli_katago_path: str | None = _cli_args.katago
    _cli_katago_config: str = _cli_args.katago_config or ""
    _cli_model_path: str = _cli_args.model or ""
    _cli_config_path: str | None = _cli_args.config

    # Centralised bootstrap: generate run_id, configure logging, set context.
    from log_config import bootstrap

    _bridge_run_id = bootstrap(
        verbose=_cli_args.verbose,
        log_dir=_cli_args.log_dir,
        console_format="human",
    )
    logger.info("Bridge server run_id=%s", _bridge_run_id)

    uvicorn.run(app, host=_cli_args.host, port=_cli_args.port, log_level="info")
