# Plan — Phase B Merge Refactor

**Initiative**: `2026-03-06-refactor-phase-b-merge`  
**Selected Option**: OPT-1 — Flat Merge into analyzers/  
**Last Updated**: 2026-03-06

---

## Summary

Move 4 modules from `tools/puzzle-enrichment-lab/phase_b/` into `tools/puzzle-enrichment-lab/analyzers/`, update all imports to use `analyzers.*` paths, delete the empty `phase_b/` directory, and update living documentation. Zero behavior change.

---

## Transformations

### T1: Move module files

| #   | Source                             | Destination                          | Transform                                 |
| --- | ---------------------------------- | ------------------------------------ | ----------------------------------------- |
| M1  | `phase_b/teaching_comments.py`     | `analyzers/teaching_comments.py`     | Move file + update internal imports       |
| M2  | `phase_b/vital_move.py`            | `analyzers/vital_move.py`            | Move file (no internal imports to update) |
| M3  | `phase_b/refutation_classifier.py` | `analyzers/refutation_classifier.py` | Move file (no internal imports to update) |
| M4  | `phase_b/comment_assembler.py`     | `analyzers/comment_assembler.py`     | Move file (no internal imports to update) |

### T2: Update internal imports in teaching_comments.py

After moving to `analyzers/`, the file's internal imports change:

| Line  | Before                                                                                                              | After                                                                                                                 |
| ----- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 30    | `from phase_b.vital_move import VitalMoveResult, detect_vital_move`                                                 | `from analyzers.vital_move import VitalMoveResult, detect_vital_move`                                                 |
| 31-33 | `from phase_b.refutation_classifier import (ClassifiedRefutation, classify_all_refutations,)`                       | `from analyzers.refutation_classifier import (ClassifiedRefutation, classify_all_refutations,)`                       |
| 35-39 | `from phase_b.comment_assembler import (assemble_correct_comment, assemble_vital_comment, assemble_wrong_comment,)` | `from analyzers.comment_assembler import (assemble_correct_comment, assemble_vital_comment, assemble_wrong_comment,)` |

### T3: Update enrich_single.py imports

| Line | Before                                                               | After                                                                  |
| ---- | -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 49   | `from phase_b.teaching_comments import generate_teaching_comments`   | `from analyzers.teaching_comments import generate_teaching_comments`   |
| 89   | `from ..phase_b.teaching_comments import generate_teaching_comments` | `from ..analyzers.teaching_comments import generate_teaching_comments` |

### T4: Update test imports

| Test File                               | Before                                                              | After                                                                 |
| --------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `test_teaching_comments.py`             | `from phase_b.teaching_comments import generate_teaching_comments`  | `from analyzers.teaching_comments import generate_teaching_comments`  |
| `test_vital_move.py`                    | `from phase_b.vital_move import detect_vital_move, VitalMoveResult` | `from analyzers.vital_move import detect_vital_move, VitalMoveResult` |
| `test_refutation_classifier.py`         | `from phase_b.refutation_classifier import (...)`                   | `from analyzers.refutation_classifier import (...)`                   |
| `test_comment_assembler.py`             | `from phase_b.comment_assembler import (...)`                       | `from analyzers.comment_assembler import (...)`                       |
| `test_teaching_comments_integration.py` | `from phase_b.teaching_comments import generate_teaching_comments`  | `from analyzers.teaching_comments import generate_teaching_comments`  |

### T5: Delete phase_b/ directory

Remove `phase_b/__init__.py`, `phase_b/__pycache__/`, and the `phase_b/` directory itself.

### T6: Update documentation

| Doc                                            | Section                          | Change                                                                   |
| ---------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------ |
| `CHANGELOG.md`                                 | `[Unreleased]`                   | Add refactor entry noting module relocation                              |
| `docs/architecture/tools/katago-enrichment.md` | D37 (line ~365)                  | Change `phase_b/teaching_comments.py` → `analyzers/teaching_comments.py` |
| `docs/architecture/tools/katago-enrichment.md` | Pipeline integration (line ~371) | Same path update                                                         |

---

## Invariants

| #     | Invariant                                                                               | Verification                                                                        |
| ----- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| INV-1 | Zero behavior change — all module APIs, function signatures, class interfaces identical | Diff inspection: only `from phase_b.` → `from analyzers.` changes in moved files    |
| INV-2 | All 169+ tests pass                                                                     | `pytest` in `tools/puzzle-enrichment-lab/`                                          |
| INV-3 | No `phase_b` references remain in code files                                            | `grep -r "phase_b" tools/puzzle-enrichment-lab/ --include="*.py"` returns 0 results |
| INV-4 | Module content unchanged                                                                | `diff` between moved files and originals (excluding import lines)                   |

---

## Risks and Mitigations

| #   | Risk                                    | Probability | Impact | Mitigation                                                                                                                 |
| --- | --------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------------- |
| R1  | Concurrent work touches same files      | Low         | Medium | Feature branch isolates changes. Merge conflicts are in import lines only — trivial to resolve.                            |
| R2  | Missed import in untested code path     | Very Low    | Medium | `grep -r "phase_b"` catches all references. `enrich_single.py` has a try/except import block — both paths must be updated. |
| R3  | `__pycache__` stale bytecode after move | Low         | Low    | Delete `phase_b/__pycache__/` as part of cleanup. Python will regenerate cache for new paths.                              |

---

## Rollback Strategy

Single `git revert` of the merge commit restores all files to their pre-refactor state. No configuration, schema, or data changes to undo.

---

## SOLID/DRY/KISS/YAGNI Mapping

| Principle | Assessment                                                                                                     |
| --------- | -------------------------------------------------------------------------------------------------------------- |
| **SRP**   | Each module retains its single responsibility. No logic changes.                                               |
| **OCP**   | `analyzers/` is open for extension (new modules can be added). Moving modules in doesn't modify existing ones. |
| **KISS**  | Flat sibling pattern is the simplest organization. Eliminates the "what is phase_b?" question.                 |
| **DRY**   | No duplication introduced or removed.                                                                          |
| **YAGNI** | No new abstractions, sub-packages, or re-export layers. Only what's needed.                                    |
