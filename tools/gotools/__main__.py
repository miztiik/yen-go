"""Entry point for ``python -m tools.gotools``.

Subcommands:
    (default)          — Run the GoTools ingestor
    embed-collections  — Embed YL[] into GoTools SGFs via filename pattern
"""

import argparse
import re
import sys
from pathlib import Path

# GoTools level number → name for CollectionMatcher lookup
GOTOOLS_LEVEL_MAP: dict[str, str] = {
    "1": "gotools elementary",
    "2": "gotools intermediate",
    "3": "gotools upper-intermediate",
    "4": "gotools advanced",
    "5": "gotools low-dan",
    "6": "gotools high-dan",
}

_GOTOOLS_PATTERN = re.compile(
    r"gotools_lv(?P<level>\d+)_(?P<chapter>\d+)_p(?P<position>\d+)\.sgf"
)

_DEFAULT_SOURCE_DIR = Path("external-sources/gotools")


def embed_collections_cmd() -> int:
    """Embed YL[] into GoTools SGF files using filename pattern strategy."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.gotools embed-collections",
        description="Embed YL[slug:chapter/position] into GoTools SGFs from filename pattern.",
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

    args = parser.parse_args(sys.argv[2:])

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    from tools.core.collection_embedder import (
        EmbedCheckpoint,
        FilenamePatternStrategy,
        embed_collections,
    )
    from tools.core.collection_matcher import CollectionMatcher
    from tools.core.logging import setup_logging

    logger = setup_logging(
        source_dir,
        "gotools-embed",
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
        log_suffix="embed-collections",
    )

    matcher = CollectionMatcher()
    strategy = FilenamePatternStrategy(
        _GOTOOLS_PATTERN, matcher, level_map=GOTOOLS_LEVEL_MAP
    )

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
    if len(sys.argv) > 1 and sys.argv[1] == "embed-collections":
        sys.exit(embed_collections_cmd())
    else:
        from tools.gotools.gotools_ingestor import main
        sys.exit(main() or 0)
