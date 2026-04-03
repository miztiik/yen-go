"""Unit tests for tagger module."""


from backend.puzzle_manager.core.tagger import (
    APPROVED_TAGS,
    detect_techniques,
    get_approved_tags,
)


class TestApprovedTags:
    """Tests for approved tag constants loaded from global config."""

    def test_approved_tags_is_set(self) -> None:
        """Approved tags should be a set."""
        assert isinstance(APPROVED_TAGS, set)

    def test_approved_tags_non_empty(self) -> None:
        """Approved tags should not be empty."""
        assert len(APPROVED_TAGS) > 0

    def test_common_tags_present(self) -> None:
        """Common Go technique tags should be present (from global config/tags.json)."""
        # These are the canonical tags from config/tags.json
        assert "life-and-death" in APPROVED_TAGS
        assert "ladder" in APPROVED_TAGS
        assert "snapback" in APPROVED_TAGS
        assert "ko" in APPROVED_TAGS

    def test_get_approved_tags_returns_set(self) -> None:
        """get_approved_tags() should return a set."""
        tags = get_approved_tags()
        assert isinstance(tags, set)
        assert len(tags) > 0


class TestDetectTechniques:
    """Tests for technique detection."""

    def test_returns_list(self) -> None:
        """Detection should return a list of tags."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        assert isinstance(tags, list)
        assert all(isinstance(t, str) for t in tags)

    def test_returns_sorted(self) -> None:
        """Detected tags should be sorted."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc][cd]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        assert tags == sorted(tags)

    def test_defaults_to_empty_when_no_technique(self) -> None:
        """No confident detection should return empty list (precision-over-recall)."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sgf = """(;GM[1]FF[4]SZ[9]
        PL[B]AB[cc]AW[dd]
        ;B[dc])"""
        game = parse_sgf(sgf)

        tags = detect_techniques(game)

        assert tags == []
