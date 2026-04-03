"""Lightweight property policy reader for the enrichment lab.

Reads ``config/sgf-property-policies.json`` and implements the subset of
enrichment policies relevant to the KataGo enricher:

- ``enrich_if_absent``  → enrich only when no value exists
- ``enrich_if_partial`` → enrich when value is absent or fails validation
- ``override``          → always enrich (overwrite)

This module exists because ``tools/`` must NOT import from ``backend/``.
The single source of truth remains the shared JSON config — this is a
thin, read-only mirror of ``backend.puzzle_manager.core.property_policy``.

See also: ADR-007 (007-adr-policy-aligned-enrichment.md)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "sgf-property-policies.json"

_policy_cache: dict[str, Any] | None = None


def _load_policies() -> dict[str, Any]:
    """Load and cache property policies from config JSON."""
    global _policy_cache
    if _policy_cache is not None:
        return _policy_cache

    if not _CONFIG_PATH.exists():
        logger.warning("Property policies config not found: %s", _CONFIG_PATH)
        _policy_cache = {}
        return _policy_cache

    with open(_CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    _policy_cache = data.get("policies", {})
    return _policy_cache


def clear_policy_cache() -> None:
    """Clear the cached policies (for testing)."""
    global _policy_cache
    _policy_cache = None


# ---------------------------------------------------------------------------
# Validators — string-based parsing (Plan 010, P5.9: no regex)
# ---------------------------------------------------------------------------


def _validate_quality_metrics(value: str) -> bool:
    """Validate quality_metrics format: q:<1-5>;rc:<digits>;hc:<0-2>."""
    parts = value.split(";")
    if len(parts) != 3:
        return False
    try:
        # q:<1-5>
        k1, v1 = parts[0].split(":", 1)
        if k1 != "q" or not v1.isdigit() or not (1 <= int(v1) <= 5):
            return False
        # rc:<digits>
        k2, v2 = parts[1].split(":", 1)
        if k2 != "rc" or not v2.isdigit():
            return False
        # hc:<0-2>
        k3, v3 = parts[2].split(":", 1)
        if k3 != "hc" or not v3.isdigit() or not (0 <= int(v3) <= 2):
            return False
        return True
    except (ValueError, IndexError):
        return False


def _validate_complexity_metrics(value: str) -> bool:
    """Validate complexity_metrics format: d:<d>;r:<d>;s:<d>;u:<0|1>[;w:<d>][;a:<d>]."""
    parts = value.split(";")
    if len(parts) < 4 or len(parts) > 6:
        return False
    try:
        # Required: d, r, s, u (in order)
        required_keys = ["d", "r", "s", "u"]
        for i, expected_key in enumerate(required_keys):
            k, v = parts[i].split(":", 1)
            if k != expected_key or not v.isdigit():
                return False
            if expected_key == "u" and int(v) not in (0, 1):
                return False
        # Optional: w and a (independent, either can appear without the other)
        allowed_optional = {"w", "a"}
        seen_optional: set[str] = set()
        for j in range(4, len(parts)):
            k, v = parts[j].split(":", 1)
            if k not in allowed_optional or k in seen_optional or not v.isdigit():
                return False
            seen_optional.add(k)
        return True
    except (ValueError, IndexError):
        return False


_VALIDATORS: dict[str, object] = {
    "quality_metrics": _validate_quality_metrics,
    "complexity_metrics": _validate_complexity_metrics,
}


def _validate_value(validator_name: str, value: str) -> bool:
    """Return True if value passes the named validator."""
    validator = _VALIDATORS.get(validator_name)
    if validator is None:
        logger.warning("Unknown validator: %s -- treating as invalid", validator_name)
        return False
    return bool(validator(value))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_policy(prop: str) -> str:
    """Return the policy string for a property, or 'preserve' if unknown."""
    policies = _load_policies()
    entry = policies.get(prop, {})
    if isinstance(entry, dict):
        return entry.get("policy", "preserve")
    return "preserve"


def is_enrichment_needed(prop: str, existing_value: str | None) -> bool:
    """Determine whether the enricher should write a value for ``prop``.

    Logic mirrors ``PropertyPolicyRegistry.is_enrichment_needed()`` from
    the pipeline (``backend.puzzle_manager.core.property_policy``).

    Args:
        prop: SGF property key (e.g. "YG", "YX", "YR").
        existing_value: Current value in the SGF, or None/empty if absent.

    Returns:
        True if the enricher should compute and write this property.
    """
    policies = _load_policies()
    entry = policies.get(prop, {})

    if not isinstance(entry, dict):
        return False

    policy = entry.get("policy", "preserve")

    if policy == "override":
        return True

    if policy == "enrich_if_absent":
        # Enrich only when value is absent/empty
        return not existing_value or not existing_value.strip()

    if policy == "enrich_if_partial":
        # Absent → enrich
        if not existing_value or not existing_value.strip():
            return True
        # Present but invalid → enrich
        validator_name = entry.get("validator")
        if validator_name:
            return not _validate_value(validator_name, existing_value.strip())
        # No validator defined → treat present value as valid
        return False

    # preserve, blocked, remove, hardcode, configurable → do not enrich
    return False
