"""Tests for GoProblems Pydantic models."""

from tools.go_problems.models import (
    GoProblemsCollection,
    GoProblemsDetail,
    GoProblemsListResponse,
    GoProblemsRank,
    GoProblemsRating,
)


def test_detail_full_response():
    """Parse a fully-populated API response."""
    data = {
        "id": 42,
        "sgf": "(;FF[4]GM[1]SZ[9]AB[cc][cd]AW[dc][dd];B[bc])",
        "genre": "life and death",
        "rank": {"value": 15, "unit": "kyu"},
        "problemLevel": 10,
        "rating": {"stars": 4.2, "votes": 25},
        "isCanon": True,
        "playerColor": "black",
        "collections": [{"id": 1, "name": "Beginner Set"}],
        "source": "anonymous",
    }
    puzzle = GoProblemsDetail.model_validate(data)

    assert puzzle.id == 42
    assert puzzle.sgf.startswith("(;")
    assert puzzle.genre == "life and death"
    assert puzzle.rank is not None
    assert puzzle.rank.value == 15
    assert puzzle.rank.unit == "kyu"
    assert puzzle.rating is not None
    assert puzzle.rating.stars == 4.2
    assert puzzle.rating.votes == 25
    assert puzzle.isCanon is True
    assert puzzle.playerColor == "black"
    assert len(puzzle.collections) == 1
    assert puzzle.collections[0].name == "Beginner Set"


def test_detail_minimal_response():
    """Parse a response with only required fields."""
    data = {"id": 100, "sgf": "(;SZ[9])"}
    puzzle = GoProblemsDetail.model_validate(data)

    assert puzzle.id == 100
    assert puzzle.genre is None
    assert puzzle.rank is None
    assert puzzle.rating is None
    assert puzzle.isCanon is False
    assert puzzle.playerColor == "black"
    assert puzzle.collections is None


def test_detail_missing_sgf_defaults_empty():
    """Missing sgf field defaults to empty string."""
    data = {"id": 1}
    puzzle = GoProblemsDetail.model_validate(data)
    assert puzzle.sgf == ""


def test_rank_model():
    """Parse rank sub-model."""
    rank = GoProblemsRank.model_validate({"value": 3, "unit": "dan"})
    assert rank.value == 3
    assert rank.unit == "dan"
    assert rank.exact is False


def test_rating_model_defaults():
    """Rating defaults to 0 stars, 0 votes."""
    rating = GoProblemsRating.model_validate({})
    assert rating.stars == 0.0
    assert rating.votes == 0


def test_list_response():
    """Parse paginated list response."""
    data = {
        "count": 15000,
        "next": "https://www.goproblems.com/api/v2/problems?page=2",
        "previous": None,
        "results": [{"id": 1}, {"id": 2}, {"id": 3}],
    }
    page = GoProblemsListResponse.model_validate(data)

    assert page.count == 15000
    assert page.next is not None
    assert page.previous is None
    assert len(page.results) == 3
    assert page.results[0].id == 1


def test_list_response_empty():
    """Parse empty list response."""
    data = {"count": 0, "results": []}
    page = GoProblemsListResponse.model_validate(data)
    assert page.count == 0
    assert len(page.results) == 0


def test_collection_model():
    """Parse collection sub-model."""
    coll = GoProblemsCollection.model_validate({"id": 5, "name": "Nakade Problems"})
    assert coll.id == 5
    assert coll.name == "Nakade Problems"


def test_detail_null_player_color():
    """playerColor=null should parse without error (defaults to None)."""
    data = {"id": 7, "sgf": "(;SZ[9])", "playerColor": None}
    puzzle = GoProblemsDetail.model_validate(data)
    assert puzzle.playerColor is None


def test_detail_missing_player_color():
    """Missing playerColor should default to 'black'."""
    data = {"id": 8, "sgf": "(;SZ[9])"}
    puzzle = GoProblemsDetail.model_validate(data)
    assert puzzle.playerColor == "black"

