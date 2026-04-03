"""
Tests for the publish stage path format and sharding behavior.

Verify that the publish stage uses the flat path format
``sgf/{NNNN}/{hash}.sgf`` (no level in path, no year/month segments)
and that batch state is global (not per-level).

Coverage:
- T010: Path format assertions for published files
- T010: Global batch state (not per-level)
- T010: Resolved path uses flat format (sgf/{NNNN})
"""

import json
import re
from pathlib import Path

from backend.puzzle_manager.models.config import (
    BatchConfig,
    CleanupPolicy,
    OutputConfig,
    PipelineConfig,
    StagingConfig,
)
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.stages.publish import PublishStage
from backend.puzzle_manager.state.models import RunState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_analyzed_sgf(
    level_slug: str = "beginner",
    tags: list[str] | None = None,
) -> str:
    """Build a minimal but valid analyzed SGF for publish tests."""
    tags = tags or ["life-and-death"]
    tags_str = ",".join(tags)
    return (
        f"(;FF[4]GM[1]SZ[9]PL[B]"
        f"YV[8]YG[{level_slug}]YT[{tags_str}]"
        f"YQ[q:2;rc:0]YX[d:2;r:5;s:8;u:1]"
        f"AB[dd];B[ee])"
    )


def _make_context(
    staging_dir: Path,
    output_dir: Path,
    *,
    batch_size: int = 100,
    max_files_per_dir: int = 100,
    skip_validation: bool = True,
) -> StageContext:
    """Create a StageContext suitable for publish stage tests."""
    config = PipelineConfig(
        batch=BatchConfig(size=batch_size, max_files_per_dir=max_files_per_dir),
        staging=StagingConfig(cleanup_policy=CleanupPolicy.NEVER),
        output=OutputConfig(root=str(output_dir)),
    )
    state = RunState(run_id="test123456ab")
    return StageContext(
        config=config,
        staging_dir=staging_dir,
        output_dir=output_dir,
        state=state,
        dry_run=False,
        skip_validation=skip_validation,
        source_id="test_source",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPublishPathFormat:
    """Verify published files use sgf/{NNNN}/{hash}.sgf."""

    def test_published_file_lands_at_flat_path(self, tmp_path: Path):
        """T010: Published puzzle uses flat sgf/{NNNN}/ path."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        sgf_content = _create_analyzed_sgf("intermediate")
        (analyzed / "puzzle-001.sgf").write_text(sgf_content, encoding="utf-8")

        ctx = _make_context(staging, output)
        result = PublishStage().run(ctx)

        assert result.processed == 1, f"Expected 1 processed, got {result.processed}; errors: {result.errors}"

        # Find published file
        sgf_root = output / "sgf"
        published = list(sgf_root.rglob("*.sgf"))
        assert len(published) == 1, f"Expected 1 published file, found {len(published)}"

        # Verify flat path: sgf/NNNN/hash.sgf
        rel = published[0].relative_to(output).as_posix()
        pattern = r"^sgf/\d{4}/[a-f0-9]{16}\.sgf$"
        assert re.match(pattern, rel), (
            f"Published path '{rel}' does not match flat format '{pattern}'"
        )

    def test_no_level_slug_in_published_path(self, tmp_path: Path):
        """T010: Published path contains no level slug — flat batch dirs only."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        sgf_content = _create_analyzed_sgf("beginner")
        (analyzed / "puzzle-001.sgf").write_text(sgf_content, encoding="utf-8")

        ctx = _make_context(staging, output)
        PublishStage().run(ctx)

        sgf_root = output / "sgf"
        published = list(sgf_root.rglob("*.sgf"))
        assert len(published) >= 1

        for p in published:
            rel = p.relative_to(output).as_posix()
            # Path should be sgf/NNNN/hash.sgf — exactly 3 segments
            parts = rel.split("/")
            assert len(parts) == 3, (
                f"Path '{rel}' should have 3 segments (sgf/NNNN/file), got {len(parts)}"
            )
            # No level slug in path
            for part in parts[:-1]:  # Exclude filename
                assert not re.match(r"^[a-z]+-?[a-z]+$", part) or part == "sgf", (
                    f"Path '{rel}' contains level-like slug '{part}'"
                )

    def test_batch_number_is_four_digits(self, tmp_path: Path):
        """T010: Batch directories use 4-digit numbering (NNNN)."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        sgf_content = _create_analyzed_sgf("advanced")
        (analyzed / "puzzle-001.sgf").write_text(sgf_content, encoding="utf-8")

        ctx = _make_context(staging, output)
        PublishStage().run(ctx)

        sgf_root = output / "sgf"
        # Batch dirs are direct children of sgf/ with 4-digit names
        batch_dirs = [d for d in sgf_root.iterdir() if d.is_dir() and re.match(r"^\d{4}$", d.name)]
        assert len(batch_dirs) >= 1, (
            f"No 4-digit batch dirs found under {sgf_root}; contents: {list(sgf_root.iterdir())}"
        )

        for bd in batch_dirs:
            assert re.match(r"^\d{4}$", bd.name), (
                f"Batch dir '{bd.name}' is not 4-digit format"
            )


class TestPublishStateKey:
    """Verify batch state is global (at sgf root), not per-level."""

    def test_global_batch_state_exists(self, tmp_path: Path):
        """T010: A single global batch state exists at sgf root."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        # Write puzzles for two different levels
        (analyzed / "puzzle-beg.sgf").write_text(
            _create_analyzed_sgf("beginner"), encoding="utf-8"
        )
        (analyzed / "puzzle-int.sgf").write_text(
            _create_analyzed_sgf("intermediate"), encoding="utf-8"
        )

        ctx = _make_context(staging, output, batch_size=10)
        PublishStage().run(ctx)

        # Verify single global batch state at sgf/.batch-state.json
        sgf_root = output / "sgf"
        state_file = sgf_root / ".batch-state.json"
        assert state_file.exists(), (
            f"Global batch state not found at {state_file}"
        )
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["current_batch"] >= 1
        assert "schema_version" in data

    def test_single_batch_state_at_sgf_root(self, tmp_path: Path):
        """T010: Only one batch state file, at sgf root (not in subdirs)."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        (analyzed / "puzzle-001.sgf").write_text(
            _create_analyzed_sgf("beginner"), encoding="utf-8"
        )

        ctx = _make_context(staging, output)
        PublishStage().run(ctx)

        # Global batch state lives directly at sgf/.batch-state.json
        sgf_root = output / "sgf"
        all_state_files = list(sgf_root.rglob(".batch-state.json"))
        assert len(all_state_files) == 1, (
            f"Expected exactly 1 batch state file, found {len(all_state_files)}: {all_state_files}"
        )
        rel = all_state_files[0].relative_to(sgf_root).as_posix()
        assert rel == ".batch-state.json", (
            f"Batch state at '{rel}' should be at sgf root, not in a subdirectory"
        )


class TestPublishResolvedPath:
    """Verify resolved_path in StageResult uses new format."""

    def test_resolved_paths_use_flat_format(self, tmp_path: Path):
        """T010: resolved_paths in result use sgf/{NNNN} format."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        (analyzed / "puzzle-001.sgf").write_text(
            _create_analyzed_sgf("elementary"), encoding="utf-8"
        )

        ctx = _make_context(staging, output)
        result = PublishStage().run(ctx)

        assert result.processed >= 1
        assert len(result.resolved_paths) >= 1

        for rp in result.resolved_paths:
            pattern = r"^sgf/\d{4}$"
            assert re.match(pattern, rp), (
                f"Resolved path '{rp}' doesn't match flat format 'sgf/NNNN'"
            )

    def test_resolved_paths_no_level_slug(self, tmp_path: Path):
        """T010: resolved_paths contain no level slug — only sgf/{NNNN}."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        for i in range(3):
            (analyzed / f"puzzle-{i:03d}.sgf").write_text(
                _create_analyzed_sgf("beginner", tags=["ko"]), encoding="utf-8"
            )

        ctx = _make_context(staging, output, batch_size=10)
        result = PublishStage().run(ctx)

        for rp in result.resolved_paths:
            parts = rp.split("/")
            # Should be exactly 2 segments: sgf, NNNN
            assert len(parts) == 2, (
                f"Resolved path '{rp}' should have 2 segments, got {len(parts)}"
            )
            assert parts[0] == "sgf"
            assert re.match(r"^\d{4}$", parts[1]), (
                f"Resolved path '{rp}' batch segment '{parts[1]}' is not 4-digit"
            )


class TestPublishOutputFormat:
    """Verify publish produces SGF files and database (not JSON view indexes)."""

    def test_sgf_files_in_flat_batch_dirs(self, tmp_path: Path):
        """T010: Published SGFs land in flat sgf/{NNNN}/ directories."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        (analyzed / "puzzle-001.sgf").write_text(
            _create_analyzed_sgf("beginner", tags=["life-and-death"]),
            encoding="utf-8",
        )

        ctx = _make_context(staging, output)
        result = PublishStage().run(ctx)

        assert result.processed >= 1

        sgf_root = output / "sgf"
        published = list(sgf_root.rglob("*.sgf"))
        assert len(published) >= 1

        for p in published:
            rel = p.relative_to(output).as_posix()
            pattern = r"^sgf/\d{4}/[a-f0-9]{16}\.sgf$"
            assert re.match(pattern, rel), (
                f"Published path '{rel}' doesn't match flat format"
            )

    def test_no_json_view_indexes(self, tmp_path: Path):
        """T010: Publish stage builds SQLite DB, not JSON view indexes."""
        staging = tmp_path / "staging"
        analyzed = staging / "analyzed"
        analyzed.mkdir(parents=True)
        output = tmp_path / "output"
        output.mkdir()

        (analyzed / "puzzle-001.sgf").write_text(
            _create_analyzed_sgf("intermediate", tags=["ko"]),
            encoding="utf-8",
        )

        ctx = _make_context(staging, output)
        PublishStage().run(ctx)

        # No JSON view indexes should be created
        views_dir = output / "views"
        assert not views_dir.exists(), (
            "views/ directory should not exist; publish uses SQLite DB"
        )
