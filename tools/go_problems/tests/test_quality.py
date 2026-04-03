"""Tests for GoProblems YQ quality score computation."""

from tools.go_problems.models import GoProblemsRating
from tools.go_problems.quality import compute_quality_score, format_yq


class TestComputeQualityScore:
    """Tests for quality score algorithm."""

    def test_high_rated_canon(self):
        """High rating + canon = max quality."""
        rating = GoProblemsRating(stars=4.5, votes=20)
        score = compute_quality_score(rating, is_canon=True)
        assert score == 5  # round(4.5)=4, +1 canon bonus = 5

    def test_medium_rated_non_canon(self):
        """Medium rating without canon."""
        rating = GoProblemsRating(stars=3.0, votes=10)
        score = compute_quality_score(rating, is_canon=False)
        assert score == 3

    def test_low_rated(self):
        """Low rating stays clamped to 1."""
        rating = GoProblemsRating(stars=1.0, votes=5)
        score = compute_quality_score(rating, is_canon=False)
        assert score == 1

    def test_no_rating_returns_neutral(self):
        """No rating data defaults to neutral (2)."""
        score = compute_quality_score(None, is_canon=False)
        assert score == 2

    def test_zero_votes_returns_neutral(self):
        """Zero votes defaults to neutral even with stars."""
        rating = GoProblemsRating(stars=5.0, votes=0)
        score = compute_quality_score(rating, is_canon=False)
        assert score == 2

    def test_few_votes_capped(self):
        """Fewer than 3 votes caps at 3."""
        rating = GoProblemsRating(stars=5.0, votes=1)
        score = compute_quality_score(rating, is_canon=False)
        assert score == 3  # min(round(5.0), 3)

    def test_few_votes_low_rating(self):
        """Few votes with low stars stays low."""
        rating = GoProblemsRating(stars=1.5, votes=2)
        score = compute_quality_score(rating, is_canon=False)
        assert score == 2  # min(round(1.5), 3) = 2

    def test_canon_bonus_applied(self):
        """Canon bonus adds +1 when below 5."""
        rating = GoProblemsRating(stars=3.0, votes=5)
        score = compute_quality_score(rating, is_canon=True)
        assert score == 4  # 3 + 1 canon bonus

    def test_canon_bonus_not_above_5(self):
        """Canon bonus doesn't exceed 5."""
        rating = GoProblemsRating(stars=5.0, votes=10)
        score = compute_quality_score(rating, is_canon=True)
        assert score == 5  # Already at 5, no bonus

    def test_canon_bonus_at_4(self):
        """Canon pushes 4 to 5."""
        rating = GoProblemsRating(stars=4.0, votes=10)
        score = compute_quality_score(rating, is_canon=True)
        assert score == 5  # 4 + 1 = 5

    def test_no_rating_with_canon(self):
        """No rating but canon gets 2+1=3."""
        score = compute_quality_score(None, is_canon=True)
        assert score == 3  # 2 (neutral) + 1 (canon) = 3


class TestFormatYq:
    """Tests for YQ format string generation."""

    def test_basic_format(self):
        assert format_yq(3) == "q:3;rc:0;hc:0"

    def test_with_refutation(self):
        assert format_yq(4, refutation_count=2) == "q:4;rc:2;hc:0"

    def test_with_hints(self):
        assert format_yq(3, comment_level=2) == "q:3;rc:0;hc:2"

    def test_full(self):
        assert format_yq(5, refutation_count=3, comment_level=2) == "q:5;rc:3;hc:2"

    def test_minimum(self):
        assert format_yq(1) == "q:1;rc:0;hc:0"
