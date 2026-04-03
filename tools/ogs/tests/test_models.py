"""
Tests for OGSPuzzleDetail model extensions (collection + puzzle_description).
"""

from tools.ogs.models import OGSPuzzleDetail


# Minimal valid puzzle data for model construction
def _make_puzzle_data(
    collection: dict | None = None,
    puzzle_description: str | None = None,
) -> dict:
    """Build minimal puzzle data dict for OGSPuzzleDetail."""
    data: dict = {
        "id": 12345,
        "name": "Test Puzzle",
        "owner": {"id": 1, "username": "test_user", "country": "us"},
        "created": "2024-01-01T00:00:00Z",
        "modified": "2024-01-01T00:00:00Z",
        "puzzle": {
            "puzzle_type": "life_and_death",
            "width": 9,
            "height": 9,
            "initial_state": {"white": "", "black": ""},
            "initial_player": "black",
            "move_tree": {"x": -1, "y": -1},
        },
        "has_solution": True,
    }
    if collection is not None:
        data["collection"] = collection
    if puzzle_description is not None:
        data["puzzle"]["puzzle_description"] = puzzle_description
    return data


class TestOGSCollection:
    def test_collection_parsed(self) -> None:
        """Collection object parsed from API response."""
        data = _make_puzzle_data(
            collection={"id": 279, "name": "Cho Chikun Elementary"}
        )
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.collection is not None
        assert puzzle.collection.id == 279
        assert puzzle.collection.name == "Cho Chikun Elementary"

    def test_collection_null(self) -> None:
        """Null/missing collection handled gracefully."""
        data = _make_puzzle_data()
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.collection is None

    def test_collection_extra_fields_ignored(self) -> None:
        """Extra fields in collection object are ignored by Pydantic."""
        data = _make_puzzle_data(
            collection={
                "id": 100,
                "name": "Test",
                "owner": {"id": 1, "username": "x"},
                "puzzle_count": 50,
                "rating": 4.5,
            }
        )
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.collection is not None
        assert puzzle.collection.id == 100
        assert puzzle.collection.name == "Test"


class TestPuzzleDescription:
    def test_description_available(self) -> None:
        """puzzle_description property returns value from nested puzzle."""
        data = _make_puzzle_data(puzzle_description="Black to kill.")
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.puzzle_description == "Black to kill."

    def test_description_none(self) -> None:
        """puzzle_description returns None when not in API response."""
        data = _make_puzzle_data()
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.puzzle_description is None

    def test_description_empty_string(self) -> None:
        """Empty string puzzle_description is preserved (not coerced to None)."""
        data = _make_puzzle_data(puzzle_description="")
        puzzle = OGSPuzzleDetail.model_validate(data)
        assert puzzle.puzzle_description == ""
