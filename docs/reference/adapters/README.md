# Adapter Reference

> **See also**:
>
> - [How-To: Create Adapter](../../how-to/backend/create-adapter.md) — Step-by-step guide
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Design patterns
> - [Concepts: Puzzle Validation](../../concepts/puzzle-validation.md) — Centralized validation rules

**Last Updated**: 2026-03-09

Quick reference for all available puzzle adapters.

---

## Centralized Validation

All adapters use `PuzzleValidator` for consistent validation (Spec 108):

```python
from backend.puzzle_manager.core.puzzle_validator import PuzzleValidator, PuzzleData

validator = PuzzleValidator()  # Uses config/puzzle-validation.json
result = validator.validate(puzzle_data)
if not result.is_valid:
    yield FetchResult.skipped(puzzle_id, reason=result.rejection_reason)
```

Validation rules (configurable per-source):

- Board dimensions: 5-19 (non-square allowed)
- Solution required
- Minimum 2 stones
- Maximum 30 solution depth

---

## Available Adapters

| Adapter                     | Type        | Resume | Validation | Status | Config Docs                |
| --------------------------- | ----------- | ------ | ---------- | ------ | -------------------------- |
| [sanderland](sanderland.md) | GitHub      | ✓      | ✓          | Active | [Reference](sanderland.md) |
| [kisvadim](kisvadim.md)     | File System | ✗      | ✗          | Active | [Reference](kisvadim.md)   |
| [travisgk](travisgk.md)     | File System | ✗      | ✗          | Active | [Reference](travisgk.md)   |
| [local](local.md)           | File System | ✓      | ✓          | Active | [Reference](local.md)      |

---

## Quick Commands

```bash
# List all configured sources
python -m backend.puzzle_manager sources

# Run specific adapter
python -m backend.puzzle_manager run --source <adapter-id> --batch-size 100

# Check status
python -m backend.puzzle_manager status
```

---

## Configuration File

All adapters are configured in:

```text
backend/puzzle_manager/config/sources.json
```

---

## Adapter Types

### API-Based (With Resume)

- API-backed source adapters
- Scraper-backed source adapters

### File-Based (No Resume)

- Repository/file-fetch adapters
- Local file-system adapters
- Generic local/file adapters
- Generic HTTP adapters
