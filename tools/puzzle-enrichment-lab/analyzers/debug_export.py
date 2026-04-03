"""Debug artifact export — trap moves + detector activation matrix.

When ``--debug-export`` is enabled, writes per-puzzle debug JSON to
``.lab-runtime/debug/{run_id}/{puzzle_id}.debug.json``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ai_analysis_result import AiAnalysisResult

logger = logging.getLogger(__name__)

# All 28 detector tag slugs (alphabetical)
ALL_DETECTOR_SLUGS: list[str] = [
    "capture-race",
    "clamp",
    "connect-and-die",
    "connection",
    "corner",
    "cutting",
    "dead-shapes",
    "double-atari",
    "endgame",
    "escape",
    "eye-shape",
    "fuseki",
    "joseki",
    "ko",
    "ladder",
    "liberty-shortage",
    "life-and-death",
    "living",
    "nakade",
    "net",
    "sacrifice",
    "seki",
    "shape",
    "snapback",
    "tesuji",
    "throw-in",
    "under-the-stones",
    "vital-point",
]


def build_debug_artifact(result: AiAnalysisResult, run_id: str) -> dict:
    """Build the debug artifact dict from an enrichment result.

    Returns:
        Dict with keys: puzzle_id, run_id, trap_moves, detector_matrix.
    """
    # Top-5 trap moves from refutations
    trap_moves = []
    for ref in result.refutations[:5]:
        trap_moves.append({
            "wrong_move": ref.wrong_move,
            "delta": ref.delta,
            "refutation_pv": ref.refutation_pv,
            "refutation_type": ref.refutation_type,
        })

    # Detector activation matrix
    active_tags = set(result.technique_tags or [])
    detector_matrix = {slug: slug in active_tags for slug in ALL_DETECTOR_SLUGS}

    return {
        "puzzle_id": result.puzzle_id or "unknown",
        "run_id": run_id,
        "trap_moves": trap_moves,
        "detector_matrix": detector_matrix,
    }


def export_debug_artifact(
    result: AiAnalysisResult,
    run_id: str,
    base_dir: str = ".lab-runtime/debug",
) -> Path:
    """Write debug artifact JSON to disk.

    Args:
        result: Enrichment result.
        run_id: Current run ID.
        base_dir: Base directory for debug output.

    Returns:
        Path to the written debug file.
    """
    data = build_debug_artifact(result, run_id)
    puzzle_id = data["puzzle_id"]

    debug_dir = Path(base_dir) / run_id
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_file = debug_dir / f"{puzzle_id}.debug.json"
    debug_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    logger.info("Debug artifact written: %s", debug_file)
    return debug_file
