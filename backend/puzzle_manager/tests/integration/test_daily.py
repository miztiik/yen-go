"""Integration tests for daily challenge generation."""


from backend.puzzle_manager.daily.generator import DailyGenerator
from backend.puzzle_manager.models.daily import DailyChallenge


class TestDailyGenerator:
    """Tests for DailyGenerator class."""

    def test_generator_creates_with_defaults(self, tmp_path) -> None:
        """Generator should create with default configuration."""
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")
        assert generator is not None

    def test_generator_has_generate_method(self, tmp_path) -> None:
        """Generator should have generate method."""
        generator = DailyGenerator(db_path=tmp_path / "yengo-search.db")
        assert hasattr(generator, "generate")


class TestDailyChallenge:
    """Tests for DailyChallenge model."""

    def test_daily_challenge_model(self) -> None:
        """DailyChallenge model should be importable."""
        assert DailyChallenge is not None

    def test_daily_challenge_has_date(self) -> None:
        """DailyChallenge should have date field."""
        challenge = DailyChallenge(date="2025-01-15")
        assert challenge.date == "2025-01-15"
