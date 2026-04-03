"""
HTTP client for BlackToPlay (BTP) API.

BTP requires POST requests with browser-like headers. The shared
tools.core.http.HttpClient only supports GET, so this module uses
httpx directly with the retry/backoff patterns from the project.

Endpoints:
- load_data.php: Fetch full puzzle data by ID and type.
- load_list.php: Enumerate all puzzle IDs by type (may return empty
  from httpx — falls back to cached JSON).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from .config import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    BACKOFF_MULTIPLIER,
    BROWSER_HEADERS,
    BTP_LOAD_DATA_URL,
    BTP_LOAD_LIST_URL,
    CACHED_LIST_PATH,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    HTTP_TOO_MANY_REQUESTS,
    PUZZLE_TYPE_NAMES,
)
from .models import BTPListItem, BTPPuzzle

logger = logging.getLogger("btp.client")


class BTPClientError(Exception):
    """Raised when BTP API request fails after retries."""

    pass


class BTPClient:
    """HTTP client for BlackToPlay.com API.

    Uses httpx with browser-like headers and retry logic.
    Supports both live API and cached fallback for puzzle lists.

    Usage::

        with BTPClient() as client:
            puzzle = client.fetch_puzzle(puzzle_id=123, puzzle_type=0)
            items = client.list_puzzles(puzzle_type=0)
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.Client | None = None

    def __enter__(self) -> BTPClient:
        self._client = httpx.Client(
            headers=BROWSER_HEADERS,
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=BROWSER_HEADERS,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._client

    def _post_with_retry(self, url: str, data: dict[str, Any]) -> httpx.Response:
        """POST with exponential backoff retry.

        Retries on 429, 5xx, and connection errors.
        """
        client = self._ensure_client()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = client.post(url, data=data)

                if response.status_code == HTTP_TOO_MANY_REQUESTS:
                    wait = min(
                        BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** attempt),
                        BACKOFF_MAX_SECONDS,
                    )
                    logger.warning(
                        "Rate limited (429), waiting %.1fs (attempt %d/%d)",
                        wait, attempt + 1, self._max_retries + 1,
                    )
                    time.sleep(wait)
                    continue

                if response.status_code >= 500:
                    wait = min(
                        BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** attempt),
                        BACKOFF_MAX_SECONDS,
                    )
                    logger.warning(
                        "Server error %d, retrying in %.1fs (attempt %d/%d)",
                        response.status_code, wait, attempt + 1, self._max_retries + 1,
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_exc = e
                wait = min(
                    BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** attempt),
                    BACKOFF_MAX_SECONDS,
                )
                logger.warning(
                    "Connection error: %s, retrying in %.1fs (attempt %d/%d)",
                    e, wait, attempt + 1, self._max_retries + 1,
                )
                time.sleep(wait)

        raise BTPClientError(
            f"Failed after {self._max_retries + 1} attempts: {last_exc}"
        )

    # ================================================================
    # Puzzle fetch
    # ================================================================

    def fetch_puzzle(self, puzzle_id: str, puzzle_type: int) -> BTPPuzzle:
        """Fetch full puzzle data from load_data.php.

        Args:
            puzzle_id: BTP puzzle ID.
            puzzle_type: 0=Classic, 1=AI, 2=Endgame (not used in API call).

        Returns:
            BTPPuzzle with all fields populated.

        Raises:
            BTPClientError: If request fails or response is invalid.
        """
        # API requires db=0 (not the puzzle type), plus vid and rating params
        response = self._post_with_retry(
            BTP_LOAD_DATA_URL,
            data={
                "id": str(puzzle_id),
                "db": "0",
                "vid": "yengo",
                "rating": "1500",
            },
        )

        try:
            raw = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise BTPClientError(f"Invalid JSON for puzzle {puzzle_id}: {e}") from e

        return _parse_puzzle_response(raw, puzzle_id, puzzle_type)

    # ================================================================
    # Puzzle list
    # ================================================================

    def list_puzzles(
        self,
        puzzle_type: int,
        use_cache: bool = True,
    ) -> list[BTPListItem]:
        """Get list of all puzzle IDs for a given type.

        Tries live API first. If it returns empty/invalid and use_cache
        is True, falls back to cached JSON.

        Args:
            puzzle_type: 0=Classic, 1=AI, 2=Endgame.
            use_cache: Whether to use cached fallback.

        Returns:
            List of BTPListItem objects.
        """
        # Try live API
        try:
            items = self._list_puzzles_live(puzzle_type)
            if items:
                logger.info(
                    "Live API returned %d puzzles for type %s",
                    len(items), PUZZLE_TYPE_NAMES.get(puzzle_type, str(puzzle_type)),
                )
                return items
        except Exception as e:
            logger.warning("Live list API failed: %s", e)

        # Fall back to cache
        if use_cache:
            items = self._list_puzzles_cached(puzzle_type)
            if items:
                logger.info(
                    "Cached list returned %d puzzles for type %s",
                    len(items), PUZZLE_TYPE_NAMES.get(puzzle_type, str(puzzle_type)),
                )
                return items

        logger.warning(
            "No puzzle list available for type %s",
            PUZZLE_TYPE_NAMES.get(puzzle_type, str(puzzle_type)),
        )
        return []

    def _list_puzzles_live(self, puzzle_type: int) -> list[BTPListItem]:
        """Fetch puzzle list from live API.

        The public endpoint returns all puzzles at once (all types),
        so we filter by puzzle_type after fetching.
        """
        response = self._post_with_retry(
            BTP_LOAD_LIST_URL,
            data={"tsumego_request": "all_available"},
        )

        try:
            raw = response.json()
        except (json.JSONDecodeError, ValueError):
            return []

        # Response format: {"status": "success", "list": [...]}
        if not isinstance(raw, dict):
            return []

        if raw.get("status") != "success":
            return []

        entries = raw.get("list", [])
        if not isinstance(entries, list):
            return []

        items: list[BTPListItem] = []
        for entry in entries:
            if isinstance(entry, dict) and "id" in entry:
                # Filter by puzzle type (type is a string in response)
                entry_type = int(entry.get("type", -1))
                if entry_type != puzzle_type:
                    continue
                items.append(
                    BTPListItem(
                        puzzle_id=entry["id"],  # ID is alphanumeric string
                        puzzle_type=puzzle_type,
                        rating=int(entry.get("rating", 0)),
                    )
                )

        return items

    def _list_puzzles_cached(self, puzzle_type: int) -> list[BTPListItem]:
        """Load puzzle list from cached JSON file."""
        if not CACHED_LIST_PATH.exists():
            logger.debug("Cached list file not found: %s", CACHED_LIST_PATH)
            return []

        try:
            with open(CACHED_LIST_PATH, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cached list: %s", e)
            return []

        # Cache format: {"list": [...], ...} where each entry has type field
        # The "list" key contains all puzzles from all types
        if isinstance(data, dict) and "list" in data:
            entries = data["list"]
        elif isinstance(data, list):
            entries = data
        else:
            return []

        items: list[BTPListItem] = []
        for entry in entries:
            if isinstance(entry, dict) and "id" in entry:
                # Filter by puzzle type (type is a string in the cached data)
                entry_type = int(entry.get("type", -1))
                if entry_type != puzzle_type:
                    continue
                items.append(
                    BTPListItem(
                        puzzle_id=str(entry["id"]),
                        puzzle_type=entry_type,
                        rating=int(entry.get("rating", 0)),
                    )
                )

        return items


# ============================================================================
# Response parsing
# ============================================================================


def _parse_puzzle_response(
    raw: dict[str, Any],
    puzzle_id: str,
    puzzle_type: int,
) -> BTPPuzzle:
    """Parse the load_data.php JSON response into a BTPPuzzle.

    BTP response fields (observed):
    - hash: base-59 position hash string
    - board_size: visible board size
    - to_play: "B" or "W"
    - rating: integer difficulty
    - nodes: list of node strings (solution tree)
    - tags: 2-char encoded tags
    - categories: category letter(s)
    """
    # Check for error response
    if isinstance(raw, str) and "error" in raw.lower():
        from tools.blacktoplay.errors import BTPClientError
        raise BTPClientError(f"API error for puzzle {puzzle_id}: {raw}")

    # Extract node strings (may be a list or semicolon-separated string)
    nodes_raw = raw.get("nodes", [])
    if isinstance(nodes_raw, str):
        nodes = [n for n in nodes_raw.split("\n") if n.strip()]
    elif isinstance(nodes_raw, list):
        nodes = [str(n) for n in nodes_raw]
    else:
        nodes = []

    return BTPPuzzle(
        puzzle_id=puzzle_id,
        puzzle_type=puzzle_type,
        board_size=int(raw.get("board_size", 19)),
        viewport_size=int(raw.get("viewport_size", raw.get("board_size", 9))),
        position_hash=str(raw.get("hash", raw.get("position", ""))),
        to_play=str(raw.get("to_play", "B")),
        rating=int(raw.get("rating", 0)),
        nodes=nodes,
        tags=str(raw.get("tags", "")),
        categories=str(raw.get("categories", "")),
        title=str(raw.get("title", "")),
        author=str(raw.get("author", "")),
        comment=str(raw.get("comment", "")),
        raw_data=raw,
    )
