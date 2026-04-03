# SGF Directory Comparison Tool

**Last Updated:** 2026-03-25

Compare two directories of SGF tsumego puzzle files, identify duplicates by board position, and produce a granular match-level report.

> **See also:**
>
> - [Architecture: SGF Directory Comparison](../../docs/architecture/tools/sgf-directory-comparison.md) — Full design decisions (D1–D18)
> - [Tool Development Standards](../../docs/how-to/backend/tool-development-standards.md) — Project scaffolding conventions

---

## Quick Start

```bash
# From the repository root
python tools/puzzle-manager-scripts/compare_dirs.py \
  --source "external-sources/Xuan Xuan Qi Jing" \
  --target "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - XUAN XUAN QI JING"
```

Output is written to `tools/puzzle-manager-scripts/output/compare-{YYYYMMDD-HHMMSS}/`.

---

## CLI Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--source PATH` | Yes | — | Path to the source directory containing SGF files. Relative to project root or absolute. |
| `--target PATH` | Yes | — | Path to the target directory containing SGF files. Relative to project root or absolute. |
| `--resume` | No | Off | Resume from the last checkpoint. Skips files already compared. |
| `--dry-run` | No | Off | Parse and hash all files, but do not write output files. Prints summary to console. |
| `--help` | No | — | Show help message and exit. |

### Examples

```bash
# Basic comparison
python tools/puzzle-manager-scripts/compare_dirs.py \
  --source "external-sources/Xuan Xuan Qi Jing" \
  --target "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - XUAN XUAN QI JING"

# Resume an interrupted run
python tools/puzzle-manager-scripts/compare_dirs.py \
  --source "external-sources/Xuan Xuan Qi Jing" \
  --target "external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - XUAN XUAN QI JING" \
  --resume

# Dry run — parse and hash only, no output files
python tools/puzzle-manager-scripts/compare_dirs.py \
  --source "external-sources/sanderland/sgf" \
  --target "yengo-puzzle-collections/sgf/0001" \
  --dry-run
```

---

## Match Levels (0–7)

Higher number = closer match. Every output record has a numeric `match_level` field.

| Level | Name | What It Means |
|:-----:|------|--------------|
| **7** | Byte-Identical | Raw SGF file bytes are exactly the same. |
| **6** | Tree-Identical | Same board position, same solution tree moves. Only headers/comments/whitespace differ. |
| **5** | Superset | Same position, same correct line. Target has all source paths plus extra variations (enriched version). |
| **4** | Divergent | Same position, same correct line. Trees have incompatible variation branches (neither is a subset). |
| **3** | Solution-Differs | Same position, but first correct move differs. Data error or miai situation. |
| **2** | Position-Only | Position hash matches, but PL (player to move) is absent or conflicts. Lower confidence. |
| **1** | Filename-Mismatch | Same filename exists in both dirs, but position hash differs. Possible renumbering or corruption. |
| **0** | Unmatched | File exists in only one directory. No match found. |

### How to Read Match Levels

- **Level 7:** Files are identical copies. No further investigation needed.
- **Level 6:** Same puzzle, different formatting. Safe to treat as duplicates.
- **Level 5:** Target is an enriched version of source. Safe to pick the richer file.
- **Level 4:** Same puzzle but solutions disagree on wrong-move branches. Needs human review.
- **Level 3:** Red flag — sources disagree on the correct answer. Investigate.
- **Level 2:** Position matches but player-to-move can't be confirmed. Use with caution.
- **Level 1:** Filenames correlate but content is completely different. Investigate renumbering.
- **Level 0:** Orphaned file. No match by content or filename.

---

## Output Files

Each run creates a timestamped directory:

```text
tools/puzzle-manager-scripts/output/
  compare-20260325-143022/
    comparison.jsonl      ← One record per source file
    summary.md            ← Aggregate statistics
    .checkpoint.json      ← Resume state (deleted on completion)
    run.log               ← Structured event log
```

### JSONL Record Format

Each line in `comparison.jsonl` is a JSON object:

```json
{
  "source_file": "prob0047.sgf",
  "target_file": "prob0047.sgf",
  "match_level": 7,
  "position_hash": "a1b2c3d4e5f67890",
  "full_hash": "b2c3d4e5f6789012",
  "board_size": 19,
  "player_to_move_source": "B",
  "player_to_move_target": "B",
  "pl_status": "confirmed",
  "first_move_match": true,
  "correct_line_match": true,
  "source_nodes": 7,
  "target_nodes": 7,
  "source_depth": 5,
  "target_depth": 5,
  "comments_differ": false,
  "markers_differ": false,
  "detail": "Byte-identical"
}
```

#### PL Status Values

| Value | Meaning |
|-------|---------|
| `confirmed` | Both files have PL and they match |
| `conflict` | Both files have PL but values differ (genuinely different puzzle) |
| `absent_source` | Source file lacks PL property |
| `absent_target` | Target file lacks PL property |
| `absent_both` | Neither file has PL property |

### Summary Report

`summary.md` contains:

- Run metadata (timestamp, source/target paths, file counts)
- Match distribution table (count and percentage per level)
- Statistics (parse errors, PL-absent files, PL-conflict matches)
- Notable findings (Level 3 and below listed with details)

---

## Hashing

The tool computes two hashes per file:

| Hash | Includes PL? | Formula | Purpose |
|------|-------------|---------|---------|
| **Position hash** | No | `SHA256("SZ{n}:B[sorted]:W[sorted]")[:16]` | Always computed. Primary matching key. |
| **Full hash** | Yes | `SHA256("SZ{n}:B[sorted]:W[sorted]:PL[X]")[:16]` | Only when PL is present. Higher confidence. |

Stone coordinates are sorted alphabetically in SGF format (e.g., `aa,ab,cd`). This ensures the hash is independent of how the SGF file encodes the stones.

---

## Checkpointing & Resume

For large collections (1000+ files), the tool checkpoints progress every 50 files. If a run is interrupted:

1. The current state is saved to `.checkpoint.json`.
2. Re-run the same command with `--resume`.
3. Already-compared files are skipped; processing continues from where it stopped.
4. On successful completion, the checkpoint file is deleted.

If the checkpoint file is corrupted, it is backed up to `.checkpoint.json.bak` and a fresh run starts.

---

## Error Handling

| Error | What Happens |
|-------|-------------|
| SGF parse failure | File is skipped, logged as ERROR, emitted as Level 0 with `"error"` field |
| Empty SGF file | Same as parse failure |
| No stones (AB/AW missing) | Skipped — cannot compute position hash |
| Permission denied | File is skipped, logged as ERROR |
| Output directory creation fails | **Fatal exit** |
| Corrupt checkpoint | Backed up, fresh start |

The tool never stops processing because of one bad file. All errors appear in both `run.log` and the JSONL output.

---

## Architecture

```text
tools/core/sgf_compare.py              ← Library (hashing, tree comparison, match levels)
    ↑ imports
tools/puzzle-manager-scripts/
  compare_dirs.py                      ← CLI script (dirs, output, checkpointing)
  output/compare-{timestamp}/          ← Run output
```

- **`sgf_compare.py`** contains pure functions: `position_hash()`, `full_hash()`, `extract_move_paths()`, `classify_match()`, plus the `MatchLevel` enum and `CompareResult` dataclass.
- **`compare_dirs.py`** handles CLI arguments, directory scanning, the hash-map join algorithm, JSONL/Markdown output, and checkpointing.
- The library has no I/O. The CLI script handles all I/O.

---

## Dependencies

**Zero new dependencies.** Uses only:

- Python stdlib: `hashlib`, `pathlib`, `json`, `argparse`, `datetime`, `dataclasses`
- Existing `tools.core`: `sgf_parser`, `sgf_analysis`, `sgf_types`, `checkpoint`, `logging`, `paths`, `atomic_write`
