"""
HTTP client with retry and rate limiting.

Uses httpx for async-capable requests and tenacity for retries.
"""

import logging
import random
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.puzzle_manager.exceptions import FetchError

logger = logging.getLogger("puzzle_manager.http")


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
        attempt: Retry attempt number (0-indexed). Each attempt multiplies the backoff.
        multiplier: Factor to multiply backoff by each attempt.
        max_seconds: Maximum backoff duration cap.
        jitter_factor: Randomization factor (0.2 = ±20% variation).

    Returns:
        Backoff duration in seconds with jitter applied.

    Example:
        >>> # First retry: ~30s (±20%)
        >>> backoff = calculate_backoff_with_jitter(30.0, attempt=0)
        >>> # Second retry: ~60s (±20%)
        >>> backoff = calculate_backoff_with_jitter(30.0, attempt=1)
        >>> # With custom jitter
        >>> backoff = calculate_backoff_with_jitter(30.0, attempt=2, jitter_factor=0.3)
    """
    # Calculate base exponential backoff
    backoff = base_seconds * (multiplier ** attempt)

    # Apply cap
    backoff = min(backoff, max_seconds)

    # Apply jitter: randomize within ±jitter_factor range
    # e.g., jitter_factor=0.2 means 0.8 to 1.2 multiplier
    jitter_min = 1.0 - jitter_factor
    jitter_max = 1.0 + jitter_factor
    jittered_backoff = backoff * (jitter_min + random.random() * (jitter_max - jitter_min))

    return jittered_backoff


# SSRF protection - blocked hosts
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
}

# SSRF protection - blocked schemes
ALLOWED_SCHEMES = {"http", "https"}


class HttpClient:
    """HTTP client with retry logic and SSRF protection.

    Usage:
        client = HttpClient(timeout=30, max_retries=3)
        response = client.get("https://example.com/puzzle.sgf")
        content = response.text
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            headers: Default headers to include in requests.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = headers or {}
        self._client: httpx.Client | None = None

    def __enter__(self) -> "HttpClient":
        """Enter context manager."""
        self._client = httpx.Client(
            timeout=self.timeout,
            headers=self.default_headers,
            follow_redirects=True,
        )
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager."""
        if self._client:
            self._client.close()
            self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers=self.default_headers,
                follow_redirects=True,
            )
        return self._client

    def _validate_url(self, url: str) -> None:
        """Validate URL for SSRF protection.

        Args:
            url: URL to validate.

        Raises:
            FetchError: If URL is blocked.
        """
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise FetchError(
                f"Invalid URL scheme: {parsed.scheme}",
                context={"url": url},
            )

        # Check host
        host = parsed.hostname or ""
        if host.lower() in BLOCKED_HOSTS:
            raise FetchError(
                f"Blocked host: {host}",
                context={"url": url},
            )

        # Check for private IP ranges (basic check)
        if host.startswith("10.") or host.startswith("192.168."):
            raise FetchError(
                f"Private IP address blocked: {host}",
                context={"url": url},
            )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make request with retry logic."""
        client = self._get_client()
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make GET request.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response object.

        Raises:
            FetchError: If request fails.
        """
        self._validate_url(url)

        try:
            return self._request_with_retry("GET", url, params=params, headers=headers)
        except httpx.HTTPStatusError as e:
            raise FetchError(
                f"HTTP error {e.response.status_code}: {url}",
                context={"url": url, "status_code": e.response.status_code},
            ) from e
        except httpx.TimeoutException as e:
            raise FetchError(
                f"Request timeout: {url}",
                context={"url": url, "timeout": self.timeout},
            ) from e
        except httpx.NetworkError as e:
            raise FetchError(
                f"Network error: {url}",
                context={"url": url, "error": str(e)},
            ) from e
        except Exception as e:
            raise FetchError(
                f"Request failed: {url}",
                context={"url": url, "error": str(e)},
            ) from e

    def get_text(self, url: str, **kwargs: Any) -> str:
        """Make GET request and return text content.

        Args:
            url: Request URL.
            **kwargs: Additional arguments for get().

        Returns:
            Response text.
        """
        response = self.get(url, **kwargs)
        return response.text

    def get_json(self, url: str, **kwargs: Any) -> Any:
        """Make GET request and return JSON content.

        Args:
            url: Request URL.
            **kwargs: Additional arguments for get().

        Returns:
            Parsed JSON data.
        """
        response = self.get(url, **kwargs)
        return response.json()

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make POST request.

        Args:
            url: Request URL.
            data: Form data.
            json: JSON body.
            headers: Additional headers.

        Returns:
            Response object.

        Raises:
            FetchError: If request fails.
        """
        self._validate_url(url)

        try:
            return self._request_with_retry(
                "POST", url, data=data, json=json, headers=headers
            )
        except httpx.HTTPStatusError as e:
            raise FetchError(
                f"HTTP error {e.response.status_code}: {url}",
                context={"url": url, "status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise FetchError(
                f"Request failed: {url}",
                context={"url": url, "error": str(e)},
            ) from e

    def close(self) -> None:
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None
