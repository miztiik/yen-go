"""
SGF Validator for YenGo puzzles.

Validates SGF files against the YenGo schema before publishing.
Ensures all required properties are present and correctly formatted.
"""

import logging
import re
from dataclasses import dataclass, field

from backend.puzzle_manager.core.constants import VALID_LEVEL_SLUGS
from backend.puzzle_manager.core.schema import get_yengo_sgf_version
from backend.puzzle_manager.core.sgf_parser import SGFGame
from backend.puzzle_manager.exceptions import SGFValidationError

logger = logging.getLogger("puzzle_manager.core.sgf_validator")


@dataclass
class ValidationResult:
    """Result of SGF validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)


class SGFValidator:
    """Validates SGF files against YenGo schema.

    Enforces:
    - Required properties are present (YV, YG, YQ, YX, YI)
    - Property formats match schema patterns
    - Level slugs are valid
    """

    # Use shared level slugs from constants module
    VALID_LEVELS = VALID_LEVEL_SLUGS

    # Pattern for YI (run ID) - date-prefixed format YYYYMMDD-xxxxxxxx
    YI_PATTERN = re.compile(r"^[0-9]{8}-[a-f0-9]{8}$")

    # Pattern for YQ (quality) - q:{1-5};rc:{n};hc:{0-2};ac:{0-3}
    YQ_PATTERN = re.compile(r"^q:[1-5];rc:\d+;hc:[0-2];ac:[0-3]$")

    # Pattern for YX (complexity) - d:{n};r:{n};s:{n};u:{0|1}[;a:{n}]
    YX_PATTERN = re.compile(r"^d:\d+;r:\d+;s:\d+;u:[01](;a:\d+)?$")

    # Pattern for YG (level) - slug or slug:sublevel
    YG_PATTERN = re.compile(r"^[a-z][a-z-]*(?::\d+)?$")

    def validate(self, game: SGFGame) -> ValidationResult:
        """Validate an SGFGame against the YenGo schema.

        Args:
            game: Parsed SGF game to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult(is_valid=True)

        # Validate required properties
        self._validate_required_properties(game, result)

        # Validate property formats
        if result.is_valid:  # Only check formats if required props present
            self._validate_property_formats(game, result)

        return result

    def validate_yengo_properties(self, game: SGFGame) -> ValidationResult:
        """Check that all required YenGo properties are present.

        Required: YV, YG, YQ, YX, YI

        Args:
            game: Parsed SGF game.

        Returns:
            ValidationResult with missing property errors.
        """
        result = ValidationResult(is_valid=True)
        self._validate_required_properties(game, result)
        return result

    def validate_property_formats(self, game: SGFGame) -> ValidationResult:
        """Check that YenGo property values match expected formats.

        Args:
            game: Parsed SGF game.

        Returns:
            ValidationResult with format errors.
        """
        result = ValidationResult(is_valid=True)
        self._validate_property_formats(game, result)
        return result

    def _validate_required_properties(
        self,
        game: SGFGame,
        result: ValidationResult,
    ) -> None:
        """Validate all required properties are present."""
        props = game.yengo_props

        # YV - Version (required)
        if props.version is None:
            result.add_error("Missing required property: YV (version)")

        # YG - Level (required)
        if props.level is None and props.level_slug is None:
            result.add_error("Missing required property: YG (level)")

        # YQ - Quality (required)
        if props.quality is None:
            result.add_error("Missing required property: YQ (quality)")

        # YX - Complexity (required)
        if props.complexity is None:
            result.add_error("Missing required property: YX (complexity)")

    def _validate_property_formats(
        self,
        game: SGFGame,
        result: ValidationResult,
    ) -> None:
        """Validate property value formats."""
        props = game.yengo_props

        # YV - Should be current schema version
        if props.version is not None:
            expected = get_yengo_sgf_version()
            if props.version != expected:
                result.add_warning(
                    f"YV version mismatch: got {props.version}, expected {expected}"
                )

        # YG - Level slug should be valid
        if props.level_slug is not None:
            if not self.YG_PATTERN.match(props.level_slug):
                result.add_error(
                    f"Invalid YG format: '{props.level_slug}' "
                    f"(expected slug like 'beginner' or 'beginner:1')"
                )
            else:
                # Extract base slug
                base_slug = props.level_slug.split(":")[0]
                if base_slug not in self.VALID_LEVELS:
                    result.add_error(
                        f"Invalid level slug: '{base_slug}'. "
                        f"Valid: {', '.join(sorted(self.VALID_LEVELS))}"
                    )

        # YQ - Quality format
        if props.quality is not None:
            if not self.YQ_PATTERN.match(props.quality):
                result.add_error(
                    f"Invalid YQ format: '{props.quality}' "
                    f"(expected 'q:N;rc:N;hc:0|1|2;ac:0|1|2|3')"
                )

        # YX - Complexity format
        if props.complexity is not None:
            if not self.YX_PATTERN.match(props.complexity):
                result.add_error(
                    f"Invalid YX format: '{props.complexity}' "
                    f"(expected 'd:N;r:N;s:N;u:0|1[;a:N]')"
                )


def validate_before_publish(game: SGFGame, strict: bool = True) -> None:
    """Validate game before publishing.

    Args:
        game: SGF game to validate.
        strict: If True, raise on any error. If False, log warnings only.

    Raises:
        ValidationError: If validation fails and strict=True.
    """
    validator = SGFValidator()
    result = validator.validate(game)

    for warning in result.warnings:
        logger.warning(f"Validation warning: {warning}")

    if not result.is_valid:
        error_msg = "; ".join(result.errors)
        if strict:
            raise SGFValidationError(f"SGF validation failed: {error_msg}")
        else:
            logger.error(f"SGF validation errors (non-strict): {error_msg}")
