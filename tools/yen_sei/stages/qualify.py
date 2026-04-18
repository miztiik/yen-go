"""qualify stage: scan ALL of external-sources/, score each puzzle, write a
qualification report. NO files are copied or modified.

Output:
- data/qualification_v2.jsonl : one JSON line per scanned SGF with all signals
- data/qualification_v2_report.txt : human-readable per-source tier breakdown
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tools.yen_sei.config import DATA_DIR, EXT_ROOT
from tools.yen_sei.governance.config_loader import CurationConfig, load_config
from tools.yen_sei.governance.teaching_signal import extract_signals, signals_to_dict
from tools.yen_sei.governance.tier_classifier import classify
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)

QUALIFICATION_JSONL = DATA_DIR / "qualification_v2.jsonl"
QUALIFICATION_REPORT = DATA_DIR / "qualification_v2_report.txt"


# Worker globals (one per process, populated by _init_worker)
_WORKER_CFG: CurationConfig | None = None


def _init_worker(config_path: str | None) -> None:
    global _WORKER_CFG
    _WORKER_CFG = load_config(config_path)


def _process_file(args: tuple[str, str]) -> dict:
    """Worker: parse one SGF, return JSONL row dict."""
    path_str, source = args
    assert _WORKER_CFG is not None
    signals = extract_signals(Path(path_str), source, _WORKER_CFG)
    tier = classify(signals, _WORKER_CFG)
    return {
        "tier": tier,
        "curation_run_id": _WORKER_CFG.curation_run_id,
        **signals_to_dict(signals),
    }


def run_qualify(
    config_path: str | None = None,
    output_jsonl: str | None = None,
    output_report: str | None = None,
    limit_per_source: int | None = None,
    workers: int | None = None,
    scan_path: str | None = None,
    source_name: str | None = None,
    upsert: bool = False,
) -> None:
    """Scan every SGF in external-sources/, score it, write a tier label.

    Args:
        config_path: Path to curation_config.json (default: yen_sei/curation_config.json).
        output_jsonl: Override JSONL output path.
        output_report: Override report output path.
        limit_per_source: Cap files per source (for quick smoke tests).
        workers: Number of process workers (default: os.cpu_count()).
        scan_path: Scan only this directory tree (default: all of external-sources/).
            Useful for evaluating a single new author/source without re-scanning 213K files.
        source_name: Override the auto-detected source name (only meaningful with scan_path).
            By default, source = first path segment under external-sources/.
        upsert: When True with scan_path, MERGE results into the existing qualification jsonl
            by replacing rows with matching file_path. When False AND scan_path is set, results
            are written to a derived preview file (qualification_preview_<leaf>.jsonl) so the
            main baseline is never overwritten by a single-folder run.
    """
    set_context(stage="qualify")
    cfg = load_config(config_path)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Output path resolution rules (ordered):
    # 1. Explicit --output-jsonl wins.
    # 2. Full-corpus scan or --upsert => main qualification_v2.jsonl.
    # 3. Single-path preview (--path without --upsert) => derived preview path
    #    named after the leaf folder, so we NEVER overwrite the main baseline.
    if output_jsonl:
        out_jsonl = Path(output_jsonl)
        out_report = Path(output_report) if output_report else out_jsonl.with_name(out_jsonl.stem + "_report.txt")
    elif scan_path and not upsert:
        leaf = Path(scan_path).resolve().name
        # Sanitize: keep alnum, dash, underscore; replace others with "_"
        slug = "".join(c if (c.isalnum() or c in "-_") else "_" for c in leaf).strip("_") or "preview"
        out_jsonl = DATA_DIR / f"qualification_preview_{slug}.jsonl"
        out_report = DATA_DIR / f"qualification_preview_{slug}_report.txt"
    else:
        out_jsonl = QUALIFICATION_JSONL
        out_report = Path(output_report) if output_report else QUALIFICATION_REPORT

    nworkers = workers or max(1, (os.cpu_count() or 4) - 1)
    logger.info("Loaded config: run_id=%s, schema_v=%d", cfg.curation_run_id, cfg.schema_version)

    # Decide scan root + source-resolution strategy
    if scan_path:
        scan_root = Path(scan_path).resolve()
        if not scan_root.exists():
            raise SystemExit(f"--path does not exist: {scan_root}")
        if not scan_root.is_dir():
            raise SystemExit(f"--path is not a directory: {scan_root}")
        logger.info("Scanning subtree %s with %d workers (single-path mode) ...", scan_root, nworkers)
    else:
        scan_root = EXT_ROOT
        logger.info("Scanning %s with %d workers ...", EXT_ROOT, nworkers)

    # Build full work list with file-size pre-check; oversize files are flagged
    # as gate failures without ever being parsed (avoids stuck workers on game records).
    MAX_FILE_BYTES = 256 * 1024  # 256 KB; real tsumego are < 50 KB
    work: list[tuple[str, str]] = []
    oversize_rows: list[dict] = []
    per_source_total: Counter = Counter()

    def _resolve_source(file_path: Path) -> str:
        """Source = first path segment under external-sources/, or override."""
        if source_name:
            return source_name
        try:
            rel = file_path.resolve().relative_to(EXT_ROOT.resolve())
            return rel.parts[0] if rel.parts else "unknown"
        except ValueError:
            # Path is outside external-sources/. Fall back to immediate parent name.
            return file_path.parent.name

    if scan_path:
        # Single-path mode: walk the supplied directory directly (don't iterate EXT_ROOT children).
        files = sorted(scan_root.rglob("*.sgf"))
        if limit_per_source:
            files = files[:limit_per_source]
        for f in files:
            source = _resolve_source(f)
            try:
                if f.stat().st_size > MAX_FILE_BYTES:
                    oversize_rows.append({
                        "tier": "drop",
                        "curation_run_id": cfg.curation_run_id,
                        "source": source,
                        "file_path": str(f).replace("\\", "/"),
                        "original_stem": f.stem,
                        "gate_failures": ["file_too_large"],
                        "is_english": False,
                    })
                    continue
            except OSError:
                continue
            work.append((str(f), source))
            per_source_total[source] += 1
    else:
        # Full-corpus mode: walk one level under EXT_ROOT, source = directory name.
        for source_dir in sorted(EXT_ROOT.iterdir()):
            if not source_dir.is_dir():
                continue
            source = source_dir.name
            files = sorted(source_dir.rglob("*.sgf"))
            if limit_per_source:
                files = files[:limit_per_source]
            for f in files:
                try:
                    if f.stat().st_size > MAX_FILE_BYTES:
                        oversize_rows.append({
                            "tier": "drop",
                            "curation_run_id": cfg.curation_run_id,
                            "source": source,
                            "file_path": str(f).replace("\\", "/"),
                            "original_stem": f.stem,
                            "gate_failures": ["file_too_large"],
                            "is_english": False,
                        })
                        continue
                except OSError:
                    continue
                work.append((str(f), source))
            per_source_total[source] = len(files)
    total_total = len(work) + len(oversize_rows)
    logger.info("Queued %d files (%d skipped as oversize) across %d sources",
                total_total, len(oversize_rows), len(per_source_total))

    tier_counts: dict[str, Counter] = defaultdict(Counter)
    gate_failures: Counter = Counter()
    total_done = 0
    start = time.monotonic()
    new_rows_in_memory: list[dict] = []  # collected only when upsert=True

    # Decide the streaming-write target:
    # - normal mode: write directly to out_jsonl (overwrites existing)
    # - upsert mode: collect rows in memory then merge with existing jsonl at end
    write_to_disk = not upsert
    out_handle = out_jsonl.open("w", encoding="utf-8") if write_to_disk else None

    try:
        # Write oversize-skipped rows first
        for row in oversize_rows:
            tier_counts[row["source"]][row["tier"]] += 1
            for f in row["gate_failures"]:
                gate_failures[f] += 1
            if out_handle is not None:
                out_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                new_rows_in_memory.append(row)
            total_done += 1

        # Stream via pool.map: results yielded in order as workers complete.
        # Single slow worker doesn't block others (they keep grabbing work)
        # but in-order yield means a stuck file delays following writes.
        # chunksize trades off IPC overhead vs latency tolerance.
        with ProcessPoolExecutor(
            max_workers=nworkers,
            initializer=_init_worker,
            initargs=(config_path,),
        ) as pool:
            for row in pool.map(_process_file, work, chunksize=50):
                tier_counts[row["source"]][row["tier"]] += 1
                for f in row.get("gate_failures", []):
                    gate_failures[f] += 1
                if out_handle is not None:
                    out_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                else:
                    new_rows_in_memory.append(row)
                total_done += 1
                if total_done % 5000 == 0:
                    elapsed = time.monotonic() - start
                    rate = total_done / elapsed if elapsed else 0
                    eta = (total_total - total_done) / rate if rate else 0
                    logger.info("  progress: %d/%d (%.0f files/sec, ETA %.0fs)",
                                total_done, total_total, rate, eta)
                    if out_handle is not None:
                        out_handle.flush()
    finally:
        if out_handle is not None:
            out_handle.close()

    # Upsert: merge new rows into existing jsonl by file_path
    if upsert:
        new_by_path = {r["file_path"]: r for r in new_rows_in_memory}
        replaced = 0
        kept = 0
        appended = 0
        if out_jsonl.exists():
            tmp = out_jsonl.with_suffix(".jsonl.tmp")
            with out_jsonl.open(encoding="utf-8") as fin, tmp.open("w", encoding="utf-8") as fout:
                for line in fin:
                    try:
                        existing = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    fp = existing.get("file_path")
                    if fp in new_by_path:
                        fout.write(json.dumps(new_by_path.pop(fp), ensure_ascii=False) + "\n")
                        replaced += 1
                    else:
                        fout.write(line if line.endswith("\n") else line + "\n")
                        kept += 1
                # Append any new file_paths not previously present
                for r in new_by_path.values():
                    fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                    appended += 1
            tmp.replace(out_jsonl)
        else:
            with out_jsonl.open("w", encoding="utf-8") as fout:
                for r in new_rows_in_memory:
                    fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                    appended += 1
        logger.info("Upsert: %d replaced, %d new appended, %d existing rows preserved", replaced, appended, kept)

    elapsed = time.monotonic() - start
    logger.info("Done. Scanned %d files in %.1fs (%.0f files/sec)",
                total_done, elapsed, total_done / max(elapsed, 0.001))

    _write_report(out_report, cfg, tier_counts, gate_failures, total_done, elapsed)
    logger.info("Wrote: %s", out_jsonl)
    logger.info("Wrote: %s", out_report)


def _write_report(
    path: Path,
    cfg: CurationConfig,
    tier_counts: dict[str, Counter],
    gate_failures: Counter,
    total: int,
    elapsed: float,
) -> None:
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("YEN-SEI v2 QUALIFICATION REPORT")
    lines.append(f"Run ID: {cfg.curation_run_id}    Schema: v{cfg.schema_version}")
    lines.append(f"Total scanned: {total:,} files in {elapsed:.1f}s")
    lines.append("=" * 100)

    # Aggregate
    overall = Counter()
    for src_counts in tier_counts.values():
        overall.update(src_counts)
    lines.append("\n--- OVERALL TIER DISTRIBUTION ---")
    for tier in ("gold", "silver", "bronze", "drop"):
        n = overall[tier]
        pct = 100.0 * n / total if total else 0.0
        lines.append(f"  {tier:>8}: {n:>8,}  ({pct:5.1f}%)")

    lines.append("\n--- PER-SOURCE TIER BREAKDOWN ---")
    lines.append(f"{'source':<28}  {'total':>8}  {'gold':>7}  {'silver':>7}  {'bronze':>7}  {'drop':>7}  cap")
    lines.append("-" * 100)
    for source in sorted(tier_counts.keys()):
        c = tier_counts[source]
        total_src = sum(c.values())
        cap = cfg.source_overrides.get(source)
        cap_str = cap.tier_cap if cap else "-"
        lines.append(
            f"{source:<28}  {total_src:>8,}  {c['gold']:>7,}  {c['silver']:>7,}  "
            f"{c['bronze']:>7,}  {c['drop']:>7,}  {cap_str}"
        )

    lines.append("\n--- HARD-GATE FAILURE BREAKDOWN ---")
    for failure, n in gate_failures.most_common():
        lines.append(f"  {failure:<35}  {n:>8,}")

    lines.append("\n--- CONFIG SNAPSHOT ---")
    lines.append(f"  language method: {cfg.language.method}")
    lines.append(f"  min_ascii_letter_ratio: {cfg.language.min_ascii_letter_ratio}")
    lines.append(f"  min_stopword_per_100: {cfg.language.min_stopword_hits_per_100_chars}")
    lines.append(f"  hard_gates: stones={cfg.hard_gates.min_stones}-{cfg.hard_gates.max_stones}, "
                 f"sizes={sorted(cfg.hard_gates.valid_board_sizes)}, max_moves={cfg.hard_gates.max_total_moves}")
    for r in cfg.tier_rules:
        lines.append(f"  tier {r.name}: cor>={r.min_correct_explanation_chars} wrong>={r.min_wrong_explanation_chars} "
                     f"nodes>={r.min_explanation_node_count} causal>={r.min_causal_phrases} "
                     f"en>={r.min_english_word_ratio} tech>={r.min_technique_mentions}")

    lines.append("\nNext steps:")
    lines.append("  1. Review tier counts above. Tighten/loosen thresholds in curation_config.json.")
    lines.append("  2. Sample puzzles per tier:  python -m tools.yen_sei sample --tier gold --n 10")
    lines.append("  3. When happy, ingest:       python -m tools.yen_sei ingest --tiers gold,silver")

    path.write_text("\n".join(lines), encoding="utf-8")


def sample_tier(
    tier: str,
    source: str | None = None,
    n: int = 10,
    jsonl_path: str | None = None,
) -> None:
    """Print N random samples from a tier. Reads qualification_v2.jsonl."""
    import random
    src_path = Path(jsonl_path) if jsonl_path else QUALIFICATION_JSONL
    if not src_path.exists():
        print(f"Run qualify first: {src_path} not found.")
        return

    matches = []
    with src_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["tier"] != tier:
                continue
            if source and row["source"] != source:
                continue
            matches.append(row)

    if not matches:
        print(f"No matches for tier={tier} source={source}")
        return

    random.seed(42)
    chosen = random.sample(matches, min(n, len(matches)))
    print(f"=== {len(chosen)} of {len(matches)} {tier} examples"
          + (f" from {source}" if source else "") + " ===\n")
    for row in chosen:
        print(f"--- [{row['source']}] {row['file_path']} ---")
        print(f"    correct={row['correct_explanation_chars']} wrong={row['wrong_explanation_chars']} "
              f"nodes={row['explanation_node_count']} causal={row['causal_phrase_count']} "
              f"tech={row['technique_mentions']} ({','.join(row['techniques_found'][:3])}) "
              f"en_ratio={row['english_word_ratio']}")
        # Show first 200 chars of the actual SGF root comment for context
        try:
            sgf_text = Path(row["file_path"]).read_text(encoding="utf-8", errors="replace")
            import re as _re
            m = _re.search(r"C\[((?:[^\\\]]|\\.)*?)\]", sgf_text)
            if m:
                preview = m.group(1).replace("\\]", "]")[:200].replace("\n", " ")
                print(f"    PREVIEW: {preview}")
        except Exception:
            pass
        print()
