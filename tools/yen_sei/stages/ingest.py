"""ingest stage (v2): tier-aware copy from qualification_v2.jsonl into data/sources/.

This stage NEVER scans external-sources/ itself - it reads the qualification report
produced by the `qualify` stage. Files are copied with tier-prefixed names so the
harvest stage can recover the tier without parsing SGF content.

Filename convention (from curation_config.json):
    {tier}_{source}_{original_stem}.sgf
    e.g., gold_goproblems_3300.sgf, silver_kisvadim-goproblems_0025.sgf

Outputs:
    data/sources/                         flat directory of tier-prefixed SGFs
    data/sources/_manifest.jsonl          one row per copied file with provenance
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from tools.yen_sei.config import SOURCES_DIR
from tools.yen_sei.governance.config_loader import load_config
from tools.yen_sei.stages.qualify import QUALIFICATION_JSONL
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)

MANIFEST_PATH = SOURCES_DIR / "_manifest.jsonl"

_STEM_SAFE = re.compile(r"[^A-Za-z0-9.\-]+")


def _safe_stem(stem: str) -> str:
    cleaned = _STEM_SAFE.sub("-", stem).strip("-")
    return cleaned or "unnamed"


def run_ingest(
    qualification_jsonl: str | None = None,
    config_path: str | None = None,
    tiers: tuple[str, ...] = ("gold", "silver", "bronze"),
    dry_run: bool = False,
    clean: bool = True,
) -> None:
    """Copy qualified SGFs into data/sources/ with tier-prefixed names."""
    set_context(stage="ingest")
    cfg = load_config(config_path)
    qual_path = Path(qualification_jsonl) if qualification_jsonl else QUALIFICATION_JSONL

    if not qual_path.exists():
        logger.error("Qualification file not found: %s. Run 'yen-sei qualify' first.", qual_path)
        return

    pattern = cfg.filename_pattern
    logger.info("Reading qualification: %s", qual_path)
    logger.info("Filename pattern: %s", pattern)
    logger.info("Tiers to ingest: %s", ", ".join(tiers))

    selected: list[dict] = []
    with qual_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("tier") in tiers:
                selected.append(row)

    logger.info("Selected %d rows across tiers %s", len(selected), tiers)

    if dry_run:
        per_tier: Counter = Counter(r["tier"] for r in selected)
        per_source: Counter = Counter((r["source"], r["tier"]) for r in selected)
        print(f"\nDry run: would copy {len(selected):,} files")
        for tier in ("gold", "silver", "bronze"):
            if per_tier.get(tier):
                print(f"  {tier}: {per_tier[tier]:,}")
        print("\nBy source/tier:")
        for (src, tier), count in sorted(per_source.items()):
            print(f"  {src} / {tier}: {count:,}")
        return

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    if clean:
        existing = list(SOURCES_DIR.glob("*.sgf"))
        if existing:
            logger.info("Clearing %d existing files in %s", len(existing), SOURCES_DIR)
            for f in existing:
                f.unlink()
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink()

    copied: Counter = Counter()
    skipped_missing = 0
    skipped_collision = 0
    seen_dest_names: set[str] = set()

    with MANIFEST_PATH.open("w", encoding="utf-8") as manifest:
        for row in selected:
            src_path = Path(row["file_path"])
            if not src_path.exists():
                skipped_missing += 1
                continue
            tier = row["tier"]
            source = row["source"]
            stem = _safe_stem(row.get("original_stem") or src_path.stem)
            dest_name = pattern.format(tier=tier, source=source, original_stem=stem)
            if dest_name in seen_dest_names:
                suffix = hashlib.sha1(str(src_path).encode("utf-8")).hexdigest()[:8]
                base, ext = dest_name.rsplit(".", 1)
                dest_name = f"{base}-{suffix}.{ext}"
                if dest_name in seen_dest_names:
                    skipped_collision += 1
                    continue
            seen_dest_names.add(dest_name)
            dest_path = SOURCES_DIR / dest_name
            try:
                shutil.copyfile(src_path, dest_path)
            except OSError as e:
                logger.warning("Copy failed %s -> %s: %s", src_path, dest_path, e)
                continue
            copied[tier] += 1
            manifest.write(json.dumps({
                "dest_name": dest_name,
                "tier": tier,
                "source": source,
                "original_stem": stem,
                "source_path": str(src_path),
                "curation_run_id": row.get("curation_run_id", ""),
                "english_word_ratio": row.get("english_word_ratio"),
                "correct_explanation_chars": row.get("correct_explanation_chars"),
                "wrong_explanation_chars": row.get("wrong_explanation_chars"),
                "explanation_node_count": row.get("explanation_node_count"),
                "techniques_found": row.get("techniques_found", []),
            }) + "\n")

    total = sum(copied.values())
    logger.info("Ingest complete: %d copied, %d missing, %d collisions",
                total, skipped_missing, skipped_collision)
    print(f"\nCopied {total:,} files into {SOURCES_DIR}:")
    for tier in ("gold", "silver", "bronze"):
        if copied.get(tier):
            print(f"  {tier}: {copied[tier]:,}")
    print(f"\nManifest: {MANIFEST_PATH}")
