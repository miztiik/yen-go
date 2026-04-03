# Options — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24

---

## Options Overview

All three options achieve the same outcome (27 dead files + 2 dirs deleted, docs fixed, quality config merged, AGENTS.md regenerated). They differ in **execution ordering** and **risk isolation**.

---

## OPT-1: Category-Ordered Batches (Recommended)

**Approach**: Group deletions by category (dead code → stale docs → active fixes → merge → regen). Each batch is a logical unit tested in isolation.

### Execution Order

| Batch | Category | Files | Test Gate |
|-------|----------|-------|-----------|
| B1 | Dead services (shard system) | `shardPageLoader.ts`, `snapshotService.ts`, `queryPlanner.ts`, `schemaValidator.ts`, `sgfSolutionVerifier.ts` | `npm test` + `npm run build` |
| B2 | Dead lib dirs | `lib/shards/` (2 files), `lib/rules/` (6 files), `lib/config-loader.ts`, `lib/daily-challenge-loader.ts` | `npm test` + `npm run build` |
| B3 | Dead lib/puzzle files | `manifest.ts`, `refresh.ts`, `level-loader.ts`, `compact-entry.ts`, `_rewrite_pagination.py` | `npm test` + `npm run build` |
| B4 | Dead types + recovery debris | `types/manifest.ts`, `types/snapshot.ts`, `types/source-registry.ts`, `types/mastery.ts`, `app.tsx.new`, `types/index.ts` comment fix | `npm test` + `npm run build` |
| B5 | Service worker cleanup | `sw.ts` — remove stale `manifest` + `puzzles/` patterns | `npm test` + `npm run build` |
| B6 | Quality config merge | `services/qualityConfig.ts` → `lib/quality/config.ts`, update `QualityFilter.tsx` | `npm test` + `npm run build` |
| B7 | Stale docs deletion | Delete `snapshot-shard-terminology.md`, `snapshot-deployment-topology.md`, `view-index-types.md` | N/A (docs only) |
| B8 | Docs factual fixes | Fix 6 architecture docs (`structure.md`, `overview.md`, `puzzle-solving.md`, `puzzle-modes.md`, `sgf-processing.md`, `go-rules-engine.md`) | N/A (docs only) |
| B9 | README.md rewrite | Rewrite Data Sources, Key Services, Routes sections | N/A (docs only) |
| B10 | CLAUDE.md update | Add missing services, pages, lib directories | N/A (docs only) |
| B11 | AGENTS.md regeneration | Full regeneration using prompt template | N/A (docs only) |

### Benefits
- Logical grouping makes review easy — each batch is thematically coherent
- Test gates after each code batch catch issues early
- Docs batches are risk-free and can be done in parallel after code is done
- Easy to pause/resume at any batch boundary

### Drawbacks
- 11 batches may feel like overkill for a cleanup
- Quality config merge (B6) is the only non-trivial code change, sitting mid-sequence

### Risk: Low
### Complexity: Low
### Rollback: Git revert per batch

---

## OPT-2: Two-Phase (Code Then Docs)

**Approach**: All code deletions + quality merge in Phase 1 (single commit). All doc fixes in Phase 2 (single commit).

### Execution Order

| Phase | Scope | Test Gate |
|-------|-------|-----------|
| P1 | Delete 27 files + 2 dirs + merge qualityConfig + fix sw.ts + fix `types/index.ts` comment | `npm test` + `npm run build` |
| P2 | Delete 3 stale docs + fix 6 docs + rewrite README + update CLAUDE.md + regen AGENTS.md | N/A (docs only) |

### Benefits
- Only 2 commits — minimal git overhead
- Fast execution — no intermediate test runs
- Clear separation: code changes vs documentation changes

### Drawbacks
- **High blast radius in P1** — if TypeScript compilation fails, harder to identify which deletion caused the issue
- If any file has a hidden import, debugging across 30+ simultaneous deletions is painful
- Quality config merge mixed with mass deletion — harder to review
- No granular rollback (revert all or nothing in P1)

### Risk: Medium
### Complexity: Low
### Rollback: Git revert P1 (all code) or P2 (all docs)

---

## OPT-3: Dependency-Ordered (Bottom-Up)

**Approach**: Delete in strict dependency order — leaf files first, then their importers, then types, then docs. Quality config merge last (it's a behavioral change).

### Execution Order

| Step | Action | Why This Order |
|------|--------|---------------|
| S1 | Delete leaf dead files (`lib/rules/liberties.ts`, `lib/rules/captures.ts`, `lib/rules/ko.ts`, `lib/rules/suicide.ts`, `lib/shards/shard-key.ts`, `lib/shards/count-tier.ts`) | No dependents |
| S2 | Delete their importers (`lib/rules/engine.ts`, `lib/rules/index.ts`, `services/queryPlanner.ts`, `services/snapshotService.ts`) | Dependents removed in S1 |
| S3 | Delete next level (`services/shardPageLoader.ts`, `services/schemaValidator.ts`, `services/sgfSolutionVerifier.ts`) | No remaining live imports |
| S4 | Delete standalone dead files (`lib/config-loader.ts`, `lib/daily-challenge-loader.ts`, `lib/puzzle/manifest.ts`, `lib/puzzle/refresh.ts`, `lib/puzzle/level-loader.ts`, `lib/puzzle/compact-entry.ts`, `lib/puzzle/_rewrite_pagination.py`) | Independent |
| S5 | Delete dead types (`types/manifest.ts`, `types/snapshot.ts`, `types/source-registry.ts`, `types/mastery.ts`) | No remaining consumers |
| S6 | Delete recovery debris (`app.tsx.new`) + fix `types/index.ts` comment | Cleanup |
| S7 | Fix `sw.ts` stale patterns | Independent |
| S8 | Quality config merge | Behavioral change, isolated |
| S9 | All docs (delete 3 + fix 6 + README + CLAUDE.md + AGENTS.md) | Post-code |

### Benefits
- Maximum safety — each step only deletes files whose consumers are already gone
- If a hidden import exists, it surfaces at the exact step

### Drawbacks
- 9 steps with test gates is slow
- Dependency ordering is overly cautious — since ALL files have 0 active imports, ordering doesn't add real safety
- More complex to track

### Risk: Very Low (but overkill)
### Complexity: Medium (more steps to track)
### Rollback: Git revert per step

---

## Comparison Matrix

| Criterion | OPT-1 (Category) | OPT-2 (Two-Phase) | OPT-3 (Bottom-Up) |
|-----------|-------------------|--------------------|--------------------|
| Risk isolation | ✅ Good (per-category) | ❌ Low (30+ files at once) | ✅ Best (per-dependency) |
| Test frequency | ✅ 6 code gates | ⚠️ 1 code gate | ✅ 8 code gates |
| Rollback granularity | ✅ Per batch | ⚠️ All-or-nothing code | ✅ Per step |
| Execution speed | ⚠️ 11 batches | ✅ 2 phases | ⚠️ 9 steps |
| Cognitive load for review | ✅ Low (thematic) | ⚠️ Medium (big diff) | ⚠️ Medium (dependency reasoning) |
| AGENTS.md regen timing | ✅ Last (clean state) | ✅ Last (clean state) | ✅ Last (clean state) |
| Quality merge isolation | ✅ Own batch (B6) | ❌ Mixed with mass delete | ✅ Own step (S8) |

**Recommendation**: **OPT-1** — best balance of safety, review clarity, and practical execution speed. Category-ordered batches are intuitive for reviewers and provide adequate test gates without the overhead of 9 dependency-ordered steps.
