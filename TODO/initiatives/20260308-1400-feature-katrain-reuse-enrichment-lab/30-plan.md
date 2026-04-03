# Technical Plan (Selected Option: OPT-1)

**Last Updated:** 2026-03-08

## 1. Solution Overview

Implement a targeted KA Train algorithm reuse refactor inside `tools/puzzle-enrichment-lab` by porting pure, non-UI tsumego frame and utility logic where 1:1 match exists, while preserving enrichment-lab-specific behavior where KA Train is partial.

Selected option scope is intentionally narrow:
- In scope: `analyzers/tsumego_frame.py` parity improvements, lightweight utility imports (`var_to_grid` if needed), provenance/docs/tests.
- Out of scope: KA Train Kivy-coupled engine/game/ai module vendoring; whole-game rules engine migration; ELO-table replacement of puzzle difficulty model.

## 2. Architecture and Design Decisions

| decision_id | decision | rationale | impact |
|---|---|---|---|
| AD-1 | Keep `LocalEngine` and current async query architecture | KA Train engine module is Kivy-coupled and whole-game oriented | Avoids dependency/complexity regression |
| AD-2 | Port only pure frame algorithms from KA Train | Direct 1:1 reuse exists and currently known local gaps are in this area | Highest ROI with low blast radius |
| AD-3 | Use adapter mapping for coordinate conventions | KA Train frame internals are `(row,col)`; lab is `(x,y)` | Prevents silent frame misplacement bugs |
| AD-4 | Enforce parity-first test gate before deleting legacy frame logic | Governance RC-1 and unresolved flip-intent uncertainty | Makes replacement decision data-driven |
| AD-5 | Preserve puzzle-specific deltas in wrapper layer | User requires delta retention when KA Train is partial | Maintains existing behavior that KA Train does not provide |
| AD-6 | Apply MIT attribution metadata in code + docs | Required by license and governance RC-2 | Legal and provenance compliance |

## 3. Data/Model Contract Impact

| contract_id | current | planned | compatibility_note |
|---|---|---|---|
| DC-1 | `apply_tsumego_frame(position, margin, offense_color) -> Position` | Same public signature | No external API break required despite no backward-compat obligation |
| DC-2 | Internal frame candidate generation is local checkerboard logic | Internal algorithm replaced by KA Train-aligned pure helpers + adapter | Behavior may change in edge positions; covered by parity/regression tests |
| DC-3 | Optional policy-grid conversion logic is ad hoc/not centralized | Optional `var_to_grid` utility helper with tests | Internal-only enhancement |

## 4. Risk Register and Mitigations

| risk_id | risk | severity | mitigation | owner_task |
|---|---|---|---|---|
| R1 | Wrong axis mapping while porting frame logic | High | Add coordinate contract tests and fixture parity checks | T4 |
| R2 | Behavior regression on small boards/ko puzzles | Medium | Add targeted fixture coverage for 9x9/13x13/19x19 and ko-tagged cases | T5 |
| R3 | Missing MIT attribution for copied logic | Medium | Mandatory attribution and docs tasks with review checklist | T8 |
| R4 | Scope creep into engine/rules migration | Medium | Explicit non-goals and task-level guardrails | T2 |
| R5 | Delta behavior loss during replacement | High | Add delta-preservation assertions before legacy code deletion | T6 |

## 5. Rollout and Rollback

| rollout_id | step | success_criteria | rollback |
|---|---|---|---|
| RO-1 | Land parity test scaffolding | Tests reproduce current+expected frame behavior | Revert test commits if fixtures invalid |
| RO-2 | Introduce KA Train-aligned frame helpers behind adapter | All frame parity/regression tests pass | Toggle back to legacy frame path via single-module revert |
| RO-3 | Remove superseded legacy frame internals | No failing tests, no behavior gaps per acceptance checks | Restore previous implementation from git history |
| RO-4 | Ship docs/provenance updates | Docs mention source/adaptation limits and constraints | Revert docs changes independently if wording issue only |

## 6. Constraints and Guardrails

1. No imports from `backend/puzzle_manager/`.
2. No vendoring of Kivy-coupled KA Train modules (`core/engine.py`, `core/game.py`, or UI-tied classes).
3. Any KA Train-derived code must carry source attribution comments and be listed in docs.
4. Replacement allowed only after parity gate evidence is green.
5. Preserve enrichment-lab-only behavior via adapter/delta wrapper before old code removal.

## 7. TDD-First Validation Strategy

| test_id | phase | test_type | objective |
|---|---|---|---|
| V1 | Pre-port | unit | Capture current frame behavior on representative fixture set |
| V2 | Port | unit | Validate coordinate mapping and parity with expected KA Train behavior |
| V3 | Port | unit | Verify ko-threat and flip normalization behavior |
| V4 | Post-port | integration | Ensure enrich pipeline stage using frame still returns expected outputs |
| V5 | Post-port | regression | Ensure no unintended changes in solve/difficulty stages |

## 8. Documentation Plan

### files_to_update

| doc_id | path | why_updated |
|---|---|---|
| DP-1 | `tools/puzzle-enrichment-lab/README.md` | Document KA Train-derived frame logic, scope limits, and attribution note |
| DP-2 | `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` | Add attribution/provenance comments and adapter behavior notes |
| DP-3 | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/70-governance-decisions.md` | Record plan governance decision and constraints traceability |

### files_to_create

| doc_id | path | why_created |
|---|---|---|
| DP-4 | `docs/how-to/backend/reuse-katrain-in-enrichment-lab.md` | Canonical how-to for future KA Train reuse decisions and licensing/provenance checklist |

### cross-references

| ref_id | target | reason |
|---|---|---|
| XR-1 | `docs/architecture/tools/katago-enrichment.md` | Explain why Kivy-coupled modules remain out-of-scope and how enrichment tooling is structured |
| XR-2 | `docs/concepts/levels.md` and `docs/concepts/sgf-properties.md` | Clarify why ELO tables are not used for puzzle difficulty mapping and preserve SGF semantics |
| XR-3 | `docs/reference/enrichment-config.md` and `docs/reference/cli-quick-ref.md` | Keep enrichment behavior and CLI/reference docs consistent after frame parity changes |
