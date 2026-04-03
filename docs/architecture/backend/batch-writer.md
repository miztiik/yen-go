# BatchWriter Module

High-performance batch directory management for SGF file publishing.

**Last Updated**: 2026-02-20

## Overview

The `batch_writer` module provides utilities for organizing SGF puzzle files into
flat batch directories with:

- **O(1) fast path** for high-throughput publishing using in-memory state tracking
- **O(N) fallback** with filesystem scanning for recovery/initialization
- **Schema versioning** for forward/backward compatibility
- **Crash recovery** via filesystem reconstruction (supports legacy layout)

## Path Structure

```
{sgf_root}/{NNNN}/{puzzle_id}.sgf

Example:
sgf/0001/abc123def456.sgf
sgf/0001/xyz789ghi012.sgf
sgf/0002/fed987cba654.sgf
```

All puzzles share a single global batch counter regardless of difficulty level.
The level is stored in each SGF file (`YG` property) and in view index entries
(`l` field), NOT in the directory path.

## Configuration

Batch sizes are configured in `pipeline.json`, not hardcoded:

| Setting                   | Default | Purpose                           |
| ------------------------- | ------- | --------------------------------- |
| `batch.max_files_per_dir` | 2000    | Max SGF files per batch directory |
| `batch.size`              | 2000    | Max puzzles per pipeline run      |

**Source of truth**: `backend/puzzle_manager/config/pipeline.json`

`BatchWriter` requires `max_files_per_dir` as a parameter — it has no default.
Callers must pass the value from `BatchConfig.max_files_per_dir`.

## Quick Start

### Basic Usage (O(N) fallback)

```python
from backend.puzzle_manager.core.batch_writer import BatchWriter

writer = BatchWriter(sgf_root, max_files_per_dir=2000)

# Get next batch number (scans filesystem)
batch_num = writer.get_next_batch_number()

# Get/create batch directory
batch_dir = writer.get_batch_dir(batch_num)

# Write file
output_path = batch_dir / "puzzle_id.sgf"
output_path.write_text(sgf_content)
```

### High-Performance Usage (O(1) fast path)

```python
from backend.puzzle_manager.core.batch_writer import BatchWriter, BatchState

writer = BatchWriter(sgf_root, max_files_per_dir=2000)

# Load or recover global state
state = BatchState.load_or_recover(sgf_root, batch_size=2000)

for puzzle in puzzles:
    # O(1) batch directory resolution (no filesystem scan)
    batch_dir, batch_num = writer.get_batch_dir_fast(
        state.current_batch, state.files_in_current_batch
    )

    # Write file
    output_path = batch_dir / f"{puzzle.id}.sgf"
    output_path.write_text(puzzle.content)

    # Update state AFTER successful write
    state.record_file_saved(batch_size=2000)

# Save state for crash recovery
state.save(sgf_root)
```

## API Reference

### BatchWriter

Main class for batch directory management.

| Method                             | Complexity | Description                    |
| ---------------------------------- | ---------- | ------------------------------ |
| `get_next_batch_number()`          | O(N)       | Scan filesystem for next batch |
| `get_batch_dir(batch_num)`         | O(1)       | Get/create batch directory     |
| `get_batch_dir_fast(batch, files)` | O(1)       | Fast path with state           |
| `is_batch_full(batch_num)`         | O(N)       | Check if batch is full         |
| `advance_batch()`                  | O(1)       | Increment cached batch number  |
| `clear_cache()`                    | O(1)       | Clear cached batch number      |
| `get_batch_summary()`              | O(N)       | Stats for all batches          |

### BatchState

Persistent state tracking for O(1) operations.

| Method                                          | Description                         |
| ----------------------------------------------- | ----------------------------------- |
| `load(state_dir)`                               | Load state from file                |
| `save(state_dir)`                               | Save state atomically               |
| `load_or_recover(sgf_root, batch_size)`         | Load or recover from filesystem     |
| `recover_from_filesystem(sgf_root, batch_size)` | Reconstruct state from files        |
| `record_file_saved(batch_size)`                 | Update state after successful write |
| `record_error(error)`                           | Track errors for debugging          |

## Design Decisions

### Flat vs. Per-Level Directories

**Decision**: Flat `sgf/{NNNN}/` (no level nesting).

**Rationale**:

- Frontend `expandPath("0001/hash")` → `sgf/0001/hash.sgf` works directly
- No path reconstruction ambiguity in compact view entries
- Simpler rollback (single global batch counter)
- Difficulty reassessment doesn't require file moves

### Global Batch Counter

**Decision**: Single `.batch-state.json` at `sgf_root`, shared by all levels.

**Rationale**:

- Puzzles of all levels coexist in the same batch directories
- Simpler state management (one file, not per-level)
- Batch numbers are purely a sharding mechanism, not semantic

### Config-Driven Batch Size

**Decision**: `max_files_per_dir` is a required parameter (no default in BatchWriter).

**Rationale**:

- Single source of truth: `pipeline.json` → `BatchConfig` → `BatchWriter`
- No silent default shadowing
- Easy to override for testing (tests use `max_files_per_dir=10`)

### Legacy Format Support

`recover_from_filesystem()` supports both:

- **New**: `sgf/{NNNN}/*.sgf` directories
- **Legacy**: `sgf/{level}/batch-{NNNN}/*.sgf` directories (fallback scan)

> **See also**:
>
> - [Architecture: Pipeline](../../../docs/architecture/backend/pipeline.md) — Pipeline overview
> - [How-To: Run Pipeline](../../../docs/how-to/backend/run-pipeline.md) — Operations guide
