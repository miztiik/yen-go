# 101weiqi Download Strategy

> How to use `discovery-catalog.json` to prioritise what to download, and which commands to run.

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

## Priority Tiers

### Tier 1 — Classical Books (highest pedagogical value)

The oldest, most authoritative Go puzzle collections. Recommended first.

| Book ID | Chinese Name      | English Name                     | Puzzles | Difficulty |
| ------- | ----------------- | -------------------------------- | ------- | ---------- |
| 5       | 玄玄棋经          | Xuan Xuan Qi Jing                | 253     | 1D+        |
| 201     | 棋经众妙          | Gokyo Shumyo                     | 12,888  | 2D         |
| 6       | 官子谱—吴清源解说 | Guanzi Pu (Go Seigen commentary) | 1,320   | 1D+        |
| 190     | 桑原道节 发阳论   | Hatsuyoron — Kuwabara Doseki     | ~200    | 2D+        |
| 3675    | 重修仙机武库      | Revised Heavenly Arsenal         | 303     | 2D         |

```bash
# Once you have the puzzle IDs for these books:
python -m tools.weiqi101 puzzle --ids <ids> \
    --output-dir external-sources/101weiqi/books/book-5/
```

---

### Tier 2 — Beginner & Elementary (20K–15K)

Good for players just starting. For bulk beginner content, sweeping the `chizi` category (capture
stones) is more efficient than targeting specific books because that category has the widest
easy-difficulty coverage:

```bash
# Sample the chizi category (sequential IDs, broad difficulty)
python -m tools.weiqi101 puzzle --start-id 1 --end-id 5000 \
    --output-dir external-sources/101weiqi/category-chizi/ \
    --max-puzzles 2000
```

The `YG[]` (level slug) and `YT[]` (tag) fields are written per-puzzle at download time from the
puzzle's own `levelname` and `qtypename` fields — so difficulty filtering happens at the pipeline
stage, not at download time.

---

### Tier 3 — Author Curated Sets (intermediate to dan)

| Tag ID | Author          | Books | Typical Difficulty |
| ------ | --------------- | ----- | ------------------ |
| 6      | Hashimoto Utaro | 11    | 1K–3D              |
| 7      | Maeda Nobuaki   | 11    | 1K–4D              |
| 43     | Cho Chikun      | 13    | 1K–5D              |
| 3      | Go Seigen       | 10    | 2D–5D              |

To download an author's books with each in its own directory, you need the book IDs from the catalog
and the puzzle IDs within each book (currently requires scraping `/book/levelorder/{book_id}/`).

Planned workflow (once `discover-book-ids` is implemented):
```bash
python -m tools.weiqi101 discover-book-ids --tag-id 6   # get all Hashimoto book puzzle IDs
# then for each book:
python -m tools.weiqi101 puzzle --ids <ids> \
    --output-dir external-sources/101weiqi/books/book-28499/
```

---

### Tier 4 — Category Downloads (broad coverage)

| Category | Slug       | Est. Puzzles | Best for        |
| -------- | ---------- | ------------ | --------------- |
| Endgame  | `guanzi`   | ~4,120       | All levels      |
| Capture  | `chizi`    | ~4,000       | Beginners–5K    |
| Opening  | `buju`     | ~1,980       | Fuseki training |
| Go Theory| `qili`     | ~1,480       | Strategy        |

Category puzzles are found by sequential ID probing — there is no category-to-ID index. A reasonable
approach is to download a broad ID range and let the per-puzzle `qtypename` field (embedded in each
page) classify them:

```bash
python -m tools.weiqi101 puzzle --start-id 50000 --end-id 100000 \
    --output-dir external-sources/101weiqi/bulk/ \
    --max-puzzles 5000
```

---

### Tier 5 — Daily Puzzles (ongoing maintenance)

Daily puzzles are **completely separate** from books and categories. They are 8 editorial picks per
day, accessed by date. They may or may not come from books (the `bookinfos` field in the downloaded
SGF tells you after the fact). Store them in a dedicated directory:

```bash
# Separate output dir keeps daily separate from book downloads
python -m tools.weiqi101 daily \
    --start-date 2026-01-01 --end-date 2026-03-15 \
    --output-dir external-sources/101weiqi/daily/
```

---

## Recommended Download Order

```bash
# Step 1: Daily puzzles (recent 3 months) — fast, editorial quality
python -m tools.weiqi101 daily \
    --start-date 2025-12-01 --end-date 2026-03-15 \
    --output-dir external-sources/101weiqi/daily/

# Step 2: Classical books — once puzzle IDs are known
# (requires discover-book-ids enhancement)

# Step 3: Broad ID sweep to catch popular puzzle IDs
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


> How to use `discovery-catalog.json` to prioritise what to download, and which commands to run.

The `discovery-catalog.json` file (in `external-sources/101weiqi/`) is the **metadata reference** for
everything available on 101weiqi.com. It was produced by `discover-books` and refreshed on 2026-03-15.
Use it to decide *what* to download before spending rate-limited request budget.

---

## How Discovery Connects to Downloading

```
discover-books          →  discovery-catalog.json   (metadata: what exists)
                                    ↓
            you decide which books / categories to target
                                    ↓
python -m tools.weiqi101 puzzle …  (downloads actual SGF puzzles)
```

The download commands (`puzzle`, `daily`) do **not** read the catalog automatically — you use the
catalog as a reference to choose the right IDs or category slugs to pass on the command line.

---

## Priority Tiers

### Tier 1 — Classical Books (highest pedagogical value)

These are the oldest, most authoritative Go puzzle collections. Recommended first.

| Book ID | Chinese Name       | English Name                    | Puzzles | Difficulty |
| ------- | ------------------ | ------------------------------- | ------- | ---------- |
| 5       | 玄玄棋经           | Xuan Xuan Qi Jing               | 253     | 1D+        |
| 201     | 棋经众妙           | Gokyo Shumyo                    | 12,888  | 2D         |
| 6       | 官子谱—吴清源解说  | Guanzi Pu (Go Seigen commentary)| 1,320   | 1D+        |
| 190     | 桑原道节 发阳论    | Hatsuyoron — Kuwabara Doseki    | ~200    | 2D+        |
| 3675    | 重修仙机武库       | Revised Heavenly Arsenal        | 303     | 2D         |

**Why first**: Referenced in every serious Go curriculum. High-quality curated problems with known
difficulty calibration.

```bash
python -m tools.weiqi101 puzzle --book-ids 5,201,6,190,3675
```

---

### Tier 2 — Beginner & Elementary (20K–15K / elementary + intermediate level)

Target these if your collection is thin at the easier end. Good for players just starting out.

| Book ID | English Name                          | Puzzles | Difficulty | Tag             |
| ------- | ------------------------------------- | ------- | ---------- | --------------- |
| 4661    | Cho U 4-Line Tsumego                  | 300     | 9K+        | Classical       |
| 25527   | Qu Liqi — 1-Dan Practical Tesuji     | ~200    | 1K+        | Tesuji          |
| 28483   | Yamada Kimio — 3-Dan Breakthrough     | ~120    | 3D         | Tsumego 120     |

For bulk beginner content, the **category download** is more efficient:

```bash
# Capture-stones category: ~4,000 puzzles, wide difficulty spread, good for beginners
python -m tools.weiqi101 puzzle --category chizi --max-puzzles 2000

# Life-and-death book puzzles from the Tsumego 120 series (tag 42, 10 books)
python -m tools.weiqi101 puzzle --tag-id 42
```

---

### Tier 3 — Author Curated Sets (intermediate to dan)

Well-regarded professional authors — Hashimoto Utaro and Maeda Nobuaki in particular have the most
books on the site (11 each) and the widest difficulty range.

| Tag ID | Author               | Books | Typical Difficulty |
| ------ | -------------------- | ----- | ------------------ |
| 6      | Hashimoto Utaro      | 11    | 1K–3D              |
| 7      | Maeda Nobuaki        | 11    | 1K–4D              |
| 43     | Cho Chikun           | 13    | 1K–5D              |
| 3      | Go Seigen            | 10    | 2D–5D              |
| 1      | Classical Go Books   | 11    | 1D+                |

```bash
# All Hashimoto Utaro books (~1,800 puzzles across 11 books)
python -m tools.weiqi101 puzzle --tag-id 6

# All Cho Chikun books
python -m tools.weiqi101 puzzle --tag-id 43
```

---

### Tier 4 — Category Downloads (broad coverage)

Download by category when you want wide coverage rather than specific authors.
Categories use the **Pinyin slug** from `discovery-catalog.json`.

| Category | Slug       | Est. Puzzles | Best for               |
| -------- | ---------- | ------------ | ---------------------- |
| Endgame  | `guanzi`   | ~4,120       | All levels             |
| Capture  | `chizi`    | ~4,000       | Beginners to 5K        |
| Opening  | `buju`     | ~1,980       | Fuseki training        |
| Go Theory| `qili`     | ~1,480       | Strategic understanding|
| Middle   | `zhongpan` | ~780         | Mid-game tactics       |

```bash
# Endgame category — largest volume
python -m tools.weiqi101 puzzle --category guanzi

# Limit to 500 to sample first
python -m tools.weiqi101 puzzle --category guanzi --max-puzzles 500
```

---

### Tier 5 — Daily Puzzles (ongoing maintenance)

After the initial backfill, run daily downloads to stay current. Each day publishes 8 puzzles.

```bash
# Backfill the last 6 months of daily puzzles (~1,440 puzzles)
python -m tools.weiqi101 daily --start-date 2025-09-01 --end-date 2026-03-15

# Ongoing: just today
python -m tools.weiqi101 daily --start-date 2026-03-15 --end-date 2026-03-15
```

---

## Recommended Download Order

If starting fresh, follow this sequence to build a well-balanced collection:

```bash
# Step 1: Classical books — 201 books' worth of hand-curated material
#         Start with the most pedagogically important (~15,000 puzzles).
python -m tools.weiqi101 puzzle --book-ids 5,201,6,190,3675

# Step 2: Sample the endgame category — most populated, all levels
python -m tools.weiqi101 puzzle --category guanzi --max-puzzles 1000

# Step 3: Capture / life-and-death for beginners
python -m tools.weiqi101 puzzle --category chizi --max-puzzles 1000

# Step 4: Hashimoto and Maeda series for intermediate players
python -m tools.weiqi101 puzzle --tag-id 6
python -m tools.weiqi101 puzzle --tag-id 7

# Step 5: Daily puzzles backfill (recent 3 months)
python -m tools.weiqi101 daily --start-date 2025-12-01 --end-date 2026-03-15
```

---

## Refreshing the Catalog

If you want to check whether new books have been added to the site since 2026-03-15:

```bash
# Re-run discovery (takes ~10 min with polite rate limiting)
python -m tools.weiqi101 discover-books --output external-sources/101weiqi/discovery-catalog.json

# After discovery, re-enrich with English translations
python tools/101weiqi/enrich_catalog.py
```

---

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
