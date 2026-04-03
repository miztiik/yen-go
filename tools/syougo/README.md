# Syougo.jp Puzzle Ingestor

A configuration-driven Python utility to ingest Go/Baduk tsumego puzzles from [syougo.jp](https://www.syougo.jp/jk/khantei.html) (将碁友の会).

## Overview

This tool downloads puzzles from the skill assessment (棋力判定) section of syougo.jp, which provides 123 puzzles across 5 difficulty levels.

| Level | Japanese | English      | Puzzles |
| ----- | -------- | ------------ | ------- |
| 1     | 初級     | Beginner     | 25      |
| 2     | 中級     | Intermediate | 25      |
| 3     | 上級     | Advanced     | 25      |
| 4     | 有段     | Dan-level    | 24      |
| 5     | 高段     | High-Dan     | 24      |

## Quick Start

**Run from project root** (`yen-go/`):

```bash
# Download all puzzles from all levels
python -m tools.syougo --all

# Download specific levels
python -m tools.syougo --levels 1,2,3

# Show status
python -m tools.syougo --status

# Full help
python -m tools.syougo --help

# Process downloads into pipeline-ready SGFs (external-sources/syougo/)
python -m tools.syougo.syougo_processor
python -m tools.syougo.syougo_processor --dry-run     # preview only
python -m tools.syougo.syougo_processor --levels 1,2  # specific levels
```

## Prerequisites

- **Python 3.8+**
- **requests library**: `pip install requests`

## Output Structure

```
downloads/
├── level_1_beginner/
│   ├── syougo_L1_P01.sgf
│   ├── syougo_L1_P01.json   # metadata
│   └── ...
├── level_2_intermediate/
│   └── ...
└── level_3_advanced/
    └── ...
```

## SGF Format Notes

The source uses standard SGF format embedded in JavaScript:

- `SZ[9]` or `SZ[13]` - Board size (9x9 for levels 1-4, 13x13 for level 5)
- `AB[...]` - Initial black stones
- `AW[...]` - Initial white stones
- `C[...]` - Comments (problem prompt at root, result after solution)
- Move sequences include correct solution and wrong variations

### Japanese Terms in Comments

| Japanese           | English                    |
| ------------------ | -------------------------- |
| 黒番です           | Black to play              |
| 白を取ってください | Capture the white stones   |
| 黒生きてください   | Make black live            |
| コウになります     | It becomes ko              |
| 正解               | Correct                    |
| 残念               | Wrong (lit. "regrettable") |
| 良く出来ました     | Well done                  |

## Configuration

Edit `config.json` to customize:

- Network delays and retry behavior
- Output directory and file formats
- Logging settings

## State Management

The tool maintains `state.json` to track:

- Successfully downloaded puzzles
- Failed downloads for retry
- Run history

Use `--retry` to retry failed downloads, or `--force` to re-download everything.

## Design Pattern

This tool follows the YenGo tools design pattern:

1. **Configuration-driven**: All settings in JSON files
2. **State tracking**: Resume capability via state.json
3. **Centralized logging**: Uses `config/logging.json` for log directory
4. **Rate limiting**: Configurable delays with jitter
5. **Idempotent**: Safe to run multiple times

## License

MIT - Part of the YenGo Project
