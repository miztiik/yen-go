"""Gokyo Shumyo index builder with position matching.

Generates the Sensei's Library index for Gokyo Shumyo using the section
structure from config, then fetches all diagram SGFs and position-matches
them against local files using D4-invariant canonical hashing.

Usage:
    # Build index, fetch diagrams, and run position matching
    python -m tools.senseis_enrichment._build_gokyo_index

    # Only rebuild index cache (no fetching/matching)
    python -m tools.senseis_enrichment._build_gokyo_index --index-only

    # Re-run position matching from cached data (no network)
    python -m tools.senseis_enrichment._build_gokyo_index --match-only

    # Custom config path
    python -m tools.senseis_enrichment._build_gokyo_index --config path/to/config.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.core.position_transform import (
    canonical_position_hash,
    find_transform,
    transform_point,
)
from tools.core.sgf_parser import SgfTree, parse_sgf, read_sgf_file
from tools.core.sgf_types import Point, PositionTransform
from tools.senseis_enrichment.config import SenseisConfig, load_config
from tools.senseis_enrichment.fetcher import SenseisFetcher

logger = logging.getLogger("senseis_enrichment.build_gokyo_index")

_TOOL_DIR = Path(__file__).parent
_PROJECT_ROOT = _TOOL_DIR.parent.parent


# --- Data structures ---

@dataclass
class SenseisEntry:
    """A single Sensei's Library problem entry."""

    global_n: int
    page_name: str
    section_number: int
    section_name: str
    section_problem_number: int
    canonical_hash: str = ""
    transform_to_canonical: dict | None = None


@dataclass
class LocalEntry:
    """A local SGF file entry."""

    local_n: int
    filename: str
    canonical_hash: str = ""
    transform_to_canonical: dict | None = None


@dataclass
class MappingEntry:
    """A matched local ↔ Sensei's pair."""

    local_file: str
    local_n: int
    senseis_global: int
    page_name: str
    section_number: int
    section_name: str
    section_pos: int
    transform: dict
    match_type: str  # "exact" (identity) or "d4_symmetry"


@dataclass
class PositionMapping:
    """Complete position mapping result."""

    mappings: list[MappingEntry] = field(default_factory=list)
    unmatched_local: list[dict] = field(default_factory=list)
    unmatched_senseis: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# --- Step 1: Generate index from sections config ---

def build_index_from_sections(config: SenseisConfig) -> dict[int, SenseisEntry]:
    """Generate global sequential → SenseisEntry mapping from sections config.

    Returns dict keyed by global sequential number (1-based).
    """
    if not config.sections:
        raise ValueError("Config has no sections defined")

    entries: dict[int, SenseisEntry] = {}
    global_n = 1

    for section in config.sections:
        section_number = section["number"]
        section_name = section["name"]
        prefix = section["senseis_prefix"]

        # Section 7 has non-contiguous numbering
        if "number_list" in section:
            problem_numbers = section["number_list"]
        else:
            problem_numbers = list(range(1, section["count"] + 1))

        for prob_n in problem_numbers:
            page_name = f"{prefix}{prob_n}"
            entries[global_n] = SenseisEntry(
                global_n=global_n,
                page_name=page_name,
                section_number=section_number,
                section_name=section_name,
                section_problem_number=prob_n,
            )
            global_n += 1

    return entries


def save_index_cache(entries: dict[int, SenseisEntry], cache_path: Path) -> None:
    """Save index as {global_n: page_name} for pipeline compatibility."""
    index = {str(n): e.page_name for n, e in sorted(entries.items())}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    logger.info("Saved index cache: %d entries -> %s", len(index), cache_path)


# --- Step 2: Fetch diagram SGFs ---

def fetch_all_diagrams(
    config: SenseisConfig,
    entries: dict[int, SenseisEntry],
) -> None:
    """Fetch all problem pages and diagram SGFs from Sensei's Library.

    Results cached in _page_cache/ and _diagram_sgfs/.
    """
    # Build a temporary index compatible with SenseisFetcher
    index = {n: e.page_name for n, e in entries.items()}

    with SenseisFetcher(config) as fetcher:
        # Override the fetcher's index
        total = len(entries)
        for i, (n, entry) in enumerate(sorted(entries.items()), 1):
            logger.info("Fetching %d/%d: P%d (%s)", i, total, n, entry.page_name)
            fetcher.fetch_problem_page(n, index)


# --- Step 3: Build position hash indexes ---

def _extract_stones(tree: SgfTree) -> tuple[list[Point], list[Point]]:
    """Extract black and white stone lists from a parsed SGF tree."""
    return tree.black_stones, tree.white_stones


def build_senseis_hashes(
    config: SenseisConfig,
    entries: dict[int, SenseisEntry],
) -> dict[str, list[SenseisEntry]]:
    """Compute canonical position hashes for all Sensei's diagrams.

    Returns {canonical_hash: [SenseisEntry, ...]}.
    """
    hash_index: dict[str, list[SenseisEntry]] = {}
    page_cache = config.page_cache_dir()
    diagram_cache = config.diagram_cache_dir()

    for n, entry in sorted(entries.items()):
        # Load cached page data to get diagram SGF URL
        page_file = page_cache / f"{n:04d}.json"
        if not page_file.exists():
            logger.debug("  P%d: no cached page, skipping hash", n)
            continue

        with open(page_file, encoding="utf-8") as f:
            page_data = json.load(f)

        diagram_url = page_data.get("diagram_sgf_url", "")
        if not diagram_url:
            logger.debug("  P%d: no diagram SGF URL", n)
            continue

        # Load cached diagram SGF
        diagram_filename = diagram_url.replace("/", "_")
        diagram_file = diagram_cache / diagram_filename
        if not diagram_file.exists():
            logger.debug("  P%d: diagram SGF not cached", n)
            continue

        sgf_content = diagram_file.read_text(encoding="utf-8")
        try:
            tree = parse_sgf(sgf_content)
        except Exception as e:
            logger.warning("  P%d: failed to parse diagram SGF: %s", n, e)
            continue

        black, white = _extract_stones(tree)
        if not black and not white:
            logger.debug("  P%d: empty position", n)
            continue

        c_hash, c_transform = canonical_position_hash(black, white, tree.board_size)
        entry.canonical_hash = c_hash
        entry.transform_to_canonical = asdict(c_transform)

        hash_index.setdefault(c_hash, []).append(entry)

    logger.info("Built Sensei's hash index: %d unique hashes from %d entries",
                len(hash_index), sum(len(v) for v in hash_index.values()))
    return hash_index


def build_local_hashes(
    config: SenseisConfig,
) -> tuple[dict[str, list[LocalEntry]], list[LocalEntry]]:
    """Compute canonical position hashes for all local SGF files.

    Returns ({canonical_hash: [LocalEntry, ...]}, all_entries).
    """
    local_dir = _PROJECT_ROOT / config.local_dir
    hash_index: dict[str, list[LocalEntry]] = {}
    all_entries: list[LocalEntry] = []

    sgf_files = sorted(local_dir.glob("*.sgf"))
    logger.info("Hashing %d local SGF files from %s", len(sgf_files), local_dir)

    for sgf_path in sgf_files:
        # Extract local number from filename
        stem = sgf_path.stem
        try:
            local_n = int(stem.lstrip("0") or "0")
        except ValueError:
            # Try extracting from problem_NNNN_pN pattern
            import re
            m = re.match(r"problem_(\d+)_p\d+", stem)
            if m:
                local_n = int(m.group(1))
            else:
                logger.warning("Cannot parse local number from: %s", sgf_path.name)
                continue

        content, _ = read_sgf_file(sgf_path)
        try:
            tree = parse_sgf(content)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", sgf_path.name, e)
            continue

        black, white = _extract_stones(tree)
        if not black and not white:
            continue

        c_hash, c_transform = canonical_position_hash(black, white, tree.board_size)

        entry = LocalEntry(
            local_n=local_n,
            filename=sgf_path.name,
            canonical_hash=c_hash,
            transform_to_canonical=asdict(c_transform),
        )
        all_entries.append(entry)
        hash_index.setdefault(c_hash, []).append(entry)

    logger.info("Built local hash index: %d unique hashes from %d files",
                len(hash_index), len(all_entries))
    return hash_index, all_entries


# --- Subset matching for boundary stones ---

# D4 group: 4 rotations x 2 reflections = 8 transforms
_D4_TRANSFORMS = [
    PositionTransform(rotation=r, reflect=ref)
    for r in (0, 90, 180, 270)
    for ref in (False, True)
]


def _try_subset_match(
    local_black: list[Point],
    local_white: list[Point],
    senseis_black: list[Point],
    senseis_white: list[Point],
    board_size: int,
) -> tuple[PositionTransform | None, str]:
    """Try to match positions where one is a subset of the other.

    Sensei's diagrams often include extra boundary stones for context.
    Checks if local stones are a subset of Sensei's across all D4 transforms.

    Returns (transform, match_type) or (None, "") if no match.
    The transform maps Sensei's coordinates to local space.
    """
    local_b_set = {p.to_sgf() for p in local_black}
    local_w_set = {p.to_sgf() for p in local_white}

    for t in _D4_TRANSFORMS:
        # Transform Sensei's stones to candidate local space
        s_b_transformed = {transform_point(p, board_size, t).to_sgf() for p in senseis_black}
        s_w_transformed = {transform_point(p, board_size, t).to_sgf() for p in senseis_white}

        # Check if local is a subset of transformed Sensei's
        if local_b_set.issubset(s_b_transformed) and local_w_set.issubset(s_w_transformed):
            match_type = "subset_exact" if t.is_identity else "subset_d4"
            return t, match_type

    return None, ""


# --- Step 4: Position match ---

def match_positions(
    senseis_hashes: dict[str, list[SenseisEntry]],
    local_hashes: dict[str, list[LocalEntry]],
    all_local: list[LocalEntry],
    all_senseis: dict[int, SenseisEntry],
    config: SenseisConfig,
) -> PositionMapping:
    """Match local files to Sensei's problems using canonical position hashes."""
    mapping = PositionMapping()

    matched_local: set[int] = set()
    matched_senseis: set[int] = set()

    # Find matches via canonical hash
    for c_hash, local_entries in local_hashes.items():
        if c_hash not in senseis_hashes:
            continue

        senseis_entries = senseis_hashes[c_hash]

        for local_e in local_entries:
            for senseis_e in senseis_entries:
                if local_e.local_n in matched_local:
                    continue
                if senseis_e.global_n in matched_senseis:
                    continue

                # Determine exact transform between positions
                local_path = (_PROJECT_ROOT / config.local_dir /
                              local_e.filename)
                content, _ = read_sgf_file(local_path)
                local_tree = parse_sgf(content)
                local_black, local_white = _extract_stones(local_tree)

                # Load Sensei's diagram position
                page_file = config.page_cache_dir() / f"{senseis_e.global_n:04d}.json"
                with open(page_file, encoding="utf-8") as f:
                    page_data = json.load(f)
                diagram_url = page_data.get("diagram_sgf_url", "")
                diagram_filename = diagram_url.replace("/", "_")
                diagram_file = config.diagram_cache_dir() / diagram_filename
                sgf_content = diagram_file.read_text(encoding="utf-8")
                senseis_tree = parse_sgf(sgf_content)
                senseis_black, senseis_white = _extract_stones(senseis_tree)

                transform = find_transform(
                    senseis_black, senseis_white,
                    local_black, local_white,
                    config.board_size,
                )

                if transform is None:
                    # Canonical hash matched but find_transform failed — shouldn't happen
                    logger.warning(
                        "Hash match but transform failed: local %d ↔ senseis %d",
                        local_e.local_n, senseis_e.global_n,
                    )
                    continue

                match_type = "exact" if transform.is_identity else "d4_symmetry"

                mapping.mappings.append(MappingEntry(
                    local_file=local_e.filename,
                    local_n=local_e.local_n,
                    senseis_global=senseis_e.global_n,
                    page_name=senseis_e.page_name,
                    section_number=senseis_e.section_number,
                    section_name=senseis_e.section_name,
                    section_pos=senseis_e.section_problem_number,
                    transform=asdict(transform),
                    match_type=match_type,
                ))

                matched_local.add(local_e.local_n)
                matched_senseis.add(senseis_e.global_n)
                break  # Move to next local entry

    # --- Pass 2: Subset matching for unmatched N↔N pairs ---
    # Sensei's diagrams often include extra boundary stones for context.
    # Check if local stones are a subset of Sensei's (or vice versa)
    # using the sequential N↔N assumption.
    subset_matched = 0
    for local_e in all_local:
        if local_e.local_n in matched_local:
            continue
        n = local_e.local_n
        if n not in all_senseis:
            continue
        senseis_e = all_senseis[n]
        if senseis_e.global_n in matched_senseis:
            continue

        # Load both positions
        local_path = _PROJECT_ROOT / config.local_dir / local_e.filename
        if not local_path.exists():
            continue
        content, _ = read_sgf_file(local_path)
        try:
            local_tree = parse_sgf(content)
        except Exception:
            continue
        local_black, local_white = _extract_stones(local_tree)

        page_file = config.page_cache_dir() / f"{n:04d}.json"
        if not page_file.exists():
            continue
        with open(page_file, encoding="utf-8") as f:
            page_data = json.load(f)
        diagram_url = page_data.get("diagram_sgf_url", "")
        if not diagram_url:
            continue
        diagram_filename = diagram_url.replace("/", "_")
        diagram_file = config.diagram_cache_dir() / diagram_filename
        if not diagram_file.exists():
            continue
        sgf_content = diagram_file.read_text(encoding="utf-8")
        try:
            senseis_tree = parse_sgf(sgf_content)
        except Exception:
            continue
        senseis_black, senseis_white = _extract_stones(senseis_tree)

        # Try subset matching across all 8 D4 transforms
        transform, match_type = _try_subset_match(
            local_black, local_white, senseis_black, senseis_white,
            config.board_size,
        )
        if transform is not None:
            mapping.mappings.append(MappingEntry(
                local_file=local_e.filename,
                local_n=local_e.local_n,
                senseis_global=senseis_e.global_n,
                page_name=senseis_e.page_name,
                section_number=senseis_e.section_number,
                section_name=senseis_e.section_name,
                section_pos=senseis_e.section_problem_number,
                transform=asdict(transform),
                match_type=match_type,
            ))
            matched_local.add(local_e.local_n)
            matched_senseis.add(senseis_e.global_n)
            subset_matched += 1

    if subset_matched:
        logger.info("Subset matching (N=N): %d additional matches", subset_matched)

    # --- Pass 3: Brute-force subset matching across all remaining pairs ---
    # For unmatched local files, try matching against ALL unmatched Sensei entries.
    # This handles cases where local numbering diverges from Sensei's section order.
    remaining_local = [e for e in all_local if e.local_n not in matched_local]
    remaining_senseis = [
        (n, e) for n, e in sorted(all_senseis.items())
        if n not in matched_senseis and e.canonical_hash
    ]

    if remaining_local and remaining_senseis:
        logger.info(
            "Brute-force subset matching: %d local x %d senseis = %d pairs",
            len(remaining_local), len(remaining_senseis),
            len(remaining_local) * len(remaining_senseis),
        )

        # Pre-load all remaining Sensei positions
        senseis_positions: dict[int, tuple[list[Point], list[Point]]] = {}
        for n, entry in remaining_senseis:
            page_file = config.page_cache_dir() / f"{n:04d}.json"
            if not page_file.exists():
                continue
            with open(page_file, encoding="utf-8") as f:
                page_data = json.load(f)
            diagram_url = page_data.get("diagram_sgf_url", "")
            if not diagram_url:
                continue
            diagram_file = config.diagram_cache_dir() / diagram_url.replace("/", "_")
            if not diagram_file.exists():
                continue
            try:
                stree = parse_sgf(diagram_file.read_text(encoding="utf-8"))
                senseis_positions[n] = _extract_stones(stree)
            except Exception:
                continue

        brute_matched = 0
        for local_e in remaining_local:
            if local_e.local_n in matched_local:
                continue
            local_path = _PROJECT_ROOT / config.local_dir / local_e.filename
            if not local_path.exists():
                continue
            content, _ = read_sgf_file(local_path)
            try:
                ltree = parse_sgf(content)
            except Exception:
                continue
            local_black, local_white = _extract_stones(ltree)
            if not local_black and not local_white:
                continue

            for sn, entry in remaining_senseis:
                if sn in matched_senseis:
                    continue
                if sn not in senseis_positions:
                    continue
                s_black, s_white = senseis_positions[sn]

                # Try exact D4 match first
                transform = find_transform(
                    s_black, s_white, local_black, local_white,
                    config.board_size,
                )
                if transform is not None:
                    mt = "cross_exact" if transform.is_identity else "cross_d4"
                else:
                    # Try subset match
                    transform, mt = _try_subset_match(
                        local_black, local_white, s_black, s_white,
                        config.board_size,
                    )
                    if transform is not None:
                        mt = "cross_subset" if transform.is_identity else "cross_subset_d4"

                if transform is not None:
                    se = all_senseis[sn]
                    mapping.mappings.append(MappingEntry(
                        local_file=local_e.filename,
                        local_n=local_e.local_n,
                        senseis_global=sn,
                        page_name=se.page_name,
                        section_number=se.section_number,
                        section_name=se.section_name,
                        section_pos=se.section_problem_number,
                        transform=asdict(transform),
                        match_type=mt,
                    ))
                    matched_local.add(local_e.local_n)
                    matched_senseis.add(sn)
                    brute_matched += 1
                    break

        if brute_matched:
            logger.info("Brute-force matching: %d additional matches", brute_matched)

    # Collect unmatched
    for local_e in all_local:
        if local_e.local_n not in matched_local:
            mapping.unmatched_local.append({
                "local_n": local_e.local_n,
                "filename": local_e.filename,
                "canonical_hash": local_e.canonical_hash,
            })

    for n, entry in sorted(all_senseis.items()):
        if n not in matched_senseis:
            mapping.unmatched_senseis.append({
                "global_n": n,
                "page_name": entry.page_name,
                "section_number": entry.section_number,
                "section_name": entry.section_name,
                "section_pos": entry.section_problem_number,
            })

    # Stats
    mapping.stats = {
        "total_local": len(all_local),
        "total_senseis": len(all_senseis),
        "matched": len(mapping.mappings),
        "exact_matches": sum(1 for m in mapping.mappings if m.match_type == "exact"),
        "d4_matches": sum(1 for m in mapping.mappings if m.match_type == "d4_symmetry"),
        "subset_exact": sum(1 for m in mapping.mappings if m.match_type == "subset_exact"),
        "subset_d4": sum(1 for m in mapping.mappings if m.match_type == "subset_d4"),
        "cross_exact": sum(1 for m in mapping.mappings if m.match_type == "cross_exact"),
        "cross_d4": sum(1 for m in mapping.mappings if m.match_type == "cross_d4"),
        "cross_subset": sum(1 for m in mapping.mappings if m.match_type == "cross_subset"),
        "cross_subset_d4": sum(1 for m in mapping.mappings if m.match_type == "cross_subset_d4"),
        "unmatched_local": len(mapping.unmatched_local),
        "unmatched_senseis": len(mapping.unmatched_senseis),
    }

    return mapping


# --- Serialization ---

def save_mapping(mapping: PositionMapping, output_path: Path) -> None:
    """Save position mapping to JSON."""
    data = {
        "mappings": [asdict(m) for m in mapping.mappings],
        "unmatched_local": mapping.unmatched_local,
        "unmatched_senseis": mapping.unmatched_senseis,
        "stats": mapping.stats,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved position mapping -> %s", output_path)


def save_hash_cache(
    senseis_entries: dict[int, SenseisEntry],
    local_entries: list[LocalEntry],
    working_dir: Path,
) -> None:
    """Cache hash indexes for quick re-matching."""
    senseis_data = {
        str(n): {
            "page_name": e.page_name,
            "section_number": e.section_number,
            "section_name": e.section_name,
            "section_pos": e.section_problem_number,
            "canonical_hash": e.canonical_hash,
        }
        for n, e in sorted(senseis_entries.items())
        if e.canonical_hash
    }
    with open(working_dir / "_senseis_hashes.json", "w", encoding="utf-8") as f:
        json.dump(senseis_data, f, indent=2, ensure_ascii=False)

    local_data = {
        str(e.local_n): {
            "filename": e.filename,
            "canonical_hash": e.canonical_hash,
        }
        for e in local_entries
        if e.canonical_hash
    }
    with open(working_dir / "_local_hashes.json", "w", encoding="utf-8") as f:
        json.dump(local_data, f, indent=2, ensure_ascii=False)

    logger.info("Saved hash caches: %d senseis, %d local",
                len(senseis_data), len(local_data))


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="build_gokyo_index",
        description="Build Gokyo Shumyo index with position matching.",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config JSON (defaults to gokyo_shumyo_config.json)",
    )
    parser.add_argument(
        "--index-only", action="store_true",
        help="Only build index cache (no fetching or matching)",
    )
    parser.add_argument(
        "--match-only", action="store_true",
        help="Only run position matching from cached data (no network)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    config_path = Path(args.config) if args.config else _TOOL_DIR / "gokyo_shumyo_config.json"
    config = load_config(config_path)

    working = config.working_dir()
    working.mkdir(parents=True, exist_ok=True)

    # Step 1: Build index from sections
    logger.info("=== Step 1: Building index from sections config ===")
    entries = build_index_from_sections(config)
    save_index_cache(entries, config.index_cache_path())
    logger.info("Index: %d entries (expected %d)", len(entries), config.problem_count)

    if args.index_only:
        logger.info("Done (--index-only).")
        return

    # Step 2: Fetch all diagram SGFs
    if not args.match_only:
        logger.info("=== Step 2: Fetching diagram SGFs from Sensei's ===")
        fetch_all_diagrams(config, entries)

    # Step 3: Build position hash indexes
    logger.info("=== Step 3: Building position hash indexes ===")
    senseis_hashes = build_senseis_hashes(config, entries)
    local_hashes, all_local = build_local_hashes(config)

    # Save hash caches
    save_hash_cache(entries, all_local, config.results_dir())

    # Step 4: Position match
    logger.info("=== Step 4: Position matching ===")
    mapping = match_positions(senseis_hashes, local_hashes, all_local, entries, config)

    # Save mapping
    mapping_path = config.results_dir() / "_position_mapping.json"
    save_mapping(mapping, mapping_path)

    # Report
    logger.info("=== Position Matching Results ===")
    logger.info("  Local files:      %d", mapping.stats["total_local"])
    logger.info("  Sensei's entries:  %d", mapping.stats["total_senseis"])
    logger.info("  Matched:          %d", mapping.stats["matched"])
    logger.info("    Exact (identity): %d", mapping.stats["exact_matches"])
    logger.info("    D4 symmetry:      %d", mapping.stats["d4_matches"])
    logger.info("    Subset exact:     %d", mapping.stats["subset_exact"])
    logger.info("    Subset D4:        %d", mapping.stats["subset_d4"])
    logger.info("  Unmatched local:  %d", mapping.stats["unmatched_local"])
    logger.info("  Unmatched Sensei: %d", mapping.stats["unmatched_senseis"])

    if mapping.unmatched_local:
        logger.info("  Unmatched local files:")
        for entry in mapping.unmatched_local[:10]:
            logger.info("    %s (local #%d)", entry["filename"], entry["local_n"])
        if len(mapping.unmatched_local) > 10:
            logger.info("    ... and %d more", len(mapping.unmatched_local) - 10)

    logger.info("Done. Mapping saved to %s", mapping_path)


if __name__ == "__main__":
    main()
