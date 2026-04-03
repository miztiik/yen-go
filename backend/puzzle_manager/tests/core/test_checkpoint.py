"""
Tests for AdapterCheckpoint utility.

Tests verify:
- Checkpoint save/load/clear/exists/get_path operations
- Corrupted checkpoint handling
- Proper file format with wrapper structure
- Thread-safe operation (future consideration)
"""

import json
from datetime import datetime

import pytest

from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint

# ==============================
# Test Fixtures
# ==============================

@pytest.fixture
def temp_runtime_dir(tmp_path):
    """Create a temporary runtime directory for checkpoints."""
    runtime_dir = tmp_path / ".pm-runtime" / "state"
    runtime_dir.mkdir(parents=True)
    return runtime_dir


@pytest.fixture
def mock_runtime_path(tmp_path, monkeypatch):
    """Mock the runtime path to use temp directory."""
    runtime_dir = tmp_path / ".pm-runtime" / "state"
    runtime_dir.mkdir(parents=True)

    # Patch get_runtime_dir to return our temp path
    monkeypatch.setattr(
        "backend.puzzle_manager.core.checkpoint.get_runtime_dir",
        lambda: tmp_path / ".pm-runtime"
    )
    return runtime_dir


# ==============================
# T002: Basic CRUD Operations
# ==============================

class TestAdapterCheckpointSave:
    """Tests for AdapterCheckpoint.save() method."""

    def test_save_creates_checkpoint_file(self, mock_runtime_path):
        """T002a: save() should create checkpoint JSON file."""
        state = {"current_folder": "1a. Tsumego Beginner", "files_completed": 50}

        AdapterCheckpoint.save("sanderland", state)

        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        assert checkpoint_path.exists(), "Checkpoint file should be created"

    def test_save_includes_timestamp(self, mock_runtime_path):
        """T002b: save() should add ISO 8601 timestamp."""
        state = {"files_completed": 10}

        AdapterCheckpoint.save("sanderland", state)

        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        data = json.loads(checkpoint_path.read_text())

        assert "timestamp" in data
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_save_includes_adapter_id(self, mock_runtime_path):
        """T002c: save() should include adapter_id in file."""
        state = {"test": "data"}

        AdapterCheckpoint.save("ogs", state)

        checkpoint_path = mock_runtime_path / "ogs_checkpoint.json"
        data = json.loads(checkpoint_path.read_text())

        assert data["adapter_id"] == "ogs"

    def test_save_wraps_state_in_structure(self, mock_runtime_path):
        """T002d: save() should wrap state in standard structure."""
        state = {
            "current_folder": "1b. Tsumego Intermediate",
            "files_completed": 245,
            "total_processed": 1308,
        }

        AdapterCheckpoint.save("sanderland", state)

        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        data = json.loads(checkpoint_path.read_text())

        assert "adapter_id" in data
        assert "timestamp" in data
        assert "state" in data
        assert data["state"] == state

    def test_save_creates_directory_if_missing(self, tmp_path, monkeypatch):
        """T002e: save() should create directory structure if needed."""
        # Point to non-existent directory
        monkeypatch.setattr(
            "backend.puzzle_manager.core.checkpoint.get_runtime_dir",
            lambda: tmp_path / "new-runtime"
        )

        state = {"test": "data"}
        AdapterCheckpoint.save("test-adapter", state)

        checkpoint_path = tmp_path / "new-runtime" / "state" / "test-adapter_checkpoint.json"
        assert checkpoint_path.exists()

    def test_save_overwrites_existing_checkpoint(self, mock_runtime_path):
        """T002f: save() should overwrite existing checkpoint."""
        # Save initial state
        AdapterCheckpoint.save("sanderland", {"files_completed": 10})

        # Save updated state
        AdapterCheckpoint.save("sanderland", {"files_completed": 100})

        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        data = json.loads(checkpoint_path.read_text())

        assert data["state"]["files_completed"] == 100


class TestAdapterCheckpointLoad:
    """Tests for AdapterCheckpoint.load() method."""

    def test_load_returns_saved_state(self, mock_runtime_path):
        """T002g: load() should return previously saved state."""
        state = {
            "current_folder": "1a. Tsumego Beginner",
            "files_completed": 75,
            "total_processed": 75,
        }
        AdapterCheckpoint.save("sanderland", state)

        loaded = AdapterCheckpoint.load("sanderland")

        assert loaded is not None
        assert loaded["state"] == state

    def test_load_returns_none_when_not_found(self, mock_runtime_path):
        """T002h: load() should return None if checkpoint doesn't exist."""
        result = AdapterCheckpoint.load("nonexistent-adapter")

        assert result is None

    def test_load_returns_wrapper_with_metadata(self, mock_runtime_path):
        """T002i: load() should return full wrapper structure."""
        state = {"test": "data"}
        AdapterCheckpoint.save("ogs", state)

        loaded = AdapterCheckpoint.load("ogs")

        assert "adapter_id" in loaded
        assert "timestamp" in loaded
        assert "state" in loaded
        assert loaded["adapter_id"] == "ogs"


class TestAdapterCheckpointClear:
    """Tests for AdapterCheckpoint.clear() method."""

    def test_clear_deletes_checkpoint_file(self, mock_runtime_path):
        """T002j: clear() should delete checkpoint file."""
        AdapterCheckpoint.save("sanderland", {"test": "data"})
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        assert checkpoint_path.exists()

        result = AdapterCheckpoint.clear("sanderland")

        assert result is True
        assert not checkpoint_path.exists()

    def test_clear_returns_false_when_not_found(self, mock_runtime_path):
        """T002k: clear() should return False if file doesn't exist."""
        result = AdapterCheckpoint.clear("nonexistent-adapter")

        assert result is False


class TestAdapterCheckpointExists:
    """Tests for AdapterCheckpoint.exists() method."""

    def test_exists_returns_true_when_checkpoint_exists(self, mock_runtime_path):
        """T002l: exists() should return True when file exists."""
        AdapterCheckpoint.save("sanderland", {"test": "data"})

        assert AdapterCheckpoint.exists("sanderland") is True

    def test_exists_returns_false_when_not_found(self, mock_runtime_path):
        """T002m: exists() should return False when file missing."""
        assert AdapterCheckpoint.exists("nonexistent") is False


class TestAdapterCheckpointGetPath:
    """Tests for AdapterCheckpoint.get_path() method."""

    def test_get_path_returns_correct_path(self, mock_runtime_path):
        """T002n: get_path() should return correct checkpoint path."""
        path = AdapterCheckpoint.get_path("sanderland")

        assert path.name == "sanderland_checkpoint.json"
        assert "state" in str(path)


# ==============================
# T003: Corrupted Checkpoint Handling
# ==============================

class TestCorruptedCheckpointHandling:
    """Tests for handling corrupted checkpoint files."""

    def test_load_returns_none_for_invalid_json(self, mock_runtime_path, caplog):
        """T003a: load() should return None for corrupted JSON."""
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        checkpoint_path.write_text("{ invalid json }", encoding="utf-8")

        result = AdapterCheckpoint.load("sanderland")

        assert result is None
        # Should log warning
        assert any("corrupt" in record.message.lower() or "invalid" in record.message.lower()
                   for record in caplog.records)

    def test_load_deletes_corrupted_file(self, mock_runtime_path):
        """T003b: load() should delete corrupted checkpoint file."""
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        checkpoint_path.write_text("not valid json at all", encoding="utf-8")

        AdapterCheckpoint.load("sanderland")

        # File should be deleted after detecting corruption
        assert not checkpoint_path.exists()

    def test_load_handles_missing_state_key(self, mock_runtime_path, caplog):
        """T003c: load() should handle JSON missing 'state' key."""
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        # Valid JSON but missing required structure
        checkpoint_path.write_text('{"adapter_id": "sanderland"}', encoding="utf-8")

        result = AdapterCheckpoint.load("sanderland")

        # Should return None or handle gracefully
        assert result is None or "state" not in result

    def test_load_handles_empty_file(self, mock_runtime_path):
        """T003d: load() should handle empty checkpoint file."""
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        checkpoint_path.write_text("", encoding="utf-8")

        result = AdapterCheckpoint.load("sanderland")

        assert result is None


# ==============================
# Integration Tests
# ==============================

class TestCheckpointIntegration:
    """Integration tests for checkpoint workflow."""

    def test_full_checkpoint_lifecycle(self, mock_runtime_path):
        """Test complete save -> load -> update -> clear cycle."""
        # Initial state
        state1 = {
            "current_folder": "1a. Tsumego Beginner",
            "current_folder_index": 0,
            "files_completed": 0,
            "total_processed": 0,
            "total_failed": 0,
        }

        # Save initial
        AdapterCheckpoint.save("sanderland", state1)
        assert AdapterCheckpoint.exists("sanderland")

        # Load and verify
        loaded = AdapterCheckpoint.load("sanderland")
        assert loaded["state"]["files_completed"] == 0

        # Update
        state2 = loaded["state"].copy()
        state2["files_completed"] = 100
        state2["total_processed"] = 100
        AdapterCheckpoint.save("sanderland", state2)

        # Reload and verify update
        reloaded = AdapterCheckpoint.load("sanderland")
        assert reloaded["state"]["files_completed"] == 100

        # Clear
        cleared = AdapterCheckpoint.clear("sanderland")
        assert cleared is True
        assert not AdapterCheckpoint.exists("sanderland")

    def test_multiple_adapters_independent(self, mock_runtime_path):
        """Checkpoints for different adapters should be independent."""
        AdapterCheckpoint.save("sanderland", {"index": 10})
        AdapterCheckpoint.save("ogs", {"index": 20})

        sanderland_data = AdapterCheckpoint.load("sanderland")
        ogs_data = AdapterCheckpoint.load("ogs")

        assert sanderland_data["state"]["index"] == 10
        assert ogs_data["state"]["index"] == 20

        # Clearing one shouldn't affect other
        AdapterCheckpoint.clear("sanderland")
        assert not AdapterCheckpoint.exists("sanderland")
        assert AdapterCheckpoint.exists("ogs")

# ==============================
# Schema Versioning Tests
# ==============================

class TestSchemaVersioning:
    """Tests for checkpoint schema versioning and migration."""

    def test_save_includes_schema_version(self, mock_runtime_path):
        """save() should include schema_version in checkpoint."""
        from backend.puzzle_manager.core.checkpoint import CHECKPOINT_SCHEMA_VERSION

        AdapterCheckpoint.save("sanderland", {"files_completed": 10})

        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        data = json.loads(checkpoint_path.read_text())

        assert "schema_version" in data
        assert data["schema_version"] == CHECKPOINT_SCHEMA_VERSION
        assert data["schema_version"] == 2  # Current version

    def test_load_migrates_v1_checkpoint(self, mock_runtime_path, caplog):
        """load() should migrate v1 checkpoints to current version."""
        import logging
        caplog.set_level(logging.INFO)

        # Create a v1 checkpoint (no schema_version field)
        checkpoint_path = mock_runtime_path / "sanderland_checkpoint.json"
        v1_data = {
            "adapter_id": "sanderland",
            "timestamp": "2025-01-01T00:00:00Z",
            "state": {"files_completed": 50},
        }
        checkpoint_path.write_text(json.dumps(v1_data), encoding="utf-8")

        loaded = AdapterCheckpoint.load("sanderland")

        assert loaded is not None
        # Should have been upgraded to current schema
        assert loaded["schema_version"] == 2
        # State should be preserved
        assert loaded["state"]["files_completed"] == 50
        # Should log migration message (contains "schema v1" and "Migrating")
        assert any("schema v1" in record.message and "migrating" in record.message.lower()
                   for record in caplog.records)

    def test_load_handles_current_version(self, mock_runtime_path, caplog):
        """load() should handle current version checkpoints without migration."""
        AdapterCheckpoint.save("sanderland", {"files_completed": 10})

        caplog.clear()
        loaded = AdapterCheckpoint.load("sanderland")

        assert loaded["schema_version"] == 2
        # Should NOT log migration message
        assert not any("migrating" in record.message.lower()
                       for record in caplog.records)

    def test_schema_version_constant_exported(self):
        """CHECKPOINT_SCHEMA_VERSION should be exported from core."""
        from backend.puzzle_manager.core import CHECKPOINT_SCHEMA_VERSION

        assert CHECKPOINT_SCHEMA_VERSION == 2
