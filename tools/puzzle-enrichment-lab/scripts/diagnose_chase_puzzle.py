#!/usr/bin/env python3
"""Diagnostic script for chase/capture puzzles that return zero candidates.

Runs the enrichment pipeline on the given SGF with enhanced logging,
then dumps diagnostic data. Supports alternate config profiles via
in-memory overrides (no disk writes).

Usage:
    cd tools/puzzle-enrichment-lab
    python scripts/diagnose_chase_puzzle.py

Profiles:
    default     — Standard config from katago-enrichment.json
    wide_margin — puzzle_region_margin=4 (more candidate moves)
    no_frame    — Skip tsumego frame (raw position analysis)
    high_visits — T1=2000, T2=5000 visits
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

# Ensure lab root is importable
_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

from analyzers.enrich_single import enrich_single_puzzle
from analyzers.frame_adapter import apply_frame
from analyzers.query_builder import build_query_from_position
from analyzers.single_engine import SingleEngineManager
from config import EnrichmentConfig, clear_cache, load_enrichment_config
from config.helpers import KATAGO_PATH, TSUMEGO_CFG, model_path
from core.tsumego_analysis import extract_correct_first_move_color, extract_position, parse_sgf
from log_config import bootstrap

# ---------------------------------------------------------------------------
# Test SGF: chase/capture puzzle (White to move)
# ---------------------------------------------------------------------------
TEST_SGF = "(;GM[1]FF[3]SZ[19]AB[il][kl][kj][hj][ii]AW[jk]PL[W];W[jj];B[ki];W[ik];B[hl];W[ji];B[jh];W[ih];B[kk];W[hi];B[ij];W[hk])"


# ---------------------------------------------------------------------------
# Config profiles (in-memory overrides)
# ---------------------------------------------------------------------------

def make_profile(name: str, base: EnrichmentConfig) -> EnrichmentConfig:
    """Create a config profile by cloning base and applying overrides."""
    cfg = base.model_copy(deep=True)

    if name == "default":
        pass  # No overrides

    elif name == "wide_margin":
        cfg.analysis_defaults.puzzle_region_margin = 4

    elif name == "high_visits":
        cfg.analysis_defaults.default_max_visits = 2000
        if cfg.visit_tiers:
            cfg.visit_tiers.T1.visits = 2000
            cfg.visit_tiers.T2.visits = 5000

    elif name == "relaxed_refutations":
        cfg.refutations.delta_threshold = 0.03
        cfg.refutations.candidate_min_policy = 0.0
        cfg.refutations.candidate_max_count = 10
        cfg.refutations.refutation_max_count = 5
        if cfg.refutation_escalation:
            cfg.refutation_escalation.escalation_delta_threshold = 0.01
            cfg.refutation_escalation.escalation_candidate_min_policy = 0.001

    else:
        raise ValueError(f"Unknown profile: {name}")

    return cfg


# ---------------------------------------------------------------------------
# Step 1: Offline position analysis (no engine needed)
# ---------------------------------------------------------------------------

def diagnose_position(sgf_text: str, config: EnrichmentConfig) -> dict:
    """Analyze position + frame offline. Returns diagnostic dict."""
    root = parse_sgf(sgf_text)

    # Infer player if PL absent
    player_override = None
    pl_prop = root.get("PL")
    if not pl_prop:
        player_override = extract_correct_first_move_color(root)

    position = extract_position(root, player_override=player_override)

    print("\n--- Position Analysis ---")
    print(f"  Board size: {position.board_size}")
    print(f"  Player to move: {position.player_to_move.value}")
    print(f"  Stones: {len(position.stones)} (B={len(position.black_stones)}, W={len(position.white_stones)})")
    print(f"  Komi: {position.komi}")

    # Puzzle region moves (pre-frame)
    margin = config.analysis_defaults.puzzle_region_margin
    region_moves = position.get_puzzle_region_moves(margin=margin)
    print(f"  Puzzle region (margin={margin}): {len(region_moves)} empty intersections")
    print(f"    Sample: {', '.join(sorted(region_moves)[:15])}")

    # Apply frame
    frame_result = apply_frame(
        position,
        margin=margin,
        ko=False,
    )
    framed = frame_result.position
    print("\n--- Frame Analysis ---")
    print(f"  Attacker color: {frame_result.attacker_color.value}")
    print(f"  Stones added: {frame_result.frame_stones_added}")
    print(f"  Total stones after frame: {len(framed.stones)}")
    print(f"  Black stones: {len(framed.black_stones)}")
    print(f"  White stones: {len(framed.white_stones)}")
    print(f"  Empty intersections: {position.board_size**2 - len(framed.stones)}")

    # Check if the player to move has any legal-looking moves in the region
    occupied_after_frame = {(s.x, s.y) for s in framed.stones}
    region_still_empty = [m for m in region_moves if _gtp_to_xy(m, position.board_size) not in occupied_after_frame]
    print(f"  Region moves still empty after frame: {len(region_still_empty)}")
    if region_still_empty:
        print(f"    {', '.join(sorted(region_still_empty)[:20])}")

    # Build the KataGo query to inspect
    query_result = build_query_from_position(
        position,
        max_visits=config.analysis_defaults.default_max_visits,
        config=config,
    )
    req = query_result.request
    payload = req.to_katago_json()
    allow_moves_spec = payload.get("allowMoves", [])
    if allow_moves_spec:
        am_player = allow_moves_spec[0].get("player", "?")
        am_moves = allow_moves_spec[0].get("moves", [])
        am_depth = allow_moves_spec[0].get("untilDepth", "?")
        print("\n--- KataGo allowMoves ---")
        print(f"  Player: {am_player}")
        print(f"  Moves count: {len(am_moves)}")
        print(f"  untilDepth: {am_depth}")
        print(f"  Moves: {', '.join(sorted(am_moves))}")
    else:
        print("\n--- KataGo allowMoves: NONE (all moves allowed) ---")

    print("\n--- KataGo Request Summary ---")
    print(f"  initialPlayer: {payload.get('initialPlayer', '?')}")
    print(f"  boardXSize: {payload.get('boardXSize')}")
    print(f"  maxVisits: {payload.get('maxVisits')}")
    print(f"  rules: {payload.get('rules')}")
    print(f"  initialStones count: {len(payload.get('initialStones', []))}")

    # Framed SGF for visual inspection
    print("\n--- Framed Position SGF ---")
    print(f"  {framed.to_sgf()}")

    return {
        "position": position,
        "framed_position": framed,
        "frame_attacker": frame_result.attacker_color.value,
        "region_moves": region_moves,
        "region_after_frame": region_still_empty,
        "payload": payload,
    }


def _gtp_to_xy(gtp: str, board_size: int) -> tuple[int, int]:
    letters = "ABCDEFGHJKLMNOPQRST"
    col = letters.index(gtp[0].upper())
    row = board_size - int(gtp[1:])
    return col, row


# ---------------------------------------------------------------------------
# Step 2: Full pipeline run (needs KataGo engine)
# ---------------------------------------------------------------------------

async def run_pipeline(
    sgf_text: str,
    config: EnrichmentConfig,
    profile_name: str,
) -> dict:
    """Run full enrichment pipeline and return diagnostic summary."""
    model = model_path("deep_enrich")
    engine_manager = SingleEngineManager(
        config,
        katago_path=str(KATAGO_PATH),
        model_path=str(model),
        katago_config_path=str(TSUMEGO_CFG),
    )

    print(f"\n{'='*60}")
    print(f"  Running pipeline with profile: {profile_name}")
    print(f"{'='*60}")

    t0 = time.monotonic()
    try:
        await engine_manager.start()
        result = await enrich_single_puzzle(
            sgf_text=sgf_text,
            engine_manager=engine_manager,
            config=config,
            source_file=f"diagnose-{profile_name}.sgf",
            run_id=f"diag-{profile_name}",
        )
    finally:
        await engine_manager.shutdown()

    elapsed = time.monotonic() - t0

    # Dump result summary
    v = result.validation
    print(f"\n--- Pipeline Result ({profile_name}, {elapsed:.1f}s) ---")
    print(f"  Status: {v.status}")
    print(f"  Validated: {result.validated}")
    print(f"  Correct move: {result.correct_move}")
    print(f"  Level: {result.level_slug}")
    print(f"  Tags: {result.tags}")
    print(f"  Flags: {v.flags}")
    print(f"  Refutations: {len(result.refutations)}")
    for i, ref in enumerate(result.refutations):
        print(f"    [{i}] move={ref.wrong_move}, policy={ref.wrong_move_policy:.4f}, "
              f"pv={ref.refutation_sequence[:3]}")
    print(f"  Hints: {result.hints}")
    print(f"  Quality: q={result.quality_metrics}")
    print(f"  Complexity: {result.complexity_metrics}")

    if hasattr(result, 'enriched_sgf') and result.enriched_sgf:
        print("\n--- Enriched SGF ---")
        print(f"  {result.enriched_sgf[:500]}")

    return {
        "profile": profile_name,
        "status": str(v.status),
        "validated": result.validated,
        "correct_move": result.correct_move,
        "refutation_count": len(result.refutations),
        "level": result.level_slug,
        "tags": result.tags,
        "flags": v.flags,
        "elapsed": elapsed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    bootstrap(verbose=True, console_format="human")

    # Configure console logging to see everything
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Ensure at least one INFO handler on console
    has_console = any(
        isinstance(h, logging.StreamHandler) and h.stream in (sys.stdout, sys.stderr)
        for h in root_logger.handlers
    )
    if not has_console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root_logger.addHandler(ch)

    print("=" * 60)
    print("  Chase Puzzle Diagnostic")
    print("=" * 60)
    print(f"\nSGF: {TEST_SGF}")

    # Load base config
    clear_cache()
    base_config = load_enrichment_config()

    # Step 1: Offline position analysis (always runs)
    diagnose_position(TEST_SGF, base_config)

    # Step 2: Check if KataGo is available before attempting pipeline
    if not KATAGO_PATH.exists():
        print(f"\n*** KataGo not found at {KATAGO_PATH} — skipping pipeline runs ***")
        print("Position analysis above should reveal the issue.")
        return

    # Determine which profiles to run
    profiles = sys.argv[1:] if len(sys.argv) > 1 else ["default"]

    results = []
    for profile_name in profiles:
        clear_cache()  # Fresh config each time
        base = load_enrichment_config()
        profile_config = make_profile(profile_name, base)

        # Log profile overrides
        if profile_name != "default":
            print(f"\n--- Profile overrides: {profile_name} ---")
            if profile_name == "wide_margin":
                print(f"  puzzle_region_margin: {base.analysis_defaults.puzzle_region_margin} → {profile_config.analysis_defaults.puzzle_region_margin}")
            elif profile_name == "high_visits":
                print(f"  T1 visits: {base.visit_tiers.T1.visits} → {profile_config.visit_tiers.T1.visits}")
                print(f"  T2 visits: {base.visit_tiers.T2.visits} → {profile_config.visit_tiers.T2.visits}")
            elif profile_name == "relaxed_refutations":
                print(f"  delta_threshold: {base.refutations.delta_threshold} → {profile_config.refutations.delta_threshold}")
                print(f"  candidate_max_count: {base.refutations.candidate_max_count} → {profile_config.refutations.candidate_max_count}")

        result = await run_pipeline(TEST_SGF, profile_config, profile_name)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for r in results:
        print(f"  [{r['profile']}] status={r['status']}, "
              f"refutations={r['refutation_count']}, "
              f"validated={r['validated']}, "
              f"elapsed={r['elapsed']:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
