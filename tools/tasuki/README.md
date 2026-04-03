# Tasuki SGF Collection Extractor

Last Updated: 2026-02-26

## Purpose

Downloads multi-puzzle SGF collection files from the [tasuki2sgf](https://github.com/Seon82/tasuki2sgf) GitHub repository and splits each one into individual, standalone puzzle SGF files suitable for the yen-go pipeline.

## Source

- **Repository**: https://github.com/Seon82/tasuki2sgf
- **Raw files**: https://raw.githubusercontent.com/Seon82/tasuki2sgf/main/generated/
- **Metadata**: https://raw.githubusercontent.com/Seon82/tasuki2sgf/main/comments.json
- **Original author**: Vit Brunner (tasuki) — [tsumego.tasuki.org](https://tsumego.tasuki.org/)
- **Upstream format**: `.tex` files converted to SGF by [Seon82/tasuki2sgf](https://github.com/Seon82/tasuki2sgf)

## Collections

| Key            | Output Directory           | Name                                                     | Puzzles   | Description                                                                                                                  |
| -------------- | -------------------------- | -------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `cho-1`        | `cho-chikun-elementary/`   | Cho Chikun - Encyclopedia of Life & Death - Elementary   | 900       | Beginner problems; a dan player solves each in seconds                                                                       |
| `cho-2`        | `cho-chikun-intermediate/` | Cho Chikun - Encyclopedia of Life & Death - Intermediate | 861       | Strong kyu problems; a dan player needs < 1 min each                                                                         |
| `cho-3`        | `cho-chikun-advanced/`     | Cho Chikun - Encyclopedia of Life & Death - Advanced     | 792       | Advanced problems; a dan player needs minutes each                                                                           |
| `gokyoshumyo`  | `gokyoshumyo/`             | Gokyo Shumyo                                             | 520       | Classical 1822 collection by Hayashi Genbi (7 sections: living, killing, ko, capturing races, oiotoshi, connecting, various) |
| `hatsuyoron`   | `hatsuyoron/`              | Igo Hatsuyo-ron                                          | 183       | Notoriously difficult problems compiled ~1710 by Inoue Dosetsu Inseki                                                        |
| `lee-chang-ho` | `lee-chang-ho/`            | Lee Chang-ho - Selected Life and Death Problems          | 738       | 6-volume series, difficulty increases through volumes                                                                        |
| `xxqj`         | `xuanxuan-qijing/`         | Xuanxuan Qijing (Gengen Gokyo)                           | 347       | Classical Chinese collection ~1347 by Yan Defu and Yan Tianzhang                                                             |
|                |                            | **Total**                                                | **4,341** |                                                                                                                              |

All problems are black to move unless the source SGF specifies `PL[W]` (some gokyoshumyo and other collections mix black/white to play).

## Output Structure

```
external-sources/tasuki/
├── cho-chikun-elementary/
│   └── batch-001/           # Up to 1000 files per batch
│       ├── problem_0001_p1.sgf
│       ├── problem_0002_p2.sgf
│       └── ...              # 900 files
├── cho-chikun-intermediate/
│   └── batch-001/
│       └── ...              # 861 files
├── cho-chikun-advanced/
│   └── batch-001/
│       └── ...              # 792 files
├── gokyoshumyo/
│   └── batch-001/
│       └── ...              # 520 files
├── hatsuyoron/
│   └── batch-001/
│       └── ...              # 183 files
├── lee-chang-ho/
│   └── batch-001/
│       └── ...              # 738 files
└── xuanxuan-qijing/
    └── batch-001/
        └── ...              # 347 files
```

### File Naming Convention

Filenames follow the pattern `problem_{SEQ}_p{LABEL}.sgf` where:

- `{SEQ}` — 4-digit zero-padded sequential number (1-indexed order in the source SGF)
- `{LABEL}` — Original problem identifier extracted from the comment (e.g., `42`, `1-103`)

Examples:

- Cho: `problem_0001_p1.sgf`, `problem_0042_p42.sgf`
- Gokyoshumyo: `problem_0001_p1-1.sgf`, `problem_0520_p7-46.sgf` (section-number format)
- Lee Chang-ho: `problem_0001.sgf` (no `_p` suffix when comment lacks a parseable label)

### Batch Naming Convention

Follows the same convention as `external-sources/ambak-tsumego/`: directories named `batch-NNN` with up to 1000 SGF files per batch. Since no collection exceeds 1000 puzzles, all currently fit in a single `batch-001`.

### Output File Format

Each generated SGF file is a standalone puzzle:

```sgf
(;SZ[19]FF[4]GM[1]PL[B]C[problem 1 | Source: Cho Chikun - Encyclopedia of Life & Death - Elementary]AB[be][dc][cc][eb][fb][bc]AW[bb][ab][db][da][cb])
```

Properties preserved per puzzle:

- `SZ` — Board size (always 19, from root node)
- `FF[4]`, `GM[1]` — SGF format version 4, game type Go
- `PL` — Player to move (`B` or `W`)
- `C` — Original comment text + source collection attribution
- `AB` — Black setup stones
- `AW` — White setup stones

**Note**: These puzzles have **no solution trees** — the source collection provides positions only, without solution sequences (the original author chose this deliberately to encourage reading).

## Upstream SGF Format (Input)

Each upstream file (e.g., `cho-1.sgf`) is a single SGF game tree where **all puzzles are sibling variations of the root node**:

```sgf
(;FF[4]GM[1]SZ[19]
C[Collection description...]
(;C[problem 1]PL[B]AB[be][dc][cc]AW[bb][ab][db])
(;C[problem 2]PL[B]AB[bb][ab][db]AW[ea][ac][dc])
...
(;C[problem 900]PL[B]AB[...]AW[...])
)
```

Key characteristics:

- **Root node**: Contains `FF`, `GM`, `SZ`, and a collection description in `C[]`
- **Each child variation**: One puzzle with `C[]` (problem label), `PL[]` (player to move), `AB[]`/`AW[]` (setup stones)
- **No moves**: No `B[]` or `W[]` properties — setup only, no solution tree
- **Comment format varies by collection**:
  - Cho collections: `C[problem 42]`
  - Gokyoshumyo: `C[problem 1-103, white to play]` (section-number format)
  - Some have `PL[W]` (white to play) — not always black

## Design Decisions

### 1. Proper SGF parsing, no regex

The tool uses `tools.core.sgf_parser.parse_sgf()` — the project's standalone recursive-descent SGF parser — instead of regex-based splitting. This correctly handles:

- Escaped brackets in property values (`\]`)
- Multi-value properties (`AB[aa][bb][cc]` joined as `"aa,bb,cc"`)
- Nested parentheses in variation trees
- Whitespace and newlines within property values

### 2. Dual numbering in filenames (`problem_{SEQ}_p{LABEL}.sgf`)

Filenames combine a sequential index (for guaranteed uniqueness) with the original problem label (for human readability). The sequential number is the 1-indexed position in the source SGF's variation list. The label is extracted from the comment text (everything after `"problem "` up to the first comma).

- Sequential index prevents collisions (gokyoshumyo's `"problem 1-103"` would otherwise collide with `"problem 1-1"`)
- Original label preserves the author's numbering for cross-referencing with printed books
- When no label can be parsed (e.g., Lee Chang-ho comments without `"problem"` prefix), the `_p{LABEL}` suffix is omitted
- The original comment text is also preserved verbatim in the output SGF's `C[]` property

### 3. SGFBuilder for output (no string concatenation)

Output SGFs are built using `tools.core.sgf_builder.SGFBuilder`, ensuring:

- Properly escaped property values
- Valid SGF structure (`FF[4]`, `GM[1]`, correct bracket nesting)
- Consistent formatting across all output files

### 4. Batch directory structure

Files are organized into `batch-NNN` subdirectories matching the `ambak-tsumego` convention:

- Max 1000 files per batch (configurable via `MAX_FILES_PER_BATCH`)
- Currently all collections fit in `batch-001`
- Formula: `batch_number = ((puzzle_index - 1) // 1000) + 1`

### 5. Download from GitHub raw content

Uses `urllib.request` (stdlib — no extra dependencies) to fetch SGF files directly from GitHub raw URLs. No git clone, no API tokens required. A `--local` flag allows offline operation from pre-downloaded files.

### 6. No YenGo properties added

The tool produces **clean, minimal SGFs** without any YenGo custom properties (`YV`, `YG`, `YT`, etc.). Those are added later by the pipeline's analyze stage. This tool is solely an extraction/splitting utility.

## File Structure

```
tools/tasuki/
├── __init__.py      # Package marker
├── __main__.py      # Entry point for `python -m tools.tasuki`
├── extract.py       # All extraction logic (download, parse, split, write)
└── README.md        # This file
```

### `extract.py` — Module Overview

| Function                               | Purpose                                                                             |
| -------------------------------------- | ----------------------------------------------------------------------------------- |
| `download_text(url)`                   | HTTP GET with User-Agent header, 30s timeout                                        |
| `download_comments()`                  | Fetches and parses `comments.json` (collection descriptions)                        |
| `download_collection_sgf(key)`         | Fetches a single collection SGF from GitHub                                         |
| `extract_puzzles_from_collection(sgf)` | Parses collection SGF, extracts each child variation as a puzzle dict               |
| `_extract_problem_label(comment)`      | Extracts problem identifier from comment (e.g., `"problem 1-103, ..."` → `"1-103"`) |
| `build_puzzle_sgf(puzzle, name)`       | Builds standalone SGF string from puzzle dict using `SGFBuilder`                    |
| `batch_dir_name(n)`                    | Returns `"batch-NNN"` string                                                        |
| `write_puzzles(puzzles, ...)`          | Writes puzzle SGFs to batch-organized directories                                   |
| `process_collection(key, sgf, ...)`    | End-to-end: parse + write for one collection                                        |
| `main(args)`                           | CLI entry point: parse args, iterate collections, report totals                     |

### `__main__.py`

Delegates to `extract.main()` so the tool can be invoked as `python -m tools.tasuki`.

## Usage

```bash
# Extract all 7 collections (downloads from GitHub)
python -m tools.tasuki.extract

# Extract a single collection
python -m tools.tasuki.extract --collection cho-1

# Use local files instead of downloading
python -m tools.tasuki.extract --local ./path/to/generated/

# Preview without writing files
python -m tools.tasuki.extract --dry-run

# Verbose logging (debug level)
python -m tools.tasuki.extract -v

# Custom output directory
python -m tools.tasuki.extract --output /tmp/tasuki-output

# Also works as a package
python -m tools.tasuki
```

### CLI Arguments

| Argument        | Default                    | Description                                                                                                        |
| --------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `--collection`  | all                        | Process only the named collection (`cho-1`, `cho-2`, `cho-3`, `gokyoshumyo`, `hatsuyoron`, `lee-chang-ho`, `xxqj`) |
| `--local DIR`   | (download)                 | Read `.sgf` files from a local directory instead of GitHub                                                         |
| `--output DIR`  | `external-sources/tasuki/` | Output root directory                                                                                              |
| `--dry-run`     | off                        | Log what would be written without creating files                                                                   |
| `-v, --verbose` | off                        | Enable debug-level logging                                                                                         |

## Dependencies

- **Python 3.11+** (uses `X | Y` union type syntax)
- **No external packages** — uses only stdlib (`urllib.request`, `argparse`, `json`, `logging`, `pathlib`)
- **Internal**: `tools.core.sgf_parser`, `tools.core.sgf_builder`, `tools.core.sgf_types` (standalone, no `backend/` imports)

## Re-running / Idempotency

The tool overwrites existing files without warning. To do a clean re-run:

```bash
# Remove existing output, then re-extract
Remove-Item -Recurse -Force external-sources/tasuki   # PowerShell
rm -rf external-sources/tasuki                         # Unix
python -m tools.tasuki.extract
```

> **See also**:
>
> - [tools/core/README.md](../core/README.md) — Shared SGF parser/builder used by this tool
> - [external-sources/ambak-tsumego/](../../external-sources/ambak-tsumego/) — Similar batch directory convention
