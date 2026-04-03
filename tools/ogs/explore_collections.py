"""
OGS Collections Explorer

Fetches metadata about OGS puzzle collections and their puzzles.
Outputs a JSONL file (one JSON object per line) with incremental writes.

Line 1: metadata header (updated at end with final counts)
Line 2+: one collection per line (written immediately after fetch)

Usage:
    python -m tools.ogs.explore_collections --sample 5
    python -m tools.ogs.explore_collections --min-puzzles 10
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from tools.core.paths import rel_path
from tools.ogs.config import DEFAULT_OUTPUT_DIR, get_project_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

OGS_API_BASE = "https://online-go.com/api/v1"
OGS_WEB_BASE = "https://online-go.com"
DEFAULT_PAGE_SIZE = 50
REQUEST_DELAY_SECONDS = 0.5  # Be nice to OGS servers
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class CollectionDifficulty:
    """Difficulty range for a collection."""
    min_rank: int  # OGS rank (lower = easier, 0 = unrated)
    max_rank: int
    yengo_level: str = ""  # Mapped to our level system

    def __post_init__(self):
        # Map OGS rank to Yengo level
        # OGS ranks: 0-9 = very beginner, 10-15 = DDK, 16-20 = SDK, 21-30 = dan
        if self.max_rank == 0:
            self.yengo_level = "unknown"
        elif self.max_rank <= 10:
            self.yengo_level = "novice"
        elif self.max_rank <= 15:
            self.yengo_level = "beginner"
        elif self.max_rank <= 18:
            self.yengo_level = "elementary"
        elif self.max_rank <= 20:
            self.yengo_level = "intermediate"
        elif self.max_rank <= 25:
            self.yengo_level = "upper-intermediate"
        elif self.max_rank <= 30:
            self.yengo_level = "advanced"
        else:
            self.yengo_level = "dan"


@dataclass
class CollectionStats:
    """Statistics for a collection."""
    puzzle_count: int
    view_count: int
    solved_count: int
    attempt_count: int
    rating: float
    rating_count: int


@dataclass
class Collection:
    """A puzzle collection from OGS."""
    id: int
    name: str
    url: str
    created: str
    difficulty: CollectionDifficulty
    stats: CollectionStats
    puzzles: list[int] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Collection:
        """Create Collection from OGS API response."""
        return cls(
            id=data["id"],
            name=data["name"],
            url=f"{OGS_WEB_BASE}/puzzle/{data['id']}",
            created=data.get("created", ""),
            difficulty=CollectionDifficulty(
                min_rank=data.get("min_rank", 0),
                max_rank=data.get("max_rank", 0),
            ),
            stats=CollectionStats(
                puzzle_count=data.get("puzzle_count", 0),
                view_count=data.get("view_count", 0),
                solved_count=data.get("solved_count", 0),
                attempt_count=data.get("attempt_count", 0),
                rating=data.get("rating", 0.0),
                rating_count=data.get("rating_count", 0),
            ),
        )


# ============================================================================
# HTTP Client
# ============================================================================

class OGSExplorerClient:
    """HTTP client for exploring OGS collections API."""

    def __init__(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        delay_seconds: float = REQUEST_DELAY_SECONDS,
    ):
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self._client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "YenGo-Explorer/1.0"},
        )
        self._request_count = 0

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> OGSExplorerClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _request(self, url: str, params: dict | None = None) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                if self._request_count > 0:
                    time.sleep(self.delay_seconds)

                response = self._client.get(url, params=params)
                self._request_count += 1

                if response.status_code == 429:
                    delay = BACKOFF_FACTOR ** (attempt + 1)
                    logger.warning(f"Rate limited, waiting {delay:.1f}s")
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"HTTP error {e.response.status_code}, retrying...")
            except httpx.RequestError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Request error: {e}, retrying...")

        raise RuntimeError("Max retries exceeded")

    def iter_collections(
        self,
        ordering: str = "-view_count",
        min_puzzle_count: int = 1,
    ) -> Iterator[Collection]:
        """Iterate through all collections.

        Args:
            ordering: Sort order (e.g., "-view_count", "-puzzle_count", "name")
            min_puzzle_count: Skip collections with fewer puzzles

        Yields:
            Collection objects (without puzzles populated)
        """
        page = 1
        total_count = None

        while True:
            url = f"{OGS_API_BASE}/puzzles/collections"
            params = {
                "page": page,
                "page_size": self.page_size,
                "ordering": ordering,
            }

            data = self._request(url, params)

            if total_count is None:
                total_count = data["count"]
                logger.info(f"Total collections in OGS: {total_count}")

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                if item.get("puzzle_count", 0) >= min_puzzle_count:
                    yield Collection.from_api_response(item)

            if not data.get("next"):
                break

            page += 1
            logger.info(f"Fetched page {page - 1}, total requests: {self._request_count}")

    def get_collection_puzzles(self, collection_id: int) -> list[int]:
        """Get all puzzle IDs in a collection.

        Args:
            collection_id: OGS collection ID

        Returns:
            List of puzzle IDs
        """
        puzzle_ids: list[int] = []
        page = 1

        while True:
            url = f"{OGS_API_BASE}/puzzles"
            params = {
                "collection": collection_id,
                "page": page,
                "page_size": self.page_size,
            }

            data = self._request(url, params)
            results = data.get("results", [])

            if not results:
                break

            for item in results:
                puzzle_ids.append(item["id"])

            if not data.get("next"):
                break

            page += 1

        return puzzle_ids


# ============================================================================
# Resume Support
# ============================================================================

def load_existing_collection_ids(path: Path) -> set[int]:
    """Read an existing JSONL file and return the set of collection IDs already fetched."""
    ids: set[int] = set()
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("type") == "collection":
            ids.add(record["id"])
    return ids


# ============================================================================
# Incremental JSONL Writer
# ============================================================================

class CollectionWriter:
    """Writes collections incrementally to a JSONL file.

    Format:
        Line 1: {"type": "metadata", ...}
        Line 2+: {"type": "collection", ...}
    """

    def __init__(self, output_path: Path, extraction_params: dict[str, Any],
                 resume_count: int = 0, resume_puzzles: int = 0):
        self.output_path = output_path
        self.count = resume_count
        self.total_puzzles = resume_puzzles
        self._start_time = datetime.now(UTC)

        if resume_count > 0:
            # Append mode: file already has metadata + previous collections
            self._file = open(output_path, "a", encoding="utf-8")
            logger.info(f"Resuming: {resume_count} collections already in {rel_path(output_path)}")
        else:
            # Fresh start
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(output_path, "w", encoding="utf-8")

        # Write/overwrite metadata header
        self._metadata = {
            "type": "metadata",
            "extracted_at": self._start_time.isoformat(),
            "source": "online-go.com",
            "api_base": OGS_API_BASE,
            "total_collections": resume_count,
            "total_puzzles": resume_puzzles,
            "extraction_params": extraction_params,
            "status": "in_progress",
        }
        if resume_count == 0:
            self._write_line(self._metadata)
        logger.info(f"Writing to: {rel_path(output_path)}")

    def write_collection(self, collection: Collection) -> None:
        """Write a single collection to the JSONL file immediately."""
        record = asdict(collection)
        record["type"] = "collection"
        self._write_line(record)
        self.count += 1
        self.total_puzzles += collection.stats.puzzle_count

    def _write_line(self, obj: dict[str, Any]) -> None:
        self._file.write(json.dumps(obj, ensure_ascii=False))
        self._file.write("\n")
        self._file.flush()

    def close(self, status: str = "completed") -> None:
        """Close the file. Rewrite metadata header with final counts."""
        self._file.close()

        # Rewrite line 1 with final metadata
        lines = self.output_path.read_text(encoding="utf-8").splitlines(keepends=True)
        self._metadata["total_collections"] = self.count
        self._metadata["total_puzzles"] = self.total_puzzles
        self._metadata["status"] = status
        self._metadata["finished_at"] = datetime.now(UTC).isoformat()
        lines[0] = json.dumps(self._metadata, ensure_ascii=False) + "\n"
        self.output_path.write_text("".join(lines), encoding="utf-8")

        logger.info(
            f"Finalized: {self.count} collections, "
            f"{self.total_puzzles} puzzles -> {rel_path(self.output_path)}"
        )

    def __enter__(self) -> CollectionWriter:
        return self

    def __exit__(self, exc_type, *args) -> None:
        status = "completed" if exc_type is None else "interrupted"
        self.close(status=status)


# ============================================================================
# Main Extraction Logic
# ============================================================================

def extract_collections(
    client: OGSExplorerClient,
    writer: CollectionWriter,
    max_collections: int | None = None,
    min_puzzle_count: int = 1,
    fetch_puzzles: bool = True,
    skip_ids: set[int] | None = None,
) -> None:
    """Extract collections and write each one incrementally.

    Args:
        client: OGS API client
        writer: JSONL writer (writes each collection immediately)
        max_collections: Maximum number of collections to fetch (None = all)
        min_puzzle_count: Minimum puzzles required in collection
        fetch_puzzles: Whether to fetch puzzle ID list for each collection
        skip_ids: Collection IDs to skip (already fetched in a previous run)
    """
    skip_ids = skip_ids or set()
    collection_iter = client.iter_collections(
        ordering="-view_count",
        min_puzzle_count=min_puzzle_count,
    )

    written = 0
    skipped = 0
    for _i, collection in enumerate(collection_iter):
        if max_collections and written >= max_collections:
            break

        if collection.id in skip_ids:
            skipped += 1
            logger.debug(f"  Skipping already-fetched collection {collection.id}: {collection.name}")
            continue

        logger.info(
            f"[{writer.count + 1}] Processing: {collection.name} "
            f"({collection.stats.puzzle_count} puzzles, "
            f"{collection.stats.view_count:,} views)"
        )

        if fetch_puzzles:
            collection.puzzles = client.get_collection_puzzles(collection.id)
            logger.info(f"  Fetched {len(collection.puzzles)} puzzle IDs")

        writer.write_collection(collection)
        written += 1

    if skipped:
        logger.info(f"Skipped {skipped} already-fetched collections")


# ============================================================================
# CLI
# ============================================================================

def _default_output_path() -> Path:
    """Generate timestamped output path in external-sources/ogs/."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_project_root() / DEFAULT_OUTPUT_DIR / f"{timestamp}-collections.jsonl"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Explore OGS puzzle collections and extract metadata"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output JSONL file path (default: external-sources/ogs/YYYYMMDD-HHMMSS-collections.jsonl)",
    )
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="Fetch only the first N collections (sorted by popularity)",
    )
    parser.add_argument(
        "--min-puzzles", "-m",
        type=int,
        default=1,
        help="Minimum puzzle count per collection (default: 1)",
    )
    parser.add_argument(
        "--skip-puzzles",
        action="store_true",
        help="Skip fetching individual puzzle ID lists",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        metavar="FILE",
        help="Resume from an existing JSONL file (skips already-fetched collections, appends new ones)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SECONDS,
        help=f"Delay between requests in seconds (default: {REQUEST_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_path = args.resume if args.resume else (args.output if args.output else _default_output_path())

    logger.info("OGS Collections Explorer")
    logger.info("=" * 40)
    logger.info(f"Output: {rel_path(output_path)}")

    # Resume: load already-fetched collection IDs
    skip_ids: set[int] = set()
    resume_count = 0
    resume_puzzles = 0
    if args.resume:
        skip_ids = load_existing_collection_ids(output_path)
        resume_count = len(skip_ids)
        # Count total puzzles from existing file for accurate metadata
        if output_path.exists():
            for line in output_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "collection":
                    resume_puzzles += record.get("stats", {}).get("puzzle_count", 0)
        logger.info(f"Resume: found {resume_count} existing collections to skip")

    extraction_params = {
        "max_collections": args.sample,
        "fetch_puzzles": not args.skip_puzzles,
        "min_puzzle_count": args.min_puzzles,
        "resumed_from": str(args.resume) if args.resume else None,
    }

    with OGSExplorerClient(delay_seconds=args.delay) as client, \
         CollectionWriter(output_path, extraction_params,
                          resume_count=resume_count, resume_puzzles=resume_puzzles) as writer:
        extract_collections(
            client=client,
            writer=writer,
            max_collections=args.sample,
            min_puzzle_count=args.min_puzzles,
            fetch_puzzles=not args.skip_puzzles,
            skip_ids=skip_ids,
        )

    logger.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
