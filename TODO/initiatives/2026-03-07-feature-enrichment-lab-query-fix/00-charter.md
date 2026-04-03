# Charter: Enrichment Lab Query Fix + DRY Refactor

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07

---

## Problem Statement

The puzzle enrichment lab produces broken output for position-only puzzles:

- Zero correct solutions found
- Solution trees built on irrelevant board areas (star points D4, Q16, Q4)
- Garbled non-ASCII characters in SGF comments
- Diagnostic engine data (winrate %, score lead) embedded in user-facing C[] comments
- All enrichment log files are empty (0 bytes)

Root cause: `SyncEngineAdapter.query()` in `solve_position.py` omits `allowed_moves` from its `AnalysisRequest`, but the real enabler is an **architectural DRY violation** — three independent code paths build KataGo analysis requests with the same tsumego preparation logic (komi=0, frame application, puzzle region computation, allowed_moves), leading to inconsistency and exactly the class of bug observed.

## Goals

1. Fix all 6 bugs identified in the analysis phase
2. Eliminate the DRY/SRP violation by consolidating tsumego query preparation into a single shared function
3. Fix the logging namespace filter so enrichment logs actually write to files
4. Align enrichment log file naming with KataGo log naming pattern
5. Add a golden fixture regression test using the failing puzzle
6. Document changes

## Non-Goals

- `enrich_single.py` decomposition (separate initiative, already at closeout)
- Refactoring the tree builder algorithm itself
- Changing KataGo configuration or model files
- Frontend changes

## Constraints

- Must NOT break existing test suite (125+ tests in `test_enrich_single.py`, `test_solve_position.py`)
- Must follow project DRY/KISS/YAGNI/SOLID principles
- Must NOT add non-ASCII characters in enrichment-generated text
- Must preserve original SGF C[] content as-is; only sanitize enrichment-added text
- `tools/` must NOT import from `backend/`

## Acceptance Criteria

- [ ] AC-1: Running enrichment on the golden puzzle produces at least one "Correct" branch
- [ ] AC-2: No moves in any solution tree branch fall outside the puzzle bounding box + margin
- [ ] AC-3: No garbled/non-ASCII characters in enrichment-added SGF comments
- [ ] AC-4: No diagnostic data (winrate %, score lead) in SGF C[] properties — only teaching comments
- [ ] AC-5: Enrichment log files contain structured JSON log entries (not empty)
- [ ] AC-6: Enrichment log file naming matches pattern: `YYYYMMDD-HHMMSS-HASH.log`
- [ ] AC-7: Only ONE code path prepares tsumego queries (DRY compliance)
- [ ] AC-8: All existing tests pass
- [ ] AC-9: Golden fixture regression test exists and passes

> **See also**:
>
> - [10-clarifications.md](./10-clarifications.md) — User decisions
> - [25-options.md](./25-options.md) — DRY refactor option analysis
> - [30-plan.md](./30-plan.md) — Technical plan
