"""
Unit tests for atomic state writes (Step 5) and StageResult improvements.
"""


from backend.puzzle_manager.stages.protocol import StageResult


class TestStageResultRemaining:
    """Tests for remaining field in StageResult."""

    def test_remaining_defaults_to_zero(self):
        """remaining should default to 0."""
        result = StageResult(success=True, processed=5)
        assert result.remaining == 0

    def test_remaining_in_partial_result(self):
        """partial_result should accept remaining parameter."""
        result = StageResult.partial_result(
            processed=10, failed=0, errors=[], duration=1.0,
            skipped=2, remaining=8,
        )
        assert result.remaining == 8
        assert result.success is True

    def test_remaining_in_str_when_nonzero(self):
        """__str__ should include remaining when > 0."""
        result = StageResult(success=True, processed=5, remaining=3)
        s = str(result)
        assert "remaining=3" in s

    def test_remaining_not_in_str_when_zero(self):
        """__str__ should omit remaining when 0."""
        result = StageResult(success=True, processed=5, remaining=0)
        s = str(result)
        assert "remaining" not in s

    def test_success_result_no_remaining(self):
        """success_result factory should have remaining=0."""
        result = StageResult.success_result(processed=5, duration=1.0)
        assert result.remaining == 0

    def test_failure_result_no_remaining(self):
        """failure_result factory should have remaining=0."""
        result = StageResult.failure_result(error="failed", duration=1.0)
        assert result.remaining == 0
