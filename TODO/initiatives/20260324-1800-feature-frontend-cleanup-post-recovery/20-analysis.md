# Analysis — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | **88** |
| `risk_level` | **low** |
| `research_invoked` | Yes (2 passes: code audit + docs audit) |

---

## Consistency & Coverage Analysis

### Charter ↔ Plan Mapping

| Charter Goal | Plan Batch | Tasks | Status |
|--------------|-----------|-------|--------|
| G1: Delete dead code (27 files + 2 dirs) | B1–B4 | T1–T29 | ✅ covered |
| G2: Delete stale docs (3 files) | B7 | T41–T43 | ✅ covered |
| G3: Merge quality config | B6 | T34–T40 | ✅ covered |
| G4: Fix README.md | B9 | T50–T53 | ✅ covered |
| G5: Update CLAUDE.md | B10 | T54–T58 | ✅ covered |
| G6: Regenerate AGENTS.md | B11 | T59–T60 | ✅ covered |
| G7: Clean service worker | B5 | T30–T33 | ✅ covered |

### AC ↔ Task Traceability

| AC-ID | Criterion | Verified By Task(s) |
|-------|-----------|---------------------|
| AC-1 | 27 dead files + 2 dirs deleted | T2–T7, T9–T12, T15–T19, T22–T26 |
| AC-2 | `npm test` passes | T8, T14, T21, T29, T33, T40, T61 |
| AC-3 | `npm run build` succeeds | T8, T14, T21, T29, T33, T40, T62 |
| AC-4 | 3 stale docs deleted | T41–T43 |
| AC-5 | 6 docs factual errors fixed | T44–T49 |
| AC-6 | README.md rewritten | T50–T53 |
| AC-7 | CLAUDE.md updated | T54–T58 |
| AC-8 | AGENTS.md regenerated | T59–T60 |
| AC-9 | qualityConfig deleted, QualityFilter uses lib/quality | T35–T39 |
| AC-10 | sw.ts stale patterns removed | T30–T32 |
| AC-11 | No remaining imports to deleted files | T63 |
| AC-12 | types/index.ts comment cleaned | T27 |

### Unmapped Tasks

None. All 64 tasks trace to charter goals or acceptance criteria.

---

## Findings

| finding_id | severity | category | description | resolution |
|------------|----------|----------|-------------|------------|
| F1 | Low | Scope | File count: charter says "27", research says "26 + DC-26 comment fix". The 27th file is `_rewrite_pagination.py` (counted as a file deletion). Consistent. | ✅ reconciled |
| F2 | Low | Coverage | Test files for dead modules need identification (T1, T13, T20, T28). If no test files exist, tasks are no-ops. | ✅ tasks include grep step |
| F3 | Low | Risk | `QualityFilter.tsx` async→sync change — verify `config/puzzle-quality.json` has all required fields at build time | ✅ T34 reads JSON first |
| F4 | Info | Exclusion | Timed-loader chain (`useTimedPuzzles`, `timed-loader`, `daily-loader`, `tag-loader`) explicitly excluded per Q4. Detailed brief in `10-clarifications.md §Q4-BRIEF`. | ✅ documented |
| F5 | Info | Exclusion | `services/puzzleAdapter.ts` NOT deleted — it exports `adaptToPagesPuzzle` which is active. Only the deleted `adaptToLegacyPuzzle` is gone (already removed in spec 115). | ✅ N/A |
| F6 | Info | Dependency | `types/indexes.ts` is KEPT — it has 20+ active imports. Only its stale manifest comment (line 25) is cleaned. | ✅ T27 |

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | QualityFilter.tsx | Low | B6 isolated; async→sync swap; test gate T40 | T36 | ✅ addressed |
| RE-2 | downstream | config/cdn.ts | Cosmetic | Remove stale comment referencing qualityConfig | T38 | ✅ addressed |
| RE-3 | lateral | Test files | Medium | Grep for test imports before deletion (T1, T13, T20, T28) | T1, T13, T20, T28 | ✅ addressed |
| RE-4 | lateral | sw.ts caching | Low | Only remove dead patterns; preserve active .db, .sgf, .wasm | T30–T32 | ✅ addressed |
| RE-5 | downstream | AGENTS.md consumers | Low | Regen is last batch (B11) so reflects final state | T59–T60 | ✅ addressed |
| RE-6 | upstream | types/indexes.ts | None | File kept; only comment cleaned | T27 | ✅ addressed |
| RE-7 | lateral | Timed-loader chain | Excluded | Separate initiative per Q4 decision | N/A | ✅ excluded by design |
| RE-8 | lateral | Active services (rulesEngine, boardAnalysis, puzzleGameState) | None | Not touched in any task | N/A | ✅ no impact |
| RE-9 | lateral | solutionVerifier.ts (active) | None | Preserved; only unused sgfSolutionVerifier deleted | T6 | ✅ addressed |
| RE-10 | upstream | config/puzzle-quality.json | None | Read-only; lib/quality/config.ts already imports it | T34–T35 | ✅ addressed |
