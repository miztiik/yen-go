"""
Unit tests for SGFValidator.

Tests validation of required properties and format patterns.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.puzzle_manager.core.sgf_validator import (
    SGFValidator,
    ValidationResult,
    validate_before_publish,
)
from backend.puzzle_manager.exceptions import SGFValidationError


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_starts_valid(self):
        """New result should be valid."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_makes_invalid(self):
        """Adding error should set is_valid to False."""
        result = ValidationResult(is_valid=True)
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_add_warning_keeps_valid(self):
        """Adding warning should not affect validity."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Test warning")

        assert result.is_valid is True
        assert "Test warning" in result.warnings


class TestSGFValidator:
    """Tests for SGFValidator class."""

    def _make_game(
        self,
        version: int | None = 5,
        level: int | None = 2,
        level_slug: str | None = "beginner",
        run_id: str | None = "20260129-abc12345",
        quality: str | None = "q:3;rc:2;hc:1;ac:0",
        complexity: str | None = "d:5;r:13;s:24;u:1",
    ):
        """Create a mock SGFGame with specified properties."""
        game = MagicMock()
        props = MagicMock()
        props.version = version
        props.level = level
        props.level_slug = level_slug
        props.run_id = run_id
        props.quality = quality
        props.complexity = complexity
        game.yengo_props = props
        return game

    # --- Required Properties Tests ---

    def test_valid_game_passes(self):
        """Game with all required properties should pass."""
        game = self._make_game()
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True
        assert result.errors == []

    def test_missing_version_fails(self):
        """Missing YV should fail."""
        game = self._make_game(version=None)
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YV" in e for e in result.errors)

    def test_missing_level_fails(self):
        """Missing YG should fail."""
        game = self._make_game(level=None, level_slug=None)
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YG" in e for e in result.errors)

    def test_missing_quality_fails(self):
        """Missing YQ should fail."""
        game = self._make_game(quality=None)
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YQ" in e for e in result.errors)

    def test_missing_complexity_fails(self):
        """Missing YX should fail."""
        game = self._make_game(complexity=None)
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YX" in e for e in result.errors)

    # --- Format Validation Tests ---

    def test_valid_run_id_format(self):
        """Valid YYYYMMDD-xxxxxxxx run_id should pass."""
        game = self._make_game(run_id="20260129-abcdef12")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True

    # --- Run ID Format Tests (spec-041) ---

    def test_valid_new_run_id_format(self):
        """Date-prefixed run_id (YYYYMMDD-xxxxxxxx) should pass."""
        game = self._make_game(run_id="20260129-abc12345")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True

    def test_valid_quality_format(self):
        """Valid YQ format should pass."""
        game = self._make_game(quality="q:1;rc:0;hc:0;ac:0")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True

    def test_invalid_quality_tier(self):
        """YQ tier > 5 should fail."""
        game = self._make_game(quality="q:6;rc:0;hc:0;ac:0")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YQ format" in e for e in result.errors)

    def test_valid_complexity_format(self):
        """Valid YX format should pass."""
        game = self._make_game(complexity="d:0;r:1;s:5;u:0")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True

    def test_invalid_complexity_format(self):
        """Malformed YX should fail."""
        game = self._make_game(complexity="depth:5;reading:10")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("YX format" in e for e in result.errors)

    # --- Level Slug Tests ---

    def test_valid_level_slugs(self):
        """All valid level slugs should pass."""
        validator = SGFValidator()

        valid_slugs = [
            "novice", "beginner", "elementary",
            "intermediate", "upper-intermediate", "advanced",
            "low-dan", "high-dan", "expert",
        ]

        for slug in valid_slugs:
            game = self._make_game(level_slug=slug)
            result = validator.validate(game)
            assert result.is_valid is True, f"Slug '{slug}' should be valid"

    def test_level_slug_with_sublevel(self):
        """Level slug with sublevel should pass."""
        game = self._make_game(level_slug="beginner:1")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is True

    def test_invalid_level_slug(self):
        """Invalid level slug should fail."""
        game = self._make_game(level_slug="pro-dan")
        validator = SGFValidator()
        result = validator.validate(game)

        assert result.is_valid is False
        assert any("Invalid level slug" in e for e in result.errors)

    # --- Version Warning Test ---

    @patch('backend.puzzle_manager.core.sgf_validator.get_yengo_sgf_version')
    def test_version_mismatch_warning(self, mock_version):
        """Version mismatch should produce warning, not error."""
        mock_version.return_value = 5

        game = self._make_game(version=4)  # Old version
        validator = SGFValidator()
        result = validator.validate(game)

        # Should pass but with warning
        assert result.is_valid is True
        assert any("version mismatch" in w for w in result.warnings)


class TestValidateBeforePublish:
    """Tests for validate_before_publish function."""

    def _make_game(self, valid: bool = True):
        """Create a mock game."""
        game = MagicMock()
        props = MagicMock()
        if valid:
            props.version = 5
            props.level = 2
            props.level_slug = "beginner"
            props.run_id = "20260129-abc12345"
            props.quality = "q:3;rc:2;hc:1;ac:0"
            props.complexity = "d:5;r:13;s:24;u:1"
        else:
            props.version = None
            props.level = None
            props.level_slug = None
            props.run_id = None
            props.quality = None
            props.complexity = None
        game.yengo_props = props
        return game

    def test_valid_game_passes_strict(self):
        """Valid game should pass in strict mode."""
        game = self._make_game(valid=True)
        # Should not raise
        validate_before_publish(game, strict=True)

    def test_invalid_game_raises_strict(self):
        """Invalid game should raise SGFValidationError in strict mode."""
        game = self._make_game(valid=False)

        with pytest.raises(SGFValidationError):
            validate_before_publish(game, strict=True)

    def test_invalid_game_logs_nonstrict(self):
        """Invalid game should log but not raise in non-strict mode."""
        game = self._make_game(valid=False)

        # Should not raise
        validate_before_publish(game, strict=False)


class TestValidateYengoProperties:
    """Tests for validate_yengo_properties method."""

    def test_returns_validation_result(self):
        """Should return ValidationResult object."""
        game = MagicMock()
        props = MagicMock()
        props.version = 5
        props.level = 2
        props.level_slug = "beginner"
        props.run_id = "a1b2c3d4e5f6"
        props.quality = "q:3;rc:2;hc:1"
        props.complexity = "d:5;r:13;s:24;u:1"
        game.yengo_props = props

        validator = SGFValidator()
        result = validator.validate_yengo_properties(game)

        assert isinstance(result, ValidationResult)


class TestValidatePropertyFormats:
    """Tests for validate_property_formats method."""

    def test_returns_validation_result(self):
        """Should return ValidationResult object."""
        game = MagicMock()
        props = MagicMock()
        props.version = 5
        props.level_slug = "beginner"
        props.run_id = "a1b2c3d4e5f6"
        props.quality = "q:3;rc:2;hc:1"
        props.complexity = "d:5;r:13;s:24;u:1"
        game.yengo_props = props

        validator = SGFValidator()
        result = validator.validate_property_formats(game)

        assert isinstance(result, ValidationResult)
