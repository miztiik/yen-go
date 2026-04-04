#!/usr/bin/env python3
"""Merge N[] (node name) properties into C[] (comment) properties in SGF files.

For each node in each SGF file:
1. If node has N[text] AND C[comment]: set C[text. comment], remove N[text]
2. If node has N[text] but NO C[]:       add C[text], remove N[text]
3. If node has no N[]:                   leave unchanged
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Regex for SGF property values (handles escaped brackets: \] inside values)
_PROP_VALUE = r'\[([^\]\\]*(?:\\.[^\]\\]*)*)\]'
N_RE = re.compile(r'N' + _PROP_VALUE)
C_RE = re.compile(r'C' + _PROP_VALUE)


def find_node_spans(content: str) -> list[tuple[int, int]]:
    """Find (start, end) index spans for each node in SGF content.

    A node starts at ';' (outside property values) and extends until the next
    ';', '(', or ')' that is also outside property values.
    """
    spans: list[tuple[int, int]] = []
    in_bracket = False
    node_start: int | None = None

    i = 0
    while i < len(content):
        ch = content[i]

        if in_bracket:
            if ch == '\\' and i + 1 < len(content):
                i += 2  # skip escaped character
                continue
            if ch == ']':
                in_bracket = False
        else:
            if ch == '[':
                in_bracket = True
            elif ch == ';':
                if node_start is not None:
                    spans.append((node_start, i))
                node_start = i
            elif ch in '()':
                if node_start is not None:
                    spans.append((node_start, i))
                    node_start = None

        i += 1

    # Handle last node if file doesn't end with ) or ;
    if node_start is not None:
        spans.append((node_start, len(content)))

    return spans


def process_node(node_text: str) -> str:
    """Process a single node: merge N[] into C[] if N[] exists."""
    n_match = N_RE.search(node_text)
    if not n_match:
        return node_text  # No N[], nothing to do

    n_value = n_match.group(1)
    c_match = C_RE.search(node_text)

    if c_match:
        # Case 1: Both N[] and C[] exist — merge N value into C
        c_value = c_match.group(1)
        new_c_value = f"{n_value}. {c_value}"

        # Remove N[] first (work from right to left to preserve positions)
        if n_match.start() > c_match.start():
            # N is after C: remove N first, then replace C
            node_text = node_text[:n_match.start()] + node_text[n_match.end():]
            c_match = C_RE.search(node_text)  # re-find C (position unchanged)
            node_text = node_text[:c_match.start()] + f"C[{new_c_value}]" + node_text[c_match.end():]
        else:
            # N is before C: replace C first, then remove N
            node_text = node_text[:c_match.start()] + f"C[{new_c_value}]" + node_text[c_match.end():]
            n_match = N_RE.search(node_text)  # re-find N (position unchanged)
            node_text = node_text[:n_match.start()] + node_text[n_match.end():]
    else:
        # Case 2: N[] exists but no C[] — convert N to C
        node_text = node_text[:n_match.start()] + f"C[{n_value}]" + node_text[n_match.end():]

    return node_text


def process_sgf(content: str) -> str:
    """Process entire SGF content, merging N[] into C[] for all nodes."""
    spans = find_node_spans(content)

    if not spans:
        return content

    # Process nodes from right to left so string positions stay valid
    result = content
    for start, end in reversed(spans):
        node_text = result[start:end]
        processed = process_node(node_text)
        if processed != node_text:
            result = result[:start] + processed + result[end:]

    return result


@dataclass
class MergeStats:
    """Result of a merge-node-names run."""

    total: int = 0
    modified: int = 0
    errors: int = 0
    error_files: list[str] = field(default_factory=list)


def merge_node_names(source_dir: Path, *, dry_run: bool = False) -> MergeStats:
    """Merge N[] into C[] for all SGFs under *source_dir*.

    Walks the directory tree recursively.  Returns stats.
    """
    stats = MergeStats()

    for root, _dirs, files in os.walk(source_dir):
        for filename in sorted(files):
            if not filename.endswith(".sgf"):
                continue
            stats.total += 1
            filepath = Path(root) / filename

            try:
                content = filepath.read_text(encoding="utf-8")
                processed = process_sgf(content)

                if processed != content:
                    stats.modified += 1
                    if not dry_run:
                        filepath.write_text(processed, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                stats.errors += 1
                stats.error_files.append(f"{filepath}: {exc}")

    return stats
