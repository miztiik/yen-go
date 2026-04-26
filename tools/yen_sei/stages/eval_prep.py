"""eval_prep stage: build named evaluation test sets.

Reads:
    - latest qualification jsonl (timestamp-prefixed run or latest pointer)
  - curation_config.json -> test_sets[]

Writes one file per test_set into data/refined/:
  - test_{id}.jsonl           ChatML rows with [system, user] only (no assistant).
  - test_{id}_metadata.jsonl  sidecar with one row per test puzzle:
        {test_set_id, puzzle_hash, source, file_path, board_size,
         player_to_move, level, tags, side_to_move, correct_first_move,
         wrong_first_moves, has_reference_prose}

Two test-set sources are supported:

  1. source: "marker_only"
     Selects rows from qualification jsonl where the puzzle has zero teaching
     prose (so nothing leaks via the prompt) but is still a valid puzzle —
     i.e. it has a structured solution tree with at least one correct first
     move and one wrong first move. These rows are NOT in data/sources/ (they
     were filtered out at ingest). We re-parse the SGF directly here.

  2. source: "training_pool"
     Held-out gold/silver puzzles (with teaching prose). Used as a sanity
     check vs the marker-only sets.
"""

from __future__ import annotations

import json
import random
from hashlib import sha256
from pathlib import Path

from tools.core.sgf_parser import parse_sgf
from tools.yen_sei.config import REFINED_DIR, SYSTEM_PROMPT
from tools.yen_sei.data_paths import (
    from_posix_rel,
    resolve_latest,
    resolve_latest_pointer,
    to_posix_rel,
)
from tools.yen_sei.governance.config_loader import load_config
from tools.yen_sei.stages.qualify import QUALIFICATION_JSONL
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)


def _is_marker_only_candidate(row: dict) -> bool:
    """Row qualifies for marker-only test pool: structurally valid puzzle but no
    English teaching prose. We accept rows with tier=='drop' whose ONLY drop
    reasons are language/prose related (no hard-gate failures).

    Required positive signals:
      - variation_count >= 2 (has correct + wrong branches)
      - correct_first_move present (we know the answer)
      - at least one wrong_first_move (otherwise nothing to discriminate)
      - no AI contamination (yq_ac == 0 AND ai_signature_hits == 0)
      - source not in dropped pool (handled via hard_gates already passing)
    """
    if not row.get("correct_first_move"):
        return False
    if not (row.get("wrong_first_moves") or []):
        return False
    if (row.get("variation_count") or 0) < 2:
        return False
    if (row.get("yq_ac") or 0) > 0:
        return False
    if (row.get("ai_signature_hits") or 0) >= 2:
        return False
    # Hard-gate failures other than english/prose mean structurally invalid.
    fails = set(row.get("gate_failures") or [])
    structural_fails = fails - {"is_english", "no_variations", "ai_signature_prose"}
    # `no_variations` is a teachable_content gate; if the variation tree is
    # actually present (variation_count >= 2) we treat it as a content-only
    # failure, not structural.
    if structural_fails:
        return False
    return True


def _matches_selectors(row: dict, sel: dict) -> bool:
    bsizes = sel.get("board_sizes")
    if bsizes and (row.get("board_size") not in bsizes):
        return False
    techs_any = sel.get("techniques_any")
    if techs_any:
        found = {t.lower() for t in (row.get("techniques_found") or [])}
        if not (found & {t.lower() for t in techs_any}):
            return False
    return True


def _puzzle_hash(file_path: str, correct_first_move: str, board_size: int) -> str:
    return sha256(f"{file_path}|{correct_first_move}|{board_size}".encode()).hexdigest()[:16]


def _build_user_prompt(board_size: int, side_to_move: str,
                       black_stones: list[str], white_stones: list[str]) -> str:
    """Same shape as refine.py's _build_user_prompt — board + side + setup only.

    Level and Tags are omitted (yen-go custom terms, noisy, not useful for model).
    """
    lines = [f"Board: {board_size}x{board_size}", f"{side_to_move} to play"]
    if black_stones:
        lines.append(f"Black stones: {', '.join(black_stones[:20])}")
    if white_stones:
        lines.append(f"White stones: {', '.join(white_stones[:20])}")
    return "\n".join(lines)


def _stones_from_tree(tree) -> tuple[list[str], list[str], str]:
    """Return (black_setup, white_setup, side_to_move) from a parsed SgfTree."""
    black = sorted(p.to_sgf() for p in tree.black_stones)
    white = sorted(p.to_sgf() for p in tree.white_stones)
    side = "Black"
    # Side-to-move heuristic: first move on the solution tree's first child.
    if tree.solution_tree and tree.solution_tree.children:
        first = tree.solution_tree.children[0]
        if first.color is not None:
            side = "Black" if str(first.color).lower().endswith("black") else "White"
    return black, white, side


def _row_to_test_example(row: dict, test_set_id: str, has_reference_prose: bool) -> tuple[dict, dict] | None:
    """Re-parse the SGF and produce (chat_row, sidecar_row). Returns None on failure."""
    file_path = row.get("file_path") or ""
    src_path = from_posix_rel(file_path)
    if not src_path.exists():
        return None
    try:
        raw = src_path.read_text(encoding="utf-8", errors="replace")
        tree = parse_sgf(raw)
    except Exception:
        return None

    black, white, side = _stones_from_tree(tree)
    # Tags and level still extracted for sidecar metadata (used by grounded scorer)
    tags: list[str] = list(getattr(tree.yengo_props, "tags", []) or [])
    level = getattr(tree.yengo_props, "level_slug", "") or ""

    user_prompt = _build_user_prompt(
        board_size=tree.board_size or row.get("board_size") or 19,
        side_to_move=side,
        black_stones=black,
        white_stones=white,
    )
    chat_row = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    }
    sidecar = {
        "test_set_id": test_set_id,
        "puzzle_hash": _puzzle_hash(file_path, row.get("correct_first_move", ""), tree.board_size or 19),
        "source": row.get("source", ""),
        "file_path": to_posix_rel(src_path),
        "board_size": tree.board_size,
        "side_to_move": side,
        "level": level,
        "tags": tags,
        "correct_first_move": row.get("correct_first_move", ""),
        "wrong_first_moves": row.get("wrong_first_moves", []),
        "has_reference_prose": has_reference_prose,
        "techniques_found": row.get("techniques_found", []),
    }
    return chat_row, sidecar


def run_eval_prep(
    qualification_jsonl: str | None = None,
    config_path: str | None = None,
    seed: int = 42,
) -> None:
    set_context(stage="eval_prep")
    cfg = load_config(config_path)
    test_sets_cfg = (cfg.raw or {}).get("test_sets") or []
    if not test_sets_cfg:
        logger.warning("No test_sets configured in curation_config.json -> test_sets[]")
        return

    if qualification_jsonl:
        qual_path = Path(qualification_jsonl)
    else:
        latest = resolve_latest("qualification", "jsonl")
        latest_ptr = resolve_latest_pointer("qualification", "jsonl")
        qual_path = latest or latest_ptr or QUALIFICATION_JSONL
    if not qual_path.exists():
        logger.error("Qualification file not found: %s", to_posix_rel(qual_path))
        return

    rng = random.Random(seed)
    rows: list[dict] = []
    with qual_path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    logger.info("eval_prep: loaded %d qualification rows from %s", len(rows), to_posix_rel(qual_path))

    # Pre-bucket by source kind
    marker_pool = [r for r in rows if _is_marker_only_candidate(r)]
    training_pool = [r for r in rows if r.get("tier") in ("gold", "silver", "bronze")
                     and r.get("correct_first_move")]
    logger.info("eval_prep: marker_only pool=%d, training_pool=%d", len(marker_pool), len(training_pool))

    REFINED_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []

    for ts in test_sets_cfg:
        ts_id = ts["id"]
        size = int(ts.get("size", 0))
        selectors = ts.get("selectors") or {}
        source_kind = ts.get("source", "marker_only")

        if source_kind == "marker_only":
            pool = [r for r in marker_pool if _matches_selectors(r, selectors)]
            has_ref = False
        elif source_kind == "training_pool":
            tiers = set(ts.get("tiers") or ["gold", "silver"])
            pool = [r for r in training_pool
                    if r.get("tier") in tiers and _matches_selectors(r, selectors)]
            has_ref = True
        else:
            logger.warning("eval_prep: unknown source '%s' for test set %s", source_kind, ts_id)
            continue

        rng.shuffle(pool)
        chosen = pool[:size]
        out_chat = REFINED_DIR / f"test_{ts_id}.jsonl"
        out_meta = REFINED_DIR / f"test_{ts_id}_metadata.jsonl"
        n_emitted = 0
        with out_chat.open("w", encoding="utf-8") as fc, out_meta.open("w", encoding="utf-8") as fm:
            for row in chosen:
                result = _row_to_test_example(row, ts_id, has_ref)
                if result is None:
                    continue
                chat_row, sidecar = result
                fc.write(json.dumps(chat_row, ensure_ascii=False) + "\n")
                fm.write(json.dumps(sidecar, ensure_ascii=False) + "\n")
                n_emitted += 1

        logger.info("eval_prep: %s -> %d/%d emitted (pool=%d) -> %s",
                    ts_id, n_emitted, size, len(pool), out_chat.name)
        summary.append({
            "test_set_id": ts_id, "source": source_kind, "requested": size,
            "pool": len(pool), "emitted": n_emitted,
            "chat_file": str(out_chat.name), "metadata_file": str(out_meta.name),
        })

    summary_path = REFINED_DIR / "test_sets_summary.json"
    summary_path.write_text(json.dumps({"test_sets": summary}, indent=2), encoding="utf-8")
    print("\nEval test sets:")
    for s in summary:
        print(f"  {s['test_set_id']:32s}  pool={s['pool']:>5}  emitted={s['emitted']:>4}  "
              f"({s['source']})")
    print(f"\nSummary: {summary_path}")
