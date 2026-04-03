"""Tests for GoProblems SGF converter/enricher."""

from tools.go_problems.converter import (
    YENGO_SGF_VERSION,
    _extract_root_comment,
    convert_puzzle,
    enrich_sgf,
    escape_sgf_text,
)


class TestExtractRootComment:
    """Tests for root C[] extraction."""

    def test_simple_comment(self):
        sgf = '(;FF[4]C[Black to play and live]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) == "Black to play and live"

    def test_no_comment(self):
        sgf = '(;FF[4]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) is None

    def test_ignores_move_comment(self):
        """Should only extract root C[], not move C[]."""
        sgf = '(;FF[4]SZ[9];B[cc]C[Correct!])'
        assert _extract_root_comment(sgf) is None

    def test_escaped_brackets_in_comment(self):
        sgf = r'(;FF[4]C[text with \] bracket]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) == r"text with \] bracket"

    def test_comment_with_parens_in_previous_values(self):
        """C[] should still be found after TM[30:00(5x1:00)]."""
        sgf = '(;FF[4]TM[30:00(5x1:00)]C[black to live]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) == "black to live"

    def test_empty_comment(self):
        sgf = '(;FF[4]C[]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) is None

    def test_whitespace_only_comment(self):
        sgf = '(;FF[4]C[  \n  ]SZ[9];B[cc])'
        assert _extract_root_comment(sgf) is None

    def test_no_root_marker(self):
        assert _extract_root_comment("invalid") is None


class TestEscapeSgfText:
    """Tests for SGF text escaping."""

    def test_escapes_backslash(self):
        assert escape_sgf_text("a\\b") == "a\\\\b"

    def test_escapes_bracket(self):
        assert escape_sgf_text("a]b") == "a\\]b"

    def test_escapes_colon(self):
        assert escape_sgf_text("a:b") == "a\\:b"

    def test_empty_string(self):
        assert escape_sgf_text("") == ""

    def test_no_special_chars(self):
        assert escape_sgf_text("hello") == "hello"


class TestEnrichSgf:
    """Tests for SGF enrichment."""

    def test_basic_enrichment(self):
        sgf = '(;SZ[9]AB[cc]AW[dc];B[bc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=42,
            level="intermediate",
            tags=["life-and-death"],
            pl_value="B",
        )
        assert "GM[1]" in result
        assert "FF[4]" in result
        assert f"YV[{YENGO_SGF_VERSION}]" in result
        assert "YG[intermediate]" in result
        assert "YT[life-and-death]" in result
        assert "PL[B]" in result

    def test_tags_sorted_and_deduped(self):
        sgf = '(;SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=["tesuji", "life-and-death", "tesuji"],
            pl_value="B",
        )
        assert "YT[life-and-death,tesuji]" in result

    def test_collection_slugs(self):
        sgf = '(;SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=["tesuji"],
            pl_value="B",
            collection_slugs=["cho-chikun", "essential-life-and-death"],
        )
        assert "YL[cho-chikun,essential-life-and-death]" in result

    def test_yq_value(self):
        sgf = '(;SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=["tesuji"],
            pl_value="W",
            yq_value="q:4;rc:0;hc:0",
        )
        assert "YQ[q:4;rc:0;hc:0]" in result
        assert "PL[W]" in result

    def test_pl_not_duplicated_if_present(self):
        sgf = '(;SZ[9]PL[B];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
        )
        # Should not have duplicate PL[]
        assert result.count("PL[") == 1

    def test_root_comment_stripped(self):
        sgf = '(;C[Some comment]SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
        )
        assert "C[Some comment]" not in result

    def test_so_property_stripped(self):
        sgf = '(;SO[goproblems.com]SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
        )
        assert "SO[" not in result

    def test_ru_sy_dt_stripped(self):
        sgf = '(;RU[Japanese]SY[Cgoban 1.9.2]DT[1999-07-28]SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
        )
        assert "RU[" not in result
        assert "SY[" not in result
        assert "DT[" not in result
        assert "SZ[9]" in result

    def test_no_duplicate_gm_ff_ca(self):
        """Original GM/FF should be stripped (we inject canonical versions)."""
        sgf = '(;GM[1]FF[3]CA[UTF-8]SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
        )
        # Should only appear once each (our injected versions)
        assert result.count("GM[1]") == 1
        assert result.count("FF[4]") == 1
        # Original FF[3] should be gone
        assert "FF[3]" not in result

    def test_root_comment_injected(self):
        sgf = '(;SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
            root_comment="life-and-death-black-live",
        )
        assert "C[life-and-death-black-live]" in result

    def test_root_comment_replaces_original(self):
        """Original C[] stripped, resolved C[] injected."""
        sgf = '(;C[Black to play and live]SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
            root_comment="life-and-death-black-live",
        )
        assert "C[Black to play and live]" not in result
        assert "C[life-and-death-black-live]" in result

    def test_root_comment_escaping(self):
        sgf = '(;SZ[9];B[cc])'
        result = enrich_sgf(
            sgf,
            puzzle_id=1,
            level="beginner",
            tags=[],
            pl_value="B",
            root_comment="text with ] bracket",
        )
        assert r"C[text with \] bracket]" in result

    def test_real_world_sgf_with_all_properties(self):
        """Test with realistic GoProblems SGF containing all problematic properties."""
        sgf = (
            '(;GM[1]FF[3]\n'
            'RU[Japanese]SZ[19]HA[0]KM[5.5]\n'
            'PW[White]\n'
            'PB[Black]\n'
            'GN[White (W) vs. Black (B)]\n'
            'DT[1999-07-29]\n'
            'SY[Cgoban 1.9.2]TM[30:00(5x1:00)]'
            'AW[qn][ro]AB[rp][rq]'
            'C[black to live\n]\n'
            '(;B[ss];W[sp];B[sq]C[RIGHT\n])\n'
            '(;B[sp];W[sr]))'
        )
        result = enrich_sgf(
            sgf,
            puzzle_id=9,
            level="beginner",
            tags=["life-and-death"],
            pl_value="B",
            yq_value="q:5;rc:0;hc:0",
            root_comment="life-and-death-black-live",
        )
        # Stripped
        assert result.count("GM[1]") == 1
        assert "FF[3]" not in result
        assert "RU[" not in result
        assert "DT[" not in result
        assert "SY[" not in result
        assert "C[black to live" not in result
        assert "GN[" not in result
        assert "TM[" not in result
        assert "KM[" not in result
        # No empty lines
        assert "\n\n" not in result
        # Preserved
        assert "SZ[19]" in result
        assert "PW[White]" in result
        assert "AW[qn]" in result
        assert "C[RIGHT" in result  # move comment preserved
        # Injected
        assert "FF[4]" in result
        assert "YV[10]" in result
        assert "YG[beginner]" in result
        assert "YT[life-and-death]" in result
        assert "YQ[q:5;rc:0;hc:0]" in result
        assert "C[life-and-death-black-live]" in result


class TestConvertPuzzle:
    """Tests for high-level convert_puzzle function."""

    def test_successful_conversion(self):
        api_response = {
            "id": 42,
            "sgf": "(;SZ[9]AB[cc]AW[dc];B[bc])",
            "playerColor": "black",
            "rank": {"value": 15, "unit": "kyu"},
            "rating": {"stars": 4.0, "votes": 10},
            "isCanon": True,
        }
        result = convert_puzzle(
            api_response,
            puzzle_ref="goproblems-42",
            level="intermediate",
            tags=["life-and-death"],
        )
        assert result.success is True
        assert result.sgf_content is not None
        assert "YG[intermediate]" in result.sgf_content
        assert "YT[life-and-death]" in result.sgf_content

    def test_null_player_color(self):
        """playerColor=null should default to black."""
        api_response = {
            "id": 7,
            "sgf": "(;SZ[9]AB[cc]AW[dc];B[bc])",
            "playerColor": None,
        }
        result = convert_puzzle(
            api_response,
            puzzle_ref="goproblems-7",
            level="beginner",
            tags=["life-and-death"],
        )
        assert result.success is True
        assert "PL[B]" in result.sgf_content

    def test_missing_sgf_fails(self):
        api_response = {"id": 99}
        result = convert_puzzle(
            api_response,
            puzzle_ref="goproblems-99",
            level="beginner",
            tags=[],
        )
        assert result.success is False
        assert result.error is not None

    def test_invalid_sgf_format_fails(self):
        api_response = {"id": 100, "sgf": "not valid sgf"}
        result = convert_puzzle(
            api_response,
            puzzle_ref="goproblems-100",
            level="beginner",
            tags=[],
        )
        assert result.success is False

    def test_root_comment_passed_through(self):
        api_response = {
            "id": 42,
            "sgf": "(;SZ[9];B[cc])",
            "playerColor": "black",
        }
        result = convert_puzzle(
            api_response,
            puzzle_ref="goproblems-42",
            level="beginner",
            tags=[],
            root_comment="life-and-death-black-live",
        )
        assert result.success is True
        assert "C[life-and-death-black-live]" in result.sgf_content
