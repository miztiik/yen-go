# Analysis — Playing Modes DRY Compliance (OPT-1)

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29
**Planning Confidence Score**: 92 (post-options, post-research)
**Risk Level**: medium
**Research Invoked**: Yes (Feature-Researcher audit of all 8 modes)

---

## 1. Cross-Artifact Consistency

| F | Charter Goal | Plan Section | Task IDs | Covered? |
|---|-------------|-------------|----------|----------|
| F1 | Migrate Rush to PSP + SolverView | Plan §1, §7 | T22-T25 | ✅ |
| F2 | Migrate Random to PSP | Plan §8 | T16-T18 | ✅ |
| F3 | SolverView `minimal` variant | Plan §1 | T08, T11, T13 | ✅ |
| F4 | StreamingLoader interface | Plan §2 | T09, T12, T15 | ✅ |
| F5 | Delete dead code (5 files) | Plan Phase 1 | T02-T06 | ✅ |
| F6 | Delete InlineSolver | Plan §7 | T27 | ✅ |
| F7 | Delete RushPuzzleRenderer | Plan §7 | T28 | ✅ |
| F8 | Playwright canvas-click play tests | Plan §Playwright | T36, T37 | ✅ |
| F9 | Playwright board sizing screenshots | Plan §Playwright | T38, T39 | ✅ |
| F10 | Playwright transition timing | Plan §Playwright | T40 | ✅ |

### Coverage Gaps
- **None found.** All charter goals map to plan sections and task IDs. All acceptance criteria have corresponding Playwright tests.

---

## 2. Governance RC Traceability

| RC | Source | Requirement | Plan Section | Task ID | Status |
|----|--------|-------------|-------------|---------|--------|
| RC-1 | GV-2 (Lee Sedol) | Rush transition <300ms, PSP auto-advance bypassable | Plan §3 | T10, T40 | ✅ addressed |
| RC-2 | GV-4 (Staff Eng A) | Streaming `totalPuzzles` type design | Plan §2 | T09, T12 | ✅ addressed |
| RC-3 | GV-4 (Staff Eng A) | RushOverlay positioning with wider board | Plan §4 | (no task needed — analysis shows no change required) | ✅ addressed |
| RC-4 | GV-6 (Hana Park) | PSP auto-advance timing quantified | Plan §3 | T10 (`failOnWrongDelayMs`) | ✅ addressed |
| RC-5 | Plan GV-6 (Hana Park) | Rush puzzle transition: no skeleton flash, use prefetch | Plan §3 | T22 (prefetch), T23 (no skeleton) | ✅ addressed |
| RC-6 | Plan GV-6 (Hana Park) | Auto-advance override via prop, not global mutation | Plan §3 | T10 (`autoAdvanceEnabled` prop) | ✅ addressed |
| RC-7 | Plan GV-4 (Staff Eng A) | Streaming initial `totalPuzzles` value specified | Plan §2 | T12 | ✅ addressed |

---

## 3. Ripple Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| IMP-1 | upstream | `PuzzleSetLoader` interface — 3 existing implementations (Collection, Daily, Training) | Low — additive interface extension only (StreamingLoader extends, doesn't modify) | StreamingPuzzleSetLoader is new interface; existing loaders unchanged | T09 | ✅ addressed |
| IMP-2 | downstream | `App.tsx` — `renderPuzzle`/`renderRandomPuzzle` callbacks removed | Medium — these are the render-prop indirection that connects Rush/Random to board rendering | Remove in T33-T34 after Rush/Random migrated; verify no other consumers | T33, T34 | ✅ addressed |
| IMP-3 | downstream | Rush test files (19 total: 5 e2e, 6 unit, 2 integration, 6 visual) | Medium — all reference current component structure / testids | Update in T29-T31, T41 | T29-T31, T41 | ✅ addressed |
| IMP-4 | downstream | Random test files (1 unit, 2 visual) | Low — small surface | Update in T19-T20 | T19, T20 | ✅ addressed |
| IMP-5 | lateral | `SolverView` — adding `minimal` prop | Low — single boolean, conditional render | Test in T13 | T08, T13 | ✅ addressed |
| IMP-6 | lateral | `PuzzleSetPlayer` — `failOnWrongDelayMs` + `minimal` + streaming | Medium — 3 new props/behaviors added | Each independently testable; existing behavior unchanged when props absent | T10-T14 | ✅ addressed |
| IMP-7 | lateral | `useRushSession` hook — must bridge to PSP `onPuzzleComplete` | Low — hook is already decoupled from rendering | Bridge in T24; hook itself unchanged | T24 | ✅ addressed |
| IMP-8 | upstream | GobanContainer / `.solver-layout` CSS — Rush board now uses these | Low — battle-tested across 6 modes | No CSS changes needed; SolverView + solver-layout handles everything | (none) | ✅ addressed |
| IMP-9 | downstream | `frontend/src/types/page-mode.ts` — may need 'rush' and 'random' modes if not present | Low — possibly already defined | Check and add if missing | T23, T17 | ✅ addressed |
| IMP-10 | lateral | Barrel exports (`puzzleLoaders/index.ts`, `Rush/index.ts`) | Low — add/remove exports | T15, T28 | T15, T28 | ✅ addressed |

---

## 4. Severity-Based Findings

| F | Severity | Finding | Resolution |
|---|----------|---------|------------|
| F11 | **High** | Rush `failOnWrong` delay is hardcoded 400ms in PSP — Rush needs ~100ms | Plan §3 adds `failOnWrongDelayMs` prop (T10); Playwright timing test (T40) |
| F12 | **Medium** | PuzzleSetPlayer completion detection (`completedCount === totalPuzzles`) breaks with streaming | Plan §2 uses `isStreaming` flag — streaming modes never trigger "all complete" (T12) |
| F13 | **Medium** | App.tsx `getNextPuzzle`/`getRandomPuzzle` move into loaders — 50+ lines of App.tsx affected | Phased approach: Random first (T18), Rush second (T26), cleanup last (T33-T34) |
| F14 | **Low** | RushOverlay is full-width flex bar above board — unaffected by board width changes | No task needed — confirmed in plan §4 |
| F15 | **Low** | SolverView `minimal` might leak unused keyboard shortcut handlers | Minimal variant has no sidebar targets for shortcuts — harmless no-ops |

---

## 5. Unmapped Tasks Check

All 44 tasks map to charter goals or governance RCs. No orphan tasks. No unmapped charter goals.

---

## 6. Test Strategy

| Strategy | Description |
|----------|-------------|
| **Unit** | New: SolverView minimal (T13), failOnWrongDelayMs (T14). Updated: 6 Rush unit + 1 Random unit (T19, T29) |
| **Integration** | Updated: 2 Rush integration tests (T30) |
| **Visual** | Updated: 6 Rush visual + 2 Random visual (T20, T31) |
| **E2E (Playwright)** | New: 5 Playwright tests (T36-T40). Updated: 5 existing Rush e2e (T41) |
| **Evidence** | Canvas-click play tests verify puzzle interaction. Screenshots verify board sizing. Timing measurements verify transition speed. |
