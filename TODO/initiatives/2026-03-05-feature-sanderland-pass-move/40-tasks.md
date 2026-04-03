# Tasks: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Last Updated**: 2026-03-05

## Dependency-Ordered Checklist

### T1 — Add `_is_pass_coord` helper [P]

- **File**: `backend/puzzle_manager/adapters/sanderland/adapter.py`
- **Scope**: New static/private method `_is_pass_coord(coord: str) -> bool`
- **Logic**: Returns `True` if `coord` is `"zz"` or `""` (empty string)
- **Lines**: ~5

### T2 — Update sequential path in `_build_solution_tree`

- **File**: `backend/puzzle_manager/adapters/sanderland/adapter.py`
- **Depends**: T1
- **Scope**: In the "Standard sequential behavior" loop (~L596-L604), detect pass via `_is_pass_coord(coord)`:
  - If pass: emit `{color}[]` instead of `{color}[{coord}]`
  - Build comment: if existing SOL comment is non-empty, append ` — {Color} passes`; otherwise set `{Color} passes`
  - Emit `C[{comment}]`
- **Lines**: ~8 changed

### T3 — Update miai path in `_build_solution_tree`

- **File**: `backend/puzzle_manager/adapters/sanderland/adapter.py`
- **Depends**: T1
- **Scope**: In the miai variation loop (~L588-L594), same pass detection + comment logic as T2
- **Lines**: ~5 changed

### T4 — Write unit tests [P after T2+T3]

- **File**: `backend/puzzle_manager/tests/adapters/test_sanderland.py`
- **Depends**: T2, T3
- **Test cases**:
  1. `_is_pass_coord("zz")` → `True`
  2. `_is_pass_coord("")` → `True`
  3. `_is_pass_coord("cd")` → `False`
  4. `_build_solution_tree([["W", "zz", "", ""]])` → `;W[]C[White passes]`
  5. `_build_solution_tree([["B", "zz", "", ""]])` → `;B[]C[Black passes]`
  6. `_build_solution_tree([["B", "cd"], ["W", "zz"], ["B", "ef"]])` → `;B[cd];W[]C[White passes];B[ef]`
  7. Miai with pass: `_build_solution_tree([["B", "zz"], ["B", "cd"]])` → variation with pass
  8. Pass with existing comment: `_build_solution_tree([["W", "zz", "Correct", ""]])` → `C[Correct — White passes]`
- **Lines**: ~40 new

### T5 — Validation run

- **Depends**: T4
- **Command**: `pytest -m "not (cli or slow)"`
- **Criteria**: All existing + new tests pass; no regressions

## Parallel Markers

```
T1 ──┬── T2 ──┬── T4 ── T5
     └── T3 ──┘
```

T1 is independent. T2 and T3 can be done in parallel after T1. T4 after both. T5 last.

## Compatibility Strategy

No legacy removal tasks. No backward compatibility tasks. This is a net-new detection path.
