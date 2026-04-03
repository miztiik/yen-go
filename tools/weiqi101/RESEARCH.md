# 101weiqi Tool — Research & Architecture Proposal

**Date**: 2026-03-14
**Status**: Research complete, awaiting approval
**Reference tools**: `tools/ogs/`, `tools/go_problems/`

---

## 1. Executive Summary

Rebuild the existing `tools/101weiqi/` prototype into a proper modular tool following
the established pattern from `tools/ogs/` (reference implementation per tool-development-standards).

### Current State (Prototype)
- **Single 1,260-line monolith** (`101weiqi_ingestor.py`)
- SGF built via manual string concatenation (no `SgfBuilder`)
- Level/type info dumped in root `C[]` comment, NOT as `YG[]`/`YT[]` properties
- Outputs 3 separate files per puzzle: `.json`, `.sgf`, `_meta.json`
- Only supports daily puzzles (每日八题) source
- No batch directory organization, no `sgf-index.txt`, no proper checkpointing

### Target State (New Tool)
- **Modular tool** matching OGS architecture (12+ focused modules)
- SGF-only output with embedded `YG[]`, `YT[]`, `YV[]`, `YL[]` properties via `tools.core.sgf_builder`
- Batch directories (`sgf/batch-001/`, etc.) with dedup index
- Multiple source modes: daily, puzzle-by-id, book
- Full `tools.core` integration: logging, checkpoint, batching, validation, rate limiting
- Chinese → YenGo level/tag mapping

---

## 2. 101weiqi.com Data Model

### 2.1 URL Patterns (Confirmed)

| Source | URL Pattern | Example | Description |
|--------|-------------|---------|-------------|
| **daily** | `/qday/{year}/{month}/{day}/{num}/` | `/qday/2026/1/23/1/` | Daily 8 puzzles (每日八题) |
| **puzzle-by-id** | `/q/{problem_id}/` | `/q/78000/` | Individual puzzle by numeric ID |
| **book** | `/book{book_id}/{chapter_id}/?page={page}` | `/book/27421/140516/` | Book chapter (lists puzzle IDs) |
| **special** | `/{named_path}/{chapter_id}/` | `/fayang/587/` | Named special collections |

### 2.2 Puzzle JSON (`qqdata`) Structure

```json
{
  "id": 78000,
  "publicid": 78000,
  "levelname": "13K+",     // Chinese kyu/dan format
  "qtypename": "死活题",    // Puzzle category in Chinese
  "qtype": 1,              // Numeric type ID
  "boardsize": 19,
  "firsthand": 1,          // 1=black, 2=white
  "prepos": [
    ["pd", "pe", ...],     // Black setup stones (SGF coords)
    ["oc", "oe", ...]      // White setup stones
  ],
  "andata": {              // Hierarchical solution tree
    "0": {
      "pt": "pd",          // Move coordinate
      "o": 1,              // Correct flag
      "f": 0,              // Failure flag
      "subs": [1, 2],      // Child node IDs
      "c": "good move"     // Optional comment
    }
  },
  "taskresult": {
    "ok_total": 11112,     // Community correct answers
    "fail_total": 5345     // Community wrong answers
  },
  "vote": 5.0              // Community rating
}
```

### 2.3 Alternate Data Fields (from 101books analysis)

Some puzzle sources use additional/alternate fields:
- `blackfirst` (boolean) instead of `firsthand` (int)
- `c` field with base64+XOR encoded position data (keys `"101222"` / `"101333"`)
- `xv` field controlling board transformation (`xv % 3 != 0` → flip)
- `answers` array with `ty=1` (correct) and `ty=3` (failure) — flat structure vs hierarchical `andata`
- `psm.prepos` as fallback when `prepos` is empty/missing

---

## 3. Mapping Tables

### 3.1 Level Mapping: `levelname` → YenGo Level Slug (Calibrated)

101weiqi uses a Chinese rating system where kyu ranks are approximately **10 stones inflated** compared to international standards. A puzzle labeled "15K" on 101weiqi contains beginner-level captures, not intermediate content.

**Calibration**: `_local_levels_mapping.json` applies `kyu_offset: 10` before bracket lookup. Dan ranks are not calibrated (`dan_offset: 0`).

| 101weiqi `levelname` | Raw Rank | Calibrated Rank | YenGo Slug | Level ID |
|----------------------|----------|-----------------|------------|----------|
| `20K+` – `16K` | 20k–16k | 30k–26k | `novice` | 110 |
| `15K+` – `11K` | 15k–11k | 25k–21k | `beginner` | 120 |
| `10K+` – `6K` | 10k–6k | 20k–16k | `elementary` | 130 |
| `5K+` – `1K` | 5k–1k | 15k–11k | `intermediate` | 140 |
| *(n/a: no 101weiqi content in this range)* | — | 10k–6k | `upper-intermediate` | 150 |
| *(n/a)* | — | 5k–1k | `advanced` | 160 |
| `1D` – `3D` | 1d–3d | 1d–3d | `low-dan` | 210 |
| `4D` – `6D` | 4d–6d | 4d–6d | `high-dan` | 220 |
| `7D+` – `9D` | 7d–9d | 7d–9d | `expert` | 230 |
| `1P` – `9P` | 1p–9p | 1p–9p | `expert` | 230 |
| *(blank/missing)* | — | — | *(fallback to complexity)* | — |

**Implementation**: Strip `+` suffix → parse rank → apply calibration offset → bracket lookup.

### 3.2 Tag Mapping: `qtypename` → YenGo Tag Slug

| `qtypename` | English | YenGo Tag | Tag ID | Notes |
|-------------|---------|-----------|--------|-------|
| 死活题 | Life & Death | `life-and-death` | 10 | Direct match |
| 手筋 | Tesuji | `tesuji` | 52 | Direct match |
| 布局 | Opening/Fuseki | `fuseki` | 82 | Direct match |
| 定式 | Joseki | `joseki` | 80 | Direct match |
| 官子 | Endgame | `endgame` | 78 | Direct match |
| 对杀 | Capture Race | `capture-race` | 60 | Semantic match |
| 综合 | Mixed/Comprehensive | *(null)* | — | Too generic; pipeline tagger detects |
| 中盘 | Middle Game | *(null)* | — | Broad category; pipeline tagger refines |

---

## 4. Architecture Proposal

### 4.1 Module Structure (following OGS pattern)

```
tools/101weiqi/
├── __init__.py                 # Package metadata + version
├── __main__.py                 # CLI entry point (argparse)
├── config.py                   # Constants: URLs, delays, batch size, paths
├── client.py                   # HTTP client (GET with retry, backoff, jitter)
├── models.py                   # Dataclasses for qqdata JSON structure
├── extractor.py                # HTML → qqdata JSON extraction (regex + brace matching)
├── converter.py                # qqdata → SGF conversion (prepos, andata → tree, +YM)
├── storage.py                  # SGF file saving (batch dirs, index, enrichment)
├── orchestrator.py             # Main download loop (sources, pagination, resume)
├── checkpoint.py               # Resume state (extends tools.core.checkpoint)
├── levels.py                   # Level mapping: levelname → YG[] slug (with calibration)
├── tags.py                     # Tag mapping: qtypename → YT[] slug
├── discover.py                 # Book/tag/category discovery + chapter scraping
├── validator.py                # Puzzle validation (board size, stones, solution)
├── logging_config.py           # Structured logging setup
├── index.py                    # sgf-index.txt management (thin wrapper)
├── batching.py                 # Batch directory management (thin wrapper)
├── _local_levels_mapping.json  # Calibration offsets (kyu_offset=10, dan_offset=0)
├── _local_collections_mapping.json # Chinese category → YenGo collection slug
├── _local_intent_mapping.py    # Chinese category → root C[] intent text
├── README.md                   # Tool documentation
├── RESEARCH.md                 # This document
├── tests/                      # Test suite
│   ├── test_extractor.py
│   ├── test_converter.py
│   ├── test_storage.py
│   ├── test_levels.py
│   ├── test_tags.py
│   └── test_validator.py
└── _archive/                   # Archived prototype (original monolith)
    └── 101weiqi_ingestor.py
```

### 4.2 Source Modes

#### Mode 1: `daily` (Priority: High — existing, refine)
- URL: `/qday/{year}/{month}/{day}/{num}/`
- Puzzle count: Fixed 8 per day
- Iteration: By date range + puzzle number
- Volume: ~2,920 puzzles/year
- Risk: Low
- CLI: `python -m tools.101weiqi daily --start-date 2026-01-01 --end-date 2026-03-14`

#### Mode 2: `puzzle` (Priority: Medium — new, high volume)
- URL: `/q/{problem_id}/`
- Puzzle count: Tens of thousands (IDs up to 100k+)
- Iteration: By ID range with probe for valid IDs
- Volume: Very high (entire puzzle database)
- Risk: Medium (rate limiting, blocking)
- CLI: `python -m tools.101weiqi puzzle --start-id 1 --end-id 1000`
- CLI: `python -m tools.101weiqi puzzle --ids 78000,78001,78002`

#### Mode 3: `book` (Priority: Low — copyright-sensitive)
- URL: `/book{book_id}/{chapter_id}/`
- Two-phase: (1) scrape chapter page for puzzle IDs, (2) fetch individual puzzles
- Volume: ~13,000 across 60+ books
- Risk: High (copyright for modern books; public-domain classics are safe)
- CLI: `python -m tools.101weiqi book --book-id 27421`
- Deferred to Phase 2 (requires copyright assessment per collection)

### 4.3 Data Flow

```
HTML page
  ↓ (HTTP GET with retry + backoff + jitter)
  ↓
Raw HTML
  ↓ (extractor.py: regex find `var qqdata = {...}`)
  ↓
qqdata JSON dict
  ↓ (models.py: parse to PuzzleData dataclass)
  ↓
PuzzleData
  ↓ (validator.py: board size, stones, solution depth)
  ↓
Validated PuzzleData
  ↓ (converter.py: prepos → stones, andata → solution tree)
  ↓ (levels.py: levelname → YG[slug])
  ↓ (tags.py: qtypename → YT[tag])
  ↓ (storage.py: assemble SGF with YenGo properties)
  ↓
SGF file → sgf/batch-NNN/{puzzle_id}.sgf
         → sgf-index.txt (append)
         → .checkpoint.json (update)
```

### 4.4 SGF Output Format

```sgf
(;FF[4]GM[1]CA[UTF-8]
SZ[19]
YG[beginner]
YT[life-and-death]
YM[{"t":"a1b2c3d4e5f67890","f":"78000.sgf"}]
PL[B]
AB[pd][pe][qd][qe]
AW[oc][oe][rc][re]
;B[pd]C[Correct]
(;W[pe]C[Wrong])
(;W[qd];B[re]C[Correct])
)
```

**Properties embedded:**
| Property | Source | Example |
|----------|--------|---------|
| `FF[4]GM[1]CA[UTF-8]` | Mandatory | Always |
| `SZ[N]` | `boardsize` | `SZ[19]` |
| `PL[B\|W]` | `firsthand` | `PL[B]` |
| `AB[]/AW[]` | `prepos` | Setup stones |
| `YG[slug]` | `levelname` mapped + calibrated | `YG[beginner]` |
| `YT[tags]` | `qtypename` mapped | `YT[life-and-death]` |
| `YL[entries]` | Collection membership (v14: supports `:CHAPTER/POSITION`) | `YL[life-and-death]` |
| `YM[json]` | Pipeline metadata (trace_id + filename) | `YM[{"t":"...","f":"78000.sgf"}]` |
| Move `C[]` | `andata` o/f flags | `C[Correct]`/`C[Wrong]` |

**Excluded** (per spec): `GN[]`, `PC[]`, `EV[]`, `SO[]`

### 4.5 Output Directory Structure

```
external-sources/101weiqi/
├── sgf/
│   ├── batch-001/
│   │   ├── 78000.sgf
│   │   ├── 78001.sgf
│   │   └── ...  (up to 1000 files)
│   └── batch-002/
│       └── ...
├── logs/
│   └── 101weiqi-YYYYMMDD_HHMMSS.jsonl
├── sgf-index.txt
└── .checkpoint.json
```

### 4.6 Shared Infrastructure Usage

| Feature | Module | From `tools.core` |
|---------|--------|-------------------|
| Logging | `logging_config.py` | `tools.core.logging.setup_logging` |
| Paths | `config.py` | `tools.core.paths.get_project_root, rel_path` |
| Checkpoint | `checkpoint.py` | `tools.core.checkpoint.ToolCheckpoint, BatchTrackingMixin` |
| Batching | `batching.py` | `tools.core.batching.get_batch_for_file_fast` |
| Index | `index.py` | `tools.core.index.load_index, extract_ids, add_entry` |
| Validation | `validator.py` | `tools.core.validation.validate_puzzle` |
| Rate Limit | `orchestrator.py` | `tools.core.rate_limit.RateLimiter` |
| HTTP | `client.py` | `tools.core.http.HttpClient` or custom (see below) |
| SGF Build | `converter.py` | *Manual build* (101weiqi uses custom tree format, not sgfmill) |

**Note on HTTP**: The existing `tools.core.http.HttpClient` uses `httpx`. The 101weiqi
tool may use this or keep `requests` (already a dependency). Decision: use `httpx` via
`tools.core.http` for consistency.

### 4.7 Rate Limiting Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base delay | 3.0s | Higher than OGS (2s), 101weiqi is more sensitive |
| Jitter factor | 0.5 | ±50%, matches OGS |
| Backoff base | 30.0s | Same as OGS |
| Backoff multiplier | 2.0 | 30s → 60s → 120s → 240s |
| Backoff max | 240.0s | 4 minutes cap |
| Max retries | 5 | Same as OGS |
| Consecutive failure stop | 5 | Stop after 5 consecutive 404s (for probing) |

---

## 5. Implementation Phases

### Phase 1: Core Tool (This PR)
1. Create modular file structure
2. Implement `daily` and `puzzle` source modes
3. Level mapping (`levelname` → `YG[]`)
4. Tag mapping (`qtypename` → `YT[]`)
5. Proper SGF output with YenGo properties
6. Batch directories + index + checkpoint
7. Structured logging
8. Tests for extractor, converter, levels, tags, validator
9. README documentation

### Phase 2: Collections & Books (Future)
1. Book source mode (with copyright-safe collections list)
2. Collection matching (`YL[]` property)
3. Collection exploration + scoring pipeline (like OGS `sort_collections.py`)
4. Special collection source mode

### Phase 3: Post-Processing (Future)
1. Collection-based grouping (like OGS `sgf-by-collection/`)
2. Quality scoring integration
3. Deduplication against existing external-sources

---

## 6. Open Questions for User

| # | Question | Options | Recommended |
|---|----------|---------|-------------|
| Q1 | Proxy support (Tor/SOCKS) for rate-limit avoidance? | A: Standard HTTP only / B: Configurable proxy | A: Standard HTTP only (for now) |
| Q2 | Puzzle ID discovery for `puzzle` mode? | A: Sequential probe / B: Scrape pages for IDs / C: Known ranges | A: Sequential probe with gap tolerance |
| Q3 | Professional-level puzzles (`1P-9P`) map to? | A: `expert` / B: New level | A: `expert` |
| Q4 | Should we move old downloads/state to `_archive/`? | A: Move / B: Delete / C: Keep | A: Move prototype to `_archive/` |

---

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rate limiting/IP blocking | Medium | Exponential backoff, jitter, User-Agent emulation, configurable delays |
| Copyright (book mode) | High | Phase 2 only; public-domain classics first |
| Data format changes | Low | qqdata structure is stable (confirmed over months) |
| Missing `levelname` | Low | Fallback: skip `YG[]`, let pipeline classifier handle |
| `prepos` missing | Low | Fallback to `psm.prepos` if available |

---

## Appendix: Files to Archive

The following files from the prototype will be moved to `_archive/`:
- `101weiqi_ingestor.py` (replaced by modular tool)
- `config.json` (replaced by `config.py`)
- `sources.json` (replaced by source mode architecture)
- `state.json` (replaced by `.checkpoint.json`)
- `downloads/` (local prototype data)
