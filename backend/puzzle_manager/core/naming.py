"""Centralized SGF filename generation utility.

This module provides the single source of truth for SGF filename generation,
ensuring all adapters use consistent 16-character content-based hashing.

Spec Reference: 028-adapter-standards
Schema Reference: config/schemas/sgf-naming.schema.json
"""

from __future__ import annotations

import hashlib
import re

# Constants - Single source of truth
HASH_LENGTH: int = 16  # Characters from SHA-256 hex digest
SGF_EXTENSION: str = ".sgf"

# Pattern for valid SGF filename
SGF_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{16}\.sgf$")


def generate_sgf_filename(sgf_content: str) -> str:
    """Generate content-based SGF filename.

    Uses SHA-256 hash of SGF content, truncated to 16 hex characters.
    This provides virtually zero collision probability at scale.

    Args:
        sgf_content: Valid SGF content string

    Returns:
        Filename in format: {16-char-hex-hash}.sgf

    Raises:
        ValueError: If sgf_content is empty or whitespace-only

    Example:
        >>> generate_sgf_filename("(;GM[1]FF[4])")
        'a3f2c1b0d4e5f6a7.sgf'
    """
    if not sgf_content or not sgf_content.strip():
        raise ValueError("SGF content cannot be empty")

    content_hash = generate_content_hash(sgf_content)
    return f"{content_hash}{SGF_EXTENSION}"


def generate_content_hash(sgf_content: str) -> str:
    """Generate content hash without extension.

    Useful when only the hash is needed (e.g., for deduplication checks).

    Args:
        sgf_content: Valid SGF content string

    Returns:
        16-character lowercase hex hash

    Raises:
        ValueError: If sgf_content is empty or whitespace-only
    """
    if not sgf_content or not sgf_content.strip():
        raise ValueError("SGF content cannot be empty")

    return hashlib.sha256(
        sgf_content.encode("utf-8")
    ).hexdigest()[:HASH_LENGTH]


def is_valid_sgf_filename(filename: str) -> bool:
    r"""Check if filename conforms to naming standard.

    Args:
        filename: Filename to validate (not a full path)

    Returns:
        True if filename matches pattern ^[a-f0-9]{16}\.sgf$
        False otherwise

    Example:
        >>> is_valid_sgf_filename("a3f2c1b0d4e5f6a7.sgf")
        True
        >>> is_valid_sgf_filename("puzzle-001.sgf")
        False
    """
    return bool(SGF_FILENAME_PATTERN.match(filename))
