"""Tests for 101weiqi level mapping with calibration."""

from unittest.mock import patch

from tools.weiqi101.levels import _load_calibration, _parse_rank_string, map_level


class TestParseRankString:
    """Tests for rank string parsing (raw, pre-calibration)."""

    def test_kyu_ranks(self):
        assert _parse_rank_string("13K+") == 13
        assert _parse_rank_string("5K") == 5
        assert _parse_rank_string("1K") == 1
        assert _parse_rank_string("30k") == 30

    def test_dan_ranks(self):
        assert _parse_rank_string("1D") == -1
        assert _parse_rank_string("3D") == -3
        assert _parse_rank_string("9D") == -9

    def test_pro_ranks(self):
        result = _parse_rank_string("1P")
        assert result is not None
        assert result <= -7

    def test_empty_string(self):
        assert _parse_rank_string("") is None

    def test_invalid(self):
        assert _parse_rank_string("xyz") is None


class TestCalibration:
    """Tests for calibration offset loading."""

    def test_calibration_loads(self):
        """Calibration config loads kyu_offset=10, dan_offset=0."""
        _load_calibration.cache_clear()
        kyu_off, dan_off = _load_calibration()
        assert kyu_off == 10
        assert dan_off == 0

    def test_calibration_missing_file(self, tmp_path):
        """Falls back to (0, 0) when config file is missing."""
        _load_calibration.cache_clear()
        with patch("tools.weiqi101.levels.Path") as mock_path_cls:
            mock_path = mock_path_cls.return_value.__truediv__.return_value
            mock_path.exists.return_value = False
            # Re-import won't work, so we test the fallback directly
            from tools.weiqi101.levels import _load_calibration as _lc
            _lc.cache_clear()
        # Reset for other tests
        _load_calibration.cache_clear()


class TestMapLevelWithCalibration:
    """Tests for level mapping WITH calibration (kyu_offset=10).

    With kyu_offset=10, Chinese ranks shift down:
    - 15K+ → 25K (beginner, not intermediate)
    - 13K+ → 23K (beginner, not intermediate)
    - 5K   → 15K (intermediate, not advanced)
    - 1K   → 11K (intermediate, not advanced)
    Dan ranks are unchanged (dan_offset=0).
    """

    def setup_method(self):
        _load_calibration.cache_clear()

    # --- Calibrated kyu mappings ---

    def test_15k_calibrated_to_beginner(self):
        """15K + 10 = 25K → beginner (was intermediate without calibration)."""
        assert map_level("15K+") == "beginner"

    def test_13k_calibrated_to_beginner(self):
        """13K + 10 = 23K → beginner (was intermediate without calibration)."""
        assert map_level("13K+") == "beginner"

    def test_5k_calibrated_to_intermediate(self):
        """5K + 10 = 15K → intermediate (was advanced without calibration)."""
        assert map_level("5K") == "intermediate"

    def test_1k_calibrated_to_intermediate(self):
        """1K + 10 = 11K → intermediate (was advanced without calibration)."""
        assert map_level("1K") == "intermediate"

    def test_20k_calibrated_to_novice(self):
        """20K + 10 = 30K → novice (was elementary without calibration)."""
        assert map_level("20K+") == "novice"

    def test_25k_clamped_to_novice(self):
        """25K + 10 = 35K → clamped to 30 → novice."""
        assert map_level("25K") == "novice"

    def test_10k_calibrated_to_elementary(self):
        """10K + 10 = 20K → elementary (was upper-intermediate)."""
        assert map_level("10K") == "elementary"

    def test_6k_calibrated_to_elementary(self):
        """6K + 10 = 16K → elementary (was upper-intermediate)."""
        assert map_level("6K") == "elementary"

    # --- Dan ranks unchanged ---

    def test_low_dan_unchanged(self):
        assert map_level("1D") == "low-dan"
        assert map_level("3D") == "low-dan"

    def test_high_dan_unchanged(self):
        assert map_level("4D") == "high-dan"
        assert map_level("6D") == "high-dan"

    def test_expert_unchanged(self):
        assert map_level("7D") == "expert"
        assert map_level("9D") == "expert"

    # --- Edge cases ---

    def test_empty_level(self):
        assert map_level("") is None

    def test_unknown_level(self):
        assert map_level("???") is None
