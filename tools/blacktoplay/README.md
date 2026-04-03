# BlackToPlay Puzzle Downloader

Standalone tool to download Go tsumego puzzles from [BlackToPlay.com](https://blacktoplay.com) and store them as SGF files.

_Last updated: 2026-02-25_

## Features

- **Proprietary format conversion**: Decodes BTP's base-59 hash-encoded board positions to standard SGF
- **Full solution trees**: Parses BTP's node strings into branching SGF solution trees with correct/wrong moves
- **Go legality engine**: Self-contained engine for decoding BTP's compressed wrong-move format
- **Three puzzle types**: Classic (1,178), AI-generated (2,121), Endgame (520) — 3,819 total
- **Checkpoint/resume**: Interrupted downloads can be resumed with `--resume`
- **Per-file checkpointing**: Checkpoint saved after every 10 puzzles
- **Index file**: `sgf-index.txt` tracks all downloaded files for duplicate prevention
- **Structured logging**: Console + JSONL file logging
- **Rate limiting**: Configurable delays with ±30% jitter to respect API limits
- **Retry with backoff**: Exponential backoff on 429/5xx/connection errors (3 retries)
- **Level mapping**: Maps BTP 0–3000 rating to YenGo 9-level system via `YG[]`
- **Tag embedding**: Maps BTP's 99 tags to YenGo tags via `YT[]`
- **Collection matching**: Maps BTP's 15 categories (A–O) to YenGo collections via `YL[]`
- **Intent resolution**: Derives puzzle objective text for root `C[]` from categories and tags
- **Cached list fallback**: Falls back to cached puzzle list when live API returns empty
- **Batch organization**: 500 files per batch directory
- **Graceful shutdown**: SIGINT saves checkpoint before exit

## Usage

```bash
# From project root:
python -m tools.blacktoplay --help

# Download up to 100 puzzles (dry run)
python -m tools.blacktoplay --max-puzzles 100 --dry-run

# Download all classic puzzles
python -m tools.blacktoplay --types classic

# Download only AI and endgame puzzles
python -m tools.blacktoplay --types ai endgame

# Resume interrupted download
python -m tools.blacktoplay --resume

# Download all types with verbose logging
python -m tools.blacktoplay --max-puzzles 5000 -v

# Download without collection or intent enrichment
python -m tools.blacktoplay --no-match-collections --no-resolve-intent

# Disable cached puzzle list fallback (live API only)
python -m tools.blacktoplay --no-cache

# Custom output directory
python -m tools.blacktoplay --output-dir external-sources/blacktoplay-test
```

## Configuration

| Option                   | Default                        | Description                                         |
| ------------------------ | ------------------------------ | --------------------------------------------------- |
| `--max-puzzles`          | 10000                          | Maximum puzzles to download                         |
| `--batch-size`           | 500                            | Files per batch directory                           |
| `--puzzle-delay`         | 1.0s                           | Delay between puzzle requests (with ±30% jitter)    |
| `--output-dir`           | `external-sources/blacktoplay` | Output directory                                    |
| `--resume`               | false                          | Resume from checkpoint                              |
| `--dry-run`              | false                          | Preview without downloading                         |
| `--types`                | all                            | Puzzle types: `classic`, `ai`, `endgame`            |
| `--no-cache`             | false                          | Disable cached puzzle list fallback                 |
| `--no-log-file`          | false                          | Disable file logging (console only)                 |
| `--match-collections`    | true                           | Enable YL[] collection matching from BTP categories |
| `--no-match-collections` | —                              | Disable YL[] collection matching                    |
| `--resolve-intent`       | true                           | Enable C[] intent/objective resolution              |
| `--no-resolve-intent`    | —                              | Disable C[] intent resolution                       |
| `--intent-threshold`     | 0.8                            | Minimum confidence for intent match                 |
| `--min-stones`           | config default (2)             | Minimum stones required on board                    |
| `-v` / `--verbose`       | false                          | Enable DEBUG logging                                |

## Output Structure

```
external-sources/blacktoplay/
├── sgf/
│   ├── batch-001/
│   │   ├── btp-1.sgf
│   │   ├── btp-42.sgf
│   │   └── ... (up to 500 files)
│   ├── batch-002/
│   │   └── ...
│   └── batch-NNN/
├── logs/
│   └── btp-download-YYYYMMDD_HHMMSS.jsonl
├── sgf-index.txt          # Index of all downloaded files
└── .checkpoint.json
```

## Enrichment Behavior

By default, **all four enrichment layers are applied** to every downloaded puzzle:

| SGF Prop | Enrichment                                               | Toggle                                           | Default |
| -------- | -------------------------------------------------------- | ------------------------------------------------ | ------- |
| `YG[]`   | Level mapping (BTP rating → 9-level slug)                | Always on                                        | —       |
| `YT[]`   | Tag mapping (BTP tags → YenGo tags)                      | Always on                                        | —       |
| `YL[]`   | Collection matching (BTP categories → YenGo collections) | `--match-collections` / `--no-match-collections` | Enabled |
| `C[]`    | Intent/objective (derived from categories + tags)        | `--resolve-intent` / `--no-resolve-intent`       | Enabled |

Level and tag mapping are always applied (no toggle) because they are essential metadata. Collection and intent enrichment can be disabled for faster downloads or debugging.

## BTP API & Data Format

### Endpoints

| Endpoint        | Method | Purpose                               |
| --------------- | ------ | ------------------------------------- |
| `load_data.php` | POST   | Fetch full puzzle data by ID and type |
| `load_list.php` | POST   | Enumerate all puzzle IDs by type      |

Both endpoints require browser-like headers (`User-Agent`, `Origin`, `Referer`, `X-Requested-With`). BTP blocks requests without these headers.

### Puzzle Types

| Type ID | Name    | Count | Description                   |
| ------- | ------- | ----- | ----------------------------- |
| 0       | Classic | 1,178 | Human-curated tsumego puzzles |
| 1       | AI      | 2,121 | AI-generated puzzles          |
| 2       | Endgame | 520   | Endgame-specific puzzles      |

### Position Hash Format

BTP encodes board positions as base-59 strings using a custom charset that excludes `l` (lowercase L), `I` (uppercase i), and `O` (uppercase o) to avoid visual ambiguity:

```
0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ
```

Each position encodes a ternary value per intersection (empty/black/white). Hash length is deterministic per board size — e.g., 24 chars for 9×9.

**Board size handling**:

- Classic puzzles: 9×9 viewport on a 19×19 board (top-left origin)
- AI/Endgame puzzles: Variable board sizes (typically 9×9 or 19×19)

### Node Format

BTP solution nodes are semicolon-delimited strings:

```
id;parent_id;ko_point;correct_moves;wrong_moves;standard_response;move_categories
```

**Correct moves**: Repeating 6-character groups — `{2-char coord}{2-char response}{child_node_id_char}{T|F}`.

**Wrong moves**: Compressed skip-counts over the legal-move enumeration. This requires a Go legality engine to reconstruct, since BTP iterates board intersections in row-by-row order and skips illegal moves (occupied, ko, suicide).

## SGF Output

### BTP API Fields → SGF Mapping

| BTP Field             | Stored?     | SGF Property      | Notes                                                |
| --------------------- | ----------- | ----------------- | ---------------------------------------------------- |
| `position_hash`       | Yes         | `AB[...] AW[...]` | Decoded from base-59 to stone positions              |
| `board_size`          | Yes         | `SZ[]`            | Board dimension                                      |
| `to_play`             | Yes         | `PL[B\|W]`        | Player to move                                       |
| `rating`              | Yes         | `YG[]`            | Mapped to 9-level slug                               |
| `tags`                | Yes         | `YT[]`            | 99 BTP tags → YenGo tags                             |
| `categories`          | Yes         | `YL[]`            | 15 categories → collection slugs                     |
| `categories` + `tags` | Yes         | `C[]` (root)      | Intent derived from category domain + tag refinement |
| `nodes`               | Yes         | Solution tree     | Correct/wrong move branches                          |
| `comment`             | Yes         | `C[]` (root)      | Appended to intent when present                      |
| `puzzle_id`           | As filename | `btp-{id}.sgf`    | Also in `sgf-index.txt`                              |
| `title`               | No          | —                 | Not pedagogical                                      |
| `author`              | No          | —                 | Not pedagogical                                      |

### Included SGF Properties

- `FF[4]GM[1]` — SGF format headers
- `SZ[...]` — Board size
- `PL[B]` or `PL[W]` — Player to move
- `AB[...]/AW[...]` — Initial stone positions
- `YG[...]` — Difficulty level (e.g., `YG[intermediate]`)
- `YT[...]` — Tags sorted, deduplicated (e.g., `YT[ko,ladder,life-and-death]`)
- `YS[blacktoplay]` — Source identifier
- `YL[...]` — Collections (e.g., `YL[eye-shape-mastery]`)
- `C[...]` — Root comment with puzzle objective
- Move `C[Correct]` / `C[Wrong]` in solution tree

### Excluded (per project spec)

`GN[]`, `PC[]`, `EV[]`, `SO[]`, `AP[]`, `CA[]` — assigned later by pipeline enricher or stripped by whitelist.

## Level Mapping

BTP `rating` (0–3000 scale) mapped to YenGo's 9-level system:

| BTP Rating | Go Rank (approx) | YenGo Level          |
| ---------- | ---------------- | -------------------- |
| 0–99       | below 20k        | `novice`             |
| 100–549    | 20k–16k          | `elementary`         |
| 550–1049   | 15k–11k          | `intermediate`       |
| 1050–1549  | 10k–6k           | `upper-intermediate` |
| 1550–2049  | 5k–1k            | `advanced`           |
| 2050–2349  | 1d–3d            | `low-dan`            |
| 2350–2649  | 4d–6d            | `high-dan`           |
| 2650–3000  | 7d–9d            | `expert`             |

Formula: `rank = 21 - round(rating / 100)`, clamped to [-8, 20].

> **Note**: No BTP puzzles map to `beginner` (25k–21k) — the lowest BTP rating starts at 20k.

## Tag Mapping

BTP has 99 tags encoded as 2-character codes (`[A-Z][a-z]` → index = `upper*26 + lower`). Tags are decoded to names, then mapped to YenGo slugs via `_local_tag_mapping.json`.

**Coverage**: 69/99 mapped (70%) — 18 exact matches, 24 high confidence, 27 medium confidence, 30 unmapped.

**Sample mappings**:

| BTP Tag         | YenGo Tag        | Confidence |
| --------------- | ---------------- | ---------- |
| `bent-four`     | `dead-shapes`    | exact      |
| `clamp`         | `clamp`          | exact      |
| `ko`            | `ko`             | exact      |
| `ladder`        | `ladder`         | exact      |
| `snapback`      | `snapback`       | exact      |
| `bamboo-joint`  | `connection`     | high       |
| `broken-ladder` | `ladder`         | high       |
| `double-atari`  | `atari`          | high       |
| `capture`       | `life-and-death` | medium     |
| `placement`     | `placement`      | medium     |

## Collection Mapping (YL)

BTP has 15 categories (A–O) mapped to YenGo collection slugs. 12/15 categories have matches:

| Letter | BTP Category | YenGo Collection                           |
| ------ | ------------ | ------------------------------------------ |
| A      | attachments  | _(unmapped)_                               |
| B      | basics       | `beginner-essentials`, `novice-essentials` |
| C      | capturing    | `capture-problems`                         |
| D      | endgame      | `endgame-problems`                         |
| E      | eyes         | `eye-shape-mastery`                        |
| F      | ko           | `ko-problems`                              |
| G      | placements   | _(unmapped)_                               |
| H      | reductions   | _(unmapped)_                               |
| I      | sacrifice    | `sacrifice-techniques`                     |
| J      | seki         | `seki-problems`                            |
| K      | semeai       | `capturing-race`                           |
| L      | shape        | `shape-problems`                           |
| M      | shortage     | `liberty-shortage`                         |
| N      | tactics      | `tesuji-training`                          |
| O      | vital-point  | `vital-point`                              |

## Intent Resolution (C[])

Puzzle objectives are derived statically from BTP categories and tags — no semantic resolver needed since BTP has structured metadata.

**Category → domain mapping**:

| Domain         | Categories                                                           |
| -------------- | -------------------------------------------------------------------- |
| LIFE_AND_DEATH | basics, eyes, seki                                                   |
| CAPTURING      | capturing                                                            |
| FIGHT          | ko, semeai, shortage                                                 |
| SHAPE          | shape                                                                |
| TESUJI         | attachments, placements, reductions, sacrifice, tactics, vital-point |
| ENDGAME        | endgame                                                              |

**Tag refinement** narrows the domain to specific objectives:

| Domain         | Refinement                             | Example Objective            |
| -------------- | -------------------------------------- | ---------------------------- |
| LIFE_AND_DEATH | escape tags → "Escape and live"        | `escape`, `running`          |
| LIFE_AND_DEATH | live tags → "Make two eyes"            | `two-eyes`, `making-eyes`    |
| LIFE_AND_DEATH | default → "Kill the group"             |                              |
| FIGHT          | ko tags → "Win the ko"                 | `ko`, `ko-fight`             |
| FIGHT          | semeai tags → "Win the capturing race" | `semeai`, `liberty-count`    |
| SHAPE          | connect tags → "Connect the stones"    | `connection`, `bamboo-joint` |
| SHAPE          | cut tags → "Cut and separate"          | `cutting`, `cross-cut`       |
| TESUJI         | default → "Find the tesuji"            |                              |
| ENDGAME        | default → "Find the best move"         |                              |

## Quality (YQ) — Pipeline-Computed

YQ is computed by the pipeline's `analyze` stage, not at download time. All quality-relevant signals survive the SGF round-trip:

| BTP Data                | SGF Representation     | Pipeline Recovery                            |
| ----------------------- | ---------------------- | -------------------------------------------- |
| Solution tree structure | Preserved branches     | `count_refutation_moves()` → `rc` count      |
| Correct moves           | `C[Correct]` on leaves | Layer 2 correctness inference                |
| Wrong moves             | `C[Wrong]` on leaves   | Layer 2 correctness inference                |
| Teaching comments       | Root `C[]` intent text | `compute_comment_level()` → `hc:1` or `hc:2` |

## Module Architecture

```
tools/blacktoplay/
├── __main__.py           # CLI entry point (argparse)
├── orchestrator.py       # Main download loop with resume + graceful shutdown
├── client.py             # HTTP client (POST with browser headers, retry/backoff)
├── models.py             # BTPPuzzle, BTPNode, BTPListItem dataclasses
├── config.py             # Constants, API URLs, paths, rate limit settings
├── hash_decoder.py       # Base-59 hash decode/encode
├── go_engine.py          # Minimal Go legality engine (captures, ko, suicide)
├── node_parser.py        # BTP node strings → SgfNode solution trees
├── enrichment.py         # Rating/tag/category → YG/YT/YL/C[] mapping
├── sgf_converter.py      # Full BTP puzzle → SGF string pipeline
├── storage.py            # Batch directory saves + index management
├── btp_checkpoint.py     # Download checkpoint state
├── logging_config.py     # Structured logger setup
├── _local_level_mapping.json     # Rating → level breakpoints
├── _local_tag_mapping.json       # 99 BTP tags → YenGo tags
├── _local_collections_mapping.json  # 15 categories → collections
└── intent_signals.json            # Category → objective derivation rules
```

## Research & Verification Tools

These scripts were used during development to reverse-engineer and verify the BTP format:

| Script                           | Purpose                                                                                   |
| -------------------------------- | ----------------------------------------------------------------------------------------- |
| `verify_hash_decode.py`          | Fetches puzzles from BTP API and tests decode→encode round-trip fidelity (11/11 PASS)     |
| `enumerate_puzzles.py`           | Parses cached puzzle list, breaks down by type/category/rating distribution               |
| `screenshot_verify.py`           | Uses Playwright to capture BTP board screenshots for visual hash decode verification      |
| `programmatic_intent_mapping.py` | Cross-references BTP categories/tags with `puzzle_intent` resolver for mapping comparison |

### Verification Results

Located in `verification_output/`:

| File                                     | Contents                                                             |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `hash_verification_results.json`         | 11/11 hash decode round-trip tests passed                            |
| `puzzle_enumeration.json`                | Full breakdown: 1,178 classic + 2,121 AI + 520 endgame = 3,819 total |
| `programmatic_intent_mapping.json`       | Automated tag/category mapping results                               |
| `manual_vs_programmatic_comparison.json` | Comparison of manual vs automated mappings                           |
| `screenshots/`                           | Visual verification screenshots                                      |

## Go Legality Engine

The tool includes a self-contained Go legality engine (`go_engine.py`) — not imported from `backend/` per the `tools/` isolation boundary. It exists solely to decode BTP's compressed wrong-move format.

**Capabilities**: Board state management, move legality checking (occupied, ko, suicide), capture detection via flood-fill, legal move enumeration in BTP row-by-row order, undo via history snapshots.

**Not a general-purpose engine** — it handles only what's needed for BTP wrong-move decompression.

## Dependencies

Uses only standard library + packages already in the project:

- `httpx` — HTTP client (BTP requires POST, shared `HttpClient` only supports GET)

Optional (research scripts only):

- `playwright` — Required by `screenshot_verify.py` for visual verification

## Known Limitations

1. **No `beginner` level mapping** — BTP's rating scale starts at a level corresponding to 20k, so no puzzles map to `beginner` (25k–21k)
2. **30% unmapped tags** — 30/99 BTP tags have no YenGo equivalent (e.g., `atari`, `pushing`, `peeping`)
3. **3 unmapped categories** — `attachments`, `placements`, `reductions` lack YenGo collection matches
4. **Classic viewport placement** — Classic puzzles use a 9×9 viewport on 19×19, placed at top-left origin (0,0). Other viewport positions are not handled.
5. **`load_list.php` reliability** — The live API may return empty responses from httpx; the tool falls back to a cached list in `TODO/btp-list-response.json`

> **See also**:
>
> - [Tool Development Standards](../../docs/how-to/backend/tool-development-standards.md) — Normative standards for puzzle tools
> - [OGS README](../ogs/README.md) — Reference implementation README
