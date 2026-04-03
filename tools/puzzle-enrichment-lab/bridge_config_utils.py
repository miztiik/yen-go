"""Config override utility for the bridge API.

Converts flat dotted-path override dicts into nested dicts and applies
them to a base EnrichmentConfig via Pydantic re-construction.

Usage:
    overrides = {"visit_tiers.T1.visits": 1000, "refutations.delta_threshold": 0.05}
    merged = apply_config_overrides(base_config, overrides)
"""

from __future__ import annotations

from typing import Any

from config import EnrichmentConfig


def unflatten_dotted_paths(flat: dict[str, Any]) -> dict[str, Any]:
    """Convert {"a.b.c": 1, "a.d": 2} → {"a": {"b": {"c": 1}, "d": 2}}."""
    result: dict[str, Any] = {}
    for dotted_key, value in flat.items():
        parts = dotted_key.split(".")
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return result


def deep_merge(base: dict, overrides: dict) -> None:
    """Recursively merge *overrides* into *base* (mutates base)."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def apply_config_overrides(
    base: EnrichmentConfig, overrides: dict[str, Any]
) -> EnrichmentConfig:
    """Apply dotted-path overrides to a base config.

    Re-constructs through ``EnrichmentConfig(**merged)`` so Pydantic
    validators (ge/le/type constraints) are triggered for every field.
    Invalid overrides will raise ``ValidationError``.
    """
    if not overrides:
        return base
    nested = unflatten_dotted_paths(overrides)
    base_dict = base.model_dump()
    deep_merge(base_dict, nested)
    return EnrichmentConfig(**base_dict)
