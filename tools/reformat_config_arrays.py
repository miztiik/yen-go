"""Reformat config JSON files so string-only arrays (alias lists) stay on one line.

Run from the project root:
    python tools/reformat_config_arrays.py

Targets:
  config/tags.json
  config/puzzle-objectives.json

Safe to run repeatedly — idempotent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# JSON files whose string arrays should be kept inline
TARGETS = [
    Path("config/tags.json"),
    Path("config/puzzle-objectives.json"),
]


def reformat_inline_arrays(path: Path) -> None:
    """Collapse string-only JSON arrays onto a single line."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)

    # Re-serialize with standard 2-space indent
    formatted = json.dumps(data, indent=2, ensure_ascii=False)

    # Collapse any array whose items are ALL plain strings onto one line.
    # Matches:  [\n  "a",\n  "b"\n]  =>  ["a", "b"]
    def collapse(m: re.Match) -> str:
        items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(0))
        return "[" + ", ".join('"' + s + '"' for s in items) + "]"

    result = re.sub(
        r"\[\s*\n(?:\s*\"(?:[^\"\\]|\\.)*\"\s*,?\s*\n)+\s*\]",
        collapse,
        formatted,
    )

    path.write_text(result, encoding="utf-8", newline="\n")  # type: ignore[call-arg]
    print(f"  Reformatted: {path}")


def main() -> None:
    root = Path(__file__).parent.parent
    print("Reformatting config alias arrays...")
    for target in TARGETS:
        full = root / target
        if full.exists():
            reformat_inline_arrays(full)
        else:
            print(f"  SKIP (not found): {target}")
    print("Done.")


if __name__ == "__main__":
    main()
