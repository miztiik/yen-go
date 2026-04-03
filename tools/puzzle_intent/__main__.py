"""CLI entry point for puzzle_intent.

Usage:
    python -m tools.puzzle_intent "Black to play and live"
    python -m tools.puzzle_intent --no-semantic "Black to play"
    python -m tools.puzzle_intent --file comment.txt
    python -m tools.puzzle_intent --rebuild-embeddings
    echo "Black to play" | python -m tools.puzzle_intent

Examples:
    # Exact match (fast, deterministic)
    $ python -m tools.puzzle_intent "Black to play"
    {"objective_id": "MOVE.BLACK.PLAY", "slug": "black-to-play", "name": "Black to Play", "confidence": 1.0, "match_tier": "exact", ...}

    # Semantic match (requires sentence-transformers)
    $ python -m tools.puzzle_intent "Play as black and win"
    {"objective_id": "MOVE.BLACK.PLAY", "slug": "black-to-play", "name": "Black to Play", "confidence": 0.82, "match_tier": "semantic", ...}

    # Read from file (recommended for CJK / multi-line SGF comments)
    $ python -m tools.puzzle_intent --file sgf_comment.txt
    {"objective_id": "LIFE_AND_DEATH.BLACK.LIVE", ...}

    # Rebuild embedding cache (run after changing aliases in puzzle-objectives.json)
    $ python -m tools.puzzle_intent --rebuild-embeddings
    Cache rebuilt: a1b2c3d4e5f67890.npy (107 aliases, 384 dims)

    # No match
    $ python -m tools.puzzle_intent "Hello world"
    {"objective_id": null, "confidence": 0.0, "match_tier": "none", ...}

Exit codes:
    0 - Objective matched (or rebuild succeeded)
    1 - No match found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .intent_resolver import resolve_intent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.puzzle_intent",
        description=(
            "Resolve puzzle objectives from noisy SGF comment text.\n\n"
            "Uses a tiered matching strategy:\n"
            "  Tier 1: Deterministic exact substring/token matching (fast)\n"
            "  Tier 2: Sentence-transformer semantic similarity (fuzzy)\n\n"
            "Returns JSON with objective_id, slug, name, confidence, match_tier, and more.\n"
            "Exit code 0 if matched, 1 if no match."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  python -m tools.puzzle_intent "Black to play and live"\n'
            '  python -m tools.puzzle_intent --no-semantic "Black to play"\n'
            "  python -m tools.puzzle_intent --file sgf_comment.txt\n"
            '  echo "Black to play" | python -m tools.puzzle_intent\n'
        ),
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text to resolve. Reads from --file or stdin if omitted.",
    )
    parser.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        default=None,
        help="Read input text from a UTF-8 file (recommended for CJK / multi-line text).",
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        default=False,
        help="Disable semantic (ML) matching; use deterministic mode only.",
    )
    parser.add_argument(
        "--rebuild-embeddings",
        action="store_true",
        default=False,
        help="Rebuild the .npy embedding cache and exit. Run after changing aliases.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run puzzle intent resolution from CLI arguments.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 if matched, 1 if no match.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Handle --rebuild-embeddings (standalone action, no text needed)
    if args.rebuild_embeddings:
        import logging

        from .semantic_matcher import rebuild_embedding_cache

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        cache_file = rebuild_embedding_cache()
        print(f"Embedding cache rebuilt: {cache_file}")
        return 0

    # Priority: positional arg > --file > stdin
    text = args.text
    if text is not None and args.file is not None:
        parser.error("Cannot use both positional text and --file.")

    if text is None and args.file is not None:
        path = Path(args.file)
        if not path.is_file():
            parser.error(f"File not found: {args.file}")
        text = path.read_text(encoding="utf-8").strip()

    if text is None:
        if sys.stdin.isatty():
            parser.error("No text provided. Pass text as argument, --file, or pipe via stdin.")
        # Force UTF-8 for stdin to handle CJK on Windows
        stdin = sys.stdin
        if hasattr(stdin, "reconfigure"):
            stdin.reconfigure(encoding="utf-8", errors="replace")
        text = stdin.read().strip()

    if not text:
        parser.error("Empty text provided.")

    enable_semantic = not args.no_semantic
    result = resolve_intent(text, enable_semantic=enable_semantic)

    # Force UTF-8 for stdout to handle CJK on Windows
    stdout = sys.stdout
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")

    json.dump(result.to_dict(), stdout, indent=2, ensure_ascii=False)
    stdout.write("\n")

    return 0 if result.matched else 1


if __name__ == "__main__":
    sys.exit(main())
