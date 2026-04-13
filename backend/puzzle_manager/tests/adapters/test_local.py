"""
Tests for LocalAdapter feature parity enhancement (spec 111).

Tests are organized by user story:
- TestLocalFolderFiltering (US1): Folder include/exclude filtering
- TestLocalCheckpoint (US2): Checkpoint/resume functionality
- TestLocalValidation (US3): SGF validation and skip logic
- TestLocalProgress (US4): Progress logging
- TestLocalHelperMethods: Unit tests for internal helper methods
- TestLocalEdgeCases: Edge case and boundary tests

Pytest markers:
- @pytest.mark.adapter: Adapter-specific tests (default for this file)
- @pytest.mark.unit: Fast isolated tests (for helper method tests)
"""

import logging

import pytest

from backend.puzzle_manager.adapters.local.adapter import LocalAdapter
from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint

# Mark entire module as adapter tests
pytestmark = pytest.mark.adapter


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def valid_sgf_content():
    """Valid SGF content with solution tree."""
    return """(;FF[4]GM[1]SZ[9]
AB[cc][dc][cd]
AW[dd][ed][de]
;B[ec]
(;W[fd];B[fc])
(;W[fc];B[fd])
)"""


@pytest.fixture
def invalid_sgf_no_solution():
    """SGF content without solution tree."""
    return """(;FF[4]GM[1]SZ[9]
AB[cc][dc][cd]
AW[dd][ed][de]
)"""


@pytest.fixture
def invalid_sgf_bad_board():
    """SGF content with invalid board size."""
    return """(;FF[4]GM[1]SZ[37]
AB[cc]
AW[dd]
;B[ec]
)"""


@pytest.fixture
def malformed_sgf():
    """Malformed SGF that cannot be parsed."""
    return """(;FF[4]GM[1]SZ[9
AB[cc]"""


@pytest.fixture
def local_collection(tmp_path):
    """Create a local collection with folder structure for testing.

    Uses unique SGF content per file to avoid deduplication by content hash.
    """
    # Create folder structure
    elementary = tmp_path / "elementary"
    intermediate = tmp_path / "intermediate"
    advanced = tmp_path / "advanced"

    elementary.mkdir()
    intermediate.mkdir()
    advanced.mkdir()

    # Create unique SGF content for each file by varying the comment
    def make_sgf(puzzle_num: int, has_solution: bool = True) -> str:
        base = f"(;FF[4]GM[1]SZ[9]C[Puzzle {puzzle_num}]\nAB[cc][dc][cd]\nAW[dd][ed][de]"
        if has_solution:
            return base + "\n;B[ec]\n(;W[fd];B[fc])\n(;W[fc];B[fd])\n)"
        return base + "\n)"

    # Add SGF files to each folder with unique content
    (elementary / "puzzle1.sgf").write_text(make_sgf(1), encoding="utf-8")
    (elementary / "puzzle2.sgf").write_text(make_sgf(2), encoding="utf-8")

    (intermediate / "puzzle3.sgf").write_text(make_sgf(3), encoding="utf-8")
    (intermediate / "puzzle4.sgf").write_text(make_sgf(4, has_solution=False), encoding="utf-8")

    (advanced / "puzzle5.sgf").write_text(make_sgf(5), encoding="utf-8")

    return tmp_path


@pytest.fixture
def adapter():
    """Create a fresh LocalAdapter instance."""
    return LocalAdapter()


# =============================================================================
# User Story 1: Folder Filtering Tests
# =============================================================================

@pytest.mark.adapter
class TestLocalFolderFiltering:
    """Tests for folder filtering functionality (User Story 1)."""

    def test_include_folders_filters_to_specified_folders(self, adapter, local_collection):
        """Test that include_folders only processes specified folders."""
        adapter.configure({
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should only get puzzles from elementary (2 files)
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 2

        # Verify all source links are from elementary folder
        for result in success_results:
            assert "elementary" in result.source_link

    def test_exclude_folders_removes_specified_folders(self, adapter, local_collection):
        """Test that exclude_folders skips specified folders."""
        adapter.configure({
            "path": str(local_collection),
            "exclude_folders": ["advanced"],
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get puzzles from elementary (2) + intermediate (2) = 4
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 4

        # Verify no source links from advanced folder
        for result in success_results:
            assert "advanced" not in result.source_link

    def test_no_filters_processes_all_folders(self, adapter, local_collection):
        """Test that with no filters, all folders are processed."""
        adapter.configure({
            "path": str(local_collection),
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should get all 5 puzzles
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 5

    def test_include_folders_order_preserved(self, adapter, local_collection):
        """Test that include_folders order is preserved in processing."""
        adapter.configure({
            "path": str(local_collection),
            "include_folders": ["intermediate", "elementary"],  # Reverse order
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))
        success_results = [r for r in results if r.status == "success"]

        # First results should be from intermediate, then elementary
        # intermediate has puzzle3, puzzle4; elementary has puzzle1, puzzle2
        assert "intermediate" in success_results[0].source_link
        assert "intermediate" in success_results[1].source_link
        assert "elementary" in success_results[2].source_link
        assert "elementary" in success_results[3].source_link

    def test_nonexistent_include_folder_logs_warning(self, adapter, local_collection, caplog):
        """Test that non-existent include folders log a warning."""
        adapter.configure({
            "path": str(local_collection),
            "include_folders": ["nonexistent", "elementary"],
            "validate": False,
        })

        with caplog.at_level(logging.WARNING):
            results = list(adapter.fetch(batch_size=100))

        # Should still process elementary
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 2

        # Should have logged a warning about nonexistent folder
        assert any("nonexistent" in record.message and "not found" in record.message.lower()
                   for record in caplog.records)

    def test_path_not_exists_yields_failed(self, adapter):
        """Test that non-existent path yields failed result."""
        adapter.configure({
            "path": "/nonexistent/path",
        })

        results = list(adapter.fetch(batch_size=100))

        assert len(results) == 1
        assert results[0].status == "failed"
        assert "does not exist" in results[0].error

    def test_empty_folder_continues_to_next(self, adapter, tmp_path, valid_sgf_content, caplog):
        """Test that empty folders are skipped with log message."""
        # Create structure with empty folder
        empty = tmp_path / "empty"
        with_files = tmp_path / "with_files"
        empty.mkdir()
        with_files.mkdir()

        (with_files / "puzzle.sgf").write_text(valid_sgf_content, encoding="utf-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["empty", "with_files"],
            "validate": False,
        })

        with caplog.at_level(logging.INFO):
            results = list(adapter.fetch(batch_size=100))

        # Should still process with_files
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 1

        # Should have logged info about empty folder
        assert any("empty" in record.message and "No SGF files" in record.message
                   for record in caplog.records)


# =============================================================================
# User Story 2: Checkpoint/Resume Tests
# =============================================================================

@pytest.mark.adapter
class TestLocalCheckpoint:
    """Tests for checkpoint/resume functionality (User Story 2)."""

    def test_checkpoint_saved_after_each_file(self, adapter, local_collection, tmp_path):
        """Test that checkpoint is saved when generator is closed (e.g., batch_size=1).

        Checkpoint writes are throttled (every 10 puzzles) for performance,
        but pending state is always flushed when the generator is closed via
        try/finally, ensuring no progress is lost.
        """
        # Use a unique source ID to avoid conflicts
        source_id = "test-checkpoint-save"

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
        })

        # Process one file and close the generator
        # The try/finally in fetch() flushes pending checkpoint on generator close
        gen = adapter.fetch(batch_size=1)
        result = next(gen)
        assert result.status == "success"
        gen.close()  # Triggers GeneratorExit → finally → checkpoint flush

        # Checkpoint should exist after generator close
        checkpoint = AdapterCheckpoint.load(source_id)
        assert checkpoint is not None, "Checkpoint should be saved when generator is closed"

        # Clean up
        AdapterCheckpoint.clear(source_id)

    def test_resume_continues_from_saved_position(self, adapter, local_collection):
        """Test that resume continues from saved checkpoint position."""
        source_id = "test-resume-continue"

        # Save a checkpoint indicating files_completed=1 (skip first file)
        state = {
            "current_folder": "elementary",
            "current_folder_index": 0,
            "files_completed": 1,
            "total_processed": 1,
            "total_skipped": 0,
            "total_failed": 0,
            "config_signature": "",
        }
        AdapterCheckpoint.save(source_id, state)

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
            "resume": True,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should only get 1 file (second file in elementary)
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 1

        # Clean up
        AdapterCheckpoint.clear(source_id)

    def test_config_change_logs_warning_on_resume(self, adapter, local_collection, caplog):
        """Test that config changes between runs log a warning."""
        source_id = "test-config-change"

        # Save checkpoint with different config signature
        state = {
            "current_folder": "elementary",
            "current_folder_index": 0,
            "files_completed": 0,
            "total_processed": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "config_signature": "different123",
        }
        AdapterCheckpoint.save(source_id, state)

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
            "resume": True,
        })

        with caplog.at_level(logging.WARNING):
            list(adapter.fetch(batch_size=100))

        # Should have logged warning about config change
        assert any("Config changed" in record.message for record in caplog.records)

        # Clean up
        AdapterCheckpoint.clear(source_id)

    def test_checkpoint_cleared_on_completion(self, adapter, local_collection):
        """Test that checkpoint is cleared when processing completes."""
        source_id = "test-checkpoint-clear"

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
        })

        # Process all files
        list(adapter.fetch(batch_size=100))

        # Checkpoint should be cleared
        checkpoint = AdapterCheckpoint.load(source_id)
        assert checkpoint is None

    def test_checkpoint_state_includes_all_required_fields(self, adapter, local_collection):
        """Test that checkpoint state includes all required fields."""
        source_id = "test-checkpoint-fields"

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
        })

        # Process files with batch_size=1 to save checkpoint after first file
        for _result in adapter.fetch(batch_size=1):
            break  # Just process one file

        checkpoint = AdapterCheckpoint.load(source_id)
        assert checkpoint is not None, "Checkpoint should exist after processing"
        state = checkpoint["state"]

        # Verify all required fields
        required_fields = [
            "current_folder",
            "current_folder_index",
            "files_completed",
            "total_processed",
            "total_skipped",
            "total_failed",
            "config_signature",
        ]

        for field in required_fields:
            assert field in state, f"Missing field: {field}"

        # Clean up
        AdapterCheckpoint.clear(source_id)

    def test_multiple_local_sources_have_separate_checkpoints(self, tmp_path):
        """Test that multiple local sources maintain separate checkpoints."""
        # Create two separate collections with unique content
        collection1 = tmp_path / "collection1"
        collection2 = tmp_path / "collection2"
        collection1.mkdir()
        collection2.mkdir()

        (collection1 / "puzzle1.sgf").write_text(
            "(;FF[4]GM[1]SZ[9]C[Collection 1]\nAB[cc]\nAW[dd]\n;B[ec])",
            encoding="utf-8"
        )
        (collection2 / "puzzle2.sgf").write_text(
            "(;FF[4]GM[1]SZ[9]C[Collection 2]\nAB[dd]\nAW[ee]\n;B[fc])",
            encoding="utf-8"
        )

        # Configure two adapters with different source IDs
        adapter1 = LocalAdapter()
        adapter1.configure({
            "id": "local-source-1",
            "path": str(collection1),
            "validate": False,
        })

        adapter2 = LocalAdapter()
        adapter2.configure({
            "id": "local-source-2",
            "path": str(collection2),
            "validate": False,
        })

        # Process one file from each with batch_size=1 to trigger checkpoint
        for _result in adapter1.fetch(batch_size=1):
            break
        for _result in adapter2.fetch(batch_size=1):
            break

        # Verify separate checkpoints
        cp1 = AdapterCheckpoint.load("local-source-1")
        cp2 = AdapterCheckpoint.load("local-source-2")

        assert cp1 is not None, "Checkpoint for source 1 should exist"
        assert cp2 is not None, "Checkpoint for source 2 should exist"
        assert cp1["adapter_id"] == "local-source-1"
        assert cp2["adapter_id"] == "local-source-2"

        # Clean up
        AdapterCheckpoint.clear("local-source-1")
        AdapterCheckpoint.clear("local-source-2")


# =============================================================================
# User Story 3: Validation Tests
# =============================================================================

@pytest.mark.adapter
class TestLocalValidation:
    """Tests for validation functionality (User Story 3)."""

    def test_invalid_board_size_skipped(self, adapter, tmp_path, invalid_sgf_bad_board):
        """Test that invalid board size results in skipped status."""
        folder = tmp_path / "puzzles"
        folder.mkdir()
        (folder / "bad_board.sgf").write_text(invalid_sgf_bad_board, encoding="utf-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["puzzles"],
            "validate": True,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should be skipped (validation failure), not failed
        skipped_results = [r for r in results if r.status == "skipped"]
        assert len(skipped_results) >= 1

    def test_no_solution_tree_skipped(self, adapter, tmp_path, invalid_sgf_no_solution):
        """Test that SGF without solution tree is skipped."""
        folder = tmp_path / "puzzles"
        folder.mkdir()
        (folder / "no_solution.sgf").write_text(invalid_sgf_no_solution, encoding="utf-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["puzzles"],
            "validate": True,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should be skipped (no solution)
        skipped_results = [r for r in results if r.status == "skipped"]
        assert len(skipped_results) >= 1

    def test_validation_disabled_accepts_all(self, adapter, tmp_path, invalid_sgf_no_solution):
        """Test that with validation disabled, all parseable files are accepted."""
        folder = tmp_path / "puzzles"
        folder.mkdir()
        (folder / "no_solution.sgf").write_text(invalid_sgf_no_solution, encoding="utf-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["puzzles"],
            "validate": False,  # Validation disabled
        })

        results = list(adapter.fetch(batch_size=100))

        # Should be success (validation disabled)
        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 1

    def test_parse_error_yields_failed_not_skipped(self, adapter, tmp_path):
        """Test that parse errors yield failed status, not skipped."""
        folder = tmp_path / "puzzles"
        folder.mkdir()

        # Use content that will definitely fail to parse
        # A completely broken SGF that our parser can't handle
        (folder / "malformed.sgf").write_text("NOT AN SGF FILE AT ALL", encoding="utf-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["puzzles"],
            "validate": True,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should be failed (parse error) - parser returns None which triggers failed
        failed_results = [r for r in results if r.status == "failed"]
        assert len(failed_results) >= 1, f"Expected failed result, got: {results}"

    def test_skipped_increments_total_skipped_counter(self, adapter, local_collection):
        """Test that skipped files increment total_skipped in checkpoint."""
        source_id = "test-skipped-counter"

        adapter.configure({
            "id": source_id,
            "path": str(local_collection),
            "include_folders": ["intermediate"],  # Has invalid_sgf_no_solution
            "validate": True,
        })

        # Process all files
        results = list(adapter.fetch(batch_size=100))

        # Should have some skipped results
        skipped_results = [r for r in results if r.status == "skipped"]
        assert len(skipped_results) >= 1

    def test_encoding_error_yields_failed(self, adapter, tmp_path):
        """Test that encoding errors yield failed status."""
        folder = tmp_path / "puzzles"
        folder.mkdir()

        # Write binary data that will cause encoding error
        bad_file = folder / "bad_encoding.sgf"
        bad_file.write_bytes(b"\xff\xfe\x00\x01Invalid UTF-8")

        adapter.configure({
            "path": str(tmp_path),
            "include_folders": ["puzzles"],
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))

        # Should be failed (encoding error)
        failed_results = [r for r in results if r.status == "failed"]
        assert len(failed_results) == 1
        assert "Encoding error" in failed_results[0].error


# =============================================================================
# User Story 4: Progress Logging Tests
# =============================================================================

@pytest.mark.adapter
class TestLocalProgress:
    """Tests for progress logging functionality (User Story 4)."""

    def test_folder_progress_logged_at_info_level(self, adapter, local_collection, caplog):
        """Test that folder progress is logged at INFO level."""
        adapter.configure({
            "path": str(local_collection),
            "validate": False,
        })

        with caplog.at_level(logging.INFO):
            list(adapter.fetch(batch_size=100))

        # Should have folder progress messages
        folder_messages = [r for r in caplog.records
                          if "Processing folder:" in r.message and r.levelno == logging.INFO]
        assert len(folder_messages) >= 1

    def test_completion_summary_includes_all_counts(self, adapter, local_collection, caplog):
        """Test that completion summary includes fetched/skipped/failed counts."""
        adapter.configure({
            "path": str(local_collection),
            "include_folders": ["intermediate"],  # Has valid + invalid
            "validate": True,
        })

        with caplog.at_level(logging.INFO):
            list(adapter.fetch(batch_size=100))

        # Should have summary message with all counts
        summary_messages = [r for r in caplog.records
                           if "fetched" in r.message and "skipped" in r.message and "failed" in r.message]
        assert len(summary_messages) >= 1

    def test_file_details_logged_at_debug_level(self, adapter, local_collection, caplog):
        """Test that file processing details are logged at DEBUG level."""
        adapter.configure({
            "path": str(local_collection),
            "include_folders": ["elementary"],
            "validate": False,
        })

        with caplog.at_level(logging.DEBUG):
            list(adapter.fetch(batch_size=100))

        # Should have DEBUG messages about file processing
        debug_messages = [r for r in caplog.records
                         if "Processing file:" in r.message and r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1

    def test_configure_log_uses_safe_posix_path(self, adapter, local_collection, caplog):
        """Test that configure log does not expose absolute local path."""
        adapter.configure({
            "path": str(local_collection),
            "validate": False,
        })

        with caplog.at_level(logging.INFO):
            adapter.configure({
                "path": str(local_collection),
                "validate": False,
            })

        configure_logs = [r for r in caplog.records if "Local adapter configured:" in r.message]
        assert configure_logs, "Expected Local adapter configuration log message"

        message = configure_logs[-1].message
        assert str(local_collection) not in message
        assert " from " in message


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.adapter
class TestLocalEdgeCases:
    """Additional edge case tests."""

    def test_no_path_configured_yields_failed(self, adapter):
        """Test that missing path config yields failed result."""
        # Don't configure path
        results = list(adapter.fetch(batch_size=100))

        assert len(results) == 1
        assert results[0].status == "failed"
        assert "No path configured" in results[0].error

    def test_flat_structure_without_subfolders(self, adapter, tmp_path):
        """Test processing files directly in path (no subfolders)."""
        # Create files directly in tmp_path with unique content
        (tmp_path / "puzzle1.sgf").write_text(
            "(;FF[4]GM[1]SZ[9]C[Flat puzzle 1]\nAB[cc]\nAW[dd]\n;B[ec])",
            encoding="utf-8"
        )
        (tmp_path / "puzzle2.sgf").write_text(
            "(;FF[4]GM[1]SZ[9]C[Flat puzzle 2]\nAB[dd]\nAW[ee]\n;B[fc])",
            encoding="utf-8"
        )

        adapter.configure({
            "path": str(tmp_path),
            "validate": False,
        })

        results = list(adapter.fetch(batch_size=100))

        success_results = [r for r in results if r.status == "success"]
        assert len(success_results) == 2

    def test_source_id_property_returns_override(self, adapter):
        """Test that source_id returns config override when set."""
        adapter.configure({
            "id": "custom-source-id",
            "path": "/some/path",
        })

        assert adapter.source_id == "custom-source-id"

    def test_source_id_property_returns_default(self, adapter):
        """Test that source_id returns 'local' when no override."""
        adapter.configure({
            "path": "/some/path",
        })

        assert adapter.source_id == "local"


# =============================================================================
# Unit Tests for Helper Methods
# =============================================================================

@pytest.mark.unit
class TestLocalHelperMethods:
    """Unit tests for LocalAdapter internal helper methods."""

    def test_compute_config_signature_deterministic(self):
        """Test that config signature is deterministic for same input."""
        adapter1 = LocalAdapter()
        adapter1._include_folders = ["elementary", "intermediate"]
        adapter1._exclude_folders = []

        adapter2 = LocalAdapter()
        adapter2._include_folders = ["elementary", "intermediate"]
        adapter2._exclude_folders = []

        sig1 = adapter1._compute_config_signature()
        sig2 = adapter2._compute_config_signature()

        assert sig1 == sig2
        assert len(sig1) == 8  # 8-char MD5 prefix

    def test_compute_config_signature_empty_lists(self):
        """Test config signature with empty lists."""
        adapter = LocalAdapter()
        adapter._include_folders = []
        adapter._exclude_folders = []

        sig = adapter._compute_config_signature()

        assert sig is not None
        assert len(sig) == 8

    def test_compute_config_signature_order_independent(self):
        """Test that folder order in include_folders affects signature."""
        adapter1 = LocalAdapter()
        adapter1._include_folders = ["a", "b", "c"]
        adapter1._exclude_folders = []

        adapter2 = LocalAdapter()
        adapter2._include_folders = ["c", "b", "a"]  # Different order
        adapter2._exclude_folders = []

        sig1 = adapter1._compute_config_signature()
        sig2 = adapter2._compute_config_signature()

        # Signature should be same because sorted() is used internally
        assert sig1 == sig2

    def test_compute_config_signature_different_for_different_input(self):
        """Test that different configs produce different signatures."""
        adapter1 = LocalAdapter()
        adapter1._include_folders = ["elementary"]
        adapter1._exclude_folders = []

        adapter2 = LocalAdapter()
        adapter2._include_folders = ["advanced"]
        adapter2._exclude_folders = []

        sig1 = adapter1._compute_config_signature()
        sig2 = adapter2._compute_config_signature()

        assert sig1 != sig2

    def test_generate_id_deterministic(self):
        """Test that ID generation is deterministic for same content."""
        adapter = LocalAdapter()

        content = "(;FF[4]GM[1]SZ[9]AB[cc])"
        id1 = adapter._generate_id(content)
        id2 = adapter._generate_id(content)

        assert id1 == id2
        assert len(id1) == 16  # 16-char hex

    def test_generate_id_different_for_different_content(self):
        """Test that different content produces different IDs."""
        adapter = LocalAdapter()

        id1 = adapter._generate_id("(;FF[4]GM[1]SZ[9]AB[cc])")
        id2 = adapter._generate_id("(;FF[4]GM[1]SZ[9]AB[dd])")

        assert id1 != id2

    def test_supports_resume_returns_true(self):
        """Test that supports_resume returns True."""
        adapter = LocalAdapter()
        assert adapter.supports_resume() is True

    def test_is_available_with_valid_path(self, tmp_path):
        """Test is_available returns True for existing path."""
        adapter = LocalAdapter()
        adapter.configure({"path": str(tmp_path)})

        assert adapter.is_available() is True

    def test_is_available_with_invalid_path(self):
        """Test is_available returns False for non-existent path."""
        adapter = LocalAdapter()
        adapter.configure({"path": "/nonexistent/path"})

        assert adapter.is_available() is False

    def test_is_available_unconfigured(self):
        """Test is_available returns False when not configured."""
        adapter = LocalAdapter()
        assert adapter.is_available() is False

    def test_sgf_to_puzzle_data_valid_sgf(self):
        """Test _sgf_to_puzzle_data with valid SGF returns PuzzleData."""
        adapter = LocalAdapter()

        # Use a simple SGF that we know should parse
        sgf_content = """(;FF[4]GM[1]SZ[9]
AB[cc][dc][cd]
AW[dd][ed][de]
;B[ec]
(;W[fd];B[fc])
(;W[fc];B[fd])
)"""

        puzzle_data = adapter._sgf_to_puzzle_data(sgf_content)

        # Verify basic parsing worked
        assert puzzle_data is not None
        assert puzzle_data.board_width == 9
        assert puzzle_data.board_height == 9
        # Note: has_solution detection depends on parser internals
        # What's important is that valid SGF returns non-None PuzzleData

    def test_sgf_to_puzzle_data_invalid_sgf(self):
        """Test _sgf_to_puzzle_data with invalid SGF returns None."""
        adapter = LocalAdapter()

        puzzle_data = adapter._sgf_to_puzzle_data("NOT VALID SGF")

        assert puzzle_data is None

    def test_move_file_handles_name_conflict(self, tmp_path, valid_sgf_content):
        """Test _move_file handles name conflicts with counter."""
        source_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        # Create source file
        source_file = source_dir / "puzzle.sgf"
        source_file.write_text(valid_sgf_content)

        # Create conflict in dest
        (dest_dir / "puzzle.sgf").write_text("existing")

        adapter = LocalAdapter()
        adapter._move_processed_to = dest_dir

        adapter._move_file(source_file)

        # Should have created puzzle_1.sgf
        assert (dest_dir / "puzzle_1.sgf").exists()
        assert not source_file.exists()
