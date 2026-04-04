#!/usr/bin/env python3
"""Enrichment script for all 10 MAEDA directories.

Orchestrates: rename → prepare → translate → merge N[] → embed YL[] → verify.

Usage:
    python -m tools.kisvadim_goproblems._enrich_maeda [--dry-run] [--dir NAME]
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kisvadim.enrich_maeda")

# ── Directory → slug mapping ────────────────────────────────────────────

MAEDA_DIRS: list[dict] = [
    {
        "dir": "MAEDA NOBUAKI The God of Tsumego VOL1",
        "slug": "maeda-nobuaki-god-of-tsumego",
        "vol_offset": 0,
        "type": "A",  # watermark-only
    },
    {
        "dir": "MAEDA NOBUAKI The God of Tsumego VOL2",
        "slug": "maeda-nobuaki-god-of-tsumego",
        "vol_offset": 100,
        "type": "A",
    },
    {
        "dir": "MAEDA NOBUAKI Delightful Tsumego (selected 160 from God of Tsumego)",
        "slug": "maeda-nobuaki-delightful-tsumego",
        "vol_offset": 0,
        "type": "A",
    },
    {
        "dir": "MAEDA NOBUAKI Newly Selected Tsumego 100 Problems for 1-8k",
        "slug": "maeda-nobuaki-newly-selected-100",
        "vol_offset": 0,
        "type": "A",
    },
    {
        "dir": "MAEDA NOBUAKI Newly Selected Tsumego 100 Problems (Continued) for 1-8k",
        "slug": "maeda-nobuaki-newly-selected-100-continued",
        "vol_offset": 0,
        "type": "B",  # Chinese teaching comments + N[]
    },
    {
        "dir": "MAEDA TSUMEGO - Tsumego for the Millions 100 VOL 1",
        "slug": "maeda-nobuaki-tsumego-for-the-millions",
        "vol_offset": 0,
        "type": "A",
    },
    {
        "dir": "MAEDA TSUMEGO Collection - SHOKYU",
        "slug": "maeda-nobuaki-beginner-tsumego",
        "vol_offset": 0,
        "type": "B",  # Chinese teaching comments + N[]
    },
    {
        "dir": "MAEDA TSUMEGO Collection - CHUKYU",
        "slug": "maeda-nobuaki-intermediate-tsumego",
        "vol_offset": 0,
        "type": "A",
    },
    {
        "dir": "MAEDA TSUMEGO Collection - JOKYU",
        "slug": "maeda-nobuaki-advanced-tsumego",
        "vol_offset": 0,
        "type": "A",
    },
    {
        "dir": "MAEDA TSUMEGO Tsumego Masterpieces",
        "slug": "maeda-nobuaki-tsumego-masterpieces",
        "vol_offset": 0,
        "type": "C",  # Japanese literary comments
    },
]

BASE = Path("external-sources/kisvadim-goproblems")


# ── Step 1: Rename files to 4-digit zero-padded ────────────────────────

def natural_sort_key(name: str) -> list:
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def rename_to_4digit(source_dir: Path, *, dry_run: bool = False) -> int:
    """Rename SGF files to 0001.sgf, 0002.sgf, ... using natural sort."""
    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: natural_sort_key(p.name))
    if not sgf_files:
        logger.warning("No SGF files in %s", source_dir)
        return 0

    renamed = 0
    # Two-pass rename to avoid collisions
    temp_map: list[tuple[Path, str]] = []
    for i, sgf_path in enumerate(sgf_files, 1):
        new_name = f"{i:04d}.sgf"
        if sgf_path.name != new_name:
            temp_path = sgf_path.parent / f"_tmp_rename_{i:04d}.sgf"
            if not dry_run:
                sgf_path.rename(temp_path)
            temp_map.append((temp_path, new_name))
            renamed += 1

    for temp_path, new_name in temp_map:
        if not dry_run:
            temp_path.rename(temp_path.parent / new_name)

    logger.info("  Renamed %d/%d files to 4-digit format", renamed, len(sgf_files))
    return len(sgf_files)


# ── Step 5: Embed YL[] ─────────────────────────────────────────────────

def embed_yl(source_dir: Path, slug: str, vol_offset: int, *, dry_run: bool = False) -> int:
    """Embed YL[slug:N] into each SGF file. N = sequence + vol_offset."""
    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: natural_sort_key(p.name))
    embedded = 0

    for i, sgf_path in enumerate(sgf_files, 1):
        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" in content:
            continue

        seq = i + vol_offset
        yl_prop = f"YL[{slug}:{seq}]"

        # Insert YL after PL[B] or PL[W]
        pl_match = re.search(r"(PL\[[BW]\])", content)
        if pl_match:
            insert_pos = pl_match.end()
            content = content[:insert_pos] + yl_prop + content[insert_pos:]
        else:
            # Insert after SZ[19] as fallback
            sz_match = re.search(r"(SZ\[\d+\])", content)
            if sz_match:
                insert_pos = sz_match.end()
                content = content[:insert_pos] + yl_prop + content[insert_pos:]
            else:
                # Last resort: insert after first (;
                content = content.replace("(;", f"(;{yl_prop}", 1)

        if not dry_run:
            sgf_path.write_text(content, encoding="utf-8")
        embedded += 1

    logger.info("  Embedded YL[] in %d files (slug=%s, offset=%d)", embedded, slug, vol_offset)
    return embedded


# ── Japanese translation for Masterpieces ──────────────────────────────

JP_DICT_PATH = Path("config/jp-en-dictionary.json")
# Hiragana + Katakana + CJK ranges
JP_CJK_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3400-\u4dbf]")
COMMENT_RE = re.compile(r"C\[([^\]]*(?:\\.[^\]]*)*)\]")


def _load_jp_dictionary() -> dict[str, str]:
    """Load flat JP→EN dictionary from config."""
    data = json.loads(JP_DICT_PATH.read_text(encoding="utf-8"))
    flat: dict[str, str] = {}
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            flat.update(val)
        elif isinstance(val, str):
            flat[key] = val
    return flat


def translate_japanese_comments(source_dir: Path, *, dry_run: bool = False) -> tuple[int, set[str]]:
    """Translate Japanese C[] comments using jp-en-dictionary.json.

    Returns (modified_count, remaining_jp_fragments).
    """
    jp_dict = _load_jp_dictionary()
    # Sort by longest key first for greedy matching
    sorted_keys = sorted(jp_dict.keys(), key=len, reverse=True)

    sgf_files = sorted(source_dir.glob("*.sgf"))
    modified = 0
    remaining: set[str] = set()

    for sgf_path in sgf_files:
        content = sgf_path.read_text(encoding="utf-8")
        new_content = content

        def _replace_jp_comment(m: re.Match) -> str:
            inner = m.group(1).replace("\\]", "]").replace("\\\\", "\\")
            if not JP_CJK_RE.search(inner):
                return m.group(0)

            translated = inner
            for jp_term in sorted_keys:
                if jp_term in translated:
                    translated = translated.replace(jp_term, jp_dict[jp_term])

            # Re-escape
            translated = translated.replace("\\", "\\\\").replace("]", "\\]")
            return f"C[{translated}]"

        new_content = COMMENT_RE.sub(_replace_jp_comment, new_content)

        if new_content != content:
            modified += 1
            if not dry_run:
                sgf_path.write_text(new_content, encoding="utf-8")

        # Check remaining JP/CJK
        for m in COMMENT_RE.finditer(new_content):
            inner = m.group(1).replace("\\]", "]").replace("\\\\", "\\")
            jp_seqs = re.findall(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+", inner)
            remaining.update(jp_seqs)

    logger.info("  JP translation: %d files modified, %d remaining fragments", modified, len(remaining))
    return modified, remaining


# ── Clean non-standard properties from Masterpieces ────────────────────

MK_RE = re.compile(r"MK\[[^\]]*(?:\\.[^\]]*)*\]")
LB_RE = re.compile(r"LB\[[^\]]*(?:\\.[^\]]*)*\]")
ID_RE = re.compile(r"ID\[[^\]]*(?:\\.[^\]]*)*\]")
FF_RE = re.compile(r"FF\[\d+\]")


def clean_masterpiece_props(source_dir: Path, *, dry_run: bool = False) -> int:
    """Remove MK[], LB[], ID[], FF[1] from Masterpieces SGFs (not handled by prepare)."""
    sgf_files = sorted(source_dir.glob("*.sgf"))
    cleaned = 0

    for sgf_path in sgf_files:
        content = sgf_path.read_text(encoding="utf-8")
        new_content = content
        new_content = MK_RE.sub("", new_content)
        new_content = ID_RE.sub("", new_content)
        # Clean up multiple whitespace artifacts
        new_content = re.sub(r"\n\s*\n", "\n", new_content)

        if new_content != content:
            cleaned += 1
            if not dry_run:
                sgf_path.write_text(new_content, encoding="utf-8")

    logger.info("  Cleaned non-standard props from %d files", cleaned)
    return cleaned


# ── Main orchestrator ──────────────────────────────────────────────────

def enrich_directory(entry: dict, *, dry_run: bool = False) -> dict:
    """Run full enrichment pipeline for one MAEDA directory."""
    dir_name = entry["dir"]
    slug = entry["slug"]
    vol_offset = entry["vol_offset"]
    dir_type = entry["type"]
    source_dir = BASE / dir_name

    if not source_dir.exists():
        logger.error("Directory not found: %s", source_dir)
        return {"dir": dir_name, "status": "error", "reason": "not found"}

    logger.info("═══ Enriching: %s (type=%s) ═══", dir_name, dir_type)

    # Step 1: Rename to 4-digit
    logger.info("  Step 1: Rename files")
    file_count = rename_to_4digit(source_dir, dry_run=dry_run)

    # Step 2: Prepare (re-encode + clean)
    logger.info("  Step 2: Prepare (re-encode + clean properties)")
    from tools.kisvadim_goproblems._prepare import prepare_sgf_files
    prep_stats = prepare_sgf_files(source_dir, dry_run=dry_run)
    logger.info("  Prepare: converted=%d errors=%d", prep_stats.converted, prep_stats.errors)

    if prep_stats.errors > 0:
        logger.warning("  Prepare errors in: %s", prep_stats.error_files)

    # Step 3: Translate CJK
    remaining_cjk: set[str] = set()
    if dir_type in ("A", "B"):
        logger.info("  Step 3: Translate CJK (Chinese)")
        from tools.kisvadim_goproblems._translate import translate_sgf_files
        trans_stats = translate_sgf_files(source_dir, dry_run=dry_run)
        logger.info("  Translate: modified=%d remaining_cjk=%d", trans_stats.modified, len(trans_stats.remaining_cjk_fragments))
        remaining_cjk = trans_stats.remaining_cjk_fragments
    elif dir_type == "C":
        logger.info("  Step 3a: Clean non-standard Masterpiece properties")
        clean_masterpiece_props(source_dir, dry_run=dry_run)
        logger.info("  Step 3b: Translate Japanese comments")
        _, remaining_cjk = translate_japanese_comments(source_dir, dry_run=dry_run)

    # Step 4: Merge N[] into C[] (only for type B dirs with N[])
    if dir_type == "B":
        logger.info("  Step 4: Merge N[] into C[]")
        from tools.kisvadim_goproblems._merge_n_into_c import merge_node_names
        merge_stats = merge_node_names(source_dir, dry_run=dry_run)
        logger.info("  Merge: modified=%d errors=%d", merge_stats.modified, merge_stats.errors)
    else:
        logger.info("  Step 4: Skipped (no N[] in type %s)", dir_type)

    # Step 5: Embed YL[]
    logger.info("  Step 5: Embed YL[]")
    embed_yl(source_dir, slug, vol_offset, dry_run=dry_run)

    # Step 6: Verify
    logger.info("  Step 6: Verify")
    from tools.kisvadim_goproblems._translate import verify_no_cjk
    vstats = verify_no_cjk(source_dir)

    sgf_files = sorted(source_dir.glob("*.sgf"))
    yl_count = sum(1 for f in sgf_files if "YL[" in f.read_text(encoding="utf-8"))
    ap_count = sum(1 for f in sgf_files if "AP[" in f.read_text(encoding="utf-8"))

    result = {
        "dir": dir_name,
        "slug": slug,
        "files": len(sgf_files),
        "yl_coverage": f"{yl_count}/{len(sgf_files)}",
        "remaining_cjk": vstats.files_with_cjk,
        "remaining_cjk_fragments": sorted(vstats.unique_fragments) if vstats.unique_fragments else [],
        "ap_remaining": ap_count,
        "status": "ok" if vstats.is_clean and yl_count == len(sgf_files) and ap_count == 0 else "needs_review",
    }

    logger.info("  Result: %s", json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Enrich MAEDA directories")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    parser.add_argument("--dir", type=str, help="Process only this directory name (substring match)")
    parser.add_argument("--type", type=str, choices=["A", "B", "C"], help="Process only this type")
    args = parser.parse_args()

    dirs_to_process = MAEDA_DIRS
    if args.dir:
        dirs_to_process = [d for d in dirs_to_process if args.dir.lower() in d["dir"].lower()]
    if args.type:
        dirs_to_process = [d for d in dirs_to_process if d["type"] == args.type]

    if not dirs_to_process:
        logger.error("No directories matched the filter")
        sys.exit(1)

    logger.info("Processing %d directories (dry_run=%s)", len(dirs_to_process), args.dry_run)

    results = []
    for entry in dirs_to_process:
        result = enrich_directory(entry, dry_run=args.dry_run)
        results.append(result)

    # Summary
    logger.info("\n═══════════════════════════════════")
    logger.info("ENRICHMENT SUMMARY")
    logger.info("═══════════════════════════════════")
    for r in results:
        status_marker = "OK" if r.get("status") == "ok" else "REVIEW"
        logger.info("  [%s] %s → %s (%s files, YL %s)",
                     status_marker, r["dir"][:50], r.get("slug", "?"), r.get("files", "?"), r.get("yl_coverage", "?"))
        if r.get("remaining_cjk_fragments"):
            logger.info("    Remaining CJK: %s", r["remaining_cjk_fragments"][:10])

    # Write summary JSON
    summary_path = Path("tools/kisvadim_goproblems/_maeda_enrichment_results.json")
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("\nResults written to %s", summary_path)


if __name__ == "__main__":
    main()
