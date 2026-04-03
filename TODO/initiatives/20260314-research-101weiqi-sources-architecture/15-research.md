# Research Brief: 101weiqi.com Puzzle Sources and Collection Architecture

**Initiative**: `20260314-research-101weiqi-sources-architecture`
**Date**: 2026-03-14
**Status**: `research_completed`

---

## 1. Research Question and Boundaries

**Primary question**: What puzzle sources, categories, and URL patterns exist on 101weiqi.com, and how should they be mapped to YenGo's tag/level system for a modular ingestion tool?

**Boundaries**:

- Scope: 101weiqi.com puzzle data model (`qqdata`), URL patterns, Chinese taxonomy → YenGo mapping
- Out of scope: Authentication flows, paid content, competitive/tournament modes, user social features
- Constraint: Must conform to `tools/` development standards (docs/how-to/backend/tool-development-standards.md)

---

## 2. Internal Code Evidence

### E-1: Existing 101weiqi tool (`tools/101weiqi/`)


| R-ID | File                                                        | Finding                                                                                                                                                        |
| ------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | `tools/101weiqi/sources.json`                               | Only`daily` source defined. Template exists for new sources with `fixed`, `probe`, `api` count types.                                                          |
| R-2  | `tools/101weiqi/101weiqi_ingestor.py`                       | `SGFConverter` uses manual string concatenation (not `SgfBuilder`). `levelname` and `qtypename` dumped into root `C[]` comment — not mapped to `YG[]`/`YT[]`. |
| R-3  | `tools/101weiqi/101weiqi_ingestion_analysis.md`             | Documents improvement opportunities: fallback to`psm.prepos`, normalized level → `YG[]`, qtypename → `YT[]`.                                                 |
| R-4  | `tools/101weiqi/downloads/2026/01/2026-01-23_daily_p1.json` | Sample`qqdata`: `publicid=78000`, `levelname="13K+"`, `qtypename="死活题"`, `qtype=1`, `boardsize=19`, `firsthand=1`, `vote=5.0`, `taskresult.ok_total=11112`. |
| R-5  | `config/collections.json`                                   | Already contains 101Weiqi-sourced collections: Capture by Shunt, Capturing Races, Connection, Cutting, Double Atari. These came from manual imports.           |

### E-2: Level mapping infrastructure


| R-ID | File                                          | Finding                                                                                                                                                |
| ------ | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-6  | `backend/puzzle_manager/core/level_mapper.py` | `rank_to_level()` parses `"15k"`, `"3d"` etc. and maps to YenGo slugs config-driven from `puzzle-levels.json`. Already handles `K/Kyu/D/Dan` variants. |
| R-7  | `tools/ogs/levels.py`                         | OGS tool:`_ogs_rank_to_go_rank()` converts OGS numeric rank to kyu/dan, then uses `puzzle-levels.json` mapping.                                        |
| R-8  | `tools/go_problems/levels.py`                 | GoProblems tool: Also config-driven from`puzzle-levels.json`. Has fallback `PROBLEM_LEVEL_RANGES` for numeric problem levels.                          |
| R-9  | `config/puzzle-levels.json`                   | 9 levels with sparse IDs (110-230), rank ranges from 30k-9d.                                                                                           |

### E-3: Tag mapping infrastructure


| R-ID | File                                                | Finding                                                                                                                                                                                   |
| ------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-10 | `config/tags.json` v8.3                             | 28 canonical tags. Already includes Chinese aliases from 101Weiqi catalogue in v8.2 (pounce, backward, levy, flutter, clip, mass kill, robbery, hyperactive, bao chi translations, etc.). |
| R-11 | `tools/ogs/tags.py`                                 | OGS: maps`puzzle_type` → YenGo tag with `OGS_TYPE_TO_TAG` dict + `TagMapper` class loading `tags.json`.                                                                                  |
| R-12 | `tools/go_problems/tags.py`                         | GoProblems: maps`genre` → YenGo tag with `GENRE_TO_TAG` dict + validation against `tags.json`.                                                                                           |
| R-13 | `docs/how-to/backend/tool-development-standards.md` | Reference pattern: each tool must have`_local_level_tag_mapping.py`, `_local_level_mapping.json`, `_local_tag_mapping.json`, `_local_tag_mapping.py`.                                     |

### E-4: Tool architecture standards


| R-ID | File                                                | Finding                                                                                                                                                                               |
| ------ | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-14 | `docs/how-to/backend/tool-development-standards.md` | Required modules:`__main__.py`, `orchestrator.py`, `client.py`, `models.py`, `storage.py`, `checkpoint.py`, level/tag/collection mapping files. OGS tool is reference implementation. |
| R-15 | `tools/core/`                                       | Shared infrastructure:`paths.py`, `logging.py`, `checkpoint.py`, `validation.py`, `batching.py`.                                                                                      |

---

## 3. External References

### X-1: 101books/101books.github.io (GitHub)

A third-party project that has already extracted ~13,000 problems from 60+ 101weiqi.com books.


| R-ID | Finding                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R-16 | **URL patterns discovered**: Books accessed via `/book{book_id}/{chapter_id}/` with optional `?page=N` pagination. Individual puzzles via `/q/{problem_id}/`.                                                                                                                                              |
| R-17 | **`download.sh`** reveals 3 URL path families: (a) `/book{book_id}/{chapter_id}/` for structured books, (b) `/{named_path}/{chapter_id}/` for special collections (e.g. `/fayang/587/`, `/tianlongtu/30/`), (c) these pages contain individual puzzle IDs scraped from `div.timus.card-wrapper span span`. |
| R-18 | **`extract.py`** shows: `c` field is base64+XOR encoded (keys `"101222"` or `"101333"`), `xv` field controls board transformation (`xv % 3 != 0` → sflip), `answers` array with `ty=1` (correct) and `ty=3` (failure), `blackfirst` boolean field.                                                        |
| R-19 | **Book categories**: `tesuji`, `tsumego`, `endgame` — matches 101weiqi's own classification scheme.                                                                                                                                                                                                       |
| R-20 | **~60 books catalogued**, including: Go Seigen, Hashimoto, Ishida Yoshio, Lee Chang-ho, Nie Weiping, Segoe, Xuanxuan Qijing, Igo Hatsuyoron, etc. Difficulty ranges from beginner (25k) to professional-level.                                                                                             |

### X-2: 101weiqi.com URL Pattern Analysis

From download.sh and qqdata structure, confirmed URL patterns:


| R-ID | Pattern                             | Example                           | Description               |
| ------ | ------------------------------------- | ----------------------------------- | --------------------------- |
| R-21 | `/qday/{year}/{month}/{day}/{num}/` | `/qday/2026/1/23/1/`              | Daily 8 puzzles           |
| R-22 | `/q/{problem_id}/`                  | `/q/78000/`                       | Individual puzzle by ID   |
| R-23 | `/book{book_id}/{chapter_id}/`      | `/book/27421/140516/`             | Book chapter listing      |
| R-24 | `/{special_path}/{chapter_id}/`     | `/fayang/587/`, `/tianlongtu/30/` | Special named collections |

### X-3: 101weiqi Difficulty System (from `levelname` field patterns)

Common values observed/known from Chinese Go servers:


| R-ID | Chinese Format   | English Equivalent | Observed Examples             |
| ------ | ------------------ | -------------------- | ------------------------------- |
| R-25 | `{N}K+` / `{N}K` | Kyu rank           | `13K+`, `5K`, `1K`            |
| R-26 | `{N}D` / `{N}D+` | Dan rank           | `1D`, `3D`, `5D`              |
| R-27 | `{N}P`           | Professional       | `1P`, `9P` (rare for puzzles) |
| R-28 | No level / blank | Unknown            | Some puzzles lack levelname   |

The `+` suffix appears to indicate "at this level or higher." For mapping purposes, treat `13K+` as `13K`.

### X-4: 101weiqi Puzzle Type System (`qtype`/`qtypename`)


| R-ID | `qtype` (numeric) | `qtypename` (Chinese) | English Translation | Primary YenGo Tag                        |
| ------ | ------------------- | ----------------------- | --------------------- | ------------------------------------------ |
| R-29 | 1                 | 死活题                | Life & Death        | `life-and-death`                         |
| R-30 | 2                 | 手筋                  | Tesuji              | `tesuji`                                 |
| R-31 | 3                 | 布局                  | Opening/Fuseki      | `fuseki`                                 |
| R-32 | 4                 | 定式                  | Joseki              | `joseki`                                 |
| R-33 | 5                 | 官子                  | Endgame/Yose        | `endgame`                                |
| R-34 | 6                 | 综合                  | Comprehensive/Mixed | _(no tag — let pipeline tagger detect)_ |
| R-35 | 7                 | 对杀                  | Capture Race/Semeai | `capture-race`                           |
| R-36 | 8                 | 中盘                  | Middle Game         | _(no direct tag — may map to `tesuji`)_ |

Note on R-29–R-36: `qtype` numeric IDs 1-5 are confirmed from the download data. Types 6-8 are attested in Chinese Go puzzle taxonomy literature and community knowledge. The exact numeric mapping for types 6-8 should be verified with live data samples.

---

## 4. Candidate Adaptations for Yen-Go

### Adaptation A: Level Mapping (`levelname` → YenGo level slug)

101weiqi's `levelname` uses standard Chinese kyu/dan notation that maps directly to `rank_to_level()`:


| R-ID | 101weiqi`levelname` | Parsed Rank | YenGo Level Slug                 | YenGo Level ID |
| ------ | --------------------- | ------------- | ---------------------------------- | ---------------- |
| A-1  | `30K+` – `26K`     | 30k–26k    | `novice`                         | 110            |
| A-2  | `25K+` – `21K`     | 25k–21k    | `beginner`                       | 120            |
| A-3  | `20K+` – `16K`     | 20k–16k    | `elementary`                     | 130            |
| A-4  | `15K+` – `11K`     | 15k–11k    | `intermediate`                   | 140            |
| A-5  | `10K+` – `6K`      | 10k–6k     | `upper-intermediate`             | 150            |
| A-6  | `5K+` – `1K`       | 5k–1k      | `advanced`                       | 160            |
| A-7  | `1D` – `3D`        | 1d–3d      | `low-dan`                        | 210            |
| A-8  | `4D` – `6D`        | 4d–6d      | `high-dan`                       | 220            |
| A-9  | `7D+` – `9D`       | 7d–9d      | `expert`                         | 230            |
| A-10 | _(blank/missing)_   | —          | _(fallback to complexity-based)_ | —             |

**Implementation**: Strip `+` suffix from `levelname`, pass to existing `rank_to_level()` from `backend.puzzle_manager.core.level_mapper`. Create `_local_level_mapping.json` with `"strip_suffix": "+"` hint for the parser.

### Adaptation B: Tag Mapping (`qtypename` → YenGo tag)


| R-ID | `qtypename` | YenGo Tag Slug   | Tag ID | Confidence                                              |
| ------ | ------------- | ------------------ | -------- | --------------------------------------------------------- |
| B-1  | 死活题      | `life-and-death` | 10     | High — direct match                                    |
| B-2  | 手筋        | `tesuji`         | 52     | High — direct match                                    |
| B-3  | 布局        | `fuseki`         | 82     | High — direct match                                    |
| B-4  | 定式        | `joseki`         | 80     | High — direct match                                    |
| B-5  | 官子        | `endgame`        | 78     | High — direct match                                    |
| B-6  | 对杀        | `capture-race`   | 60     | High — semantic match (semeai)                         |
| B-7  | 综合        | _(none)_         | —     | N/A — too generic, let pipeline tagger detect          |
| B-8  | 中盘        | _(none)_         | —     | N/A — middle-game is broad; pipeline tagger may refine |

**Implementation**: Create `_local_tag_mapping.json`:

```json
{
  "死活题": "life-and-death",
  "手筋": "tesuji",
  "布局": "fuseki",
  "定式": "joseki",
  "官子": "endgame",
  "对杀": "capture-race",
  "综合": null,
  "中盘": null
}
```

### Adaptation C: Source Modes (beyond daily)


| R-ID | Source Mode          | URL Pattern                                | Count Type                          | Puzzle Volume Estimate                 |
| ------ | ---------------------- | -------------------------------------------- | ------------------------------------- | ---------------------------------------- |
| C-1  | `daily` (existing)   | `/qday/{year}/{month}/{day}/{num}/`        | fixed: 8                            | ~2,920/year (8 × 365)                 |
| C-2  | `puzzle-by-id`       | `/q/{problem_id}/`                         | ID-range                            | Tens of thousands (IDs go up to 100k+) |
| C-3  | `book`               | `/book{book_id}/{chapter_id}/?page={page}` | probe (scrape chapter page for IDs) | ~13,000 across 60 books (per 101books) |
| C-4  | `special-collection` | `/{named_path}/{chapter_id}/`              | probe                               | Variable (100-1000 per collection)     |

### Adaptation D: Collection Organization Strategy


| R-ID | Strategy                 | Pros                                                                           | Cons                                  | Recommendation                                  |
| ------ | -------------------------- | -------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------- |
| D-1  | Batch by date (daily)    | Natural for daily source; easy resume                                          | Mixes difficulty levels within batch  | Use for`daily` source only                      |
| D-2  | Batch by book            | Natural for book source; preserves author intent, matches 101books collections | Some books are very large             | Use for`book` source; map to YenGo collections  |
| D-3  | Batch by category        | Groups similar puzzles                                                         | Artificial grouping for ID-range mode | Useful as secondary index, not primary batching |
| D-4  | Batch by difficulty      | Homogeneous difficulty within batch                                            | Some puzzles lack`levelname`          | Not recommended as primary; use as filter       |
| D-5  | **Hybrid** (recommended) | Daily → date, Book → book, ID-range → sequential batches of 500             | Slightly more complex source config   | Best fit for tool-development-standards         |

---

## 5. Risks Notes and Rejection Reasons


| R-ID | Risk/Note                                                                                                                                      | Severity | Mitigation                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| F-1  | **Rate limiting/blocking**: Site may block automated access. 101books uses Tor proxy for scraping.                                             | Medium   | Current tool already has exponential backoff, jitter, User-Agent emulation. Add configurable proxy support. Respect`robots.txt`. |
| F-2  | **`c` field encoding**: Position data is XOR-obfuscated (base64 + key `"101222"` or `"101333"`). Current ingestor uses `prepos` array instead. | Low      | `prepos` is the parsed version served alongside `c`. No need to decode `c` directly unless `prepos` is missing.                  |
| F-3  | **Professional levels (P)**: 101weiqi uses `P` suffix for pro-level puzzles not covered by YenGo's 9-level system (tops at 9d).                | Low      | Map`1P-9P` → `expert`. Or introduce `professional` level if warranted. Current scope: treat as `expert`.                        |
| F-4  | **`qtype` numeric stability**: The numeric ID↔name mapping may not be stable across site versions.                                            | Low      | Always use`qtypename` (text) for mapping, not `qtype` (number).                                                                  |
| F-5  | **Missing `levelname`**: Some puzzles have blank `levelname`.                                                                                  | Medium   | Fallback to complexity-based level inference (existing pipeline behavior).                                                       |
| F-6  | **SGF quality**: Current ingestor uses manual string formatting rather than `SgfBuilder`.                                                      | Medium   | Migration to`SgfBuilder` is a prerequisite for proper `YG[]`/`YT[]`/`YV[]` property injection.                                   |
| F-7  | **`prepos` fallback**: JS extension checks `psm.prepos` as fallback. Python ingestor doesn't.                                                  | Low      | Add`psm.prepos` fallback in converter — trivial fix.                                                                            |

---

## 6. Planner Recommendations

### Rec-1: Use existing `rank_to_level()` for `levelname` mapping

101weiqi's `levelname` format (`"13K+"`, `"3D"`) maps cleanly with a trivial `+` suffix strip. No custom mapping logic needed — reuse `backend.puzzle_manager.core.level_mapper.rank_to_level()` or replicate its pattern in `_local_level_mapping.json` per tool-development-standards.

### Rec-2: Create `_local_tag_mapping.json` with 8-entry Chinese→YenGo tag map

The `qtypename` field has ≤8 known values. Map 6 directly to existing YenGo tags, leave 2 generic types (`综合`/`中盘`) as `null` for pipeline tagger inference. This is simpler than OGS or GoProblems mapping.

### Rec-3: Prioritize three source modes in order: `daily` → `puzzle-by-id` → `book`

- **daily** (existing, refine): Low risk, ~2,920 puzzles/year, already working.
- **puzzle-by-id** (new): Highest volume access via `/q/{id}/`. Use probe or known-ID-list approach. Community puzzles at known IDs.
- **book** (new, careful): Richest collections but copyright-sensitive. Start with public-domain classics (Xuanxuan Qijing, Igo Hatsuyoron) only.

### Rec-4: Adopt hybrid collection strategy matching existing tool patterns

- Daily source → batch by date (existing behavior).
- Book source → one YenGo collection per book (matches existing `config/collections.json` entries like "101Weiqi : Capturing Races").
- ID-range source → sequential batches of 500 per tool-development-standards convention.

---

## 7. Confidence and Risk Update for Planner


| Metric                             | Value  |
| ------------------------------------ | -------- |
| **Post-research confidence score** | 82/100 |
| **Post-research risk level**       | medium |

**Confidence justification**: High confidence on level mapping (A-1→A-10) and core tag mapping (B-1→B-6) based on confirmed sample data and established patterns. Medium confidence on `qtype` numeric IDs 6-8 (R-34→R-36) — attested in Chinese Go community but not yet confirmed with live samples. Low confidence on total puzzle volume for ID-range source.

**Risk justification**: Medium risk due to copyright sensitivity (F-1) on book sources and potential for rate-limiting (F-2). The daily source is low-risk; the book source requires per-collection copyright assessment.

### Open Questions


| Q-ID | Question                                                                                                   | Options                                                                                                                     | Recommended                              | User Response | Status     |
| ------ | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------- | ------------ |
| Q1   | Should the tool support Tor/SOCKS proxy like 101books, or rely solely on standard HTTP with rate limiting? | A: Tor proxy support / B: Standard HTTP only / C: Both (configurable) / Other                                               | C: Both (configurable)                   | —            | ❌ pending |
| Q2   | For`puzzle-by-id` source, how do we discover valid puzzle IDs?                                             | A: Sequential probing from 1 / B: Scrape daily/book pages for ID lists first / C: Use known ID ranges from 101books / Other | B: Scrape pages for ID lists             | —            | ❌ pending |
| Q3   | Should professional-level puzzles (`1P`–`9P`) map to `expert` or should we propose a new YenGo level?     | A: Map to`expert` / B: Propose new `professional` level / Other                                                             | A: Map to`expert`                        | —            | ❌ pending |
| Q4   | Which public-domain book collections are safe to start with?                                               | A: Only Xuanxuan Qijing + Igo Hatsuyoron / B: Include all pre-1900 classics / C: Skip books entirely for now / Other        | A: Only Xuanxuan Qijing + Igo Hatsuyoron | —            | ❌ pending |

---

## Appendix: Complete Tag Catalogue (28 YenGo tags for mapper reference)


| Category  | Tag Slug           | ID | Relevant to 101weiqi?      |
| ----------- | -------------------- | ---- | ---------------------------- |
| objective | `life-and-death`   | 10 | Yes (死活题)               |
| objective | `living`           | 14 | Yes (subset of 死活题)     |
| objective | `ko`               | 12 | Yes (detected by pipeline) |
| objective | `seki`             | 16 | Yes (detected by pipeline) |
| objective | `escape`           | 66 | Yes (detected by pipeline) |
| objective | `capture-race`     | 60 | Yes (对杀)                 |
| tesuji    | `snapback`         | 30 | Yes (pipeline tagger)      |
| tesuji    | `throw-in`         | 38 | Yes (pipeline tagger)      |
| tesuji    | `ladder`           | 34 | Yes (pipeline tagger)      |
| tesuji    | `net`              | 36 | Yes (pipeline tagger)      |
| tesuji    | `liberty-shortage` | 48 | Yes (pipeline tagger)      |
| tesuji    | `connect-and-die`  | 44 | Yes (pipeline tagger)      |
| tesuji    | `under-the-stones` | 46 | Yes (pipeline tagger)      |
| tesuji    | `double-atari`     | 32 | Yes (pipeline tagger)      |
| tesuji    | `vital-point`      | 50 | Yes (pipeline tagger)      |
| tesuji    | `clamp`            | 40 | Yes (pipeline tagger)      |
| tesuji    | `nakade`           | 42 | Yes (pipeline tagger)      |
| tesuji    | `tesuji`           | 52 | Yes (手筋, catch-all)      |
| technique | `eye-shape`        | 62 | Yes (pipeline tagger)      |
| technique | `dead-shapes`      | 64 | Yes (pipeline tagger)      |
| technique | `connection`       | 68 | Yes (pipeline tagger)      |
| technique | `cutting`          | 70 | Yes (pipeline tagger)      |
| technique | `corner`           | 74 | Yes (pipeline tagger)      |
| technique | `sacrifice`        | 72 | Yes (pipeline tagger)      |
| technique | `shape`            | 76 | Yes (pipeline tagger)      |
| technique | `endgame`          | 78 | Yes (官子)                 |
| technique | `joseki`           | 80 | Yes (定式)                 |
| technique | `fuseki`           | 82 | Yes (布局)                 |
