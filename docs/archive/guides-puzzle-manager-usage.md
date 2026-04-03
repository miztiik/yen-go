# Puzzle Manager Usage Guide

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/how-to/backend/cli-reference.md](../how-to/backend/cli-reference.md)
> Archived: 2026-03-24

This guide covers the puzzle manager CLI, with particular emphasis on source (adapter) selection behavior.

## Quick Start

```bash
# Run full pipeline with active adapter
python -m backend.puzzle_manager run

# Run specific stages
python -m backend.puzzle_manager run --stage ingest
python -m backend.puzzle_manager run --stage analyze --stage publish

# Check status
python -m backend.puzzle_manager status
python -m backend.puzzle_manager sources
```

## Source Selection Behavior

The puzzle manager uses a **source adapter** to fetch puzzles from external sources (OGS, GoProblems, Sanderland, etc.). Understanding how source selection works is essential for effective pipeline operations.

### Key Concepts

| Concept | Description |
|---------|-------------|
| `active_adapter` | The default adapter set in `sources.json`. Used when `--source` is not specified. |
| `--source` | CLI flag to specify which adapter to use for the **ingest stage only**. |
| `--source-override` | Required when `--source` differs from `active_adapter`. Safety mechanism. |
| `enable-adapter` | Command to change the `active_adapter` in `sources.json`. |
| `disable-adapter` | Command to clear the `active_adapter` (requires explicit `--source`). |

### The Pipeline Stages

The puzzle manager has 3 stages:

1. **ingest** - Fetches puzzles from source → writes to `.pm-runtime/staging/`
2. **analyze** - Enriches puzzles (hints, tags, level) → updates staging files
3. **publish** - Writes finalized SGF to `yengo-puzzle-collections/`

**Important**: The `--source` flag only affects the **ingest** stage. The analyze and publish stages process whatever is in the staging directory.

### Source Selection Rules

| Scenario | `--source` | `--source-override` | Result |
|----------|-----------|---------------------|--------|
| Default operation | Not specified | N/A | Uses `active_adapter` |
| Source matches active | `--source X` (X == active) | Not needed | Proceeds normally |
| Source differs from active | `--source X` (X != active) | Not specified | **ERROR + exit** |
| Source differs with override | `--source X` (X != active) | `--source-override` | Proceeds with warning |
| No source, no active | Not specified | N/A | **ERROR + exit** |

### Why This Design?

The override requirement prevents accidental data mixing:

- **Scenario**: Active adapter is `ogs`, you run `--source sanderland` by mistake
- **Without safety**: Sanderland puzzles get ingested, but analyze/publish might process OGS leftovers
- **With safety**: CLI stops you with clear error message

## Command Reference

### run - Execute Pipeline

```bash
# Full pipeline with active adapter
python -m backend.puzzle_manager run

# Specific stages only
python -m backend.puzzle_manager run --stage ingest
python -m backend.puzzle_manager run --stage analyze --stage publish

# With different source (requires override if different from active)
python -m backend.puzzle_manager run --source ogs
python -m backend.puzzle_manager run --source sanderland --source-override

# Dry run (no file changes)
python -m backend.puzzle_manager run --dry-run
```

### ingest - Fetch Puzzles

```bash
# Ingest with active adapter
python -m backend.puzzle_manager ingest

# Ingest from specific source
python -m backend.puzzle_manager ingest ogs
python -m backend.puzzle_manager ingest sanderland --source-override

# Limited batch size
python -m backend.puzzle_manager ingest --batch-size 50
```

### enable-adapter - Set Active Adapter

```bash
# Set OGS as the active adapter
python -m backend.puzzle_manager enable-adapter ogs

# Set Sanderland as the active adapter  
python -m backend.puzzle_manager enable-adapter sanderland

# Verify change
python -m backend.puzzle_manager sources
```

### disable-adapter - Clear Active Adapter

```bash
# Disable the active adapter
python -m backend.puzzle_manager disable-adapter

# Now --source is required
python -m backend.puzzle_manager run --source ogs
```

### sources - List Configured Sources

```bash
# List all sources
python -m backend.puzzle_manager sources

# Check source availability
python -m backend.puzzle_manager sources --check

# JSON output
python -m backend.puzzle_manager sources --json
```

## Common Workflows

### Daily Operations (Standard)

Uses the configured `active_adapter`:

```bash
# Check current active adapter
python -m backend.puzzle_manager sources

# Run full pipeline
python -m backend.puzzle_manager run

# Check results
python -m backend.puzzle_manager status
```

### Testing a Different Adapter

When you want to test a different source without changing the default:

```bash
# Current active: ogs
# Want to test: goproblems

# This requires --source-override since it differs from active
python -m backend.puzzle_manager run --source goproblems --source-override --dry-run

# See the warning in output
⚠️  Source overridden to 'goproblems' (active_adapter is 'ogs'). --source-override flag present.
```

### Permanently Changing Adapters

When switching to a different source for ongoing work:

```bash
# Change the active adapter
python -m backend.puzzle_manager enable-adapter sanderland

# Verify
python -m backend.puzzle_manager sources
# Output: Active adapter: sanderland

# Now run normally (no --source needed)
python -m backend.puzzle_manager run
```

### Clearing Active Adapter

If you prefer explicit source specification every time:

```bash
# Disable the active adapter
python -m backend.puzzle_manager disable-adapter

# Now commands require --source
python -m backend.puzzle_manager run
# ERROR: No --source specified and no active_adapter configured

python -m backend.puzzle_manager run --source ogs
# Works!
```

## Error Messages

### "No active_adapter configured"

```
❌ ERROR: No --source specified and no active_adapter configured
   To proceed, either:
   1. Specify a source: run --source ogs
   2. Set an active adapter: enable-adapter ogs
```

**Solution**: Either specify `--source` explicitly or set an active adapter with `enable-adapter`.

### "Source differs from active_adapter"

```
❌ ERROR: --source 'sanderland' differs from active_adapter 'ogs'
   To proceed, either:
   1. Add --source-override flag: run --source sanderland --source-override
   2. Change active adapter: enable-adapter sanderland
```

**Solution**: Either add `--source-override` for a one-time override, or change the active adapter if you want to switch permanently.

### "Warning: --source only affects ingest stage"

```
⚠️  --source 'ogs' only affects 'ingest' stage; ignored for ['analyze', 'publish']
```

**Explanation**: This warning appears when you use `--source` with non-ingest stages. The source flag only affects which adapter fetches puzzles; analyze and publish process existing staging files.

## Configuration Files

### sources.json

Located at `backend/puzzle_manager/config/sources.json`:

```json
{
  "active_adapter": "ogs",
  "sources": [
    {
      "id": "ogs",
      "name": "OGS Puzzles",
      "adapter": "ogs",
      "config": { ... }
    },
    {
      "id": "sanderland",
      "name": "Sanderland Collection",
      "adapter": "sanderland",
      "config": { ... }
    }
  ]
}
```

The `active_adapter` field is managed by the `enable-adapter` and `disable-adapter` commands. You can also edit it directly.

### Runtime Directories

| Directory | Purpose |
|-----------|---------|
| `.pm-runtime/staging/` | Ingested puzzles awaiting enrichment |
| `.pm-runtime/state/` | Pipeline state and checkpoints |
| `.pm-runtime/logs/` | Log files |
| `yengo-puzzle-collections/` | Published SGF files |

## Logging

When source override is used, messages are logged to both console and log file:

- **Console**: `⚠️  Source overridden to 'X' (active_adapter is 'Y')...`
- **Log file**: `WARNING - Source overridden to 'X' (active_adapter is 'Y')...`

This dual logging ensures administrators can track when overrides were used.

## See Also

- [CLI Reference](../reference/puzzle-manager-cli.md) - Full command documentation
- [Adapter Design Standards](../architecture/backend/adapter-design-standards.md) - How adapters work
- [Configuration Guide](../reference/configuration.md) - All config options
