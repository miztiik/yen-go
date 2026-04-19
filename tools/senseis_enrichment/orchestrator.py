"""Orchestrator for full Senseis enrichment pipeline.

Iterates through all problems with checkpoint/resume support,
fetching metadata + solutions and merging into enriched SGF copies.

Supports two iteration modes:
  - Default (N↔N): local file N maps to Senseis problem N (Xuan Xuan, Hatsuyo-ron)
  - Position-mapped: reads _position_mapping.json to resolve local↔Senseis pairs
    (Gokyo Shumyo, where local sequential numbers don't match Senseis section numbering)
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
from tools.core.sgf_types import PositionTransform

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


# --- Position mapping support ---

@dataclass
class MappedProblem:
    """A problem resolved via position mapping."""

    local_n: int
    senseis_n: int  # Global sequential number for Senseis
    page_name: str
    section_name: str
    section_pos: int
    transform: PositionTransform
    match_type: str


def _load_position_mapping(config: SenseisConfig) -> list[MappedProblem] | None:
    """Load position mapping if available. Returns None if not found."""
    mapping_path = config.working_dir() / "_position_mapping.json"
    if not mapping_path.exists():
        return None

    with open(mapping_path, encoding="utf-8") as f:
        data = json.load(f)

    if "mappings" not in data:
        return None

    result = []
    for m in data["mappings"]:
        t = m.get("transform", {})
        result.append(MappedProblem(
            local_n=m["local_n"],
            senseis_n=m["senseis_global"],
            page_name=m["page_name"],
            section_name=m.get("section_name", ""),
            section_pos=m.get("section_pos", 0),
            transform=PositionTransform(
                rotation=t.get("rotation", 0),
                reflect=t.get("reflect", False),
            ),
            match_type=m.get("match_type", "exact"),
        ))

    # Sort by senseis_n for consistent ordering
    result.sort(key=lambda x: x.senseis_n)
    logger.info("Loaded position mapping: %d entries", len(result))
    return result


# --- Download mode helpers ---

def _create_local_from_diagram(config: SenseisConfig, n: int) -> bool:
    """Create a local SGF file from cached Senseis diagram data (download mode).

    Reuses create_sgf_from_diagram() from create_missing_sgfs module.
    Returns True if the file was created successfully.
    """
    from tools.senseis_enrichment.create_missing_sgfs import create_sgf_from_diagram

    sgf_content = create_sgf_from_diagram(config, n)
    if sgf_content is None:
        return False

    local_path = config.local_sgf_path(n)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(sgf_content, encoding="utf-8")
    logger.info("  P%d: created local file from diagram: %s", n, local_path.name)
    return True


def _merge_variant_trees(config: SenseisConfig) -> None:
    """Merge variant problem trees into their parent enriched SGFs.

    For collections with a 'variants' map (e.g. ShikatsuMyoki), each variant
    is a standalone puzzle that is a variation of a parent problem. This step
    reads the enriched variant SGF and grafts its solution tree onto the parent
    as an additional branch with a '(Variant N)' comment.
    """
    if not config.variants:
        return

    from tools.core.sgf_parser import parse_sgf, read_sgf_file
    from tools.core.sgf_builder import SGFBuilder

    merged_count = 0
    for parent_str, children in config.variants.items():
        parent_n = int(parent_str)
        parent_path = config.enriched_sgf_path(parent_n)
        if not parent_path.exists():
            logger.warning("Variant merge: parent %d enriched file missing", parent_n)
            continue

        parent_content, _ = read_sgf_file(parent_path)
        try:
            parent_tree = parse_sgf(parent_content)
        except Exception as e:
            logger.error("Variant merge: failed to parse parent %d: %s", parent_n, e)
            continue

        variants_added = 0
        for child_n in children:
            child_path = config.enriched_sgf_path(child_n)
            if not child_path.exists():
                logger.warning("Variant merge: child %d enriched file missing", child_n)
                continue

            child_content, _ = read_sgf_file(child_path)
            try:
                child_tree = parse_sgf(child_content)
            except Exception as e:
                logger.error("Variant merge: failed to parse child %d: %s", child_n, e)
                continue

            # Graft the variant's solution tree onto the parent's root
            # The variant has its own setup stones + solution tree
            # We add the variant's solution branches as children of the parent root
            variant_root = child_tree.solution_tree
            if variant_root.children:
                for branch in variant_root.children:
                    # Tag the first move of each branch with variant info
                    variant_label = f"(Variant {child_n})"
                    if branch.comment:
                        branch.comment = f"{variant_label} {branch.comment}"
                    else:
                        branch.comment = variant_label
                    parent_tree.solution_tree.add_child(branch)
                    variants_added += 1

        if variants_added > 0:
            # Rebuild and save the parent SGF
            builder = SGFBuilder.from_tree(parent_tree)
            builder.root_comment = parent_tree.root_comment
            new_sgf = builder.build()
            parent_path.write_text(new_sgf, encoding="utf-8")
            merged_count += 1
            logger.info(
                "Variant merge: parent %d <- %d variant branches from %s",
                parent_n, variants_added, children,
            )

    logger.info("Variant merge complete: %d parents updated", merged_count)


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

    ckpt_dir = config.working_dir()
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Check for position mapping (used by Gokyo Shumyo etc.)
    pos_mapping = _load_position_mapping(config)

    if pos_mapping is not None:
        return _run_mapped_enrichment(config, pos_mapping, start, end, dry_run)
    else:
        return _run_sequential_enrichment(config, start, end, dry_run)


def _run_mapped_enrichment(
    config: SenseisConfig,
    pos_mapping: list[MappedProblem],
    start: int | None,
    end: int | None,
    dry_run: bool,
) -> dict:
    """Run enrichment using position mapping (local↔Senseis pairs pre-resolved)."""
    ckpt_dir = config.working_dir()

    checkpoint = load_checkpoint(ckpt_dir, EnrichmentCheckpoint)
    if checkpoint is None:
        checkpoint = EnrichmentCheckpoint()

    # Filter mapping by range (using senseis_n for ordering)
    entries = pos_mapping
    if start is not None:
        entries = [e for e in entries if e.senseis_n >= start]
    if end is not None:
        entries = [e for e in entries if e.senseis_n <= end]

    # Resume from checkpoint
    if start is None and checkpoint.last_completed > 0:
        entries = [e for e in entries if e.senseis_n > checkpoint.last_completed]
        if entries:
            logger.info("Resuming from Senseis #%d (checkpoint)", entries[0].senseis_n)

    if not entries:
        logger.info("Nothing to do (all entries filtered or completed)")
        return _summary(checkpoint)

    if not dry_run:
        prepare_enriched_directory(config)

    # Build index for fetcher
    index_cache = config.index_cache_path()
    if index_cache.exists():
        with open(index_cache, encoding="utf-8") as f:
            raw = json.load(f)
        index = {int(k): v for k, v in raw.items()}
    else:
        index = {e.senseis_n: e.page_name for e in pos_mapping}

    with SenseisFetcher(config) as fetcher:
        total = len(entries)
        logger.info("Processing %d mapped problems", total)

        for i, mapped in enumerate(entries, 1):
            sn = mapped.senseis_n
            ln = mapped.local_n
            logger.info(
                "--- [%d/%d] Senseis #%d (%s) <-> Local #%d ---",
                i, total, sn, mapped.page_name, ln,
            )

            # Fetch using Senseis number
            page_data = fetcher.fetch_problem_page(sn, index)
            if page_data is None:
                logger.warning("  S%d: problem page fetch failed, skipping", sn)
                checkpoint.total_skipped += 1
                checkpoint.skipped_problems.append(sn)
                checkpoint.last_completed = sn
                save_checkpoint(checkpoint, ckpt_dir)
                continue

            solution_data = fetcher.fetch_solution_page(sn, index)

            # Use pre-computed match from position mapping
            match_result = MatchResult(
                problem_number=sn,
                matched=True,
                transform=mapped.transform,
                detail=f"{mapped.match_type} (section: {mapped.section_name} #{mapped.section_pos})",
            )
            checkpoint.total_matched += 1

            sol_status = solution_data.status if solution_data else "none"
            sol_diagrams = len(solution_data.diagrams) if solution_data else 0
            logger.info(
                "  S%d->L%d: sol=%s (%d diagrams), match=%s",
                sn, ln, sol_status, sol_diagrams, match_result.detail,
            )

            if not dry_run:
                # Merge using LOCAL file number for file paths
                success = merge_problem(config, ln, page_data, solution_data, match_result)
                if success:
                    checkpoint.total_enriched += 1
                else:
                    checkpoint.total_failed += 1
                    checkpoint.failed_problems.append(sn)
                    logger.warning("  S%d->L%d: merge FAILED", sn, ln)

            checkpoint.last_completed = sn
            save_checkpoint(checkpoint, ckpt_dir)

    return _finish_enrichment(config, checkpoint)


def _run_sequential_enrichment(
    config: SenseisConfig,
    start: int | None,
    end: int | None,
    dry_run: bool,
) -> dict:
    """Run enrichment with default N↔N mapping (original behavior).

    Supports download mode: when local_dir doesn't exist, creates local SGF
    files from Senseis diagram data before enrichment.
    """
    end = end or config.problem_count
    ckpt_dir = config.working_dir()

    checkpoint = load_checkpoint(ckpt_dir, EnrichmentCheckpoint)
    if checkpoint is None:
        checkpoint = EnrichmentCheckpoint()

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

    # Detect download mode: local directory doesn't exist yet
    download_mode = not config.local_dir_exists()
    if download_mode:
        logger.info("Download mode: local_dir does not exist, will create from Senseis diagrams")
        config.ensure_local_dir()

    if not dry_run:
        prepare_enriched_directory(config)

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

            # Fetch problem page first (needed for download mode)
            page_data = fetcher.fetch_problem_page(n, index)
            if page_data is None:
                logger.warning("  P%d: problem page fetch failed, skipping", n)
                checkpoint.total_skipped += 1
                checkpoint.skipped_problems.append(n)
                checkpoint.last_completed = n
                save_checkpoint(checkpoint, ckpt_dir)
                continue

            # Download mode: create local file from diagram if needed
            if not config.local_sgf_path(n).exists():
                if download_mode:
                    created = _create_local_from_diagram(config, n)
                    if not created:
                        logger.warning("  P%d: could not create local file from diagram, skipping", n)
                        checkpoint.total_skipped += 1
                        checkpoint.skipped_problems.append(n)
                        checkpoint.last_completed = n
                        save_checkpoint(checkpoint, ckpt_dir)
                        continue
                else:
                    logger.warning("  P%d: local file missing, skipping", n)
                    checkpoint.total_skipped += 1
                    checkpoint.skipped_problems.append(n)
                    checkpoint.last_completed = n
                    save_checkpoint(checkpoint, ckpt_dir)
                    continue

            solution_data = fetcher.fetch_solution_page(n, index)

            match_result = _match_problem(config, n, page_data)
            if match_result.matched:
                checkpoint.total_matched += 1
            else:
                logger.info("  P%d: no position match (%s)", n, match_result.detail)

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

    summary = _finish_enrichment(config, checkpoint)

    # Post-enrichment: merge variant trees into parent problems
    if not dry_run and config.variants:
        _merge_variant_trees(config)

    return summary


def _finish_enrichment(config: SenseisConfig, checkpoint: EnrichmentCheckpoint) -> dict:
    """Log summary and save results."""
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
