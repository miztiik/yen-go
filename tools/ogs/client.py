"""
HTTP client for OGS API with rate limiting and retry support.
"""

from __future__ import annotations

import logging
import random
import shutil
import subprocess
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
    HTTP_TOO_MANY_REQUESTS,
    OGS_API_BASE,
    USER_AGENT,
)

logger = logging.getLogger("ogs.client")


class OGSClientError(Exception):
    """Error from OGS API client."""
    pass


class OGSClient:
    """HTTP client for OGS API with rate limiting."""

    def __init__(
        self,
        base_url: str = OGS_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """Initialize OGS client.

        Args:
            base_url: OGS API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for rate limits
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

        # Rate limit tracking
        self._consecutive_rate_limits = 0

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> OGSClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

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
            OGSClientError: On HTTP errors
        """
        url = f"{self.base_url}/puzzles/"
        params = {"page": page, "page_size": page_size}

        return self._request_with_retry(url, params)

    def get_puzzle(self, puzzle_id: int) -> dict[str, Any]:
        """Fetch a single puzzle by ID.

        Args:
            puzzle_id: OGS puzzle ID

        Returns:
            Parsed puzzle JSON data

        Raises:
            OGSClientError: On HTTP errors
        """
        url = f"{self.base_url}/puzzles/{puzzle_id}/"
        return self._request_with_retry(url)

    def _request_with_retry(
        self,
        url: str,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic for rate limits.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            OGSClientError: On HTTP errors after retries exhausted
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url, params=params)

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

                # Reset rate limit counter on success
                self._consecutive_rate_limits = 0

                # Raise for other HTTP errors
                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 404:
                    raise OGSClientError(f"Puzzle not found: {url}") from e
                raise OGSClientError(f"HTTP error {e.response.status_code}: {url}") from e

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error: {e}, retrying...")
                time.sleep(self._calculate_backoff(attempt))
                continue

        raise OGSClientError(
            f"Max retries ({self.max_retries}) exceeded for {url}"
        ) from last_error

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** attempt)
        delay = min(base_delay, BACKOFF_MAX_SECONDS)

        # Add jitter (±20%)
        jitter = delay * DELAY_JITTER_FACTOR * (2 * random.random() - 1)
        return delay + jitter

    def get_puzzle_page_html(self, puzzle_id: int) -> str | None:
        """Fetch the HTML page for a puzzle using curl.

        Uses curl (subprocess) instead of httpx because the OGS puzzle page
        is a JavaScript-rendered SPA — curl fetches the raw HTML which
        contains the objective text in meta tags or server-rendered content,
        while httpx would get the same result but curl is explicitly
        requested by the plan for potential future cookie/JS handling.

        Args:
            puzzle_id: OGS puzzle ID

        Returns:
            Raw HTML string, or None if curl is unavailable or fetch fails
        """
        if not self._curl_available():
            return None

        url = f"https://online-go.com/puzzle/{puzzle_id}"
        try:
            result = subprocess.run(
                [
                    "curl",
                    "--silent",
                    "--max-time", str(int(self.timeout)),
                    "--user-agent", USER_AGENT,
                    "--location",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=int(self.timeout) + 5,
            )
            if result.returncode != 0:
                logger.warning(
                    f"curl returned exit code {result.returncode} for puzzle {puzzle_id}"
                )
                return None
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"curl timed out fetching puzzle page {puzzle_id}")
            return None
        except OSError as e:
            logger.warning(f"curl execution failed: {e}")
            return None

    @staticmethod
    def _curl_available() -> bool:
        """Check if curl is available on the system."""
        return shutil.which("curl") is not None


def add_delay_with_jitter(base_delay: float, jitter_factor: float = DELAY_JITTER_FACTOR) -> float:
    """Add jitter to a delay value.

    Args:
        base_delay: Base delay in seconds
        jitter_factor: Jitter range (±factor)

    Returns:
        Delay with jitter applied
    """
    jitter = base_delay * jitter_factor * (2 * random.random() - 1)
    return base_delay + jitter


def wait_with_jitter(
    base_delay: float,
    jitter_factor: float = DELAY_JITTER_FACTOR,
    logger_func: Any | None = None,
) -> None:
    """Wait for a delay with jitter.

    Args:
        base_delay: Base delay in seconds
        jitter_factor: Jitter range (±factor)
        logger_func: Optional logging function for rate limit events
    """
    delay = add_delay_with_jitter(base_delay, jitter_factor)

    if logger_func:
        logger_func(delay)

    time.sleep(delay)
