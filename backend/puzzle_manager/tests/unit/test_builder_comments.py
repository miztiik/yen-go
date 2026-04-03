"""Tests for YG preserve-first policy and SGFBuilder comment enhancements.

Steps 1, 5-6 of the analyzer enhancement plan.
"""


from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import SolutionNode


class TestBuilderCommentStandardization:
    """Tests for move comment standardization in _build_node."""

    def _build_with_single_move(
        self,
        comment: str = "",
        is_correct: bool = True,
    ) -> str:
        """Helper: build SGF with one solution move."""
        builder = SGFBuilder()
        builder.board_size = 9
        builder.player_to_move = Color.BLACK
        builder.add_black_stone(Point(2, 2))
        builder.add_white_stone(Point(3, 3))

        root = SolutionNode()
        child = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment=comment,
            is_correct=is_correct,
        )
        root.add_child(child)
        builder.solution_tree = root

        return builder.build()

    def _build_with_multiple_moves(self) -> str:
        """Helper: build SGF with multiple first-level moves."""
        builder = SGFBuilder()
        builder.board_size = 9
        builder.player_to_move = Color.BLACK
        builder.add_black_stone(Point(2, 2))
        builder.add_white_stone(Point(3, 3))

        root = SolutionNode()
        correct = SolutionNode(
            move=Point(4, 4),
            color=Color.BLACK,
            comment="",
            is_correct=True,
        )
        wrong = SolutionNode(
            move=Point(5, 5),
            color=Color.BLACK,
            comment="",
            is_correct=False,
        )
        root.add_child(correct)
        root.add_child(wrong)
        builder.solution_tree = root

        return builder.build()

    # --- Step 5: Comment standardization ---

    def test_correct_comment_standardized(self) -> None:
        sgf = self._build_with_single_move(comment="RIGHT — good tesuji", is_correct=True)
        assert "C[Correct" in sgf

    def test_wrong_comment_standardized(self) -> None:
        sgf = self._build_with_single_move(comment="Incorrect; bad move", is_correct=False)
        assert "C[Wrong" in sgf
        assert "BM[1]" in sgf

    def test_empty_correct_comment(self) -> None:
        """Single-move with no comment → auto-inferred."""
        sgf = self._build_with_single_move(comment="", is_correct=True)
        assert "C[Correct {auto-inferred}]" in sgf

    def test_empty_wrong_comment(self) -> None:
        sgf = self._build_with_single_move(comment="", is_correct=False)
        assert "C[Wrong]" in sgf

    # --- Step 6: Single-move auto-inferred ---

    def test_single_move_no_comment_auto_inferred(self) -> None:
        """Single first-level move with no comment → 'Correct {auto-inferred}'."""
        sgf = self._build_with_single_move(comment="", is_correct=True)
        assert "Correct {auto-inferred}" in sgf

    def test_single_move_existing_correct_preserved(self) -> None:
        """Single first-level move with existing 'Correct' → preserved as 'Correct'."""
        sgf = self._build_with_single_move(comment="Correct", is_correct=True)
        assert "C[Correct]" in sgf
        assert "auto-inferred" not in sgf

    def test_multiple_moves_no_auto_inference(self) -> None:
        """Multiple first-level moves → no auto-inference applied."""
        sgf = self._build_with_multiple_moves()
        assert "auto-inferred" not in sgf

    def test_single_move_bm_marker_not_overridden(self) -> None:
        """Single first-level move with BM marker → respected as wrong."""
        sgf = self._build_with_single_move(comment="", is_correct=False)
        assert "BM[1]" in sgf
        assert "auto-inferred" not in sgf

    # --- CJK stripping in output ---

    def test_cjk_stripped_from_move_comment(self) -> None:
        """CJK in move comment stripped in output."""
        sgf = self._build_with_single_move(comment="Black コウ ko", is_correct=True)
        assert "コウ" not in sgf

    def test_cjk_only_comment_becomes_label(self) -> None:
        """CJK-only comment → just the correctness label."""
        sgf = self._build_with_single_move(comment="コウ", is_correct=True)
        # After CJK stripping, comment is effectively empty
        # For single-move correct: becomes auto-inferred
        assert "Correct" in sgf
