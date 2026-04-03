"""Tests for OGS converter — marks_to_sgf and move_tree_to_sgf markup."""


from tools.ogs.converter import marks_to_sgf, move_tree_to_sgf
from tools.ogs.models import OGSMark, OGSMoveNode

# ---------------------------------------------------------------------------
# marks_to_sgf
# ---------------------------------------------------------------------------


class TestMarksToSgf:
    """Tests for marks_to_sgf conversion."""

    def test_empty_marks(self) -> None:
        assert marks_to_sgf([]) == ""

    def test_single_label(self) -> None:
        marks = [OGSMark(x=0, y=0, marks={"letter": "A"})]
        assert marks_to_sgf(marks) == "LB[aa:A]"

    def test_multiple_labels(self) -> None:
        marks = [
            OGSMark(x=0, y=0, marks={"letter": "1"}),
            OGSMark(x=1, y=0, marks={"letter": "2"}),
        ]
        assert marks_to_sgf(marks) == "LB[aa:1][ba:2]"

    def test_triangle(self) -> None:
        marks = [OGSMark(x=2, y=3, marks={"triangle": True})]
        assert marks_to_sgf(marks) == "TR[cd]"

    def test_square(self) -> None:
        marks = [OGSMark(x=5, y=5, marks={"square": True})]
        assert marks_to_sgf(marks) == "SQ[ff]"

    def test_circle(self) -> None:
        marks = [OGSMark(x=3, y=4, marks={"circle": True})]
        assert marks_to_sgf(marks) == "CR[de]"

    def test_cross(self) -> None:
        marks = [OGSMark(x=1, y=1, marks={"cross": True})]
        assert marks_to_sgf(marks) == "MA[bb]"

    def test_mixed_mark_types(self) -> None:
        """Multiple mark types produce combined SGF output."""
        marks = [
            OGSMark(x=0, y=0, marks={"letter": "A"}),
            OGSMark(x=1, y=1, marks={"triangle": True}),
            OGSMark(x=2, y=2, marks={"square": True}),
        ]
        result = marks_to_sgf(marks)
        assert "LB[aa:A]" in result
        assert "TR[bb]" in result
        assert "SQ[cc]" in result

    def test_combined_mark_on_same_point(self) -> None:
        """Single point with both a label and triangle."""
        marks = [OGSMark(x=0, y=0, marks={"letter": "1", "triangle": True})]
        result = marks_to_sgf(marks)
        assert "LB[aa:1]" in result
        assert "TR[aa]" in result

    def test_invalid_coordinates_skipped(self) -> None:
        """Out-of-bounds marks are silently skipped."""
        marks = [OGSMark(x=0, y=0, marks={"letter": "A"})]
        # Valid mark only
        assert marks_to_sgf(marks) == "LB[aa:A]"


# ---------------------------------------------------------------------------
# OGSMark model
# ---------------------------------------------------------------------------


class TestOGSMarkModel:
    """Tests for OGSMark Pydantic model."""

    def test_parse_letter_mark(self) -> None:
        data = {"x": 5, "y": 11, "marks": {"letter": "1"}}
        mark = OGSMark.model_validate(data)
        assert mark.x == 5
        assert mark.y == 11
        assert mark.marks["letter"] == "1"

    def test_parse_triangle_mark(self) -> None:
        data = {"x": 6, "y": 12, "marks": {"triangle": True}}
        mark = OGSMark.model_validate(data)
        assert mark.marks["triangle"] is True

    def test_parse_square_mark(self) -> None:
        data = {"x": 1, "y": 11, "marks": {"square": True}}
        mark = OGSMark.model_validate(data)
        assert mark.marks["square"] is True


# ---------------------------------------------------------------------------
# OGSMoveNode with marks
# ---------------------------------------------------------------------------


class TestOGSMoveNodeMarks:
    """Tests for marks field on OGSMoveNode."""

    def test_move_node_without_marks(self) -> None:
        """Marks default to empty list."""
        node = OGSMoveNode(x=0, y=0)
        assert node.marks == []

    def test_move_node_with_marks(self) -> None:
        """Marks parsed from API response."""
        data = {
            "x": 5,
            "y": 11,
            "marks": [
                {"x": 6, "y": 11, "marks": {"letter": "1"}},
                {"x": 5, "y": 12, "marks": {"letter": "2"}},
            ],
            "correct_answer": True,
            "text": "Correct answer",
        }
        node = OGSMoveNode.model_validate(data)
        assert len(node.marks) == 2
        assert node.marks[0].marks["letter"] == "1"
        assert node.marks[1].marks["letter"] == "2"

    def test_root_node_with_marks(self) -> None:
        """Root node (x=-1, y=-1) can have marks."""
        data = {
            "x": -1,
            "y": -1,
            "marks": [
                {"x": 1, "y": 11, "marks": {"square": True}},
                {"x": 6, "y": 11, "marks": {"letter": "1"}},
            ],
            "branches": [],
        }
        node = OGSMoveNode.model_validate(data)
        assert len(node.marks) == 2


# ---------------------------------------------------------------------------
# move_tree_to_sgf with marks
# ---------------------------------------------------------------------------


class TestMoveTreeToSgfWithMarks:
    """Tests that move_tree_to_sgf emits markup properties."""

    def test_root_marks_emitted(self) -> None:
        """Root node marks appear before first move."""
        root = OGSMoveNode(
            x=-1,
            y=-1,
            marks=[
                OGSMark(x=1, y=11, marks={"square": True}),
                OGSMark(x=6, y=11, marks={"letter": "1"}),
            ],
            branches=[
                OGSMoveNode(x=5, y=11, correct_answer=True),
            ],
        )
        result = move_tree_to_sgf(root, "B")
        assert "SQ[bl]" in result
        assert "LB[gl:1]" in result
        assert ";B[fl]" in result

    def test_leaf_node_marks_emitted(self) -> None:
        """Leaf node marks appear on the move node."""
        root = OGSMoveNode(
            x=-1,
            y=-1,
            branches=[
                OGSMoveNode(
                    x=5,
                    y=11,
                    marks=[
                        OGSMark(x=5, y=11, marks={"letter": "1"}),
                        OGSMark(x=4, y=12, marks={"letter": "2"}),
                    ],
                    correct_answer=True,
                    text="Good move",
                ),
            ],
        )
        result = move_tree_to_sgf(root, "B")
        assert ";B[fl]" in result
        assert "LB[fl:1][em:2]" in result

    def test_no_marks_no_markup(self) -> None:
        """Nodes without marks produce no markup properties."""
        root = OGSMoveNode(
            x=-1,
            y=-1,
            branches=[OGSMoveNode(x=5, y=11)],
        )
        result = move_tree_to_sgf(root, "B")
        assert "LB" not in result
        assert "TR" not in result
        assert "SQ" not in result
