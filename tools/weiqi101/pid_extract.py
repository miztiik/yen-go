"""Single source of truth for extracting a 101weiqi puzzle id (pid) from a filename.

The pid is the integer that uniquely identifies a puzzle on 101weiqi.com,
regardless of which directory the SGF lives in or what slug prefix it carries.

Recognised filename shapes (in priority order):

  1. qday daily-puzzle:        ``YYYYMMDD-N-<pid>.sgf``
  2. book chapter form:        ``ch{NN}_{pos}_{slug}_{pid}.sgf``
  3. book legacy pos form:     ``{pos}_{slug}_{pid}.sgf``
  4. trailing-pid generic:     ``...<sep><pid>.sgf`` where sep is ``_`` or ``-``
  5. bare numeric stem:        ``<pid>.sgf``  (top-level ``sgf/`` pool)

Slugs may contain CJK characters today; cleanup is a separate concern. The
trailing pid token is always pure ASCII digits, so this extractor is robust
to slug churn.

Returns ``None`` for anything that does not match — callers decide whether
to treat that as an error or just skip the file.
"""

from __future__ import annotations

import re

_QDAY_RE = re.compile(r"^\d{8}-\d+-(\d+)\.sgf$")


def pid_from_filename(name: str) -> int | None:
    """Return the trailing puzzle id from an SGF filename, or ``None``."""
    if not name.endswith(".sgf"):
        return None

    m = _QDAY_RE.match(name)
    if m:
        return int(m.group(1))

    stem = name[:-4]

    # Bare numeric stem: ``12345.sgf``.
    if stem.isdigit():
        return int(stem)

    # Trailing token after the last underscore or hyphen.
    for sep in ("_", "-"):
        tail = stem.rsplit(sep, 1)[-1]
        if tail.isdigit():
            return int(tail)

    return None
