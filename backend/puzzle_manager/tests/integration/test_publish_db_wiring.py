"""Integration tests for publish → SQLite DB wiring.

Verifies that PublishStage.run() produces yengo-search.db + db-version.json
instead of snapshot output.
"""

import json
import sqlite3

from backend.puzzle_manager.models.config import PipelineConfig
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.stages.publish import PublishStage
from backend.puzzle_manager.state.models import RunState


def _make_valid_sgf(
    level: int = 5,
    tags: list[str] | None = None,
    collections: list[str] | None = None,
) -> str:
    """Create a minimal valid SGF for publish testing."""
    tags_str = ",".join(tags or ["life-and-death"])
    level_slug = {
        1: "novice", 5: "elementary", 10: "intermediate",
        15: "upper-intermediate", 20: "advanced",
    }.get(level, "elementary")
    cols_str = ""
    if collections:
        cols_str = f"YL[{','.join(collections)}]"
    return (
        f"(;FF[4]GM[1]SZ[19]"
        f"YV[13]YG[{level_slug}]YT[{tags_str}]"
        f"YQ[q:2;rc:0;hc:0;ac:0]YX[d:1;r:2;s:11;u:1]"
        f"YK[none]YO[strict]YC[TL]"
        f"YM[{{\"t\":\"0000000000000000\",\"s\":\"test\",\"i\":\"test-run\"}}]"
        f"{cols_str}"
        f"AB[pd][qf]AW[qd][pe]"
        f";B[oe]"
        f"(;W[of];B[ne])"
        f"(;W[ne];B[of]))"
    )


class TestPublishDbWiring:
    """Verify PublishStage produces SQLite DB output."""

    def test_publish_creates_db_and_version(self, tmp_path):
        """Publish with valid SGFs → yengo-search.db + db-version.json exist."""
        output_dir = tmp_path / "output"
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        analyzed_dir.mkdir(parents=True)

        # Create 3 test SGFs with unique content
        for i in range(3):
            sgf = _make_valid_sgf(level=5)
            sgf = sgf.replace("AB[pd]", f"AB[{chr(ord('a') + i)}{chr(ord('a') + i)}]")
            (analyzed_dir / f"puzzle_{i}.sgf").write_text(sgf)

        stage = PublishStage()
        context = StageContext(
            config=PipelineConfig(),
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=RunState(run_id="test-db-wiring"),
            skip_validation=True,
            source_id="test",
        )

        result = stage.run(context)

        assert result.processed == 3, f"Expected 3 published, got: {result}"

        # Verify DB exists and has puzzles
        db_path = output_dir / "yengo-search.db"
        assert db_path.exists(), "yengo-search.db not created"

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
        conn.close()
        assert count == 3, f"Expected 3 puzzles in DB, got {count}"

        # Verify version file
        version_path = output_dir / "db-version.json"
        assert version_path.exists(), "db-version.json not created"
        version = json.loads(version_path.read_text())
        assert version["puzzle_count"] == 3
        assert "db_version" in version
        assert "generated_at" in version

    def test_empty_batch_no_db(self, tmp_path):
        """Empty batch (no files) → no DB created."""
        output_dir = tmp_path / "output"
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        analyzed_dir.mkdir(parents=True)

        stage = PublishStage()
        context = StageContext(
            config=PipelineConfig(),
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=RunState(run_id="test-empty"),
            skip_validation=True,
            source_id="test",
        )
        result = stage.run(context)

        assert result.processed == 0
        assert not (output_dir / "yengo-search.db").exists()
        assert not (output_dir / "db-version.json").exists()

    def test_db_contains_tags_and_collections(self, tmp_path):
        """DB junction tables are populated for tagged puzzles."""
        output_dir = tmp_path / "output"
        staging_dir = tmp_path / "staging"
        analyzed_dir = staging_dir / "analyzed"
        analyzed_dir.mkdir(parents=True)

        sgf = _make_valid_sgf(level=5, tags=["life-and-death", "ladder"])
        (analyzed_dir / "tagged.sgf").write_text(sgf)

        stage = PublishStage()
        context = StageContext(
            config=PipelineConfig(),
            staging_dir=staging_dir,
            output_dir=output_dir,
            state=RunState(run_id="test-tags"),
            skip_validation=True,
            source_id="test",
        )
        result = stage.run(context)
        assert result.processed == 1

        db_path = output_dir / "yengo-search.db"
        conn = sqlite3.connect(db_path)
        tag_count = conn.execute("SELECT COUNT(*) FROM puzzle_tags").fetchone()[0]
        conn.close()

        # Should have 2 tag rows (life-and-death + ladder)
        assert tag_count == 2, f"Expected 2 tag rows, got {tag_count}"

    def test_protocol_db_paths(self, tmp_path):
        """StageContext exposes db_output_path and db_version_path."""
        context = StageContext(
            config=PipelineConfig(),
            staging_dir=tmp_path / "staging",
            output_dir=tmp_path / "output",
            state=RunState(run_id="test-paths"),
        )

        assert context.db_output_path == tmp_path / "output" / "yengo-search.db"
        assert context.db_version_path == tmp_path / "output" / "db-version.json"
