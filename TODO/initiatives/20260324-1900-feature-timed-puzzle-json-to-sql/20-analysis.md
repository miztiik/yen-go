# Analysis — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24
**Planning Confidence Score**: 92
**Risk Level**: low
**Research Invoked**: No (confidence ≥ 70, risk low, no external patterns needed)

---

## 1. Consistency Findings

| finding_id | severity | area | finding | resolution |
|------------|----------|------|---------|------------|
| F1 | info | charter↔plan | Charter lists E3 as "Remove `path` from `CollectionSummary`"; plan confirms 0 consumers | ✅ consistent |
| F2 | info | charter↔tasks | Charter AC-1 through AC-7 all mapped to verification tasks T13-T15 | ✅ consistent |
| F3 | info | options↔plan | OPT-1 selected; plan implements single-commit approach | ✅ consistent |
| F4 | minor | charter↔tasks | Charter E5 (loader.ts stale CDN comment) added post-governance RC-1 — verified task T11 covers it | ✅ addressed |
| F5 | info | plan↔tasks | DD-3 (keep interface types, only remove 2 functions) reflected in T8 detail: only `isDailyIndexV2` + `isTimedV2` removed | ✅ consistent |
| F6 | info | plan↔tasks | DD-5 (keep VIEW_PATHS) verified — not in T8 removal list | ✅ consistent |
| F7 | resolved | governance | GOV-PLAN-CONDITIONAL: E1/T8 scope shrunk from 8 types to 2 functions per R1 architect review | ✅ addressed |
| F8 | resolved | governance | GOV-PLAN-CONDITIONAL: D7 dropped (`app.tsx.new` does not exist) per R2 integrity review | ✅ addressed |
| F9 | resolved | governance | GOV-PLAN-CONDITIONAL: E2/T10 extended to include `views/by-collection/` per R2 integrity review | ✅ addressed |

---

## 2. Coverage Map

| Charter Item | Mapped Task(s) | Status |
|-------------|----------------|--------|
| D1: useTimedPuzzles.ts | T1 | ✅ |
| D2: timed-loader.ts | T2 | ✅ |
| D3: daily-loader.ts | T3 | ✅ |
| D4: tag-loader.ts | T4 | ✅ |
| D5: dailyPath.ts | T5 | ✅ |
| D6: cdn.ts | T6 | ✅ |
| D7: app.tsx.new | — (DROPPED) | ❌ file does not exist |
| E1: indexes.ts orphan functions | T8 | ✅ (2 functions only) |
| E2: collectionService.ts vestigial paths | T10 | ✅ |
| E3: collection.ts path field | T9 | ✅ |
| E4: AGENTS.md | T12 | ✅ |
| E5: loader.ts CDN comment | T11 | ✅ |
| AC-1: 0 remaining imports | T15 (grep gate) | ✅ |
| AC-2: grep verification | T15 | ✅ |
| AC-3: no orphan function exports | T8 | ✅ |
| AC-4: no views/by-* refs | T10 | ✅ |
| AC-5: vitest passes | T14 | ✅ |
| AC-6: tsc passes | T13 | ✅ |
| AC-7: AGENTS.md updated | T12 | ✅ |

**Unmapped tasks**: None. All tasks trace to charter items.

---

## 3. Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| IMP-1 | downstream | TS barrel `types/index.ts` | Barrel re-exports some deleted types (if any barrel re-export points to removed orphans) | T8 only removes types NOT in barrel; barrel-re-exported `DailyTimed`, `DailyStandard`, `isDailyIndex` are KEPT | T8 | ✅ addressed |
| IMP-2 | downstream | `collectionService.ts` construction | Removing `CollectionSummary.path` field causes TS error on construction sites | T10 removes the construction-site `path:` lines after T9 removes the interface field | T9, T10 | ✅ addressed |
| IMP-3 | lateral | `pagination.ts` → `VIEW_PATHS` | pagination.ts imports `VIEW_PATHS` which is active | DD-5 keeps `VIEW_PATHS` — no impact | — | ✅ addressed |
| IMP-4 | lateral | `usePaginatedPuzzles.ts` | Uses `ViewEntry` from indexes.ts | `ViewEntry` is KEPT — no impact | — | ✅ addressed |
| IMP-5 | lateral | `dailyChallengeService.ts` | Imports `DailyIndex`, `DailyTimedV2`, `DailyByTag`, `DailyStandardV2`, `DailyPuzzleEntry` | All 5 types are KEPT — no impact | — | ✅ addressed |
| IMP-6 | upstream | CDN config | `loader.ts` had stale comment referencing deleted `@/config/cdn` | T11 removes the stale comment | T11 | ✅ addressed |
| IMP-7 | lateral | Tests | Test files may import from deleted files or use deleted types | T14 (vitest gate) catches any test breakage | T14 | ✅ addressed |
| IMP-8 | downstream | `CollectionPuzzleEntry.path` | Must NOT be removed (actively used at `collectionService.ts:918,926`) | DD-2 explicitly preserves `CollectionPuzzleEntry.path` | T9 | ✅ addressed |

---

## 4. Quality Assessment

| Dimension | Assessment |
|-----------|-----------|
| Scope completeness | ✅ All charter items mapped to tasks |
| Test strategy | ✅ tsc + vitest + grep verification gates |
| Rollback | ✅ Single `git revert` — no data migration |
| Documentation | ✅ AGENTS.md update in same commit |
| Risk | Low — all files have 0 consumers, verified exhaustively |
| Confidence | 92/100 — minor uncertainty was type orphan analysis, now resolved |
