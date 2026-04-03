# Action Plan: Browser Analysis Feature 134

Last Updated: 2026-02-17

## Goal

Deliver a constraint-aware plan for puzzle analysis UX that clarifies what can ship now, what requires policy changes, and how to stage work safely.

## Baseline Decision

This plan assumes current constraints remain active unless explicitly revised:

- Zero runtime backend
- Local-first persistence


If these constraints are changed, a separate “Policy Exception Track” applies (see Workstream 5).

## Workstreams

## Workstream 1: Documentation and Spec Hygiene

1. Normalize Feature 134 artifacts under `TODO/134-score-estimation-wasm/`.
2. Resolve inconsistencies in `spec.md`:
   - Remove placeholder entities and template success criteria.
   - Keep one measurable success criteria section.
3. Resolve inconsistencies in `tasks.md`:
   - Fix source references (`specs/134...` mismatch).
   - Replace stale/non-existent component paths with current frontend touchpoints.
   - Renumber duplicate task IDs.
4. Align asset naming assumptions across docs and scripts.

Exit Criteria:

- `spec.md`, `plan.md`, `tasks.md` are internally consistent and executable as planning artifacts.

## Workstream 2: Constraint-Compliant MVP (No Runtime AI)

1. Define MVP scope as deterministic guidance only:
   - Analysis mode UI shell
   - Precomputed/static hints overlays where available
   - No runtime inference or Monte Carlo
2. Map integration touchpoints in frontend:
   - `frontend/src/components/Solver/SolverView.tsx`
   - `frontend/src/hooks/usePuzzleState.ts`
   - `frontend/src/hooks/useGoban.ts`
   - `frontend/src/components/Transforms/TransformBar.tsx`
3. Define data contract for static analysis payloads (if added via pipeline).

Exit Criteria:

- Clear MVP scope with no policy conflicts.
- File-level integration map validated.

## Workstream 3: Precompute Data Feasibility (Pipeline)

1. Evaluate whether limited analysis metadata can be generated offline in pipeline:
   - Root/trunk ownership-like summaries
   - Variation-level pedagogical annotations
2. Identify schema impact and compatibility boundaries:
   - `backend/puzzle_manager/core/schema.py`
   - `config/schemas/sgf-properties.schema.json`
3. Define storage/index impact on published collections and views.

Exit Criteria:

- Go/No-Go for precompute metadata path with documented cost/benefit.

## Workstream 4: Validation and Quality Gates

1. Add acceptance checklist tied to feature stories:
   - UI responsiveness
   - No mutation of puzzle solved state
   - Deterministic outputs for same inputs
2. Define test coverage targets:
   - Frontend unit tests for state transitions
   - Integration checks for overlay rendering and fallback behavior
3. Define performance budgets appropriate to non-AI MVP path.

Exit Criteria:

- Test and verification strategy agreed before implementation.

## Workstream 5: Policy Exception Track (Only If Requested)

This track is blocked unless architecture constraints are explicitly revised.

1. Draft proposal to allow browser inference (scope, guardrails, fallback policy).
2. Prototype capability matrix (desktop/mobile, browser features).
3. Set runtime budget and graceful degradation rules.
4. Reassess deterministic guarantees and user-experience variance.

Exit Criteria:

- Approved exception document and revised architecture constraints.

## Sequence and Milestones

- M1: Artifact Cleanup Complete (Workstream 1)
- M2: Constraint-Compliant MVP Scope Locked (Workstream 2)
- M3: Precompute Feasibility Decision (Workstream 3)
- M4: Verification Plan Locked (Workstream 4)
- M5: Optional Exception Approved (Workstream 5, only if needed)

## Risks and Mitigations

- Risk: Scope drift toward runtime AI without policy approval.
  - Mitigation: explicit gate before any inference-related work.
- Risk: Stale file paths/tasks reduce execution quality.
  - Mitigation: complete Workstream 1 first.
- Risk: Overpromising GoProblems parity under static-only constraints.
  - Mitigation: define parity as UX guidance, not live depth.

## Definition of Done (Planning)

- Research findings documented in docs reference.
- Action plan documented under TODO with milestones and gates.
- Possible vs not possible vs limitations explicitly captured.
- Policy-exception branch isolated as optional path.

## References

- `docs/reference/katago-browser-analysis-research.md`
- `TODO/134-score-estimation-wasm/spec.md`
- `TODO/134-score-estimation-wasm/plan.md`
- `TODO/134-score-estimation-wasm/tasks.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `frontend/CLAUDE.md`
