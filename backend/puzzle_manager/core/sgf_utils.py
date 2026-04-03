"""SGF text processing utilities.

Shared utilities for SGF text manipulation. This module has minimal imports
to avoid circular dependencies.

Usage:
    from backend.puzzle_manager.core.sgf_utils import escape_sgf_value

    # Escape special characters for SGF property values
    escaped = escape_sgf_value("test]value")  # Returns "test\\]value"
"""


def escape_sgf_value(value: str) -> str:
    """Escape special characters in SGF property values.

    SGF requires escaping of backslash and closing bracket characters.
    The order of operations matters: backslash must be escaped first.

    Args:
        value: Raw string value to escape.

    Returns:
        Escaped string safe for SGF property value.

    Example:
        >>> escape_sgf_value("test]value")
        'test\\]value'
        >>> escape_sgf_value("path\\\\file")
        'path\\\\\\\\file'
        >>> escape_sgf_value("both\\]chars")
        'both\\\\\\]chars'
        >>> escape_sgf_value("")
        ''
        >>> escape_sgf_value("no special chars")
        'no special chars'

    Note:
        This function is the single authoritative implementation of SGF
        escaping. All modules must use this function rather than implementing
        their own escaping logic.
    """
    # Escape backslash first (order matters!)
    value = value.replace("\\", "\\\\")
    # Escape closing bracket
    value = value.replace("]", "\\]")
    return value


def unescape_sgf_value(value: str) -> str:
    """Unescape SGF property value — inverse of escape_sgf_value().

    Reverses SGF FF[4] escaping: ``\\]`` → ``]``, ``\\\\`` → ``\\``.
    Order matters: bracket first, then backslash (reverse of escape order).

    Args:
        value: SGF-escaped string from a parsed property value.

    Returns:
        Unescaped raw string.

    Example:
        >>> unescape_sgf_value("test\\]value")
        'test]value'
        >>> unescape_sgf_value("test\\\\value")
        'test\\value'
    """
    # Unescape bracket first, then backslash (reverse of escape order)
    value = value.replace("\\]", "]")
    value = value.replace("\\\\", "\\")
    return value
