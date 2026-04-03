# Rollback Guide

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/how-to/backend/rollback.md](../how-to/backend/rollback.md)
> Archived: 2026-03-24

This guide covers how to rollback puzzles published by the pipeline.

## When to Use Rollback

- **Bad import**: A pipeline run imported corrupted or incorrect puzzles
- **Quality issue**: Specific puzzles failed quality review after publication
- **Testing cleanup**: Remove test puzzles from production collections

## Rollback Commands

### Rollback by Run ID

Remove all puzzles from a specific pipeline run:

```bash
# Preview what would be deleted
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

## What Rollback Does

1. **Validates** all puzzle IDs exist (fails fast if any missing)
2. **Acquires lock** to prevent concurrent rollbacks
3. **Backs up** files to `.rollback-backup/` directory
4. **Deletes** SGF files from collections
5. **Updates** level and tag indexes (removes deleted entries)
6. **Writes** audit log entry
7. **Releases** lock and cleans up backup

If any step fails, files are restored from backup.

## Audit Trail

All rollback operations are logged to:

```
yengo-puzzle-collections/publish-log/rollback-audit.jsonl
```

View recent rollbacks:

```bash
tail -20 yengo-puzzle-collections/publish-log/rollback-audit.jsonl | jq
```

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
ls yengo-puzzle-collections/.rollback-backup/
```

If backup directory exists with files, restoration was incomplete. Contact maintainer.

## Best Practices

1. **Always use --dry-run first** to preview changes
2. **Document the reason** in commit message when committing rollback
3. **Verify indexes** after large rollbacks with `--verify` flag
4. **Check audit log** to confirm operation completed

---

*See also: [Troubleshoot Common Issues](troubleshoot.md)*
