"""
Tests for YL[] and C[] output in convert_puzzle_to_sgf.
"""

from tools.ogs.models import OGSPuzzleDetail
from tools.ogs.storage import convert_puzzle_to_sgf


def _make_puzzle_detail(**overrides) -> OGSPuzzleDetail:
    """Build a minimal OGSPuzzleDetail for SGF converter tests."""
    data = {
        "id": 999,
        "name": "Test",
        "owner": {"id": 1, "username": "tester", "country": "us"},
        "created": "2024-01-01T00:00:00Z",
        "modified": "2024-01-01T00:00:00Z",
        "puzzle": {
            "puzzle_type": "life_and_death",
            "width": 9,
            "height": 9,
            "initial_state": {"white": "aa", "black": "bb"},
            "initial_player": "black",
            "move_tree": {"x": -1, "y": -1},
            "puzzle_rank": 25,
        },
        "has_solution": True,
        **overrides,
    }
    return OGSPuzzleDetail.model_validate(data)


class TestYLProperty:
    def test_yl_present_when_slug_provided(self) -> None:
        """YL[] appears in SGF when collection_slugs is passed."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, collection_slugs=["cho-chikun-life-death-elementary"])
        assert "YL[cho-chikun-life-death-elementary]" in sgf

    def test_no_yl_when_slug_none(self) -> None:
        """YL[] is absent when collection_slugs is None."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle)
        assert "YL[" not in sgf

    def test_no_yl_when_slug_empty(self) -> None:
        """YL[] is absent when collection_slugs is empty list."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, collection_slugs=[])
        assert "YL[" not in sgf

    def test_multi_slug_yl(self) -> None:
        """YL[] contains comma-separated slugs when multiple provided."""
        puzzle = _make_puzzle_detail()
        slugs = ["alpha-collection", "beta-collection", "gamma-collection"]
        sgf = convert_puzzle_to_sgf(puzzle, collection_slugs=slugs)
        assert "YL[alpha-collection,beta-collection,gamma-collection]" in sgf

    def test_single_slug_in_list(self) -> None:
        """YL[] works with a single slug in a list."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, collection_slugs=["tesuji-training"])
        assert "YL[tesuji-training]" in sgf


class TestRootComment:
    def test_root_comment_present(self) -> None:
        """Root C[] appears when root_comment is provided."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, root_comment="life-and-death-black-kill")
        assert "C[life-and-death-black-kill]" in sgf

    def test_no_root_comment_when_none(self) -> None:
        """Root C[] is absent when root_comment is None."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle)
        # No root C[], but move C[] might exist
        # Check that there's no C[] right before the closing paren or move tree
        assert "C[life-and-death" not in sgf

    def test_root_comment_escaping(self) -> None:
        """Special SGF characters in root_comment are escaped."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, root_comment="text with ] bracket")
        assert "C[text with \\] bracket]" in sgf

    def test_root_comment_backslash_escaping(self) -> None:
        """Backslashes in root_comment are escaped."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(puzzle, root_comment="path\\to\\file")
        assert "C[path\\\\to\\\\file]" in sgf


class TestBothProperties:
    def test_yl_and_comment_coexist(self) -> None:
        """Both YL[] and C[] can appear in the same SGF."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(
            puzzle,
            collection_slugs=["tesuji-training"],
            root_comment="tesuji-black",
        )
        assert "YL[tesuji-training]" in sgf
        assert "C[tesuji-black]" in sgf

    def test_property_ordering(self) -> None:
        """YL[] appears after YT[], C[] appears after initial stones."""
        puzzle = _make_puzzle_detail()
        sgf = convert_puzzle_to_sgf(
            puzzle,
            collection_slugs=["test-collection"],
            root_comment="move-black-play",
        )
        yl_pos = sgf.index("YL[")
        c_pos = sgf.index("C[move")

        # YL should appear after YT
        if "YT[" in sgf:
            yt_pos = sgf.index("YT[")
            assert yl_pos > yt_pos, "YL[] should appear after YT[]"

        # C[] should appear after YL[]
        assert c_pos > yl_pos, "Root C[] should appear after YL[]"
