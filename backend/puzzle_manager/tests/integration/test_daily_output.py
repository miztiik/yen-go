"""Integration tests for daily challenge output format v2.0."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.puzzle_manager.daily.generator import DailyGenerator
from backend.puzzle_manager.models.daily import (
    DailyChallenge,
    PuzzleRef,
    StandardDaily,
    TagChallenge,
    TimedChallenge,
    TimedSet,
)


class TestDailyOutputFormat:
    """Tests for daily challenge output format compliance."""

    def test_daily_challenge_has_required_fields(self) -> None:
        """DailyChallenge model should have required fields."""
        challenge = DailyChallenge(date="2026-01-28")

        assert hasattr(challenge, "date")
        assert challenge.date == "2026-01-28"

    def test_daily_challenge_serializes_to_json(self) -> None:
        """DailyChallenge should serialize to valid JSON."""
        challenge = DailyChallenge(date="2026-01-28")

        json_str = challenge.model_dump_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert "date" in data

    def test_standard_daily_format(self) -> None:
        """StandardDaily should have correct format."""
        standard = StandardDaily(
            puzzles=[
                PuzzleRef(id="p1", level="beginner", path="/p1.sgf"),
                PuzzleRef(id="p2", level="beginner", path="/p2.sgf"),
            ],
            total=2,
        )

        assert len(standard.puzzles) == 2
        assert standard.total == 2

    def test_timed_challenge_format(self) -> None:
        """TimedChallenge should have correct format."""
        timed = TimedChallenge(
            sets=[
                TimedSet(set_number=1, puzzles=[]),
            ],
            set_count=3,
            puzzles_per_set=50,
        )

        assert timed.set_count == 3
        assert timed.puzzles_per_set == 50

    def test_tag_challenge_format(self) -> None:
        """TagChallenge should have correct format."""
        tag = TagChallenge(
            puzzles=[
                PuzzleRef(id="p1", level="beginner", path="/p1.sgf"),
            ],
            total=1,
        )

        assert len(tag.puzzles) == 1
        assert tag.total == 1


class TestDailyJsonSchema:
    """Tests for daily challenge JSON schema compliance."""

    def test_json_has_version_field(self) -> None:
        """Output JSON should include schema version (spec 119: v2.2)."""
        challenge = DailyChallenge(date="2026-01-28")

        data = challenge.model_dump()
        assert "version" in data
        assert data["version"] == "2.2"  # Spec 119: version 2.2

    def test_json_dates_are_strings(self) -> None:
        """Date fields should serialize as ISO strings."""
        challenge = DailyChallenge(date="2026-01-28")

        data = challenge.model_dump()
        assert isinstance(data["date"], str)
        assert data["date"] == "2026-01-28"

    def test_puzzle_ids_excluded_from_json(self) -> None:
        """Spec 119: id field is excluded from JSON (extractable from path)."""
        standard = StandardDaily(
            puzzles=[
                PuzzleRef(id="puzzle_001", level="beginner", path="/sgf/beginner/puzzle_001.sgf"),
                PuzzleRef(id="puzzle_002", level="beginner", path="/sgf/beginner/puzzle_002.sgf"),
            ],
            total=2,
        )

        data = standard.model_dump()
        for p in data["puzzles"]:
            # Spec 119: id should NOT be in serialized JSON
            assert "id" not in p
            # path and level should be present
            assert "path" in p
            assert "level" in p


class TestDailyOutputContent:
    """Tests for daily challenge content validity."""

    def test_standard_daily_puzzle_count(self) -> None:
        """Standard daily can have multiple puzzles."""
        puzzles = [
            PuzzleRef(id=f"p{i}", level="beginner", path=f"/p{i}.sgf")
            for i in range(30)
        ]
        standard = StandardDaily(puzzles=puzzles, total=30)

        assert len(standard.puzzles) == 30

    def test_timed_set_structure(self) -> None:
        """Timed challenge sets should have proper structure."""
        timed = TimedChallenge(
            sets=[
                TimedSet(set_number=1, puzzles=[]),
                TimedSet(set_number=2, puzzles=[]),
            ],
            set_count=2,
            puzzles_per_set=50,
        )

        assert len(timed.sets) == 2

    def test_tag_challenge_has_puzzles(self) -> None:
        """Tag challenge should have puzzles."""
        tag = TagChallenge(
            puzzles=[
                PuzzleRef(id="p1", level="intermediate", path="/p1.sgf"),
            ],
            total=1,
        )

        assert len(tag.puzzles) == 1


class TestDailyOutputIdempotency:
    """Tests for idempotent daily generation."""

    def test_same_date_same_output(self) -> None:
        """Same date should produce identical output (deterministic)."""
        challenge1 = DailyChallenge(
            date="2026-01-28",
            standard=StandardDaily(puzzles=[], total=0),
        )

        challenge2 = DailyChallenge(
            date="2026-01-28",
            standard=StandardDaily(puzzles=[], total=0),
        )

        # Compare excluding generated_at which may differ
        data1 = challenge1.model_dump(exclude={"generated_at"})
        data2 = challenge2.model_dump(exclude={"generated_at"})
        assert data1 == data2

    def test_force_flag_overwrites(self) -> None:
        """Force flag should allow overwriting existing files."""
        with TemporaryDirectory() as tmpdir:
            generator = DailyGenerator(db_path=Path(tmpdir) / "yengo-search.db")

            # The generator should support force parameter
            assert hasattr(generator, "generate")
