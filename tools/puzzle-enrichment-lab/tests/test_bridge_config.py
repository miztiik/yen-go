"""Tests for bridge_config_utils — config override helpers."""

from __future__ import annotations

import pytest
from bridge_config_utils import apply_config_overrides, deep_merge, unflatten_dotted_paths
from config import EnrichmentConfig, load_enrichment_config
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# unflatten_dotted_paths
# ---------------------------------------------------------------------------


class TestUnflattenDottedPaths:
    def test_simple_path(self):
        assert unflatten_dotted_paths({"a.b": 1}) == {"a": {"b": 1}}

    def test_nested_paths_merge(self):
        result = unflatten_dotted_paths({"a.b": 1, "a.c": 2})
        assert result == {"a": {"b": 1, "c": 2}}

    def test_no_dots_passthrough(self):
        assert unflatten_dotted_paths({"key": "val"}) == {"key": "val"}

    def test_empty_dict(self):
        assert unflatten_dotted_paths({}) == {}


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_basic_merge(self):
        base = {"a": 1, "b": 2}
        deep_merge(base, {"c": 3})
        assert base == {"a": 1, "b": 2, "c": 3}

    def test_deep_nested_merge(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        deep_merge(base, {"a": {"b": {"c": 99}}})
        assert base == {"a": {"b": {"c": 99, "d": 2}}}

    def test_override_scalar(self):
        base = {"a": {"x": 1}}
        deep_merge(base, {"a": {"x": 5}})
        assert base["a"]["x"] == 5


# ---------------------------------------------------------------------------
# apply_config_overrides
# ---------------------------------------------------------------------------


class TestApplyConfigOverrides:
    @pytest.fixture()
    def base_config(self) -> EnrichmentConfig:
        return load_enrichment_config()

    def test_empty_overrides_returns_same(self, base_config: EnrichmentConfig):
        result = apply_config_overrides(base_config, {})
        assert result.model_dump() == base_config.model_dump()

    def test_valid_override_changes_value(self, base_config: EnrichmentConfig):
        original_visits = base_config.visit_tiers.T1.visits
        new_visits = original_visits + 100
        result = apply_config_overrides(
            base_config, {"visit_tiers.T1.visits": new_visits}
        )
        assert result.visit_tiers.T1.visits == new_visits
        # Original unchanged
        assert base_config.visit_tiers.T1.visits == original_visits

    def test_invalid_type_raises_validation_error(self, base_config: EnrichmentConfig):
        with pytest.raises(ValidationError):
            apply_config_overrides(
                base_config, {"visit_tiers.T1.visits": "not_an_int"}
            )

    def test_unknown_paths_ignored(self, base_config: EnrichmentConfig):
        # Pydantic model_dump() round-trip drops unknown keys; no error raised
        result = apply_config_overrides(
            base_config, {"totally_unknown.nested.key": 42}
        )
        # Should succeed — extra keys silently dropped by Pydantic re-construction
        assert isinstance(result, EnrichmentConfig)
