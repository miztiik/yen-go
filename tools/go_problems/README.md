# GoProblems Puzzle Downloader & Collections Processor

Standalone tool to download Go tsumego puzzles from [GoProblems.com](https://www.goproblems.com) and process their collections through a scoring and bootstrap pipeline.

## Features

### Puzzle Downloader

- **ID range fetch**: Download puzzles by ID range (`--start-id N --end-id M`)
- **Specific IDs**: Download specific puzzles (`--ids 42,100,250`)
- **Paginated listing**: Discover puzzles via API listing (`--list`)
- **Checkpoint/resume**: Resume interrupted downloads with `--resume`
- **SGF enrichment**: Injected YenGo properties (`YV`, `YG`, `YT`, `YL`, `YQ`)
- **Level mapping**: GoProblems rank -> YenGo 9-level system
- **Tag mapping**: Genre -> YenGo tags
- **Collection matching**: `YL[]` slugs via phrase matching against `config/collections.json`
- **Quality scoring**: `YQ[]` from stars/votes/isCanon
- **Batch organization**: 1000 files per batch directory
- **Index tracking**: `sgf-index.txt` for duplicate prevention

### Collections Pipeline (3-stage)

- **Explore**: Discover collections via Collections API (`/api/collections`), with optional per-puzzle enrichment for quality stats
- **Sort**: Score collections using adaptive formulas (full 4-component for enriched, content+group for API-only) and assign quality tiers
- **Bootstrap**: Generate `config/collections.json` entries for unmatched collections

## Usage

```bash
# From project root:

# --- Puzzle Downloader ---
python -m tools.go_problems --help
python -m tools.go_problems --start-id 1 --end-id 5000 --resume
python -m tools.go_problems --ids 42,100,250
python -m tools.go_problems --list --max-puzzles 500

# --- Collections Pipeline ---
# Step 1: Discover collections via API (3 requests, fast)
python -m tools.go_problems.explore_collections -v

# Step 1 (hybrid): API discovery + enrichment from downloaded puzzles
python -m tools.go_problems.explore_collections \
    --enrich-ids external-sources/goproblems/sgf-index.txt \
    --enrich-sample 500 -v

# Step 2: Score and assign tiers
python -m tools.go_problems.sort_collections -i reports/collections.jsonl -v

# Step 3: Bootstrap config entries
python -m tools.go_problems.bootstrap_collections -i reports/collections-sorted.jsonl --dry-run
```

## Output Structure

```
external-sources/goproblems/
├── sgf/
│   ├── batch-001/
│   │   ├── 42.sgf
│   │   ├── 100.sgf
│   │   └── ... (up to 1000 files)
│   └── batch-NNN/
├── reports/
│   ├── YYYYMMDD-HHMMSS-collections.jsonl       (from explore)
│   └── YYYYMMDD-HHMMSS-collections-sorted.jsonl (from sort)
├── logs/
│   └── go-problems-download-YYYYMMDD_HHMMSS.jsonl
├── sgf-index.txt
├── .checkpoint.json
├── .explore-checkpoint.json
└── README.md
```

## GoProblems API Fields & SGF Mapping

The GoProblems `/api/v2/problems/{id}` endpoint returns puzzle details including the raw SGF and metadata. This table documents what is stored and what is discarded.

| API field                       | Stored in SGF? | SGF property  | Notes                                           |
| ------------------------------- | -------------- | ------------- | ----------------------------------------------- |
| `sgf`                           | Yes            | (entire root) | Raw SGF content, enriched with YenGo properties |
| `playerColor`                   | Yes            | `PL[B\|W]`    | Player to move; `null` defaults to Black        |
| `rank.value` + `rank.unit`      | Yes            | `YG[]`        | Mapped to 9-level slug via `levels.py`          |
| `genre`                         | Yes            | `YT[]`        | Mapped to canonical tags via `tags.py`          |
| `rating.stars` + `rating.votes` | Yes            | `YQ[]`        | Quality score from stars/votes/isCanon          |
| `isCanon`                       | Yes            | `YQ[]`        | Canonical status included in quality scoring    |
| `collections[].name`            | Yes            | `YL[]`        | Matched against `config/collections.json`       |
| `id`                            | As filename    | `{id}.sgf`    | Unique identifier; also in `sgf-index.txt`      |
| `problemLevel`                  | Yes            | `YG[]`        | Fallback difficulty signal when rank is missing |
| `source`                        | No             | --            | Author attribution (not needed for SGF)         |
| `collections[].id`              | No             | --            | Used only during collection discovery           |

## SGF Enrichment Algorithm

Each GoProblems puzzle SGF is enriched through the following steps:

1. **Strip existing root properties**: Remove `GM`, `FF`, `CA`, `RU`, `SY`, `DT`, `SO`, `AP`, `ST`, `KM`, `GN`, `TM`, and root `C[]` (move `C[]` preserved)
2. **Inject standard headers**: `FF[4]GM[1]CA[UTF-8]`
3. **Inject YenGo version**: `YV[10]`
4. **Inject difficulty level**: `YG[intermediate]` (from rank mapping)
5. **Inject tags**: `YT[life-and-death,tesuji]` (sorted, deduplicated)
6. **Inject player to move**: `PL[B]` or `PL[W]` (not duplicated if already present)
7. **Inject quality score**: `YQ[q:4;rc:0;hc:0]`
8. **Inject collections**: `YL[cho-chikun,essential-life-and-death]` (if `--match-collections`)
9. **Inject root comment**: `C[life-and-death-black-live]` (resolved objective slug)

### Solution Depth Validation

Solution depth is computed using `tools.core.sgf_parser` (tree-based, NOT regex).
The tree parser counts the maximum depth of any single path, not the sum of all
nodes across all branches. `--max-depth` is now properly propagated through to
the validator.

### YL Collection Match Logging

After resolving collection slugs, matched slugs are logged at INFO level per puzzle.
If a puzzle belongs to collections on GoProblems but none matched our config, a
WARNING is logged with the unmatched collection names.

### Intent Resolution Logging

Matched intent slugs and confidence are logged at INFO level. No-match and
below-threshold results are logged at DEBUG level.

## Level Mapping

GoProblems uses two difficulty signals: `rank` (kyu/dan with value) and `problemLevel` (1-50+ scale). Both are mapped to YenGo's 9-level system:

### From rank (primary)

| rank.value + rank.unit | Go Rank | YenGo Level          |
| ---------------------- | ------- | -------------------- |
| 25+ kyu                | 25k+    | `novice`             |
| 20-24 kyu              | 20-24k  | `beginner`           |
| 15-19 kyu              | 15-19k  | `elementary`         |
| 10-14 kyu              | 10-14k  | `intermediate`       |
| 5-9 kyu                | 5-9k    | `upper-intermediate` |
| 1-4 kyu                | 1-4k    | `advanced`           |
| 1-3 dan                | 1-3d    | `low-dan`            |
| 4-6 dan                | 4-6d    | `high-dan`           |
| 7+ dan                 | 7d+     | `expert`             |

### From problemLevel (fallback)

| problemLevel | YenGo Level          |
| ------------ | -------------------- |
| 1-5          | `novice`             |
| 6-10         | `beginner`           |
| 11-15        | `elementary`         |
| 16-20        | `intermediate`       |
| 21-25        | `upper-intermediate` |
| 26-30        | `advanced`           |
| 31-35        | `low-dan`            |
| 36-40        | `high-dan`           |
| 41+          | `expert`             |

## Tag Mapping

GoProblems `genre` field is mapped to YenGo tags:

| GoProblems genre | YenGo tag        | Notes                     |
| ---------------- | ---------------- | ------------------------- |
| `life and death` | `life-and-death` | Core tsumego objective    |
| `tesuji`         | `tesuji`         | General tactical move     |
| `joseki`         | `joseki`         | Standard corner sequences |
| `fuseki`         | `fuseki`         | Opening patterns          |
| `endgame`        | `endgame`        | Late-game yose techniques |
| `best move`      | `best-move`      | Best local move           |
| `other`          | (not mapped)     | Unclassified              |

## Quality Score (YQ)

YQ is computed from GoProblems rating data:

```
base_score = clamp(stars, 0, 5)   # Direct star rating
canon_bonus = 1 if isCanon else 0  # Canonical puzzle bonus
quality = min(5, base_score + canon_bonus)
```

Format: `YQ[q:{quality};rc:0;hc:0]`

## Collections Discovery Algorithm

GoProblems has a Collections API at `GET /api/collections?offset=N&limit=M` that returns all collections in a few paginated requests (max limit 100, ~259 total collections).

### Collections API Response

```json
{
  "entries": [
    {
      "id": 18,
      "name": "Semeai / Capturing Race",
      "description": "...",
      "group": "Style",
      "numberOfProblems": 2546,
      "privacy": "public",
      "author": { "id": 1, "name": "admin", "rank": "9d" },
      "createdAt": "2003-05-24T09:11:07+00:00"
    }
  ],
  "totalRecords": 259
}
```

**Key fields:**

- `group`: `"Style"` (curated/themed by admins) or `"Collection"` (user-created)
- `numberOfProblems`: Authoritative puzzle count
- `author`: Creator info

### Discovery Process

1. **API discovery** (always, ~3 requests): Paginate `/api/collections` to get all collections with their names, puzzle counts, groups, authors, and descriptions
2. **Optional enrichment** (`--enrich-ids`): Scan individual puzzle detail responses (`/api/v2/problems/{id}`) to add per-puzzle stats (avg_stars, avg_votes, canon_count, genre_distribution)
3. **Output**: Write JSONL (metadata header + one collection record per line)

The API provides collection-level metadata but no per-puzzle quality stats. Enrichment fills this gap by fetching individual puzzle details and accumulating ratings, canon status, and genre data.

### What Each Mode Provides

| Signal                   | API-only | Hybrid (enriched) |
| ------------------------ | -------- | ----------------- |
| Name, ID, puzzle count   | Yes      | Yes               |
| Group (Style/Collection) | Yes      | Yes               |
| Author, description      | Yes      | Yes               |
| avg_stars, avg_votes     | No       | Yes               |
| canon_count/ratio        | No       | Yes               |
| genre_distribution       | No       | Yes               |

### Why not use `?collection={id}` filter?

The GoProblems API has a `?collection={id}` query parameter, but testing revealed it's unreliable:

- Returns results for non-existent collection IDs
- Pagination doesn't work (page 2 returns same results as page 1)
- Caps at 50 results per collection regardless of actual size

## Collections Processing Pipeline

```
GoProblems Collections API (/api/collections)
    |  3 requests, ~259 collections
    v
[explore_collections.py] -- API discovery
    |          \
    |           +-- Optional: --enrich-ids sgf-index.txt
    |               scans puzzle details (/api/v2/problems/{id})
    |               adds avg_stars, avg_votes, canon, genre stats
    v
reports/YYYYMMDD-HHMMSS-collections.jsonl
    |
    v
[sort_collections.py]
    | adaptive scoring:
    |   enriched -> full 4-component Bayesian formula
    |   API-only -> content + group score
    | percentile-based tier assignment
    v
reports/YYYYMMDD-HHMMSS-collections-sorted.jsonl
    |
    v
[bootstrap_collections.py]
    | match vs config/collections.json
    | generate entries for unmatched premier+curated
    | CJK normalization via tools.core.text
    v
config/collections-proposed-goproblems.json  (human review & merge)
```

### Scoring Formulas

The sorter uses adaptive scoring based on data availability:

#### Full Formula (enriched collections)

Used when per-puzzle stats are available (via `--enrich-ids`):

```
priority_score = (
    0.35 * bayesian_quality_norm +    # Confidence-adjusted avg stars
    0.25 * engagement_norm +          # log(avg_votes+1) / log(max+1)
    0.20 * canon_ratio +              # canonical / total puzzles
    0.20 * content_norm               # log2(puzzle_count+1) / log2(max+1)
) * size_multiplier
```

**Components:**

- **Bayesian quality** (35%): `(avg_stars * rated_count + global_mean * C) / (rated_count + C)`, normalized to [0,1] via `(bayesian - 1.0) / 4.0`. Prevents single high ratings from dominating.
- **Engagement** (25%): `log10(avg_votes + 1) / log10(max_avg_votes + 1)`. Uses average votes per puzzle as a proxy for popularity.
- **Canon ratio** (20%): `canon_count / puzzle_count`. Already 0-1, measures community vetting.
- **Content** (20%): `log2(puzzle_count + 1) / log2(max_puzzle_count + 1)`. Log-scaled to prevent very large collections from dominating.

#### API-Only Formula (non-enriched collections)

Used when only Collections API data is available (no per-puzzle stats):

```
priority_score = (
    0.70 * content_norm +             # log2(numberOfProblems+1) / log2(max+1)
    0.30 * group_score                # Style=0.8, Collection=0.3, unknown=0.1
) * size_multiplier
```

**Components:**

- **Content** (70%): Same log-scaled puzzle count formula. The dominant signal since it's the only quantitative metric from the API.
- **Group bonus** (30%): `"Style"` collections (curated/themed) receive 0.8, `"Collection"` (user-created) receives 0.3, unknown group receives 0.1.

#### Size Multiplier (both formulas)

- < 3 puzzles: 0.3
- < 5 puzzles: 0.5
- < 10 puzzles: 0.8
- > = 10 puzzles: 1.0

### Quality Tiers

Tiers are assigned by percentile rank after sorting by priority_score:

| Percentile | Tier        | Description                                   |
| ---------- | ----------- | --------------------------------------------- |
| Top 10%    | `premier`   | Highest-quality, well-established collections |
| 10-30%     | `curated`   | Good quality, community-vetted                |
| 30-60%     | `community` | Acceptable quality, may need review           |
| Bottom 40% | `unvetted`  | Low quality or insufficient data              |

Only `premier` and `curated` tiers are eligible for automatic bootstrap into `config/collections.json`.

### Text Normalization (Shared)

Collection name normalization uses `tools.core.text` (shared with OGS pipeline):

1. **CJK/special bracket normalization**: `\u3010...\u3011` -> spaces
2. **Bracket suffix removal**: `[username]` stripped
3. **Possessive removal**: `'s` stripped
4. **Leading number removal**: `3. ` prefix stripped
5. **Bilingual extraction**: For names with CJK/Thai/Cyrillic + English, extract the English portion if it contains Go terminology
6. **Slug generation**: `unidecode()` -> lowercase -> kebab-case -> max 64 chars

## Configuration

### Puzzle Downloader

| Option          | Default | Description                               |
| --------------- | ------- | ----------------------------------------- |
| `--start-id`    | --      | Start of puzzle ID range                  |
| `--end-id`      | --      | End of puzzle ID range                    |
| `--ids`         | --      | Comma-separated specific puzzle IDs       |
| `--list`        | false   | Use paginated listing to discover puzzles |
| `--max-puzzles` | --      | Maximum puzzles to download               |
| `--batch-size`  | 1000    | Files per batch directory                 |
| `--delay`       | 7.0s    | Delay between API requests                |
| `--resume`      | false   | Resume from checkpoint                    |
| `--canon-only`  | false   | Download only canonical puzzles           |

### explore_collections

| Option            | Default          | Description                                                   |
| ----------------- | ---------------- | ------------------------------------------------------------- |
| `--output`, `-o`  | auto-timestamped | Output JSONL file path                                        |
| `--enrich-ids`    | --               | File with puzzle IDs for enrichment (sgf-index.txt format)    |
| `--enrich-sample` | all              | When enriching, scan only the first N puzzles                 |
| `--delay`         | 7.0s             | Delay between enrichment API requests                         |
| `--verbose`, `-v` | false            | Enable verbose logging                                        |
| `--input-ids`     | --               | [Deprecated: use `--enrich-ids`] File with puzzle IDs         |
| `--sample`, `-s`  | all              | [Deprecated: use `--enrich-sample`] Scan only first N puzzles |

### sort_collections

| Option            | Default                | Description                   |
| ----------------- | ---------------------- | ----------------------------- |
| `--input`, `-i`   | (required)             | Input JSONL from explore step |
| `--output`, `-o`  | `<input>-sorted.jsonl` | Output JSONL file path        |
| `--verbose`, `-v` | false                  | Enable verbose logging        |

### bootstrap_collections

| Option                | Default                                       | Description                       |
| --------------------- | --------------------------------------------- | --------------------------------- |
| `--input`, `-i`       | (required)                                    | Input sorted JSONL from sort step |
| `--collections`, `-c` | auto-detect                                   | Path to `config/collections.json` |
| `--output`, `-o`      | `config/collections-proposed-goproblems.json` | Output file                       |
| `--dry-run`           | false                                         | Preview without writing           |
| `--verbose`, `-v`     | false                                         | Enable verbose logging            |

## Dependencies

Uses only standard library + packages already in the project:

- `httpx` - HTTP client
- `pydantic` - Data validation
- `unidecode` - Non-Latin character transliteration (for slug generation)
