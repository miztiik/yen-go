"""Wayback Machine-aware HTTP crawler with local page caching.

Handles fetching from the Wayback Machine with:
- Rate limiting with jitter
- Local HTML page cache (fetch once, reuse)
- Image downloading with binary caching
- Retry logic for transient failures
- Structured event logging
"""

from __future__ import annotations

import hashlib
import random
import time
from pathlib import Path

import httpx

from tools.core.logging import EventType, StructuredLogger
from tools.minoru_harada_tsumego.config import CollectionConfig


class WaybackCrawler:
    """Rate-limited HTTP fetcher with local page/image caching."""

    def __init__(self, config: CollectionConfig, logger: StructuredLogger) -> None:
        self._config = config
        self._logger = logger
        self._client: httpx.Client | None = None
        self._last_request_time: float = 0.0

    def __enter__(self) -> WaybackCrawler:
        self._client = httpx.Client(
            timeout=self._config.request_timeout,
            follow_redirects=True,
            headers={"User-Agent": self._config.user_agent},
        )
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # --- Rate limiting ---

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        if self._last_request_time == 0.0:
            self._last_request_time = time.monotonic()
            return

        elapsed = time.monotonic() - self._last_request_time
        delay = self._config.rate_limit_seconds
        jitter = random.uniform(0, self._config.rate_limit_jitter)
        target = delay + jitter

        if elapsed < target:
            wait = target - elapsed
            self._logger.api_wait(wait, "rate_limit")
            time.sleep(wait)

        self._last_request_time = time.monotonic()

    # --- Page cache ---

    def _cache_key(self, url: str) -> str:
        """Generate deterministic cache filename from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16] + ".html"

    def _get_cached_page(self, url: str) -> str | None:
        """Check local cache for a previously fetched page."""
        cache_dir = self._config.page_cache_dir()
        cache_file = cache_dir / self._cache_key(url)
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        return None

    def _save_page_cache(self, url: str, content: str) -> Path:
        """Save fetched HTML to local cache."""
        cache_dir = self._config.page_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / self._cache_key(url)
        cache_file.write_text(content, encoding="utf-8")
        return cache_file

    def fetch_page(self, url: str, description: str = "") -> str | None:
        """Fetch an HTML page, using cache if available.

        Returns HTML content or None on failure.
        """
        # Check cache first
        cached = self._get_cached_page(url)
        if cached is not None:
            self._logger.item_skip(description or url, "cached")
            return cached

        # Fetch from web
        self._rate_limit()
        self._logger.api_request(url, description)

        if not self._client:
            raise RuntimeError("Crawler not initialized. Use 'with' context manager.")

        for attempt in range(self._config.max_retries):
            try:
                response = self._client.get(url)

                if response.status_code == 404:
                    self._logger.event(
                        EventType.ITEM_ERROR,
                        f"404 {description or url}",
                        url=url,
                        status_code=404,
                    )
                    # Cache 404 as empty to avoid refetching
                    self._save_page_cache(url, "<!-- 404 NOT FOUND -->")
                    return None

                if response.status_code == 429:
                    wait = 30 * (attempt + 1)
                    self._logger.api_wait(wait, "rate_limited_429")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                content = response.text
                self._save_page_cache(url, content)
                self._logger.event(
                    EventType.API_RESPONSE,
                    f"OK {len(content)} bytes {description}",
                    url=url,
                    size=len(content),
                )
                return content

            except httpx.TimeoutException:
                self._logger.api_error(url, f"timeout attempt {attempt + 1}")
                if attempt < self._config.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
            except httpx.HTTPStatusError as e:
                self._logger.api_error(url, str(e), e.response.status_code)
                if attempt < self._config.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
            except httpx.HTTPError as e:
                self._logger.api_error(url, str(e))
                if attempt < self._config.max_retries - 1:
                    time.sleep(5 * (attempt + 1))

        return None

    # --- Image downloading ---

    def _image_cache_path(self, year: int, filename: str) -> Path:
        """Get local path for a cached image."""
        image_dir = self._config.image_dir() / str(year)
        return image_dir / filename

    @staticmethod
    def _is_valid_image(data: bytes) -> bool:
        """Check if binary data starts with a valid image header (GIF/PNG)."""
        return data[:3] == b"GIF" or data[:4] == b"\x89PNG"

    def download_image(
        self,
        url: str,
        year: int,
        filename: str,
        description: str = "",
    ) -> tuple[bool, str, int]:
        """Download a GIF image, using cache if available.

        Returns (success, local_path, file_size).
        Validates that downloaded content is actually an image (not an
        HTML error page served with 200 status by Wayback Machine).
        """
        local_path = self._image_cache_path(year, filename)

        # Check if already downloaded AND valid image
        if local_path.exists() and local_path.stat().st_size > 0:
            with open(local_path, "rb") as f:
                header = f.read(4)
            if self._is_valid_image(header):
                size = local_path.stat().st_size
                self._logger.item_skip(description or filename, "cached")
                return True, str(local_path.relative_to(self._config.working_dir())), size
            # Corrupt file (HTML masquerading as image) — delete and re-download
            self._logger.event(
                EventType.ITEM_ERROR,
                f"Corrupt cached image (HTML), re-downloading: {filename}",
                url=url,
            )
            local_path.unlink(missing_ok=True)

        # Download
        self._rate_limit()
        self._logger.api_request(url, f"image {description or filename}")

        if not self._client:
            raise RuntimeError("Crawler not initialized. Use 'with' context manager.")

        for attempt in range(self._config.max_retries):
            try:
                response = self._client.get(url)

                if response.status_code == 404:
                    self._logger.event(
                        EventType.ITEM_ERROR,
                        f"404 image {description or filename}",
                        url=url,
                    )
                    return False, "404", 0

                if response.status_code == 429:
                    wait = 30 * (attempt + 1)
                    self._logger.api_wait(wait, "rate_limited_429")
                    time.sleep(wait)
                    continue

                response.raise_for_status()

                # Validate content is actually an image
                if not self._is_valid_image(response.content):
                    self._logger.event(
                        EventType.ITEM_ERROR,
                        f"Wayback served HTML instead of image: {filename}",
                        url=url,
                    )
                    return False, "404", 0

                # Save binary image
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(response.content)
                size = len(response.content)

                rel = str(local_path.relative_to(self._config.working_dir()))
                self._logger.event(
                    EventType.ITEM_SAVE,
                    f"IMAGE {size}B {description or filename}",
                    url=url,
                    local_path=rel,
                    size=size,
                )
                return True, rel, size

            except httpx.TimeoutException:
                self._logger.api_error(url, f"timeout attempt {attempt + 1}")
                if attempt < self._config.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
            except httpx.HTTPError as e:
                self._logger.api_error(url, str(e))
                if attempt < self._config.max_retries - 1:
                    time.sleep(5 * (attempt + 1))

        return False, "", 0
