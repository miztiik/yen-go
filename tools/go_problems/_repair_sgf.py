"""One-time repair: re-fetch and re-enrich all SGF files with updated stripping + whitespace cleanup."""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
from pathlib import Path

import httpx

from tools.go_problems.collections import resolve_collection_slugs
from tools.go_problems.converter import _extract_root_comment, enrich_sgf
from tools.go_problems.levels import map_rank_to_level
from tools.go_problems.models import GoProblemsDetail
from tools.go_problems.quality import compute_quality_score, format_yq
from tools.go_problems.tags import map_collections_to_tags, map_genre_to_tags

sgf_dir = Path(__file__).resolve().parent.parent.parent / "external-sources" / "goproblems" / "sgf" / "batch-001"
files = sorted(sgf_dir.glob("*.sgf"))
print(f"Re-enriching {len(files)} files from {sgf_dir}...")

client = httpx.Client(timeout=30, headers={"User-Agent": "YenGo/1.0"})
fixed = 0
errors = 0

for sgf_file in files:
    puzzle_id = int(sgf_file.stem)
    try:
        resp = client.get(f"https://www.goproblems.com/api/v2/problems/{puzzle_id}")
        if resp.status_code != 200:
            print(f"  {puzzle_id}: HTTP {resp.status_code}, skipping")
            errors += 1
            continue

        raw_data = resp.json()
        puzzle = GoProblemsDetail.model_validate(raw_data)

        tags = map_genre_to_tags(puzzle.genre)
        if puzzle.collections:
            coll_tags = map_collections_to_tags([c.model_dump() for c in puzzle.collections])
            tags.extend(coll_tags)
        tags = sorted(set(tags))

        rank_dict = puzzle.rank.model_dump() if puzzle.rank else None
        level = map_rank_to_level(rank_dict, puzzle.problemLevel)

        collection_slugs = None
        if puzzle.collections:
            collection_slugs = resolve_collection_slugs([c.model_dump() for c in puzzle.collections])

        q_score = compute_quality_score(puzzle.rating, puzzle.isCanon)
        yq_value = format_yq(q_score)
        player_color = (puzzle.playerColor or "black").lower()
        pl_value = "B" if player_color == "black" else "W"

        root_comment = None
        raw_comment = _extract_root_comment(puzzle.sgf)
        if raw_comment:
            try:
                from tools.go_problems.logging_config import get_logger
                from tools.go_problems.orchestrator import _resolve_puzzle_intent
                logger = get_logger()
                root_comment = _resolve_puzzle_intent(puzzle_id, raw_comment, 0.8, logger)
            except Exception:
                pass

        enriched = enrich_sgf(
            sgf_content=puzzle.sgf,
            puzzle_id=puzzle.id,
            level=level,
            tags=tags,
            pl_value=pl_value,
            collection_slugs=collection_slugs,
            yq_value=yq_value,
            root_comment=root_comment,
        )

        sgf_file.write_text(enriched, encoding="utf-8")
        fixed += 1
        print(f"  {puzzle_id}: OK (level={level}, tags={tags})")
        time.sleep(0.3)

    except Exception as e:
        print(f"  {puzzle_id}: ERROR {e}")
        errors += 1

client.close()
print(f"\nDone: {fixed} fixed, {errors} errors out of {len(files)} total")
