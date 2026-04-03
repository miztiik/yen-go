# Analysis — SQLite Puzzle Index

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`

---

## 1. Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 92 |
| Risk Level | low |
| Research Invoked | Yes (Feature-Researcher, 15-research.md) |
| Research Trigger Reason | External library evaluation (sql.js) + schema design validation |

---

## 2. Cross-Artifact Consistency

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| F1 | Charter goals covered by tasks | ✅ | G1 (DB-1) → T1-T2, T28; G2 (DB-2) → T3, T35-T36; G3 (FTS5) → T2, T20; G4 (frontend) → T8-T27; G5 (daily) → T30; G6 (decommission) → T38-T46; G7 (dedup) → T36-T37; G8 (docs) → T47-T56; G9 (size) → verified in research |
| F2 | Charter acceptance criteria verifiable by tasks | ✅ | AC1 (loads DB) → T10; AC2 (≤1MB) → T4 sample; AC3 (<300ms) → T26 Playwright; AC4 (FTS5) → T14; AC5 (dedup) → T37; AC6 (zero shard) → T46; AC7 (docs) → T47-T56; AC8 (CI) → T33-T34; AC9 (config) → T1; AC10 (types) → T11 |
| F3 | Option election rationale matches plan architecture | ✅ | OPT-1 frontend-first → plan §1 Step 1-3 before Step 4-5 |
| F4 | Clarification answers reflected in plan | ✅ | Q7 (no backward compat) → no migration code; Q8 (db-version.json) → T12; Q12 (FTS5) → T2, T20 |
| F5 | Research schema matches plan contracts | ✅ | Research §5 5-table schema = plan §4 output contract |
| F6 | Risk mitigations have corresponding tasks | ✅ | RK-1 → T10 Web Worker; RK-2 → T4 early catch; RK-3 → T30+T34; RK-4 → phased steps; RK-5 → T8 verify |
| F7 | Task dependencies form a DAG (no cycles) | ✅ | Verified: T1→T2→T4→T8→T10→T11→T15→T28→T38→T46→T47 |
| F8 | Governance RC-1 (daily generator) has explicit tasks | ✅ | T30 (update generator) + T34 (integration test) |
| F9 | All 41 impacted files from analysis mapped to tasks | ✅ | See §5 coverage map |
| F10 | Documentation plan files mapped to tasks | ✅ | D1→T47, D2→T48, D3→T49, D4→T50, D5→T51, D6→T53, D7→T52, D8→T54, D9-D13→T55 |

---

## 3. Ripple-Effects Analysis

| ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|----|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | `config/puzzle-levels.json` — numeric level IDs | Low | IDs already exist, DB schema uses them | T1 | ✅ addressed |
| RE-2 | upstream | `config/tags.json` — numeric tag IDs | Low | IDs already exist, DB schema uses them | T1 | ✅ addressed |
| RE-3 | upstream | `config/collections.json` — numeric collection IDs | Low | IDs already exist, DB schema uses them | T1 | ✅ addressed |
| RE-4 | downstream | Frontend `configService.ts` — currently loads config JSONs for ID decode | Medium | `puzzleQueryService.ts` handles decode; `configService` may become lighter or removed | T16 | ✅ addressed |
| RE-5 | downstream | Frontend `entryDecoder.ts` — current array-of-arrays decoder | Medium | Replaced by direct SQL row mapping | T16 | ✅ addressed |
| RE-6 | downstream | Frontend service worker (PWA cache) — currently caches shard JSON | Medium | Cache strategy changes to single .db file + db-version.json; scoped into T10 per governance RC-1 | T10 | ✅ addressed |
| RE-7 | downstream | GitHub Actions CI — currently publishes shard directories | Medium | CI must produce .db files instead of shard dirs; absorbed into T33 scope per governance | T33 | ✅ addressed |
| RE-8 | lateral | `tools/puzzle-enrichment-lab/` — self-contained, no shard imports | None | No change needed | — | ✅ addressed |
| RE-9 | lateral | `tools/collections_align.py` — reads collection config | Low | No shard dependency; unaffected | — | ✅ addressed |
| RE-10 | downstream | `backend/puzzle_manager/core/naming.py` — batch/hash path construction | Low | Still needed for SGF file paths; DB stores same `batch/hash` in `p` column | — | ✅ addressed |
| RE-11 | downstream | Daily challenge JSON format (v2.2) — reads from published data | Medium | T30 switches source from shards to DB-1 | T30, T34 | ✅ addressed |
| RE-12 | upstream | `yengo-puzzle-collections/sgf/` — raw SGF files remain unchanged | None | SGF distribution unchanged; DB is an index over them | — | ✅ addressed |
| RE-13 | downstream | `cleanup.py` — currently cleans snapshot directories | Medium | Must clean old .db files instead | T31 | ✅ addressed |
| RE-14 | lateral | `.pm-runtime/state/` — pipeline state tracking | Low | No shard state refs; run state tracks stage completion | — | ✅ addressed |

### Unresolved Ripple Effects

All ripple effects resolved after governance RC-1 through RC-3.

---

## 4. Unmapped Tasks Check

| Source | Item | Mapped? | Task |
|--------|------|---------|------|
| Charter G1 | DB-1 for frontend | ✅ | T1-T2, T28 |
| Charter G2 | DB-2 for backend | ✅ | T3, T35-T36 |
| Charter G3 | FTS5 collection search | ✅ | T2, T20 |
| Charter G4 | Frontend sql.js | ✅ | T8-T27 |
| Charter G5 | Daily generator | ✅ | T30, T34 |
| Charter G6 | Shard decommission | ✅ | T38-T46 |
| Charter G7 | Dedup detection | ✅ | T36-T37 |
| Charter G8 | Documentation | ✅ | T47-T56 |
| Charter G9 | Size target | ✅ | Verified in research |
| User: .gitignore | DB files in .gitignore | ✅ | T45 |
| User: reimagine architecture | update | ✅ | T47 |
| Governance RC-1 | Daily generator scope | ✅ | T30, T34 |

**Unmapped items**: None.

---

## 5. File Coverage Map (41 files → tasks)

### Backend Files (22 affected)

| File | Action | Task |
|------|--------|------|
| `core/db_models.py` | NEW | T1 |
| `core/db_builder.py` | NEW | T2 |
| `core/content_db.py` | NEW | T3 |
| `core/shard_writer.py` | DELETE | T38 |
| `core/shard_models.py` | DELETE | T39 |
| `core/snapshot_builder.py` | DELETE | T40 |
| `core/shard_key.py` | REPURPOSE/DELETE | T41 |
| `stages/publish.py` | MODIFY | T28, T35 |
| `stages/protocol.py` | MODIFY | T29 |
| `stages/ingest.py` | MODIFY | T36 |
| `daily/generator.py` | MODIFY | T30 |
| `pipeline/cleanup.py` | MODIFY | T31 |
| `cli.py` | MODIFY | T32 |
| `tests/unit/test_db_models.py` | NEW | T5 |
| `tests/unit/test_db_builder.py` | NEW | T6 |
| `tests/unit/test_content_db.py` | NEW | T7 |
| `tests/unit/test_shard_writer.py` | DELETE | T42 |
| `tests/unit/test_shard_models.py` | DELETE | T42 |
| `tests/unit/test_shard_labels.py` | DELETE | T42 |
| `tests/unit/test_shard_writer_n_assignment.py` | DELETE | T42 |
| `tests/integration/test_snapshot_builder.py` | DELETE | T42 |
| `tests/integration/test_publish_snapshot_wiring.py` | DELETE | T42 |

### Frontend Files (14 affected)

| File | Action | Task |
|------|--------|------|
| `services/sqliteService.ts` | NEW | T10 |
| `services/puzzleQueryService.ts` | NEW | T11 |
| `services/snapshotService.ts` | DELETE | T21 |
| `services/shardPageLoader.ts` | DELETE | T22 |
| `services/queryPlanner.ts` | DELETE | T23 |
| `services/puzzleLoaders.ts` | MODIFY | T15 |
| `services/entryDecoder.ts` | MODIFY | T16 |
| `lib/shards/shard-key.ts` | REPURPOSE/DELETE | T24 |
| `pages/TrainingSelectionPage.tsx` | MODIFY | T17 |
| `app.tsx` | MODIFY | T18 |
| `components/puzzle/FilterBar.tsx` | MODIFY | T19 |
| `components/puzzle/FilterDropdown.tsx` | MODIFY | T19 |
| Tests (new: 4 files) | NEW | T13, T14, T25, T26, T27 |

### Config/Collections (3 affected)

| File | Action | Task |
|------|--------|------|
| `yengo-puzzle-collections/db-version.json` | NEW | T12 |
| `yengo-puzzle-collections/active-snapshot.json` | DELETE | T44 |
| `yengo-puzzle-collections/snapshots/` | DELETE | T44 |

### Documentation (13 affected)

(All mapped to T47-T56, see plan §6 for file-level detail.)

### Tools (1 affected)

| File | Action | Task |
|------|--------|------|
| `backend/puzzle_manager/scripts/seed_sample_db.py` | NEW | T4 |

---

## 6. Severity Findings

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| SF-1 | Info | 56 total tasks is large but well-sequenced with 7 steps | Executor should batch per-step PRs |
| SF-2 | Low | RE-6 (service worker) and RE-7 (CI) identified as unresolved ripple effects | Add sub-tasks or expand T10/T33 scope |
| SF-3 | Info | Research confidence 92 and risk low — no blockers for execution | Proceed with handoff |
| SF-4 | Low | `configService.ts` may need cleanup after DB migration (RE-4) | Executor should assess during Step 3 |

---

> **See also**:
> - [Plan](./30-plan.md) — Architecture, contracts, test plan
> - [Tasks](./40-tasks.md) — Dependency-ordered checklist
> - [Charter](./00-charter.md) — Goals and acceptance criteria
