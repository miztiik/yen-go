"""
Test fixtures for run_id format testing.

Provides constants for the YYYYMMDD-xxxxxxxx run_id format
to ensure consistent test coverage across the codebase.

Usage:
    from backend.puzzle_manager.tests.fixtures.run_id import (
        RUN_ID,
        VALID_RUN_IDS,
        INVALID_RUN_IDS,
    )
"""

# Standard format: YYYYMMDD-xxxxxxxx (date prefix + 8 hex chars)
# Used in schema v6 and later (spec-041)
RUN_ID = "20260129-abc12345"

# Valid examples for testing
VALID_RUN_IDS = [
    "20260129-abc12345",
    "20241231-00000000",
    "20300101-ffffffff",
    "20260101-deadbeef",
]

# Invalid formats that should fail validation
INVALID_RUN_IDS = [
    "",                     # Empty
    "a1b2c3d4e5f6",         # Old 12-char format (no longer valid)
    "20260129abc12345",     # Missing hyphen
    "2026012-abc12345",     # Date too short
    "202601299-abc12345",   # Date too long
    "20260129-abc1234",     # Hex part too short
    "20260129-abc123456",   # Hex part too long
    "20260129-ABC12345",    # Uppercase hex (invalid)
    "2026-01-29-abc12345",  # Wrong date format
    "abcd1234-12345678",    # Non-date prefix
]

# Pattern for validation (new format only)
RUN_ID_PATTERN = r"^[0-9]{8}-[a-f0-9]{8}$"
