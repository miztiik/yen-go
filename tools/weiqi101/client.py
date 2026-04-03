"""
HTTP client for 101weiqi.com page fetching.

Handles rate limiting, exponential backoff, jitter, and retry logic.
Uses httpx for HTTP requests (via tools.core.http if available, else direct).
"""

from __future__ import annotations

import logging
import random
import time

import httpx

from .config import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    BACKOFF_MULTIPLIER,
    BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DELAY_JITTER_FACTOR,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    USER_AGENT,
)

logger = logging.getLogger("101weiqi.client")


class WeiQiClient:
    """HTTP client for 101weiqi.com with retry and backoff."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        cookies: dict[str, str] | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "DNT": "1",
                "Sec-GPC": "1",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            },
            cookies=cookies or {},
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> WeiQiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER**attempt)
        jitter = base * DELAY_JITTER_FACTOR * random.random()
        return min(base + jitter, BACKOFF_MAX_SECONDS)

    def fetch_page(self, url: str) -> str | None:
        """Fetch a page with retry and exponential backoff.

        Args:
            url: Full URL to fetch.

        Returns:
            Response text on success, None on failure after all retries.
        """
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url)

                if response.status_code == HTTP_NOT_FOUND:
                    logger.debug(f"404 Not Found: {url}")
                    return None

                if response.status_code == HTTP_TOO_MANY_REQUESTS:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Rate limited (429), backoff {delay:.1f}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue

                if response.status_code >= 500:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Server error {response.status_code}, backoff {delay:.1f}s "
                        f"(attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                return response.text

            except httpx.TimeoutException:
                delay = self._calculate_backoff(attempt)
                logger.warning(
                    f"Timeout fetching {url}, backoff {delay:.1f}s (attempt {attempt + 1})"
                )
                time.sleep(delay)

            except httpx.HTTPError as e:
                delay = self._calculate_backoff(attempt)
                logger.warning(
                    f"HTTP error fetching {url}: {e}, backoff {delay:.1f}s "
                    f"(attempt {attempt + 1})"
                )
                time.sleep(delay)

        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def fetch_daily_puzzle(self, year: int, month: int, day: int, num: int) -> str | None:
        """Fetch a daily puzzle page.

        Args:
            year: Puzzle year.
            month: Puzzle month (1-12).
            day: Puzzle day (1-31).
            num: Puzzle number (1-8 typically).

        Returns:
            HTML content or None on failure.
        """
        url = f"{BASE_URL}/qday/{year}/{month}/{day}/{num}/"
        logger.info(f"GET {url}")
        return self.fetch_page(url)

    def fetch_puzzle_by_id(self, puzzle_id: int) -> str | None:
        """Fetch a puzzle by its numeric ID.

        Args:
            puzzle_id: 101weiqi public puzzle ID.

        Returns:
            HTML content or None on failure.
        """
        url = f"{BASE_URL}/q/{puzzle_id}/"
        logger.info(f"GET {url}")
        return self.fetch_page(url)
