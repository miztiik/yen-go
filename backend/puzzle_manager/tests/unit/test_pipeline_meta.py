"""
Tests for YM pipeline metadata round-trip through the pipeline stages.

Verifies that YM set at ingest survives through analyze and publish.
"""

from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.core.trace_utils import (
    build_pipeline_meta,
    generate_trace_id,
    parse_pipeline_meta,
)


class TestYMInSGFRoundtrip:
    """Test YM property embedding and extraction in SGF files."""

    def test_builder_sets_ym(self):
        """SGFBuilder.set_pipeline_meta() produces YM in output."""
        from backend.puzzle_manager.core.primitives import Color, Point

        builder = SGFBuilder(board_size=9)
        builder.add_black_stone(Point(3, 3))
        builder.set_player_to_move(Color.BLACK)
        builder.set_pipeline_meta("a1b2c3d4e5f67890", "puzzle.sgf")
        builder.add_solution_move(Color.BLACK, Point(4, 4))

        sgf = builder.build()
        assert 'YM[{"t":"a1b2c3d4e5f67890","f":"puzzle.sgf"}]' in sgf

    def test_parser_reads_ym(self):
        """parse_sgf() extracts YM into yengo_props.pipeline_meta."""
        sgf = '(;FF[4]GM[1]SZ[9]PL[B]YM[{"t":"a1b2c3d4e5f67890","f":"puzzle.sgf"}]AB[dd];B[ee])'
        game = parse_sgf(sgf)
        assert game.yengo_props.pipeline_meta == '{"t":"a1b2c3d4e5f67890","f":"puzzle.sgf"}'

    def test_ym_round_trip_through_builder(self):
        """YM survives parse → from_game → build round-trip."""
        original = '(;FF[4]GM[1]SZ[9]PL[B]YM[{"t":"fedcba9876543210","f":"test.sgf"}]AB[dd];B[ee])'
        game = parse_sgf(original)

        # Rebuild via SGFBuilder
        rebuilt = SGFBuilder.from_game(game).build()

        # Re-parse to verify
        game2 = parse_sgf(rebuilt)
        trace_id, filename, source, run_id = parse_pipeline_meta(game2.yengo_props.pipeline_meta)
        assert trace_id == "fedcba9876543210"
        assert filename == "test.sgf"

    def test_ym_without_filename(self):
        """YM with only trace_id (no filename) survives round-trip."""
        meta = build_pipeline_meta("abcdef0123456789")
        sgf = f'(;FF[4]GM[1]SZ[9]PL[B]YM[{meta}]AB[dd];B[ee])'
        game = parse_sgf(sgf)
        trace_id, filename, source, run_id = parse_pipeline_meta(game.yengo_props.pipeline_meta)
        assert trace_id == "abcdef0123456789"
        assert filename == ""

    def test_missing_ym_returns_none(self):
        """SGF without YM property has pipeline_meta = None."""
        sgf = "(;FF[4]GM[1]SZ[9]PL[B]AB[dd];B[ee])"
        game = parse_sgf(sgf)
        assert game.yengo_props.pipeline_meta is None

    def test_ym_preserved_alongside_other_props(self):
        """YM coexists with other YenGo properties."""
        sgf = (
            '(;FF[4]GM[1]SZ[9]PL[B]'
            'YV[12]YG[beginner]YT[life-and-death]'
            'YQ[q:2;rc:0;hc:0]YX[d:1;r:2;s:5;u:1]'
            'YM[{"t":"1234567890abcdef"}]'
            'AB[dd];B[ee])'
        )
        game = parse_sgf(sgf)
        assert game.yengo_props.version == 12
        assert game.yengo_props.level_slug == "beginner"
        assert game.yengo_props.tags == ["life-and-death"]
        assert game.yengo_props.pipeline_meta == '{"t":"1234567890abcdef"}'

    def test_ym_sgf_escaping(self):
        """YM value with SGF-special chars is properly escaped."""
        # Filenames rarely contain ] but we test defensively
        builder = SGFBuilder(board_size=9)
        from backend.puzzle_manager.core.primitives import Color, Point
        builder.add_black_stone(Point(3, 3))
        builder.set_player_to_move(Color.BLACK)
        builder.set_pipeline_meta("a1b2c3d4e5f67890", "file]name.sgf")
        builder.add_solution_move(Color.BLACK, Point(4, 4))

        sgf = builder.build()
        # Should not break SGF parsing
        game = parse_sgf(sgf)
        trace_id, filename, source, run_id = parse_pipeline_meta(game.yengo_props.pipeline_meta)
        assert trace_id == "a1b2c3d4e5f67890"
        assert filename == "file]name.sgf"

    def test_generate_trace_id_format(self):
        """generate_trace_id() produces 16-char hex strings."""
        tid = generate_trace_id()
        assert len(tid) == 16
        assert all(c in "0123456789abcdef" for c in tid)

    def test_f_stripped_at_publish_rebuild(self):
        """Simulates publish behavior: rebuild YM without f (original_filename).

        At publish, f is extracted for the publish log then stripped from YM.
        The published SGF should contain only t and i (no f).
        """
        # Pre-publish YM (set at ingest, has f)
        ingest_ym = build_pipeline_meta("a1b2c3d4e5f67890", "puzzle_42.sgf")
        assert '"f":"puzzle_42.sgf"' in ingest_ym

        # Parse as publish stage does
        trace_id, original_filename, _, _ = parse_pipeline_meta(ingest_ym)
        assert original_filename == "puzzle_42.sgf"

        # Rebuild without f (publish strips it, adds run_id)
        publish_ym = build_pipeline_meta(trace_id, original_filename="", run_id="20260222-abc12345")
        assert '"t":"a1b2c3d4e5f67890"' in publish_ym
        assert '"i":"20260222-abc12345"' in publish_ym
        assert '"f"' not in publish_ym  # f must be stripped

    def test_f_stripped_round_trip_through_sgf(self):
        """YM with f at ingest → rebuild without f → published SGF has no f."""
        from backend.puzzle_manager.core.primitives import Color, Point

        # Ingest: build SGF with f in YM
        builder = SGFBuilder(board_size=9)
        builder.add_black_stone(Point(3, 3))
        builder.set_player_to_move(Color.BLACK)
        builder.set_pipeline_meta("fedcba9876543210", "source_file.sgf")
        builder.add_solution_move(Color.BLACK, Point(4, 4))
        sgf = builder.build()
        assert '"f":"source_file.sgf"' in sgf

        # Publish: parse, strip f, rebuild
        game = parse_sgf(sgf)
        trace_id, original_filename, _, _ = parse_pipeline_meta(game.yengo_props.pipeline_meta)
        assert original_filename == "source_file.sgf"

        # Rebuild YM without f (as publish stage does)
        game.yengo_props.pipeline_meta = build_pipeline_meta(
            trace_id, original_filename="", run_id="20260222-test1234"
        )
        rebuilt = SGFBuilder.from_game(game).build()

        # Verify published SGF has no f
        game2 = parse_sgf(rebuilt)
        trace_id2, filename2, _, run_id2 = parse_pipeline_meta(game2.yengo_props.pipeline_meta)
        assert trace_id2 == "fedcba9876543210"
        assert filename2 == ""  # f is stripped
        assert run_id2 == "20260222-test1234"
        assert '"f"' not in game2.yengo_props.pipeline_meta
