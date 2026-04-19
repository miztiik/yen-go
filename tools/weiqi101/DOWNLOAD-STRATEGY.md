# 101weiqi Download Strategy

_Last Updated: 2026-04-17_

> How to use `discovery-catalog.json` and `book-ids.jsonl` to prioritise what to download,
> and which commands to run.
>
> **See also**:
> - [Collection Grading](../../docs/concepts/collection-grading.md) — Scoring methodology for collection tiers
> - [Collections](../../docs/concepts/collections.md) — Collection taxonomy and tier definitions

The `discovery-catalog.json` file (in `external-sources/101weiqi/`) is the **metadata reference** for
everything available on 101weiqi.com. It was produced by `discover-books` and refreshed on 2026-03-15.
Use it to decide *what* to download before spending rate-limited request budget.

---

## How Content Is Organised on 101weiqi (Three Separate Axes)

Understanding this prevents confusion:

| Axis | What it is | Size | Notes |
|------|-----------|------|-------|
| **Books** | Curated puzzle collections, each with a `book_id` | 201 books, 83,119 puzzles | The main library — classical texts, pro authors |
| **Tags** | Labels on books (author names, genres) | 58 tags | A book can have multiple tags |
| **Categories** | Puzzle type per-puzzle (`qtypename` field) | 7 types | Applied per-puzzle at download time, not per-book |
| **Daily** | 8 editorial picks published each calendar day | ~8/day | Separate URL pattern; may overlap with books |

These are **not a hierarchy** — they are independent. The same puzzle can appear in a book, have a
category type (死活题), and also be a daily pick. All are downloaded by puzzle ID; the axes are just
different ways to filter which IDs to target.

---

## How the Download Commands Actually Work

The tool has exactly **two download modes**:

```bash
# Mode 1: Daily — download by calendar date (8 puzzles per day)
python -m tools.weiqi101 daily --start-date 2026-01-01 --end-date 2026-01-31

# Mode 2: Puzzle — download by numeric puzzle ID
python -m tools.weiqi101 puzzle --start-id 1 --end-id 1000
python -m tools.weiqi101 puzzle --ids 78000,78001,78002
```

**There are no `--book-id`, `--tag-id`, or `--category` flags.** To download a specific book or
category, you must first discover the puzzle IDs that belong to it, then pass those to `puzzle --ids`.

---

## Downloading by Book (Per-Book Output Directories)

The `--output-dir` flag lets you isolate a book's puzzles into its own directory:

```bash
python -m tools.weiqi101 puzzle --ids <id1,id2,...> \
    --output-dir external-sources/101weiqi/books/book-5/
```

Each output directory gets its **own** `sgf/batch-001/`, `sgf-index.txt`, and `.checkpoint.json`,
so progress is tracked per-book automatically.

**The gap**: `discovery-catalog.json` records each book's `puzzle_count` but **not the individual
puzzle IDs**. To get IDs for a book you need to scrape `/book/levelorder/{book_id}/` — this is a
planned enhancement to `discover.py` (see issue below).

Until that is built, the workarounds are:

1. **Download a known ID range** — many books have sequentially allocated IDs. Check the book URL to
   estimate the range, then filter by `bookinfos.book_id` after download.
2. **Use the category mode for broad sweeps** — download all `chizi` puzzles regardless of which book
   they came from; the pipeline stage tags them with `YL[]` anyway.

---

## How Discovery Connects to Downloading

```
discover-books          →  discovery-catalog.json   (metadata: what exists)
                                    ↓
            you decide which books / categories to target
            (future: discover-book-ids --book-id 5 → puzzle ID list)
                                    ↓
python -m tools.weiqi101 puzzle --ids <list> --output-dir books/book-5/
```

---

## Progress Tracking

| Scope | Mechanism | Location |
|-------|-----------|----------|
| Per output-dir | `sgf-index.txt` | One line per downloaded puzzle ID |
| Per output-dir | `.checkpoint.json` | Last ID / date + counters |
| Global (planned) | `downloads-manifest.json` | Not yet implemented — see below |

**Current limitation**: there is no global registry showing "book 5 = 100% done, book 6 = not started."
Each output directory is self-contained.

**Recommended workaround** — maintain a simple manifest manually alongside downloads:

```
external-sources/101weiqi/
├── books/
│   ├── book-5/           ← Xuan Xuan Qi Jing
│   │   ├── sgf/batch-001/
│   │   ├── sgf-index.txt   ← 253 lines = 253 downloaded
│   │   └── .checkpoint.json
│   ├── book-201/         ← Gokyo Shumyo
│   │   └── sgf-index.txt   ← compare wc -l vs catalog puzzle_count
│   └── ...
└── daily/
    ├── sgf/batch-001/
    └── sgf-index.txt
```

Completeness check — compare `sgf-index.txt` line count against `puzzle_count` in the catalog:

```powershell
# PowerShell: check book-5 (253 expected)
(Get-Content external-sources/101weiqi/books/book-5/sgf-index.txt | Measure-Object -Line).Lines
```

```bash
# bash
wc -l external-sources/101weiqi/books/book-5/sgf-index.txt
```

---

## Book Priority System

Book priorities use the **same vocabulary** as the YenGo collection tier system
(see [Collection Grading](../../docs/concepts/collection-grading.md) and
[Collections](../../docs/concepts/collections.md)):

| Priority     | Meaning                                                                     | Books | Puzzles  |
| ------------ | --------------------------------------------------------------------------- | ----: | -------: |
| `editorial`  | Canonical pro author works or classical Go canon. Hand-reviewed.            |    79 |   29,744 |
| `premier`    | Top-quality large compilations/reference works. High community value.       |     8 |   24,888 |
| `curated`    | Good quality, known authors, fills level/technique gaps.                    |   152 |   90,373 |
| `community`  | Small, unknown author, niche. Usable but non-essential.                     |    82 |   12,638 |
| `skip`       | Too small (<30 pz), wrong content type, incomplete. Do not process.         |    53 |    3,846 |

Each book in `book-ids.jsonl` has a `"priority"` field with one of these values.

### How priorities were assigned

Expert domain review by two personas:
- **Go-Advisor** (Cho Chikun 9p) — classical authority, provenance, pedagogical canon
- **Modern-Player-Reviewer** (Hana Park 1p) — modern app user appeal, level coverage

Their independent ratings were averaged into a consensus tier, then mapped:
- Consensus tier-1 + named pro author or classical canon → `editorial`
- Consensus tier-1 + large compilation without single canonical author → `premier`
- Consensus tier-2 → `curated`
- Consensus tier-3 → `community`
- Consensus skip → `skip`

Full review data: `external-sources/101weiqi/_book_priority_report.json`

### editorial — Classical canon & named pro authors (79 books)

The oldest, most authoritative Go puzzle collections. Process first.

**Classical canon**: Xuan Xuan Qi Jing (5), Gokyo Shumyo (65), Hatsuyoron (190),
Tian Long Tu (2), Senki Buko (116), Shikatsu Myoki (166)

**Named pro authors**: Segoe Kensaku (1, 3), Go Seigen (197, 46440),
Lee Changho (321, 446, 29867), Cho Chikun (346, 4595, 27288, 27659, 29133, 29276-29281),
Sakata (28364), Ishida (27574), Kitani (28697), Takagawa (29166), Kato (29207),
Hashimoto/Maeda/Yamada/Guo Qiuzhen/Kada/Ishigure/Fujisawa series (28480-28517)

### premier — Large reference compilations (8 books)

High-value but multi-author compilations: Tsumego Masters Collection (201, 12,862 pz),
Tsumego Storm (967, 4,887 pz), L&D Complete Collection (42, 3,959 pz),
Nihon Ki-in Tesuji Encyclopedia (469, 2,608 pz), Korean L&D Classics (1355),
Classic L&D 3600 intermediate/elementary (49954, 63354)

### curated — Good quality, fills gaps (152 books)

Known authors, solid pedagogy, useful for level or technique coverage.
Includes graded series (TOM L&D, Yingang, Teacher Ye, Hitome),
technique-focused collections, and well-structured practice sets.

### community — Supplemental (82 books)

Small collections (<100 puzzles), unknown authors, niche topics.
Process after editorial/premier/curated are complete.

### skip — Excluded (53 books)

Too small (<30 puzzles), wrong content type (fuseki, joseki, not tsumego),
incomplete, or low quality.

---

## Non-Book Download Strategies

Books are the primary content axis, but two other download modes exist:

### Category Downloads (broad coverage, complements books)

| Category  | Slug     | Est. Puzzles | Best for     |
| --------- | -------- | ------------ | ------------ |
| Endgame   | `guanzi` | ~4,120       | All levels   |
| Capture   | `chizi`  | ~4,000       | Beginners–5K |
| Opening   | `buju`   | ~1,980       | Fuseki       |
| Go Theory | `qili`   | ~1,480       | Strategy     |

Category puzzles are found by sequential ID probing. Download a broad ID range and let the
per-puzzle `qtypename` field classify them:

```bash
python -m tools.weiqi101 puzzle --start-id 50000 --end-id 100000 \
    --output-dir external-sources/101weiqi/bulk/ \
    --max-puzzles 5000
```

**Priority mapping**: Category downloads don't have a book-level priority. Puzzles within
them get classified individually by the pipeline. Use category downloads to fill beginner/
elementary gaps that book collections don't cover well.

### Daily Puzzles (ongoing maintenance)

Daily puzzles are 8 editorial picks per day, accessed by date. They may overlap with books
(check `bookinfos` field after download). Store in a dedicated directory:

```bash
python -m tools.weiqi101 daily \
    --start-date 2026-01-01 --end-date 2026-03-15 \
    --output-dir external-sources/101weiqi/daily/
```

**Priority mapping**: Daily puzzles are inherently `editorial` quality — they are
hand-picked by 101weiqi editors.

---

## Recommended Download Order

```bash
# Step 1: Daily puzzles (recent 3 months) — fast, editorial quality
python -m tools.weiqi101 daily \
    --start-date 2025-12-01 --end-date 2026-03-15 \
    --output-dir external-sources/101weiqi/daily/

# Step 2: editorial + premier books (87 books, ~55K puzzles)
# Filter book-ids.jsonl for priority=editorial|premier, extract puzzle IDs
python -m tools.weiqi101 puzzle --ids <ids> \
    --output-dir external-sources/101weiqi/books/book-{id}/

# Step 3: curated books (152 books, ~90K puzzles) — after editorial/premier complete
# Same approach, filter for priority=curated

# Step 4: Category sweep for beginner gap coverage (optional)
python -m tools.weiqi101 puzzle --start-id 70000 --end-id 90000 \
    --output-dir external-sources/101weiqi/bulk/ \
    --max-puzzles 5000
```

---

## What Is Missing / Planned

| Gap | Impact | Planned fix |
|-----|--------|-------------|
| `discover-book-ids` command | Can't target a specific book for download | Add `/book/levelorder/{id}/` scraping to `discover.py` |
| Global downloads manifest | No central log of which books are done | Add `downloads-manifest.json` updated per job |
| `--category` filter | Can't filter download to one category | Not planned — filter at pipeline stage instead |

---

## Refreshing the Catalog

If you want to check whether new books have been added to the site:

```bash
# Re-run discovery (~10 min with polite rate limiting)
python -m tools.weiqi101 discover-books \
    --output external-sources/101weiqi/discovery-catalog.json

# Re-enrich with English translations
python tools/101weiqi/enrich_catalog.py
```

## Checking What You Already Have

```bash
# Count already-downloaded SGF files
(Get-ChildItem external-sources/101weiqi/sgf -Recurse -Filter *.sgf).Count   # PowerShell
find external-sources/101weiqi/sgf -name "*.sgf" | wc -l                      # bash

# Count unique IDs in the index
(Get-Content external-sources/101weiqi/sgf-index.txt | Measure-Object -Line).Lines  # PowerShell
wc -l external-sources/101weiqi/sgf-index.txt                                        # bash
```

The `sgf-index.txt` file acts as the deduplication guard — re-running any download command
is safe; already-downloaded IDs are skipped automatically.
