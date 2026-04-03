"""Tests for publish stage cleanup changes.

Covers:
- _strip_ym_filename: strips f from YM, no-op when absent/malformed
- trace_id extraction from YM in publish log entries
- PublishLogEntry serialization without removed fields
"""

import json
from types import SimpleNamespace

from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.stages.publish import _strip_ym_filename


class TestStripYmFilename:
    """Tests for _strip_ym_filename helper."""

    def test_strips_f_from_ym(self):
        """f key is removed from YM JSON."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(
                pipeline_meta='{"t":"abc123","f":"puzzle_42.sgf","i":"20260306-run1"}'
            )
        )
        _strip_ym_filename(game)
        meta = json.loads(game.yengo_props.pipeline_meta)
        assert "f" not in meta
        assert meta["t"] == "abc123"
        assert meta["i"] == "20260306-run1"

    def test_noop_when_no_f(self):
        """No-op when YM has no f key."""
        original = '{"t":"abc123","i":"20260306-run1"}'
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(pipeline_meta=original)
        )
        _strip_ym_filename(game)
        assert json.loads(game.yengo_props.pipeline_meta) == json.loads(original)

    def test_noop_for_malformed_ym(self):
        """No-op for malformed YM JSON."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(pipeline_meta="not-json")
        )
        _strip_ym_filename(game)
        assert game.yengo_props.pipeline_meta == "not-json"

    def test_noop_for_none_ym(self):
        """No-op when pipeline_meta is None."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(pipeline_meta=None)
        )
        _strip_ym_filename(game)
        assert game.yengo_props.pipeline_meta is None

    def test_noop_for_empty_string_ym(self):
        """No-op when pipeline_meta is empty string."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(pipeline_meta="")
        )
        _strip_ym_filename(game)
        assert game.yengo_props.pipeline_meta == ""

    def test_preserves_all_other_keys(self):
        """All keys except f are preserved."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(
                pipeline_meta='{"t":"abc","f":"file.sgf","i":"run1","ct":3,"tc":5}'
            )
        )
        _strip_ym_filename(game)
        meta = json.loads(game.yengo_props.pipeline_meta)
        assert set(meta.keys()) == {"t", "i", "ct", "tc"}

    def test_compact_separators(self):
        """Output uses compact JSON separators (no spaces)."""
        game = SimpleNamespace(
            yengo_props=SimpleNamespace(
                pipeline_meta='{"t": "abc", "f": "file.sgf"}'
            )
        )
        _strip_ym_filename(game)
        assert " " not in game.yengo_props.pipeline_meta


class TestPublishLogEntryWithoutDeadFields:
    """Verify PublishLogEntry no longer has source_file/original_filename."""

    def test_no_source_file_field(self):
        """source_file field no longer exists on PublishLogEntry."""
        entry = PublishLogEntry(
            run_id="20260306-abc12345",
            puzzle_id="hash123",
            source_id="test",
            path="sgf/0001/hash123.sgf",
            quality=3,
            trace_id="trace456",
            level="beginner",
        )
        assert not hasattr(entry, "source_file")

    def test_no_original_filename_field(self):
        """original_filename field no longer exists on PublishLogEntry."""
        entry = PublishLogEntry(
            run_id="20260306-abc12345",
            puzzle_id="hash123",
            source_id="test",
            path="sgf/0001/hash123.sgf",
            quality=3,
            trace_id="trace456",
            level="beginner",
        )
        assert not hasattr(entry, "original_filename")

    def test_serialization_excludes_dead_fields(self):
        """to_jsonl output does not contain source_file or original_filename."""
        entry = PublishLogEntry(
            run_id="20260306-abc12345",
            puzzle_id="hash123",
            source_id="test",
            path="sgf/0001/hash123.sgf",
            quality=3,
            trace_id="trace456",
            level="beginner",
        )
        data = json.loads(entry.to_jsonl())
        assert "source_file" not in data
        assert "original_filename" not in data

    def test_deserialization_ignores_legacy_fields(self):
        """from_jsonl gracefully handles JSON that still has the old fields."""
        jsonl = json.dumps({
            "run_id": "20260306-abc12345",
            "puzzle_id": "hash123",
            "source_id": "test",
            "path": "sgf/0001/hash123.sgf",
            "quality": 3,
            "tags": [],
            "trace_id": "trace456",
            "level": "beginner",
            "source_file": "old_value",
            "original_filename": "old.sgf",
            "collections": [],
        })
        entry = PublishLogEntry.from_jsonl(jsonl)
        assert entry.puzzle_id == "hash123"
        assert entry.trace_id == "trace456"
        assert not hasattr(entry, "source_file")
