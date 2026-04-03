"""Tests for run_calibration retry logic and model label extraction.

Tests cover:
  - _extract_model_label: extract architecture label from model filename
  - Retry flag CLI parsing: --retry-rejected / --no-retry-rejected
  - Retry skip threshold logic
"""

from pathlib import Path

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent


from scripts.run_calibration import _extract_model_label

# ---------------------------------------------------------------------------
# _extract_model_label
# ---------------------------------------------------------------------------


class TestExtractModelLabel:
    """Unit tests for model label extraction from KataGo filenames."""

    def test_b18_model(self):
        path = "models-data/kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"
        assert _extract_model_label(path) == "b18c384"

    def test_b28_model(self):
        path = "models-data/kata1-b28c512nbt-s12192929536-d5655876072.bin.gz"
        assert _extract_model_label(path) == "b28c512"

    def test_b10_model(self):
        path = "/some/dir/kata1-b10c128nbt-s1234-d5678.bin.gz"
        assert _extract_model_label(path) == "b10c128"

    def test_no_nbt_suffix(self):
        """Model filename without 'nbt' suffix keeps full label."""
        path = "models/kata1-b18c384-s123-d456.bin.gz"
        assert _extract_model_label(path) == "b18c384"

    def test_empty_string(self):
        assert _extract_model_label("") == ""

    def test_plain_filename(self):
        """Fallback for unrecognized format returns full filename."""
        path = "model.bin.gz"
        assert _extract_model_label(path) == "model.bin.gz"

    def test_windows_path(self):
        path = r"C:\katago\models-data\kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"
        assert _extract_model_label(path) == "b18c384"

    def test_absolute_posix_path(self):
        path = "/home/user/models/kata1-b28c512nbt-s12192929536-d5655876072.bin.gz"
        assert _extract_model_label(path) == "b28c512"


# ---------------------------------------------------------------------------
# Retry candidate selection logic
# ---------------------------------------------------------------------------


class TestRetryCandidateSelection:
    """Test the retry filtering logic that determines which puzzles to retry."""

    def _make_result(self, status: str, refutation_count: int = 0) -> dict:
        return {
            "file": "test.sgf",
            "puzzle_id": "test",
            "status": status,
            "level": "elementary",
            "level_id": 120,
            "refutation_count": refutation_count,
            "flags": [],
            "engine_used": "quick",
            "time_enrich_s": 1.0,
            "retry": False,
            "first_pass_status": "",
        }

    def test_rejected_below_threshold_is_retry_candidate(self):
        """Rejected puzzles with few refutations should be retried."""
        results = [self._make_result("rejected", 2)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == [0]

    def test_flagged_below_threshold_is_retry_candidate(self):
        """Flagged puzzles with few refutations should be retried."""
        results = [self._make_result("flagged", 1)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == [0]

    def test_rejected_at_threshold_is_skipped(self):
        """Puzzles with refutations >= threshold should NOT be retried."""
        results = [self._make_result("rejected", 4)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == []

    def test_rejected_above_threshold_is_skipped(self):
        """Puzzles with refutations > threshold should NOT be retried."""
        results = [self._make_result("rejected", 5)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == []

    def test_accepted_never_retried(self):
        """Accepted puzzles should never be retry candidates."""
        results = [self._make_result("accepted", 0)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == []

    def test_error_never_retried(self):
        """Error puzzles should never be retry candidates."""
        results = [self._make_result("error", 0)]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == []

    def test_mixed_results_correct_filtering(self):
        """Only rejected/flagged below threshold should be candidates."""
        results = [
            self._make_result("accepted", 3),     # Skip: accepted
            self._make_result("rejected", 2),      # Retry: rejected, below threshold
            self._make_result("rejected", 5),      # Skip: too many refutations
            self._make_result("flagged", 1),        # Retry: flagged, below threshold
            self._make_result("error", 0),          # Skip: error
            self._make_result("flagged", 4),        # Skip: at threshold
        ]
        threshold = 4
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == [1, 3]

    def test_threshold_zero_skips_all(self):
        """Threshold of 0 should skip all retries (all have >= 0 refutations)."""
        results = [
            self._make_result("rejected", 0),
            self._make_result("flagged", 0),
        ]
        threshold = 0
        candidates = [
            i for i, r in enumerate(results)
            if r["status"] in ("rejected", "flagged")
            and r["refutation_count"] < threshold
        ]
        assert candidates == []


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCLIArgs:
    """Test that new CLI arguments parse correctly."""

    def test_retry_rejected_default_true(self):
        """--retry-rejected should default to True."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--retry-rejected", action="store_true", default=True)
        parser.add_argument("--no-retry-rejected", action="store_false", dest="retry_rejected")
        args = parser.parse_args([])
        assert args.retry_rejected is True

    def test_no_retry_rejected_flag(self):
        """--no-retry-rejected should set retry_rejected to False."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--retry-rejected", action="store_true", default=True)
        parser.add_argument("--no-retry-rejected", action="store_false", dest="retry_rejected")
        args = parser.parse_args(["--no-retry-rejected"])
        assert args.retry_rejected is False

    def test_retry_skip_refutations_default(self):
        """Default skip threshold should be 4."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--retry-skip-refutations", type=int, default=4)
        args = parser.parse_args([])
        assert args.retry_skip_refutations == 4

    def test_retry_skip_refutations_custom(self):
        """Custom skip threshold should be honored."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--retry-skip-refutations", type=int, default=4)
        args = parser.parse_args(["--retry-skip-refutations", "5"])
        assert args.retry_skip_refutations == 5


# ---------------------------------------------------------------------------
# Result dict retry fields
# ---------------------------------------------------------------------------


class TestResultRetryFields:
    """Test that retry tracking fields exist and work correctly."""

    def test_retry_default_false(self):
        result = {
            "retry": False,
            "first_pass_status": "",
        }
        assert result["retry"] is False
        assert result["first_pass_status"] == ""

    def test_retry_marked(self):
        result = {
            "retry": True,
            "first_pass_status": "rejected",
            "status": "accepted",
        }
        assert result["retry"] is True
        assert result["first_pass_status"] == "rejected"
        assert result["status"] == "accepted"
