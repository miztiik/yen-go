# Tian Long Tu (天龙图) Puzzle Ingestor v1.0

A modular, idempotent Python utility to ingest Go/Baduk tsumego puzzles from the [liryan1/101weiqi](https://github.com/liryan1/101weiqi) GitHub repository.

## Source

- **Name**: Tian Long Tu (天龙图) - "Dragon Gate Diagram"
- **URL**: https://raw.githubusercontent.com/liryan1/101weiqi/main/data/json/tian_long_tu.json
- **Format**: Static JSON with 82 problems
- **Board Size**: 19×19
- **Difficulty Range**: 3K+ to 2D+

## Quick Start

```bash
# Download all puzzles
python tianlongtu_ingestor.py

# Download specific puzzles
python tianlongtu_ingestor.py -p 1,5,10

# Download a range
python tianlongtu_ingestor.py -p 1-20

# Force re-download
python tianlongtu_ingestor.py --force

# Show status
python tianlongtu_ingestor.py --status

# Retry failed downloads
python tianlongtu_ingestor.py --retry

# Verbose output
python tianlongtu_ingestor.py -v
```

## Prerequisites

- **Python 3.8+**
- **requests library**: `pip install requests`

## Output Structure

```
downloads/
├── sgf/
│   ├── tlt_p0001.sgf
│   ├── tlt_p0002.sgf
│   └── ...
├── json/
│   ├── tlt_p0001.json       # Original source data
│   ├── tlt_p0002.json
│   └── ...
└── metadata/
    ├── tlt_p0001_meta.json  # Processing metadata
    ├── tlt_p0002_meta.json
    └── ...
```

## Level Mapping

| Source Rating | YenGo Level  | Sub-level | Kyu/Dan Range |
| ------------- | ------------ | --------- | ------------- |
| 3K+, 3K       | intermediate | 1         | 3 kyu         |
| 2K+, 2K       | intermediate | 2         | 2 kyu         |
| 1K+, 1K       | intermediate | 3         | 1 kyu         |
| 1D, 1D+       | advanced     | 1         | 1 dan         |
| 2D, 2D+       | advanced     | 2         | 2 dan         |

## SGF Format (YenGo v3.1)

Generated SGF files follow YenGo v3.1 format:

```sgf
(;GM[1]FF[4]
CA[UTF-8]
SZ[19]
AP[YENGO:3.1]
YV[3]
YG[intermediate:2]
C[Source difficulty: 2K]
PL[B]
AB[hr][hp][ho][hn][gq][er][eq][dr][bq][am][bm][cl][cn][dn][en][do][fm][gm]
AW[fn][go][gp][fp][ep][eo][dq][dp][cp][co][bp][bn][an][ao]
;B[ra];W[pa]
(;B[ng];W[rc];B[rb];W[qc];B[sc];W[sb];B[sd];W[qa];B[sa];W[sb];B[rb];W[ra];B[sa])
(;B[ng];W[rc];B[rb];W[qc];B[sc];W[sb];B[sa];W[qa];B[sd];W[sb];B[rb];W[ra];B[sa])
)
```

### YenGo-Specific Properties

| Property        | Description                     | Example              |
| --------------- | ------------------------------- | -------------------- |
| `YV[3]`         | YenGo SGF format version        | `YV[3]`              |
| `YG[level:sub]` | Difficulty level with sub-level | `YG[intermediate:2]` |
| `AP[YENGO:3.1]` | Application attribution         | `AP[YENGO:3.1]`      |

## Variations

SGF variations are preserved using standard SGF branch notation:

```sgf
;B[ra];W[pa]        # Common prefix
(;B[ng]...)         # Main solution branch
(;B[rc]...)         # Alternative variation
```

This ensures all solution paths from the source data are preserved for study and analysis.

## Features

| Feature                   | Status | Description                           |
| ------------------------- | ------ | ------------------------------------- |
| Static JSON source        | ✅     | Single file download, no web scraping |
| Idempotent state tracking | ✅     | Resume, skip existing, retry failed   |
| YenGo SGF v3.1 format     | ✅     | Proper level tags and formatting      |
| Level mapping             | ✅     | Kyu/Dan → YenGo levels                |
| Variation preservation    | ✅     | All solution paths saved              |
| Colored console output    | ✅     | ANSI colors for log levels            |
| Per-run log files         | ✅     | `logs/ingest_YYYY-MM-DD_HH-MM-SS.log` |
| Metadata extraction       | ✅     | Original difficulty, processing info  |

## State Management

State is tracked in `state.json` for idempotent operations:

```json
{
  "started_at": "2026-01-25T10:00:00",
  "last_updated": "2026-01-25T10:05:00",
  "source_hash": "abc123def456...",
  "completed_puzzles": [1, 2, 3, 4, 5],
  "failed_puzzles": {},
  "total_puzzles": 82
}
```

### Commands

```bash
# Clear state and start fresh
python tianlongtu_ingestor.py --clear

# Retry only failed puzzles
python tianlongtu_ingestor.py --retry

# Force re-download all
python tianlongtu_ingestor.py --force
```

## Configuration

Edit `config.json` for persistent settings:

```json
{
  "output": {
    "directory": "./downloads",
    "save_sgf": true,
    "save_raw_json": true,
    "save_metadata": true
  },
  "logging": {
    "level": "INFO",
    "to_file": true
  }
}
```

## Related Sources

The same repository contains other classical Go problem collections:

| Collection           | Chinese  | Description                |
| -------------------- | -------- | -------------------------- |
| `guan_zi_pu`         | 官子谱   | Classical endgame problems |
| `qi_jing_zhong_miao` | 棋经众妙 | Various classical problems |
| `xuan_xuan_qi_jing`  | 玄玄棋经 | Mysterious Chess Classic   |

These could be added as additional sources using the same ingestor pattern.

## License

MIT License - YenGo Project
