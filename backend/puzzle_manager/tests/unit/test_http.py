"""Tests for core HTTP utilities."""


from backend.puzzle_manager.core.http import calculate_backoff_with_jitter


class TestCalculateBackoffWithJitter:
    """Tests for calculate_backoff_with_jitter utility."""

    def test_basic_backoff_at_attempt_zero(self) -> None:
        """Attempt 0 should return approximately base_seconds with jitter."""
        base = 30.0
        result = calculate_backoff_with_jitter(base, attempt=0)

        # With default 20% jitter: 30 * 0.8 to 30 * 1.2 = 24 to 36
        assert 24.0 <= result <= 36.0

    def test_exponential_growth(self) -> None:
        """Each attempt should roughly double the backoff."""
        base = 30.0

        # Attempt 0: ~30s, Attempt 1: ~60s, Attempt 2: ~120s
        # Test without jitter to verify exponential growth
        r0 = calculate_backoff_with_jitter(base, attempt=0, jitter_factor=0)
        r1 = calculate_backoff_with_jitter(base, attempt=1, jitter_factor=0)
        r2 = calculate_backoff_with_jitter(base, attempt=2, jitter_factor=0)

        assert r0 == 30.0
        assert r1 == 60.0
        assert r2 == 120.0

    def test_max_seconds_cap(self) -> None:
        """Backoff should be capped at max_seconds."""
        base = 100.0
        max_seconds = 200.0

        # Attempt 3 would be 100 * 2^3 = 800, but should be capped at 200
        result = calculate_backoff_with_jitter(
            base,
            attempt=3,
            max_seconds=max_seconds,
            jitter_factor=0,
        )

        assert result == max_seconds

    def test_custom_multiplier(self) -> None:
        """Custom multiplier should affect growth rate."""
        base = 10.0

        # With multiplier=3: 10, 30, 90, 270
        r0 = calculate_backoff_with_jitter(base, attempt=0, multiplier=3.0, jitter_factor=0)
        r1 = calculate_backoff_with_jitter(base, attempt=1, multiplier=3.0, jitter_factor=0)
        r2 = calculate_backoff_with_jitter(base, attempt=2, multiplier=3.0, jitter_factor=0)

        assert r0 == 10.0
        assert r1 == 30.0
        assert r2 == 90.0

    def test_custom_jitter_factor(self) -> None:
        """Custom jitter_factor should affect randomization range."""
        base = 100.0

        # With 50% jitter: 100 * 0.5 to 100 * 1.5 = 50 to 150
        for _ in range(20):
            result = calculate_backoff_with_jitter(base, attempt=0, jitter_factor=0.5)
            assert 50.0 <= result <= 150.0

    def test_jitter_produces_variation(self) -> None:
        """Multiple calls should produce different values (with very high probability)."""
        base = 30.0

        results = [
            calculate_backoff_with_jitter(base, attempt=0)
            for _ in range(10)
        ]

        # All values should be different (vanishingly unlikely to get duplicates)
        unique_results = set(results)
        assert len(unique_results) >= 5  # At least 5 different values

    def test_zero_jitter_is_deterministic(self) -> None:
        """With jitter_factor=0, result should be deterministic."""
        base = 30.0

        results = [
            calculate_backoff_with_jitter(base, attempt=1, jitter_factor=0)
            for _ in range(5)
        ]

        assert all(r == 60.0 for r in results)

    def test_default_ogs_config(self) -> None:
        """Test with OGS adapter's default configuration."""
        # OGS defaults: base=30, multiplier=2, max=240
        base = 30.0
        multiplier = 2.0
        max_seconds = 240.0

        # Verify progression without jitter
        assert calculate_backoff_with_jitter(base, 0, multiplier, max_seconds, 0) == 30.0
        assert calculate_backoff_with_jitter(base, 1, multiplier, max_seconds, 0) == 60.0
        assert calculate_backoff_with_jitter(base, 2, multiplier, max_seconds, 0) == 120.0
        assert calculate_backoff_with_jitter(base, 3, multiplier, max_seconds, 0) == 240.0
        assert calculate_backoff_with_jitter(base, 4, multiplier, max_seconds, 0) == 240.0  # capped
