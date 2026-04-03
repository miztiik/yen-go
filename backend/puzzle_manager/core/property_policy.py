"""
Property Policy Registry for SGF property handling.

Provides a declarative, config-driven system for controlling how each SGF
property is handled as it flows through the pipeline (ingest → analyze → publish).

Policies:
    BLOCKED          — Dropped at parse time. Never enters the pipeline.
    PRESERVE         — Source value passed through unchanged.
    HARDCODE         — Always set to a fixed value regardless of source.
    OVERRIDE         — Always overwritten by pipeline computation.
    ENRICH_IF_ABSENT — Computed only when source provides no value.
    ENRICH_IF_PARTIAL— Source preserved if valid; recomputed if malformed/partial.
    REMOVE           — Explicitly deleted during processing.
    CONFIGURABLE     — Behavior controlled by a runtime flag.

Usage:
    from backend.puzzle_manager.core.property_policy import get_policy_registry

    registry = get_policy_registry()
    policy = registry.get_policy("YT")  # PropertyPolicy.ENRICH_IF_ABSENT
    if registry.is_enrichment_needed("YT", existing_tags):
        tags = detect_techniques(game)
"""

import json
import logging
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Final

logger = logging.getLogger("property_policy")


class PropertyPolicy(Enum):
    """SGF property handling policy."""

    BLOCKED = "blocked"
    PRESERVE = "preserve"
    HARDCODE = "hardcode"
    OVERRIDE = "override"
    ENRICH_IF_ABSENT = "enrich_if_absent"
    ENRICH_IF_PARTIAL = "enrich_if_partial"
    REMOVE = "remove"
    CONFIGURABLE = "configurable"


# --- Validators for ENRICH_IF_PARTIAL ---

# YQ pattern: q:{1-5};rc:{0+};hc:{0-2};ac:{0-3}
_YQ_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^q:[1-5];rc:\d+;hc:[0-2];ac:[0-3]$"
)

# YX pattern: d:{0+};r:{1+};s:{1+};u:{0|1}[;w:{0+}][;a:{0+}]
_YX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^d:\d+;r:\d+;s:\d+;u:[01](;w:\d+)?(;a:\d+)?$"
)


def validate_quality_metrics(value: str | None) -> bool:
    """Check if YQ value is a complete, valid quality metrics string.

    Args:
        value: YQ property value (e.g., "q:3;rc:2;hc:1").

    Returns:
        True if the value is complete and valid; False if absent, empty, or malformed.
    """
    if not value:
        return False
    return bool(_YQ_PATTERN.match(value))


def validate_complexity_metrics(value: str | None) -> bool:
    """Check if YX value is a complete, valid complexity metrics string.

    Args:
        value: YX property value (e.g., "d:5;r:13;s:24;u:1").

    Returns:
        True if the value is complete and valid; False if absent, empty, or malformed.
    """
    if not value:
        return False
    return bool(_YX_PATTERN.match(value))


# Validator registry: maps validator names (from config JSON) to functions
_VALIDATORS: dict[str, object] = {
    "quality_metrics": validate_quality_metrics,
    "complexity_metrics": validate_complexity_metrics,
}


def _get_validator(name: str):
    """Get a validator function by name.

    Args:
        name: Validator name as declared in sgf-property-policies.json.

    Returns:
        Validator function (str | None) -> bool.

    Raises:
        ValueError: If validator name is not registered.
    """
    if name not in _VALIDATORS:
        raise ValueError(
            f"Unknown validator '{name}'. "
            f"Available: {sorted(_VALIDATORS.keys())}"
        )
    return _VALIDATORS[name]


class PropertyPolicyRegistry:
    """Registry of SGF property handling policies.

    Loaded from config/sgf-property-policies.json. Provides lookup methods
    for determining how each property should be handled during pipeline stages.
    """

    def __init__(self, config: dict) -> None:
        """Initialize from parsed config dict.

        Args:
            config: Parsed JSON from sgf-property-policies.json.
        """
        self._config = config
        self._policies: dict[str, PropertyPolicy] = {}
        self._hardcode_values: dict[str, str] = {}
        self._enrich_defaults: dict[str, str] = {}  # prop -> default value
        self._validators: dict[str, str] = {}  # prop -> validator name
        self._configurable_flags: dict[str, str] = {}  # prop -> flag name
        self._configurable_defaults: dict[str, bool] = {}  # prop -> default

        policies = config.get("policies", {})
        for prop_key, entry in policies.items():
            policy_str = entry.get("policy", "")
            try:
                policy = PropertyPolicy(policy_str)
            except ValueError:
                logger.warning(
                    f"Unknown policy '{policy_str}' for property '{prop_key}', "
                    f"defaulting to PRESERVE"
                )
                policy = PropertyPolicy.PRESERVE

            self._policies[prop_key] = policy

            if policy == PropertyPolicy.HARDCODE:
                self._hardcode_values[prop_key] = entry.get("value", "")

            if policy in (PropertyPolicy.ENRICH_IF_ABSENT, PropertyPolicy.ENRICH_IF_PARTIAL):
                default_val = entry.get("default_value")
                if default_val is not None:
                    self._enrich_defaults[prop_key] = str(default_val)

            if policy == PropertyPolicy.ENRICH_IF_PARTIAL:
                validator_name = entry.get("validator", "")
                if validator_name:
                    # Validate that the named validator exists
                    _get_validator(validator_name)
                    self._validators[prop_key] = validator_name

            if policy == PropertyPolicy.CONFIGURABLE:
                self._configurable_flags[prop_key] = entry.get("flag", "")
                self._configurable_defaults[prop_key] = entry.get("default", True)

    def get_policy(self, prop_key: str) -> PropertyPolicy | None:
        """Get the policy for a property.

        Args:
            prop_key: SGF property key (e.g., "YT", "SZ", "DT").

        Returns:
            PropertyPolicy enum value, or None if property is not in the registry.
        """
        return self._policies.get(prop_key)

    def get_hardcode_value(self, prop_key: str) -> str | None:
        """Get the hardcoded value for a HARDCODE policy property.

        Args:
            prop_key: SGF property key.

        Returns:
            The fixed value string, or None if not a HARDCODE property.
        """
        return self._hardcode_values.get(prop_key)

    def get_enrich_default(self, prop_key: str) -> str | None:
        """Get the default value for an enrichable property.

        Used when ENRICH_IF_ABSENT and no source value exists, to provide
        a known default (e.g., SZ defaults to 19).

        Args:
            prop_key: SGF property key.

        Returns:
            Default value string, or None if no default configured.
        """
        return self._enrich_defaults.get(prop_key)

    def get_configurable_flag(self, prop_key: str) -> str | None:
        """Get the runtime flag name for a CONFIGURABLE policy property.

        Args:
            prop_key: SGF property key.

        Returns:
            Flag name string, or None if not a CONFIGURABLE property.
        """
        return self._configurable_flags.get(prop_key)

    def get_configurable_default(self, prop_key: str) -> bool:
        """Get the default value for a CONFIGURABLE policy property.

        Args:
            prop_key: SGF property key.

        Returns:
            Default boolean value (True if not found).
        """
        return self._configurable_defaults.get(prop_key, True)

    def blocked_properties(self) -> frozenset[str]:
        """Get the set of blocked property keys.

        Returns:
            Frozen set of property keys with BLOCKED policy.
        """
        return frozenset(
            k for k, v in self._policies.items()
            if v == PropertyPolicy.BLOCKED
        )

    def preserved_properties(self) -> frozenset[str]:
        """Get the set of preserved property keys.

        Returns:
            Frozen set of property keys with PRESERVE policy.
        """
        return frozenset(
            k for k, v in self._policies.items()
            if v == PropertyPolicy.PRESERVE
        )

    def enrichable_properties(self) -> frozenset[str]:
        """Get properties that may be enriched (ENRICH_IF_ABSENT or ENRICH_IF_PARTIAL).

        Returns:
            Frozen set of enrichable property keys.
        """
        return frozenset(
            k for k, v in self._policies.items()
            if v in (PropertyPolicy.ENRICH_IF_ABSENT, PropertyPolicy.ENRICH_IF_PARTIAL)
        )

    def is_enrichment_needed(self, prop_key: str, existing_value: object) -> bool:
        """Determine if enrichment computation is needed for a property.

        Logic by policy type:
        - ENRICH_IF_ABSENT: True if existing_value is None/empty/falsy.
        - ENRICH_IF_PARTIAL: True if validator says value is incomplete/invalid.
        - OVERRIDE: Always True (pipeline always overwrites).
        - PRESERVE/BLOCKED/REMOVE/HARDCODE/CONFIGURABLE: Always False.

        For list-typed properties (tags, collections, hints), pass the list
        directly — an empty list is treated as absent.

        Args:
            prop_key: SGF property key.
            existing_value: Current value from source SGF (str, list, int, or None).

        Returns:
            True if the pipeline should compute/enrich this property.
        """
        policy = self._policies.get(prop_key)
        if policy is None:
            return False

        if policy == PropertyPolicy.OVERRIDE:
            return True

        if policy == PropertyPolicy.ENRICH_IF_ABSENT:
            # For lists: empty list = absent
            if isinstance(existing_value, list):
                return len(existing_value) == 0
            # For strings/ints: None or empty string = absent
            return not existing_value

        if policy == PropertyPolicy.ENRICH_IF_PARTIAL:
            validator_name = self._validators.get(prop_key)
            if not validator_name:
                # No validator configured — treat as enrich_if_absent
                return not existing_value
            validator_fn = _get_validator(validator_name)
            # If value is absent → needs enrichment
            if not existing_value:
                return True
            # If value is present but invalid/partial → needs enrichment
            return not validator_fn(existing_value)

        # PRESERVE, BLOCKED, REMOVE, HARDCODE, CONFIGURABLE → no enrichment
        return False

    def is_property_allowed(self, prop_key: str) -> bool:
        """Check if a property is allowed to pass through the pipeline.

        Returns False for BLOCKED properties (should be dropped at parse).
        Returns True for all other policies (including unknown properties
        not in the registry — they pass through by default for safety).

        Args:
            prop_key: SGF property key.

        Returns:
            True if property is allowed; False if blocked.
        """
        policy = self._policies.get(prop_key)
        if policy is None:
            # Unknown property — not in registry. Default: allow (preserve).
            return True
        return policy != PropertyPolicy.BLOCKED


def _get_config_path() -> Path:
    """Get path to the property policies config file."""
    from backend.puzzle_manager.paths import get_global_config_dir
    return get_global_config_dir() / "sgf-property-policies.json"


@lru_cache(maxsize=1)
def _load_policy_config() -> dict:
    """Load property policies from config JSON.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    config_path = _get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Property policy config not found: {config_path}"
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_policy_registry() -> PropertyPolicyRegistry:
    """Get the singleton PropertyPolicyRegistry.

    Loads from config/sgf-property-policies.json on first call, cached thereafter.

    Returns:
        PropertyPolicyRegistry instance.
    """
    config = _load_policy_config()
    return PropertyPolicyRegistry(config)
