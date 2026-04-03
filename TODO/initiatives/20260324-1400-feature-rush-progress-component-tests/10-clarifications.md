# Clarifications

**Last Updated:** 2026-03-24

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? | A: Yes / B: No | B: No — test-only addition | N/A (test-only, no compat concern) | ✅ resolved |
| Q2 | Should old code be removed? | A: Yes / B: No | B: No — no old code involved | N/A | ✅ resolved |
| Q3 | ProgressPage already has 8 tests at `tests/unit/ProgressPage.test.tsx`. Create duplicate at `src/pages/__tests__/`? | A: Create duplicate / B: Skip / C: Move existing | B: Skip — avoid duplication | Inferred: Skip (DRY) | ✅ resolved |
| Q4 | SmartPracticePage already has 6 tests at `tests/unit/SmartPracticePage.test.tsx`. Create duplicate? | A: Create duplicate / B: Skip / C: Move existing | B: Skip — avoid duplication | Inferred: Skip (DRY) | ✅ resolved |
| Q5 | `tests/integration/rushMode.test.tsx` tests OLD `RushResults`/`RushScoreDisplay` from `RushMode.tsx`. New `Score.tsx` and `Results.tsx` are different components. Confirm: test the new components? | A: Yes | A: Yes — new components have different interfaces | Confirmed by scope spec | ✅ resolved |
| Q6 | PuzzleRushPage has complex state (countdown→playing→finished). Test all 3 states or just initial render? | A: All states / B: Just initial + finished | A: All states — user wants rendering assertions per state | Inferred from "rendering assertions" scope | ✅ resolved |
