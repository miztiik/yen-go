# Troubleshoot Common Issues

> **See also**:
>
> - [Architecture: Pipeline Design](../../architecture/backend/pipeline.md) — How the pipeline works
> - [Run Pipeline](./run-pipeline.md) — Operating the pipeline
> - [Rollback](./rollback.md) — Undoing bad imports
> - [Configure Sources](./configure-sources.md) — Source configuration

**Last Updated**: 2026-03-10

This guide covers solutions to common problems in the Yen-Go puzzle pipeline.

---

## Quick Reference: Error → Solution

| Error Message                          | Likely Cause                        | Quick Fix                                  |
| -------------------------------------- | ----------------------------------- | ------------------------------------------ |
| `Source 'xyz' not found`               | Typo or missing source              | `python -m backend.puzzle_manager sources` |
| `--source is required`                 | Missing required flag               | Add `--source <name>` to command           |
| `Source differs from active_adapter`   | Safety check                        | Use `--source-override` flag               |
| `AdapterNotFoundError`                 | Adapter not registered              | Check `@register_adapter` decorator        |
| `No puzzles found`                     | Empty source or filter too strict   | Check source config filters                |
| `SGFParseError`                        | Invalid SGF format                  | Validate with `parse_sgf()`                |
| `Checkpoint not found`                 | State reset                         | Remove `--resume` flag                     |
| `Permission denied`                    | Write access issue                  | Check directory permissions                |
| `Connection timeout`                   | Network/API issue                   | Check source URL, increase timeout         |
| `Skipping corrupted publish log entry` | Crash left truncated JSONL line     | Automatic — self-healing on next read      |
| `Failed to update inventory`           | Inventory write error after publish | `inventory --reconcile`                    |

---

## Crash Recovery

### Orphaned SGF Files After Crash

**Symptoms**: Pipeline crashed during publish. Some SGF files were written but don't appear in the frontend.

**Cause**: The snapshot (which the frontend reads) is built at the end of the publish loop. A crash mid-loop means written SGFs have publish log entries but aren't in the snapshot.

**Fix**: **Automatic** — the next `--stage publish` run detects the crashed run via state file (O(1) check), reads its publish log entries, and includes any orphans in the new snapshot. No user action required.

### Corrupted Publish Log

**Symptoms**: `publish-log search` reports `Skipping corrupted publish log entry` warnings.

**Cause**: A crash truncated the last JSONL line during write-ahead logging.

**Fix**: **Self-healing** — the reader automatically skips malformed lines and processes all valid entries. The truncated line represents at most one puzzle. That puzzle's SGF file is either:

- Still in `staging/analyzed/` (cleanup never ran) → re-processed on next run
- Recovered via orphan recovery → included in next snapshot

### Inventory Shows Zero But Files Exist

**Symptoms**: `inventory.json` has `total_puzzles: 0` but SGF files exist in
`yengo-puzzle-collections/sgf/`. The `last_run_id` may show `clean-{timestamp}`.

**Root Cause (fixed 2026-03-10)**: A test isolation bug in `test_inventory_protection.py`
caused `_reset_inventory()` to write to the real `inventory.json` every time the test
suite ran. The test patched `get_output_dir` but not `_reset_inventory`, which resolves
its own path independently via `InventoryManager()`. Two defense-in-depth fixes were
also applied: audit entry is now written before inventory reset (preventing silent
state corruption), and `cleanup_target("puzzles-collection")` now defaults to dry-run
unless `dry_run=False` is explicitly passed.

**Fix**: Reconcile inventory from the ground truth (actual SGF files on disk):

```bash
python -m backend.puzzle_manager inventory --reconcile
```

This scans all SGF files, extracts metadata from root properties, and rebuilds
inventory counts. See [Architecture: Inventory Operations](../../architecture/backend/inventory-operations.md) for details on the error isolation design.

---

## Pipeline Issues

### Pipeline Stuck or Won't Proceed

**Symptoms**: `python -m backend.puzzle_manager run` hangs or reports no progress.

**Solutions**:

1. Check current state:

   ```bash
   python -m backend.puzzle_manager status
   ```

2. Reset state only (keeps staging files):

   ```bash
   python -m backend.puzzle_manager clean --target state
   ```

3. Manually remove state file:

   ```bash
   rm .pm-runtime/state/current_run.json
   ```

4. Resume from specific stage:
   ```bash
   python -m backend.puzzle_manager run --stage analyze
   ```

### Missing Puzzles in Output

**Symptoms**: Fewer puzzles than expected in `yengo-puzzle-collections/`.

**Solutions**:

1. Check for failures:

   ```bash
   cat .pm-runtime/state/failures/*.json
   ```

2. Resume from last checkpoint:

   ```bash
   python -m backend.puzzle_manager run --resume
   ```

3. Review logs for errors:
   ```bash
   grep -r "ERROR" .pm-runtime/logs/
   ```

### Full Reset (Nuclear Option)

When nothing else works:

```bash
# Preview
python -m backend.puzzle_manager clean --target all --dry-run

# Execute - clears staging, state, and logs
python -m backend.puzzle_manager clean --target all

# Re-run pipeline from scratch
python -m backend.puzzle_manager run --source yengo-source
```

---

## Source/Adapter Issues

### Source Not Found

**Error**: `Source 'xyz' not found in sources.json`

**Solutions**:

1. List available sources:

   ```bash
   python -m backend.puzzle_manager sources
   ```

2. Check configuration in `backend/puzzle_manager/config/sources.json`

### Source Connection Failures

1. Test source availability:

   ```bash
   python -m backend.puzzle_manager sources --check
   ```

2. Check rate limits - some sources need delays between requests

3. Verify network access to source URLs

### Source Override Required

**Error**: `Source 'X' differs from active_adapter 'Y'. Use --source-override to proceed.`

This safety check prevents accidental mixing of data from different sources.

**Solutions**:

1. Use the expected source:

   ```bash
   python -m backend.puzzle_manager run --source Y
   ```

2. Or explicitly override:
   ```bash
   python -m backend.puzzle_manager run --source X --source-override
   ```

See [Configure Sources](./configure-sources.md) for details on `active_adapter` and `--source-override`.

---

## Import Issues

### SGF Files Won't Parse

1. Validate SGF syntax:

   ```bash
   python -c "from backend.puzzle_manager.core.sgf_parser import parse_sgf; parse_sgf(open('puzzle.sgf').read())"
   ```

2. Check for encoding issues (should be UTF-8)

3. Verify SGF properties:
   - Must have `SZ[]` (board size)
   - Must have `AB[]` or `AW[]` (stones)
   - Must have solution tree

### Batch Processing Stops Mid-way

1. Use `--resume` to continue:

   ```bash
   python -m backend.puzzle_manager run --resume
   ```

2. Check checkpoint file:
   ```bash
   cat .pm-runtime/state/current_run.json
   ```

---

## Configuration Issues

### Invalid tags.json

**Symptoms**: Tag validation errors.

**Solutions**:

1. Validate JSON syntax:

   ```bash
   python -m json.tool config/tags.json
   ```

2. Check required fields:
   - `tags` array must exist
   - `aliases` map tags to canonical names

### Invalid puzzle-levels.json

1. Verify 9-level system (novice → expert)
2. Check level IDs are sequential 1-9
3. Verify rank ranges don't overlap

### Logging Not Working

1. Check `config/logging.json` exists
2. Verify log directory is writable
3. Set log level explicitly:
   ```bash
   export YENGO_LOG_LEVEL=DEBUG
   ```

---

## Environment Issues

### Python Version Mismatch

Requires Python 3.11+:

```bash
python --version
```

### Missing Dependencies

```bash
cd backend/puzzle_manager
pip install -e ".[dev]"
```

### Runtime Directory Issues

Default runtime directory is `.pm-runtime/` at project root.

Override with environment variable:

```bash
export YENGO_RUNTIME_DIR=/custom/path
python -m backend.puzzle_manager run --source yengo-source
```

---

## Rollback Issues

### Rollback Not Finding Puzzles

1. Verify run ID format (e.g., `20260130-abc12345`)
2. Check publish logs exist:
   ```bash
   python -m backend.puzzle_manager publish-log list
   ```

### Indexes Not Regenerating

After rollback, manually trigger publish:

```bash
python -m backend.puzzle_manager run --stage publish
```

---

## Getting Help

### View Logs

```bash
# Recent logs
tail -100 .pm-runtime/logs/pipeline.jsonl | jq .

# Search for errors
grep '"level":"ERROR"' .pm-runtime/logs/pipeline.jsonl
```

### Command Help

```bash
python -m backend.puzzle_manager --help
python -m backend.puzzle_manager run --help
python -m backend.puzzle_manager clean --help
```

### Environment Variables

| Variable            | Purpose           | Default                          |
| ------------------- | ----------------- | -------------------------------- |
| `YENGO_RUNTIME_DIR` | Runtime directory | `.pm-runtime/`                   |
| `YENGO_LOG_LEVEL`   | Log verbosity     | `INFO`                           |
| `YENGO_CONFIG_DIR`  | Config directory  | `backend/puzzle_manager/config/` |
