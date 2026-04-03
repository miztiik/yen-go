# Clarifications — Playing Modes DRY Compliance

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29

---

## Resolved Clarifications

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Backward compatibility for Rush/Random test IDs, route paths, localStorage keys, score history? | A: No backward compat / B: Preserve routes+localStorage / C: Full compat | A: Clean break — internal only | A (auto-resolved) | ✅ resolved |
| Q2 | Delete dead code (`RushPage.tsx`, `RushMode.tsx`, `PuzzleSolvePage.tsx`, `ReviewPage.tsx`, `TrainingPage.tsx`) in this initiative? | A: Delete all / B: Separate PR / C: Keep | A: Delete all — policy says "delete, don't deprecate" | A (auto-resolved) | ✅ resolved |
| Q3 | Board solver approach: SolverView `minimal` variant vs promote InlineSolver? | A: SolverView minimal / B: Promote InlineSolver / C: New shared component | A: Single rendering pipeline, all improvements flow through | A (auto-resolved) | ✅ resolved |
| Q4 | Random mode puzzle loading: build `StreamingLoader` for PuzzleSetPlayer or Random-specific adapter? | A: StreamingLoader (future-proof) / B: Random adapter / C: Keep separate | A: Needed for future modes (retry queue, spaced repetition) | A (auto-resolved) | ✅ resolved |
| Q5 | Playwright evidence: canvas click play, visual screenshots, or both? | A: Canvas click / B: Screenshots / C: Both | C: Canvas play proves correctness, screenshots prove sizing | C (user-requested) | ✅ resolved |
| Q6 | Scope: only Rush+Random or all 8 modes? | A: Rush+Random only / B: All 8 / C: Rush+Random+SmartPractice | A: Focus on violations — 6 compliant modes work correctly | A (auto-resolved) | ✅ resolved |

## Key Decision: Backward Compatibility

**Is backward compatibility required?** No.
**Should old code be removed?** Yes — delete all dead files in this initiative.

## Rationale

- Route paths (`/modes/rush`, `/modes/random`) are internal — users don't bookmark them
- `data-testid` attributes are test infrastructure, updated alongside code
- localStorage Rush score keys will be preserved (progress data) but component internals are not public API
- Dead code violates project policy ("Delete, don't deprecate. Git history preserves everything.")
