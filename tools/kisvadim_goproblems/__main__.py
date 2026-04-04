"""Entry point for ``python -m tools.kisvadim_goproblems``.

Subcommands:
    embed              Embed YL[] into all kisvadim-goproblems SGFs via phrase-match
    prepare            Re-encode SGFs to UTF-8 and clean properties (AP, GN, EV)
    embed-chapters     Embed YL[] with chapter/position via directory mapping
    merge-node-names   Merge N[] (node name) into C[] (comment) for all SGFs
    translate          Translate CJK in C[] and N[] comments to English
    verify             Verify no CJK remains in C[] and N[] comments

Usage:
    python -m tools.kisvadim_goproblems embed --dry-run
    python -m tools.kisvadim_goproblems prepare --source-dir "external-sources/.../WEIQI 1000 PROBLEMS"
    python -m tools.kisvadim_goproblems embed-chapters --mapping _chapter_mapping.json --dry-run
    python -m tools.kisvadim_goproblems merge-node-names --source-dir "external-sources/.../YAMADA..."
    python -m tools.kisvadim_goproblems translate --source-dir "external-sources/.../Hashimoto..."
    python -m tools.kisvadim_goproblems verify --source-dir "external-sources/.../Hashimoto..."
"""

import argparse
import json
import sys
from pathlib import Path

_DEFAULT_SOURCE_DIR = Path("external-sources/kisvadim-goproblems")


def _cmd_embed(args: argparse.Namespace) -> int:
    """Embed YL[] into kisvadim-goproblems SGFs using phrase-match strategy."""
    from tools.core.collection_embedder import (
        EmbedCheckpoint,
        PhraseMatchStrategy,
        embed_collections,
    )
    from tools.core.collection_matcher import CollectionMatcher
    from tools.core.logging import setup_logging

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

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


def _cmd_prepare(args: argparse.Namespace) -> int:
    """Re-encode SGFs to UTF-8 and clean properties via parser/builder round-trip."""
    import logging

    from tools.kisvadim_goproblems._prepare import prepare_sgf_files

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    stats = prepare_sgf_files(source_dir, dry_run=args.dry_run)

    print(
        f"\nTotal: {stats.total}  Converted: {stats.converted}  "
        f"Errors: {stats.errors}"
    )
    if stats.error_files:
        print(f"Error files: {', '.join(stats.error_files[:10])}")
        if len(stats.error_files) > 10:
            print(f"  ... and {len(stats.error_files) - 10} more")

    return 0 if stats.errors == 0 else 1


def _cmd_embed_chapters(args: argparse.Namespace) -> int:
    """Embed YL[] with chapter/position using directory-to-chapter mapping."""
    from tools.core.collection_embedder import (
        DirectoryChapterStrategy,
        EmbedCheckpoint,
        embed_collections,
    )
    from tools.core.collection_matcher import CollectionMatcher
    from tools.core.logging import setup_logging

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    # Load the chapter mapping
    mapping_path: Path = args.mapping
    if not mapping_path.is_absolute():
        # Resolve relative to the tool's package directory
        mapping_path = Path(__file__).parent / mapping_path
    if not mapping_path.is_file():
        print(f"Error: mapping file not found: {mapping_path}")
        return 1

    with open(mapping_path, encoding="utf-8") as f:
        mapping_data = json.load(f)

    collection_slug = mapping_data["collection_slug"]
    chapter_map = mapping_data["chapters"]

    logger = setup_logging(
        source_dir,
        "kisvadim-embed-chapters",
        verbose=args.verbose,
        log_to_file=not args.no_log_file,
        log_suffix="embed-chapters",
    )

    matcher = CollectionMatcher()
    strategy = DirectoryChapterStrategy(chapter_map, collection_slug)

    logger.info(
        f"Source: {source_dir}  collection={collection_slug}  "
        f"chapters={len(chapter_map)}  dry_run={args.dry_run}"
    )

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
        f"\nEmbedded: {summary.embedded}  Updated: {summary.updated}  "
        f"Already: {summary.already_embedded}  Conflicts: {summary.conflicts}  "
        f"Skipped: {summary.skipped}  Errors: {summary.errors}  "
        f"Coverage: {summary.coverage_pct:.1f}%"
    )
    return 0 if summary.errors == 0 else 1


def _cmd_translate(args: argparse.Namespace) -> int:
    """Translate CJK in C[] and N[] comments to English."""
    from tools.kisvadim_goproblems._translate import translate_sgf_files

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    stats = translate_sgf_files(source_dir, dry_run=args.dry_run)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(
        f"\n{prefix}Total: {stats.total}  Modified: {stats.modified}  "
        f"Translated: {stats.comments_translated}  "
        f"Remaining CJK: {stats.files_with_remaining_cjk}  Errors: {stats.errors}"
    )
    if stats.remaining_cjk_fragments:
        frags = sorted(stats.remaining_cjk_fragments)
        print(f"Remaining CJK fragments ({len(frags)}): {frags}")
    if stats.error_files:
        print(f"Error files: {', '.join(stats.error_files[:10])}")

    return 0 if stats.errors == 0 and stats.files_with_remaining_cjk == 0 else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verify no CJK remains in C[] and N[] comments."""
    from tools.kisvadim_goproblems._translate import verify_no_cjk

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    stats = verify_no_cjk(source_dir)

    print(f"\n=== Verification: {source_dir.name} ===")
    print(f"  Total files:              {stats.total}")
    print(f"  Files with remaining CJK: {stats.files_with_cjk}")
    print(f"  Comments with CJK:        {stats.comments_with_cjk}")
    if stats.unique_fragments:
        print(f"  Unique CJK fragments:     {sorted(stats.unique_fragments)}")
        print(f"  Problem files:")
        for pf in stats.problem_files[:20]:
            print(f"    - {pf}")
    else:
        print(f"  Status: CLEAN")

    return 0 if stats.is_clean else 1


def _cmd_merge_node_names(args: argparse.Namespace) -> int:
    """Merge N[] node name properties into C[] comments."""
    from tools.kisvadim_goproblems._merge_n_into_c import merge_node_names

    source_dir: Path = args.source_dir
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}")
        return 1

    stats = merge_node_names(source_dir, dry_run=args.dry_run)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(
        f"\n{prefix}Total: {stats.total}  Modified: {stats.modified}  "
        f"Errors: {stats.errors}"
    )
    if stats.error_files:
        print(f"Error files: {', '.join(stats.error_files[:10])}")
        if len(stats.error_files) > 10:
            print(f"  ... and {len(stats.error_files) - 10} more")

    return 0 if stats.errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.kisvadim_goproblems",
        description="Manage kisvadim-goproblems SGF files: embed collections, prepare encoding, embed chapters.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- embed (default behavior) ---
    p_embed = subparsers.add_parser(
        "embed",
        help="Embed YL[] into SGFs via phrase-match strategy (default)",
    )
    p_embed.add_argument(
        "--source-dir", type=Path, default=_DEFAULT_SOURCE_DIR,
        help=f"Root directory of SGF files (default: {_DEFAULT_SOURCE_DIR})",
    )
    p_embed.add_argument("--dry-run", action="store_true", help="Report without writing")
    p_embed.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    p_embed.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    p_embed.add_argument("--no-log-file", action="store_true", help="Console-only logging")

    # --- prepare ---
    p_prepare = subparsers.add_parser(
        "prepare",
        help="Re-encode SGFs to UTF-8 and clean properties (AP, GN, EV)",
    )
    p_prepare.add_argument(
        "--source-dir", type=Path, required=True,
        help="Directory containing SGF files to prepare",
    )
    p_prepare.add_argument("--dry-run", action="store_true", help="Report without writing")
    p_prepare.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    # --- embed-chapters ---
    p_chapters = subparsers.add_parser(
        "embed-chapters",
        help="Embed YL[] with chapter/position via directory mapping",
    )
    p_chapters.add_argument(
        "--source-dir", type=Path, required=True,
        help="Directory containing chapter subdirectories with SGF files",
    )
    p_chapters.add_argument(
        "--mapping", type=Path, default=Path("_chapter_mapping.json"),
        help="Path to chapter mapping JSON (default: _chapter_mapping.json, relative to tool dir)",
    )
    p_chapters.add_argument("--dry-run", action="store_true", help="Report without writing")
    p_chapters.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    p_chapters.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    p_chapters.add_argument("--no-log-file", action="store_true", help="Console-only logging")

    # --- merge-node-names ---
    p_merge = subparsers.add_parser(
        "merge-node-names",
        help="Merge N[] (node name) into C[] (comment) — preserves branch labels before pipeline drops N[]",
    )
    p_merge.add_argument(
        "--source-dir", type=Path, required=True,
        help="Directory containing SGF files to process (recursive)",
    )
    p_merge.add_argument("--dry-run", action="store_true", help="Report without writing")

    # --- translate ---
    p_translate = subparsers.add_parser(
        "translate",
        help="Translate CJK in C[] and N[] comments to English using cn-en-dictionary",
    )
    p_translate.add_argument(
        "--source-dir", type=Path, required=True,
        help="Directory containing SGF files to translate (recursive)",
    )
    p_translate.add_argument("--dry-run", action="store_true", help="Report without writing")

    # --- verify ---
    p_verify = subparsers.add_parser(
        "verify",
        help="Verify no CJK remains in C[] and N[] comments (read-only scan)",
    )
    p_verify.add_argument(
        "--source-dir", type=Path, required=True,
        help="Directory containing SGF files to verify (recursive)",
    )

    args = parser.parse_args()

    # Default to 'embed' if no subcommand given
    if args.command is None:
        args.command = "embed"
        args.source_dir = _DEFAULT_SOURCE_DIR
        args.dry_run = False
        args.resume = False
        args.verbose = False
        args.no_log_file = False

    if args.command == "embed":
        return _cmd_embed(args)
    elif args.command == "prepare":
        return _cmd_prepare(args)
    elif args.command == "embed-chapters":
        return _cmd_embed_chapters(args)
    elif args.command == "merge-node-names":
        return _cmd_merge_node_names(args)
    elif args.command == "translate":
        return _cmd_translate(args)
    elif args.command == "verify":
        return _cmd_verify(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
