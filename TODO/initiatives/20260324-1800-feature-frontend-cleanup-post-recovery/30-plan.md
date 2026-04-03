# Plan — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Selected Option**: OPT-1 — Category-Ordered Batches
**Last Updated**: 2026-03-24

---

## Architecture Decision

No new architecture required. This initiative removes dead code and fixes documentation to align with the existing SQLite architecture. The only behavioral change is merging `services/qualityConfig.ts` (async runtime fetch) into `lib/quality/config.ts` (sync build-time Vite import).

## Execution Strategy

11 batches in category order. Test gates after each code batch (B1–B6). Docs batches (B7–B11) are risk-free.

---

## Batch Specifications

### B1: Dead Services (Shard System + Unused Verifier)

**Delete 5 files:**

| File | Purpose (dead) | Verified 0 imports |
|------|----------------|--------------------|
| `frontend/src/services/shardPageLoader.ts` | Old shard page loading | ✅ |
| `frontend/src/services/snapshotService.ts` | Old snapshot/manifest loading | ✅ |
| `frontend/src/services/queryPlanner.ts` | Old shard query planning | ✅ |
| `frontend/src/services/schemaValidator.ts` | Old JSON schema validation | ✅ |
| `frontend/src/services/sgfSolutionVerifier.ts` | Unused SGF-native verifier (YAGNI) | ✅ |

**Also delete associated tests** (any test files in `services/__tests__/` that import only from these modules).

**Test gate**: `npm test` + `npm run build`

### B2: Dead Lib Directories + Standalone Loaders

**Delete 2 directories (8 files) + 2 standalone files:**

| File/Dir | Purpose (dead) | Verified 0 imports |
|----------|----------------|--------------------|
| `frontend/src/lib/shards/shard-key.ts` | Shard key construction | ✅ |
| `frontend/src/lib/shards/count-tier.ts` | Count accuracy tier | ✅ |
| `frontend/src/lib/rules/engine.ts` | Deprecated Go rules (string-based) | ✅ |
| `frontend/src/lib/rules/index.ts` | Barrel export | ✅ |
| `frontend/src/lib/rules/liberties.ts` | Liberty counting | ✅ |
| `frontend/src/lib/rules/captures.ts` | Capture detection | ✅ |
| `frontend/src/lib/rules/ko.ts` | Ko rule | ✅ |
| `frontend/src/lib/rules/suicide.ts` | Suicide rule | ✅ |
| `frontend/src/lib/config-loader.ts` | Deprecated config loader | ✅ |
| `frontend/src/lib/daily-challenge-loader.ts` | Superseded daily JSON loader | ✅ |

**Test gate**: `npm test` + `npm run build`

### B3: Dead lib/puzzle Files

**Delete 5 files:**

| File | Purpose (dead) | Verified 0 imports |
|------|----------------|--------------------|
| `frontend/src/lib/puzzle/manifest.ts` | Old manifest loading | ✅ |
| `frontend/src/lib/puzzle/refresh.ts` | Old manifest auto-refresh | ✅ |
| `frontend/src/lib/puzzle/level-loader.ts` | Stub loader (throws NotImplementedError) | ✅ |
| `frontend/src/lib/puzzle/compact-entry.ts` | Duplicate of entryDecoder.ts | ✅ |
| `frontend/src/lib/puzzle/_rewrite_pagination.py` | Python script artifact | ✅ |

**Test gate**: `npm test` + `npm run build`

### B4: Dead Types + Recovery Debris

**Delete 4 type files + 1 recovery file + 1 comment fix:**

| File | Purpose (dead) | Verified 0 imports |
|------|----------------|--------------------|
| `frontend/src/types/manifest.ts` | Old manifest types | ✅ |
| `frontend/src/types/snapshot.ts` | Old snapshot/shard types | ✅ |
| `frontend/src/types/source-registry.ts` | Old source registry types | ✅ |
| `frontend/src/types/mastery.ts` | Duplicate mastery types | ✅ |
| `frontend/src/app.tsx.new` | Recovery debris (635 lines) | ✅ |

**Plus**: Clean stale comment in `frontend/src/types/index.ts` (line 25: `// Manifest types removed — dead code (M1/L1/L2 audit cleanup)` — remove this now-confusing comment).

**Test gate**: `npm test` + `npm run build`

### B5: Service Worker Cleanup

**Modify 1 file:** `frontend/src/sw.ts`

| Change | Detail |
|--------|--------|
| Remove `manifest` regex pattern | `manifest: /\/manifest\.json$/` — dead, no manifest.json exists |
| Update `puzzles` regex pattern | Remove stale `puzzles/` prefix, keep `yengo-puzzle-collections/` |
| Remove stale handler references | Any code referencing `manifest` pattern in fetch handlers |

**Test gate**: `npm test` + `npm run build`

### B6: Quality Config Merge (Behavioral Change)

**Modify 2 files, delete 1:**

| Action | File | Detail |
|--------|------|--------|
| **Extend** | `frontend/src/lib/quality/config.ts` | Add `selectionWeight`, `requirements`, `displayColor` fields to `QualityMeta` from the JSON config |
| **Rewrite** | `frontend/src/components/QualityFilter.tsx` | Change `import { loadQualityConfig } from '../services/qualityConfig'` → `import { QUALITIES } from '@/lib/quality/config'`. Remove async loading state (`setIsConfigLoaded`). Use synchronous `QUALITIES` array. |
| **Delete** | `frontend/src/services/qualityConfig.ts` | No longer needed — build-time config replaces runtime fetch |
| **Update** | `frontend/src/config/cdn.ts` | Remove comment referencing `qualityConfig.ts` (line 18) |

**Test gate**: `npm test` + `npm run build` (critical — this is the only active-code behavior change)

### B7: Stale Docs Deletion

**Delete 3 files:**

| File | Why |
|------|-----|
| `docs/archive/snapshot-shard-terminology.md` | Describes fully superseded shard/manifest system |
| `docs/archive/snapshot-deployment-topology.md` | Full ADR for replaced snapshot architecture |
| `docs/architecture/frontend/view-index-types.md` | Describes old JSON compact entry pagination |

### B8: Docs Factual Fixes

**Fix 6 files:**

| File | Fix |
|------|-----|
| `docs/architecture/frontend/structure.md` | Remove references to non-existent `puzzleService.ts`, `progressService.ts`, `puzzle.ts`, `progress.ts`, `achievements.ts`. Update with actual file names. |
| `docs/architecture/frontend/overview.md` | Remove reference to dead `config-loader.ts`. Update boot sequence to reflect `boot.ts` + `configService.ts`. |
| `docs/architecture/frontend/puzzle-solving.md` | Update `MoveNode` type description to match actual `SolutionNode` from `lib/sgf-solution.ts`. |
| `docs/architecture/frontend/puzzle-modes.md` | Remove non-existent "Survival" mode. Update daily challenge format to SQLite tables. |
| `docs/architecture/frontend/sgf-processing.md` | Fix "single SGF parser" claim — document all 3 SGF modules (`sgf-parser.ts`, `sgf-metadata.ts`, `sgf-preprocessor.ts`). |
| `docs/architecture/frontend/go-rules-engine.md` | Update to document active `services/rulesEngine.ts` (integer Stone), not dead `lib/rules/` (string Stone). |

### B9: README.md Rewrite

**Rewrite 3 sections in `frontend/README.md`:**

| Section | Fix |
|---------|-----|
| "Puzzle Data Sources" | Rewrite from JSON shard description to SQLite architecture (`yengo-search.db` + `sgf/{NNNN}/`) |
| "Key Services" | Replace with current services: `sqliteService`, `puzzleQueryService`, `entryDecoder`, `configService`, `dailyQueryService`, `boardAnalysis`, `puzzleGameState`, `solutionVerifier`, `progressAnalytics` |
| "Routes" | Fix component names to match actual files. Add missing routes (`/progress`, `/smart-practice`, `/rush-browse`, `/achievements`, `/random-page`, `/review`). |

**Also**: Update SGF custom properties table to schema v15 (currently shows v8).

### B10: CLAUDE.md Update

**Update `frontend/CLAUDE.md`:**

| Section | Fix |
|---------|-----|
| "Key Directories" `lib/` | Add missing subdirs: `achievements/`, `presentation/`, `progress/`, `review/`, `rush/`, `sgf/`, `solver/`, `tree/` |
| "Key Directories" | Add missing `constants/`, `contexts/`, `data/` directories |
| New section or expanded | Document `GobanBoard/` vs `GobanContainer/` distinction |
| New section | List active pages beyond current 5 (30+ exist) |
| New section | Document undocumented active services |

### B11: AGENTS.md Regeneration

**Full regeneration of `frontend/src/AGENTS.md`:**

Using `.github/prompts/regen-agents-map.prompt.md` template. Must be done LAST (after all deletions) to reflect final file state.

Must cover:
- All ~30+ pages
- All ~20 hooks
- All ~25 services
- All ~30 lib modules
- All types, models, utils, constants, data, contexts directories
- Updated data flow diagrams
- Updated decommission notes (if still relevant)

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Hidden import to deleted file causes build failure | Low | Test gate after each batch; grep verification before deletion |
| Quality config merge breaks QualityFilter | Low | B6 is isolated; focused test run; manual verify filter renders |
| AGENTS.md regen misses nuances | Low | Review before commit; compare with pre-existing correct entries |
| Test files import dead code | Medium | Search test directories for imports before deleting each batch |
| Stale docs deletion removes useful historical context | Low | User confirmed: git history preserves everything |

---

## Documentation Plan

| doc_action | file | why_updated |
|------------|------|-------------|
| delete | `docs/archive/snapshot-shard-terminology.md` | Superseded by SQLite architecture |
| delete | `docs/archive/snapshot-deployment-topology.md` | Superseded by SQLite architecture |
| delete | `docs/architecture/frontend/view-index-types.md` | Superseded by SQLite architecture |
| fix | `docs/architecture/frontend/structure.md` | References non-existent files |
| fix | `docs/architecture/frontend/overview.md` | References dead `config-loader.ts` |
| fix | `docs/architecture/frontend/puzzle-solving.md` | Describes non-existent interfaces |
| fix | `docs/architecture/frontend/puzzle-modes.md` | Lists non-existent "Survival" mode |
| fix | `docs/architecture/frontend/sgf-processing.md` | Wrong "single parser" claim |
| fix | `docs/architecture/frontend/go-rules-engine.md` | Documents dead `lib/rules/` |
| rewrite | `frontend/README.md` | 3 sections describe wrong architecture |
| update | `frontend/CLAUDE.md` | Missing ~15 services, 20+ pages |
| regen | `frontend/src/AGENTS.md` | Missing ~50% of file entries |

> **See also**:
> - [Concepts: SQLite Index Architecture](../../docs/concepts/sqlite-index-architecture.md) — canonical data architecture
> - [Architecture: Goban Integration](../../docs/architecture/frontend/goban-integration.md) — accurate board integration doc
