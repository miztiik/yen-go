# Governance Decisions (v2)

_Last Updated: 2026-03-29_

## Historical (v1) — ARCHIVED

v1 of this initiative focused on pipeline changes (analyze.py source_link fix, YM.sl extension, sources.json OGS path change, featured:boolean schema). Three governance gates were passed. The user fundamentally redirected the approach to a pre-pipeline utility. All v1 decisions are invalidated.

## v2 Gates

### Gate 1: Combined Charter + Options Review

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Decision | approve_with_conditions |
| Status Code | GOV-CHARTER-CONDITIONAL + GOV-OPTIONS-CONDITIONAL |
| Selected Option | OPT-2: Multi-Strategy Embedder |

#### Panel Support

| id | member | domain | vote |
|----|--------|--------|------|
| GV-1 | Cho Chikun (9p) | Go domain authority | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Principal Staff Engineer A | Systems architecture | concern |
| GV-5 | Principal Staff Engineer B | Data pipeline | concern |
| GV-6 | Hana Park (1p) | Player experience | approve |
| GV-7 | Mika Chen (DevTools UX) | Developer tools UX | approve |

#### Required Changes (Pre-Plan)

| rc_id | description | status |
|-------|-------------|--------|
| RC-1 | Promote `.new` artifact files → replace originals | ❌ pending |
| RC-2 | Reset status.json with OPT-2, phase states reset | ❌ pending |
| RC-3 | Rewrite plan/tasks/analysis for v2 scope | ✅ done (.new files created) |
| RC-4 | G8 (in-section search): specify SQL approach in plan | ✅ done (collections_fts + type filter) |
| RC-5 | OGS coverage validation ≥80% threshold in plan | ✅ done |
| RC-6 | Dry-run mode + checkpoint resume in plan | ✅ done |
| RC-7 | JSONL logging event schema in plan | ✅ done |
| RC-8 | Minimal-edit SGF exception documented in plan | ✅ done |

#### Selection Rationale

OPT-2 is the only option covering all ~50K exploitable puzzles while maintaining DRY/SOLID compliance. OPT-1 misses 42K OGS puzzles. OPT-3 violates DRY with 5+ copies of similar logic.

#### Must-Hold Constraints
1. `tools/core/` does NOT import from `backend/`
2. Backward-compatible YL values (additive only)
3. Minimal-edit SGF approach (embedder adds/updates YL only)
4. Strategy B (OGS) includes ≥80% coverage validation
5. DRY consolidation of 4 matchers is prerequisite
6. Dry-run mode for all strategies

### Gate 2: Plan Review

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Decision | approve_with_conditions |
| Status Code | GOV-PLAN-CONDITIONAL |

#### Panel Support

| id | member | domain | vote |
|----|--------|--------|------|
| GV-1 | Cho Chikun (9p) | Go domain authority | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Principal Staff Engineer A | Systems architecture | concern |
| GV-5 | Principal Staff Engineer B | Data pipeline | concern |
| GV-6 | Hana Park (1p) | Player experience | approve |
| GV-7 | Mika Chen (DevTools UX) | Developer tools UX | approve |
| GV-8 | Dr. David Wu (KataGo) | MCTS engine | approve |
| GV-9 | Dr. Shin Jinseo (Tsumego) | Tsumego correctness | approve |

#### Required Changes (All Resolved)

| rc_id | description | status |
|-------|-------------|--------|
| RC-1 | T6: explicit type resolution — CollectionViewPage passes `collectionType` to loader | ✅ fixed |
| RC-2 | T3b: scope pinned — IN: kisvadim + gotools; DEFERRED: eidogo, tasuki, 101weiqi, syougo | ✅ fixed |
| RC-3 | T2: SGF formatting — round-trip whitespace diffs acceptable for pre-ingest files | ✅ fixed |
| RC-4 | T10: dry-run enforcement — must execute BEFORE any actual writes | ✅ fixed |
| RC-5 | T5: section visibility threshold — hide section if <2 collections visible | ✅ fixed |
| RC-6 | Promote .new files + reset status.json for OPT-2 | ✅ fixed |

#### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve_with_conditions |
| message | Plan v2 (OPT-2: Multi-Strategy Embedder) approved. All 6 RCs resolved. Execute Phase 1 first: T1 (matcher consolidation) → T2 (embedder core) → T3 (OGS wrapper) + T3b (kisvadim+gotools). Then T10 dry-run validation before actual writes. Phase 3 frontend tasks parallelizable. |
| blocking_items | (none — all RCs resolved) |

### Gate 3: Implementation Review

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Decision | approve |
| Status Code | GOV-REVIEW-APPROVED |
| Unanimous | 9/9 |

#### Required Changes

| rc_id | description | status |
|-------|-------------|--------|
| RC-1 | Track dead code cleanup of modular `CollectionPuzzleLoader.ts` as follow-up | ✅ tracked (not blocking) |

### Gate 4: Closeout Audit

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Decision | approve |
| Status Code | GOV-CLOSEOUT-APPROVED |
| Unanimous | 9/9 |

#### Summary
All 10 charter goals met. 86 tests pass. 6 documentation files updated. Architecture boundaries clean. Full traceability: goals → tasks → execution → validation. Two minor housekeeping items: status.json phase update (✅ done) and dead code cleanup (follow-up tracked).
