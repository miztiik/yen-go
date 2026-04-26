"""Structured file logging for oshie eval runs.

All oshie logs go to tools/oshie/logs/ with the naming convention:
    YYYYMMDD_<run_id>_<logname>.log

Each log file includes a metadata header with:
    - run_id, prompt_version, model, max_tokens, endpoint, timestamp

Usage:
    from tools.oshie.eval.log_setup import setup_run_logger, log_puzzle_io

    logger, log_path = setup_run_logger(run_id, prompt_version, metadata)
    logger.info("Run started")

    # Log per-puzzle I/O verbatim
    log_puzzle_io(log_path.parent, run_id, puzzle_id, user_prompt, reasoning, content, score)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def setup_run_logger(
    run_id: str,
    prompt_version: str,
    metadata: dict,
) -> tuple[logging.Logger, Path]:
    """Create a file logger for a specific eval run.

    Args:
        run_id: Run identifier (YYYYMMDD-HHMMSS format).
        prompt_version: Prompt version being evaluated (e.g. "v3.1").
        metadata: Dict with model, endpoint, max_tokens, n_puzzles, etc.

    Returns:
        (logger, log_path) tuple. Logger writes to both file and console.
    """
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_prefix = run_id.split("-")[0] if "-" in run_id else datetime.now().strftime("%Y%m%d")
    log_path = _LOGS_DIR / f"{date_prefix}_{run_id}_eval.log"

    logger = logging.getLogger(f"oshie.eval.{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler -- everything
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.addHandler(fh)

    # Write metadata header
    header = {
        "run_id": run_id,
        "prompt_version": prompt_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    fh.stream.write(f"# OSHIE EVAL RUN METADATA\n")
    fh.stream.write(f"# {json.dumps(header, ensure_ascii=False)}\n")
    fh.stream.write(f"#\n")
    fh.stream.flush()

    return logger, log_path


def log_puzzle_io(
    run_id: str,
    puzzle_index: int,
    puzzle_id: str,
    prompt_version: str,
    user_prompt: str,
    system_prompt: str,
    reasoning: str,
    content: str,
    score: float,
    think_tokens: int,
    content_tokens: int,
    elapsed_s: float,
    finish_reason: str,
    dimension_scores: dict[str, float] | None = None,
) -> Path:
    """Write a per-puzzle verbatim I/O log file.

    Creates: YYYYMMDD_<run_id>_puzzle_<NN>_<puzzle_id>.log

    This is the primary debugging artifact -- contains the exact prompts
    sent and exact output received, with no truncation.
    """
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_prefix = run_id.split("-")[0] if "-" in run_id else datetime.now().strftime("%Y%m%d")
    safe_id = puzzle_id.replace("/", "_").replace("\\", "_")
    log_path = _LOGS_DIR / f"{date_prefix}_{run_id}_puzzle_{puzzle_index:02d}_{safe_id}.log"

    dim_str = ""
    if dimension_scores:
        dim_str = "\n".join(f"  {k}: {v:.3f}" for k, v in dimension_scores.items())

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# OSHIE PUZZLE I/O LOG\n")
        f.write(f"# run_id: {run_id}\n")
        f.write(f"# prompt_version: {prompt_version}\n")
        f.write(f"# puzzle: [{puzzle_index}] {puzzle_id}\n")
        f.write(f"# score: {score:.4f}\n")
        f.write(f"# think_tokens: {think_tokens}\n")
        f.write(f"# content_tokens: {content_tokens}\n")
        f.write(f"# elapsed_s: {elapsed_s:.1f}\n")
        f.write(f"# finish_reason: {finish_reason}\n")
        f.write(f"# timestamp: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"#\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"SYSTEM PROMPT\n")
        f.write(f"{'='*80}\n")
        f.write(system_prompt)
        f.write(f"\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"USER PROMPT\n")
        f.write(f"{'='*80}\n")
        f.write(user_prompt)
        f.write(f"\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"REASONING ({think_tokens} tokens)\n")
        f.write(f"{'='*80}\n")
        f.write(reasoning if reasoning else "(empty)")
        f.write(f"\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"CONTENT ({content_tokens} tokens)\n")
        f.write(f"{'='*80}\n")
        f.write(content if content else "(empty)")
        f.write(f"\n\n")

        if dim_str:
            f.write(f"{'='*80}\n")
            f.write(f"DIMENSION SCORES (weighted_total: {score:.4f})\n")
            f.write(f"{'='*80}\n")
            f.write(dim_str)
            f.write(f"\n")

    return log_path
