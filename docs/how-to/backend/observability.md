# Observability Guide

> **See also**:
>
> - [Architecture: Pipeline](../../architecture/backend/pipeline.md) — Pipeline design and stages
> - [How-To: Run Pipeline](./run-pipeline.md) — Running the pipeline
> - [How-To: Rollback](./rollback.md) — Rolling back puzzles
> - [Reference: Configuration](../../reference/configuration.md) — Config options

**Last Updated**: 2026-03-24

This guide explains how to monitor and analyze the YenGo puzzle collection using the inventory system.

## Overview

The puzzle collection inventory (`puzzle-collection-inventory.json`) provides a single source of truth for collection statistics. It's automatically updated during publish and rollback operations.

## Inventory File

### Location

```
yengo-puzzle-collections/puzzle-collection-inventory.json
```

### Schema

The inventory file follows JSON Schema v1.1. See `config/schemas/puzzle-collection-inventory-schema.json` for full specification.

### Structure

```json
{
  "schema_version": "1.1",
  "last_updated": "2026-01-30T10:00:00Z",
  "last_run_id": "20260130-abc12345",
  "collection": {
    "total_puzzles": 15000,
    "by_puzzle_level": {
      "beginner": 3000,
      "intermediate": 5000,
      "advanced": 4000,
      "low-dan": 2000,
      "high-dan": 1000
    },
    "by_tag": {
      "life-and-death": 8000,
      "tesuji": 4000,
      "ko": 2000,
      "ladder": 1000
    },
    "by_puzzle_quality": {
      "1": 1000,
      "2": 3500,
      "3": 6000,
      "4": 3000,
      "5": 1500
    },
    "avg_quality_score": 4.2,
    "hint_coverage_pct": 85.0
  },
  "stages": {
    "ingest": {"attempted": 16000, "passed": 15500, "failed": 500},
    "analyze": {"enriched": 15200, "skipped": 300},
    "publish": {"new": 15000}
  },
  "metrics": {
    "daily_publish_throughput": 150,
    "error_rate_ingest": 0.031,
    "error_rate_publish": 0.002
  },
  "audit": {
    "total_rollbacks": 3,
    "last_rollback_date": "2026-01-25T14:30:00Z"
  }
}
```

## Update Rules

The inventory is updated automatically:

1. **On Publish**: Increments `total_puzzles`, `by_puzzle_level`, `by_tag`, and `stages.publish.new`
2. **On Rollback**: Decrements counts and increments `audit.total_rollbacks`
3. **On Stage Completion**: Updates `stages.ingest` and `stages.analyze` metrics

### Atomic Updates

All updates use atomic file writes (temp file + rename) to prevent corruption.

### Concurrency

The inventory uses advisory file locking (`filelock` library) to handle concurrent access. Lock timeout is 30 seconds.

## CLI Commands

### View Inventory

```bash
# Human-readable summary
python -m backend.puzzle_manager inventory

# JSON output
python -m backend.puzzle_manager inventory --json

# Rebuild from publish logs
python -m backend.puzzle_manager inventory --rebuild
```

### Sample Output

```
Puzzle Collection Inventory
===========================
Total Puzzles: 15,000

By Level:
  beginner:         3,000 (20.0%)
  intermediate:     5,000 (33.3%)
  advanced:         4,000 (26.7%)
  low-dan:          2,000 (13.3%)
  high-dan:         1,000 (6.7%)

By Tag (top 10):
  life-and-death:   8,000 (53.3%)
  tesuji:           4,000 (26.7%)
  ko:               2,000 (13.3%)
  ladder:           1,000 (6.7%)

By Quality:
  Premium (5):      1,500 (10.0%)
  High (4):         3,000 (20.0%)
  Standard (3):     6,000 (40.0%)
  Basic (2):        3,500 (23.3%)
  Unverified (1):   1,000 (6.7%)

Quality Metrics:
  Average Quality Score: 4.2/5.0
  Hint Coverage: 85.0%

Stage Metrics:
  Ingest:  15,500 passed / 16,000 attempted (96.9%)
  Analyze: 15,200 enriched / 300 skipped
  Publish: 15,000 new

Error Rates:
  Ingest:  3.1%
  Publish: 0.2%

Audit:
  Total Rollbacks: 3
  Last Rollback:   2026-01-25T14:30:00Z

Last Updated: 2026-01-30T10:00:00Z
Last Run ID:  20260130-abc12345
```

## Protection Rules

The inventory file is protected from cleanup operations:

1. **Log cleanup** (`cleanup_old_files`): Does not delete inventory
2. **Staging cleanup** (`cleanup_target staging`): Does not affect inventory
3. **Collection cleanup** (`cleanup_target puzzles-collection`): Preserves inventory

### Why Protected?

The inventory provides historical data that cannot be reconstructed from SGF files alone:
- Rollback counts and dates
- Stage metrics over time
- Error rate trends

If inventory is lost, use `--rebuild` to reconstruct collection stats from publish logs.

## Stage-Level Metrics

### Ingest Stage

| Metric | Description |
|--------|-------------|
| `attempted` | Total puzzles fetched from sources |
| `passed` | Puzzles that passed validation |
| `failed` | Puzzles that failed validation |

### Analyze Stage

| Metric | Description |
|--------|-------------|
| `enriched` | Puzzles with hints/tags added |
| `skipped` | Puzzles already enriched |

### Publish Stage

| Metric | Description |
|--------|-------------|
| `new` | Puzzles published (new files created) |

### Computed Metrics

| Metric | Formula |
|--------|---------|
| `error_rate_ingest` | `failed / attempted` |
| `error_rate_publish` | Errors during write / total writes |
| `daily_publish_throughput` | Average puzzles published per day |

## Monitoring Integration

### Prometheus Metrics

Export inventory metrics to Prometheus (planned):

```yaml
# metrics endpoint: /metrics
yengo_collection_total_puzzles 15000
yengo_collection_by_level{level="beginner"} 3000
yengo_collection_by_level{level="intermediate"} 5000
yengo_stage_ingest_passed 15500
yengo_stage_ingest_failed 500
yengo_audit_rollbacks_total 3
```

### Alerting

Set alerts for:
- `error_rate_ingest > 0.10` (10% failure rate)
- `total_rollbacks` increasing rapidly
- `hint_coverage_pct < 0.50` (50% coverage)

## Troubleshooting

### Inventory Out of Sync

If inventory doesn't match actual collection:

```bash
# Rebuild from publish logs
python -m backend.puzzle_manager inventory --rebuild
```

### Missing Inventory File

If inventory file is deleted:

1. The file will be auto-created on next publish
2. Or rebuild manually: `inventory --rebuild`

### Corrupted Inventory

If JSON is malformed:

1. Delete the corrupted file
2. Rebuild: `inventory --rebuild`

### Counts Don't Match

If `total_puzzles != sum(by_puzzle_level)`:

- Some puzzles may not have level assigned
- Rebuild will correct the counts

## API Reference

### InventoryManager

```python
from backend.puzzle_manager.inventory import InventoryManager

manager = InventoryManager()

# Check if exists
if manager.exists():
    inventory = manager.load()
    print(f"Total: {inventory.collection.total_puzzles}")

# Increment (called by publish stage)
from backend.puzzle_manager.inventory import InventoryUpdate
update = InventoryUpdate(
    puzzles_added=10,
    level_increments={"beginner": 5, "intermediate": 5},
    tag_increments={"life-and-death": 8, "tesuji": 2},
)
manager.increment(update, run_id="20260130-abc12345")

# Decrement (called by rollback)
manager.decrement(
    puzzles_removed=5,
    level_decrements={"beginner": 5},
    tag_decrements={"life-and-death": 3},
    quality_decrements={"3": 3, "4": 2},  # Spec 102
    run_id="rollback-20260131",
)

# Rebuild from logs
from backend.puzzle_manager.inventory import rebuild_and_save
inventory = rebuild_and_save()
```

## Quality Logging

Quality level assignment is logged during the pipeline:

### Analyze Stage

- **DEBUG level**: Per-puzzle quality assignment after enrichment
- **INFO level**: Batch summary with quality distribution

Example batch log:
```
Analyze complete: processed=100, failed=2, skipped=5, duration=12.5s
  quality_summary: "10×Premium, 25×High, 40×Standard, 20×Basic, 5×Unverified"
```

### Publish Stage  

- **INFO level**: Batch summary with quality breakdown

Example batch log:
```
Publish complete: processed=100, failed=0, skipped=0, duration=5.2s
  quality_summary: "10×Premium, 25×High, 40×Standard, 20×Basic, 5×Unverified"
```

### Enabling Debug Logs

To see per-puzzle quality assignment:

```bash
# Set logging level to DEBUG
export YENGO_LOG_LEVEL=DEBUG
python -m backend.puzzle_manager run --source yengo-source --stage analyze
```

## See Also

- [How-To: Run Pipeline](./run-pipeline.md) - Running the pipeline
- [How-To: Rollback](./rollback.md) - Rolling back puzzles
- [Reference: Configuration](../../reference/configuration.md) - Config files
