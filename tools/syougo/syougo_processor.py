#!/usr/bin/env python3
"""
Syougo Processor — Repackage downloaded syougo.jp puzzles into pipeline-ready SGFs.

Reads SGF+JSON pairs from tools/syougo/downloads/, applies whitelist rebuild,
enriches with YG/YT/YL/C[], and writes to external-sources/syougo/.

Usage:
    python -m tools.syougo.syougo_processor              # Process all
    python -m tools.syougo.syougo_processor --dry-run     # Preview only
    python -m tools.syougo.syougo_processor --levels 1,2  # Specific levels
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from tools.core.paths import get_project_root, rel_path
from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_types import Color
from tools.core.validation import validate_sgf_puzzle

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

TOOL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = get_project_root()

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

TAG_MAP = _load_json(TOOL_DIR / "_local_tag_mapping.json")["mappings"]
COLL_MAP = _load_json(TOOL_DIR / "_local_collections_mapping.json")["mappings"]
SOURCES = _load_json(TOOL_DIR / "sources.json")
LEVEL_MAP: dict[str, str] = SOURCES["level_mapping"]

# ---------------------------------------------------------------------------
# Intent mapping: prompt pattern → objective action
# Side is derived from PL[] at runtime.
# ---------------------------------------------------------------------------

# Ordered longest-first so more specific patterns match before generic ones.
INTENT_PATTERNS: list[tuple[str, str]] = [
    ("endgame",    "endgame"),
    ("capture",    "kill"),
    ("save",       "live"),
    ("live",       "live"),
    ("defense",    "live"),
    ("ko",         "win-ko"),
    ("cut off",    "cut"),
    ("connection", "connect"),
    ("tesuji",     "tesuji"),
    ("snapback",   "tesuji"),
]


def _derive_side(player: Color) -> str:
    return "black" if player == Color.BLACK else "white"


def derive_intent(prompt: str, player: Color) -> str | None:
    """Derive root C[] objective slug from prompt + player to move."""
    text = prompt.lower()
    side = _derive_side(player)
    for pattern, action in INTENT_PATTERNS:
        if pattern in text:
            return f"{side}-to-{action}" if action != "endgame" else f"{side}-{action}"
    return None


def derive_tags(prompt: str) -> list[str]:
    """Derive tags from prompt using _local_tag_mapping.json. No defaults."""
    text = prompt.lower()
    tags: set[str] = set()
    for pattern, tag_list in TAG_MAP.items():
        # "make * live" → regex "make.*live"
        regex = pattern.replace(" * ", ".*")
        if re.search(regex, text):
            tags.update(tag_list)
    return sorted(tags)


def derive_collection(level_dir: str) -> str | None:
    """Map level directory name to YenGo collection slug."""
    return COLL_MAP.get(level_dir)


def _fix_comment_spacing(text: str) -> str:
    """Fix stuck token patterns in translated comments.

    Fixes: 'is6 point' → 'is 6 point', '1shortage' → '1 shortage',
           'isflower' → 'is flower' (lowercase-lowercase word boundary).
    """
    if not text:
        return text
    # Insert space between letter and digit
    result = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    result = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', result)
    # Insert space at lowercase→lowercase word boundary where two known
    # English words got concatenated (e.g. "isflower", "isshortage")
    # Heuristic: insert space before known English words that got stuck
    stuck_words = [
        "flower", "shortage", "territory", "snapback", "point",
        "killing", "tesuji", "eye", "dead", "shape",
    ]
    for word in stuck_words:
        result = re.sub(rf'([a-z])({word})', r'\1 \2', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def _fix_tree_comments(node) -> None:
    """Recursively fix spacing in all solution tree node comments."""
    if node.comment:
        node.comment = _fix_comment_spacing(node.comment)
    for child in node.children:
        _fix_tree_comments(child)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_puzzle(
    sgf_path: Path,
    json_path: Path,
    level_dir: str,
) -> tuple[str | None, str]:
    """Process one puzzle pair. Returns (rebuilt_sgf, puzzle_id) or (None, puzzle_id)."""
    sgf_text = sgf_path.read_text(encoding="utf-8")
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    puzzle_id = meta.get("puzzle_id", sgf_path.stem)

    # Validate raw SGF first
    result = validate_sgf_puzzle(sgf_text)
    if not result.is_valid:
        print(f"  SKIP {puzzle_id}: validation failed — {result.reason}")
        return None, puzzle_id

    # Parse and whitelist-rebuild
    tree = parse_sgf(sgf_text)
    builder = SGFBuilder.from_tree(tree)

    # Fix spacing in existing move comments (stuck number-letter patterns)
    _fix_tree_comments(builder.solution_tree)

    # Fix YG level slug (strip :N suffix if present)
    level_slug = meta.get("yengo_level") or LEVEL_MAP.get(meta.get("level_num", ""), "intermediate")
    builder.set_level_slug(level_slug)

    # Clear any pre-existing tags, then derive from prompt
    builder.yengo_props.tags = []
    prompt = meta.get("prompt_english", "")
    tags = derive_tags(prompt)
    if tags:
        builder.add_tags(tags)

    # Collection from level dir
    coll = derive_collection(level_dir)
    if coll:
        builder.yengo_props.collections = [coll]

    # Root comment = intent objective slug (side-aware)
    intent = derive_intent(prompt, tree.player_to_move)
    if intent:
        builder.set_comment(intent)
    else:
        # Also try Japanese prompt for basic patterns
        prompt_jp = meta.get("prompt_japanese", "")
        intent_jp = _derive_intent_from_japanese(prompt_jp, tree.player_to_move)
        if intent_jp:
            builder.set_comment(intent_jp)
        else:
            builder.set_comment("")

    # Strip GN (publish stage sets it) by clearing metadata
    builder.metadata.pop("GN", None)

    rebuilt = builder.build()
    return rebuilt, puzzle_id


def _derive_intent_from_japanese(prompt_jp: str, player: Color) -> str | None:
    """Fallback intent derivation from Japanese prompt for garbled-English cases."""
    side = _derive_side(player)
    jp_patterns: list[tuple[str, str]] = [
        ("ヨセ",     "endgame"),
        ("取って",   "kill"),
        ("取りに",   "kill"),
        ("助けて",   "live"),
        ("逃げて",   "live"),
        ("生きて",   "live"),
        ("守る",     "live"),
        ("コウ",     "win-ko"),
        ("分断",     "cut"),
        ("ツギ",     "connect"),
        ("手筋",     "tesuji"),
        ("うってがえし", "tesuji"),
    ]
    for pattern, action in jp_patterns:
        if pattern in prompt_jp:
            return f"{side}-to-{action}" if action != "endgame" else f"{side}-{action}"
    # Fallback: if it's a tsumego site, "black-to-play" is a valid generic
    return f"{side}-to-play"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Repackage syougo downloads into pipeline-ready SGFs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--levels", type=str, default="", help="Comma-separated level numbers (e.g., 1,2,3)")
    args = parser.parse_args()

    downloads_dir = TOOL_DIR / "downloads"
    output_root = PROJECT_ROOT / "external-sources" / "syougo"

    if not downloads_dir.exists():
        print(f"ERROR: Downloads directory not found: {rel_path(downloads_dir)}")
        return 1

    # Determine which levels to process
    level_dirs = sorted(d for d in downloads_dir.iterdir() if d.is_dir())
    if args.levels:
        requested = set(args.levels.split(","))
        level_dirs = [d for d in level_dirs if any(f"level_{n}_" in d.name or d.name.endswith(f"_{n}") for n in requested)]

    stats = {"processed": 0, "skipped": 0, "written": 0}

    print(f"\n{'='*60}")
    print("Syougo Processor")
    print(f"{'='*60}")
    print(f"Input:  {rel_path(downloads_dir)}")
    print(f"Output: {rel_path(output_root)}")
    print(f"Levels: {len(level_dirs)}")
    print(f"Dry run: {args.dry_run}")
    print(f"{'='*60}\n")

    for level_dir in level_dirs:
        level_name = level_dir.name
        sgf_files = sorted(level_dir.glob("*.sgf"))

        if not sgf_files:
            continue

        out_dir = output_root / level_name
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{level_name}] {len(sgf_files)} puzzles")

        for sgf_path in sgf_files:
            json_path = sgf_path.with_suffix(".json")
            if not json_path.exists():
                print(f"  SKIP {sgf_path.stem}: no JSON metadata")
                stats["skipped"] += 1
                continue

            rebuilt, puzzle_id = process_puzzle(sgf_path, json_path, level_name)

            if rebuilt is None:
                stats["skipped"] += 1
                continue

            stats["processed"] += 1

            if args.dry_run:
                # Show sample for first puzzle in each level
                if stats["processed"] == 1 or sgf_files.index(sgf_path) == 0:
                    preview = rebuilt[:120] + "..." if len(rebuilt) > 120 else rebuilt
                    print(f"  PREVIEW {puzzle_id}: {preview}")
            else:
                out_path = out_dir / f"{puzzle_id}.sgf"
                out_path.write_text(rebuilt, encoding="utf-8")
                stats["written"] += 1

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped:   {stats['skipped']}")
    print(f"Written:   {stats['written']}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
