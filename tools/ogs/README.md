# OGS Puzzle Downloader

Standalone tool to download Go tsumego puzzles from [Online-Go.com (OGS)](https://online-go.com) and store them as SGF files.

## Features

- **Pagination support**: Downloads all available puzzles from OGS API
- **Single page mode**: Download only a specific page with `--page N`
- **Checkpoint/resume**: Interrupted downloads can be resumed with `--resume`
- **Per-file checkpointing**: Checkpoint saved after each file (not per batch)
- **Index file**: `sgf-index.txt` tracks all downloaded files for duplicate prevention
- **Structured logging**: Console + JSON file logging for analysis
- **Rate limiting**: Configurable delays with jitter to respect API limits
- **Backoff on 429**: Automatic exponential backoff when rate-limited
- **Proper solution detection**: Validates puzzles by traversing move tree for `correct_answer` nodes (not the unreliable `has_solution` API field)
- **Level mapping**: Maps OGS `puzzle_rank` to YenGo 9-level system via `YG[]` property
- **Tag embedding**: Maps OGS `puzzle_type` to YenGo tags via `YT[]` property
- **Japanese translation**: Optional translation of Japanese Go terminology
- **Batch organization**: 1000 files per batch directory

## Usage

```bash
# From project root:
python -m tools.ogs --help

# Download up to 5000 puzzles
python -m tools.ogs --max-puzzles 5000

# Resume interrupted download
python -m tools.ogs --resume

# Download a specific page only
python -m tools.ogs --page 10

# Dry run (show what would be downloaded)
python -m tools.ogs --max-puzzles 100 --dry-run

# Custom output directory
python -m tools.ogs --output-dir external-sources/ogs-test

# Verbose logging
python -m tools.ogs --max-puzzles 100 -v

# Analyze download logs
python -m tools.ogs.analyze_logs --summary
python -m tools.ogs.analyze_logs --failures
```

## Output Structure

```
external-sources/ogs/
├── sgf/
│   ├── batch-001/
│   │   ├── 45.sgf
│   │   ├── 1555.sgf
│   │   └── ... (up to 1000 files)
│   ├── batch-002/
│   │   └── ...
│   └── batch-NNN/
├── logs/
│   └── ogs-download-YYYYMMDD_HHMMSS.jsonl
├── sgf-index.txt          # Index of all downloaded files
├── .checkpoint.json
└── README.md
```

## OGS API Fields & SGF Mapping

The OGS `/api/v1/puzzles/{id}/` endpoint returns the following fields. This table
documents what is stored in SGF and what is discarded at ingest time.

| OGS API field                    | Stored in SGF? | SGF property  | Notes                                                                                                                                |
| -------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `puzzle.width` / `puzzle.height` | Yes            | `SZ[]`        | Board size (width assumed = height)                                                                                                  |
| `puzzle.initial_player`          | Yes            | `PL[B\|W]`    | Player to move                                                                                                                       |
| `puzzle.initial_state.black`     | Yes            | `AB[...]`     | Black setup stones                                                                                                                   |
| `puzzle.initial_state.white`     | Yes            | `AW[...]`     | White setup stones                                                                                                                   |
| `puzzle.puzzle_rank`             | Yes            | `YG[]`        | Mapped to 9-level slug via `levels.py`                                                                                               |
| `puzzle.puzzle_type`             | Yes            | `YT[]`        | Mapped to canonical tag via `tags.py`                                                                                                |
| `puzzle.move_tree`               | Yes            | Solution tree | Recursive branches with `C[Correct!]` / `C[Wrong]`                                                                                   |
| `puzzle.move_tree[].text`        | Yes            | `C[]` (move)  | Japanese text translated via `translator.py`                                                                                         |
| `puzzle.puzzle_description`      | Optional       | `C[]` (root)  | Resolved via `puzzle_intent` when `--resolve-intent` enabled                                                                         |
| `collection.name`                | Optional       | `YL[]`        | Matched against `config/collections.json` when `--match-collections` enabled; combined with reverse index from `--collections-jsonl` |
| `id`                             | As filename    | `{id}.sgf`    | Unique identifier; also in `sgf-index.txt`                                                                                           |
| `name`                           | No             | —             | Puzzle title, not pedagogical                                                                                                        |
| `owner.id` / `owner.username`    | No             | —             | Author info, not pedagogical                                                                                                         |
| `created` / `modified`           | No             | —             | Timestamps, not pedagogical                                                                                                          |
| `has_solution`                   | No             | —             | Unreliable; solution detected by tree traversal                                                                                      |
| `puzzle.mode`                    | No             | —             | Always `"puzzle"`                                                                                                                    |

**Discarded but potentially useful** — these fields are dropped at ingest because no
SGF property exists for them yet, but they could inform future heuristics:

- **`puzzle_rank`** (numeric 0-50) — raw difficulty signal (currently only the mapped
  level slug is stored).
- **`rating`** / **`rating_count`** — crowd-sourced puzzle ratings from OGS users;
  absent from the current API response fields we model, but may reappear in extended
  endpoints.
- **`owner`** — could attribute puzzles to prolific authors.
- **`created`** / **`modified`** — age signal; newer puzzles may track current meta.

## SGF Output Rules

Each puzzle is saved with minimal properties per `storage.py` and the project spec
(`config/schemas/sgf-properties.schema.json` v10):

**Included:**

- `FF[4]GM[1]CA[UTF-8]` — SGF format headers
- `SZ[...]` — Board size
- `PL[B]` or `PL[W]` — Player to move
- `AB[...]/AW[...]` — Initial stone positions
- `YG[...]` — Difficulty level mapped from OGS `puzzle_rank` (e.g., `YG[intermediate]`)
- `YT[...]` — Tags mapped from OGS `puzzle_type` + objective parsing (e.g., `YT[life-and-death,living]`)
- `YL[...]` — Collection slugs matched from OGS collections (comma-separated, sorted; optional, `--match-collections`)
- Root `C[...]` — Puzzle objective from `puzzle_description` via `puzzle_intent` (optional, `--resolve-intent`)
- Move comments: `C[Correct!]`/`C[Wrong]` in solution tree

**Excluded (per project spec):**

- `GN[]` — Game name (assigned later by enricher)
- `PC[]` — Place/source (tracked in index)
- `EV[]` — Event/name (not pedagogical)

## Level Mapping

OGS `rank` field (scale 0-50) is mapped to YenGo's 9-level system:

| OGS rank | Go Rank (approx) | YenGo Level          |
| -------- | ---------------- | -------------------- |
| 0-4      | 30k-26k          | `novice`             |
| 5-9      | 25k-21k          | `beginner`           |
| 10-14    | 20k-16k          | `elementary`         |
| 15-19    | 15k-11k          | `intermediate`       |
| 20-24    | 10k-6k           | `upper-intermediate` |
| 25-29    | 5k-1k            | `advanced`           |
| 30-33    | 1d-3d            | `low-dan`            |
| 34-36    | 4d-6d            | `high-dan`           |
| 37+      | 7d+              | `expert`             |

Formula: `go_rank = 30 - ogs_rank` (positive = kyu, negative/zero = dan)

## Tag Mapping

OGS `puzzle_type` is mapped to YenGo tags (all tags valid in `config/tags.json` v6.0):

| OGS puzzle_type  | YenGo tag        | Notes                           |
| ---------------- | ---------------- | ------------------------------- |
| `life_and_death` | `life-and-death` | Core tsumego objective          |
| `tesuji`         | `tesuji`         | General tactical move           |
| `joseki`         | `joseki`         | Standard corner sequences       |
| `fuseki`         | `fuseki`         | Opening patterns                |
| `endgame`        | `endgame`        | Late-game yose techniques       |
| `best_move`      | (not mapped)     | Too generic — let tagger detect |
| `elementary`     | (not mapped)     | Not a technique                 |
| `unknown`        | (not mapped)     | Unclassified                    |

## YL Collections

Collection membership (`YL[]`) can be assigned at download time when `--match-collections`
is enabled. The downloader resolves collections from **two sources**:

1. **API source**: The OGS API returns a `collection` object with a `name` field for each puzzle
2. **Reverse index source**: A pre-built JSONL file mapping puzzle IDs to all collections they belong to (via `--collections-jsonl`)

Both sources are matched against `config/collections.json` using:

1. Exact normalized match (slug, name, or alias)
2. Phrase matching (tokenized contiguous subsequence, longest match wins)

All matched slugs are deduplicated, sorted alphabetically, and written as comma-separated
values in `YL[slug1,slug2,slug3]`. If no match is found from either source, a warning
is logged with the unmatched collection name for future alias addition.

```bash
# Enable collection matching (API source only)
python -m tools.ogs --max-puzzles 100 --match-collections

# Enable multi-collection matching with reverse index
python -m tools.ogs --max-puzzles 100 --match-collections --collections-jsonl external-sources/ogs/20260211-203516-collections-sorted.jsonl

# Combined with intent resolution
python -m tools.ogs --max-puzzles 100 --match-collections --resolve-intent
```

### Bootstrap Collections

The `bootstrap_collections` tool generates new `config/collections.json` entries for
OGS collections that don't have a YenGo match. Only premier and curated quality tiers
(top 30% by the scoring engine in `sort_collections.py`) are eligible.

```bash
# Dry run: preview proposed entries
python -m tools.ogs.bootstrap_collections --input external-sources/ogs/20260211-203516-collections-sorted.jsonl --dry-run

# Generate proposed entries to file
python -m tools.ogs.bootstrap_collections --input external-sources/ogs/20260211-203516-collections-sorted.jsonl --output config/collections-proposed.json

# Verbose logging
python -m tools.ogs.bootstrap_collections --input external-sources/ogs/20260211-203516-collections-sorted.jsonl --dry-run --verbose
```

Output is written to `config/collections-proposed.json` for human review before merging
into `config/collections.json`.

## Intent Resolution

When `--resolve-intent` is enabled, the downloader sends each puzzle's `puzzle_description`
through the `tools.puzzle_intent` resolver to identify the puzzle objective (e.g.,
"LIFE_AND_DEATH.BLACK.KILL"). The result is written as a root `C[]` comment in the SGF.

Matching strategy:

1. Semantic matching via sentence-transformers (if installed)
2. Falls back to deterministic matching (exact + keyword) if semantic is unavailable

The `--intent-threshold` flag (default 0.8) controls the minimum confidence required.

```bash
# Enable intent resolution
python -m tools.ogs --max-puzzles 100 --resolve-intent

# With custom threshold
python -m tools.ogs --max-puzzles 100 --resolve-intent --intent-threshold 0.7
```

## Configuration

| Option                | Default       | Description                                                               |
| --------------------- | ------------- | ------------------------------------------------------------------------- |
| `--max-puzzles`       | 10000         | Maximum puzzles to download                                               |
| `--batch-size`        | 1000          | Files per batch directory                                                 |
| `--page-delay`        | 3.75s         | Delay between page requests                                               |
| `--puzzle-delay`      | 1.25s         | Delay between puzzle requests                                             |
| `--max-depth`         | 50            | Maximum move tree depth                                                   |
| `--resume`            | false         | Resume from checkpoint                                                    |
| `--page`              | -             | Download only this page                                                   |
| `--start-page`        | -             | Start from this page                                                      |
| `--dry-run`           | false         | Preview without downloading                                               |
| `--fetch-objective`   | false         | Fetch puzzle HTML page and parse objective text for extra `YT[]` tags     |
| `--match-collections` | false         | Match OGS collection names to `YL[]` slugs from `config/collections.json` |
| `--collections-jsonl` | auto-discover | Path to sorted collections JSONL for reverse-index YL[] enrichment        |
| `--resolve-intent`    | false         | Resolve `puzzle_description` to objective and write as root `C[]`         |
| `--intent-threshold`  | 0.8           | Minimum confidence for intent resolution                                  |

## Solution Detection Fix

The OGS API has an unreliable `has_solution` field that returns `false` even for puzzles with valid solutions. This tool fixes that by:

1. **Traversing the move tree** to find `correct_answer: true` nodes
2. **Ignoring the `has_solution` metadata** field
3. **Only rejecting puzzles** that truly have no solution in their move tree

This ensures we import all valid puzzles that were previously being incorrectly rejected.

## Logs

Logs are written to `external-sources/ogs/logs/` in JSON Lines format:

```json
{"timestamp": "2026-02-04T...", "level": "INFO", "event_type": "puzzle_save", "data": {"puzzle_id": 45}}
{"timestamp": "2026-02-04T...", "level": "WARNING", "event_type": "puzzle_skip", "data": {"puzzle_id": 123, "reason": "..."}}
```

### Log Analysis Tool

```bash
# Show summary statistics
python -m tools.ogs.analyze_logs --summary

# Show failures and skips
python -m tools.ogs.analyze_logs --failures

# Filter by event type
python -m tools.ogs.analyze_logs --event-type puzzle_save

# Custom logs directory
python -m tools.ogs.analyze_logs --logs-dir external-sources/ogs/logs --summary
```

### Manual Log Analysis

```bash
# Count downloaded puzzles
grep '"event_type": "puzzle_save"' logs/*.jsonl | wc -l

# Find all skipped puzzles
grep '"event_type": "puzzle_skip"' logs/*.jsonl
```

## Quality (YQ) — Pipeline-Computed, No Ingest-Time Enrichment Needed

All OGS quality signals survive the SGF round-trip and are fully recoverable by
the pipeline's `analyze` stage. **No ingest-time YQ computation is required.**

### Signal Preservation

| OGS API Field                 | SGF Representation                            | Pipeline Recovery                                  |
| ----------------------------- | --------------------------------------------- | -------------------------------------------------- |
| `wrong_answer` on move node   | `C[Wrong]` (via `standardize_move_comment()`) | Layer 2 correctness inference → `is_correct=False` |
| `correct_answer` on move node | `C[Correct!]` (via move comment)              | Layer 2 correctness inference → `is_correct=True`  |
| `text` on move node           | Appended to `C[]` comment                     | `compute_comment_level()` → `hc:2` (teaching text) |
| Move tree structure           | Preserved in SGF branches                     | `count_refutation_moves()` → `rc` count            |

Unlike Go Problems (whose crowd signals like `stars`, `votes`, `isCanon` are
ephemeral and lost after download), OGS embeds all quality-relevant data
directly in the move tree structure, which is faithfully serialized to SGF.

### Comment Level Detection

The pipeline's `compute_comment_level()` distinguishes:

- `hc:0` — no comments at all
- `hc:1` — correctness markers only (`C[Correct!]`, `C[Wrong]`, `C[+]`)
- `hc:2` — genuine teaching text beyond bare markers (e.g., `C[Correct! This captures the cutting stones]`)

OGS puzzles with `text` fields containing explanatory content will receive
`hc:2`; those with only `correct_answer`/`wrong_answer` markers get `hc:1`.

## Dependencies

Uses only standard library + packages already in the project:

- `httpx` - HTTP client
- `pydantic` - Data validation

Optional (for `--resolve-intent` with semantic matching):

- `sentence-transformers` - Required by `tools.puzzle_intent` for semantic matching.
  Install with `pip install sentence-transformers` or `pip install -e ".[nlp]"`.
  Falls back to deterministic (exact + keyword) matching if not installed.
