"""
HTML → qqdata JSON extraction for 101weiqi pages.

Extracts the `var qqdata = {...}` JavaScript object from raw HTML
using regex + brace matching. Handles string escaping and invalid
Unicode surrogate pairs.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger("101weiqi.extractor")
# Markers that indicate the site returned a CAPTCHA / rate-limit page
# instead of actual puzzle content.
_RATE_LIMIT_MARKERS = ("TCaptcha.js", "turing.captcha.qcloud.com")

# Markers that indicate the page redirected to a login wall.
# These appear in the page URL or HTML when the site requires authentication
# to view a puzzle (e.g., locked content, session expired).
_LOGIN_MARKERS = (
    "/accounts/signin",
    "/accounts/login",
    "/login/",
    "denglu",            # Chinese for "login" in URL paths
    'id="login-form"',
    'class="login-page"',
)


def is_rate_limited_page(html: str) -> bool:
    """Detect if the returned HTML is a CAPTCHA / rate-limit page.

    When 101weiqi rate-limits a session, it returns a smaller (~26 KB)
    generic page that loads Tencent CAPTCHA JS instead of puzzle data.
    """
    if "var qqdata" in html:
        return False  # Normal puzzle page (even if data is partial)
    return any(marker in html for marker in _RATE_LIMIT_MARKERS)


def is_login_page(html: str) -> bool:
    """Detect if the returned HTML is a login/authentication page.

    When the site requires login to view a puzzle, it redirects to
    a login page instead of rendering puzzle data.
    """
    if "var qqdata" in html:
        return False  # Has puzzle data — not a login redirect
    return any(marker in html for marker in _LOGIN_MARKERS)

def extract_qqdata(html: str) -> dict | None:
    """Extract the qqdata JSON object from an HTML page.

    Finds `var qqdata = {...}` in the page source, extracts the JSON
    object by matching braces (respecting string literals), and parses it.

    Args:
        html: Raw HTML page content.

    Returns:
        Parsed dict on success, None on failure.
    """
    match = re.search(r"var\s+qqdata\s*=\s*", html)
    if not match:
        logger.error("Could not find 'var qqdata' in page")
        return None

    start_pos = match.end()

    if start_pos >= len(html) or html[start_pos] != "{":
        logger.error("Expected '{' after 'var qqdata ='")
        return None

    # Find the matching closing brace, respecting string literals
    brace_count = 0
    in_string = False
    escape_next = False
    end_pos = start_pos

    for i in range(start_pos, len(html)):
        char = html[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break

    if brace_count != 0:
        logger.error("Unbalanced braces in qqdata")
        return None

    json_str = html[start_pos:end_pos]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error, attempting sanitization: {e}")
        try:
            # Sanitize invalid Unicode surrogate pairs
            sanitized = re.sub(
                r"\\u[dD][89abAB][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2}",
                "?",
                json_str,
            )
            return json.loads(sanitized)
        except json.JSONDecodeError:
            logger.error("Failed to parse qqdata JSON even after sanitization")
            return None
