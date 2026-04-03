"""Tests for tools.puzzle_search — SGF file search utility."""

from __future__ import annotations

from pathlib import Path

from tools.puzzle_search import find_sgf_files

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SGF_19 = "(;FF[4]GM[1]SZ[19]C[test comment about hane]AB[dd])"
VALID_SGF_9 = "(;FF[4]GM[1]SZ[9]AB[dd])"
SGF_WITH_PROPERTY = "(;FF[4]GM[1]SZ[19]GN[puzzle-001]C[correct answer]AB[dd])"
INVALID_SGF = "this is not valid sgf content"


def _make_source_tree(tmp_path: Path) -> Path:
    """Build a minimal external-sources/ layout under tmp_path.

    Structure:
        external-sources/
            sakata-tesuji/
                sgf/
                    kiri-001.sgf   (19x19, comment with "hane")
                    push-002.sgf   (19x19, GN property)
            small-board/
                sgf/
                    tiny.sgf       (9x9, no comment)
    """
    ext = tmp_path / "external-sources"

    sakata = ext / "sakata-tesuji" / "sgf"
    sakata.mkdir(parents=True)
    (sakata / "kiri-001.sgf").write_text(VALID_SGF_19, encoding="utf-8")
    (sakata / "push-002.sgf").write_text(SGF_WITH_PROPERTY, encoding="utf-8")

    small = ext / "small-board" / "sgf"
    small.mkdir(parents=True)
    (small / "tiny.sgf").write_text(VALID_SGF_9, encoding="utf-8")

    return ext


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pattern_matching(tmp_path: Path) -> None:
    """--pattern glob filters on filename."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, pattern="kiri-*")
    assert len(results) == 1
    assert results[0].name == "kiri-001.sgf"


def test_comment_search(tmp_path: Path) -> None:
    """--comment performs case-insensitive substring search in root C[]."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, comment="HANE")
    assert len(results) == 1
    assert results[0].name == "kiri-001.sgf"


def test_board_size_filter(tmp_path: Path) -> None:
    """--board-size filters by SZ property."""
    ext = _make_source_tree(tmp_path)

    results_19 = find_sgf_files(ext, board_size=19)
    results_9 = find_sgf_files(ext, board_size=9)

    assert len(results_19) == 2  # kiri-001 + push-002
    assert len(results_9) == 1
    assert results_9[0].name == "tiny.sgf"


def test_source_filter(tmp_path: Path) -> None:
    """--source filters source directories by case-insensitive substring."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, source_filter="sakata")
    names = {r.name for r in results}
    assert names == {"kiri-001.sgf", "push-002.sgf"}

    results_small = find_sgf_files(ext, source_filter="small-board")
    assert len(results_small) == 1
    assert results_small[0].name == "tiny.sgf"


def test_empty_results(tmp_path: Path) -> None:
    """No matches returns empty list."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, pattern="nonexistent-*")
    assert results == []


def test_count_mode(tmp_path: Path) -> None:
    """find_sgf_files returns a list whose len() gives the count."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, source_filter="sakata")
    assert isinstance(len(results), int)
    assert len(results) == 2


def test_invalid_sgf_skipped(tmp_path: Path) -> None:
    """Files with broken SGF content are skipped when parsing is needed."""
    ext = _make_source_tree(tmp_path)

    # Add a broken SGF file
    broken_dir = ext / "broken-source" / "sgf"
    broken_dir.mkdir(parents=True)
    (broken_dir / "bad.sgf").write_text(INVALID_SGF, encoding="utf-8")

    # comment search requires parsing — broken file must be silently skipped
    results = find_sgf_files(ext, comment="hane")
    assert len(results) == 1
    assert results[0].name == "kiri-001.sgf"


def test_property_value_search(tmp_path: Path) -> None:
    """--property/--value matches a specific SGF property."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, property_name="GN", property_value="puzzle-001")
    assert len(results) == 1
    assert results[0].name == "push-002.sgf"


def test_property_name_only(tmp_path: Path) -> None:
    """--property without --value checks property existence."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, property_name="GN")
    # Only push-002.sgf has GN
    assert len(results) == 1
    assert results[0].name == "push-002.sgf"


def test_combined_filters(tmp_path: Path) -> None:
    """Multiple filters are ANDed together."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext, source_filter="sakata", board_size=19, pattern="kiri-*")
    assert len(results) == 1
    assert results[0].name == "kiri-001.sgf"


def test_missing_directory(tmp_path: Path) -> None:
    """Non-existent external-sources dir returns empty list."""
    results = find_sgf_files(tmp_path / "does-not-exist")
    assert results == []


def test_all_files(tmp_path: Path) -> None:
    """No filters returns all SGF files."""
    ext = _make_source_tree(tmp_path)

    results = find_sgf_files(ext)
    assert len(results) == 3
