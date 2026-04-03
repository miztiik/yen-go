"""
Tsumego Hero HTTP client with rate limiting.

Downloads puzzles from tsumego.com with conservative rate limiting
to avoid being blocked.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from tools.core.rate_limit import apply_rate_limit as _core_apply_rate_limit

logger = logging.getLogger("tsumego_hero.client")


@dataclass
class PuzzleData:
    """Parsed puzzle data from Tsumego Hero."""

    url_id: int
    sgf: str
    tsumego_id: int | None = None
    set_id: int | None = None
    sgf_id: int | None = None
    collection_name: str | None = None
    description: str | None = None
    difficulty: str | None = None
    difficulty_rating: float | None = None  # Numerical ELO-style rating (e.g., 587.069)
    author: str | None = None
    tags: list[dict[str, Any]] | None = None
    raw_html: str | None = None


class TsumegoHeroClientError(Exception):
    """Error from Tsumego Hero client."""
    pass


class TsumegoHeroClient:
    """HTTP client for tsumego.com with rate limiting.

    Example:
        client = TsumegoHeroClient()
        puzzle = client.fetch_puzzle(5225)
        collections = client.fetch_collections()
    """

    def __init__(
        self,
        base_url: str = "https://tsumego.com",
        base_delay: float = 2.5,
        jitter_factor: float = 0.4,
        timeout: float = 30.0,
        max_retries: int = 3,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ) -> None:
        """Initialize client.

        Args:
            base_url: Base URL for tsumego.com
            base_delay: Base delay between requests in seconds
            jitter_factor: Jitter factor for delay (0.4 = ±40%)
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: User agent string for requests
        """
        self.base_url = base_url.rstrip("/")
        self.base_delay = base_delay
        self.jitter_factor = jitter_factor
        self.max_retries = max_retries

        self._http = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        # Used only for collection-page fetches (not puzzle fetches).
        # Puzzle-fetch rate limiting is driven by the orchestrator via apply_rate_limit().
        self._last_request_time: float = 0.0

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self) -> TsumegoHeroClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _wait_with_jitter(self) -> None:
        """Wait between collection-page requests with jitter.

        Used internally for set/collection page fetches only.
        Puzzle fetches use apply_rate_limit() driven by the orchestrator.
        Delegates to tools.core.rate_limit.apply_rate_limit().
        """
        elapsed = time.monotonic() - self._last_request_time
        _core_apply_rate_limit(
            elapsed=elapsed,
            min_delay=self.base_delay * (1 - self.jitter_factor),
            max_delay=self.base_delay * (1 + self.jitter_factor),
        )

    def apply_rate_limit(self, elapsed: float = 0.0) -> None:
        """Apply inter-puzzle rate limiting, subtracting time already spent.

        Called by the orchestrator after each full puzzle fetch cycle
        (HTTP + validate + enrich + save).  Delegates to
        ``tools.core.rate_limit.apply_rate_limit()`` so the logic lives
        in one canonical place.

        Args:
            elapsed: Seconds already spent in the current cycle,
                     measured with ``time.monotonic()`` by the caller.
        """
        _core_apply_rate_limit(
            elapsed=elapsed,
            min_delay=self.base_delay * (1 - self.jitter_factor),
            max_delay=self.base_delay * (1 + self.jitter_factor),
        )

    def _get(self, path: str, skip_rate_limit: bool = False) -> str:
        """Make GET request with optional rate limiting.

        Args:
            path: URL path (e.g., "/5225" or "/sets/view/104")
            skip_rate_limit: If True, bypass the internal jitter wait.
                             Use this for puzzle fetches where the orchestrator
                             drives rate limiting via apply_rate_limit().

        Returns:
            Response text

        Raises:
            TsumegoHeroClientError: On HTTP errors
        """
        if not skip_rate_limit:
            self._wait_with_jitter()
        url = f"{self.base_url}{path}"

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"GET {url} (attempt {attempt + 1})")
                response = self._http.get(url)
                self._last_request_time = time.monotonic()

                response.raise_for_status()
                return response.text

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    backoff = self.base_delay * (2 ** attempt) + random.random()
                    logger.warning(f"Rate limited, waiting {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                raise TsumegoHeroClientError(f"HTTP {e.response.status_code}: {url}") from e

            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise TsumegoHeroClientError(f"Request failed: {url}") from e
                time.sleep(self.base_delay * (attempt + 1))

        raise TsumegoHeroClientError(f"Max retries exceeded: {url}")

    def fetch_collections(self) -> dict[str, dict[str, Any]]:
        """Fetch list of all collections.

        Returns:
            Dict of set_id -> collection info
        """
        html = self._get("/sets")

        collections = {}

        # First pass: Extract all unique set IDs from links
        # Include paginated links like /sets/view/263/1
        set_pattern = r'href="/sets/view/(\d+)(?:/\d+)?"'
        for match in re.finditer(set_pattern, html):
            set_id = match.group(1)
            if set_id not in collections:
                collections[set_id] = {"set_id": int(set_id)}

        # Second pass: Match set_id with tile content using combined pattern
        # Structure: <a href="/sets/view/{id}"...>...<div class="collection-top">{name}</div>...<div class="collection-middle-left">{count} problems</div>
        tile_pattern = r'href="/sets/view/(\d+)"[^>]*>.*?<div class="collection-top">([^<]+)</div>.*?<div class="collection-middle-left">(\d+) problems</div>.*?<div class="collection-middle-right">~(\d+[kd])</div>'
        for match in re.finditer(tile_pattern, html, re.DOTALL):
            set_id, name, count, difficulty = match.groups()
            if set_id in collections:
                collections[set_id]["name"] = name.strip()
                collections[set_id]["puzzle_count"] = int(count)
                collections[set_id]["difficulty"] = difficulty

        # Third pass: Fetch missing metadata from individual collection pages
        for set_id, info in collections.items():
            if info.get("name") is None:
                try:
                    coll_html = self._get(f"/sets/view/{set_id}")
                    # Extract name from title
                    title_match = re.search(r'<title>([^<]+)', coll_html)
                    if title_match:
                        info["name"] = title_match.group(1).replace(" on Tsumego Hero", "").strip()
                    # Extract puzzle count
                    count_match = re.search(r'(\d+) Problems', coll_html)
                    if count_match:
                        info["puzzle_count"] = int(count_match.group(1))
                    # Extract difficulty from page if available
                    diff_match = re.search(r'~(\d+[kd])', coll_html)
                    if diff_match:
                        info["difficulty"] = diff_match.group(1)
                except TsumegoHeroClientError:
                    logger.warning(f"Failed to fetch details for collection {set_id}")

        logger.info(f"Found {len(collections)} collections")
        return collections

    def fetch_collection_puzzles(self, set_id: int) -> list[int]:
        """Fetch puzzle URL IDs for a collection, following all pages.

        Some collections are paginated: /sets/view/{set_id}/1,
        /sets/view/{set_id}/2, etc.  We keep fetching pages until a page
        yields no new puzzle IDs that weren't already seen, which indicates
        we have reached the end (or a navigation-only page).

        Args:
            set_id: Collection/set ID

        Returns:
            List of puzzle URL IDs in collection order (all pages combined).
        """
        puzzle_pattern = r'href="/(\d+)"'
        # Pattern for "next page" links: /sets/view/{id}/2, /sets/view/{id}/3 …
        next_page_pattern = rf'href="/sets/view/{set_id}/(\d+)"'

        seen: set[int] = set()
        ordered: list[int] = []

        def _extract_puzzle_ids(html: str) -> list[int]:
            ids = []
            for m in re.finditer(puzzle_pattern, html):
                pid = int(m.group(1))
                # Exclude IDs that look like set/navigation IDs (> 100000)
                if pid < 100000:
                    ids.append(pid)
            return ids

        # Page 1 — always the base URL
        html = self._get(f"/sets/view/{set_id}")
        page_ids = _extract_puzzle_ids(html)
        new_on_page = 0
        for pid in page_ids:
            if pid not in seen:
                seen.add(pid)
                ordered.append(pid)
                new_on_page += 1
        logger.debug(f"Collection {set_id} page 1: {new_on_page} new puzzle IDs")

        # Detect if further pages exist and follow them
        page_nums_found = {
            int(m.group(1))
            for m in re.finditer(next_page_pattern, html)
        }
        page = 2
        while page in page_nums_found or page_nums_found:
            # If current page number wasn't linked, stop
            if page not in page_nums_found:
                break

            html = self._get(f"/sets/view/{set_id}/{page}")
            page_ids = _extract_puzzle_ids(html)
            new_on_page = 0
            for pid in page_ids:
                if pid not in seen:
                    seen.add(pid)
                    ordered.append(pid)
                    new_on_page += 1

            logger.debug(
                f"Collection {set_id} page {page}: {new_on_page} new puzzle IDs"
            )

            # Discover any further page links on this page
            page_nums_found = {
                int(m.group(1))
                for m in re.finditer(next_page_pattern, html)
            }

            # Stop if page added nothing new (safety guard against loops)
            if new_on_page == 0:
                logger.debug(
                    f"Collection {set_id}: page {page} yielded no new IDs, stopping"
                )
                break

            page += 1

        logger.info(f"Collection {set_id}: {len(ordered)} puzzles across {page - 1} page(s)")
        return ordered

    def fetch_puzzle(self, url_id: int) -> PuzzleData | None:
        """Fetch and parse a single puzzle.

        Rate limiting is NOT applied here — the orchestrator owns the timing.
        It calls apply_rate_limit(elapsed) after the full fetch cycle.

        Args:
            url_id: Puzzle URL ID (e.g., 5225)

        Returns:
            PuzzleData or None if puzzle not found/invalid
        """
        html = self._get(f"/{url_id}", skip_rate_limit=True)

        # Extract SGF
        # Match the full JavaScript assignment: options.sgf2 = "..."+"\n"+"..."...;
        sgf_match = re.search(r'options\.sgf2\s*=\s*(.+?);\s*\n', html)
        if not sgf_match:
            logger.warning(f"No SGF found for puzzle {url_id}")
            return None

        # Parse JavaScript string concatenation
        # The SGF is stored as: "(;..."+"\n"+"RU[...]"+"\n"+"..."
        # Split by the concatenation pattern and join
        full_expr = sgf_match.group(1)
        parts = full_expr.split('"+\"')
        sgf = ''.join(parts)

        # Strip leading/trailing quotes
        sgf = sgf.strip('"')

        # Unescape newlines (literal backslash-n in source)
        sgf = sgf.replace('\\n', '\n')

        # Validate basic SGF structure
        if not sgf.startswith("(;") or "GM[1]" not in sgf:
            logger.warning(f"Invalid SGF structure for puzzle {url_id}")
            return None

        puzzle = PuzzleData(url_id=url_id, sgf=sgf)

        # Extract tsumegoID
        match = re.search(r'var tsumegoID = (\d+);', html)
        if match:
            puzzle.tsumego_id = int(match.group(1))

        # Extract setID
        match = re.search(r'var setID = (\d+);', html)
        if match:
            puzzle.set_id = int(match.group(1))

        # Extract sgfID from editor link
        match = re.search(r'sgfID=(\d+)', html)
        if match:
            puzzle.sgf_id = int(match.group(1))

        # Extract collection name
        match = re.search(r'href="/sets/view/\d+">([^<]+)<', html)
        if match:
            puzzle.collection_name = match.group(1).strip()

        # Extract description
        match = re.search(r'id="descriptionText">([^<]+)<', html)
        if match:
            puzzle.description = match.group(1).strip()

        # Extract difficulty
        match = re.search(r'<font size="4">\s*(\d+[kd])', html)
        if match:
            puzzle.difficulty = match.group(1)

        # Extract numerical rating (e.g., 587.069)
        match = re.search(r'<font size="4">\s*\d+[kd]\s*<font[^>]*>\((\d+\.\d+)\)', html)
        if match:
            puzzle.difficulty_rating = float(match.group(1))

        # Extract author
        match = re.search(r'var author = "([^"]+)";', html)
        if match:
            puzzle.author = match.group(1)

        # Extract tags (JSON-ish format in JavaScript, spans multiple lines)
        # Format: tags: [{name: '...', id: N, isAdded: 0/1, isHint: 0/1, ...}, ...]
        # IMPORTANT: Only tags with isAdded: 1 are actually assigned to this puzzle.
        # Tags with isAdded: 0 are just available for users to add.
        match = re.search(r'tags:\s*\[(.+?)\]', html, re.DOTALL)
        if match:
            try:
                # Clean up the captured content
                tags_content = match.group(1)
                # Remove excessive whitespace between objects
                tags_content = re.sub(r'\s+', ' ', tags_content)
                tags_str = "[" + tags_content + "]"
                # Convert JavaScript object notation to JSON
                # Handle single quotes around values
                tags_str = tags_str.replace("'", '"')
                # Handle escaped quotes in names (e.g., Carpenter\'s Square)
                tags_str = tags_str.replace('\\"', "'")
                # Quote property names
                tags_str = re.sub(r'(\w+):', r'"\1":', tags_str)
                all_tags = json.loads(tags_str)

                # Filter to only include tags actually assigned to this puzzle:
                # - isAdded: 1 means the tag is assigned
                # - Exclude generic "Tsumego" tag (not meaningful for classification)
                puzzle.tags = [
                    tag for tag in all_tags
                    if tag.get("isAdded") == 1 and tag.get("name") != "Tsumego"
                ]
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Could not parse tags for puzzle {url_id}: {e}")

        logger.debug(
            f"Puzzle {url_id}: {puzzle.collection_name}, "
            f"{puzzle.difficulty}, {len(puzzle.sgf)} chars"
        )

        return puzzle


def save_sgf(puzzle: PuzzleData, output_dir: Path, collection_slug: str) -> Path:
    """Save puzzle SGF to file.

    Args:
        puzzle: Parsed puzzle data
        output_dir: Output directory
        collection_slug: Collection slug for subdirectory

    Returns:
        Path to saved file
    """
    sgf_dir = output_dir / "sgf" / collection_slug
    sgf_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{puzzle.url_id}.sgf"
    filepath = sgf_dir / filename

    filepath.write_text(puzzle.sgf, encoding="utf-8")

    return filepath


def save_metadata(puzzle: PuzzleData, output_dir: Path) -> Path:
    """Save puzzle metadata to JSON.

    Args:
        puzzle: Parsed puzzle data
        output_dir: Output directory

    Returns:
        Path to saved file
    """
    meta_dir = output_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "url_id": puzzle.url_id,
        "tsumego_id": puzzle.tsumego_id,
        "set_id": puzzle.set_id,
        "sgf_id": puzzle.sgf_id,
        "collection_name": puzzle.collection_name,
        "description": puzzle.description,
        "difficulty": puzzle.difficulty,
        "tags": puzzle.tags,
    }

    filename = f"{puzzle.url_id}.json"
    filepath = meta_dir / filename

    filepath.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return filepath


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    with TsumegoHeroClient() as client:
        # Test single puzzle
        puzzle = client.fetch_puzzle(5225)
        if puzzle:
            print(f"\nPuzzle {puzzle.url_id}:")
            print(f"  Collection: {puzzle.collection_name}")
            print(f"  Description: {puzzle.description}")
            print(f"  Difficulty: {puzzle.difficulty}")
            print(f"  SGF preview: {puzzle.sgf[:100]}...")
            if puzzle.tags:
                print(f"  Tags: {[t.get('name') for t in puzzle.tags]}")

        # Test collection enumeration
        print("\n\nFetching collection 104 (Easy Life)...")
        puzzle_ids = client.fetch_collection_puzzles(104)
        print(f"Found {len(puzzle_ids)} puzzles: {puzzle_ids[:10]}...")
