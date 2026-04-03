# Rollback Guide

> **See also**:
>
> - [Architecture: Integrity](../../architecture/backend/integrity.md) — Why this design
> - [Run Pipeline](./run-pipeline.md) — Operating the pipeline
> - [Monitor](./monitor.md) — Observability and logs

**Last Updated**: 2026-03-14

This guide covers how to rollback puzzles published by the pipeline.

---

## When to Use Rollback

- **Bad import**: A pipeline run imported corrupted or incorrect puzzles
- **Quality issue**: Specific puzzles failed quality review after publication
- **Testing cleanup**: Remove test puzzles from production collections

---

## Rollback Commands

### Rollback by Run ID

Remove all puzzles from a specific pipeline run:

```bash
# Preview what would be deleted (always do this first!)
python -m backend.puzzle_manager rollback --run-id 20260129-a1b2c3d4 --dry-run

# Execute rollback
python -m backend.puzzle_manager rollback --run-id 20260129-a1b2c3d4
```

### Rollback Specific Puzzles

Remove specific puzzles by ID:

```bash
# Preview
python -m backend.puzzle_manager rollback --puzzle-ids puz-001,puz-002 --dry-run

# Execute
python -m backend.puzzle_manager rollback --puzzle-ids puz-001,puz-002
```

---

## Safety Features

### Dry Run Mode

Always preview before executing:

```bash
python -m backend.puzzle_manager rollback --run-id 20260129-a1b2c3d4 --dry-run
```

Output shows what would be deleted without making changes.

### Confirmation Prompt

Rollbacks affecting >100 puzzles require confirmation:

```
About to delete 150 puzzles. Continue? [y/N]
```

Skip with `--yes` flag (use carefully):

```bash
python -m backend.puzzle_manager rollback --run-id X --yes
```

### Verification

Verify file counts after rollback:

```bash
python -m backend.puzzle_manager rollback --run-id X --verify
```

---

## Finding Puzzles to Rollback

### Search Publish Logs

Find puzzles by source:

```bash
python -m backend.puzzle_manager publish-log search --source sanderland
```

Find puzzles by date:

```bash
python -m backend.puzzle_manager publish-log list --date 2026-01-29
```

Find specific puzzle:

```bash
python -m backend.puzzle_manager publish-log search --puzzle-id puz-001
```

---

## What Rollback Does

1. **Validates** all puzzle IDs exist in publish log (fails fast if none found)
2. **Acquires lock** to prevent concurrent rollbacks
3. **Deletes** SGF files from collections
4. **Rebuilds database** — reads existing entries from `yengo-content.db`, removes deleted puzzle IDs, rebuilds `yengo-search.db` with remaining entries
5. **Rebuilds inventory** from disk (puzzle totals, tag counts)
6. **Releases** lock

If all puzzles are deleted, `db-version.json` is updated to reflect zero puzzles.

> **Note**: Rollback uses DB-based rebuild (not surgical index updates). The publish stage reads all entries from `yengo-content.db`, filters out deleted puzzles, and rebuilds `yengo-search.db`. This is simple and correct — at 500K puzzles, rebuild takes <10 seconds.

---

## Integrity Check

After rollback, verify inventory is consistent:

```bash
# Check integrity (reports discrepancies)
python -m backend.puzzle_manager inventory --check

# Check and auto-fix (rebuilds inventory if issues found)
python -m backend.puzzle_manager inventory --check --fix
```

The integrity check verifies:

- `total_puzzles` matches actual SGF file count
- Level counts match files per level directory
- No orphan publish log entries (entry exists, file missing)
- No orphan files (file exists, no publish log entry)

---

## Audit Trail

All rollback operations are logged to:

```
yengo-puzzle-collections/.puzzle-inventory-state/audit.jsonl
```

View recent rollbacks:

```bash
tail -20 yengo-puzzle-collections/.puzzle-inventory-state/audit.jsonl | jq
```

---

## Troubleshooting

### "Lock held by another process"

Another rollback is in progress. Wait for completion or check for stale lock:

```bash
cat yengo-puzzle-collections/publish-log/.rollback.lock
```

Locks older than 1 hour are automatically cleaned.

### "No puzzles found for run_id"

The run ID doesn't exist in publish logs. Check available runs:

```bash
python -m backend.puzzle_manager publish-log list
```

### Rollback Failed Mid-Way

Files are automatically restored from backup. Check:

```bash
ls yengo-puzzle-collections/.puzzle-inventory-state/rollback-backup/
```

If backup directory exists with files, restoration was incomplete. Contact maintainer.

---

## Best Practices

1. **Always dry-run first**: Preview before executing
2. **Document reason**: Note why rollback was needed
3. **Verify after**: Check indexes are correct
4. **Small scope**: Prefer targeted rollbacks over full-run rollbacks
