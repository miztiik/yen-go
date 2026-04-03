"""Tests for the local SGF parser."""

from pathlib import Path

import pytest

# Ensure tools/katago-lab is importable
_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
from core.tsumego_analysis import (
    compose_enriched_sgf,
    extract_correct_first_move,
    extract_position,
    extract_solution_tree_moves,
    parse_sgf,
)
from models.position import Color

FIXTURE_DIR = _HERE / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


class TestParseSgf:
    def test_parse_simple(self):
        sgf = "(;FF[4]GM[1]SZ[19];B[cd];W[dc])"
        root = parse_sgf(sgf)
        assert root.get("FF") == "4"
        assert root.get("SZ") == "19"
        assert len(root.children) == 1
        assert root.children[0].move is not None
        assert root.children[0].move.player == "B"
        assert root.children[0].move.sgf(root.board_size) == "cd"

    def test_parse_with_variations(self):
        sgf = "(;FF[4]GM[1]SZ[19](;B[cd](;W[dc])(;W[dd]))(;B[ce]))"
        root = parse_sgf(sgf)
        assert len(root.children) == 2  # Two variations

    def test_parse_fixture(self):
        sgf = _load_fixture("simple_life_death.sgf")
        root = parse_sgf(sgf)
        assert root.get("SZ") == "19"
        assert root.get("PL") == "B"
        # Should have AB stones
        assert len(root.get_all("AB")) > 0


class TestExtractPosition:
    def test_extract_basic(self):
        sgf = "(;FF[4]GM[1]SZ[19]PL[B]AB[cd][dd]AW[ce][de];B[cf])"
        root = parse_sgf(sgf)
        pos = extract_position(root)
        assert pos.board_size == 19
        assert pos.player_to_move == Color.BLACK
        assert len(pos.black_stones) == 2
        assert len(pos.white_stones) == 2

    def test_extract_white_to_play(self):
        sgf = "(;FF[4]GM[1]SZ[19]PL[W]AB[cd]AW[ce];W[cf])"
        root = parse_sgf(sgf)
        pos = extract_position(root)
        assert pos.player_to_move == Color.WHITE

    def test_katago_format(self):
        sgf = "(;FF[4]GM[1]SZ[19]AB[cd][dd]AW[ce];B[cf])"
        root = parse_sgf(sgf)
        pos = extract_position(root)
        stones = pos.to_katago_initial_stones()
        assert len(stones) == 3
        assert stones[0][0] == "B"  # Black stone


class TestExtractMoves:
    def test_correct_first_move(self):
        sgf = "(;FF[4]GM[1]SZ[19];B[cd];W[dc])"
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move == "cd"

    def test_solution_tree(self):
        sgf = "(;FF[4]GM[1]SZ[19];B[cd];W[dc];B[dd])"
        root = parse_sgf(sgf)
        moves = extract_solution_tree_moves(root)
        assert moves == ["cd", "dc", "dd"]

    def test_no_children(self):
        sgf = "(;FF[4]GM[1]SZ[19])"
        root = parse_sgf(sgf)
        assert extract_correct_first_move(root) is None
        assert extract_solution_tree_moves(root) == []

    def test_right_marker_in_second_variation(self):
        """When the first variation is wrong and the second has RIGHT, pick second."""
        sgf = "(;FF[4]GM[1]SZ[13]PL[B](;B[af];W[ah]C[wrong])(;B[ah];W[af];B[ae]C[RIGHT]))"
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move == "ah", f"Expected 'ah' (RIGHT-marked variation), got {move!r}"

    def test_right_marker_deep_in_subtree(self):
        """RIGHT marker can be several moves deep in the correct variation."""
        sgf = "(;FF[4]GM[1]SZ[13]PL[B](;B[ca];W[cb]C[Ko])(;B[ba];W[ca];B[db]C[RIGHT]))"
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move == "ba", f"Expected 'ba' (has RIGHT in subtree), got {move!r}"

    def test_no_right_marker_uses_first_variation(self):
        """Without RIGHT markers, the standard first-variation convention applies."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cd];W[dc])(;B[dd];W[cc]))"
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move == "cd", f"Expected 'cd' (1st variation fallback), got {move!r}"

    def test_solution_tree_follows_right_marker(self):
        """extract_solution_tree_moves follows RIGHT-marked variation."""
        sgf = "(;FF[4]GM[1]SZ[13]PL[B](;B[ca];W[cb])(;B[ba];W[ca];B[db]C[RIGHT]))"
        root = parse_sgf(sgf)
        moves = extract_solution_tree_moves(root)
        assert moves == ["ba", "ca", "db"]

    def test_solution_tree_deep_right_marker(self):
        """RIGHT marker at depth > 1 is followed by solution tree extraction."""
        # At depth 1: two variations for B. At depth 3: two sub-variations
        # where the second has RIGHT.
        sgf = "(;FF[4]GM[1]SZ[13]PL[B](;B[ba];W[ca](;B[aa])(;B[db]C[RIGHT]))(;B[af]))"
        root = parse_sgf(sgf)
        moves = extract_solution_tree_moves(root)
        # Should follow: B[ba] (1st child has RIGHT deeper) -> W[ca] -> B[db] (RIGHT)
        assert moves == ["ba", "ca", "db"]

    def test_right_marker_copyright_not_matched(self):
        """Word-boundary matching: 'copyright' should NOT trigger RIGHT detection."""
        sgf = "(;FF[4]GM[1]SZ[19](;B[cd];W[dc]C[copyright 2026])(;B[dd];W[cc]))"
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move == "cd", f"'copyright' should not match RIGHT, got {move!r}"

    def test_color_extraction_with_right_marker(self):
        """extract_correct_first_move_color picks from RIGHT-marked variation."""
        sgf = "(;FF[4]GM[1]SZ[13]PL[B](;B[af])(;W[ah];B[ae]C[RIGHT]))"
        root = parse_sgf(sgf)
        from core.tsumego_analysis import extract_correct_first_move_color
        color = extract_correct_first_move_color(root)
        assert color == Color.WHITE, f"Expected WHITE (RIGHT-marked), got {color}"

    def test_fixture_19_under_the_stones(self):
        """Real-world: puzzle #19 under_the_stones has RIGHT in 2nd variation."""
        from pathlib import Path
        fixture_path = Path(__file__).parent / "fixtures" / "perf-33" / "19_under_the_stones.sgf"
        if not fixture_path.exists():
            pytest.skip("Fixture not available")
        sgf = fixture_path.read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        # B[ah] = A6 (13x13), the correct "under the stones" move
        assert move == "ah", f"Expected 'ah' (2nd var, RIGHT), got {move!r}"

    def test_fixture_27_sacrifice(self):
        """Real-world: puzzle #27 sacrifice has RIGHT in 2nd variation."""
        from pathlib import Path
        fixture_path = Path(__file__).parent / "fixtures" / "perf-33" / "27_sacrifice.sgf"
        if not fixture_path.exists():
            pytest.skip("Fixture not available")
        sgf = fixture_path.read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        # B[ba] = B13 (13x13), the sacrifice move
        assert move == "ba", f"Expected 'ba' (2nd var, RIGHT), got {move!r}"


class TestCompose:
    def test_roundtrip(self):
        sgf = "(;FF[4]GM[1]SZ[19];B[cd];W[dc])"
        root = parse_sgf(sgf)
        result = compose_enriched_sgf(root)
        assert "(;" in result
        assert "B[cd]" in result
        assert "W[dc]" in result

    def test_with_refutations(self):
        sgf = "(;FF[4]GM[1]SZ[19];B[cd])"
        root = parse_sgf(sgf)
        refs = [
            {
                "wrong_move": "dd",
                "color": "B",
                "refutation": [("W", "dc"), ("B", "cc")],
                "comment": "Wrong. White takes the vital point.",
            }
        ]
        result = compose_enriched_sgf(root, refs)
        assert "B[dd]" in result
        assert "Wrong" in result
        assert "W[dc]" in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])


# --- Migrated from test_sprint2_fixes.py ---


@pytest.mark.unit
class TestSmallBoardFixtures:
    """G5: Verify 9×9 and 13×13 test fixtures exist and are valid SGF."""

    def test_9x9_fixture_exists(self):
        """board_9x9.sgf must exist."""
        assert (FIXTURE_DIR / "board_9x9.sgf").exists()

    def test_13x13_fixture_exists(self):
        """board_13x13.sgf must exist."""
        assert (FIXTURE_DIR / "board_13x13.sgf").exists()

    def test_9x9_fixture_parseable(self):
        """board_9x9.sgf must parse and have SZ[9]."""
        sgf = (FIXTURE_DIR / "board_9x9.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        assert root.get_property("SZ") == "9"

    def test_13x13_fixture_parseable(self):
        """board_13x13.sgf must parse and have SZ[13]."""
        sgf = (FIXTURE_DIR / "board_13x13.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        assert root.get_property("SZ") == "13"

    def test_9x9_has_correct_move(self):
        """board_9x9.sgf must have an extractable correct first move."""
        sgf = (FIXTURE_DIR / "board_9x9.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move is not None, "No correct first move in board_9x9.sgf"

    def test_13x13_has_correct_move(self):
        """board_13x13.sgf must have an extractable correct first move."""
        sgf = (FIXTURE_DIR / "board_13x13.sgf").read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        move = extract_correct_first_move(root)
        assert move is not None, "No correct first move in board_13x13.sgf"
