"""Embed YL[] collection membership tags in all Go Seigen directories.

Usage:
    python -m tools.kisvadim_goproblems._embed_go_seigen [--dry-run]
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _natural_sort_key(name: str) -> list:
    """Sort key that handles embedded numbers naturally."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", name)]


def embed_yl_flat(
    source_dir: Path, slug: str, vol_offset: int = 0, *, dry_run: bool = False,
) -> int:
    """Embed YL[slug:N] into each SGF file. N = file_index + vol_offset."""
    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: _natural_sort_key(p.name))
    embedded = 0

    for i, sgf_path in enumerate(sgf_files, 1):
        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" in content:
            continue

        seq = i + vol_offset
        yl_prop = f"YL[{slug}:{seq}]"

        pl_match = re.search(r"(PL\[[BW]\])", content)
        if pl_match:
            insert_pos = pl_match.end()
            content = content[:insert_pos] + yl_prop + content[insert_pos:]
        else:
            sz_match = re.search(r"(SZ\[\d+\])", content)
            if sz_match:
                insert_pos = sz_match.end()
                content = content[:insert_pos] + yl_prop + content[insert_pos:]
            else:
                content = content.replace("(;", f"(;{yl_prop}", 1)

        if not dry_run:
            sgf_path.write_text(content, encoding="utf-8")
        embedded += 1

    logger.info("  Embedded YL[] in %d files (slug=%s, offset=%d)", embedded, slug, vol_offset)
    return embedded


def embed_yl_chapter(
    source_dir: Path, slug: str, chapter: str, *, dry_run: bool = False,
) -> int:
    """Embed YL[slug:chapter/N] into each SGF file."""
    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: _natural_sort_key(p.name))
    embedded = 0

    for i, sgf_path in enumerate(sgf_files, 1):
        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" in content:
            continue

        yl_prop = f"YL[{slug}:{chapter}/{i}]"

        pl_match = re.search(r"(PL\[[BW]\])", content)
        if pl_match:
            insert_pos = pl_match.end()
            content = content[:insert_pos] + yl_prop + content[insert_pos:]
        else:
            sz_match = re.search(r"(SZ\[\d+\])", content)
            if sz_match:
                insert_pos = sz_match.end()
                content = content[:insert_pos] + yl_prop + content[insert_pos:]
            else:
                content = content.replace("(;", f"(;{yl_prop}", 1)

        if not dry_run:
            sgf_path.write_text(content, encoding="utf-8")
        embedded += 1

    logger.info("  Embedded YL[] in %d files (slug=%s, chapter=%s)", embedded, slug, chapter)
    return embedded


def main(*, dry_run: bool = False) -> None:
    base = Path("external-sources/kisvadim-goproblems")
    total = 0

    # ── A. Flat directories (no chapters) ──
    flat_dirs = [
        ("GO SEIGEN Evil Moves Tsumego", "go-seigen-evil-moves", 0),
        ("GO SEIGEN Striving Constantly For Self-Improvement", "go-seigen-jikyou-fusoku", 0),
        ("GO SEIGEN Tsumego Collection - The Long-Lived Stone Is Not Old", "go-seigen-jushi-furou", 0),
    ]
    for dirname, slug, offset in flat_dirs:
        d = base / dirname
        logger.info("Embedding %s ...", dirname)
        total += embed_yl_flat(d, slug, offset, dry_run=dry_run)

    # ── B. Multi-volume flat (Dojo, shared slug, offset) ──
    logger.info("Embedding GO SEIGEN TSUMEGO DOJO VOL 1 ...")
    total += embed_yl_flat(base / "GO SEIGEN TSUMEGO DOJO VOL 1", "go-seigen-tsumego-dojo", 0, dry_run=dry_run)
    logger.info("Embedding GO SEIGEN TSUMEGO DOJO VOL 2 ...")
    total += embed_yl_flat(base / "GO SEIGEN TSUMEGO DOJO VOL 2", "go-seigen-tsumego-dojo", 99, dry_run=dry_run)

    # Also embed in the merged Dojo directory
    logger.info("Embedding GO SEIGEN TSUMEGO DOJO (merged) vol-1 ...")
    total += embed_yl_flat(base / "GO SEIGEN TSUMEGO DOJO" / "vol-1", "go-seigen-tsumego-dojo", 0, dry_run=dry_run)
    logger.info("Embedding GO SEIGEN TSUMEGO DOJO (merged) vol-2 ...")
    total += embed_yl_flat(base / "GO SEIGEN TSUMEGO DOJO" / "vol-2", "go-seigen-tsumego-dojo", 99, dry_run=dry_run)

    # ── C. Shokyuu + Jokyuu as chapters ──
    logger.info("Embedding GO SEIGEN Tsumego Collection 1 - Shokyuu ...")
    total += embed_yl_chapter(
        base / "GO SEIGEN Tsumego Collection 1 - Shokyuu",
        "go-seigen-tsumego-collection", "shokyuu", dry_run=dry_run,
    )
    logger.info("Embedding GO SEIGEN Tsumego Collection 2 - Jokyuu ...")
    total += embed_yl_chapter(
        base / "GO SEIGEN Tsumego Collection 2 - Jokyuu",
        "go-seigen-tsumego-collection", "jokyuu", dry_run=dry_run,
    )

    # ── D. Reading & Training (chaptered subdirs) ──
    rt_base = base / "GO SEIGEN Reading and Training Actual Game Situations"
    rt_chapters = [
        ("part 1 - kyu", "kyu"),
        ("part 2 - dan", "dan"),
        ("part 3 - high dan", "high-dan"),
    ]
    for subdir, chapter_slug in rt_chapters:
        logger.info("Embedding Reading & Training / %s ...", subdir)
        total += embed_yl_chapter(
            rt_base / subdir,
            "go-seigen-reading-training", chapter_slug, dry_run=dry_run,
        )

    # ── E. Segoe split (flat, technique-based numbering) ──
    logger.info("Embedding segoe-kensaku-tesuji-dictionary_split ...")
    total += embed_yl_flat(
        base / "segoe-kensaku-tesuji-dictionary_split",
        "segoe-kensaku-tesuji-dictionary", 0, dry_run=dry_run,
    )

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("Done (%s). Total files embedded: %d", mode, total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
