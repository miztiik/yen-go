# Charter: Rush/Progress/SmartPractice Component Tests

**Initiative ID:** 20260324-1400-feature-rush-progress-component-tests
**Level:** 2 (Medium Single — new test files, no production code changes)
**Last Updated:** 2026-03-24

## Goals

Add component-level rendering tests for three feature areas shipped in March 2026 initiatives:
1. Rush mode Score + Results components
2. PuzzleRushPage page
3. ProgressPage (gap analysis)
4. SmartPracticePage (gap analysis)

## Non-Goals

- No production code changes
- No E2E/playwright tests
- No service-layer tests (already covered)
- No test infrastructure changes

## Constraints

- Preact + TypeScript + Vite + Vitest
- `@testing-library/preact` (confirmed in devDependencies)
- `jsdom` environment (confirmed in vitest.config.ts)
- Must follow existing patterns: `vi.mock()` at top, `vi.mocked()` typing, `render`/`screen`/`waitFor`
- vitest `include` pattern accepts `src/**/*.{test,spec}.{ts,tsx}` — co-located `__tests__` dirs work

## Existing Coverage (CRITICAL FINDING)

| File | Location | Tests | Status |
|------|----------|-------|--------|
| ProgressPage | `tests/unit/ProgressPage.test.tsx` | 8 tests | **Already exists** |
| SmartPracticePage | `tests/unit/SmartPracticePage.test.tsx` | 6 tests | **Already exists** |
| RushResults (old) | `tests/integration/rushMode.test.tsx` | 8 tests | Tests OLD `RushResults` from `RushMode.tsx`, NOT new `Results.tsx` |
| RushScoreDisplay (old) | `tests/integration/rushMode.test.tsx` | 5 tests | Tests OLD `RushScoreDisplay`, NOT new `Score.tsx` |
| Score.tsx (new) | — | 0 | **Missing** |
| Results.tsx (new) | — | 0 | **Missing** |
| PuzzleRushPage.tsx | — | 0 | **Missing** |

## Revised Scope

Given existing coverage, the **net-new work** is 3 files (not 5):

| ID | File | Priority |
|----|------|----------|
| F1 | `frontend/src/components/Rush/__tests__/Score.test.tsx` | Must |
| F2 | `frontend/src/components/Rush/__tests__/Results.test.tsx` | Must |
| F3 | `frontend/src/pages/__tests__/PuzzleRushPage.test.tsx` | Must |
| F4 | `frontend/src/pages/__tests__/ProgressPage.test.tsx` | Skip — already at `tests/unit/` |
| F5 | `frontend/src/pages/__tests__/SmartPracticePage.test.tsx` | Skip — already at `tests/unit/` |

## Acceptance Criteria

- AC-1: All 3 new test files pass with `npx vitest run --no-coverage`
- AC-2: ≥15 test cases total across 3 files
- AC-3: Zero production code changes
- AC-4: Existing test suite remains green (no regressions)
