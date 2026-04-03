# Kisvadim Adapter Reference

> **See also**:
>
> - [How-To: Create Adapter](../../how-to/backend/create-adapter.md) — Step-by-step guide
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Design patterns

**Last Updated**: 2026-02-01

Technical reference for the Kisvadim local collection adapter.

---

## Configuration

File: `backend/puzzle_manager/config/sources.json` (kisvadim entry)

```json
{
  "id": "kisvadim",
  "name": "Kisvadim Collection",
  "adapter": "kisvadim",
  "enabled": true,
  "config": {
    "base_path": "external-sources/kisvadim-goproblems",
    "pattern": "**/*.sgf"
  }
}
```

### Config Options

| Option      | Type   | Default    | Description                        |
| ----------- | ------ | ---------- | ---------------------------------- |
| `base_path` | string | (required) | Path to local collection directory |
| `pattern`   | string | `**/*.sgf` | Glob pattern for SGF files         |

---

## Usage

```bash
# Run import
python -m backend.puzzle_manager run --source kisvadim --batch-size 100

# Check status
python -m backend.puzzle_manager status
```

---

## Features

- **File System**: Reads SGF files from local directory
- **Professional Collections**: Includes Cho Chikun, Igo Hatsuyoron
- **Organized by Author**: Subdirectories per author/collection
- **Pre-validated**: Curated and validated puzzles

---

## Source Structure

The Kisvadim collection is organized by author:

```
external-sources/kisvadim-goproblems/
├── CHO CHIKUN/
│   ├── Elementary/
│   ├── Intermediate/
│   └── Advanced/
├── IGO HATSUYORON/
│   └── ...
└── ...
```

---

## Output

Puzzles are written to staging directory:

```
.pm-runtime/staging/kisvadim/
├── YENGO-abc123def456.sgf
└── ...
```

---

## Error Handling

| Error Type     | Behavior                         |
| -------------- | -------------------------------- |
| File Not Found | Skip, log warning                |
| Invalid SGF    | Record as `FetchResult.failed()` |
| Parse Error    | Skip, log error                  |

---

## Notes

- No checkpoint support (file-based adapter)
- Processes all matching files per run
- Duplicate detection via content hash
