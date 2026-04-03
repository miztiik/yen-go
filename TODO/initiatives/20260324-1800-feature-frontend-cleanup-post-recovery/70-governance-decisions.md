# Governance Decisions — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24

---

## Charter Review (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-CHARTER-APPROVED`
**Unanimous**: Yes (10/10)

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Charter cleanly separates dead code from active puzzle infrastructure. Q5 correctly preserves active verifier. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Timed-loader deferral is principled — broken import needs investigation, not silent deletion. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Two-pass research with transitive import analysis is correct methodology. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Quality config merge from async to sync Vite import is clean improvement. |
| GV-5 | Staff Engineer A | Systems architect | approve | All required charter elements present. Minor file count discrepancy (27 vs 26+1) non-blocking. |
| GV-6 | Staff Engineer B | Data pipeline | approve | Service worker cleanup correct. SQLite/WASM patterns preserved. |
| GV-7 | Hana Park (1p) | Player experience | approve | No behavioral changes guarantee is critical. Quality filter UX improves (no loading flash). |
| GV-8 | Mika Chen | DevTools UX | approve | AGENTS.md/CLAUDE.md updates improve developer onboarding. |
| GV-9 | Dr. David Wu | KataGo | approve | No KataGo/enrichment overlap. Pass. |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve | Active verifier correctly preserved. Dead rules engine safe to delete. |

### Handover

- **From**: Governance-Panel → Feature-Planner
- **Required**: Create `25-options.md` with 2-3 execution strategies, return for options governance.
- **Blocking items**: None.

---

## Options Review (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`
**Unanimous**: Yes (10/10)
**Selected Option**: `OPT-1` — Category-Ordered Batches

### Key Selection Rationale
- Quality merge isolation (B6) is OPT-1's critical advantage — only change modifying active imports
- Dependency ordering (OPT-3) unnecessary — all files have 0 active imports
- OPT-2 blast radius too high — 30+ simultaneous deletions harder to debug

### Must-Hold Constraints
1. `npm test` + `npm run build` after every code batch B1–B6
2. Stage files by explicit path only — never `git add .`
3. B11 AGENTS.md regen must be last batch
4. B6 quality merge must NOT be combined with any deletion batch

### Handover

- **From**: Governance-Panel → Feature-Planner
- **Required**: Create `30-plan.md` + `40-tasks.md`, return for plan governance.
- **Blocking items**: None.

---

## Plan Review (2026-03-24)

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`
**Vote**: 9 approve, 2 concern → approve_with_conditions

### Required Changes (resolved)

| rc_id | severity | artifact | fix | status |
|-------|----------|----------|-----|--------|
| RC-1 | Major | `30-plan.md`, `40-tasks.md` | Fix B7 doc paths: T41 → `docs/archive/snapshot-shard-terminology.md`, T42 → `docs/archive/snapshot-deployment-topology.md` | ✅ Fixed |
| RC-2 | Minor | `40-tasks.md` | Change T55–T58 from `[S]` sequential to `[P] D:T54` parallel | ✅ Fixed |

### Handover to Executor

- **From**: Governance-Panel → Plan-Executor
- **Message**: Execute B1–B11 in order. Test gates after B1–B6. B11 (AGENTS.md regen) must be last. B6 (quality merge) must be isolated. Return for `review` governance after T64.
- **Blocking items**: None (RC-1 and RC-2 resolved).

---

## Implementation Review (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: Yes (8/8)

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Dead lib/rules/ correctly removed; active rulesEngine.ts handles all Go rules |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Timed-loader deferral (RE-7) was correct — conservative approach for latent crash |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Two-pass research methodology sound; grep verification provides confirmation |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Quality config merge correctly isolated; async→sync eliminates loading flash |
| GV-5 | Staff Engineer A | Systems architect | approve | 64/64 tasks, 12/12 AC met, 0 test regressions. CRA-1 and CRB-1 are pre-existing |
| GV-6 | Staff Engineer B | Data pipeline | approve | sw.ts cleanup correct; test count decrease matches dead test file deletion |
| GV-7 | Hana Park (1p) | Player experience | approve | No player-facing changes. QualityFilter loading flash eliminated |
| GV-8 | Mika Chen | DevTools UX | approve | AGENTS.md regen (379 lines) and CLAUDE.md (+114 lines) fill critical gaps |

### Observations (Non-Blocking)

| obs_id | observation | severity | disposition |
|--------|-------------|----------|-------------|
| OBS-1 | AC-9 import path deviation (models/quality vs lib/quality/config) — functionally correct | Minor | Noted |
| OBS-2 | lib/quality/generated-types.ts overlaps with config.ts — pre-existing duplication | Minor | Future cleanup |

### Handover

- **From**: Governance-Panel → Plan-Executor
- **Message**: Implementation review passed. Proceed to closeout governance.
- **Blocking items**: None.

---

## Closeout Audit (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Unanimous**: Yes (10/10)

### Closeout Verification

| check | status |
|-------|--------|
| All phase_states approved | ✅ |
| 64/64 tasks completed | ✅ |
| 12/12 acceptance criteria met | ✅ |
| 0 test regressions | ✅ |
| 10/10 ripple effects validated | ✅ |
| 9 docs updated/rewritten | ✅ |
| Governance chain unbroken (5 gates) | ✅ |
| No open issues | ✅ |

### Member Reviews

| review_id | member | domain | vote |
|-----------|--------|--------|------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve |
| GV-5 | Staff Engineer A | Systems architect | approve |
| GV-6 | Staff Engineer B | Data pipeline | approve |
| GV-7 | Hana Park (1p) | Player experience | approve |
| GV-8 | Mika Chen | DevTools UX | approve |
| GV-9 | Dr. David Wu | KataGo | approve |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve |

### Residual Risks (Pre-Existing, Not Introduced)

1. `useTimedPuzzles` latent crash — separate initiative (Q4-BRIEF)
2. `hints.test.tsx` / `migrations.test.ts` pre-existing failures
3. `useNavigationContext.ts` pre-existing build error
4. `lib/quality/generated-types.ts` overlapping exports with `config.ts`

### Handover

- **From**: Governance-Panel → User
- **Message**: Initiative complete. All 5 governance gates passed.
- **Blocking items**: None.
