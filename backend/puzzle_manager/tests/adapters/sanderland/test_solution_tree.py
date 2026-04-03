"""
Tests for Sanderland solution tree building with miai detection.

Spec 117: Solution Move Alternation Detection

Tests verify that:
- Single-move solutions produce sequential SGF
- Alternating solutions produce sequential SGF
- Miai solutions (same-color consecutive) produce SGF variations
- Comments are preserved in both cases
"""

import pytest

# Mark all tests in this module as adapter tests
pytestmark = pytest.mark.adapter


class TestBuildSolutionTree:
    """Test _build_solution_tree() method directly."""

    @pytest.fixture
    def adapter(self, tmp_path):
        """Create Sanderland adapter with minimal config."""
        from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter

        # Create empty collection directory
        collection_dir = tmp_path / "sanderland"
        collection_dir.mkdir()

        return SanderlandAdapter(
            source_id="sanderland",
            config={"collection_path": str(collection_dir)},
        )

    def test_single_move_returns_sequential(self, adapter):
        """Single move produces sequential SGF."""
        sol = [["B", "aa", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == ";B[aa]"

    def test_single_move_with_comment(self, adapter):
        """Single move with comment preserved."""
        sol = [["B", "aa", "Correct move"]]
        result = adapter._build_solution_tree(sol)
        assert result == ";B[aa]C[Correct move]"

    def test_alternating_bw_returns_sequential(self, adapter):
        """B-W alternating produces sequential SGF."""
        sol = [["B", "aa", ""], ["W", "bb", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == ";B[aa];W[bb]"

    def test_alternating_bwb_returns_sequential(self, adapter):
        """B-W-B alternating produces sequential SGF."""
        sol = [["B", "aa", ""], ["W", "bb", ""], ["B", "cc", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == ";B[aa];W[bb];B[cc]"

    def test_alternating_with_comments(self, adapter):
        """Alternating with comments preserved."""
        sol = [["B", "aa", "First"], ["W", "bb", "Response"], ["B", "cc", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == ";B[aa]C[First];W[bb]C[Response];B[cc]"

    def test_miai_bb_returns_variations(self, adapter):
        """B-B (miai) produces SGF variations.

        This is the critical fix from Spec 117.
        Same-color consecutive moves are alternative solutions (miai),
        not sequential moves.
        """
        sol = [["B", "oa", ""], ["B", "ra", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == "(;B[oa])(;B[ra])"

    def test_miai_bbb_returns_variations(self, adapter):
        """Three-way miai produces three variations."""
        sol = [["B", "aa", ""], ["B", "bb", ""], ["B", "cc", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == "(;B[aa])(;B[bb])(;B[cc])"

    def test_miai_ww_returns_variations(self, adapter):
        """W-W miai (white to play) produces variations."""
        sol = [["W", "aa", ""], ["W", "bb", ""]]
        result = adapter._build_solution_tree(sol)
        assert result == "(;W[aa])(;W[bb])"

    def test_miai_with_comments(self, adapter):
        """Miai with comments preserved in variations."""
        sol = [["B", "oa", "First option"], ["B", "ra", "Second option"]]
        result = adapter._build_solution_tree(sol)
        assert result == "(;B[oa]C[First option])(;B[ra]C[Second option])"

    def test_empty_sol_returns_empty(self, adapter):
        """Empty SOL returns empty string."""
        sol = []
        result = adapter._build_solution_tree(sol)
        assert result == ""

    def test_six_way_miai_puzzle_0168(self, adapter):
        """Prob0168.json: 6 possible first moves.

        Real-world test case from Sanderland collection.
        """
        sol = [
            ["B", "ab", ""], ["B", "bb", ""], ["B", "cb", ""],
            ["B", "ca", ""], ["B", "aa", ""], ["B", "ba", ""]
        ]
        result = adapter._build_solution_tree(sol)

        # Should have 6 variations
        assert result.count("(;B[") == 6
        assert "(;B[ab])" in result
        assert "(;B[bb])" in result
        assert "(;B[cb])" in result
        assert "(;B[ca])" in result
        assert "(;B[aa])" in result
        assert "(;B[ba])" in result


class TestSGFValidity:
    """Test that generated SGF is valid and parseable."""

    @pytest.fixture
    def adapter(self, tmp_path):
        """Create Sanderland adapter with minimal config."""
        from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter

        collection_dir = tmp_path / "sanderland"
        collection_dir.mkdir()

        return SanderlandAdapter(
            source_id="sanderland",
            config={"collection_path": str(collection_dir)},
        )

    def test_miai_variations_parseable(self, adapter):
        """Miai variations produce parseable SGF.

        The generated variations should be valid SGF that can be parsed.
        """
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sol = [["B", "aa", "Option A"], ["B", "bb", "Option B"]]
        variations = adapter._build_solution_tree(sol)

        # Wrap in full SGF for parsing
        full_sgf = f"(;FF[4]GM[1]SZ[9]AB[cc]AW[dd]{variations})"

        # Should parse without error
        game = parse_sgf(full_sgf)
        assert game is not None

        # Should have 2 child variations at root
        assert len(game.solution_tree.children) == 2

    def test_sequential_parseable(self, adapter):
        """Sequential moves produce parseable SGF."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf

        sol = [["B", "aa", ""], ["W", "bb", ""], ["B", "cc", ""]]
        sequence = adapter._build_solution_tree(sol)

        # Wrap in full SGF for parsing
        full_sgf = f"(;FF[4]GM[1]SZ[9]AB[dd]AW[ee]{sequence})"

        game = parse_sgf(full_sgf)
        assert game is not None

        # Should have 1 child with nested children (sequential)
        assert len(game.solution_tree.children) == 1


class TestRealWorldPuzzles:
    """Tests using real puzzle data patterns from Sanderland collection."""

    @pytest.fixture
    def adapter(self, tmp_path):
        """Create Sanderland adapter with minimal config."""
        from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter

        collection_dir = tmp_path / "sanderland"
        collection_dir.mkdir()

        return SanderlandAdapter(
            source_id="sanderland",
            config={"collection_path": str(collection_dir)},
        )

    def test_prob0009_style_miai(self, adapter):
        """Prob0009 pattern: Two-way miai for life.

        Black can play either 'ba' or 'ea' to live.
        Both are equally correct first moves.
        """
        sol = [["B", "ba", "Also lives"], ["B", "ea", "Standard tesuji"]]
        result = adapter._build_solution_tree(sol)

        assert result == "(;B[ba]C[Also lives])(;B[ea]C[Standard tesuji])"

    def test_prob0019_style_three_miai(self, adapter):
        """Prob0019 pattern: Three-way miai for life.

        Black can play 'ba', 'ea', or 'ac' to make two eyes.
        """
        sol = [
            ["B", "ba", "Eye here"],
            ["B", "ea", "Eye there"],
            ["B", "ac", "Both eyes"]
        ]
        result = adapter._build_solution_tree(sol)

        assert "(;B[ba]C[Eye here])" in result
        assert "(;B[ea]C[Eye there])" in result
        assert "(;B[ac]C[Both eyes])" in result

    def test_prob0260_exact_case(self, adapter):
        """Prob0260: The original bug case from Spec 117.

        This puzzle has [B, oa] and [B, ra] as alternative first moves.
        Previously generated invalid: ;B[oa];B[ra] (Black plays twice)
        Should generate: (;B[oa])(;B[ra]) (two variations)
        """
        sol = [["B", "oa", ""], ["B", "ra", ""]]
        result = adapter._build_solution_tree(sol)

        # MUST NOT produce sequential (Black cannot play twice in a row)
        assert ";B[oa];B[ra]" not in result

        # MUST produce variations
        assert result == "(;B[oa])(;B[ra])"
