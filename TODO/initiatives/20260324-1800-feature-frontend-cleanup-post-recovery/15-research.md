# Research — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24

---

## Research Sources

This initiative is informed by two comprehensive research passes:

1. **Code Audit**: [`TODO/initiatives/20260324-research-frontend-cleanup-deep-audit/15-research.md`](../20260324-research-frontend-cleanup-deep-audit/15-research.md)
2. **Docs/README/AGENTS.md Audit**: [`TODO/initiatives/frontend-docs-gap-audit/15-research.md`](../frontend-docs-gap-audit/15-research.md)

---

## Consolidated Findings Summary

### Dead Code (26 files + 2 directories — 0 active imports)

| ID | File | Category | Lines (est.) |
|----|------|----------|--------------|
| DC-1 | `services/shardPageLoader.ts` | Shard system | ~150 |
| DC-2 | `services/snapshotService.ts` | Shard system | ~200 |
| DC-3 | `services/queryPlanner.ts` | Shard system | ~120 |
| DC-4 | `services/schemaValidator.ts` | Old validation | ~80 |
| DC-5 | `services/sgfSolutionVerifier.ts` | YAGNI verifier | ~100 |
| DC-6 | `lib/shards/shard-key.ts` | Shard system | ~30 |
| DC-7 | `lib/shards/count-tier.ts` | Shard system | ~40 |
| DC-8 | `lib/rules/engine.ts` | Deprecated rules | ~200 |
| DC-9 | `lib/rules/index.ts` | Deprecated rules | ~10 |
| DC-10 | `lib/rules/liberties.ts` | Deprecated rules | ~60 |
| DC-11 | `lib/rules/captures.ts` | Deprecated rules | ~80 |
| DC-12 | `lib/rules/ko.ts` | Deprecated rules | ~40 |
| DC-13 | `lib/rules/suicide.ts` | Deprecated rules | ~30 |
| DC-14 | `lib/config-loader.ts` | Deprecated loader | ~50 |
| DC-15 | `lib/daily-challenge-loader.ts` | Superseded loader | ~200 |
| DC-16 | `lib/puzzle/manifest.ts` | Old manifest | ~60 |
| DC-17 | `lib/puzzle/refresh.ts` | Old manifest | ~40 |
| DC-18 | `lib/puzzle/level-loader.ts` | Stub loader | ~30 |
| DC-19 | `lib/puzzle/compact-entry.ts` | Duplicate decoder | ~70 |
| DC-20 | `lib/puzzle/_rewrite_pagination.py` | Script debris | ~50 |
| DC-21 | `types/manifest.ts` | Old types | ~40 |
| DC-22 | `types/snapshot.ts` | Old types | ~150 |
| DC-23 | `types/source-registry.ts` | Old types | ~30 |
| DC-24 | `types/mastery.ts` | Duplicate types | ~20 |
| DC-25 | `app.tsx.new` | Recovery debris | ~635 |
| DC-26 | `types/indexes.ts` comment about manifests | Comment stale | ~2 |
| — | `lib/shards/` (directory) | Entire dead dir | — |
| — | `lib/rules/` (directory) | Entire dead dir | — |

**Estimated total removable lines**: ~3,000

### Stale Documentation (22 issues across 8+ files)

| Priority | Document | Issue Count | Severity |
|----------|----------|-------------|----------|
| P0 | `frontend/README.md` | 13 issues | Critical — describes wrong architecture |
| P1 | `docs/concepts/snapshot-shard-terminology.md` | Full doc stale | Archive candidate |
| P1 | `docs/architecture/snapshot-deployment-topology.md` | Full doc stale | Archive candidate |
| P1 | `docs/architecture/frontend/view-index-types.md` | Full doc stale | Archive candidate |
| P1 | `docs/architecture/frontend/structure.md` | References non-existent files | Fix |
| P1 | `docs/architecture/frontend/overview.md` | References dead config-loader.ts | Fix |
| P2 | `frontend/src/AGENTS.md` | Missing ~50% entries | Regenerate |
| P2 | `docs/architecture/frontend/puzzle-solving.md` | Describes non-existent interfaces | Fix |
| P2 | `docs/architecture/frontend/puzzle-modes.md` | Lists non-existent mode, old format | Fix |
| P2 | `docs/architecture/frontend/sgf-processing.md` | Wrong "single parser" claim | Fix |
| P2 | `docs/architecture/frontend/go-rules-engine.md` | Documents dead lib/rules/ | Fix |
| P2 | `docs/architecture/frontend/svg-board.md` | Contradicts renderer analysis | Reconcile |
| P3 | `frontend/CLAUDE.md` | 14 missing/stale sections | Update |
| P3 | `docs/architecture/frontend/state-management.md` | Wrong storage prefix | Fix |

### Service Worker Stale Patterns (2 issues)

| ID | Pattern | Status |
|----|---------|--------|
| SW-1 | `manifest: /\/manifest\.json$/` | Dead — no manifest.json in SQLite arch |
| SW-2 | `puzzles: /\/(puzzles\|...)\/.*\.json$/` | Stale — `puzzles/` prefix is from old arch |

---

## Planning Confidence

| Metric | Pre-Research | Post-Research |
|--------|-------------|---------------|
| Confidence Score | 55 | **88** |
| Risk Level | medium | **low** |
| Research Invoked | — | Yes (2 passes) |

---

## Open Questions for Clarification

Consolidated from both research passes — see `10-clarifications.md` for full table.
