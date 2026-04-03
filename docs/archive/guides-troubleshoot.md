# Troubleshoot Common Issues

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/how-to/backend/troubleshoot.md](../how-to/backend/troubleshoot.md)
> Archived: 2026-03-24

This guide covers solutions to common problems in the Yen-Go project.

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
   rm state/pipeline_state.json
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
python -m backend.puzzle_manager run --source ogs
```

---

## Frontend Issues

### Development Server Won't Start

```bash
cd frontend
npm install
npm run dev
```

If port 5173 is busy:
```bash
npm run dev -- --port 5174
```

### Tests Failing

1. Run Vitest for unit tests:
   ```bash
   cd frontend && npm test
   ```

2. Run Playwright for e2e tests:
   ```bash
   npx playwright test
   ```

3. Update snapshots if needed:
   ```bash
   npx playwright test --update-snapshots
   ```

### Build Errors

1. Clear cache:
   ```bash
   rm -rf node_modules/.vite
   npm run build
   ```

2. Check TypeScript errors:
   ```bash
   npx tsc --noEmit
   ```

### Opening dist/index.html Directly Shows Blank Page

**Symptoms**: Double-clicking `frontend/dist/index.html` shows a blank page or console errors about missing files.

**Why This Happens**: The production build uses absolute paths (`/yen-go/assets/...`) that only work when served via HTTP, not from the filesystem.

| Method | Protocol | Works? |
|--------|----------|--------|
| Double-click index.html | `file://` | ❌ No |
| `npm run preview` | `http://localhost:4173` | ✅ Yes |
| GitHub Pages | `https://...github.io/yen-go/` | ✅ Yes |

**Solution**: Always use `npm run preview` to test production builds:

```bash
cd frontend
npm run build
npm run preview
# → Open http://localhost:4173/yen-go/
```

Or use the combined command:
```bash
npm run build:preview
```

**Note**: The preview server simulates exactly what GitHub Pages will serve. If it works in preview, it will work on GitHub Pages.

---

## CI/CD Issues

For GitHub Actions troubleshooting, see the dedicated [GitHub Actions Reference](../reference/github-actions.md#troubleshooting).

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

## Import Issues

### SGF Files Won't Parse

1. Validate SGF syntax:
   ```bash
   yengo-pm puzzle validate --file puzzle.sgf
   ```

2. Check for encoding issues (should be UTF-8)

3. Verify SGF properties:
   - Must have `SZ[]` (board size)
   - Must have `AB[]` or `AW[]` (stones)
   - Must have solution tree

### Source Connection Failures

1. Test source connection:
   ```bash
   yengo-pm sources test my-source
   ```

2. Check rate limits - some sources need 60s+ delays

3. Verify API endpoints are accessible

### Batch Processing Stops Mid-way

1. Use `--resume` to continue:
   ```bash
   yengo-pm ingest --source my-source --resume
   ```

2. Check checkpoint file:
   ```bash
   cat state/adapters/my-source_checkpoint.json
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
cd puzzle_manager
pip install -e .
```

### Node.js Version Issues

Frontend requires Node.js 18+:
```bash
node --version
```

---

## Rollback Issues

### Rollback Not Finding Puzzles

1. Verify run ID format (e.g., `2026-01-25T120000`)
2. Check publish logs exist:
   ```bash
   yengo-pm publish-log list
   ```

### Indexes Not Regenerating

After rollback, manually trigger:
```bash
yengo-pm pipeline run --stage index
```

---

## Getting Help

### View Logs

```bash
# List log files
yengo-pm logs --list

# Show specific log
yengo-pm logs --show puzzle_manager.log

# Tail recent entries
yengo-pm logs --tail 50

# Search for errors
yengo-pm logs --grep "ERROR"
```

### Command Help

```bash
yengo-pm --help
yengo-pm pipeline --help
yengo-pm cleanup --help
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YENGO_CONFIG` | Config file path | `config/pipeline.json` |
| `YENGO_LOG_LEVEL` | Log level | `INFO` |
| `YENGO_MOCK_SOLVER` | Use mock solver | `0` |
| `KATAGO_PATH` | KataGo binary path | Auto-detect |

---

## See Also

- [guides/rollback.md](rollback.md) - Rollback published puzzles
- [reference/puzzle-manager-cli.md](../reference/puzzle-manager-cli.md) - CLI reference
- [architecture/backend/testing.md](../architecture/backend/testing.md) - Test patterns
- [getting-started/develop.md](../getting-started/develop.md) - Developer setup
