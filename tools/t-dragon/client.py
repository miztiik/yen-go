"""
TsumegoDragon API client with rate limiting.

Uses HttpClient from tools.core with rate limiting (15s+ between requests)
to avoid being blocked by the Bubble.io CDN.
"""

from __future__ import annotations

import logging
import time
import urllib.parse

from tools.core.http import HttpClient, calculate_backoff_with_jitter

from .models import (
    TDCategory,
    TDCategoryResponse,
    TDPuzzle,
    TDPuzzleResponse,
)

logger = logging.getLogger("tsumegodragon.client")


# API configuration
API_BASE_URL = "https://tsumegodragon.com/api/1.1"
MAX_RESULTS_PER_PAGE = 100  # Bubble.io hard limit

# Default delay between requests (seconds)
DEFAULT_REQUEST_DELAY = 15.0

# User agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class TsumegoDragonClient:
    """Client for TsumegoDragon.com API with rate limiting.

    Uses conservative rate limiting (15s base delay with ±20% jitter)
    to avoid being blocked by the Bubble.io CDN.

    Example:
        client = TsumegoDragonClient(request_delay=15.0)
        categories = client.fetch_categories()
        puzzles = client.fetch_puzzles(category_id="...", level=0)
    """

    def __init__(
        self,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        jitter_factor: float = 0.2,
        timeout: float = 60.0,
    ) -> None:
        """Initialize client.

        Args:
            request_delay: Base delay between requests in seconds (default: 15).
            jitter_factor: Jitter factor for delay (0.2 = ±20%).
            timeout: HTTP request timeout in seconds.
        """
        self.request_delay = request_delay
        self.jitter_factor = jitter_factor
        self._http = HttpClient(
            timeout=timeout,
            max_retries=5,
            headers={"User-Agent": USER_AGENT},
        )
        self._last_request_time: float = 0.0
        self._is_rate_limited = False

    def _wait_with_jitter(self) -> None:
        """Wait between requests with jitter applied.

        Uses exponential backoff if rate limited (429 response).
        """
        base_delay = 60.0 if self._is_rate_limited else self.request_delay

        delay = calculate_backoff_with_jitter(
            base_seconds=base_delay,
            attempt=0,
            multiplier=2.0,
            max_seconds=240.0,
            jitter_factor=self.jitter_factor,
        )

        # Calculate actual wait time since last request
        elapsed = time.time() - self._last_request_time
        actual_wait = max(0, delay - elapsed)

        if actual_wait > 0:
            logger.info(f"Waiting {actual_wait:.1f}s before next request...")
            time.sleep(actual_wait)

    def _make_request(self, url: str) -> dict:
        """Make API request with rate limiting.

        Args:
            url: Full URL to request.

        Returns:
            JSON response as dict.

        Raises:
            FetchError: If request fails after retries.
        """
        self._wait_with_jitter()

        try:
            logger.debug(f"GET {url}")
            self._last_request_time = time.time()
            response = self._http.get_json(url)

            # Reset rate limit flag on success
            self._is_rate_limited = False

            return response

        except Exception as e:
            # Check for 429 in error message
            if "429" in str(e):
                logger.warning("Rate limited (429). Increasing delay.")
                self._is_rate_limited = True
            raise

    def fetch_categories(self) -> list[TDCategory]:
        """Fetch all puzzle categories.

        Returns:
            List of all categories.
        """
        url = f"{API_BASE_URL}/obj/category?limit=50"
        response = self._make_request(url)

        # Parse response
        parsed = TDCategoryResponse(**response["response"])
        logger.info(f"Fetched {len(parsed.results)} categories")

        return parsed.results

    def fetch_puzzles(
        self,
        category_id: str | None = None,
        level: int | None = None,
        cursor: int = 0,
        limit: int = MAX_RESULTS_PER_PAGE,
    ) -> TDPuzzleResponse:
        """Fetch puzzles with optional filters.

        Args:
            category_id: Filter by category ID (not slug).
            level: Filter by level (0-8).
            cursor: Pagination cursor (offset).
            limit: Max results per page (max 100).

        Returns:
            Puzzle response with results and pagination info.
        """
        # Build URL with constraints
        params = [f"limit={min(limit, MAX_RESULTS_PER_PAGE)}", f"cursor={cursor}"]

        constraints = []
        if category_id:
            constraints.append({
                "key": "category",
                "constraint_type": "equals",
                "value": category_id,
            })
        if level is not None:
            constraints.append({
                "key": "Level Sort Number",
                "constraint_type": "equals",
                "value": level,
            })

        if constraints:
            import json
            constraints_json = json.dumps(constraints)
            params.append(f"constraints={urllib.parse.quote(constraints_json)}")

        url = f"{API_BASE_URL}/obj/tsumego?{'&'.join(params)}"
        response = self._make_request(url)

        # Parse response
        parsed = TDPuzzleResponse(**response["response"])
        logger.debug(
            f"Fetched {len(parsed.results)} puzzles "
            f"(cursor={cursor}, remaining={parsed.remaining})"
        )

        return parsed

    def fetch_puzzle_by_id(self, puzzle_id: str) -> TDPuzzle:
        """Fetch a single puzzle by ID.

        Args:
            puzzle_id: Puzzle ID.

        Returns:
            Puzzle data.
        """
        url = f"{API_BASE_URL}/obj/tsumego/{puzzle_id}"
        response = self._make_request(url)

        return TDPuzzle(**response["response"])

    def close(self) -> None:
        """Close HTTP client."""
        self._http.close()

    def __enter__(self) -> TsumegoDragonClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager."""
        self.close()
