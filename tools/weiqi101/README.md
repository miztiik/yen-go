# weiqi101 — 101weiqi.com Puzzle Downloader

Modular tool to download Go/Baduk tsumego puzzles from [101weiqi.com](https://www.101weiqi.com) and store them as YenGo-enriched SGF files.

> **Note**: The package is named `weiqi101` (not `101weiqi`) because Python packages cannot start with a digit. The original prototype lives in `tools/101weiqi/`.

> **Not sure what to download first?** See [DOWNLOAD-STRATEGY.md](DOWNLOAD-STRATEGY.md) for a
> priority guide — which books and categories to start with, and how to use `discovery-catalog.json`
> to plan your downloads.

---

## Capabilities at a Glance

| Capability | Command | Output |
|---|---|---|
| **Browser capture** (bypasses CAPTCHA) | `receive` + Tampermonkey userscript | SGF files in `sgf/batch-NNN/` |
| Import from JSONL file | `import-jsonl FILE` | SGF files in `sgf/batch-NNN/` |
| Download daily 8-puzzle sets | `puzzle daily` | SGF files in `sgf/batch-NNN/` |
| Download puzzles by ID range | `puzzle --start-id/--end-id` | SGF files in `sgf/batch-NNN/` |
| Download a specific book | `puzzle --book-id N` | SGF files in `books/book-N/sgf/` |
| Discover all books & tags | `discover-books` | `discovery-catalog.json` |
| Discover puzzle IDs per book | `discover-book-ids` | `book-ids.jsonl` (merged, canonical) |
| Discover category sizes | `discover-categories` | Printed to stdout |
| Inspect tag/collection mappings | `scan-tags`, `scan-collections` | Printed to stdout |

## State Files & Orchestration

The tool writes **five canonical state files**. Each has a clear purpose in the download lifecycle:

```
external-sources/101weiqi/
│
├── discovery-catalog.json        ← (1) CATALOG: All 201 books, 58 tags, 7 categories
│                                         Source of: book names, puzzle counts, difficulty,
│                                         tag membership. Run: discover-books
│
├── book-ids.jsonl                ← (2) QUEUE: Per-book puzzle ID lists (JSONL, one line/book)
│                                         Source of: exact IDs to download per book, plus
│                                         view_count, like_count, finish_count metadata.
│                                         Run: discover-book-ids --book-id N
│                                         Format: {"book_id":5,"puzzle_ids":[...],"view_count":0,...}
│
├── sgf-index.txt                 ← (3) DONE INDEX: One puzzle ID per line, all downloaded IDs
│                                         Used for O(1) dedup — re-running a download skips
│                                         any ID already present here.
│
├── .checkpoint.json              ← (4) RESUME STATE: Last completed batch position
│                                         Use --resume to continue an interrupted run.
│                                         Reset: delete this file to start fresh.
│
└── logs/
    └── YYYYMMDD-HHMMSS-101weiqi.jsonl  ← (5) AUDIT LOG: Every request/response logged
```

### Recommended Workflow (Low Cognitive Load)

Work through books one at a time. The three-step cycle keeps you in control:

```
Step 1  CATALOG      discover-books    →  discovery-catalog.json
          ↓ Choose books to download (sort by like_count, puzzle_count, difficulty)

Step 2  QUEUE        discover-book-ids --book-id N  →  book-ids.jsonl (merged)
          ↓ Review the puzzle IDs — check puzzle_count matches catalog expectation

Step 3  DOWNLOAD     puzzle --book-id N  →  books/book-N/sgf/batch-001/
          ↓ Check sgf-index.txt grows; use --resume if interrupted
```

**Sequencing multiple books without overload:**

```bash
# 1. Get the full book catalog (one-time, ~15 mins)
python -m tools.weiqi101 discover-books
# → saves to external-sources/101weiqi/discovery-catalog.json
# → if file already exists, backs up as discovery-catalog.YYYYMMDD-HHMMSS.json

# 2. Pick a batch of books from the catalog (e.g. Cho Chikun series = tag 43)
python -m tools.weiqi101 discover-book-ids --tag-id 43
# → appends/merges all Cho Chikun books into book-ids.jsonl

# 3. Download them one at a time (check progress between runs)
python -m tools.weiqi101 puzzle --book-id 28499   # Hashimoto Utaro (1,384 puzzles)
python -m tools.weiqi101 puzzle --book-id 197     # Wu Qingyuan tsumego (1,630 puzzles)
python -m tools.weiqi101 puzzle --book-id 28513   # Maeda Nobuaki (1,473 puzzles)

# 4. Resume any interrupted download
python -m tools.weiqi101 puzzle --book-id 28499 --resume
```

**Checking progress at any time:**

```bash
# How many puzzles are downloaded?
python -c "print(sum(1 for _ in open('external-sources/101weiqi/sgf-index.txt')))"

# Which books have IDs discovered?
python -c "
import json
for line in open('external-sources/101weiqi/book-ids.jsonl'):
    b = json.loads(line)
    print(f'  Book {b[\"book_id\"]:>6}: {len(b[\"puzzle_ids\"]):>5} IDs  '
          f'views={b[\"view_count\"]:>6,}  likes={b[\"like_count\"]:>4}  {b[\"book_name_en\"][:40]}')
"
```

---

## Quick Start

```bash
# Show help
python -m tools.weiqi101 --help

# Download daily puzzles (8 per day) for a date range
python -m tools.weiqi101 daily --start-date 2026-01-01 --end-date 2026-01-31

# Download puzzles by ID range
python -m tools.weiqi101 puzzle --start-id 1 --end-id 1000

# Download specific puzzle IDs
python -m tools.weiqi101 puzzle --ids 78000,78001,78002

# Download an entire book (auto-fetches puzzle IDs, isolated output dir)
python -m tools.weiqi101 puzzle --book-id 197

# Resume an interrupted download
python -m tools.weiqi101 puzzle --start-id 1 --end-id 5000 --resume

# Dry run (show what would be downloaded)
python -m tools.weiqi101 daily --start-date 2026-03-01 --end-date 2026-03-14 --dry-run
```

## Prerequisites

- Python 3.11+ (uses `tools.core` shared infrastructure)
- `httpx` library (already in project dependencies)
- Run from the project root: `python -m tools.weiqi101 ...`

### Rate Limiting and Cookies

101weiqi.com aggressively rate-limits automated requests. The tool uses a 60s default delay with jitter, but the site may still serve Tencent CAPTCHA pages or require login after ~5-10 requests per session.

**Recommended workflow for sustained downloading:**

1. Log in to 101weiqi.com in your regular browser (Chrome/Edge/Firefox)
2. Open DevTools (F12) → Application → Cookies → `www.101weiqi.com`
3. Copy the cookie values (typically `sessionid` and `csrftoken`)
4. Pass them to the tool:

```bash
python -m tools.weiqi101 --cookies "sessionid=abc123;csrftoken=xyz789" puzzle --book-id 197 --resume
```

**Dealing with CAPTCHA blocks:**
- The tool detects CAPTCHA and login pages, saves checkpoint, and exits cleanly
- Wait 15-30 minutes between sessions for the rate-limit to expire
- Re-run with `--resume` to continue from where you left off
- Each session typically downloads ~5-10 puzzles before being blocked
- A 100-puzzle book completes in ~10-15 runs spaced over a few hours

## Source Modes

### Browser Capture (Recommended for Sustained Downloads)

The automated HTTP client gets blocked by Tencent CAPTCHA after ~5-10 requests. The **browser capture** mode bypasses this by using your real browser to browse 101weiqi.com while a Tampermonkey userscript extracts puzzle data and sends it to a local Python receiver.

#### Setup

1. Install [Tampermonkey](https://www.tampermonkey.net/) in Chrome/Edge/Firefox
2. Create a new userscript and paste the contents of [`browser/101weiqi-capture.user.js`](browser/101weiqi-capture.user.js)
3. Start the local receiver:

```bash
python -m tools.weiqi101 receive
```

4. Browse to any 101weiqi puzzle page (e.g. `https://www.101weiqi.com/q/78000/`)
5. The userscript captures the page and sends it to the receiver automatically

#### How It Works

The userscript auto-detects everything on page load:

1. Checks if the server has an active queue (e.g. from `--book-id`)
2. If a queue is active → auto-captures and navigates through it
3. If no queue → captures the current page and waits

**No mode selection needed.** Just start the server and browse.

#### Downloading a Book

**Option 1: Pre-load from CLI** (simplest)

```bash
# Discover book IDs first (one-time)
python -m tools.weiqi101 discover-book-ids --book-id 197 --by-chapter

# Start with book pre-loaded — just browse to any puzzle page
python -m tools.weiqi101 receive --book-id 197
```

**Option 2: Pick from browser** (visual)

1. Start the plain receiver: `python -m tools.weiqi101 receive`
2. Browse to any puzzle page
3. Tampermonkey menu > **"Pick a Book"**
4. A dialog shows all discovered books with download progress
5. Click one to start downloading — the script navigates automatically

#### Menu Commands

| Command | Description |
|---------|-------------|
| **Pick a Book** | Browse discovered books with progress, click to start |
| **Stop** | Pause navigation (also stops server queue) |
| **Show Telemetry** | Pop up timing, error counts, book info from server |
| **Reset Stats** | Clear local OK/Skip/Error/CAPTCHA/404 counters |

#### Status Bar

A fixed bar at the top of each page shows:
- Current action (capturing, navigating, waiting)
- Counters: `OK`, `Skip`, `Err`, `CAPTCHA`, `404`, `Total`
- State: `RUNNING` or `IDLE`

#### CAPTCHA & Error Handling

- **CAPTCHA detected**: The script pauses, shows a notification, and polls every 5s. Solve it manually; the script resumes automatically.
- **Login required**: Script stops. Log in, then reload.
- **404 / No qqdata**: Counted as `notfound`, skipped automatically.
- **Receiver unreachable**: Script stops immediately to avoid losing pages.

#### Receiver CLI Options

```bash
python -m tools.weiqi101 receive [OPTIONS]
```

| Option                      | Default    | Description                               |
| --------------------------- | ---------- | ----------------------------------------- |
| `--host`                    | 127.0.0.1  | Bind address                              |
| `--port`                    | 8101       | Bind port                                 |
| `--book-id`                 | —          | Pre-load book queue from book-ids.jsonl    |
| `--output-dir`              | (default)  | Output directory                          |
| `--batch-size`              | 1000       | Max SGF files per batch directory          |
| `--match-collections`       | on         | Assign YL[] collection from category       |
| `--resolve-intent`          | on         | Generate root C[] intent from category     |

#### Receiver Endpoints

| Endpoint            | Method | Description                              |
| ------------------- | ------ | ---------------------------------------- |
| `POST /capture`     | POST   | Submit qqdata JSON for processing         |
| `POST /queue/book`  | POST   | Load a book's IDs: `{"book_id": 197}`     |
| `POST /queue/ids`   | POST   | Load custom IDs: `{"ids": [1,2,3]}`       |
| `GET  /next`        | GET    | Pop next puzzle URL from queue             |
| `GET  /queue/status` | GET   | Queue progress (pending, visited, %)       |
| `GET  /queue/stop`  | GET    | Deactivate the queue                       |
| `GET  /books`       | GET    | List all discovered books with progress    |
| `GET  /status`      | GET    | Download stats + queue summary             |
| `GET  /telemetry`   | GET    | Detailed event log, timing, errors         |
| `GET  /health`      | GET    | Health check                               |

#### Telemetry & Logging

Both the server and userscript provide detailed telemetry:

**Server-side (Python):**
- Every capture event is logged to the file logger with `[TELEM]` prefix: timestamp, puzzle ID, status, duration, file path
- `GET /telemetry` returns a JSON summary:
  - `counts`: ok/skipped/error breakdown
  - `total_processed`, `avg_duration_ms`
  - `last_ok_at`, `last_error_at` timestamps
  - `recent_errors`: last 50 errors with details
  - `recent_events`: last 200 events with full metadata
  - `book_id`, `book_name` if a book queue is active
  - `started_at`: session start time

**Userscript-side (browser console):**
- Every action is logged to the browser console with `[YenGo] [INFO|WARN|ERROR]` prefix and ISO timestamp
- Open DevTools (F12) > Console to see the live log
- Events logged: page load, capture start/success/skip/error, navigation, CAPTCHA detection, queue requests

**File logging (persistent audit trail):**
- All server events are written to `logs/YYYYMMDD-HHMMSS-101weiqi.jsonl`
- Queue lifecycle events: load, next, stop, complete
- Each capture: puzzle ID, status, duration, SGF file path

#### Offline Import from JSONL

If you save captured data as JSONL (one `{"qqdata": {...}}` per line), import it later:

```bash
python -m tools.weiqi101 import-jsonl captured-data.jsonl
```

#### Typical Book Download Workflow

```bash
# 1. Discover book IDs (one-time per book)
python -m tools.weiqi101 discover-book-ids --book-id 197 --by-chapter

# 2. Start receiver with the book pre-loaded
python -m tools.weiqi101 receive --book-id 197

# 3. Open any 101weiqi puzzle page in browser
#    The userscript auto-captures and navigates through the queue

# 4. If interrupted (CAPTCHA, close browser), just restart:
python -m tools.weiqi101 receive --book-id 197
#    Already-downloaded puzzles are automatically skipped

# 5. Monitor progress (optional)
curl http://127.0.0.1:8101/queue/status   # queue progress
curl http://127.0.0.1:8101/books           # all books with progress
curl http://127.0.0.1:8101/telemetry      # detailed event history
```

**Throughput**: ~10-20 puzzles/minute (limited by page load + random 3-8s delay). A 1000-puzzle book takes ~1-2 hours of idle browsing.

**Bolt-on design**: This feature is fully contained in `receiver.py` + `browser/`. Remove both to uninstall completely.

### Daily Puzzles

Downloads the 8 daily puzzles published each day on 101weiqi.com.

```bash
python -m tools.weiqi101 daily --start-date 2026-01-01 --end-date 2026-01-31
```

URL pattern: `https://www.101weiqi.com/daily/dnum/{YYYY}/{M}/{D}/`

### Puzzle by ID

Downloads individual puzzles by their numeric ID.

```bash
# ID range
python -m tools.weiqi101 puzzle --start-id 1 --end-id 1000

# Specific IDs
python -m tools.weiqi101 puzzle --ids 78000,78001,78002
```

URL pattern: `https://www.101weiqi.com/chessmanual/{puzzle_id}/`

## CLI Options

| Option                      | Default                     | Description                                      |
| --------------------------- | --------------------------- | ------------------------------------------------ |
| `--output-dir`              | `external-sources/101weiqi` | Output directory                                 |
| `--batch-size`              | 1000                        | Max SGF files per batch directory                |
| `--puzzle-delay`            | 60.0                        | Delay between requests (seconds)                 |
| `--max-puzzles`             | 10000                       | Maximum puzzles to download per run              |
| `--resume`                  | off                         | Resume from last checkpoint                      |
| `--dry-run`                 | off                         | Show what would be downloaded                    |
| `--cookies`                 | —                           | Session cookies (`Name=Value;Name2=Value2`)       |
| `--no-log-file`             | off                         | Disable file logging (console only)              |
| `-v`, `--verbose`           | off                         | Enable verbose/debug logging                     |
| `--match-collections`       | on                          | Assign YL[] collection from category mapping     |
| `--no-match-collections`    | —                           | Disable YL[] collection matching                 |
| `--resolve-intent`          | on                          | Generate root C[] intent from category           |
| `--no-resolve-intent`       | —                           | Disable root C[] intent resolution               |

### Scan Utilities

```bash
# Show tag mapping coverage (Chinese → YenGo tag)
python -m tools.weiqi101 scan-tags

# Show collection mapping coverage (Chinese → YenGo collection slug)
python -m tools.weiqi101 scan-collections
```

These are read-only inspection commands that display the static mapping tables without downloading anything.

### Discovery Utilities

```bash
# Full BFS discovery: book tags, books per tag, category page counts
python -m tools.weiqi101 discover-books

# Save discovery results to a custom path
python -m tools.weiqi101 discover-books --output catalog.json

# Re-run discovery (previous file auto-backed up with timestamp)
python -m tools.weiqi101 discover-books

# Discover books under a single tag only (e.g., tag 42 = 诘棋120系列)
python -m tools.weiqi101 discover-books --tag-id 42

# Probe category pages for pagination counts
python -m tools.weiqi101 discover-categories

# Adjust polite delay between requests (default: 3s)
python -m tools.weiqi101 discover-books --delay 5.0
```

Discovery commands scrape the 101weiqi website to catalog available books, tags, and puzzle categories. Results can be saved as JSON for offline analysis.

### Discover Book IDs (Puzzle-Level Mapping)

Scrapes `/book/levelorder/{book_id}/` to get the exact ordered list of puzzle IDs in a book, plus available aggregate metadata (views, likes, completions).

Output: `external-sources/101weiqi/book-ids.jsonl` — **one JSON object per line, sorted by book_id**. Re-running merges new data with existing entries; the same `book_id` is overwritten with fresh data.

```bash
# Discover IDs for a single book
python -m tools.weiqi101 discover-book-ids --book-id 197

# Discover IDs for several books at once
python -m tools.weiqi101 discover-book-ids --book-ids 197,201,924

# Discover IDs for all books under a tag (reads discovery-catalog.json)
python -m tools.weiqi101 discover-book-ids --tag-id 43    # Cho Chikun series

# Write to a custom path instead of the default
python -m tools.weiqi101 discover-book-ids --book-id 197 --output my-book-ids.jsonl
```

**book-ids.jsonl record format:**

```jsonl
{"book_id": 197, "book_name": "吴清源诘棋", "book_name_en": "Wu Qingyuan Tsumego", "difficulty": "2D", "puzzle_count": 1630, "view_count": 84521, "like_count": 312, "finish_count": 47, "puzzle_ids": [45001, 45002, ...], "discovered_at": "2026-03-15T12:00:00+00:00"}
```

| Field | Description |
|---|---|
| `book_id` | Numeric book ID on 101weiqi.com |
| `book_name` | Original Chinese title |
| `book_name_en` | English translation (auto-generated) |
| `difficulty` | Difficulty label from the site (e.g. `"2D"`, `"3K"`) |
| `puzzle_count` | Number of puzzle IDs in this record |
| `view_count` | Page views / attempts (0 if not available in page JS) |
| `like_count` | Likes / bookmarks (0 if not available) |
| `finish_count` | Users who completed all puzzles in the book (0 if n/a) |
| `puzzle_ids` | Ordered list of puzzle IDs (difficulty order from site) |
| `discovered_at` | ISO 8601 timestamp of when this record was scraped |

**Using book-ids.jsonl to drive downloads:**

The file is designed to feed directly into `puzzle --book-id`:

```bash
# Read the queue and download each book in order
python -c "
import json, subprocess, sys
for line in open('external-sources/101weiqi/book-ids.jsonl'):
    b = json.loads(line)
    print(f'Downloading book {b[\"book_id\"]}: {b[\"book_name_en\"]} ({b[\"puzzle_count\"]} puzzles)')
    subprocess.run([sys.executable, '-m', 'tools.weiqi101', 'puzzle',
                    '--book-id', str(b['book_id']), '--resume'])
"
```

## Output Structure

```
external-sources/101weiqi/
├── discovery-catalog.json     # All books, tags, categories (from discover-books)
├── book-ids.jsonl             # Per-book puzzle ID lists & metadata (from discover-book-ids)
│
├── sgf/                       # Daily/ID-range downloads (shared batches)
│   ├── batch-001/
│   │   ├── 78000.sgf
│   │   ├── 78001.sgf
│   │   └── ...
│   └── batch-002/
│       └── ...
│
├── books/                     # Per-book downloads (puzzle --book-id N)
│   ├── book-197/
│   │   ├── sgf/
│   │   │   └── batch-001/
│   │   ├── sgf-index.txt
│   │   └── .checkpoint.json
│   └── book-201/
│       └── ...
│
├── logs/
│   └── YYYYMMDD-HHMMSS-101weiqi.jsonl
├── sgf-index.txt              # All IDs in the sgf/ pool (for dedup)
└── .checkpoint.json           # Resume state for sgf/ pool
```

## SGF Properties

Each downloaded SGF includes:

| Property     | Content                                                         | Source                           |
| ------------ | --------------------------------------------------------------- | -------------------------------- |
| `FF[4]`      | SGF file format version                                         | Mandatory                        |
| `GM[1]`      | Game type (Go)                                                  | Mandatory                        |
| `CA[UTF-8]`  | Character encoding                                              | Mandatory                        |
| `SZ[N]`      | Board size (5–19)                                               | `qqdata.boardsize`               |
| `PL[B/W]`    | Player to move first                                            | `qqdata.firsthand`               |
| `AB[..]`     | Black setup stones                                              | `qqdata.c` (decoded), fallback `prepos[0]` |
| `AW[..]`     | White setup stones                                              | `qqdata.c` (decoded), fallback `prepos[1]` |
| `YG[..]`     | YenGo level slug (mapped from Chinese kyu/dan, **calibrated**)  | `qqdata.levelname` → `levels.py` + `_local_levels_mapping.json` |
| `YT[..]`     | YenGo tag (mapped from Chinese puzzle category)                 | `qqdata.qtypename` → `tags.py`   |
| `YX[..]`     | Complexity metrics: `d:depth;r:nodes;s:sol_len;u:unique;w:wrong`| Computed from `qqdata.andata`    |
| `YL[..]`     | Collection membership (v14: supports `slug:CHAPTER/POSITION` sequence) | `qtypename` → `_local_collections_mapping.json` |
| `YM[..]`     | Pipeline metadata: trace_id + original filename for traceability| Auto-generated per puzzle        |
| `C[..]`      | Root: puzzle intent (e.g., "Black to live or kill")             | `qtypename` → `_local_intent_mapping.py` |
| `C[..]`      | Move: `Correct`/`Wrong` on solution tree leaves                | `qqdata.andata` o/f flags        |

**Excluded** (set by pipeline publish stage, NOT by this tool): `GN[]`, `YQ[]`, `YV[]`

### Example SGF Output

```sgf
(;FF[4]GM[1]CA[UTF-8]
SZ[19]
YG[beginner]
YT[life-and-death]
YX[d:2;r:5;s:1;u:3;w:2]
YL[life-and-death]
YM[{"t":"a1b2c3d4e5f67890","f":"78000.sgf"}]
PL[B]
C[Black to live or kill]
AB[rb][qb][qa][pb][ob]
AW[sd][sc][rd]
(;B[sb]C[Correct])
(;B[sa]C[Wrong];W[sb]C[Wrong])
(;B[ra]C[Wrong];W[sb]C[Wrong])
)
```

### YX[] Complexity Metrics

Computed from the `andata` solution tree at ingest time.

| Sub-field | Meaning            | Example | Derivation                               |
| --------- | ------------------ | ------- | ---------------------------------------- |
| `d`       | Max depth          | `2`     | Longest path from root to any leaf       |
| `r`       | Total reading nodes| `5`     | Count of nodes with a move coordinate    |
| `s`       | Solution length    | `1`     | Moves along the main correct line        |
| `u`       | Unique first moves | `3`     | Distinct children of the root node       |
| `w`       | Wrong first moves  | `2`     | First moves leading only to failure      |

## Level Mapping (Calibrated)

101weiqi uses a Chinese rating system where kyu ranks are approximately **10 stones weaker** than their international equivalents. This tool applies a `kyu_offset: 10` calibration before mapping to YenGo levels.

Configuration: `_local_levels_mapping.json` (kyu_offset=10, dan_offset=0)

| 101weiqi Rank | Calibrated Rank | YenGo Level          |
| ------------- | --------------- | -------------------- |
| 20K–16K       | 30K–26K         | novice               |
| 15K–11K       | 25K–21K         | beginner             |
| 10K–6K        | 20K–16K         | elementary           |
| 5K–1K         | 15K–11K         | intermediate         |
| *(n/a)*       | 10K–6K          | upper-intermediate   |
| *(n/a)*       | 5K–1K           | advanced             |
| 1D–3D         | 1D–3D (no offset)| low-dan             |
| 4D–6D         | 4D–6D           | high-dan             |
| 7D–9D / Pro   | 7D–9D           | expert               |

> **Note**: Dan ranks are not calibrated (dan_offset=0) as they roughly align between Chinese and international systems. Kyu ranks above 20K are clamped to 30K (novice).

## Tag Mapping

### Primary Categories (from `qqdata.qtypename`)

| 101weiqi Category | YenGo Tag          |
| ----------------- | ------------------ |
| 死活题             | life-and-death     |
| 手筋              | tesuji             |
| 布局              | fuseki             |
| 定式              | joseki             |
| 官子              | endgame            |
| 对杀 / 对杀题      | capture-race       |
| 综合              | *(unmapped — too generic)* |
| 中盘              | *(unmapped — too broad)*   |

### Additional Categories (from `/questionlib/` URL paths)

Discovered via website scraping and validated by 1p professional Go player review.

| 101weiqi Category | URL Slug     | YenGo Tag          | Rationale                                                    |
| ----------------- | ------------ | ------------------ | ------------------------------------------------------------ |
| 吃子              | `chizi`      | *(unmapped)*       | NOT capture-race! Involves ladder/net/snapback — pipeline detects sub-technique |
| 骗招              | `pianzhao`   | tesuji             | Trick-move puzzles; closest canonical match                  |
| 实战              | `shizhan`    | *(unmapped)*       | Real game positions — too broad for a single tag             |
| 棋理              | `qili`       | *(unmapped)*       | Go theory/principles — pipeline tagger decides               |
| 模仿              | `clone`      | *(unmapped)*       | Imitation puzzles — needs live sampling before committing    |

> **⚠️ Critical**: 吃子 ("capture the stones") must NOT be mapped to `capture-race`. Capture involves
> individual stone capture techniques (ladder, net, snapback), while 对杀/capture-race is semeai
> (two groups racing for liberties). Conflating them produces miscalibrated tags.

Source: `tags.py` — static mapping from `qtypename` field.

## Intent Mapping (Root C[] Comment)

Resolves the Chinese puzzle category to an English intent description for the root `C[]` property.
Uses `{player}` template substituted with "Black"/"White" based on `firsthand`.

| 101weiqi Category  | English Intent Template                            |
| ------------------ | -------------------------------------------------- |
| 死活题              | `{player} to live or kill`                         |
| 手筋               | `{player} to find the tesuji`                      |
| 布局               | `{player} to find the best opening move`           |
| 定式               | `{player} to find the correct joseki`              |
| 官子               | `{player} to find the best endgame move`           |
| 对杀 / 对杀题       | `{player} to win the capturing race`               |
| 综合               | *(None — too generic, pipeline tagger decides)*    |
| 中盘               | `{player} to find the best middle game move`       |
| 吃子               | `{player} to capture the stones`                   |
| 骗招               | `{player} to find the trap move`                   |
| 实战               | `{player} to find the best move`                   |
| 棋理               | `{player} to find the correct move`                |
| 模仿               | *(not mapped — needs live puzzle sampling)*         |

Source: `_local_intent_mapping.py` — static mapping with `resolve_intent(type_name, player_to_move)`.

## Collection Mapping (YL[] Property)

Maps `qtypename` to YenGo collection slugs for the `YL[]` property at ingest time.

| 101weiqi Category  | YenGo Collection Slug   |
| ------------------ | ----------------------- |
| 死活题              | `life-and-death`        |
| 手筋               | `tesuji-problems`       |
| 布局               | `opening-problems`      |
| 定式               | `joseki-problems`       |
| 官子               | `endgame-problems`      |
| 对杀 / 对杀题       | `capturing-race`        |
| 综合               | `general-practice`      |
| 中盘               | `general-practice`      |
| 吃子               | `capture-problems`      |
| 骗招               | `tesuji-problems`       |
| 实战               | `general-practice`      |
| 棋理               | `general-practice`      |
| 模仿               | `general-practice`      |

Source: `_local_collections_mapping.json` (v2.0.0) — static JSON config loaded by `_local_collections_mapping.py`.

### Collection Discovery

The `discover-books` CLI command performs BFS discovery of the website's book catalog using the `discover.py` module. The site uses AngularJS and embeds data as JavaScript variables (`var books = [...]`, `var tags = [...]`) which the parser extracts via brace-matching JSON extraction.

**Website statistics** (as of 2026-03-15, from live discovery run):

| Metric              | Count     | Source                 |
| ------------------- | --------- | ---------------------- |
| Active puzzles      | 181,101   | `/status/` page        |
| Pending puzzles     | ~214,032  | `/status/` page        |
| Retired puzzles     | ~79,311   | `/status/` page        |
| Unique books        | 201       | BFS through 58 tags    |
| Book tags           | 58        | `/book/` main page     |
| Total book puzzles  | 83,119    | Sum across all books   |
| Puzzle categories   | 7         | `/question/{slug}/`    |

**Discovery output**: `external-sources/101weiqi/discovery-catalog.json`

**Top 10 books by puzzle count:**

| Book ID | Name                             | Puzzles | Difficulty |
| ------- | -------------------------------- | ------- | ---------- |
| 36030   | C哥鋒哥詰棋集 (Chen Xi)          | 20,265  | 3K         |
| 201     | 诘棋名家专著                      | 12,888  | 2D         |
| 27533   | 银冈棋院全局官子习题集             | 2,627   | 4K         |
| 3659    | 银冈棋院官子手筋习题集             | 2,050   | 2K+        |
| 924     | 官子                             | 1,746   | 1D         |
| 197     | 吴清源诘棋                        | 1,630   | 2D         |
| 28513   | 詰棋之神 前田陈尔                  | 1,473   | 1K         |
| 28499   | 詰棋皇帝 桥本宇太郎               | 1,384   | 1D+        |
| 6       | 官子谱 (吴清源解说)                | 1,320   | 1D+        |
| 28406   | 东野弘昭诘棋                      | 1,169   | 1D         |

**Top book tags:**

| Tag ID | Name           | Books | Notes                                      |
| ------ | -------------- | ----- | ------------------------------------------ |
| 2      | 棋友原创       | 23    | User-created collections                   |
| 43     | 赵治勋         | 13    | Cho Chikun collections                     |
| 38     | 权甲龙道场     | 12    | Training school collections                |
| 1      | 古典棋书       | 11    | Classical Go books (玄玄棋経, 発陽論, etc.) |
| 6      | 桥本宇太郎     | 11    | Hashimoto Utaro collections                |
| 3      | 吴清源         | 10    | Go Seigen collections                      |
| 42     | 诘棋120系列    | 10    | Death/life series, ~120 puzzles each       |

**Category page volumes** (live, as of 2026-03-15):

| Category | Slug       | Pages | Est. Puzzles |
| -------- | ---------- | ----- | ------------ |
| 官子     | `guanzi`   | 206   | ~4,120       |
| 吃子     | `chizi`    | 200   | ~4,000       |
| 布局     | `buju`     | 99    | ~1,980       |
| 棋理     | `qili`     | 74    | ~1,480       |
| 中盘     | `zhongpan` | 39    | ~780         |
| 骗招     | `pianzhao` | 1     | ~20          |
| 实战     | `shizhan`  | 1     | ~20          |

> **Note**: 官子 (endgame) overtook 吃子 (capture) as the largest category with 206 pages.
> Run `discover-categories` for current live counts.

**URL patterns discovered:**

| Pattern                         | Content                              | Example                          |
| ------------------------------- | ------------------------------------ | -------------------------------- |
| `/book/`                        | Book catalog with tag sidebar        | Main browsing page               |
| `/book/{book_id}/`              | Individual book: puzzles, difficulty | `/book/26378/`                   |
| `/book/tag/{tag_id}/`           | Books filtered by tag                | `/book/tag/42/` (诘棋120系列)    |
| `/book/levelorder/{book_id}/`   | Book puzzles ordered by difficulty   | `/book/levelorder/26378/`        |
| `/question/{slug}/`             | Category listing with pagination     | `/question/chizi/`               |
| `/question/{slug}/?page={N}`    | Paginated category listing           | `/question/chizi/?page=200`      |

**1p professional priority ranking** (classical books):
1. 玄玄棋経 (Xuan Xuan Qi Jing) — most pedagogically valuable
2. 棋経衆妙 (Kikyō Shūmyō)
3. 発陽論 (Hatsuyo Ron)
4. 官子譜 (Guanzi Pu)
5. 死活妙機 (Shikatsu Myōki)

**Known collection signals in `qqdata`:**

| Field       | Type       | Description                                | Example                         |
| ----------- | ---------- | ------------------------------------------ | ------------------------------- |
| `bookinfos` | list[dict] | Book metadata (sparse — often empty)       | `[{"book_id": 123, "name": "..."}]` |
| `leiid`     | int        | Series/collection numeric ID               | `42` (0 if not in a series)     |
| `taotaiid`  | int        | Elimination series ID                      | `0`                             |
| `hasbook`   | bool       | Whether this puzzle belongs to a book      | `true`                          |

**Puzzle count estimates by source mode:**

| Source Mode | Estimated Volume         | Notes                                    |
| ----------- | ------------------------ | ---------------------------------------- |
| Daily       | ~2,920/year             | Fixed 8 puzzles x 365 days               |
| Puzzle-by-ID| 50,000-100,000+         | IDs exist up to >100k; sequential probe  |
| Books       | 83,119 (201 books)      | Ranges from 10 to 20,265 per book        |
| Categories  | ~12,400                 | Sum of 7 categories (~20 puzzles/page)   |

## Resilience Features

- **Checkpoint/resume**: Saves progress to `.checkpoint.json` after each batch. Use `--resume` to continue.
- **Rate limiting with jitter**: `delay = base + (base × 0.5 × random)` — 3.0s base delay (configurable via `--puzzle-delay`).
- **Exponential backoff**: On 429/5xx responses — 30s base, 2× multiplier, max 240s, up to 5 retries.
- **Idempotent**: Deduplicates via `sgf-index.txt`; re-running skips already-downloaded puzzles.
- **Consecutive failure limit**: Stops after 5 consecutive errors (likely indicates source issue).
- **SIGINT handling**: Graceful shutdown on Ctrl+C, saves checkpoint before exit.

## qqdata JSON Structure

Every puzzle page embeds a `var qqdata = {...}` JavaScript object. The extractor parses this via
regex + brace matching (not a JS engine). Key fields:

```json
{
  "publicid": 78000,          // Puzzle numeric ID
  "lu": 19,                   // Board size (路 = lines), 5–19
  "blackfirst": true,         // Side to move (true=black, false=white)
  "ru": 1,                    // Resource type (1=puzzle /q/, 2=chessmanual)
  "levelname": "13K+",        // Chinese kyu/dan string
  "qtypename": "死活题",       // Chinese puzzle category
  "qtype": 1,                 // Numeric category ID
  "content": "amsTQlYQ...",   // XOR-encoded COMPLETE board position (PRIMARY source)
  "prepos": [["pd","pe"], ["oc","oe"]],  // PARTIAL subset only — fallback
  "c": "amsTUUER...",         // XOR-encoded transformed position (NOT used for rendering)
  "andata": { "0": { "pt": "pd", "o": 1, "f": 0, "subs": [1,2] } },
  "ok_answers": [["od"]],     // Correct first-move sequences
  "fail_answers": [["pc","od"]],  // Wrong-path sequences
  "taskresult": { "ok_total": 11112, "fail_total": 5345 },
  "vote": 5.0,
  "bookinfos": [],
  "leiid": 0,
  "taotaiid": 0,
  "hasbook": false
}
```

### Content field decode chain (from production JS)

The site's JS bundle (`ca3b6e99...js`) decodes the `content` field before board init:

```
QipanAPI.buildTimu101 → test123(qqdata) → test202(encoded, key)
```

**Key derivation** (from `ru` field):
```
base   = atob("MTAx") = "101"
suffix = ru + 1                         // 2 for ru=1, 3 for ru=2
key    = base + suffix + suffix + suffix  // "101222" or "101333"
```

**test202** (XOR decode):
1. Base64-decode the encoded string
2. XOR each byte with the key (cycling through key bytes)
3. JSON.parse the result → `[[black_coords], [white_coords]]`

**buildInitGameData** reads: `{ ab: qqdata.content[0], aw: qqdata.content[1] }`

**Fields decoded by test123**: `content`, `ok_answers`, `change_answers`, `fail_answers`, `clone_pos`, `clone_prepos`

**Fields NOT encoded**: `andata` (solution tree), `prepos` (partial stones), `answers` (flat answer list)

### Field roles

| Field | Encoding | Role | Stone count |
|-------|----------|------|-------------|
| `content` | XOR + base64 (ru-dependent key) | **Primary**: complete canonical board position | Full (e.g., 31 stones) |
| `c` | XOR + base64 (opposite key) | Transformed/flipped position — NOT used for rendering | Full but different coords |
| `prepos` | Plain JSON | Legacy fallback — partial subset only | Partial (e.g., 8 stones) |
| `andata` | Plain JSON | Solution tree (nodes with `pt`, `o`, `f`, `subs`) | N/A |

### Additional fields

- `boardsize` — explicit board size (some sources use this instead of `lu`)
- `firsthand` (int) — alternative to `blackfirst` (bool): 1=black, 2=white
- `psm.prepos` — fallback setup stones when `prepos` is empty
- `xv` field — board transformation flag (`xv % 3 != 0` → flip for display variety)
- `answers` array — flat alternative to hierarchical `andata`: `{"ty": 1}` (correct) / `{"ty": 3}` (failure)

## Module Structure

| Module                          | Purpose                                               |
| ------------------------------- | ----------------------------------------------------- |
| `__main__.py`                   | CLI entry point (argparse with subcommands)           |
| `orchestrator.py`               | Download coordination (daily/puzzle modes)            |
| `client.py`                     | HTTP client (`httpx` with retry/backoff)              |
| `extractor.py`                  | Extract `qqdata` JSON from HTML pages                 |
| `models.py`                     | `PuzzleData` + `SolutionNode` dataclasses             |
| `converter.py`                  | Convert `PuzzleData` → SGF string                     |
| `complexity.py`                 | Compute YX[] metrics from solution tree               |
| `_local_intent_mapping.py`      | Chinese category → English intent for root C[]        |
| `_local_collections_mapping.py` | Chinese category → YenGo collection slug for YL[]     |
| `_local_collections_mapping.json` | Static JSON config for collection slug mappings     |
| `levels.py`                     | Chinese kyu/dan → YenGo level slug mapping            |
| `tags.py`                       | Chinese category → YenGo tag mapping                  |
| `validator.py`                  | Validate puzzle structure before saving               |
| `storage.py`                    | Save SGF to batch directory + update index            |
| `checkpoint.py`                 | `WeiQiCheckpoint` (extends `tools.core.checkpoint`)   |
| `batching.py`                   | Batch directory management (via `tools.core.batching`) |
| `index.py`                      | Index file I/O (via `tools.core.index`)               |
| `logging_config.py`             | Structured logging setup (via `tools.core.logging`)   |
| `config.py`                     | Constants, defaults, path helpers                     |
| `discover.py`                   | BFS discovery: books, tags, categories, per-book puzzle IDs |

## Running Tests

```bash
# All tests (221 tests)
python -m pytest tools/weiqi101/tests/ -v

# Quick summary
python -m pytest tools/weiqi101/tests/ -q --no-header
```

## See Also

- [RESEARCH.md](RESEARCH.md) — Detailed research document with data model analysis, URL patterns, and architecture decisions
- `tools/101weiqi/` — Original prototype (kept for reference)
- `tools/ogs/` — OGS tool (similar architecture, used as template)
- `tools/core/` — Shared infrastructure used by this tool

*Last Updated: 2026-03-15 (added discover-book-ids, book-ids.jsonl, capabilities overview, orchestration guide)*
