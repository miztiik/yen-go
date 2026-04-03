"""
HTTP client for GoProblems API with rate limiting and retry support.

Wraps httpx directy (not tools.core.http.HttpClient) to match the OGS pattern.
Provides GoProblems-specific methods for puzzle fetching.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from .config import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    BACKOFF_MULTIPLIER,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DELAY_JITTER_FACTOR,
    GOPROBLEMS_API_BASE,
    GOPROBLEMS_COLLECTIONS_API_BASE,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    USER_AGENT,
)

logger = logging.getLogger("go_problems.client")


class GoProblemsClientError(Exception):
    """Error from GoProblems API client."""

    pass


class GoProblemsClient:
    """HTTP client for GoProblems API with retry and rate limiting.

    Supports three endpoints:
    - GET /api/v2/problems/{id} -- fetch single puzzle with full SGF
    - GET /api/v2/problems?page=N -- paginated listing for discovery
    - GET /api/collections?offset=N&limit=M -- paginated collections listing

    Usage:
        with GoProblemsClient() as client:
            data = client.get_puzzle(42)
    """

    def __init__(
        self,
        base_url: str = GOPROBLEMS_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

        self._consecutive_rate_limits = 0

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> GoProblemsClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def get_puzzle(self, puzzle_id: int) -> dict[str, Any] | None:
        """Fetch a single puzzle by ID.

        Args:
            puzzle_id: GoProblems puzzle ID

        Returns:
            Parsed puzzle JSON data, or None if 404 (not found)

        Raises:
            GoProblemsClientError: On non-404 HTTP errors
        """
        url = f"{self.base_url}/problems/{puzzle_id}"
        return self._request_with_retry(url, allow_not_found=True)

    def get_puzzles_page(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Fetch a page of puzzles from the list endpoint.

        Args:
            page: Page number (1-indexed)
            page_size: Results per page (max 50)

        Returns:
            Parsed JSON response with count, next, previous, results

        Raises:
            GoProblemsClientError: On HTTP errors
        """
        url = f"{self.base_url}/problems"
        params = {"page": page, "page_size": page_size}

        result = self._request_with_retry(url, params=params)
        if result is None:
            raise GoProblemsClientError(f"List endpoint returned 404: {url}")
        return result

    def get_collections(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Fetch collections from the collections API.

        Uses the /api/collections endpoint (NOT /api/v2/).
        Max limit per request: 100. Total available: ~259.

        Args:
            offset: Starting offset for pagination.
            limit: Number of collections per request (max 100).

        Returns:
            Parsed JSON response with keys:
            - "entries": list of collection dicts
            - "totalRecords": total number of collections

        Raises:
            GoProblemsClientError: On HTTP errors.
        """
        url = f"{GOPROBLEMS_COLLECTIONS_API_BASE}/collections"
        params = {"offset": offset, "limit": min(limit, 100)}

        result = self._request_with_retry(url, params=params)
        if result is None:
            raise GoProblemsClientError(
                f"Collections endpoint returned 404: {url}"
            )
        return result

    def _request_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> dict[str, Any] | None:
        """Make HTTP request with retry logic for rate limits and server errors.

        Args:
            url: Request URL
            params: Query parameters
            allow_not_found: If True, return None on 404 instead of raising

        Returns:
            Parsed JSON response, or None if 404 and allow_not_found=True

        Raises:
            GoProblemsClientError: On HTTP errors after retries exhausted
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url, params=params)

                # Handle 404
                if response.status_code == HTTP_NOT_FOUND:
                    if allow_not_found:
                        return None
                    raise GoProblemsClientError(f"Not found: {url}")

                # Handle rate limiting
                if response.status_code == HTTP_TOO_MANY_REQUESTS:
                    self._consecutive_rate_limits += 1
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Rate limited (429), waiting {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue

                # Handle server errors (5xx) with retry
                if response.status_code >= 500:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Server error ({response.status_code}), waiting {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue

                # Reset rate limit counter on success
                self._consecutive_rate_limits = 0

                # Raise for other HTTP errors (4xx except 404/429)
                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                raise GoProblemsClientError(
                    f"HTTP error {e.response.status_code}: {url}"
                ) from e

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error: {e}, retrying...")
                time.sleep(self._calculate_backoff(attempt))
                continue

        raise GoProblemsClientError(
            f"Max retries ({self.max_retries}) exceeded for {url}"
        ) from last_error

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER**attempt)
        delay = min(base_delay, BACKOFF_MAX_SECONDS)

        # Add jitter (±20%)
        jitter = delay * DELAY_JITTER_FACTOR * (2 * random.random() - 1)
        return max(0.1, delay + jitter)
