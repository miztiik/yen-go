# Sanderland Adapter Reference

> **See also**:
>
> - [How-To: Create Adapter](../../how-to/backend/create-adapter.md) — Step-by-step guide
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Design patterns
> - [Concepts: Checkpoint/Resume](../../concepts/checkpoint-resume.md) — Resume support

**Last Updated**: 2026-02-05

Technical reference for the Sanderland local collection adapter.

---

## Configuration

File: `backend/puzzle_manager/config/sources.json` (sanderland entry)

```json
{
  "id": "sanderland",
  "name": "Sanderland Collection",
  "adapter": "sanderland",
  "config": {
    "path": "external-sources/sanderland",
    "include_folders": [
      "1a. Tsumego Beginner",
      "1b. Tsumego Intermediate",
      "1c. Tsumego Advanced"
    ],
    "exclude_folders": []
  }
}
```

### Config Options

| Option            | Type   | Default                       | Description                                         |
| ----------------- | ------ | ----------------------------- | --------------------------------------------------- |
| `path`            | string | `external-sources/sanderland` | Path to local collection directory                  |
| `include_folders` | array  | `[]` (all folders)            | Folders to include (case-sensitive, empty = all)    |
| `exclude_folders` | array  | `[]`                          | Folders to exclude (ignored if include_folders set) |

### Folder Filtering Rules

| `include_folders`          | `exclude_folders`                   | Result                        |
| -------------------------- | ----------------------------------- | ----------------------------- |
| `[]`                       | `[]`                                | All folders processed         |
| `["1a. Tsumego Beginner"]` | `[]`                                | Only "1a" processed           |
| `[]`                       | `["2c. Great Tesuji Encyclopedia"]` | All except "2c"               |
| `["1a"]`                   | `["1a"]`                            | "1a" processed (include wins) |

⚠️ **Folder names are case-sensitive**: `"1A. TSUMEGO BEGINNER"` will NOT match `"1a. Tsumego Beginner"`.

---

## Usage

```bash
# Run import (all configured folders)
python -m backend.puzzle_manager run --source sanderland --batch-size 100

# Resume interrupted import
python -m backend.puzzle_manager run --source sanderland --resume

# Check status
python -m backend.puzzle_manager status
```

---

## Features

- **Local Collection**: Reads JSON puzzle files from disk (no network)
- **Folder Filtering**: Control which folders to import via `include_folders`/`exclude_folders`
- **Checkpoint/Resume**: Resume interrupted imports with `--resume` flag
- **Centralized Validation**: Uses PuzzleValidator for consistent validation
- **Deterministic**: Same input always produces same output

---

## Resume Support

The adapter supports checkpoint/resume for large imports:

**Checkpoint saved to**: `.pm-runtime/state/sanderland_checkpoint.json`

**Checkpoint state includes**:

- Current folder being processed
- File index within folder
- Total processed/failed counts

**Usage**:

```bash
# Start import (saves checkpoint after each file)
python -m backend.puzzle_manager run --source sanderland --batch-size 500

# Resume from where you left off
python -m backend.puzzle_manager run --source sanderland --resume

# Start fresh (ignore existing checkpoint)
python -m backend.puzzle_manager run --source sanderland --batch-size 500
```

**Note**: Checkpoint is automatically cleared when all configured folders complete successfully.

---

## Source Structure

The Sanderland collection is organized in `external-sources/sanderland/problems/`:

```
problems/
├── 1a. Tsumego Beginner/      (~1,100 puzzles)
├── 1b. Tsumego Intermediate/  (~700 puzzles)
├── 1c. Tsumego Advanced/      (~800 puzzles)
├── 1d. Hashimoto Utaro Tsumego/
├── 2a. Tesuji/                (~2,000 puzzles)
├── 2b. Lee Changho Tesuji/
└── 2c. Great Tesuji Encyclopedia/ (~6,000 puzzles)
```

Total: ~12,401 puzzles across 7 folders.

---

## Output

Puzzles are written to staging directory:

```
.pm-runtime/staging/sanderland/
├── sanderland-1a-puzzle_001.sgf
├── sanderland-1a-puzzle_002.sgf
└── ...
```

---

## Error Handling

| Error Type           | Behavior                           |
| -------------------- | ---------------------------------- |
| Folder Not Found     | Log warning, skip folder, continue |
| Invalid JSON         | Record as `FetchResult.failed()`   |
| Validation Failed    | Record as `FetchResult.skipped()`  |
| Corrupted Checkpoint | Log warning, start fresh           |

---

## Notes

- Checkpoint file size remains under 1KB regardless of import size
- Resume time is under 5 seconds (loads state, skips to position)
- Duplicate detection via content hash ensures idempotent imports
