# Local Adapter Reference

> **See also**:
>
> - [How-To: Configure Sources](../../how-to/backend/configure-sources.md) — Source configuration guide
> - [How-To: Create Adapter](../../how-to/backend/create-adapter.md) — Adapter development guide
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Adapter design patterns

**Last Updated**: 2026-02-03

---

## Overview

The **LocalAdapter** imports SGF puzzle files from local directories. It's designed for:

- Importing curated puzzle collections (e.g., tsumego, life-and-death problems)
- Processing large archives (10,000+ files) with checkpoint/resume
- Selective folder filtering for incremental imports

---

## Configuration

Add to `backend/puzzle_manager/config/sources.json`:

```json
{
  "id": "tsumego",
  "name": "Tsumego Collection",
  "adapter": "local",
  "config": {
    "path": "external-sources/tsumego/problems",
    "include_folders": ["elementary", "intermediate"],
    "exclude_folders": [],
    "resume": false,
    "validate": true,
    "move_processed_to": null
  }
}
```

### Configuration Options

| Option              | Type           | Default      | Description                                                           |
| ------------------- | -------------- | ------------ | --------------------------------------------------------------------- |
| `path`              | string         | **required** | Directory containing SGF files (relative to project root or absolute) |
| `include_folders`   | string[]       | `[]`         | Whitelist of folder names to process (empty = all folders)            |
| `exclude_folders`   | string[]       | `[]`         | Blacklist of folder names to skip                                     |
| `resume`            | boolean        | `false`      | Load existing checkpoint to continue interrupted import               |
| `validate`          | boolean        | `true`       | Validate SGF files using PuzzleValidator                              |
| `move_processed_to` | string \| null | `null`       | Directory to move processed files to                                  |
| `id`                | string         | `"local"`    | Explicit source ID (for multi-source checkpoint separation)           |

---

## Features

### Folder Filtering (Spec 111, FR-001, FR-002)

Filter which subdirectories to process:

```json
{
  "include_folders": ["elementary"], // Only process elementary/
  "exclude_folders": ["wip", "rejected"] // Skip these folders
}
```

**Behavior:**

- `include_folders` takes precedence over `exclude_folders`
- Order is preserved: folders process in `include_folders` order
- Non-existent folders log a warning but don't fail
- Empty `include_folders` means "all folders"

### Checkpoint/Resume (Spec 111, FR-003, FR-005)

Resume interrupted imports from where they stopped:

```json
{
  "resume": true
}
```

**How it works:**

1. Checkpoint saved after each file (not just batches)
2. Checkpoint stores: folder index, file index, processed/skipped/failed counts
3. Config signature detects filter changes between runs
4. Checkpoint cleared on successful completion

**Checkpoint location:** `.pm-runtime/state/checkpoint_{source_id}.json`

### Validation (Spec 111, FR-007, FR-008)

Validates SGF files before yielding:

```json
{
  "validate": true
}
```

**Validation checks:**

- Valid board size (9x9, 13x13, 19x19)
- Solution tree present (at least one move variation)

**Yield types:**

- `FetchResult.success()` — Valid puzzle
- `FetchResult.skipped()` — Validation failure (invalid board, no solution)
- `FetchResult.failed()` — Parse/IO error (encoding, malformed SGF)

---

## CLI Usage

```bash
# Run full pipeline for a local source
python -m backend.puzzle_manager run --source tsumego

# Run ingest stage only (dry run)
python -m backend.puzzle_manager run --source tsumego --stage ingest

# Resume interrupted import
python -m backend.puzzle_manager run --source tsumego --resume

# Process specific batch size
python -m backend.puzzle_manager run --source tsumego --batch-size 50
```

---

## Directory Structure Support

### Subfolder Structure (Recommended)

```
external-sources/tsumego/problems/
├── elementary/
│   ├── puzzle1.sgf
│   └── puzzle2.sgf
├── intermediate/
│   └── puzzle3.sgf
└── advanced/
    └── puzzle4.sgf
```

### Flat Structure (Supported)

```
external-sources/my-collection/
├── puzzle1.sgf
├── puzzle2.sgf
└── puzzle3.sgf
```

---

## Multi-Source Support

Use different `id` values for separate checkpoints:

```json
[
  {
    "id": "elementary",
    "adapter": "local",
    "config": {
      "path": "external-sources/tsumego/problems",
      "include_folders": ["elementary"]
    }
  },
  {
    "id": "advanced",
    "adapter": "local",
    "config": {
      "path": "external-sources/tsumego/problems",
      "include_folders": ["advanced"]
    }
  }
]
```

---

## Logging

| Level   | Content                                                 |
| ------- | ------------------------------------------------------- |
| INFO    | Folder progress: "Processing folder: elementary (1/3)"  |
| INFO    | Completion summary: "fetched 500, skipped 10, failed 5" |
| DEBUG   | Individual file processing details                      |
| WARNING | Non-existent include folder, config signature mismatch  |

---

## Troubleshooting

### "Path does not exist"

- Verify `path` is correct relative to project root
- Use absolute path if uncertain

### "Config changed since checkpoint"

- Filter settings changed between runs
- Set `resume: false` for fresh start

### "No SGF files in folder"

- Folder exists but contains no `.sgf` files
- Check file extensions (case-sensitive)

### Encoding errors

- Some SGF files may have non-UTF-8 encoding
- These are logged as `failed` with encoding details

---

## Implementation Notes

- **ID Generation**: Content-based SHA256 hash (16 chars) ensures deduplication
- **Deterministic Order**: Alphabetical by folder, then by filename
- **Constitution Compliance**: Build-time only, no runtime backend

---

## Related Adapters

- [SanderlandAdapter](./sanderland.md) — Similar folder/checkpoint pattern for Sanderland collection
- [OGS Adapter](./ogs.md) — API-based adapter with pagination
