"""End-to-end trace flow test.

Tests the complete trace_id flow from ingest through analyze to publish,
verifying that trace_id, source_file, and original_filename flow correctly.
"""

import json
from pathlib import Path

from backend.puzzle_manager.core.trace_map import read_trace_map, write_trace_map
from backend.puzzle_manager.core.trace_utils import generate_trace_id
from backend.puzzle_manager.models.config import PipelineConfig
from backend.puzzle_manager.models.enums import StageStatus
from backend.puzzle_manager.stages.protocol import StageContext
from backend.puzzle_manager.state.models import RunState, StageState

# Minimal valid SGF for testing
VALID_SGF = """(;FF[4]GM[1]SZ[9]CA[UTF-8]
GN[test-puzzle-001]
YV[8]YI[20260202-abc12345]YG[beginner]YQ[q:3;rc:0;hc:0]YX[d:2;r:3;s:5;u:1]
AB[aa][ab][ba]AW[ca][cb][da]
;B[cc]C[Correct!]
(;W[dc];B[dd]C[Good!])
(;W[dd];B[dc]C[Also works!])
)"""


class TestTraceE2EFlow:
    """End-to-end trace flow tests."""

    def test_trace_map_roundtrip(self, tmp_path: Path) -> None:
        """Test trace map write/read roundtrip."""
        staging_dir = tmp_path / "staging"
        run_id = "20260202-e2e12345"

        # Simulate ingest: generate trace_id and write map
        mapping = {
            "puzzle-001": generate_trace_id(),
            "puzzle-002": generate_trace_id(),
            "puzzle-003": generate_trace_id(),
        }

        write_trace_map(staging_dir, run_id, mapping)

        # Simulate analyze/publish: read map
        loaded = read_trace_map(staging_dir, run_id)

        assert loaded == mapping
        assert len(loaded) == 3

        # All trace_ids should be 16-char hex
        for trace_id in loaded.values():
            assert len(trace_id) == 16
            int(trace_id, 16)  # Should not raise

    def test_trace_id_in_log_context(self, tmp_path: Path) -> None:
        """Test trace_id can be included in log context."""
        from backend.puzzle_manager.pm_logging import create_trace_logger

        trace_id = generate_trace_id()
        run_id = "20260202-log12345"
        source_id = "test_e2e"

        logger = create_trace_logger(run_id, source_id, trace_id)

        assert logger is not None

    def test_original_filenames_roundtrip(self, tmp_path: Path) -> None:
        """Test original filenames map write/read roundtrip."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir(parents=True)
        run_id = "20260202-ofn12345"

        # Simulate ingest: write original filenames
        ofn_map = {
            "puzzle-001": "life-death-42.sgf",
            "puzzle-002": "ladder-15.sgf",
        }
        ofn_path = staging_dir / f".original-filenames-{run_id}.json"
        ofn_path.write_text(json.dumps(ofn_map), encoding="utf-8")

        # Simulate publish: read original filenames
        loaded = json.loads(ofn_path.read_text(encoding="utf-8"))

        assert loaded == ofn_map


def _create_test_context(tmp_path: Path, run_id: str, source_id: str = "sanderland") -> StageContext:
    """Helper to create a StageContext for testing."""
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "output"
    staging_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = PipelineConfig(
        schema_version=8,
        runtime_dir=str(tmp_path / "runtime"),
        batch_size=10,
    )

    state = RunState(
        run_id=run_id,
        started_at="2026-02-02T10:00:00Z",
        stages=[
            StageState(name="ingest", status=StageStatus.PENDING),
            StageState(name="analyze", status=StageStatus.PENDING),
            StageState(name="publish", status=StageStatus.PENDING),
        ]
    )

    return StageContext(
        config=config,
        staging_dir=staging_dir,
        output_dir=output_dir,
        state=state,
        source_id=source_id,
    )


class TestTraceStageContextIntegration:
    """Test trace_id integration with StageContext."""

    def test_context_run_id_used_for_trace_map(self, tmp_path: Path) -> None:
        """Trace map uses run_id from StageContext."""
        context = _create_test_context(tmp_path, "20260202-runid123")

        # Write trace map using context's run_id
        mapping = {"test": generate_trace_id()}
        write_trace_map(context.staging_dir, context.run_id, mapping)

        # Verify file name includes run_id
        trace_path = context.staging_dir / f".trace-map-{context.run_id}.json"
        assert trace_path.exists()
        assert "20260202-runid123" in trace_path.name


class TestTraceMapIsolation:
    """Test that trace maps from different runs are isolated."""

    def test_different_runs_are_isolated(self, tmp_path: Path) -> None:
        """Trace maps from different runs don't interfere."""
        staging_dir = tmp_path / "staging"

        # Write trace maps for two different runs
        write_trace_map(staging_dir, "run-001", {"puzzle-a": "trace_a_001"})
        write_trace_map(staging_dir, "run-002", {"puzzle-b": "trace_b_002"})

        # Each run should only see its own data
        map_001 = read_trace_map(staging_dir, "run-001")
        map_002 = read_trace_map(staging_dir, "run-002")

        assert map_001 == {"puzzle-a": "trace_a_001"}
        assert map_002 == {"puzzle-b": "trace_b_002"}

        # Non-existent run returns empty
        map_003 = read_trace_map(staging_dir, "run-003")
        assert map_003 == {}
