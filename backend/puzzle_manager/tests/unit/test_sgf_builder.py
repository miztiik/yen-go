"""
Unit tests for SGF Builder.

Tests YenGo custom property setters, especially YI (run_id).
"""


import pytest

from backend.puzzle_manager.core.primitives import Color, Point
from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import SGFGame, SolutionNode, YenGoProperties
from backend.puzzle_manager.exceptions import SGFBuildError


class TestSGFBuilderFromGame:
    """Tests for SGFBuilder.from_game() classmethod (spec-103 T006-T007)."""

    def test_from_game_basic_properties(self):
        """from_game() should copy basic game properties."""
        # Create a game with basic properties
        game = SGFGame(
            board_size=9,
            black_stones=[Point(3, 3), Point(4, 4)],
            white_stones=[Point(5, 5)],
            player_to_move=Color.WHITE,
            metadata={"GN": "Test Game"},
        )

        builder = SGFBuilder.from_game(game)

        assert builder.board_size == 9
        assert Point(3, 3) in builder.black_stones
        assert Point(4, 4) in builder.black_stones
        assert Point(5, 5) in builder.white_stones
        assert builder.player_to_move == Color.WHITE
        assert builder.metadata.get("GN") == "Test Game"

    def test_from_game_yengo_properties(self):
        """from_game() should copy YenGo properties."""
        game = SGFGame(
            board_size=19,
            yengo_props=YenGoProperties(
                level=4,
                level_slug="intermediate",
                tags=["ko", "ladder"],
                hint_texts=["Hint 1", "Hint 2"],
                version=8,
                run_id="20260130-abc12345",
                quality="q:3;rc:1",
                complexity="d:5;r:12;s:20;u:1",
                source="sanderland",
            ),
        )

        builder = SGFBuilder.from_game(game)

        assert builder.yengo_props.level == 4
        assert builder.yengo_props.level_slug == "intermediate"
        assert builder.yengo_props.tags == ["ko", "ladder"]
        assert builder.yengo_props.hint_texts == ["Hint 1", "Hint 2"]
        assert builder.yengo_props.version == 8
        assert builder.yengo_props.run_id == "20260130-abc12345"
        assert builder.yengo_props.quality == "q:3;rc:1"
        assert builder.yengo_props.complexity == "d:5;r:12;s:20;u:1"
        assert builder.yengo_props.source == "sanderland"

    def test_from_game_solution_tree(self):
        """from_game() should copy solution tree."""
        root = SolutionNode()
        child1 = SolutionNode(move=Point(3, 3), color=Color.BLACK, comment="Good!")
        child2 = SolutionNode(move=Point(4, 4), color=Color.BLACK, is_correct=False)
        root.add_child(child1)
        root.add_child(child2)

        game = SGFGame(board_size=9, solution_tree=root)

        builder = SGFBuilder.from_game(game)

        assert len(builder.solution_tree.children) == 2
        assert builder.solution_tree.children[0].move == Point(3, 3)
        assert builder.solution_tree.children[0].comment == "Good!"
        assert builder.solution_tree.children[1].is_correct is False

    def test_from_game_round_trip(self):
        """from_game() → build() should preserve all properties.

        This is the critical round-trip test: game → builder → sgf should
        contain all the original properties.
        """
        game = SGFGame(
            board_size=9,
            black_stones=[Point(3, 3)],
            white_stones=[Point(4, 4)],
            player_to_move=Color.BLACK,
            yengo_props=YenGoProperties(
                level_slug="advanced",
                tags=["life-and-death"],
                hint_texts=["Think carefully"],
                version=8,
                run_id="20260130-test1234",
                quality="q:4;rc:2",
                complexity="d:6;r:15;s:22;u:0",
            ),
        )

        builder = SGFBuilder.from_game(game)
        sgf = builder.build()

        # Verify all properties present in output
        assert "SZ[9]" in sgf
        assert "AB[" in sgf and "dd" in sgf  # Point(3,3) = dd
        assert "AW[" in sgf and "ee" in sgf  # Point(4,4) = ee
        assert "PL[B]" in sgf
        assert "YG[advanced]" in sgf
        assert "YT[life-and-death]" in sgf
        assert "YH[Think carefully]" in sgf
        assert "YV[8]" in sgf
        assert "YM[" in sgf
        assert '"i":"20260130-test1234"' in sgf
        assert "YQ[q:4;rc:2]" in sgf
        assert "YX[d:6;r:15;s:22;u:0]" in sgf

    def test_from_game_allows_modification(self):
        """from_game() builder should allow modifications."""
        game = SGFGame(
            board_size=9,
            yengo_props=YenGoProperties(tags=["original"]),
        )

        builder = SGFBuilder.from_game(game)
        builder.add_tag("added")
        builder.set_level_slug("beginner")

        sgf = builder.build()

        assert "YT[original,added]" in sgf
        assert "YG[beginner]" in sgf

    def test_from_game_empty_yengo_props(self):
        """from_game() should handle empty YenGo properties."""
        game = SGFGame(board_size=9)  # Default empty YenGoProperties

        builder = SGFBuilder.from_game(game)
        sgf = builder.build()

        # Should still produce valid SGF
        assert "(;" in sgf
        assert "SZ[9]" in sgf

    def test_from_game_lists_are_copied(self):
        """from_game() should copy lists, not share references."""
        game = SGFGame(
            board_size=9,
            black_stones=[Point(3, 3)],
            yengo_props=YenGoProperties(tags=["tag1"]),
        )

        builder = SGFBuilder.from_game(game)

        # Modify builder lists
        builder.black_stones.append(Point(5, 5))
        builder.yengo_props.tags.append("tag2")

        # Original game should be unchanged
        assert len(game.black_stones) == 1
        assert len(game.yengo_props.tags) == 1


class TestSGFBuilderYengoProperties:
    """Tests for YenGo custom property setters."""

    def test_set_run_id_new_format(self):
        """set_run_id should store date-prefixed run_id in YM JSON."""
        builder = SGFBuilder(board_size=9)
        builder.set_run_id("20260129-abc12345")

        sgf = builder.build()
        assert "YM[" in sgf
        assert '"i":"20260129-abc12345"' in sgf

    def test_set_version(self):
        """set_version should store version."""
        builder = SGFBuilder(board_size=9)
        builder.set_version(5)

        sgf = builder.build()
        assert "YV[5]" in sgf

    def test_set_level_slug(self):
        """set_level_slug should store level slug."""
        builder = SGFBuilder(board_size=9)
        builder.set_level_slug("beginner")

        sgf = builder.build()
        assert "YG[beginner]" in sgf

    def test_set_level_slug_with_sublevel(self):
        """set_level_slug should support sublevel format."""
        builder = SGFBuilder(board_size=9)
        builder.set_level_slug("intermediate", sublevel=2)

        sgf = builder.build()
        assert "YG[intermediate:2]" in sgf

    def test_set_quality(self):
        """set_quality should store quality metrics."""
        builder = SGFBuilder(board_size=9)
        builder.set_quality("q:3;rc:2;hc:1")

        sgf = builder.build()
        assert "YQ[q:3;rc:2;hc:1]" in sgf

    def test_set_complexity(self):
        """set_complexity should store complexity metrics."""
        builder = SGFBuilder(board_size=9)
        builder.set_complexity("d:5;r:13;s:24;u:1")

        sgf = builder.build()
        assert "YX[d:5;r:13;s:24;u:1]" in sgf

    def test_set_source(self):
        """set_source should store source adapter ID in memory (not in YM)."""
        builder = SGFBuilder(board_size=9)
        builder.set_source("sanderland")

        assert builder.yengo_props.source == "sanderland"
        sgf = builder.build()
        # Source is NOT embedded in YM (tracked via context.source_id)
        assert '"s":"sanderland"' not in sgf

    def test_set_source_with_hyphen(self):
        """set_source should handle source IDs with hyphens."""
        builder = SGFBuilder(board_size=9)
        builder.set_source("local-imports")

        assert builder.yengo_props.source == "local-imports"
        sgf = builder.build()
        assert '"s":"local-imports"' not in sgf

    def test_all_yengo_properties_together(self):
        """All YenGo properties should coexist."""
        builder = SGFBuilder(board_size=9)
        builder.set_version(5)
        builder.set_run_id("20260129-abc12345")
        builder.set_level_slug("advanced")
        builder.set_quality("q:4;rc:5;hc:1")
        builder.set_complexity("d:7;r:20;s:30;u:0")
        builder.add_tags(["snapback", "ladder"])

        sgf = builder.build()

        assert "YV[5]" in sgf
        assert "YM[" in sgf
        assert '"i":"20260129-abc12345"' in sgf
        assert "YG[advanced]" in sgf
        assert "YQ[q:4;rc:5;hc:1]" in sgf
        assert "YX[d:7;r:20;s:30;u:0]" in sgf
        assert "YT[snapback,ladder]" in sgf


class TestSGFBuilderBasic:
    """Tests for basic SGF builder functionality."""

    def test_empty_builder(self):
        """Empty builder should produce minimal valid SGF."""
        builder = SGFBuilder(board_size=9)
        sgf = builder.build()

        assert "(;" in sgf
        assert "FF[4]" in sgf
        assert "SZ[9]" in sgf

    def test_set_board_size(self):
        """Board size should be in output."""
        builder = SGFBuilder(board_size=19)
        sgf = builder.build()

        assert "SZ[19]" in sgf

    def test_small_board_size_accepted(self):
        """Non-standard sizes in [5, 19] should be accepted."""
        builder = SGFBuilder(board_size=5)
        sgf = builder.build()
        assert "SZ[5]" in sgf

        builder = SGFBuilder(board_size=7)
        sgf = builder.build()
        assert "SZ[7]" in sgf

    def test_invalid_board_size_rejected(self):
        """Board sizes outside [5, 19] should be rejected."""
        with pytest.raises(SGFBuildError, match="Invalid board size"):
            SGFBuilder(board_size=4)
        with pytest.raises(SGFBuildError, match="Invalid board size"):
            SGFBuilder(board_size=20)

    def test_add_black_stones(self):
        """Black stones should be added."""
        builder = SGFBuilder(board_size=9)
        builder.add_black_stones([Point(3, 3), Point(4, 4)])
        sgf = builder.build()

        # SGF uses 0-indexed coordinates, so (3,3) becomes 'dd', (4,4) becomes 'ee'
        assert "AB[" in sgf and "dd" in sgf and "ee" in sgf

    def test_add_white_stones(self):
        """White stones should be added."""
        builder = SGFBuilder(board_size=9)
        builder.add_white_stones([Point(5, 5), Point(6, 6)])
        sgf = builder.build()

        # SGF uses 0-indexed coordinates, so (5,5) becomes 'ff', (6,6) becomes 'gg'
        assert "AW[" in sgf and "ff" in sgf and "gg" in sgf

    def test_set_player_to_move(self):
        """Player to move should be set."""
        builder = SGFBuilder(board_size=9)
        builder.set_player_to_move(Color.BLACK)
        sgf = builder.build()

        assert "PL[B]" in sgf

    def test_set_level(self):
        """Level should be set (legacy integer format)."""
        builder = SGFBuilder(board_size=9)
        builder.set_level(4)
        sgf = builder.build()

        # Should have YG property
        assert "YG[" in sgf

    def test_add_tags(self):
        """Tags should be added."""
        builder = SGFBuilder(board_size=9)
        builder.add_tags(["capture", "life_death"])
        sgf = builder.build()

        assert "YT[capture,life_death]" in sgf


class TestSGFBuilderMetadata:
    """Tests for metadata handling."""

    def test_set_metadata(self):
        """Metadata should be stored (except SO which is removed in v8)."""
        builder = SGFBuilder(board_size=9)
        builder.set_metadata("GN", "Test Puzzle")
        # Note: SO property is removed in v8 (provenance stored in pipeline state)
        sgf = builder.build()

        assert "GN[Test Puzzle]" in sgf


class TestSGFBuilderHints:
    """Tests for hint handling (v8 compact format: YH[hint1|hint2|hint3])."""

    def test_add_hints_single(self):
        """Single hint should be added."""
        builder = SGFBuilder(board_size=9)
        builder.add_hints(["Focus on the corner stone"])
        sgf = builder.build()

        assert "YH[Focus on the corner stone]" in sgf

    def test_add_hints_multiple(self):
        """Multiple hints should use pipe delimiter."""
        builder = SGFBuilder(board_size=9)
        builder.add_hints(["Look for the vital point", "Consider a tesuji", "The group needs two eyes"])
        sgf = builder.build()

        # v8 format: YH[hint1|hint2|hint3]
        assert "YH[Look for the vital point|Consider a tesuji|The group needs two eyes]" in sgf

    def test_add_hints_empty(self):
        """Empty hints list should not add YH property."""
        builder = SGFBuilder(board_size=9)
        builder.add_hints([])
        sgf = builder.build()

        assert "YH[" not in sgf


class TestSGFBuilderRunIdInjection:
    """Tests for run_id serialization via YM pipeline metadata."""

    def test_run_id_new_format(self):
        """Run ID should appear in YM JSON as 'i' key."""
        builder = SGFBuilder(board_size=9)
        builder.set_run_id("20260129-abcdef12")
        sgf = builder.build()

        assert "YM[" in sgf
        assert '"i":"20260129-abcdef12"' in sgf

    def test_run_id_with_all_zeros_hex(self):
        """Run ID should accept all-zero hex part."""
        builder = SGFBuilder(board_size=9)
        builder.set_run_id("20260129-00000000")
        sgf = builder.build()

        assert "YM[" in sgf
        assert '"i":"20260129-00000000"' in sgf

    def test_run_id_lowercase(self):
        """Run ID should preserve lowercase hex in YM JSON."""
        builder = SGFBuilder(board_size=9)
        builder.set_run_id("20260129-a1b2c3d4")
        sgf = builder.build()

        # Should not uppercase
        assert '"i":"20260129-a1b2c3d4"' in sgf
        assert '"i":"20260129-A1B2C3D4"' not in sgf

    def test_run_id_optional(self):
        """Build should work without run_id."""
        builder = SGFBuilder(board_size=9)
        # Don't set run_id
        sgf = builder.build()

        # Should produce valid SGF without YI
        assert "(;" in sgf
        # YI may or may not be present depending on implementation


# ---------------------------------------------------------------------------
# Markup property serialization
# ---------------------------------------------------------------------------


class TestMarkupPropertySerialization:
    """Tests that SGF markup properties (LB, SQ, CR, MA) survive build."""

    def test_node_lb_property_serialized(self) -> None:
        """LB (label) properties on move nodes are serialized."""
        builder = SGFBuilder(board_size=9)
        root = SolutionNode()
        child = SolutionNode(
            move=Point(3, 3),
            color=Color.BLACK,
            comment="Correct!",
            is_correct=True,
            properties={"LB": "dd:1,ee:A"},
        )
        root.add_child(child)
        builder.solution_tree = root
        sgf = builder.build()
        assert "LB[dd:1][ee:A]" in sgf

    def test_node_sq_property_serialized(self) -> None:
        """SQ (square) properties on move nodes are serialized."""
        builder = SGFBuilder(board_size=9)
        root = SolutionNode()
        child = SolutionNode(
            move=Point(3, 3),
            color=Color.BLACK,
            comment="Wrong",
            is_correct=False,
            properties={"SQ": "ab,cd"},
        )
        root.add_child(child)
        builder.solution_tree = root
        sgf = builder.build()
        assert "SQ[ab][cd]" in sgf

    def test_node_cr_property_serialized(self) -> None:
        """CR (circle) properties on move nodes are serialized."""
        builder = SGFBuilder(board_size=9)
        root = SolutionNode()
        child = SolutionNode(
            move=Point(3, 3),
            color=Color.BLACK,
            is_correct=True,
            properties={"CR": "ff"},
        )
        root.add_child(child)
        builder.solution_tree = root
        sgf = builder.build()
        assert "CR[ff]" in sgf

    def test_node_ma_property_serialized(self) -> None:
        """MA (cross) properties on move nodes are serialized."""
        builder = SGFBuilder(board_size=9)
        root = SolutionNode()
        child = SolutionNode(
            move=Point(3, 3),
            color=Color.BLACK,
            is_correct=True,
            properties={"MA": "gg"},
        )
        root.add_child(child)
        builder.solution_tree = root
        sgf = builder.build()
        assert "MA[gg]" in sgf

    def test_root_metadata_markup_multi_value(self) -> None:
        """Root-level markup in metadata uses multi-value bracket format."""
        builder = SGFBuilder(board_size=9)
        builder.metadata["LB"] = "aa:1,bb:2"
        builder.metadata["TR"] = "cc,dd"
        sgf = builder.build()
        assert "LB[aa:1][bb:2]" in sgf
        assert "TR[cc][dd]" in sgf

    def test_node_without_markup(self) -> None:
        """Nodes without markup properties produce no markup output."""
        builder = SGFBuilder(board_size=9)
        root = SolutionNode()
        child = SolutionNode(
            move=Point(3, 3),
            color=Color.BLACK,
            is_correct=True,
        )
        root.add_child(child)
        builder.solution_tree = root
        sgf = builder.build()
        assert "LB" not in sgf
        assert "SQ" not in sgf
        assert "CR" not in sgf
        assert "MA" not in sgf
