# Tasks — Phase B Merge Refactor

**Initiative**: `2026-03-06-refactor-phase-b-merge`  
**Selected Option**: OPT-1 — Flat Merge into analyzers/  
**Last Updated**: 2026-03-06

---

## Task Dependency Graph

```
T1 (move 4 module files) [P — all 4 moves are independent]
        │
T2 (update internal imports in teaching_comments.py)
        │
T3 (update enrich_single.py imports) [P with T4]
T4 (update test file imports) [P with T3]
        │
T5 (delete phase_b/ directory)
        │
T6 (run full test suite — validation)
        │
T7 (update documentation) [P — CHANGELOG and architecture doc independent]
        │
T8 (final grep verification)
```

`[P]` = can run in parallel with adjacent tasks at same dependency level.

---

## Tasks

### T1 — Move Module Files [P]

**Description**: Move all 4 Python modules from `phase_b/` to `analyzers/`. Do NOT modify file content at this step — content updates come in T2.

**Files**:

- `tools/puzzle-enrichment-lab/phase_b/teaching_comments.py` → `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py`
- `tools/puzzle-enrichment-lab/phase_b/vital_move.py` → `tools/puzzle-enrichment-lab/analyzers/vital_move.py`
- `tools/puzzle-enrichment-lab/phase_b/refutation_classifier.py` → `tools/puzzle-enrichment-lab/analyzers/refutation_classifier.py`
- `tools/puzzle-enrichment-lab/phase_b/comment_assembler.py` → `tools/puzzle-enrichment-lab/analyzers/comment_assembler.py`

**Deps**: None  
**Definition of Done**: All 4 files exist in `analyzers/` with identical content. Originals still in `phase_b/` until T5.

---

### T2 — Update Internal Imports in teaching_comments.py

**Description**: Update the 3 `from phase_b.*` import statements in the now-moved `analyzers/teaching_comments.py`.

**Files**:

- `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` (modify lines 30, 31-33, 35-39)

**Changes**:

```python
# Before:
from phase_b.vital_move import VitalMoveResult, detect_vital_move
from phase_b.refutation_classifier import (
    ClassifiedRefutation,
    classify_all_refutations,
)
from phase_b.comment_assembler import (
    assemble_correct_comment,
    assemble_vital_comment,
    assemble_wrong_comment,
)

# After:
from analyzers.vital_move import VitalMoveResult, detect_vital_move
from analyzers.refutation_classifier import (
    ClassifiedRefutation,
    classify_all_refutations,
)
from analyzers.comment_assembler import (
    assemble_correct_comment,
    assemble_vital_comment,
    assemble_wrong_comment,
)
```

**Deps**: T1  
**Definition of Done**: `analyzers/teaching_comments.py` has zero `phase_b` references.

---

### T3 — Update enrich_single.py Imports [P with T4]

**Description**: Update both import paths in the orchestrator.

**Files**:

- `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` (modify lines 49 and 89)

**Changes**:

```python
# Line 49 — try block:
# Before: from phase_b.teaching_comments import generate_teaching_comments
# After:  from analyzers.teaching_comments import generate_teaching_comments

# Line 89 — except/relative block:
# Before: from ..phase_b.teaching_comments import generate_teaching_comments
# After:  from ..analyzers.teaching_comments import generate_teaching_comments
```

**Deps**: T1, T2  
**Definition of Done**: `enrich_single.py` has zero `phase_b` references.

---

### T4 — Update Test File Imports [P with T3]

**Description**: Update all `from phase_b.*` imports in the 5 test files.

**Files**:

- `tools/puzzle-enrichment-lab/tests/test_teaching_comments.py` (line 7)
- `tools/puzzle-enrichment-lab/tests/test_vital_move.py` (line 7)
- `tools/puzzle-enrichment-lab/tests/test_refutation_classifier.py` (lines 7-11)
- `tools/puzzle-enrichment-lab/tests/test_comment_assembler.py` (lines 18-24)
- `tools/puzzle-enrichment-lab/tests/test_teaching_comments_integration.py` (line 7)

**Changes**: All `from phase_b.X import Y` → `from analyzers.X import Y`

**Deps**: T1, T2  
**Definition of Done**: All 5 test files have zero `phase_b` references.

---

### T5 — Delete phase_b/ Directory

**Description**: Remove the now-empty `phase_b/` directory and all its contents.

**Files to delete**:

- `tools/puzzle-enrichment-lab/phase_b/__init__.py`
- `tools/puzzle-enrichment-lab/phase_b/__pycache__/` (if present)
- `tools/puzzle-enrichment-lab/phase_b/` directory

**Deps**: T1, T2, T3, T4 (all imports must be updated before removal)  
**Definition of Done**: `phase_b/` directory no longer exists.

---

### T6 — Run Full Test Suite (Validation)

**Description**: Run `pytest` in `tools/puzzle-enrichment-lab/` to verify all 169+ tests pass with zero behavior change.

**Command**: `cd tools/puzzle-enrichment-lab && pytest`

**Deps**: T5  
**Definition of Done**: All tests pass. No failures, no errors.

---

### T7 — Update Documentation [P]

**Description**: Update living documentation to reflect the new paths.

**Files**:

- `CHANGELOG.md` — Add entry under `[Unreleased]`:
  ```markdown
  ### Changed

  - **Enrichment Lab: Phase B merge** — Moved `phase_b/` modules (teaching_comments, vital_move, refutation_classifier, comment_assembler) into `analyzers/` for consistent package organization
  ```
- `docs/architecture/tools/katago-enrichment.md` — Update D37 (line ~365) and pipeline integration (line ~371):
  - `phase_b/teaching_comments.py` → `analyzers/teaching_comments.py`
  - `phase_b/` references → `analyzers/`

**Deps**: T6 (tests pass first)  
**Definition of Done**: No `phase_b/` references in CHANGELOG code paths or architecture docs.

---

### T8 — Final Grep Verification

**Description**: Run `grep -r "phase_b" tools/puzzle-enrichment-lab/ --include="*.py"` and `grep -r "phase_b" docs/ --include="*.md"` to verify zero stale references in code and living docs.

**Deps**: T7  
**Definition of Done**: Zero matches in code files. Historical TODO docs may still reference `phase_b` (expected — they are records).

---

## Summary

| Metric                   | Value                                                    |
| ------------------------ | -------------------------------------------------------- |
| Total tasks              | 8                                                        |
| Parallel-safe tasks      | T3/T4 (import updates), T7 sub-tasks (docs)              |
| Files moved              | 4                                                        |
| Files modified (imports) | 6 (teaching_comments.py, enrich_single.py, 5 test files) |
| Files deleted            | 1-2 (\_\_init\_\_.py, \_\_pycache\_\_/) + directory      |
| Files updated (docs)     | 2 (CHANGELOG.md, katago-enrichment.md)                   |
| Total files touched      | ~13                                                      |
| Backward compatibility   | Not required (no external consumers)                     |
| Legacy removal           | `phase_b/` fully deleted (dead code policy)              |
