"""
GoProblems Collections Explorer

Discovers collections via the GoProblems Collections API (/api/collections),
with optional per-puzzle enrichment for quality stats (stars, votes, canon,
genre) from individual puzzle detail responses (/api/v2/problems/{id}).

Outputs a JSONL file (one JSON object per line) with incremental writes.

Line 1: metadata header (updated at end with final counts)
Line 2+: one discovered collection per line

Usage:
    # API-only discovery (3 requests, fast)
    python -m tools.go_problems.explore_collections -v

    # Hybrid: API discovery + enrichment from downloaded puzzles
    python -m tools.go_problems.explore_collections \
        --enrich-ids external-sources/goproblems/sgf-index.txt \
        --enrich-sample 500 -v
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.core.paths import rel_path
from tools.go_problems.client import GoProblemsClient
from tools.go_problems.config import (
    DEFAULT_PUZZLE_DELAY,
    get_output_dir,
    get_project_root,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_REPORTS_DIR = "reports"
CHECKPOINT_SAVE_INTERVAL = 50  # Save checkpoint every N puzzles
DEFAULT_API_DELAY = 1.0  # Delay between collections API requests


# ============================================================================
# Data Model
# ============================================================================

@dataclass
class DiscoveredCollection:
    """Accumulated stats for a discovered collection."""

    id: int
    name: str
    # --- Puzzle-level stats (from puzzle scanning / enrichment) ---
    puzzle_count: int = 0
    puzzle_ids: list[int] = field(default_factory=list)
    total_stars: float = 0.0
    total_votes: int = 0
    rated_puzzle_count: int = 0
    canon_count: int = 0
    genre_counts: dict[str, int] = field(default_factory=dict)
    rank_sum: int = 0
    ranked_puzzle_count: int = 0
    # --- Collections API fields ---
    group: str = ""              # "Style" or "Collection"
    description: str = ""
    author_name: str = ""
    author_id: int = 0
    created_at: str = ""
    enriched: bool = False       # True when puzzle-level stats populated

    def to_jsonl_record(self) -> dict[str, Any]:
        """Convert to JSONL-compatible dict matching downstream format."""
        avg_stars = (
            self.total_stars / self.rated_puzzle_count
            if self.rated_puzzle_count > 0
            else 0.0
        )
        avg_votes = (
            self.total_votes / self.rated_puzzle_count
            if self.rated_puzzle_count > 0
            else 0.0
        )
        avg_rank = (
            self.rank_sum / self.ranked_puzzle_count
            if self.ranked_puzzle_count > 0
            else 0.0
        )
        canon_ratio = (
            self.canon_count / self.puzzle_count
            if self.puzzle_count > 0
            else 0.0
        )

        return {
            "type": "collection",
            "id": self.id,
            "name": self.name,
            "puzzle_count": self.puzzle_count,
            "puzzles": self.puzzle_ids,
            "group": self.group,
            "description": self.description,
            "author": self.author_name,
            "enriched": self.enriched,
            "stats": {
                "puzzle_count": self.puzzle_count,
                "avg_stars": round(avg_stars, 4),
                "avg_votes": round(avg_votes, 2),
                "rated_puzzle_count": self.rated_puzzle_count,
                "canon_count": self.canon_count,
                "canon_ratio": round(canon_ratio, 4),
                "avg_rank": round(avg_rank, 2),
                "ranked_puzzle_count": self.ranked_puzzle_count,
            },
            "genre_distribution": dict(
                sorted(self.genre_counts.items(), key=lambda x: -x[1])
            ),
        }


# ============================================================================
# Accumulation Logic
# ============================================================================

def accumulate_puzzle(
    collections_map: dict[int, DiscoveredCollection],
    puzzle_data: dict[str, Any],
) -> None:
    """Extract collections from a puzzle response and update the map.

    Args:
        collections_map: Mutable map of collection_id -> DiscoveredCollection
        puzzle_data: Parsed puzzle detail response from /api/v2/problems/{id}
    """
    puzzle_id = puzzle_data.get("id")
    if puzzle_id is None:
        return

    collections = puzzle_data.get("collections")
    if not collections:
        return

    # Extract puzzle-level metadata
    rating = puzzle_data.get("rating")
    stars = rating.get("stars", 0.0) if isinstance(rating, dict) else 0.0
    votes = rating.get("votes", 0) if isinstance(rating, dict) else 0
    is_canon = puzzle_data.get("isCanon", False)
    genre = puzzle_data.get("genre")
    rank_info = puzzle_data.get("rank")
    rank_value = rank_info.get("value") if isinstance(rank_info, dict) else None

    for coll in collections:
        coll_id = coll.get("id")
        coll_name = coll.get("name", "")
        if coll_id is None:
            continue

        if coll_id not in collections_map:
            collections_map[coll_id] = DiscoveredCollection(
                id=coll_id, name=coll_name,
            )

        dc = collections_map[coll_id]
        dc.puzzle_count += 1
        dc.puzzle_ids.append(puzzle_id)

        if stars > 0 or votes > 0:
            dc.total_stars += stars
            dc.total_votes += votes
            dc.rated_puzzle_count += 1

        if is_canon:
            dc.canon_count += 1

        if genre:
            dc.genre_counts[genre] = dc.genre_counts.get(genre, 0) + 1

        if rank_value is not None and rank_value > 0:
            dc.rank_sum += rank_value
            dc.ranked_puzzle_count += 1


# ============================================================================
# API-Based Discovery
# ============================================================================

def discover_collections_via_api(
    client: GoProblemsClient,
    delay: float = DEFAULT_API_DELAY,
) -> dict[int, DiscoveredCollection]:
    """Discover all collections via the Collections API.

    Makes at most ceil(totalRecords / 100) requests (currently 3).
    Uses /api/collections endpoint with offset/limit pagination.

    Args:
        client: GoProblems API client.
        delay: Delay between paginated requests.

    Returns:
        Map of collection_id -> DiscoveredCollection with API-level fields
        populated (group, description, author_name, author_id, created_at,
        puzzle_count from numberOfProblems). Enrichment fields remain at
        defaults (enriched=False).
    """
    collections_map: dict[int, DiscoveredCollection] = {}
    offset = 0
    limit = 100
    total_records: int | None = None

    while True:
        logger.info(f"Fetching collections API: offset={offset}, limit={limit}")

        try:
            data = client.get_collections(offset=offset, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch collections at offset={offset}: {e}")
            break

        if total_records is None:
            total_records = data.get("totalRecords", 0)
            logger.info(f"Total collections available: {total_records}")

        entries = data.get("entries", [])
        if not entries:
            break

        for entry in entries:
            coll_id = entry.get("id")
            if coll_id is None:
                continue

            author_info = entry.get("author") or {}

            dc = DiscoveredCollection(
                id=coll_id,
                name=entry.get("name", ""),
                puzzle_count=entry.get("numberOfProblems", 0),
                group=entry.get("group", ""),
                description=entry.get("description", ""),
                author_name=author_info.get("name", "") if isinstance(author_info, dict) else "",
                author_id=author_info.get("id", 0) if isinstance(author_info, dict) else 0,
                created_at=entry.get("createdAt", ""),
                enriched=False,
            )
            collections_map[coll_id] = dc

        offset += limit
        if total_records is not None and offset >= total_records:
            break

        time.sleep(delay)

    logger.info(
        f"API discovery complete: {len(collections_map)} collections found"
    )
    return collections_map


# ============================================================================
# Puzzle-Level Enrichment
# ============================================================================

def enrich_from_puzzles(
    collections_map: dict[int, DiscoveredCollection],
    client: GoProblemsClient,
    puzzle_ids: list[int],
    sample: int | None = None,
    delay: float = DEFAULT_PUZZLE_DELAY,
) -> int:
    """Enrich API-discovered collections with per-puzzle statistics.

    Fetches individual puzzle details and calls accumulate_puzzle() to add
    stars, votes, canon, genre, and rank data. Sets enriched=True on each
    collection that receives at least one puzzle.

    puzzle_count from the API (numberOfProblems) is preserved as the
    authoritative count. The accumulated stats from scanning reflect only
    the sampled puzzles, not the full collection.

    Args:
        collections_map: Map of collection_id -> DiscoveredCollection
            (modified in place).
        client: GoProblems API client.
        puzzle_ids: List of puzzle IDs to scan for enrichment.
        sample: If set, only scan first N puzzles.
        delay: Delay between API requests.

    Returns:
        Number of puzzles successfully scanned.
    """
    ids_to_scan = puzzle_ids[:sample] if sample else puzzle_ids
    total = len(ids_to_scan)

    # Save API puzzle_count as the canonical number before enrichment
    api_puzzle_counts: dict[int, int] = {
        cid: dc.puzzle_count for cid, dc in collections_map.items()
    }

    # Reset accumulation counters (keep API-level fields)
    for dc in collections_map.values():
        dc.puzzle_count = 0
        dc.puzzle_ids = []
        dc.total_stars = 0.0
        dc.total_votes = 0
        dc.rated_puzzle_count = 0
        dc.canon_count = 0
        dc.genre_counts = {}
        dc.rank_sum = 0
        dc.ranked_puzzle_count = 0

    logger.info(f"Enriching from {total} puzzles...")
    puzzles_scanned = 0

    for i, puzzle_id in enumerate(ids_to_scan):
        if i > 0:
            time.sleep(delay)

        try:
            puzzle_data = client.get_puzzle(puzzle_id)
        except Exception as e:
            logger.warning(f"Failed to fetch puzzle {puzzle_id}: {e}")
            continue

        if puzzle_data is None:
            logger.debug(f"Puzzle {puzzle_id} not found (404)")
            continue

        accumulate_puzzle(collections_map, puzzle_data)
        puzzles_scanned += 1

        if puzzles_scanned % 10 == 0:
            enriched_so_far = sum(
                1 for dc in collections_map.values()
                if dc.rated_puzzle_count > 0 or dc.puzzle_ids
            )
            logger.info(
                f"Enrichment progress: {i + 1}/{total} puzzles scanned, "
                f"{enriched_so_far} collections enriched"
            )

    # Restore API puzzle_count as authoritative, mark enriched
    for cid, dc in collections_map.items():
        if dc.rated_puzzle_count > 0 or dc.puzzle_ids:
            dc.enriched = True
        # Use API count as the canonical puzzle_count
        dc.puzzle_count = api_puzzle_counts.get(cid, dc.puzzle_count)

    enriched_count = sum(1 for dc in collections_map.values() if dc.enriched)
    logger.info(
        f"Enrichment complete: {puzzles_scanned} puzzles scanned, "
        f"{enriched_count}/{len(collections_map)} collections enriched"
    )
    return puzzles_scanned


# ============================================================================
# Checkpoint
# ============================================================================

_EXPLORE_CHECKPOINT_FILE = ".explore-checkpoint.json"


def _save_explore_checkpoint(
    output_dir: Path,
    last_processed_index: int,
    collections_map: dict[int, DiscoveredCollection],
    puzzle_ids_source: str,
    puzzles_scanned: int,
) -> None:
    """Save exploration checkpoint."""
    checkpoint = {
        "version": "1.0",
        "last_processed_index": last_processed_index,
        "puzzles_scanned": puzzles_scanned,
        "puzzle_ids_source": puzzle_ids_source,
        "collections_count": len(collections_map),
        "saved_at": datetime.now(UTC).isoformat(),
        "collections": {
            str(cid): asdict(dc)
            for cid, dc in collections_map.items()
        },
    }

    path = output_dir / _EXPLORE_CHECKPOINT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")
    logger.debug(f"Saved checkpoint: {puzzles_scanned} puzzles scanned, "
                 f"{len(collections_map)} collections found")


def _load_explore_checkpoint(
    output_dir: Path,
) -> tuple[int, dict[int, DiscoveredCollection], int] | None:
    """Load exploration checkpoint.

    Returns:
        Tuple of (last_processed_index, collections_map, puzzles_scanned),
        or None if no checkpoint exists.
    """
    path = output_dir / _EXPLORE_CHECKPOINT_FILE
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None

    collections_map: dict[int, DiscoveredCollection] = {}
    for cid_str, dc_data in data.get("collections", {}).items():
        cid = int(cid_str)
        collections_map[cid] = DiscoveredCollection(
            id=dc_data["id"],
            name=dc_data["name"],
            puzzle_count=dc_data.get("puzzle_count", 0),
            puzzle_ids=dc_data.get("puzzle_ids", []),
            total_stars=dc_data.get("total_stars", 0.0),
            total_votes=dc_data.get("total_votes", 0),
            rated_puzzle_count=dc_data.get("rated_puzzle_count", 0),
            canon_count=dc_data.get("canon_count", 0),
            genre_counts=dc_data.get("genre_counts", {}),
            rank_sum=dc_data.get("rank_sum", 0),
            ranked_puzzle_count=dc_data.get("ranked_puzzle_count", 0),
            group=dc_data.get("group", ""),
            description=dc_data.get("description", ""),
            author_name=dc_data.get("author_name", ""),
            author_id=dc_data.get("author_id", 0),
            created_at=dc_data.get("created_at", ""),
            enriched=dc_data.get("enriched", False),
        )

    last_idx = data.get("last_processed_index", -1)
    puzzles_scanned = data.get("puzzles_scanned", 0)

    logger.info(f"Loaded checkpoint: index={last_idx}, "
                f"{puzzles_scanned} puzzles scanned, "
                f"{len(collections_map)} collections found")
    return last_idx, collections_map, puzzles_scanned


def _clear_explore_checkpoint(output_dir: Path) -> None:
    """Remove exploration checkpoint file."""
    path = output_dir / _EXPLORE_CHECKPOINT_FILE
    if path.exists():
        path.unlink()
        logger.info("Cleared exploration checkpoint")


# ============================================================================
# JSONL Writer
# ============================================================================

def write_collections_jsonl(
    output_path: Path,
    collections_map: dict[int, DiscoveredCollection],
    puzzles_scanned: int,
    puzzle_ids_source: str,
    discovery_method: str = "api",
) -> None:
    """Write discovered collections to JSONL file.

    Args:
        output_path: Output JSONL file path.
        collections_map: Map of collection_id -> DiscoveredCollection.
        puzzles_scanned: Total puzzles scanned for enrichment.
        puzzle_ids_source: Description of puzzle ID source.
        discovery_method: "api", "hybrid", or "puzzle_scan".
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by puzzle_count descending for readability
    sorted_collections = sorted(
        collections_map.values(),
        key=lambda dc: dc.puzzle_count,
        reverse=True,
    )

    enriched_count = sum(1 for dc in sorted_collections if dc.enriched)

    metadata = {
        "type": "metadata",
        "source": "goproblems.com",
        "discovery_method": discovery_method,
        "api_base": "https://www.goproblems.com/api",
        "extracted_at": datetime.now(UTC).isoformat(),
        "puzzle_ids_source": puzzle_ids_source,
        "puzzles_scanned": puzzles_scanned,
        "total_collections": len(sorted_collections),
        "enriched_collections": enriched_count,
        "total_puzzles_in_collections": sum(
            dc.puzzle_count for dc in sorted_collections
        ),
        "status": "completed",
    }

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False))
        f.write("\n")
        for dc in sorted_collections:
            f.write(json.dumps(dc.to_jsonl_record(), ensure_ascii=False))
            f.write("\n")

    logger.info(
        f"Wrote {len(sorted_collections)} collections to {rel_path(output_path)}"
    )


# ============================================================================
# Puzzle ID Sources
# ============================================================================

def load_puzzle_ids_from_file(path: Path) -> list[int]:
    """Load puzzle IDs from a file (one per line, or sgf-index.txt format).

    Supports:
    - Plain text with one integer per line
    - sgf-index.txt format: `batch-NNNN/12345.sgf` -> extract 12345

    Args:
        path: Path to ID file.

    Returns:
        List of puzzle IDs (deduplicated, sorted).
    """
    ids: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Try sgf-index.txt format: batch-NNNN/12345.sgf
        if "/" in line and line.endswith(".sgf"):
            filename = line.rsplit("/", 1)[-1]
            try:
                ids.add(int(filename.replace(".sgf", "")))
            except ValueError:
                continue
        else:
            try:
                ids.add(int(line))
            except ValueError:
                continue

    return sorted(ids)


def discover_puzzle_ids_via_listing(
    client: GoProblemsClient,
    max_pages: int | None = None,
    delay: float = DEFAULT_PUZZLE_DELAY,
) -> list[int]:
    """Discover puzzle IDs by paginating the list endpoint.

    Args:
        client: GoProblems API client.
        max_pages: Maximum pages to fetch (None = all).
        delay: Delay between requests.

    Returns:
        List of discovered puzzle IDs.
    """
    all_ids: list[int] = []
    page = 1

    while True:
        if max_pages and page > max_pages:
            break

        try:
            data = client.get_puzzles_page(page=page, page_size=50)
        except Exception as e:
            logger.warning(f"Failed to fetch page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            puzzle_id = item.get("id")
            if puzzle_id is not None:
                all_ids.append(puzzle_id)

        total = data.get("count", 0)
        logger.info(
            f"Page {page}: got {len(results)} IDs "
            f"(total so far: {len(all_ids)}/{total})"
        )

        if not data.get("next"):
            break

        page += 1
        time.sleep(delay)

    return all_ids


# ============================================================================
# Legacy Puzzle-Scan Discovery
# ============================================================================

def discover_collections(
    client: GoProblemsClient,
    puzzle_ids: list[int],
    output_dir: Path,
    delay: float = DEFAULT_PUZZLE_DELAY,
    sample: int | None = None,
    resume: bool = False,
    puzzle_ids_source: str = "unknown",
) -> dict[int, DiscoveredCollection]:
    """Scan puzzle details to discover and accumulate collection data.

    Legacy function: prefer discover_collections_via_api() for discovery
    and enrich_from_puzzles() for enrichment.

    Args:
        client: GoProblems API client.
        puzzle_ids: List of puzzle IDs to scan.
        output_dir: Directory for checkpoint files.
        delay: Delay between requests.
        sample: If set, only scan first N puzzles.
        resume: Whether to resume from checkpoint.
        puzzle_ids_source: Description of ID source for metadata.

    Returns:
        Map of collection_id -> DiscoveredCollection.
    """
    collections_map: dict[int, DiscoveredCollection] = {}
    start_index = 0
    puzzles_scanned = 0

    # Resume from checkpoint
    if resume:
        checkpoint = _load_explore_checkpoint(output_dir)
        if checkpoint:
            start_index, collections_map, puzzles_scanned = checkpoint
            start_index += 1  # Start after last processed

    # Apply sample limit
    ids_to_scan = puzzle_ids
    if sample:
        ids_to_scan = puzzle_ids[:sample]

    total = len(ids_to_scan)
    logger.info(f"Scanning {total} puzzles (starting from index {start_index})")

    for i in range(start_index, total):
        puzzle_id = ids_to_scan[i]

        if i > start_index:
            time.sleep(delay)

        try:
            puzzle_data = client.get_puzzle(puzzle_id)
        except Exception as e:
            logger.warning(f"Failed to fetch puzzle {puzzle_id}: {e}")
            continue

        if puzzle_data is None:
            logger.debug(f"Puzzle {puzzle_id} not found (404)")
            continue

        accumulate_puzzle(collections_map, puzzle_data)
        puzzles_scanned += 1

        if puzzles_scanned % 10 == 0:
            colls_with_puzzles = sum(
                1 for dc in collections_map.values() if dc.puzzle_count > 0
            )
            logger.info(
                f"Progress: {i + 1}/{total} puzzles scanned, "
                f"{colls_with_puzzles} collections discovered"
            )

        # Save checkpoint periodically
        if puzzles_scanned % CHECKPOINT_SAVE_INTERVAL == 0:
            _save_explore_checkpoint(
                output_dir, i, collections_map, puzzle_ids_source, puzzles_scanned,
            )

    # Final checkpoint
    _save_explore_checkpoint(
        output_dir, total - 1, collections_map, puzzle_ids_source, puzzles_scanned,
    )

    logger.info(
        f"Discovery complete: {puzzles_scanned} puzzles scanned, "
        f"{len(collections_map)} collections found"
    )
    return collections_map


# ============================================================================
# CLI
# ============================================================================

def _default_output_path() -> Path:
    """Generate timestamped output path in reports/ directory."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = get_output_dir()
    return output_dir / DEFAULT_REPORTS_DIR / f"{timestamp}-collections.jsonl"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Discover GoProblems collections via API, "
            "with optional puzzle-level enrichment"
        ),
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output JSONL file path (default: auto-timestamped in reports/)",
    )
    parser.add_argument(
        "--enrich-ids",
        type=Path,
        default=None,
        help=(
            "File with puzzle IDs for enrichment (sgf-index.txt format). "
            "Scans these puzzles to add per-puzzle stats (stars, votes, "
            "canon, genre) to API-discovered collections."
        ),
    )
    parser.add_argument(
        "--enrich-sample",
        type=int,
        default=None,
        help="When enriching, scan only the first N puzzles from the ID list",
    )
    parser.add_argument(
        "--input-ids",
        type=Path,
        default=None,
        help="[Deprecated: use --enrich-ids] File with puzzle IDs",
    )
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="[Deprecated: use --enrich-sample] Scan only the first N puzzles",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_PUZZLE_DELAY,
        help=f"Delay between enrichment API requests (default: {DEFAULT_PUZZLE_DELAY}s)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_root = get_project_root()

    # Handle deprecated --input-ids
    enrich_ids_path = args.enrich_ids or args.input_ids
    if args.input_ids and not args.enrich_ids:
        logger.warning("--input-ids is deprecated, use --enrich-ids instead")

    # Handle deprecated --sample
    enrich_sample = args.enrich_sample or args.sample
    if args.sample and not args.enrich_sample:
        logger.warning("--sample is deprecated, use --enrich-sample instead")

    logger.info("GoProblems Collections Explorer")
    logger.info("=" * 40)

    # Step 1: API-based discovery (always, ~3 requests)
    logger.info("Step 1: Discovering collections via API...")
    with GoProblemsClient() as client:
        collections_map = discover_collections_via_api(
            client, delay=DEFAULT_API_DELAY,
        )

    logger.info(f"Found {len(collections_map)} collections from API")
    logger.info("")

    # Step 2: Optional enrichment
    puzzles_scanned = 0
    discovery_method = "api"
    puzzle_ids_source = "collections_api"

    if enrich_ids_path:
        input_path = enrich_ids_path
        if not input_path.is_absolute():
            input_path = project_root / input_path
        puzzle_ids = load_puzzle_ids_from_file(input_path)
        puzzle_ids_source = f"file:{rel_path(input_path)}"

        logger.info(
            f"Step 2: Enriching from {len(puzzle_ids)} puzzles "
            f"(sample: {enrich_sample or 'all'})..."
        )

        with GoProblemsClient() as client:
            puzzles_scanned = enrich_from_puzzles(
                collections_map=collections_map,
                client=client,
                puzzle_ids=puzzle_ids,
                sample=enrich_sample,
                delay=args.delay,
            )
        discovery_method = "hybrid"
    else:
        logger.info("Step 2: Skipped (no --enrich-ids provided)")

    logger.info("")

    # Step 3: Write output
    output_path = args.output or _default_output_path()
    if not output_path.is_absolute():
        output_path = project_root / output_path

    logger.info(f"Step 3: Writing output to {rel_path(output_path)}")

    write_collections_jsonl(
        output_path, collections_map,
        puzzles_scanned=puzzles_scanned,
        puzzle_ids_source=puzzle_ids_source,
        discovery_method=discovery_method,
    )

    logger.info("")
    logger.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
