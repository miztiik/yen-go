# Getting Started: Operators

> **See also**:
>
> - [Run Pipeline](../how-to/backend/run-pipeline.md) — Full pipeline guide
> - [CLI Quick Reference](../reference/cli-quick-ref.md) — Command cheat sheet
> - [Troubleshooting](../how-to/backend/troubleshoot.md) — Common errors & fixes

**Last Updated**: 2026-03-09

Quick guide for operators who need to run the puzzle pipeline.

---

## Prerequisites

- Python 3.11+
- Access to the Yen-Go repository

## Installation

```bash
# Clone repository
git clone https://github.com/your-org/yen-go.git
cd yen-go

# Install puzzle manager
pip install -e "./backend/puzzle_manager[dev]"

# Verify installation
python -m backend.puzzle_manager --version
```

---

## Your First Pipeline Run

### 1. Check Available Sources

```bash
python -m backend.puzzle_manager sources
```

### 2. Run a Small Test

```bash
# Dry run first (preview only)
python -m backend.puzzle_manager run --source <source_id> --batch-size 5 --dry-run

# If it looks good, run for real
python -m backend.puzzle_manager run --source <source_id> --batch-size 5
```

### 3. Check Results

```bash
# Check status
python -m backend.puzzle_manager status

# View inventory
python -m backend.puzzle_manager inventory
```

---

## Common Operations

| Task               | Command                                                                    |
| ------------------ | -------------------------------------------------------------------------- |
| Run full pipeline  | `python -m backend.puzzle_manager run --source <source_id>`                |
| Run specific stage | `python -m backend.puzzle_manager run --source <source_id> --stage ingest` |
| Check status       | `python -m backend.puzzle_manager status`                                  |
| View inventory     | `python -m backend.puzzle_manager inventory`                               |
| Preview rollback   | `python -m backend.puzzle_manager rollback --run-id X --dry-run`           |
| Clean staging      | `python -m backend.puzzle_manager clean --target staging`                  |

---

## Next Steps

- [Run Pipeline](../how-to/backend/run-pipeline.md) — Detailed pipeline guide
- [Configure Sources](../how-to/backend/configure-sources.md) — Source setup
- [Monitor](../how-to/backend/monitor.md) — Observability
- [Rollback](../how-to/backend/rollback.md) — Undoing imports
