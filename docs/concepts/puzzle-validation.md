# Puzzle Validation

> **See also**:
>
> - [Config: puzzle-validation.json](../../config/README.md#puzzle-validationjson-spec-108) — Configuration reference
> - [How-To: Create Adapter](../how-to/backend/create-adapter.md#5-use-puzzlevalidator-for-consistent-validation) — Usage in adapters

**Last Updated**: 2026-02-19

Centralized puzzle validation rules ensure consistent quality filtering across all adapters.

---

## Overview

The `PuzzleValidator` class provides **build-time validation** for all puzzle imports. This means:

1. **Validation happens at pipeline time** — during ingest/analyze stages, NOT at runtime
2. **Invalid puzzles are rejected** — filtered out before entering the published collection
3. **Consistent rules** — all adapters use the same validation logic
4. **Configurable** — defaults can be overridden per-adapter

---

## Validation Rules

| Rule                  | Default | Description                                                                   |
| --------------------- | ------- | ----------------------------------------------------------------------------- |
| `min_board_dimension` | 5       | Minimum board width OR height                                                 |
| `max_board_dimension` | 19      | Maximum board width OR height                                                 |
| `min_solution_depth`  | 1       | Minimum solution tree depth (1 = solution required, 0 = no solution required) |
| `min_stones`          | 2       | Minimum total stones (black + white)                                          |
| `max_solution_depth`  | 30      | Maximum moves in solution tree                                                |

### Non-Square Boards

The validator **supports non-square boards** (e.g., 7×9). Each dimension is validated independently:

```
Board 7×9:
  - Width 7 >= 5 (min_board_dimension) ✓
  - Height 9 <= 19 (max_board_dimension) ✓
  → VALID
```

This allows partial/corner problems commonly used in tsumego books.

---

## Configuration

### Default Config

Default validation rules are stored in `config/puzzle-validation.json` (single source of truth, fail-fast loading — missing config raises `FileNotFoundError`):

```json
{
  "version": "2.0",
  "min_board_dimension": 5,
  "max_board_dimension": 19,
  "min_solution_depth": 1,
  "min_stones": 2,
  "max_solution_depth": 30
}
```

> **Note**: v2.0 uses `min_solution_depth` (integer) instead of v1.0's `require_solution` (boolean).
> The validators support both formats for backward compatibility.

### Adapter Overrides

Adapters can override specific rules in their config file:

```json
// config/adapters/my-source.json
{
  "id": "my-source",
  "validation": {
    "max_solution_depth": 20,
    "min_stones": 3
  }
}
```

The adapter's `configure()` method applies these overrides:

```python
def configure(self, config: dict) -> None:
    validation_overrides = config.get("validation", {})
    self._validator.configure(validation_overrides)
```

---

## Rejection Reasons

When validation fails, a clear rejection reason is provided:

| Rejection                             | Code | Cause                                                 |
| ------------------------------------- | ---- | ----------------------------------------------------- |
| `Board width X is below minimum Y`    | 100  | Width below `min_board_dimension`                     |
| `Board height X is above maximum Y`   | 200  | Height above `max_board_dimension`                    |
| `Insufficient stones`                 | 300  | Total stones below `min_stones`                       |
| `Puzzle has no solution`              | 400  | Solution depth below `min_solution_depth` (when >= 1) |
| `Solution depth X is below minimum Y` | 450  | Solution exists but is too shallow                    |
| `Solution depth X exceeds maximum Y`  | 500  | Solution depth exceeds `max_solution_depth`           |
| `Invalid puzzle structure`            | 600  | Structural error (corrupted data)                     |

### Rejection Codes

Rejection reasons use `IntEnum` with 100-increment codes for **ordering flexibility**:

```python
class RejectionReason(IntEnum):
    BOARD_TOO_SMALL = 100      # Board dimension rules
    BOARD_TOO_LARGE = 200
    INSUFFICIENT_STONES = 300  # Stone rules
    NO_SOLUTION = 400          # Solution rules
    SOLUTION_TOO_SHALLOW = 450 # New in v2.0
    SOLUTION_TOO_DEEP = 500
    INVALID_STRUCTURE = 600    # Structure rules
```

The 100-increment pattern allows inserting new rules between existing ones without breaking order (e.g., 150 between BOARD_TOO_SMALL and BOARD_TOO_LARGE).

---

## Validation Logging

### Ingest Stage Output

Validation rejections are logged at **INFO** level in the ingest log:

**File**: `.pm-runtime/logs/YYYY-MM-DD-ingest.log`

**Format**:

```json
{
  "ts": "2026-02-02 12:00:00",
  "msg": "Skipped puzzle",
  "action": "skip",
  "puzzle_id": "yengo-source-12345",
  "source_id": "yengo-source",
  "reason": "Board width 4 is below minimum 5"
}
```

### Summary with Breakdown

The ingest completion log includes rejection reason breakdown:

```json
{
  "ts": "2026-02-02 12:00:30",
  "msg": "Ingest complete",
  "source_id": "yengo-source",
  "processed": 85,
  "failed": 0,
  "skipped": 15,
  "duration": 30.5,
  "rejection_reasons": {
    "Board width 4 is below minimum 5": 10,
    "Puzzle has no solution": 5
  }
}
```

---

## Validation Statistics

Use `ValidationStatsCollector` to track validation outcomes:

```python
from backend.puzzle_manager.core import (
    PuzzleValidator,
    ValidationStatsCollector,
)

validator = PuzzleValidator()
stats = ValidationStatsCollector()

for puzzle in puzzles:
    result = validator.validate(puzzle)
    stats.record(result)

# Log summary
print(stats.log_summary())
# Output:
# Total: 100
# Valid: 85
# Invalid: 15
# Acceptance Rate: 85.0%
# Rejections by reason:
#   Board too small: 10
#   No solution provided: 5
```

---

## Design Principles

### 1. Build-Time, Not Runtime

Validation runs during pipeline execution (CI/CD), not in the browser. This:

- Prevents invalid puzzles from entering the collection
- Keeps the frontend static and fast
- Avoids validation overhead at runtime

### 2. Single Responsibility

`PuzzleValidator` handles **validation only**. Statistics collection is handled by the separate `ValidationStatsCollector` class (SRP).

### 3. Explicit Over Implicit

Rejection reasons are human-readable strings, not opaque error codes. This makes debugging and logging straightforward.

### 4. Adapter Agnostic

`PuzzleData` is a neutral data structure that doesn't depend on any adapter-specific formats. Adapters convert their data to `PuzzleData` before validation.

---

## Implementation

### Core Classes

| Class                      | Purpose                       |
| -------------------------- | ----------------------------- |
| `PuzzleValidator`          | Main validator class          |
| `ValidationConfig`         | Configuration dataclass       |
| `PuzzleData`               | Input data structure          |
| `ValidationResult`         | Output with is_valid + reason |
| `ValidationStatsCollector` | Statistics aggregation        |

### Module Location

```
backend/puzzle_manager/core/
├── puzzle_validator.py      # PuzzleValidator, PuzzleData, ValidationConfig
└── validation_stats.py      # ValidationStatsCollector
```

### Exports

All classes are exported from `backend.puzzle_manager.core`:

```python
from backend.puzzle_manager.core import (
    PuzzleValidator,
    PuzzleData,
    ValidationConfig,
    ValidationResult,
    RejectionReason,
    validate_puzzle,
    ValidationStatsCollector,
)
```
