# CLI Quick Reference

> **See also**:
>
> - [CLI Reference](../how-to/backend/cli-reference.md) — Complete documentation
> - [Run Pipeline](../how-to/backend/run-pipeline.md) — Pipeline guide

**Last Updated**: 2026-02-24

One-page cheat sheet for common pipeline commands.

---

## Pipeline Commands

```bash
# Run full pipeline (--source is REQUIRED)
python -m backend.puzzle_manager run --source yengo-source

# Run specific stage(s)
python -m backend.puzzle_manager run --source yengo-source --stage ingest
python -m backend.puzzle_manager run --stage analyze
python -m backend.puzzle_manager run --stage publish

# With options
python -m backend.puzzle_manager run --source yengo-source --batch-size 50
python -m backend.puzzle_manager run --source yengo-source --dry-run
python -m backend.puzzle_manager run --resume

# Skip enrichment sub-stages
python -m backend.puzzle_manager run --source yengo-source --no-enrichment  # Skip all enrichment
python -m backend.puzzle_manager run --source yengo-source --no-hints       # Skip hint generation
python -m backend.puzzle_manager run --source yengo-source --no-region      # Skip region detection
python -m backend.puzzle_manager run --source yengo-source --no-ko          # Skip ko detection

# Source override (use different adapter for existing staging files)
python -m backend.puzzle_manager run --source yengo-source --source-override
```

## Status Commands

```bash
# Check pipeline status
python -m backend.puzzle_manager status
python -m backend.puzzle_manager status --json
python -m backend.puzzle_manager status --history   # Show run history

# List sources
python -m backend.puzzle_manager sources
python -m backend.puzzle_manager sources --check

# View inventory
python -m backend.puzzle_manager inventory
python -m backend.puzzle_manager inventory --json

# Reconcile inventory from disk (most accurate)
python -m backend.puzzle_manager inventory --reconcile

# Integrity check
python -m backend.puzzle_manager inventory --check
python -m backend.puzzle_manager inventory --check --fix
```

## Cleanup Commands

```bash
# Preview cleanup
python -m backend.puzzle_manager clean --target staging --dry-run
python -m backend.puzzle_manager clean --target state --dry-run
python -m backend.puzzle_manager clean --target all --dry-run

# Execute cleanup
python -m backend.puzzle_manager clean --target staging
python -m backend.puzzle_manager clean --target state
python -m backend.puzzle_manager clean --target all
```

## Rollback Commands

```bash
# Preview rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --dry-run

# Execute rollback
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --yes     # Skip confirmation
python -m backend.puzzle_manager rollback --run-id 20260130-abc12345 --verify  # Verify integrity

# Rollback specific puzzles
python -m backend.puzzle_manager rollback --puzzle-ids puz-001,puz-002
```

## Publish Log Commands

```bash
# List publish logs
python -m backend.puzzle_manager publish-log list

# Search by criteria
python -m backend.puzzle_manager publish-log search --run-id 20260130-abc12345
python -m backend.puzzle_manager publish-log search --source yengo-source
python -m backend.puzzle_manager publish-log search --puzzle-id puz-001
python -m backend.puzzle_manager publish-log search --date 2026-02-20
```

## Validation Commands

```bash
# Validate config and schemas
python -m backend.puzzle_manager validate
```

## Daily Challenge Commands

```bash
# Generate daily challenge
python -m backend.puzzle_manager daily --date 2026-01-28
```

---

## Common Flags

| Flag                 | Description                                      |
| -------------------- | ------------------------------------------------ |
| `--source SOURCE`    | **REQUIRED** for ingest. Source adapter to use.  |
| `--stage STAGE`      | Run specific stage only. Can be repeated.        |
| `--batch-size N`     | Override batch size (default: 2000)              |
| `--drain`            | Process all pending files (overrides batch size) |
| `--dry-run`          | Preview changes without writing                  |
| `--resume`           | Resume from last checkpoint                      |
| `--no-enrichment`    | Skip all enrichment sub-stages                   |
| `--no-hints`         | Skip hint generation                             |
| `--no-region`        | Skip region detection                            |
| `--no-ko`            | Skip ko detection                                |
| `--source-override`  | Allow source mismatch with active_adapter        |
| `--flush-interval N` | Sub-batch state flush interval (default: 500)    |
| `-v, --verbose`      | Increase verbosity (-vv for debug)               |
| `--json`             | Output as JSON                                   |

---

## Environment Variables

| Variable            | Purpose           | Default                          |
| ------------------- | ----------------- | -------------------------------- |
| `YENGO_RUNTIME_DIR` | Runtime directory | `.pm-runtime/`                   |
| `YENGO_LOG_LEVEL`   | Log verbosity     | `INFO`                           |
| `YENGO_CONFIG_DIR`  | Config directory  | `backend/puzzle_manager/config/` |
