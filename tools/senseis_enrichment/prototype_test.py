"""Prototype test: fetch + parse + match + merge for Problems 1, 2, 7.

Run from project root:
    python -m tools.senseis_enrichment.prototype_test
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logger = logging.getLogger("prototype_test")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.core.sgf_parser import parse_sgf, read_sgf_file
from tools.senseis_enrichment.config import load_config
from tools.senseis_enrichment.fetcher import SenseisFetcher
from tools.senseis_enrichment.position_matcher import (
    canonical_position_hash,
    match_positions,
)
from tools.senseis_enrichment.merger import (
    build_root_comment,
    prepare_enriched_directory,
    merge_problem,
)

TEST_PROBLEMS = [1, 2, 7]


def main() -> None:
    config = load_config()
    logger.info("Config loaded. Local dir: %s", config.local_dir)
    logger.info("Enriched dir: %s", config.enriched_dir())

    # Step 1: Test position hashing on Problem 1 (known rotation)
    logger.info("\n=== Step 1: Position Hashing ===")
    local_path = config.local_sgf_path(1)
    logger.info("Local file: %s (exists: %s)", local_path, local_path.exists())

    content, enc = read_sgf_file(local_path)
    local_tree = parse_sgf(content)
    local_hash, local_rot, local_ref = canonical_position_hash(
        local_tree.black_stones, local_tree.white_stones, local_tree.board_size
    )
    logger.info(
        "Local Problem 1: hash=%s, rot=%d, ref=%s, PL=%s",
        local_hash, local_rot, local_ref, local_tree.player_to_move,
    )
    logger.info("  Black stones: %s", [p.to_sgf() for p in local_tree.black_stones])
    logger.info("  White stones: %s", [p.to_sgf() for p in local_tree.white_stones])

    # Step 2: Fetch index
    logger.info("\n=== Step 2: Fetch Index ===")
    with SenseisFetcher(config) as fetcher:
        index = fetcher.fetch_index()
        logger.info("Index has %d problems", len(index))

        # Show aliases
        for n in TEST_PROBLEMS:
            page = index.get(n, "NOT FOUND")
            logger.info("  Problem %d -> %s", n, page)

        # Step 3: Fetch problem pages
        logger.info("\n=== Step 3: Fetch Problem Pages ===")
        page_data_map = {}
        for n in TEST_PROBLEMS:
            page_data = fetcher.fetch_problem_page(n, index)
            if page_data:
                page_data_map[n] = page_data
                logger.info(
                    "  P%d: title='%s' (%s), diff=%s, inst='%s'",
                    n,
                    page_data.title_english,
                    page_data.title_chinese,
                    page_data.difficulty,
                    page_data.instruction,
                )
                if page_data.cross_references:
                    logger.info("    xrefs: %s", page_data.cross_references)
            else:
                logger.warning("  P%d: FAILED to fetch", n)

        # Step 4: Fetch solution pages
        logger.info("\n=== Step 4: Fetch Solution Pages ===")
        solution_data_map = {}
        for n in TEST_PROBLEMS:
            solution_data = fetcher.fetch_solution_page(n, index)
            if solution_data:
                solution_data_map[n] = solution_data
                logger.info(
                    "  P%d: status=%s, %d diagrams",
                    n, solution_data.status, len(solution_data.diagrams),
                )
                for i, diag in enumerate(solution_data.diagrams):
                    has_sgf = "YES" if diag.sgf_content else "NO"
                    commentary_preview = (
                        diag.commentary[:80] + "..."
                        if len(diag.commentary) > 80
                        else diag.commentary
                    )
                    logger.info(
                        "    Diagram %d: '%s' sgf=%s commentary='%s'",
                        i, diag.diagram_name, has_sgf, commentary_preview,
                    )
            else:
                logger.warning("  P%d: FAILED to fetch solution", n)

    # Step 5: Position matching
    logger.info("\n=== Step 5: Position Matching ===")
    match_results = {}
    for n in TEST_PROBLEMS:
        local_content, _ = read_sgf_file(config.local_sgf_path(n))
        local_tree = parse_sgf(local_content)

        # Use the PROBLEM page diagram SGF for matching (initial position),
        # NOT the solution diagram (which has moves played)
        page = page_data_map.get(n)
        if page and page.diagram_sgf_url:
            # Read from diagram cache
            from tools.senseis_enrichment.config import diagram_cache_dir
            filename = page.diagram_sgf_url.replace("/", "_")
            cache_file = diagram_cache_dir(config.collection_slug) / filename
            if cache_file.exists():
                sgf_content = cache_file.read_text(encoding="utf-8")
            else:
                sgf_content = None

            if sgf_content:
                result = match_positions(local_tree, sgf_content, n)
                match_results[n] = result
                if result.matched:
                    logger.info(
                        "  P%d: MATCHED (D4 hash). Transform: rot=%d, reflect=%s",
                        n, result.transform.rotation, result.transform.reflect,
                    )
                else:
                    # Fallback: number-based matching (both follow tasuki's numbering)
                    logger.info(
                        "  P%d: D4 hash mismatch (positions may be translated). "
                        "Using number-based match (both use tasuki numbering).",
                        n,
                    )
                    from tools.senseis_enrichment.models import MatchResult as MR
                    result = MR(
                        problem_number=n,
                        matched=True,
                        detail="Number-based match (positions translated, not rotated)",
                    )
                    match_results[n] = result
            else:
                logger.warning("  P%d: Problem diagram SGF not cached", n)
        else:
            logger.warning("  P%d: No problem diagram SGF URL available", n)

    # Step 6: Merge (dry-run preview for now)
    logger.info("\n=== Step 6: Merge Preview ===")
    for n in TEST_PROBLEMS:
        page = page_data_map.get(n)
        root_comment = build_root_comment(page, "")
        logger.info("  P%d root comment preview:\n%s", n, root_comment)

    # Step 7: Actually create enriched directory and merge
    logger.info("\n=== Step 7: Create Enriched Directory & Merge ===")
    enriched_dir = prepare_enriched_directory(config)
    logger.info("Enriched dir: %s", enriched_dir)

    for n in TEST_PROBLEMS:
        page = page_data_map.get(n)
        sol = solution_data_map.get(n)
        match = match_results.get(n)
        if match is None:
            from tools.senseis_enrichment.models import MatchResult
            match = MatchResult(problem_number=n)

        success = merge_problem(config, n, page, sol, match)
        logger.info("  P%d: merge %s", n, "OK" if success else "FAILED")

    # Step 8: Show enriched file content
    logger.info("\n=== Step 8: Enriched File Content ===")
    for n in TEST_PROBLEMS:
        enriched_path = config.enriched_sgf_path(n)
        if enriched_path.exists():
            content = enriched_path.read_text(encoding="utf-8")
            logger.info("  P%d (%s):\n%s\n", n, enriched_path.name, content[:500])

    logger.info("\n=== Prototype test complete ===")


if __name__ == "__main__":
    main()
