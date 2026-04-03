"""FastAPI bridge server for the Enrichment Lab GUI.

Exposes enrichment-lab Python services to the web-katrain frontend via HTTP.
Endpoints:
  POST /api/analyze  — Interactive KataGo analysis on a board position
  POST /api/enrich   — Run full pipeline with SSE progress events
  POST /api/cancel   — Cancel a running enrichment
  GET  /api/health   — Engine status
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
_lab_root = Path(__file__).resolve().parent.parent
if str(_lab_root) not in sys.path:
    sys.path.insert(0, str(_lab_root))

from analyzers.single_engine import SingleEngineManager
from config import load_enrichment_config
from models.analysis_request import AnalysisRequest
from models.position import Color, Position, Stone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifecycle: clean up engine + running tasks on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
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
            await _engine_manager.stop()
        except Exception:
            pass
        _engine_manager = None
    logger.info("Bridge server shut down cleanly.")


app = FastAPI(title="Enrichment Lab Bridge", version="0.1.0", lifespan=_lifespan)

# ---------------------------------------------------------------------------
# Singleton engine manager
# ---------------------------------------------------------------------------

_engine_manager: SingleEngineManager | None = None
_enrichment_task: asyncio.Task[Any] | None = None

# CLI overrides (set from __main__ subprocess entry point)
_cli_katago_path: str | None = None
_cli_katago_config: str = ""
_cli_model_path: str = ""
_cli_config_path: str | None = None


async def get_engine() -> SingleEngineManager:
    global _engine_manager
    if _engine_manager is None:
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
        _engine_manager = SingleEngineManager(config, **kwargs)
        try:
            await _engine_manager.start()
        except Exception:
            _engine_manager = None  # don't cache a broken engine
            raise
    return _engine_manager


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
# POST /api/analyze — Interactive analysis
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
            # Engine crashed — clear singleton so next request restarts it
            _engine_manager = None
            logger.warning("Engine died during analysis; cleared for restart: %s", exc)
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return _response_to_js(response, board_size)


# ---------------------------------------------------------------------------
# POST /api/enrich — Pipeline with SSE progress
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

    async def event_generator():
        from analyzers.enrich_single import enrich_single_puzzle

        stage_queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

        async def on_progress(stage: str, payload: dict) -> None:
            await stage_queue.put((stage, payload))

        async def run_pipeline():
            try:
                result = await enrich_single_puzzle(
                    req.sgf, engine, progress_cb=on_progress,
                )
                await stage_queue.put(("complete", result.model_dump()))
            except asyncio.CancelledError:
                await stage_queue.put(("cancelled", {}))
            except Exception as e:
                await stage_queue.put(("error", {"message": str(e)}))
            finally:
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
# POST /api/cancel — Cancel enrichment
# ---------------------------------------------------------------------------

@app.post("/api/cancel")
async def cancel_enrichment():
    global _enrichment_task
    if _enrichment_task and not _enrichment_task.done():
        _enrichment_task.cancel()
        return {"status": "cancelled"}
    return {"status": "no_task"}


# ---------------------------------------------------------------------------
# GET /api/health — Engine status
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    if _engine_manager is None:
        return {"status": "not_started", "backend": None, "modelName": None}
    return {
        "status": "ready",
        "backend": "python-bridge",
        "modelName": _engine_manager.model_label(),
    }


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
    _cli_args = _cli.parse_args()

    # Store CLI overrides so get_engine() can use them
    _cli_katago_path: str | None = _cli_args.katago
    _cli_katago_config: str = _cli_args.katago_config or ""
    _cli_model_path: str = _cli_args.model or ""
    _cli_config_path: str | None = _cli_args.config

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=_cli_args.host, port=_cli_args.port, log_level="info")
