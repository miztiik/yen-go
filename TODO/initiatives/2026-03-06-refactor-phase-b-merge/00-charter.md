# Charter — Phase B Merge Refactor

**Initiative**: `2026-03-06-refactor-phase-b-merge`  
**Type**: Refactor  
**Last Updated**: 2026-03-06

---

## Problem Statement

The `tools/puzzle-enrichment-lab/phase_b/` directory contains 4 teaching-comments V2 modules that functionally belong in the `analyzers/` package. The name "phase_b" reflects a development timeline artifact (Phase A = base enrichment, Phase B = teaching comments) rather than an architectural boundary. This creates:

1. **Conceptual confusion** — New contributors must understand that "phase_b" means "teaching comments V2" and has no relation to any "phase_a" directory.
2. **Import path oddity** — `analyzers/enrich_single.py` imports from a sibling `phase_b/` package instead of from its own `analyzers/` package.
3. **Inconsistent structure** — 15 analyzer modules live in `analyzers/`, but 4 closely related ones live in `phase_b/`.
4. **Documentation burden** — Architecture docs must explain the phase naming convention.

## Scope

### In-Scope Files

| #   | File                                                                      | Action                    |
| --- | ------------------------------------------------------------------------- | ------------------------- |
| F1  | `tools/puzzle-enrichment-lab/phase_b/teaching_comments.py`                | Move to `analyzers/`      |
| F2  | `tools/puzzle-enrichment-lab/phase_b/vital_move.py`                       | Move to `analyzers/`      |
| F3  | `tools/puzzle-enrichment-lab/phase_b/refutation_classifier.py`            | Move to `analyzers/`      |
| F4  | `tools/puzzle-enrichment-lab/phase_b/comment_assembler.py`                | Move to `analyzers/`      |
| F5  | `tools/puzzle-enrichment-lab/phase_b/__init__.py`                         | Delete                    |
| F6  | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`                  | Update imports            |
| F7  | `tools/puzzle-enrichment-lab/tests/test_teaching_comments.py`             | Update imports            |
| F8  | `tools/puzzle-enrichment-lab/tests/test_vital_move.py`                    | Update imports            |
| F9  | `tools/puzzle-enrichment-lab/tests/test_refutation_classifier.py`         | Update imports            |
| F10 | `tools/puzzle-enrichment-lab/tests/test_comment_assembler.py`             | Update imports            |
| F11 | `tools/puzzle-enrichment-lab/tests/test_teaching_comments_integration.py` | Update imports            |
| F12 | `CHANGELOG.md`                                                            | Add refactor entry        |
| F13 | `docs/architecture/tools/katago-enrichment.md`                            | Update D37/D38 references |

### Out-of-Scope (Explicit Exclusions)

| #   | Exclusion                                                 | Rationale                                                                   |
| --- | --------------------------------------------------------- | --------------------------------------------------------------------------- |
| X1  | Historical TODO/initiative docs                           | Records of what happened — do not rewrite history                           |
| X2  | `config/teaching-comments.json`                           | No changes — config is directory-agnostic                                   |
| X3  | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | No `phase_b` imports                                                        |
| X4  | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`   | References `teaching_comments` field on result objects, not the module path |
| X5  | Any functionality changes                                 | Pure structural refactor — zero behavior change                             |

## Goals

1. Eliminate the `phase_b/` directory by merging its contents into `analyzers/`
2. All imports updated consistently
3. All tests pass with zero behavior change
4. Documentation updated to reflect new paths

## Non-Goals

- Refactoring the internal logic of any module
- Changing the module APIs or function signatures
- Renaming functions or classes
- Changing test behavior or coverage

## Constraints

| #   | Constraint                                                   | Source     |
| --- | ------------------------------------------------------------ | ---------- |
| C1  | Zero behavior change — pure structural refactor              | YAGNI      |
| C2  | All 169+ enrichment lab tests must pass                      | Test-first |
| C3  | No new dependencies                                          | KISS       |
| C4  | Git safety rules — no `git add .`, no destructive operations | CLAUDE.md  |

## Acceptance Criteria

1. `phase_b/` directory no longer exists
2. All 4 modules exist in `analyzers/` with identical content (except import paths)
3. All imports across the codebase reference `analyzers.*` instead of `phase_b.*`
4. All tests pass (`pytest` in `tools/puzzle-enrichment-lab/`)
5. CHANGELOG and architecture docs updated
6. No `grep -r "phase_b"` matches in code files (docs/TODOs excluded)
