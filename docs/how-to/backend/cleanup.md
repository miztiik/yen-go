# Cleanup Utility

> **See also**:
>
> - [Architecture: Integrity](../../architecture/backend/integrity.md) — Cleanup design decisions
> - [How-To: Run Pipeline](./run-pipeline.md) — Pipeline execution
> - [Reference: CLI](../../reference/cli-reference.md) — Full command reference

**Last Updated**: 2026-02-01

How to clean up staging directories and runtime artifacts.

---

## Overview

The cleanup utility removes intermediate files from pipeline runs:

- Staging directories (ingest, analyze)
- Log files
- State files (optional)

---

## Quick Start

```bash
# Clean staging directory only
python -m backend.puzzle_manager clean --target staging

# Clean everything (staging + logs)
python -m backend.puzzle_manager clean --target all
```

---

## Clean Targets

### Staging Only

```bash
python -m backend.puzzle_manager clean --target staging
```

Removes:

- `.pm-runtime/staging/ingest/`
- `.pm-runtime/staging/analyzed/`

Preserves:

- Published output (`yengo-puzzle-collections/`)
- Logs
- State files

Use case: Prepare for fresh pipeline run while keeping logs for debugging.

### All Runtime

```bash
python -m backend.puzzle_manager clean --target all
```

Removes:

- `.pm-runtime/staging/`
- `.pm-runtime/logs/`
- `.pm-runtime/state/` (run history only)

Preserves:

- Published output (`yengo-puzzle-collections/`)
- Current publish logs (for rollback capability)

Use case: Full reset between major pipeline runs.

### Logs Only

```bash
python -m backend.puzzle_manager clean --target logs
```

Removes:

- `.pm-runtime/logs/*.log`

Use case: Clear log files when disk space is low.

---

## Options

### Dry Run

Preview what would be deleted:

```bash
python -m backend.puzzle_manager clean --target staging --dry-run
```

Output:

```
Would remove: .pm-runtime/staging/ingest/
Would remove: .pm-runtime/staging/analyzed/
Dry run complete. No files removed.
```

### Force

Skip confirmation prompt:

```bash
python -m backend.puzzle_manager clean --target all --force
```

Use in CI/CD scripts where interactive prompts aren't available.

### Verbose

Show detailed output:

```bash
python -m backend.puzzle_manager clean --target staging --verbose
```

---

## Runtime Directory Structure

```
.pm-runtime/                          # Default: $PROJECT_ROOT/.pm-runtime
├── staging/
│   ├── ingest/                       # Fetched SGF files
│   │   └── {source}/{batch}/
│   └── analyzed/                     # Enriched SGF files
│       └── {source}/{batch}/
├── logs/
│   ├── pipeline-2026-01-28.log       # Daily log files
│   └── ...
└── state/
    ├── current_run.json              # Current run state
    └── runs/                         # Historical run records
        └── {run_id}.json
```

### Custom Runtime Directory

Override with environment variable:

```bash
# Use custom directory
export YENGO_RUNTIME_DIR=/tmp/yen-go-runtime
python -m backend.puzzle_manager clean --target staging
```

---

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  pipeline:
    steps:
      - name: Run pipeline
        run: |
          python -m backend.puzzle_manager run --source ogs

      - name: Cleanup staging
        if: always() # Run even if pipeline fails
        run: |
          python -m backend.puzzle_manager clean --target staging --force
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

# ... setup ...

# Cleanup hook on container exit
CMD ["sh", "-c", "python -m backend.puzzle_manager run --source ogs && python -m backend.puzzle_manager clean --target staging --force"]
```

---

## When to Clean

| Scenario                      | Recommended Target                       |
| ----------------------------- | ---------------------------------------- |
| After successful pipeline run | `staging`                                |
| After failed pipeline run     | `logs` only (keep staging for debugging) |
| Before release                | `all`                                    |
| Disk space issues             | `staging` then `logs`                    |
| Fresh development start       | `all`                                    |

---

## What's NOT Cleaned

The cleanup utility **never** removes:

| Directory                         | Reason                                  |
| --------------------------------- | --------------------------------------- |
| `yengo-puzzle-collections/`       | Published output - use rollback instead |
| `.pm-runtime/state/publish-logs/` | Required for rollback capability        |
| `config/`                         | Configuration files                     |
| `backend/`                        | Source code                             |

---

## Troubleshooting

### Permission Denied

```bash
# On Unix
chmod -R u+w .pm-runtime/
python -m backend.puzzle_manager clean --target staging

# On Windows (as admin)
icacls .pm-runtime /grant:r %USERNAME%:F /t
python -m backend.puzzle_manager clean --target staging
```

### Directory Not Found

```
Warning: .pm-runtime/staging does not exist. Nothing to clean.
```

This is normal if no pipeline has run yet.

### Cleanup Interrupted

If cleanup is interrupted, some files may remain:

```bash
# Complete the cleanup
python -m backend.puzzle_manager clean --target staging --force
```

---

## Safety Features

1. **Confirmation Prompt**: Default behavior asks for confirmation
2. **Dry Run**: Preview deletions before executing
3. **Protected Directories**: Never removes published output or source code
4. **Publish Logs Preserved**: Rollback capability maintained
5. **Verbose Mode**: See exactly what's being removed
