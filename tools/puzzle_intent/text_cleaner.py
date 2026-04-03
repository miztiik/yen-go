"""Text cleaning utilities - re-exported from tools.core.text_cleaner.

This module is kept for backward compatibility. All functionality has been
moved to tools.core.text_cleaner. Import directly from there for new code.
"""

from tools.core.text_cleaner import (
    clean_comment_text,
    normalize_text,
    strip_boilerplate,
    strip_cjk,
    strip_html,
    strip_urls,
)

__all__ = [
    "clean_comment_text",
    "normalize_text",
    "strip_boilerplate",
    "strip_cjk",
    "strip_html",
    "strip_urls",
]
