# GoTools Puzzle Ingestor for YenGo

Downloads Go puzzles from the [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver) repository and converts them to YenGo-compatible SGF format v3.1.

## Quick Start

```bash
# Install dependencies
pip install requests

# Download all puzzles (all 6 levels, ~18,000 puzzles)
python gotools_ingestor.py

# Download specific levels
python gotools_ingestor.py -l 1        # Level 1 only
python gotools_ingestor.py -l 1-3      # Levels 1-3
python gotools_ingestor.py -l 1,4,6    # Specific levels

# Download specific files within a level
python gotools_ingestor.py -l 1 -f 1-5   # Files 1-5 of level 1

# Check progress
python gotools_ingestor.py --status

# Reset and start fresh
python gotools_ingestor.py --reset
```

---

## How We Got Here: Reverse Engineering the GoTools Format

### The Discovery Journey

1. **The official Rust parser** in [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver/blob/master/src/gotools_parser/mod.rs)
2. **The PEG grammar file** at [grammar.pest](https://github.com/cameron-martin/tsumego-solver/blob/master/src/gotools_parser/grammar.pest)
3. **Raw puzzle data** from the repository

### Key Findings from Source Code Analysis

#### 1. Stone Color Encoding (VERIFIED ✅)

From the official Rust source code (`mod.rs` lines 58-63):

```rust
let player = if chars.next().unwrap() == '?' {
    GoPlayer::White
} else {
    GoPlayer::Black
};
```

| Encoding             | Color     | Example                          |
| -------------------- | --------- | -------------------------------- |
| `ColRow` (no prefix) | **Black** | `AB` = Black at column A, row B  |
| `?ColRow` (? prefix) | **White** | `?AB` = White at column A, row B |

#### 2. First Player (VERIFIED ✅)

From the official Rust source code (end of `read_puzzle` function):

```rust
Some(Puzzle::new(GoGame::from_board(board, GoPlayer::Black)))
```

**Black ALWAYS plays first** - this is hardcoded, not detected. It follows the standard tsumego convention where:

- **Black = Attacker** (trying to kill or live)
- **White = Defender** (responding to Black's moves)

#### 3. Coordinate System

From the PEG grammar:

```pest
stone = { ( "A" | "?" ) ~ location }
location = { ASCII_ALPHA_UPPER ~ ASCII_ALPHA_UPPER }
```

- **Columns**: A-T (skipping I) for 19 positions
- **Rows**: A-S for 19 positions (A=row 1, S=row 19)
- **Solution format**: Letter pairs like `CCBC` = move at C3, then B3

### The tsumego-solver.exe Binary

The `tsumego-solver.exe` in the tools directory is **NOT from the source code** - it's a pre-built binary from [GitHub Releases v0.1.3](https://github.com/cameron-martin/tsumego-solver/releases/tag/v0.1.3).

| Binary                           | Platform | Size    |
| -------------------------------- | -------- | ------- |
| `cli-x86_64-pc-windows-msvc.exe` | Windows  | 1.2 MB  |
| `cli-x86_64-apple-darwin`        | macOS    | 1.46 MB |
| `cli-x86_64-unknown-linux-gnu`   | Linux    | 2.52 MB |

Download using: `bash tools/download-tsumego-solver.sh`

---

## GoTools Source Data

| Level | Files | Puzzles/File | Total  | Difficulty           |
| ----- | ----- | ------------ | ------ | -------------------- |
| Lv1   | 14    | ~217         | ~3,038 | Beginner (30k-15k)   |
| Lv2   | 14    | ~217         | ~3,038 | Basic (14k-8k)       |
| Lv3   | 14    | ~217         | ~3,038 | Intermediate (7k-1k) |
| Lv4   | 14    | ~217         | ~3,038 | Advanced (1d-4d)     |
| Lv5   | 14    | ~217         | ~3,038 | Expert (5d-7d)       |
| Lv6   | 14    | ~217         | ~3,038 | Expert (8d-9p)       |

**Total: 84 files, ~18,228 puzzles**

## YenGo Level Mapping (v3.1)

GoTools has 6 levels, but YenGo uses 5 levels with sub-levels (1-3):

| GoTools Level     | YenGo Level    | Sub-levels | Kyu/Dan Range |
| ----------------- | -------------- | ---------- | ------------- |
| Lv1 (files 1-5)   | beginner:1     | 1          | 30k-25k       |
| Lv1 (files 6-10)  | beginner:2     | 2          | 24k-20k       |
| Lv1 (files 11-14) | beginner:3     | 3          | 19k-15k       |
| Lv2 (files 1-5)   | basic:1        | 1          | 14k-12k       |
| Lv2 (files 6-10)  | basic:2        | 2          | 11k-9k        |
| Lv2 (files 11-14) | basic:3        | 3          | 8k            |
| Lv3 (files 1-5)   | intermediate:1 | 1          | 7k-5k         |
| Lv3 (files 6-10)  | intermediate:2 | 2          | 4k-2k         |
| Lv3 (files 11-14) | intermediate:3 | 3          | 1k            |
| Lv4 (files 1-5)   | advanced:1     | 1          | 1d-2d         |
| Lv4 (files 6-10)  | advanced:2     | 2          | 3d            |
| Lv4 (files 11-14) | advanced:3     | 3          | 4d            |
| Lv5 (files 1-7)   | expert:1       | 1          | 5d-6d         |
| Lv5 (files 8-14)  | expert:2       | 2          | 7d-8d         |
| Lv6 (all files)   | expert:3       | 3          | 9d-9p         |

---

## SGF Output Format (YenGo v3.1)

### Example Output

```sgf
(;GM[1]FF[4]CA[UTF-8]SZ[19]AP[YENGO:3.1]YV[3]YG[intermediate:2]C[]PL[B]AB[aa][ab][ba]AW[bb][bc][cc];B[ad];W[bd])
```

### SGF Properties Used

| Property    | Standard | Description             | Example              |
| ----------- | -------- | ----------------------- | -------------------- |
| `GM[1]`     | ✅       | Game type (Go)          | `GM[1]`              |
| `FF[4]`     | ✅       | SGF format version      | `FF[4]`              |
| `CA[UTF-8]` | ✅       | Character encoding      | `CA[UTF-8]`          |
| `SZ[19]`    | ✅       | Board size              | `SZ[19]`             |
| `AP`        | ✅       | Application/attribution | `AP[YENGO:3.1]`      |
| `YV`        | YenGo    | Format version marker   | `YV[3]`              |
| `YG`        | YenGo    | Level + sub-level       | `YG[intermediate:2]` |
| `PL`        | ✅       | Player to move          | `PL[B]`              |
| `AB`        | ✅       | Add black stones        | `AB[aa][ab]`         |
| `AW`        | ✅       | Add white stones        | `AW[ba][bb]`         |
| `C`         | ✅       | Comment (empty)         | `C[]`                |

### Design Decisions

**Empty Comments (`C[]`)**: We intentionally leave comments empty because:

- Source attribution is captured in `AP[YENGO:3.1]`
- Level info is in `YG[level:sub-level]`
- Verbose comments add no value to the puzzle experience

**Properties NOT Used**:

- `DI` - Obsolete difficulty property (goproblems.com legacy)
- `SO` - Source (omitted per project policy)
- `GN` - Game name (not applicable to puzzles)
- `CP` - Copyright (handled at collection level)

---

## GoTools Raw Format Reference

### File Structure

```
$ P2058006
?AB?AC?AEAAF?BA?BBABC?BD?BEABF?CAACBACDACEACFADCADDAEAAEBAEC[AB][BD]
?+l1d#5 3 1 40.00 4 ?? 0 255 :CCBC:
?-d#1 3 1 0.00 2 ?? 0 255 :DBDA:

$ P2034170
...
```

### Format Breakdown

| Element   | Meaning                           |
| --------- | --------------------------------- |
| `$ P{id}` | Problem header with unique ID     |
| `AAF`     | Black stone at column A, row F    |
| `?AB`     | White stone at column A, row B    |
| `[AB]`    | Marked point (triangle indicator) |
| `?+l...`  | Correct move sequence line        |
| `?-d...`  | Wrong move sequence line          |
| `:CCBC:`  | Solution moves (C3→B3)            |
| `@@`      | Pass move                         |

### Coordinate Mapping

```
GoTools:  A  B  C  D  E  F  G  H  J  K  L  M  N  O  P  Q  R  S  T
Column:   1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
SGF:      a  b  c  d  e  f  g  h  i  j  k  l  m  n  o  p  q  r  s

Note: GoTools skips 'I' (uses J for column 9), SGF uses 'i'
```

---

## Output Structure

```
downloads/
├── level_1/
│   └── sgf/
│       ├── gt_lv1_01_p0001.sgf
│       ├── gt_lv1_01_p0002.sgf
│       └── ...
├── level_2/
│   └── sgf/
│       └── ...
└── ...
```

## State Tracking

Progress is saved to `state.json` for resumable downloads:

```json
{
  "started_at": "2026-01-25T10:30:00",
  "last_updated": "2026-01-25T11:45:00",
  "completed_files": {
    "level_1": [1, 2, 3, 4, 5],
    "level_2": [1, 2]
  },
  "puzzle_counts": {
    "lv1.1": 217,
    "lv1.2": 217
  }
}
```

Resume a partial download simply by running the script again - completed files are skipped.

## Configuration

Settings in `config.json`:

```json
{
  "output_dir": "downloads",
  "rate_limiting": {
    "delay_seconds": 0.5,
    "jitter_seconds": 0.2
  },
  "max_retries": 3,
  "timeout_seconds": 30,
  "source": {
    "name": "GoTools",
    "repo": "cameron-martin/tsumego-solver"
  },
  "color_encoding": {
    "_comment": "Verified from cameron-martin/tsumego-solver src/gotools_parser/mod.rs",
    "no_prefix": "black",
    "question_mark_prefix": "white",
    "first_player": "black"
  }
}
```

---

## Attribution

| Item                 | Source                                                                                                          |
| -------------------- | --------------------------------------------------------------------------------------------------------------- |                                                                    |
| Puzzle repository    | [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver)                               |
| Parser reference     | [gotools_parser/mod.rs](https://github.com/cameron-martin/tsumego-solver/blob/master/src/gotools_parser/mod.rs) |
| Format grammar       | [grammar.pest](https://github.com/cameron-martin/tsumego-solver/blob/master/src/gotools_parser/grammar.pest)    |


---

## Changelog

### 2026-01-25

- **Verified color encoding** from official Rust source code
- **Confirmed Black always first** - hardcoded in tsumego-solver, standard convention
- **Simplified comments** - changed from verbose to empty `C[]`
- **Added config.json** - documented format decisions with source references
- **Updated coordinate handling** - proper GoTools A-T (no I) to SGF a-s mapping
