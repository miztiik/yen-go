"""Tests for tools.core.collection_embedder."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.core.collection_embedder import (
    BACKUP_SUFFIX,
    CHECKPOINT_FILENAME,
    EmbedResult,
    EmbedSummary,
    FilenamePatternStrategy,
    ManifestLookupStrategy,
    PhraseMatchStrategy,
    _extract_slug,
    _format_yl,
    embed_collections,
    restore_backups,
)
from tools.core.collection_matcher import CollectionMatcher
from tools.core.sgf_parser import parse_sgf

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SGF = (
    "(;SZ[19]FF[4]GM[1]PL[B]"
    "AB[dp][pp]AW[dd][pd]"
    ";B[cc])"
)

SGF_WITH_YL = (
    "(;SZ[19]FF[4]GM[1]PL[B]"
    "YL[some-collection:0/1]"
    "AB[dp][pp]AW[dd][pd]"
    ";B[cc])"
)


def _make_sgf_with_yl(slug: str, chapter: int = 0, position: int = 1) -> str:
    return (
        f"(;SZ[19]FF[4]GM[1]PL[B]"
        f"YL[{slug}:{chapter}/{position}]"
        f"AB[dp][pp]AW[dd][pd]"
        f";B[cc])"
    )


def _mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.event = MagicMock()
    return logger


@pytest.fixture
def matcher() -> CollectionMatcher:
    """Real matcher but with local overrides for predictable results."""
    return CollectionMatcher(
        local_overrides={
            "cho chikun life and death elementary": "cho-chikun-life-death-elementary",
            "test-collection": "test-collection",
            "another-collection": "another-collection",
        }
    )


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    """Create a source directory with SGF sub-directories."""
    # Directory 1: matches a known collection
    d1 = tmp_path / "test-collection"
    d1.mkdir()
    (d1 / "puzzle_001.sgf").write_text(MINIMAL_SGF, encoding="utf-8")
    (d1 / "puzzle_002.sgf").write_text(MINIMAL_SGF, encoding="utf-8")
    (d1 / "puzzle_003.sgf").write_text(MINIMAL_SGF, encoding="utf-8")

    # Directory 2: no match
    d2 = tmp_path / "unknown-stuff"
    d2.mkdir()
    (d2 / "puzzle_001.sgf").write_text(MINIMAL_SGF, encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestFormatYl:
    def test_basic(self):
        r = EmbedResult(slug="my-coll", chapter=0, position=42)
        assert _format_yl(r) == "my-coll:0/42"

    def test_with_chapter(self):
        r = EmbedResult(slug="x", chapter=3, position=12)
        assert _format_yl(r) == "x:3/12"


class TestExtractSlug:
    def test_with_chapter_position(self):
        assert _extract_slug("cho-chikun:3/12") == "cho-chikun"

    def test_plain_slug(self):
        assert _extract_slug("cho-chikun") == "cho-chikun"

    def test_zero_chapter(self):
        assert _extract_slug("test:0/1") == "test"


# ---------------------------------------------------------------------------
# Unit tests: EmbedSummary
# ---------------------------------------------------------------------------


class TestEmbedSummary:
    def test_coverage_pct_no_files(self):
        s = EmbedSummary()
        assert s.coverage_pct == 0.0

    def test_coverage_pct(self):
        s = EmbedSummary(total_files=10, embedded=3, already_embedded=5)
        assert s.coverage_pct == pytest.approx(80.0)

    def test_coverage_pct_includes_updated(self):
        s = EmbedSummary(total_files=10, embedded=2, updated=3, already_embedded=4)
        assert s.coverage_pct == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# Unit tests: PhraseMatchStrategy
# ---------------------------------------------------------------------------


class TestPhraseMatchStrategy:
    def test_resolve_match(self, matcher: CollectionMatcher):
        strategy = PhraseMatchStrategy(matcher)
        d = Path("/fake/test-collection")
        strategy.prime_directory(d, ["a.sgf", "b.sgf", "c.sgf"])

        result = strategy.resolve(d / "b.sgf", "test-collection", "b.sgf")
        assert result is not None
        assert result.slug == "test-collection"
        assert result.chapter == 0
        assert result.position == 2  # b.sgf is 2nd when sorted (a, b, c)

    def test_resolve_no_match(self, matcher: CollectionMatcher):
        strategy = PhraseMatchStrategy(matcher)
        d = Path("/fake/xyzzy-no-match-ever")
        strategy.prime_directory(d, ["a.sgf"])

        result = strategy.resolve(d / "a.sgf", "xyzzy-no-match-ever", "a.sgf")
        assert result is None

    def test_position_order(self, matcher: CollectionMatcher):
        strategy = PhraseMatchStrategy(matcher)
        d = Path("/fake/test-collection")
        strategy.prime_directory(d, ["z.sgf", "a.sgf", "m.sgf"])

        r1 = strategy.resolve(d / "a.sgf", "test-collection", "a.sgf")
        r2 = strategy.resolve(d / "m.sgf", "test-collection", "m.sgf")
        r3 = strategy.resolve(d / "z.sgf", "test-collection", "z.sgf")
        assert r1 and r1.position == 1
        assert r2 and r2.position == 2
        assert r3 and r3.position == 3


# ---------------------------------------------------------------------------
# Integration: embed_collections
# ---------------------------------------------------------------------------


class TestEmbedCollections:
    def test_no_yl_added_correctly(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """SGF with no YL → YL added correctly."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        # 3 files in test-collection should be embedded
        assert summary.embedded == 3
        # 1 file in unknown-stuff should be skipped (strategy returns None)
        assert summary.skipped == 1
        assert summary.total_files == 4

        # Verify YL was written
        sgf1 = (source_dir / "test-collection" / "puzzle_001.sgf").read_text(
            encoding="utf-8"
        )
        tree = parse_sgf(sgf1)
        assert len(tree.yengo_props.collections) == 1
        assert tree.yengo_props.collections[0] == "test-collection:0/1"

    def test_idempotent_same_slug(self, source_dir: Path, matcher: CollectionMatcher):
        """SGF with identical YL value → skipped (idempotent)."""
        # Pre-embed with the exact same slug:chapter/position that phrase-match would produce
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        sgf_path.write_text(
            _make_sgf_with_yl("test-collection", 0, 1), encoding="utf-8"
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        assert summary.already_embedded == 1
        # Other 2 in test-collection embedded, 1 in unknown skipped
        assert summary.embedded == 2

    def test_update_slug_only_yl(self, source_dir: Path, matcher: CollectionMatcher):
        """SGF with slug-only YL (no chapter/position) → updated with chapter/position."""
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        # Write slug-only YL (missing :chapter/position)
        sgf_path.write_text(
            "(;SZ[19]FF[4]GM[1]PL[B]"
            "YL[test-collection]"
            "AB[dp][pp]AW[dd][pd]"
            ";B[cc])",
            encoding="utf-8",
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        # puzzle_001 should be updated (slug matches, but value differs)
        assert summary.updated == 1
        assert summary.embedded == 2  # puzzle_002 and puzzle_003
        assert summary.already_embedded == 0

        # Verify the file now has full chapter/position
        tree = parse_sgf(sgf_path.read_text(encoding="utf-8"))
        assert tree.yengo_props.collections[0] == "test-collection:0/1"

    def test_update_stale_position(self, source_dir: Path, matcher: CollectionMatcher):
        """SGF with same slug but wrong position → updated."""
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        # Write with stale position (99 instead of correct 1)
        sgf_path.write_text(
            _make_sgf_with_yl("test-collection", 0, 99), encoding="utf-8"
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        assert summary.updated == 1
        assert summary.already_embedded == 0

        tree = parse_sgf(sgf_path.read_text(encoding="utf-8"))
        assert tree.yengo_props.collections[0] == "test-collection:0/1"

    def test_update_dry_run_no_writes(self, source_dir: Path, matcher: CollectionMatcher):
        """Dry-run update reports but does not write."""
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        sgf_path.write_text(
            _make_sgf_with_yl("test-collection", 0, 99), encoding="utf-8"
        )
        original_content = sgf_path.read_text(encoding="utf-8")

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger, dry_run=True)

        assert summary.updated == 1
        # File should be unchanged
        assert sgf_path.read_text(encoding="utf-8") == original_content

    def test_conflict_different_slug(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """SGF with different-slug YL → warned+skipped (conflict)."""
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        sgf_path.write_text(
            _make_sgf_with_yl("different-slug", 0, 1), encoding="utf-8"
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        assert summary.conflicts == 1
        assert summary.embedded == 2

    def test_dry_run_no_writes(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Dry-run mode: no file writes."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        original_content = (
            source_dir / "test-collection" / "puzzle_001.sgf"
        ).read_text(encoding="utf-8")

        summary = embed_collections(
            source_dir, strategy, matcher, logger, dry_run=True
        )

        assert summary.embedded == 3  # counted but not written

        after_content = (
            source_dir / "test-collection" / "puzzle_001.sgf"
        ).read_text(encoding="utf-8")
        assert after_content == original_content

        # No backup files should exist
        backups = list(source_dir.rglob(f"*{BACKUP_SUFFIX}"))
        assert len(backups) == 0

    def test_backup_files_created(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Backup files created on write."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        embed_collections(source_dir, strategy, matcher, logger)

        backups = list(
            (source_dir / "test-collection").glob(f"*{BACKUP_SUFFIX}")
        )
        assert len(backups) == 3

    def test_checkpoint_written_per_directory(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Checkpoint written per directory."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        embed_collections(source_dir, strategy, matcher, logger)

        cp_path = source_dir / CHECKPOINT_FILENAME
        assert cp_path.exists()

        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert "completed_dirs" in data
        assert len(data["completed_dirs"]) >= 1

    def test_checkpoint_resume_skips_completed(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Checkpoint resume: skips already-processed dirs."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        # Run once to completion
        embed_collections(source_dir, strategy, matcher, logger)

        # Record what's there after first run
        list(
            source_dir.rglob(f"*{BACKUP_SUFFIX}")
        )

        # Run again — should skip all (checkpoint present)
        logger2 = _mock_logger()
        summary2 = embed_collections(source_dir, strategy, matcher, logger2)

        assert summary2.embedded == 0
        assert summary2.total_files == 0  # Dirs skipped entirely

    def test_embed_summary_fields(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """EmbedSummary fields populated correctly."""
        # Set up a mix: one conflict, one already_embedded, rest fresh
        (source_dir / "test-collection" / "puzzle_001.sgf").write_text(
            _make_sgf_with_yl("test-collection", 0, 1), encoding="utf-8"
        )
        (source_dir / "test-collection" / "puzzle_002.sgf").write_text(
            _make_sgf_with_yl("other-slug", 0, 1), encoding="utf-8"
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        summary = embed_collections(source_dir, strategy, matcher, logger)

        assert summary.already_embedded == 1
        assert summary.conflicts == 1
        assert summary.embedded == 1
        assert summary.updated == 0
        assert summary.skipped == 1  # unknown-stuff dir
        assert summary.total_files == 4
        assert summary.errors == 0

    def test_directory_start_end_logged(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Directory start and end events are logged."""
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        embed_collections(source_dir, strategy, matcher, logger)

        event_names = [call.args[0] for call in logger.event.call_args_list]
        # Both dirs should have folder_start + folder_done
        assert event_names.count("folder_start") == 2
        assert event_names.count("folder_done") == 2

    def test_already_embedded_logged_per_file(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Already-embedded files emit per-file collection_skip events."""
        sgf_path = source_dir / "test-collection" / "puzzle_001.sgf"
        sgf_path.write_text(
            _make_sgf_with_yl("test-collection", 0, 1), encoding="utf-8"
        )

        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()

        embed_collections(source_dir, strategy, matcher, logger)

        skip_events = [
            call for call in logger.event.call_args_list
            if call.args[0] == "collection_skip"
        ]
        assert len(skip_events) == 1
        assert "puzzle_001.sgf" in skip_events[0].args[1]


# ---------------------------------------------------------------------------
# Restore backups
# ---------------------------------------------------------------------------


class TestRestoreBackups:
    def test_restore_reverses_modifications(
        self, source_dir: Path, matcher: CollectionMatcher
    ):
        """Restore-backups reverses modifications."""
        # Save original content
        original = (
            source_dir / "test-collection" / "puzzle_001.sgf"
        ).read_text(encoding="utf-8")

        # Embed
        strategy = PhraseMatchStrategy(matcher)
        logger = _mock_logger()
        embed_collections(source_dir, strategy, matcher, logger)

        # Content is now different
        modified = (
            source_dir / "test-collection" / "puzzle_001.sgf"
        ).read_text(encoding="utf-8")
        assert modified != original

        # Restore
        restored_count = restore_backups(source_dir, logger)
        assert restored_count == 3

        # Content is back to original
        after = (
            source_dir / "test-collection" / "puzzle_001.sgf"
        ).read_text(encoding="utf-8")
        assert after == original

        # Backup files removed
        backups = list(source_dir.rglob(f"*{BACKUP_SUFFIX}"))
        assert len(backups) == 0

        # Checkpoint removed
        assert not (source_dir / CHECKPOINT_FILENAME).exists()


# ---------------------------------------------------------------------------
# Unit tests: ManifestLookupStrategy (Strategy B)
# ---------------------------------------------------------------------------

_JSONL_METADATA = json.dumps({
    "type": "metadata",
    "extracted_at": "2026-02-11T00:00:00Z",
    "total_collections": 2,
})

_JSONL_COLLECTION_A = json.dumps({
    "id": 1329,
    "name": "test-collection",
    "puzzles": [10600, 10601, 10602],
    "type": "collection",
})

_JSONL_COLLECTION_B = json.dumps({
    "id": 279,
    "name": "another-collection",
    "puzzles": [2824, 2826, 10600],  # 10600 duplicated — first wins
    "type": "collection",
})


@pytest.fixture
def jsonl_path(tmp_path: Path) -> Path:
    """Create a test JSONL manifest."""
    p = tmp_path / "collections-sorted.jsonl"
    p.write_text(
        "\n".join([_JSONL_METADATA, _JSONL_COLLECTION_A, _JSONL_COLLECTION_B]),
        encoding="utf-8",
    )
    return p


class TestManifestLookupStrategy:
    def test_parse_builds_reverse_index(
        self, jsonl_path: Path, matcher: CollectionMatcher
    ):
        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        # 3 from A + 2 unique from B (10600 already in A)
        assert strategy.index_size == 5

    def test_resolve_known_puzzle(
        self, jsonl_path: Path, matcher: CollectionMatcher
    ):
        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        sgf = Path("/fake/batch-001/ogs-10601.sgf")
        result = strategy.resolve(sgf, "batch-001", "ogs-10601.sgf")
        assert result is not None
        assert result.slug == "test-collection"
        assert result.chapter == 0
        assert result.position == 2  # 0-based index 1 → 1-based 2

    def test_resolve_first_in_array(
        self, jsonl_path: Path, matcher: CollectionMatcher
    ):
        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        sgf = Path("/fake/batch-001/ogs-10600.sgf")
        result = strategy.resolve(sgf, "batch-001", "ogs-10600.sgf")
        assert result is not None
        assert result.position == 1  # first in array = position 1
        # First occurrence wins → test-collection (not another-collection)
        assert result.slug == "test-collection"

    def test_resolve_unknown_puzzle(
        self, jsonl_path: Path, matcher: CollectionMatcher
    ):
        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        sgf = Path("/fake/batch-001/ogs-99999.sgf")
        result = strategy.resolve(sgf, "batch-001", "ogs-99999.sgf")
        assert result is None

    def test_resolve_no_numeric_id(
        self, jsonl_path: Path, matcher: CollectionMatcher
    ):
        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        sgf = Path("/fake/batch-001/puzzle_abc.sgf")
        result = strategy.resolve(sgf, "batch-001", "puzzle_abc.sgf")
        assert result is None

    def test_resolve_unmatched_collection_name(self, tmp_path: Path):
        """Puzzle exists in manifest but collection name doesn't match any slug."""
        jsonl = tmp_path / "test.jsonl"
        jsonl.write_text(
            json.dumps({"name": "zzz-no-match-ever-xyz", "puzzles": [42], "type": "collection"}),
            encoding="utf-8",
        )
        matcher = CollectionMatcher()
        strategy = ManifestLookupStrategy(jsonl, matcher)
        result = strategy.resolve(Path("/f/ogs-42.sgf"), "d", "ogs-42.sgf")
        assert result is None

    def test_dry_run_with_manifest(
        self, jsonl_path: Path, matcher: CollectionMatcher, tmp_path: Path
    ):
        """Full embed_collections run with ManifestLookupStrategy in dry-run."""
        d = tmp_path / "batch-001"
        d.mkdir()
        (d / "ogs-10600.sgf").write_text(MINIMAL_SGF, encoding="utf-8")
        (d / "ogs-10601.sgf").write_text(MINIMAL_SGF, encoding="utf-8")

        strategy = ManifestLookupStrategy(jsonl_path, matcher)
        logger = _mock_logger()
        summary = embed_collections(tmp_path, strategy, matcher, logger, dry_run=True)
        assert summary.embedded == 2
        assert summary.skipped == 0

        # Dry run — file should be unchanged
        content = (d / "ogs-10600.sgf").read_text(encoding="utf-8")
        assert "YL" not in content


# ---------------------------------------------------------------------------
# Unit tests: FilenamePatternStrategy (Strategy C)
# ---------------------------------------------------------------------------

_GOTOOLS_PATTERN = re.compile(
    r"gotools_lv(?P<level>\d+)_(?P<chapter>\d+)_p(?P<position>\d+)\.sgf"
)

_GOTOOLS_LEVEL_MAP = {
    "1": "gotools elementary",
    "2": "gotools intermediate",
}


class TestFilenamePatternStrategy:
    def test_resolve_match(self):
        matcher = CollectionMatcher(
            local_overrides={"gotools elementary": "gotools-elementary"}
        )
        strategy = FilenamePatternStrategy(
            _GOTOOLS_PATTERN, matcher, level_map=_GOTOOLS_LEVEL_MAP
        )
        sgf = Path("/fake/elementary/gotools_lv1_03_p42.sgf")
        result = strategy.resolve(sgf, "elementary", "gotools_lv1_03_p42.sgf")
        assert result is not None
        assert result.slug == "gotools-elementary"
        assert result.chapter == 3
        assert result.position == 42

    def test_resolve_no_match_pattern(self):
        matcher = CollectionMatcher()
        strategy = FilenamePatternStrategy(
            _GOTOOLS_PATTERN, matcher, level_map=_GOTOOLS_LEVEL_MAP
        )
        sgf = Path("/fake/x/random_file.sgf")
        result = strategy.resolve(sgf, "x", "random_file.sgf")
        assert result is None

    def test_resolve_unknown_level(self):
        """Level number in filename not in level_map → raw value passed to matcher."""
        matcher = CollectionMatcher(
            local_overrides={"gotools elementary": "gotools-elementary"}
        )
        strategy = FilenamePatternStrategy(
            _GOTOOLS_PATTERN, matcher, level_map=_GOTOOLS_LEVEL_MAP
        )
        # lv9 not in level_map → raw "9" sent to matcher → no match
        sgf = Path("/fake/x/gotools_lv9_01_p1.sgf")
        result = strategy.resolve(sgf, "x", "gotools_lv9_01_p1.sgf")
        assert result is None

    def test_resolve_without_level_map(self):
        """No level_map → raw regex group used directly."""
        matcher = CollectionMatcher(local_overrides={"1": "level-one"})
        strategy = FilenamePatternStrategy(_GOTOOLS_PATTERN, matcher)
        sgf = Path("/fake/x/gotools_lv1_02_p5.sgf")
        result = strategy.resolve(sgf, "x", "gotools_lv1_02_p5.sgf")
        assert result is not None
        assert result.slug == "level-one"
        assert result.chapter == 2
        assert result.position == 5

    def test_pattern_without_chapter_group(self):
        """Regex without chapter group → chapter defaults to 0."""
        pattern = re.compile(r"puzzle_(?P<level>\w+)_(?P<position>\d+)\.sgf")
        matcher = CollectionMatcher(local_overrides={"basic": "basic-coll"})
        strategy = FilenamePatternStrategy(pattern, matcher)
        sgf = Path("/fake/x/puzzle_basic_10.sgf")
        result = strategy.resolve(sgf, "x", "puzzle_basic_10.sgf")
        assert result is not None
        assert result.slug == "basic-coll"
        assert result.chapter == 0
        assert result.position == 10

    def test_dry_run_with_filename_pattern(self, tmp_path: Path):
        """Full embed_collections run with FilenamePatternStrategy in dry-run."""
        d = tmp_path / "elementary"
        d.mkdir()
        (d / "gotools_lv1_01_p10.sgf").write_text(MINIMAL_SGF, encoding="utf-8")
        (d / "gotools_lv1_01_p20.sgf").write_text(MINIMAL_SGF, encoding="utf-8")

        matcher = CollectionMatcher(
            local_overrides={"gotools elementary": "gotools-elementary"}
        )
        strategy = FilenamePatternStrategy(
            _GOTOOLS_PATTERN, matcher, level_map=_GOTOOLS_LEVEL_MAP
        )
        logger = _mock_logger()

        summary = embed_collections(tmp_path, strategy, matcher, logger, dry_run=True)
        assert summary.embedded == 2


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------


class TestStrategyRegistry:
    def test_all_strategies_registered(self):
        from tools.core.collection_embedder import STRATEGIES

        assert "phrase_match" in STRATEGIES
        assert "manifest_lookup" in STRATEGIES
        assert "filename_pattern" in STRATEGIES
