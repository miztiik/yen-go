"""
HTTP client with retry logic and rate limiting.

Provides robust HTTP requests with:
- Exponential backoff with jitter
- Rate limiting
- Retry on failures
- SSRF protection

Usage:
    from tools.core.http import HttpClient, calculate_backoff_with_jitter

    client = HttpClient(timeout=30, max_retries=3)
    response = client.get("https://example.com/api")
    data = response.json()
"""

from __future__ import annotations

import logging
import random
import time
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("tools.core.http")


# SSRF protection - blocked hosts
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
}

# SSRF protection - allowed schemes
ALLOWED_SCHEMES = {"http", "https"}


class HttpError(Exception):
    """HTTP request error."""

    def __init__(self, message: str, status_code: int = None, url: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class RateLimitError(HttpError):
    """Rate limit exceeded (HTTP 429)."""
    pass


def calculate_backoff_with_jitter(
    base_seconds: float,
    attempt: int = 0,
    multiplier: float = 2.0,
    max_seconds: float = 240.0,
    jitter_factor: float = 0.2,
) -> float:
    """Calculate exponential backoff with jitter.

    Adds randomization to prevent thundering herd problem when multiple
    clients retry simultaneously.

    Args:
        base_seconds: Initial backoff duration in seconds.
        attempt: Retry attempt number (0-indexed).
        multiplier: Factor to multiply backoff by each attempt.
        max_seconds: Maximum backoff duration cap.
        jitter_factor: Randomization factor (0.2 = ±20% variation).

    Returns:
        Backoff duration in seconds with jitter applied.

    Example:
        >>> backoff = calculate_backoff_with_jitter(30.0, attempt=0)  # ~30s
        >>> backoff = calculate_backoff_with_jitter(30.0, attempt=1)  # ~60s
    """
    # Calculate base exponential backoff
    backoff = base_seconds * (multiplier ** attempt)

    # Apply cap
    backoff = min(backoff, max_seconds)

    # Apply jitter: randomize within ±jitter_factor range
    jitter_min = 1.0 - jitter_factor
    jitter_max = 1.0 + jitter_factor
    jittered_backoff = backoff * (jitter_min + random.random() * (jitter_max - jitter_min))

    return jittered_backoff


def add_jitter(delay: float, jitter_factor: float = 0.5) -> float:
    """Add jitter to a delay value.

    Args:
        delay: Base delay in seconds.
        jitter_factor: Randomization factor (0.5 = 50% to 150% of base).

    Returns:
        Delay with jitter applied.
    """
    jitter_min = 1.0 - jitter_factor
    jitter_max = 1.0 + jitter_factor
    return delay * (jitter_min + random.random() * (jitter_max - jitter_min))


def validate_url(url: str) -> None:
    """Validate URL for SSRF protection.

    Args:
        url: URL to validate.

    Raises:
        HttpError: If URL is blocked.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise HttpError(f"URL scheme not allowed: {parsed.scheme}", url=url)

    host = parsed.hostname or ""
    if host.lower() in BLOCKED_HOSTS:
        raise HttpError(f"Host is blocked: {host}", url=url)


class HttpClient:
    """HTTP client with retry logic.

    Usage:
        client = HttpClient(timeout=30, max_retries=3)
        response = client.get("https://example.com/puzzle.sgf")
        content = response.text
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] = None,
        base_backoff: float = 30.0,
        max_backoff: float = 240.0,
    ) -> None:
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            headers: Default headers for all requests.
            base_backoff: Base backoff duration for retries.
            max_backoff: Maximum backoff duration.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            **(headers or {}),
        }

        self._client: httpx.Client = None

    def __enter__(self) -> HttpClient:
        self._client = httpx.Client(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
        )
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            )
        return self._client

    def get(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
    ) -> httpx.Response:
        """Make GET request with retry logic.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            HTTP response.

        Raises:
            HttpError: On request failure after retries.
            RateLimitError: On rate limit (429) after retries.
        """
        validate_url(url)

        client = self._get_client()
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = client.get(url, params=params, headers=headers)

                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        backoff = calculate_backoff_with_jitter(
                            self.base_backoff,
                            attempt=attempt,
                            max_seconds=self.max_backoff,
                        )
                        logger.warning(
                            f"Rate limited (429), backing off {backoff:.1f}s "
                            f"(attempt {attempt + 1}/{self.max_retries + 1})"
                        )
                        time.sleep(backoff)
                        continue
                    raise RateLimitError(
                        f"Rate limited after {self.max_retries + 1} attempts",
                        status_code=429,
                        url=url,
                    )

                # Raise on HTTP errors
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                last_error = HttpError(
                    str(e),
                    status_code=e.response.status_code if e.response else None,
                    url=url,
                )
                if attempt < self.max_retries:
                    backoff = calculate_backoff_with_jitter(
                        self.base_backoff,
                        attempt=attempt,
                        max_seconds=self.max_backoff,
                    )
                    logger.warning(f"Request failed, retrying in {backoff:.1f}s: {e}")
                    time.sleep(backoff)

            except httpx.RequestError as e:
                last_error = HttpError(str(e), url=url)
                if attempt < self.max_retries:
                    backoff = calculate_backoff_with_jitter(
                        self.base_backoff,
                        attempt=attempt,
                        max_seconds=self.max_backoff,
                    )
                    logger.warning(f"Request error, retrying in {backoff:.1f}s: {e}")
                    time.sleep(backoff)

        raise last_error or HttpError(f"Request failed after {self.max_retries + 1} attempts", url=url)

    def get_text(self, url: str, params: dict = None, headers: dict = None) -> str:
        """Make GET request and return response text.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response text content.
        """
        response = self.get(url, params=params, headers=headers)
        return response.text

    def get_json(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Make GET request and return JSON content.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Parsed JSON data.
        """
        response = self.get(url, params=params, headers=headers)
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
