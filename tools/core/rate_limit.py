"""
Rate limiting utilities for download tools.

Provides timestamp-based rate limiting that overlaps wait time with processing,
minimizing total download time while respecting API rate limits.

How it works (plain English):
    1. Record time when you START processing (not when you finish)
    2. After processing, check: "How long since I started?"
    3. If processing took longer than min_delay, no wait needed
    4. If processing was faster, wait only the remaining time

Example:
    min_delay = 3 seconds
    processing_time = 4 seconds
    → No additional wait needed (4 > 3)

    min_delay = 3 seconds
    processing_time = 1 second
    → Wait only 2 more seconds (3 - 1 = 2)

Usage:
    from tools.core.rate_limit import RateLimiter, add_jitter

    limiter = RateLimiter(min_delay=3.0)

    for item in items:
        wait_time = limiter.wait_if_needed()  # Waits only remaining time
        fetch_and_process(item)               # Processing overlaps with next wait
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

logger = logging.getLogger("tools.core.rate_limit")


def add_jitter(delay: float, jitter_factor: float = 0.2) -> float:
    """Add jitter to a delay value.

    Randomizes delay to prevent thundering herd when multiple clients
    retry simultaneously.

    Args:
        delay: Base delay in seconds.
        jitter_factor: Randomization factor (0.2 = ±20% variation).

    Returns:
        Delay with jitter applied (always positive).

    Example:
        >>> delay = add_jitter(3.0, jitter_factor=0.2)
        >>> 2.4 <= delay <= 3.6  # ±20% of 3.0
        True
    """
    if delay <= 0:
        return 0.0

    jitter_min = 1.0 - jitter_factor
    jitter_max = 1.0 + jitter_factor
    jittered = delay * (jitter_min + random.random() * (jitter_max - jitter_min))
    return max(0.0, jittered)


class RateLimiter:
    """Timestamp-based rate limiter that overlaps wait with processing.

    Instead of waiting a fixed delay after each request, this tracks when
    the last request was made and only waits the remaining time. This means
    if your processing takes longer than the min_delay, there's no wait at all.

    Example:
        limiter = RateLimiter(min_delay=3.0, jitter_factor=0.2)

        for puzzle in puzzles:
            wait_time = limiter.wait_if_needed()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.1f}s")

            data = fetch(puzzle)     # This fetch is rate-limited
            process(data)            # Processing time counts toward next wait

    Attributes:
        min_delay: Minimum seconds between requests.
        jitter_factor: Randomization factor for delay (0.2 = ±20%).
    """

    def __init__(
        self,
        min_delay: float = 3.0,
        jitter_factor: float = 0.2,
        log_waits: bool = False,
    ) -> None:
        """Initialize rate limiter.

        Args:
            min_delay: Minimum seconds between requests.
            jitter_factor: Randomization factor (0.2 = ±20% variation).
            log_waits: If True, log wait times at DEBUG level.
        """
        self.min_delay = min_delay
        self.jitter_factor = jitter_factor
        self.log_waits = log_waits
        self._last_request_time: float = 0.0  # monotonic timestamp

    def wait_if_needed(self) -> float:
        """Wait only the remaining time since last request.

        Call this BEFORE each request.  It calculates how much time has
        passed since the previous request stamp and sleeps only the
        remainder.  Uses ``time.monotonic()`` to avoid wall-clock skew.

        Returns:
            Actual time waited in seconds (0 if no wait was needed).

        Example:
            # Processing took 4s, min_delay is 3s
            wait_time = limiter.wait_if_needed()
            # → wait_time = 0.0 (no wait needed, 4s > 3s)

            # Processing took 1s, min_delay is 3s
            wait_time = limiter.wait_if_needed()
            # → wait_time ≈ 2.0 (waited ~2s to reach 3s total)
        """
        now = time.monotonic()
        elapsed = now - self._last_request_time

        # Apply jitter to the delay
        delay_with_jitter = add_jitter(self.min_delay, self.jitter_factor)

        # Calculate remaining time (never negative)
        remaining = max(0.0, delay_with_jitter - elapsed)

        if remaining > 0:
            if self.log_waits:
                logger.debug(
                    f"Rate limit: target={delay_with_jitter:.2f}s, "
                    f"elapsed={elapsed:.2f}s, waiting={remaining:.2f}s"
                )
            time.sleep(remaining)

        # Update monotonic timestamp after wait
        self._last_request_time = time.monotonic()
        return remaining

    def reset(self) -> None:
        """Reset the rate limiter, allowing immediate next request."""
        self._last_request_time = 0.0

    @property
    def time_since_last_request(self) -> float:
        """Get seconds since last request (0 if never called)."""
        if self._last_request_time == 0:
            return 0.0
        return time.monotonic() - self._last_request_time


def wait_with_jitter(
    delay: float,
    jitter_factor: float = 0.2,
    log_func: Callable[[float], None] | None = None,
) -> float:
    """Wait for a delay with jitter applied.

    Simple function for one-off waits (not tracking timestamps).
    For repeated requests, use RateLimiter or apply_rate_limit() instead.

    Args:
        delay: Base delay in seconds.
        jitter_factor: Randomization factor (0.2 = ±20%).
        log_func: Optional callback to log the actual delay.

    Returns:
        Actual delay waited (with jitter applied).

    Example:
        # Wait approximately 3 seconds (±20%)
        actual = wait_with_jitter(3.0)
    """
    actual_delay = add_jitter(delay, jitter_factor)

    if log_func:
        log_func(actual_delay)

    if actual_delay > 0:
        time.sleep(actual_delay)

    return actual_delay


def apply_rate_limit(
    elapsed: float = 0.0,
    min_delay: float = 3.0,
    max_delay: float | None = None,
) -> float:
    """Elapsed-aware rate limiter: sleep for the *remaining* portion of the target window.

    The target inter-request delay is sampled uniformly from
    ``[min_delay, max_delay]``.  The ``elapsed`` seconds already spent on
    the current fetch cycle are subtracted so the total gap between the
    *start* of consecutive requests matches the target window.

    This is the canonical implementation of the pattern documented in
    ``docs/how-to/backend/tool-development-standards.md`` Section 10.

    Args:
        elapsed:   Seconds already spent in the current cycle, measured
                   with ``time.monotonic()`` by the caller.
        min_delay: Lower bound of the inter-request window (seconds).
        max_delay: Upper bound of the inter-request window (seconds).
                   Defaults to ``min_delay`` (fixed delay, no range).

    Returns:
        Actual seconds slept (0.0 if elapsed already exceeded the target).

    Example::

        from tools.core.rate_limit import apply_rate_limit
        import time

        for item in items:
            t_start = time.monotonic()
            try:
                result = fetch_and_process(item)
                yield result
            finally:
                apply_rate_limit(
                    elapsed=time.monotonic() - t_start,
                    min_delay=2.0,
                    max_delay=4.0,
                )
    """
    if max_delay is None:
        max_delay = min_delay

    target = random.uniform(min_delay, max_delay)
    remaining = max(0.0, target - elapsed)

    logger.debug(
        f"Rate limit: target={target:.2f}s, elapsed={elapsed:.2f}s, "
        f"waiting={remaining:.2f}s"
    )

    if remaining > 0:
        time.sleep(remaining)

    return remaining
