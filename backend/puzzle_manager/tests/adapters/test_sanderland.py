"""
Tests for Sanderland adapter.

These tests verify:
- Puzzle fetching from local JSON collection
- Centralized validation integration
- Consistent validation behavior matching OGS adapter
- Folder filtering (include_folders, exclude_folders)
- Checkpoint/resume support
"""

import pytest

# Mark all tests in this module as adapter tests
pytestmark = pytest.mark.adapter

import json

from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter
from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint

# ==============================
# Test Fixtures
# ==============================

@pytest.fixture
def mock_checkpoint_path(tmp_path, monkeypatch):
    """Mock checkpoint path to use temp directory."""
    runtime_dir = tmp_path / ".pm-runtime" / "state"
    runtime_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "backend.puzzle_manager.core.checkpoint.get_runtime_dir",
        lambda: tmp_path / ".pm-runtime"
    )
    return runtime_dir


@pytest.fixture
def temp_collection(tmp_path):
    """Create a temporary sanderland collection with sample puzzles.

    Uses folder structure to match the new folder-filtering adapter.
    """
    # Create collection directory with folder structure
    collection_dir = tmp_path / "sanderland"
    folder_dir = collection_dir / "test_folder"
    folder_dir.mkdir(parents=True)

    # Create a valid 9x9 puzzle
    valid_puzzle = {
        "SZ": "9",
        "C": "Black to play: Elementary",
        "AB": ["cc", "cd", "dc"],  # 3 black stones
        "AW": ["dd", "de"],         # 2 white stones
        "SOL": [
            ["B", "ce", "Correct", []]
        ]
    }
    (folder_dir / "valid_9x9.json").write_text(
        json.dumps(valid_puzzle), encoding="utf-8"
    )

    # Create a valid 7x9 non-square puzzle (partial board)
    non_square_puzzle = {
        "SZ": "7:9",  # 7 wide, 9 tall (if supported by format)
        "C": "Black to play: Intermediate",
        "AB": ["ba", "bb", "ca"],
        "AW": ["cb", "db"],
        "SOL": [
            ["B", "da", "Correct", []]
        ]
    }
    (folder_dir / "valid_7x9.json").write_text(
        json.dumps(non_square_puzzle), encoding="utf-8"
    )

    # Create an invalid 4x4 puzzle (below minimum)
    small_puzzle = {
        "SZ": "4",
        "C": "Too small",
        "AB": ["aa", "ab"],
        "AW": ["ba"],
        "SOL": [
            ["B", "bb", "Correct", []]
        ]
    }
    (folder_dir / "invalid_4x4.json").write_text(
        json.dumps(small_puzzle), encoding="utf-8"
    )

    return collection_dir


@pytest.fixture
def adapter_with_temp_collection(temp_collection):
    """Create adapter configured with temp collection."""
    adapter = SanderlandAdapter(source_dir=str(temp_collection))
    return adapter


# ==============================
# Basic Adapter Tests
# ==============================

class TestSanderlandAdapterInit:
    """Tests for adapter initialization."""

    def test_name_property(self, adapter_with_temp_collection):
        """Should have correct name."""
        assert adapter_with_temp_collection.name == "Sanderland Collection"

    def test_source_id_property(self, adapter_with_temp_collection):
        """Should have correct source_id."""
        assert adapter_with_temp_collection.source_id == "sanderland"

    def test_is_available_with_collection(self, adapter_with_temp_collection):
        """Should be available when collection exists."""
        assert adapter_with_temp_collection.is_available() is True

    def test_is_available_without_collection(self, tmp_path):
        """Should not be available when collection missing."""
        adapter = SanderlandAdapter(source_dir=str(tmp_path / "nonexistent"))
        assert adapter.is_available() is False


# ==============================
# Centralized Validation Tests (T027)
# ==============================

class TestCentralizedValidation:
    """Tests for centralized puzzle validation via PuzzleValidator.

    These tests verify the Sanderland adapter uses PuzzleValidator correctly
    and produces identical validation results to OGS adapter.
    """

    def test_4x4_board_rejected_via_centralized_validator(self, temp_collection):
        """T027a: Puzzle with 4×4 board should be rejected by Sanderland adapter.

        This verifies that the centralized PuzzleValidator is used and
        correctly rejects boards below minimum dimension (5).

        MUST produce identical rejection behavior to OGS adapter (spec 108).
        """
        adapter = SanderlandAdapter(source_dir=str(temp_collection))

        results = list(adapter.fetch(batch_size=100))

        # Find the 4x4 puzzle result
        invalid_result = None
        for r in results:
            if "4x4" in r.puzzle_id:
                invalid_result = r
                break

        assert invalid_result is not None, "4x4 puzzle should be in results"
        assert invalid_result.status == "skipped", f"4x4 should be skipped, got {invalid_result.status}"
        # FetchResult.skipped() stores reason in 'error' field
        assert invalid_result.error is not None
        assert "4" in invalid_result.error or "below" in invalid_result.error.lower() or "small" in invalid_result.error.lower()

    def test_7x9_non_square_board_accepted(self, temp_collection):
        """T027b: Puzzle with 7×9 non-square board should be ACCEPTED.

        This verifies that non-square partial boards (common in tsumego)
        are accepted by the centralized validator.

        MUST produce identical acceptance behavior to OGS adapter (spec 108).
        """
        adapter = SanderlandAdapter(source_dir=str(temp_collection))

        results = list(adapter.fetch(batch_size=100))

        # Find the 7x9 puzzle result
        non_square_result = None
        for r in results:
            if "7x9" in r.puzzle_id:
                non_square_result = r
                break

        assert non_square_result is not None, "7x9 puzzle should be in results"
        # Should be success (not skipped) - accepted by validator
        assert non_square_result.status == "success", f"7x9 should be accepted, got {non_square_result.status}: {getattr(non_square_result, 'reason', 'no reason')}"

    def test_valid_9x9_board_accepted(self, temp_collection):
        """Valid 9×9 square board should be accepted."""
        adapter = SanderlandAdapter(source_dir=str(temp_collection))

        results = list(adapter.fetch(batch_size=100))

        # Find the valid 9x9 puzzle result
        valid_result = None
        for r in results:
            if "9x9" in r.puzzle_id:
                valid_result = r
                break

        assert valid_result is not None, "9x9 puzzle should be in results"
        assert valid_result.status == "success", f"9x9 should be accepted, got {valid_result.status}"


# ==============================
# Consistency Tests (OGS-Sanderland Parity)
# ==============================

class TestValidationConsistency:
    """Tests verifying identical validation behavior between adapters.

    These tests ensure spec 108's goal of consistent validation is achieved:
    same puzzle data should produce identical accept/reject decisions
    across OGS and Sanderland adapters.
    """

    def test_rejection_message_consistency(self, temp_collection):
        """Rejection messages should follow centralized RejectionReason format.

        Both adapters should use PuzzleValidator, so rejection messages
        should be consistent (from RejectionReason enum messages).
        """
        adapter = SanderlandAdapter(source_dir=str(temp_collection))

        results = list(adapter.fetch(batch_size=100))

        skipped_results = [r for r in results if r.status == "skipped"]

        # If there are skipped puzzles, verify message format
        for r in skipped_results:
            # Centralized validator messages are structured
            # FetchResult.skipped() stores reason in 'error' field
            assert r.error is not None
            assert len(r.error) > 0
            # Messages should mention the specific dimension or reason
            assert any(word in r.error.lower() for word in ["board", "dimension", "minimum", "below", "small", "solution", "stones", "depth"])


# ==============================
# Multi-Folder Fixtures
# ==============================

@pytest.fixture
def multi_folder_collection(tmp_path):
    """Create a collection with multiple folders matching Sanderland structure."""
    collection_dir = tmp_path / "sanderland" / "problems"
    collection_dir.mkdir(parents=True)

    # Create folder structure similar to real Sanderland
    folders = [
        "1a. Tsumego Beginner",
        "1b. Tsumego Intermediate",
        "1c. Tsumego Advanced",
        "2a. Tesuji",
    ]

    sample_puzzle = {
        "SZ": "9",
        "C": "Test puzzle",
        "AB": ["cc", "cd", "dc"],
        "AW": ["dd", "de"],
        "SOL": [["B", "ce", "Correct", []]]
    }

    for folder in folders:
        folder_path = collection_dir / folder
        folder_path.mkdir()
        # Add 2 puzzles per folder
        (folder_path / "puzzle_001.json").write_text(
            json.dumps(sample_puzzle), encoding="utf-8"
        )
        (folder_path / "puzzle_002.json").write_text(
            json.dumps(sample_puzzle), encoding="utf-8"
        )

    return collection_dir


# ==============================
# Folder Filtering Tests (T011-T014a)
# ==============================

class TestFolderFiltering:
    """Tests for include_folders and exclude_folders configuration."""

    def test_include_folders_processes_only_specified_folders(self, multi_folder_collection):
        """T011: include_folders should limit processing to specified folders."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner"]
        })

        results = list(adapter.fetch(batch_size=100))

        # Should only get puzzles from 1a folder (2 puzzles)
        assert len(results) == 2
        for r in results:
            assert "1a" in r.puzzle_id.lower() or "beginner" in r.puzzle_id.lower()

    def test_include_folders_multiple_folders(self, multi_folder_collection):
        """T012: include_folders with multiple folders."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner", "2a. Tesuji"]
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get 4 puzzles (2 from each of 2 folders)
        assert len(results) == 4

    def test_exclude_folders_skips_specified_folders(self, multi_folder_collection):
        """T013: exclude_folders should skip specified folders."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "exclude_folders": ["1c. Tsumego Advanced"]
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get 6 puzzles (2 from each of 3 folders, excluding 1c)
        assert len(results) == 6
        for r in results:
            assert "1c" not in r.puzzle_id.lower() and "advanced" not in r.puzzle_id.lower()

    def test_include_takes_precedence_over_exclude(self, multi_folder_collection):
        """T014: include_folders takes precedence when both specified."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner"],
            "exclude_folders": ["1a. Tsumego Beginner"]  # Should be ignored
        })

        results = list(adapter.fetch(batch_size=100))

        # include_folders wins - process 1a
        assert len(results) == 2

    def test_empty_include_folders_processes_all(self, multi_folder_collection):
        """Empty include_folders should process all folders."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": []
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get all 8 puzzles (2 from each of 4 folders)
        assert len(results) == 8

    def test_nonexistent_folder_logged_but_continues(self, multi_folder_collection, caplog):
        """T015: Non-existent folder in include_folders logs warning."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["nonexistent", "1a. Tsumego Beginner"]
        })

        results = list(adapter.fetch(batch_size=100))

        # Should still process 1a (2 puzzles)
        assert len(results) == 2
        # Should have logged warning about nonexistent folder
        assert any("nonexistent" in record.message.lower()
                   for record in caplog.records)

    def test_case_sensitive_folder_matching(self, multi_folder_collection, caplog):
        """T014a: Folder matching should be case-sensitive."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            # Wrong case - should NOT match "1a. Tsumego Beginner"
            "include_folders": ["1A. TSUMEGO BEGINNER"]
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get 0 puzzles (case doesn't match)
        assert len(results) == 0
        # Should have logged warning about folder not found
        assert any("1a" in record.message.lower() or "not found" in record.message.lower()
                   for record in caplog.records)

    def test_folders_processed_in_include_order(self, multi_folder_collection):
        """T016: Folders should be processed in include_folders order."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            # Specify order: Tesuji first, then Beginner
            "include_folders": ["2a. Tesuji", "1a. Tsumego Beginner"]
        })

        results = list(adapter.fetch(batch_size=100))

        # First 2 results should be from Tesuji (processed first)
        assert "tesuji" in results[0].puzzle_id.lower() or "2a" in results[0].puzzle_id.lower()
        # Last 2 should be from Beginner
        assert "beginner" in results[-1].puzzle_id.lower() or "1a" in results[-1].puzzle_id.lower()

    def test_get_folders_to_process_method(self, multi_folder_collection):
        """T017: _get_folders_to_process returns correct filtered list."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1b. Tsumego Intermediate"]
        })

        folders = adapter._get_folders_to_process()

        assert len(folders) == 1
        assert folders[0].name == "1b. Tsumego Intermediate"


# ==============================
# Checkpoint/Resume Tests (T022-T037)
# ==============================

class TestCheckpointResume:
    """Tests for checkpoint and resume functionality."""

    def test_supports_resume_property(self, multi_folder_collection):
        """T022: supports_resume should return True."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        assert adapter.supports_resume() is True

    def test_checkpoint_saved_during_fetch(self, multi_folder_collection, mock_checkpoint_path):
        """T023: Checkpoint should be saved during fetch."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        # Fetch just 1 puzzle
        results = list(adapter.fetch(batch_size=1))

        assert len(results) == 1
        # Checkpoint should exist
        assert AdapterCheckpoint.exists("sanderland")

    def test_checkpoint_state_structure(self, multi_folder_collection, mock_checkpoint_path):
        """T024: Checkpoint state should have required fields."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        list(adapter.fetch(batch_size=1))

        checkpoint = AdapterCheckpoint.load("sanderland")
        state = checkpoint["state"]

        # Required fields per contract
        assert "current_folder" in state
        assert "current_folder_index" in state
        assert "files_completed" in state
        assert "total_processed" in state
        assert "total_failed" in state

    def test_resume_skips_to_checkpoint_position(self, multi_folder_collection, mock_checkpoint_path):
        """T025: Resume should skip to saved checkpoint position."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        # First run - get 1 puzzle
        results1 = list(adapter.fetch(batch_size=1))
        assert len(results1) == 1
        first_puzzle_id = results1[0].puzzle_id

        # Second run with resume - should continue from where we left off
        adapter2 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter2.configure({
            "include_folders": ["1a. Tsumego Beginner"],
            "resume": True
        })

        results2 = list(adapter2.fetch(batch_size=1))
        assert len(results2) == 1
        # Should NOT be the same puzzle
        assert results2[0].puzzle_id != first_puzzle_id

    def test_checkpoint_cleared_on_completion(self, multi_folder_collection, mock_checkpoint_path):
        """T026: Checkpoint should be cleared when all folders complete."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        # Fetch all puzzles in folder (2 puzzles)
        results = list(adapter.fetch(batch_size=100))
        assert len(results) == 2

        # Checkpoint should be cleared
        assert not AdapterCheckpoint.exists("sanderland")

    def test_resume_false_starts_fresh(self, multi_folder_collection, mock_checkpoint_path):
        """T028: resume=False should ignore existing checkpoint."""
        # Pre-create a checkpoint
        AdapterCheckpoint.save("sanderland", {
            "current_folder": "1a. Tsumego Beginner",
            "current_folder_index": 0,
            "files_completed": 1,  # Would skip first file
            "total_processed": 1,
            "total_failed": 0,
        })

        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner"],
            "resume": False  # Explicitly start fresh
        })

        results = list(adapter.fetch(batch_size=100))

        # Should process all files, not resume from checkpoint
        assert len(results) == 2

    def test_get_checkpoint_returns_json_string(self, multi_folder_collection, mock_checkpoint_path):
        """T029: get_checkpoint should return JSON string."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        list(adapter.fetch(batch_size=1))

        checkpoint_str = adapter.get_checkpoint()

        assert checkpoint_str is not None
        # Should be valid JSON
        data = json.loads(checkpoint_str)
        assert "current_folder" in data

    def test_set_checkpoint_from_json_string(self, multi_folder_collection, mock_checkpoint_path):
        """T030: set_checkpoint should accept JSON string."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        checkpoint_data = json.dumps({
            "current_folder": "1a. Tsumego Beginner",
            "current_folder_index": 0,
            "files_completed": 1,
            "total_processed": 1,
            "total_failed": 0,
        })

        adapter.set_checkpoint(checkpoint_data)

        # Verify it was saved
        assert AdapterCheckpoint.exists("sanderland")
        loaded = AdapterCheckpoint.load("sanderland")
        assert loaded["state"]["files_completed"] == 1


# ==============================
# Integration Tests
# ==============================

class TestFolderFilteringIntegration:
    """Integration tests for folder filtering with real-like scenarios."""

    def test_full_workflow_include_filter_checkpoint_resume(
        self, multi_folder_collection, mock_checkpoint_path
    ):
        """Integration: include_folders → batch_size limits → resume."""
        # First run: fetch 2 puzzles from Beginner (limited by batch_size)
        adapter1 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter1.configure({
            "include_folders": ["1a. Tsumego Beginner", "1b. Tsumego Intermediate"]
        })
        results1 = list(adapter1.fetch(batch_size=2))
        assert len(results1) == 2

        # Checkpoint should exist
        assert AdapterCheckpoint.exists("sanderland")

        # Second run: resume and get remaining
        adapter2 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter2.configure({
            "include_folders": ["1a. Tsumego Beginner", "1b. Tsumego Intermediate"],
            "resume": True
        })
        results2 = list(adapter2.fetch(batch_size=100))

        # Should get remaining 2 puzzles
        assert len(results2) == 2
        # Combined results should be 4 unique puzzles
        all_ids = [r.puzzle_id for r in results1 + results2]
        assert len(set(all_ids)) == 4

    def test_exclude_with_checkpoint(self, multi_folder_collection, mock_checkpoint_path):
        """Integration: exclude_folders works with checkpoint/resume."""
        adapter1 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter1.configure({
            "exclude_folders": ["1c. Tsumego Advanced", "2a. Tesuji"]
        })

        # Fetch 2 (should be from 1a and 1b)
        results1 = list(adapter1.fetch(batch_size=2))
        assert len(results1) == 2

        # Resume
        adapter2 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter2.configure({
            "exclude_folders": ["1c. Tsumego Advanced", "2a. Tesuji"],
            "resume": True
        })
        results2 = list(adapter2.fetch(batch_size=100))

        # Should complete remaining (2 more from 1b)
        assert len(results2) == 2


# ==============================
# Validation Tests (T044a-c)
# ==============================

class TestValidationTasks:
    """Validation tests for performance, file size, and edge cases."""

    def test_resume_performance_under_5_seconds(self, multi_folder_collection, mock_checkpoint_path):
        """T044a: Resume should complete in under 5 seconds."""
        import time

        # Create checkpoint with state
        AdapterCheckpoint.save("sanderland", {
            "current_folder": "1b. Tsumego Intermediate",
            "current_folder_index": 1,
            "files_completed": 0,
            "total_processed": 2,
            "total_failed": 0,
        })

        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner", "1b. Tsumego Intermediate"],
            "resume": True
        })

        start = time.perf_counter()
        list(adapter.fetch(batch_size=1))  # Just verify resume works
        elapsed = time.perf_counter() - start

        assert elapsed < 5.0, f"Resume took {elapsed:.2f}s, should be < 5s"

    def test_checkpoint_file_size_under_1kb(self, multi_folder_collection, mock_checkpoint_path):
        """T044b: Checkpoint file should be under 1KB."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        list(adapter.fetch(batch_size=1))

        checkpoint_path = AdapterCheckpoint.get_path("sanderland")
        if checkpoint_path.exists():
            file_size = checkpoint_path.stat().st_size
            assert file_size < 1024, f"Checkpoint is {file_size} bytes, should be < 1024"

    def test_folder_structure_change_handled(self, multi_folder_collection, mock_checkpoint_path):
        """T044c: Adapter handles folder structure changes gracefully."""
        # Create checkpoint referencing a folder that will be "removed"
        AdapterCheckpoint.save("sanderland", {
            "current_folder": "REMOVED_FOLDER",
            "current_folder_index": 5,  # Beyond current folder count
            "files_completed": 50,
            "total_processed": 100,
            "total_failed": 0,
        })

        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner"],
            "resume": True
        })

        # Should not crash - checkpoint state doesn't match but should handle gracefully
        results = list(adapter.fetch(batch_size=100))

        # Even with mismatched checkpoint, should complete without error
        # (either starts fresh or skips based on folder_index > available)
        assert isinstance(results, list)
    def test_config_change_detected_on_resume(self, multi_folder_collection, mock_checkpoint_path, caplog):
        """Config change between runs should log warning."""
        # First run with one config
        adapter1 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter1.configure({"include_folders": ["1a. Tsumego Beginner"]})
        list(adapter1.fetch(batch_size=1))

        # Second run with different config but resume=True
        adapter2 = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter2.configure({
            "include_folders": ["1b. Tsumego Intermediate"],  # Different config
            "resume": True
        })

        list(adapter2.fetch(batch_size=1))

        # Should have logged warning about config change
        assert any("config changed" in record.message.lower()
                   for record in caplog.records)

    def test_folder_index_bounds_check(self, multi_folder_collection, mock_checkpoint_path, caplog):
        """Folder index exceeding bounds should reset to start."""
        # Create checkpoint with invalid folder_index
        AdapterCheckpoint.save("sanderland", {
            "current_folder": "nonexistent",
            "current_folder_index": 999,  # Way beyond available
            "files_completed": 0,
            "total_processed": 0,
            "total_failed": 0,
            "config_signature": "",  # Empty so no config warning
        })

        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({
            "include_folders": ["1a. Tsumego Beginner"],
            "resume": True
        })

        results = list(adapter.fetch(batch_size=100))

        # Should have logged warning about exceeding bounds
        assert any("exceeds" in record.message.lower() or "starting from beginning" in record.message.lower()
                   for record in caplog.records)
        # Should still process all files in the folder
        assert len(results) == 2

    def test_config_signature_stored_in_checkpoint(self, multi_folder_collection, mock_checkpoint_path):
        """Config signature should be stored in checkpoint."""
        adapter = SanderlandAdapter(source_dir=str(multi_folder_collection))
        adapter.configure({"include_folders": ["1a. Tsumego Beginner"]})

        list(adapter.fetch(batch_size=1))

        checkpoint = AdapterCheckpoint.load("sanderland")
        assert checkpoint is not None
        assert "config_signature" in checkpoint["state"]
        assert len(checkpoint["state"]["config_signature"]) == 8  # MD5 hash truncated to 8 chars


# ==============================
# Pass Move Handling Tests
# ==============================

class TestPassMoveHandling:
    """Tests for pass move detection and SGF conversion."""

    def test_is_pass_coord_zz(self):
        """'zz' should be recognized as a pass coordinate."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        assert adapter._is_pass_coord("zz") is True

    def test_is_pass_coord_empty(self):
        """Empty string should be recognized as a pass coordinate."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        assert adapter._is_pass_coord("") is True

    def test_is_pass_coord_normal(self):
        """Normal coordinates should not be passes."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        assert adapter._is_pass_coord("cd") is False
        assert adapter._is_pass_coord("aa") is False
        assert adapter._is_pass_coord("ss") is False

    def test_single_white_pass(self):
        """Single W[zz] move should produce W[] with comment."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([["W", "zz", "", ""]])
        assert result == ";W[]C[White passes]"

    def test_single_black_pass(self):
        """Single B[zz] move should produce B[] with comment."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([["B", "zz", "", ""]])
        assert result == ";B[]C[Black passes]"

    def test_multi_move_with_embedded_pass(self):
        """Pass in the middle of a sequence should be preserved."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([
            ["B", "cd"],
            ["W", "zz"],
            ["B", "ef"],
        ])
        assert result == ";B[cd];W[]C[White passes];B[ef]"

    def test_pass_with_existing_comment(self):
        """Pass should append to existing comment with em-dash."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([["W", "zz", "Correct", ""]])
        assert result == ";W[]C[Correct \u2014 White passes]"

    def test_miai_with_pass(self):
        """Miai variation containing a pass should handle it correctly."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([
            ["B", "zz"],
            ["B", "cd"],
        ])
        assert "(;B[]C[Black passes])" in result
        assert "(;B[cd])" in result

    def test_normal_moves_unchanged(self):
        """Normal moves should not be affected by pass detection."""
        adapter = SanderlandAdapter(source_dir="/tmp/fake")
        result = adapter._build_solution_tree([["B", "cd"], ["W", "ef"]])
        assert result == ";B[cd];W[ef]"
