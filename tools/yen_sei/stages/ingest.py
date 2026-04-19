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
from tools.yen_sei.data_paths import from_posix_rel, resolve_latest, to_posix_rel
from tools.yen_sei.governance.config_loader import load_config
from tools.yen_sei.stages.qualify import QUALIFICATION_JSONL
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)

MANIFEST_PATH = SOURCES_DIR / "_manifest.jsonl"

_STEM_SAFE = re.compile(r"[^A-Za-z0-9.\-]+")


def _safe_stem(stem: str) -> str:
    cleaned = _STEM_SAFE.sub("-", stem).strip("-")
    return cleaned or "unnamed"


def _bronze_quality(row: dict, w: dict) -> float:
    """Composite quality score for ranking bronze rows when capped.
    Higher = better. Weights come from curation_config.json -> bronze_selection.sort_formula.
    """
    return (
        float(w.get("correct_chars_weight", 1.0)) * (row.get("correct_explanation_chars") or 0)
        + float(w.get("wrong_chars_weight", 2.0)) * (row.get("wrong_explanation_chars") or 0)
        + float(w.get("techniques_weight", 50.0)) * (row.get("technique_mentions") or 0)
        + float(w.get("causal_weight", 20.0)) * (row.get("causal_phrase_count") or 0)
        + float(w.get("english_ratio_weight", 100.0)) * float(row.get("english_word_ratio") or 0.0)
    )


def _apply_bronze_selection(
    bronze_rows: list[dict],
    n_gold: int,
    n_silver: int,
    bs_cfg: dict,
) -> tuple[list[dict], dict]:
    """Filter bronze rows by criteria, then cap so bronze cannot dominate gold+silver.

    Returns (kept_rows, stats_dict).
    """
    if not bs_cfg.get("enabled", True):
        return [], {"input": len(bronze_rows), "after_criteria": 0, "after_cap": 0, "reason": "disabled"}

    crit = bs_cfg.get("criteria", {})
    min_wrong = int(crit.get("min_wrong_explanation_chars", 0))
    min_tech = int(crit.get("min_technique_mentions", 0))
    min_q = float(crit.get("min_quality_score", 0.0))
    sort_w = bs_cfg.get("sort_formula", {})

    after_criteria: list[dict] = []
    for r in bronze_rows:
        if (r.get("wrong_explanation_chars") or 0) < min_wrong:
            continue
        if (r.get("technique_mentions") or 0) < min_tech:
            continue
        # Light synthetic quality_score on the fly (qualify doesn't compute one)
        q = _bronze_quality(r, sort_w) / 1000.0  # rough normalisation
        if q < min_q:
            continue
        r["_bronze_quality"] = _bronze_quality(r, sort_w)
        after_criteria.append(r)

    cap_policy = bs_cfg.get("cap_policy", "max_of_gold_silver")
    if cap_policy == "max_of_gold_silver":
        cap = n_gold + n_silver
    elif cap_policy == "fixed":
        cap = int(bs_cfg.get("cap_value", 0))
    else:  # unlimited
        cap = len(after_criteria)

    if len(after_criteria) > cap:
        after_criteria.sort(key=lambda r: r["_bronze_quality"], reverse=True)
        kept = after_criteria[:cap]
    else:
        kept = after_criteria

    return kept, {
        "input": len(bronze_rows),
        "after_criteria": len(after_criteria),
        "cap": cap,
        "after_cap": len(kept),
    }


def run_ingest(
    qualification_jsonl: str | None = None,
    config_path: str | None = None,
    tiers: tuple[str, ...] = ("gold", "silver", "bronze"),
    dry_run: bool = False,
    clean: bool = True,
) -> None:
    """Copy qualified SGFs into data/sources/ with tier-prefixed names.

    Default tiers are ("gold", "silver", "bronze"). Gold and silver are kept
    in full. Bronze is pre-filtered by curation_config.json -> bronze_selection
    (criteria + quality-ranked cap so bronze <= gold+silver). Set the tier list
    explicitly to override.
    """
    set_context(stage="ingest")
    cfg = load_config(config_path)
    if qualification_jsonl:
        qual_path = Path(qualification_jsonl)
    else:
        latest = resolve_latest("qualification", "jsonl")
        qual_path = latest if latest else QUALIFICATION_JSONL

    if not qual_path.exists():
        logger.error("Qualification file not found: %s. Run 'yen-sei qualify' first.", qual_path)
        return

    pattern = cfg.filename_pattern
    logger.info("Reading qualification: %s", qual_path)
    logger.info("Filename pattern: %s", pattern)
    logger.info("Tiers to ingest: %s", ", ".join(tiers))

    selected_by_tier: dict[str, list[dict]] = {"gold": [], "silver": [], "bronze": []}
    with qual_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            t = row.get("tier")
            if t in tiers and t in selected_by_tier:
                selected_by_tier[t].append(row)

    n_gold = len(selected_by_tier["gold"])
    n_silver = len(selected_by_tier["silver"])
    n_bronze_raw = len(selected_by_tier["bronze"])

    # Apply bronze selection (criteria + cap) so bronze cannot dominate.
    if "bronze" in tiers:
        bs_cfg = (cfg.raw or {}).get("bronze_selection", {})
        bronze_kept, bs_stats = _apply_bronze_selection(
            selected_by_tier["bronze"], n_gold, n_silver, bs_cfg,
        )
        selected_by_tier["bronze"] = bronze_kept
        logger.info(
            "Bronze selection: %d input -> %d after criteria -> %d kept (cap=%s)",
            bs_stats["input"], bs_stats["after_criteria"],
            bs_stats["after_cap"], bs_stats.get("cap", "?"),
        )

    selected: list[dict] = (
        selected_by_tier["gold"] + selected_by_tier["silver"] + selected_by_tier["bronze"]
    )
    logger.info(
        "Final ingest mix: gold=%d silver=%d bronze=%d (bronze raw was %d)",
        len(selected_by_tier["gold"]), len(selected_by_tier["silver"]),
        len(selected_by_tier["bronze"]), n_bronze_raw,
    )

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
            # `file_path` is POSIX-relative-to-repo-root (or absolute legacy).
            src_path = from_posix_rel(row["file_path"])
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
                "source_path": to_posix_rel(src_path),
                "curation_run_id": row.get("curation_run_id", ""),
                "english_word_ratio": row.get("english_word_ratio"),
                "correct_explanation_chars": row.get("correct_explanation_chars"),
                "wrong_explanation_chars": row.get("wrong_explanation_chars"),
                "explanation_node_count": row.get("explanation_node_count"),
                "techniques_found": row.get("techniques_found", []),
                "yq_ac": row.get("yq_ac", 0),
                "ai_signature_hits": row.get("ai_signature_hits", 0),
            }) + "\n")

    total = sum(copied.values())
    logger.info("Ingest complete: %d copied, %d missing, %d collisions",
                total, skipped_missing, skipped_collision)
    print(f"\nCopied {total:,} files into {SOURCES_DIR}:")
    for tier in ("gold", "silver", "bronze"):
        if copied.get(tier):
            print(f"  {tier}: {copied[tier]:,}")
    print(f"\nManifest: {MANIFEST_PATH}")
