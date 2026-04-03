"""Entry point for ``python -m tools.kisvadim_goproblems``.

Embeds YL[] into kisvadim-goproblems SGFs using phrase-match strategy.
Directory names (e.g. "CHO CHIKUN Encyclopedia Life And Death - Elementary")
are matched to collection slugs via CollectionMatcher.

Usage:
    python -m tools.kisvadim_goproblems --dry-run
    python -m tools.kisvadim_goproblems --resume --verbose
"""

import argparse
import sys
from pathlib import Path

_DEFAULT_SOURCE_DIR = Path("external-sources/kisvadim-goproblems")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.kisvadim_goproblems",
        description="Embed YL[slug:chapter/position] into kisvadim-goproblems SGFs.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=_DEFAULT_SOURCE_DIR,
        help=f"Root directory of SGF files (default: {_DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--no-log-file", action="store_true", help="Console-only logging")

    args = parser.parse_args()

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    from tools.core.collection_embedder import (
        EmbedCheckpoint,
        PhraseMatchStrategy,
        embed_collections,
    )
    from tools.core.collection_matcher import CollectionMatcher
    from tools.core.logging import setup_logging

    logger = setup_logging(
        source_dir,
        "kisvadim-embed",
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
        log_suffix="embed-collections",
    )

    matcher = CollectionMatcher()
    strategy = PhraseMatchStrategy(matcher)

    logger.info(f"Source: {source_dir}  dry_run={args.dry_run}")

    checkpoint = None
    if args.resume:
        from tools.core.checkpoint import load_checkpoint
        from tools.core.collection_embedder import CHECKPOINT_FILENAME
        checkpoint = load_checkpoint(source_dir, EmbedCheckpoint, CHECKPOINT_FILENAME)

    summary = embed_collections(
        source_dir, strategy, matcher, logger,
        dry_run=args.dry_run, checkpoint=checkpoint,
    )

    print(
        f"\nEmbedded: {summary.embedded}  Already: {summary.already_embedded}  "
        f"Conflicts: {summary.conflicts}  Skipped: {summary.skipped}  "
        f"Errors: {summary.errors}  Coverage: {summary.coverage_pct:.1f}%"
    )
    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
