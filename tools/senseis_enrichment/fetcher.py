"""HTTP fetcher for Senseis Library pages and diagram SGFs.

Handles rate limiting, User-Agent requirements, and incremental caching.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from pathlib import Path

import httpx

from tools.senseis_enrichment.config import (
    SenseisConfig,
)
from tools.senseis_enrichment.html_parser import (
    parse_problem_page,
    parse_solution_page,
)
from tools.senseis_enrichment.models import (
    SenseisDiagram,
    SenseisPageData,
    SenseisSolutionData,
)

logger = logging.getLogger("senseis_enrichment.fetcher")


class SenseisFetcher:
    """Rate-limited fetcher for Senseis Library."""

    def __init__(self, config: SenseisConfig) -> None:
        self.config = config
        self._client = httpx.Client(
            headers={"User-Agent": config.user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        self._last_request_time: float = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SenseisFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        delay = self.config.rate_limit_seconds + random.uniform(
            0, self.config.rate_limit_jitter
        )
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug("Rate limiting: sleeping %.1fs", sleep_time)
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()

    def _fetch_url(self, url: str) -> httpx.Response | None:
        """Fetch a URL with rate limiting. Returns None on 404."""
        self._rate_limit()
        logger.info("Fetching: %s", url)
        try:
            response = self._client.get(url)
            if response.status_code == 404:
                logger.info("  -> 404 Not Found")
                return None
            if response.status_code == 403:
                logger.warning("  -> 403 Forbidden (rate limited?)")
                return None
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return None

    # --- Index ---

    def fetch_index(self) -> dict[int, str]:
        """Fetch the problem index page and extract problem-to-page-name mapping.

        Returns dict of {problem_number: page_name}.
        """
        cache = self.config.index_cache_path()
        if cache.exists():
            logger.info("Loading cached index from %s", cache)
            with open(cache, encoding="utf-8") as f:
                raw = json.load(f)
            return {int(k): v for k, v in raw.items()}

        url = self.config.senseis_base_url + self.config.index_page
        response = self._fetch_url(url)
        if response is None:
            logger.error("Failed to fetch index page")
            return {}

        # Parse problem links from HTML
        # Pattern: <a href="/?PageName">N</a>
        pattern = r'<a href="/\?([^"]+)">(\d+(?:a)?)</a>'
        matches = re.findall(pattern, response.text)

        index: dict[int, str] = {}
        for page_name, number_str in matches:
            try:
                n = int(number_str)
                index[n] = page_name
            except ValueError:
                continue  # Skip "212a" etc.

        # Save cache
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in sorted(index.items())}, f, indent=2)

        logger.info("Indexed %d problems", len(index))
        return index

    # --- Problem Pages ---

    def fetch_problem_page(
        self, n: int, index: dict[int, str] | None = None
    ) -> SenseisPageData | None:
        """Fetch and parse a single problem page. Returns cached version if available."""
        cache_file = self.config.page_cache_dir() / f"{n:04d}.json"
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                return SenseisPageData.from_dict(json.load(f))

        # Determine the right URL
        if index and n in index:
            page_name = index[n]
            url = f"{self.config.senseis_base_url}/?{page_name}"
        else:
            url = self.config.problem_url(n)
            page_name = self.config.problem_page_name(n)

        response = self._fetch_url(url)
        if response is None:
            return None

        page_data = parse_problem_page(response.text, n, page_name)

        # Also fetch the problem diagram SGF if available (for position matching)
        if page_data.diagram_sgf_url:
            sgf_content = self._fetch_diagram_sgf(page_data.diagram_sgf_url)
            if sgf_content:
                # Store in the diagram cache (will be used for position matching)
                pass  # Already cached by _fetch_diagram_sgf

        # Cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(page_data.to_dict(), f, indent=2, ensure_ascii=False)

        return page_data

    # --- Solution Pages ---

    def fetch_solution_page(
        self, n: int, index: dict[int, str] | None = None
    ) -> SenseisSolutionData | None:
        """Fetch and parse a solution page including all diagram SGFs."""
        cache_file = self.config.solution_cache_dir() / f"{n:04d}.json"
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                return SenseisSolutionData.from_dict(json.load(f))

        # Determine URL
        if index and n in index:
            page_name = index[n]
            url = f"{self.config.senseis_base_url}/?{page_name}%2FSolution"
        else:
            url = self.config.solution_url(n)

        response = self._fetch_url(url)
        if response is None:
            result = SenseisSolutionData(problem_number=n, status="404")
            # Cache the 404 so we don't retry
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            return result

        solution_data = parse_solution_page(response.text, n)

        # Fetch each diagram SGF
        for diagram in solution_data.diagrams:
            if diagram.sgf_url:
                sgf_content = self._fetch_diagram_sgf(diagram.sgf_url)
                diagram.sgf_content = sgf_content or ""

        # Cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(solution_data.to_dict(), f, indent=2, ensure_ascii=False)

        return solution_data

    # --- Diagram SGFs ---

    def _fetch_diagram_sgf(self, relative_url: str) -> str | None:
        """Fetch a diagram SGF file. Caches by filename."""
        # Extract filename from URL like "diagrams/33/abc.sgf"
        filename = relative_url.replace("/", "_")
        cache_file = self.config.diagram_cache_dir() / filename
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        url = self.config.diagram_sgf_url(relative_url)
        response = self._fetch_url(url)
        if response is None:
            return None

        content = response.text
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(content, encoding="utf-8")
        return content
