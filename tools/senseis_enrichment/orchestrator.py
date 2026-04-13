"""Orchestrator for full Senseis enrichment pipeline.

Iterates through all problems with checkpoint/resume support,
fetching metadata + solutions and merging into enriched SGF copies.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.checkpoint import (
    ToolCheckpoint,
    load_checkpoint,
    save_checkpoint,
    clear_checkpoint,
)

from tools.senseis_enrichment.config import (
    SenseisConfig,
    load_config,
)
from tools.senseis_enrichment.fetcher import SenseisFetcher
from tools.senseis_enrichment.merger import merge_problem, prepare_enriched_directory
from tools.senseis_enrichment.models import MatchResult, SenseisPageData, SenseisSolutionData
from tools.senseis_enrichment.position_matcher import match_positions

from tools.core.sgf_parser import parse_sgf, read_sgf_file

logger = logging.getLogger("senseis_enrichment.orchestrator")


# --- Checkpoint ---

@dataclass
class EnrichmentCheckpoint(ToolCheckpoint):
    """Tracks enrichment progress through the collection."""

    last_completed: int = 0  # Last problem number successfully processed
    total_matched: int = 0
    total_enriched: int = 0
    total_failed: int = 0
    total_skipped: int = 0  # 404s, empty pages, etc.
    failed_problems: list[int] = field(default_factory=list)
    skipped_problems: list[int] = field(default_factory=list)


# --- Position matching with fallback ---

def _match_problem(
    config: SenseisConfig,
    n: int,
    page_data: SenseisPageData | None,
) -> MatchResult:
    """Match a local SGF position against Senseis diagram, with number-based fallback."""
    local_path = config.local_sgf_path(n)
    if not local_path.exists():
        return MatchResult(problem_number=n, detail="Local file not found")

    # Try D4 hash matching via the problem page diagram SGF
    if page_data and page_data.diagram_sgf_url:
        filename = page_data.diagram_sgf_url.replace("/", "_")
        cache_file = config.diagram_cache_dir() / filename
        if cache_file.exists():
            sgf_content = cache_file.read_text(encoding="utf-8")
            local_content, _ = read_sgf_file(local_path)
            local_tree = parse_sgf(local_content)
            result = match_positions(local_tree, sgf_content, n)
            if result.matched:
                return result

    # Fallback: number-based matching (both sources use tasuki's numbering)
    return MatchResult(
        problem_number=n,
        matched=True,
        detail="Number-based match (positions may be translated)",
    )


# --- Main orchestration ---

def run_enrichment(
    config: SenseisConfig | None = None,
    start: int | None = None,
    end: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Run the full enrichment pipeline.

    Args:
        config: Configuration (loaded from JSON if None).
        start: First problem number (1-based, overrides checkpoint).
        end: Last problem number (inclusive).
        dry_run: If True, fetch and match but don't merge.

    Returns:
        Summary dict with counts.
    """
    if config is None:
        config = load_config()

    end = end or config.problem_count
    ckpt_dir = config.working_dir()
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Load checkpoint
    checkpoint = load_checkpoint(ckpt_dir, EnrichmentCheckpoint)
    if checkpoint is None:
        checkpoint = EnrichmentCheckpoint()

    # Resume from checkpoint unless explicit start given
    if start is not None:
        resume_from = start
    elif checkpoint.last_completed > 0:
        resume_from = checkpoint.last_completed + 1
        logger.info("Resuming from problem %d (checkpoint)", resume_from)
    else:
        resume_from = 1

    if resume_from > end:
        logger.info("Nothing to do: start=%d > end=%d", resume_from, end)
        return _summary(checkpoint)

    # Prepare enriched directory (copy originals if not done)
    if not dry_run:
        prepare_enriched_directory(config)

    # Fetch index
    with SenseisFetcher(config) as fetcher:
        index = fetcher.fetch_index()
        if not index:
            logger.error("Failed to fetch index. Aborting.")
            return _summary(checkpoint)

        logger.info(
            "Processing problems %d-%d (%d total)",
            resume_from, end, end - resume_from + 1,
        )

        for n in range(resume_from, end + 1):
            logger.info("--- Problem %d/%d ---", n, end)

            # Check local file exists
            if not config.local_sgf_path(n).exists():
                logger.warning("  P%d: local file missing, skipping", n)
                checkpoint.total_skipped += 1
                checkpoint.skipped_problems.append(n)
                checkpoint.last_completed = n
                save_checkpoint(checkpoint, ckpt_dir)
                continue

            # Fetch problem page
            page_data = fetcher.fetch_problem_page(n, index)
            if page_data is None:
                logger.warning("  P%d: problem page fetch failed, skipping", n)
                checkpoint.total_skipped += 1
                checkpoint.skipped_problems.append(n)
                checkpoint.last_completed = n
                save_checkpoint(checkpoint, ckpt_dir)
                continue

            # Fetch solution page
            solution_data = fetcher.fetch_solution_page(n, index)

            # Position matching
            match_result = _match_problem(config, n, page_data)
            if match_result.matched:
                checkpoint.total_matched += 1
            else:
                logger.info("  P%d: no position match (%s)", n, match_result.detail)

            # Log summary for this problem
            sol_status = solution_data.status if solution_data else "none"
            sol_diagrams = len(solution_data.diagrams) if solution_data else 0
            logger.info(
                "  P%d: page=%s, sol=%s (%d diagrams), match=%s",
                n,
                "ok" if page_data else "fail",
                sol_status,
                sol_diagrams,
                match_result.detail or f"rot={match_result.transform.rotation}, ref={match_result.transform.reflect}" if match_result.transform else "number-based",
            )

            # Merge
            if not dry_run:
                success = merge_problem(config, n, page_data, solution_data, match_result)
                if success:
                    checkpoint.total_enriched += 1
                else:
                    checkpoint.total_failed += 1
                    checkpoint.failed_problems.append(n)
                    logger.warning("  P%d: merge FAILED", n)

            checkpoint.last_completed = n
            save_checkpoint(checkpoint, ckpt_dir)

    # Done
    summary = _summary(checkpoint)
    logger.info("=== Enrichment complete ===")
    logger.info(
        "Matched: %d, Enriched: %d, Failed: %d, Skipped: %d",
        summary["matched"], summary["enriched"], summary["failed"], summary["skipped"],
    )
    if checkpoint.failed_problems:
        logger.info("Failed problems: %s", checkpoint.failed_problems)
    if checkpoint.skipped_problems:
        logger.info("Skipped problems: %s", checkpoint.skipped_problems)

    # Save final results
    results_path = config.working_dir() / "_enrichment_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Results saved to %s", results_path)

    return summary


def _summary(checkpoint: EnrichmentCheckpoint) -> dict:
    return {
        "last_completed": checkpoint.last_completed,
        "matched": checkpoint.total_matched,
        "enriched": checkpoint.total_enriched,
        "failed": checkpoint.total_failed,
        "skipped": checkpoint.total_skipped,
        "failed_problems": checkpoint.failed_problems,
        "skipped_problems": checkpoint.skipped_problems,
    }
