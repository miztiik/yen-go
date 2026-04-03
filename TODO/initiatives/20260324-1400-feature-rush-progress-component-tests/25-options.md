# Options

**Last Updated:** 2026-03-24

Single viable approach (user explicitly constrained direction + low complexity).

| ID | Title | Approach | Benefits | Drawbacks |
|----|-------|----------|----------|-----------|
| OPT-1 | Co-located `__tests__` dirs in `src/` | Place test files at `src/components/Rush/__tests__/` and `src/pages/__tests__/` | Matches user spec; co-located with components; vitest config already includes `src/**/*.test.tsx` | New `__tests__` directories (first in `src/components/` and `src/pages/`) |
| OPT-2 | Central `tests/unit/` dir | Place all 3 files in `tests/unit/` alongside existing ProgressPage and SmartPracticePage tests | Consistent with existing test location pattern; single directory | Doesn't match user's requested file paths; less co-location |

**Selected:** OPT-1 — matches user's explicit file path spec. The vitest config `include: ['src/**/*.{test,spec}.{ts,tsx}']` already supports this pattern.
