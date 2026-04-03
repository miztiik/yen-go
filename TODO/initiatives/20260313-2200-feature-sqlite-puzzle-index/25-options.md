# Options — SQLite Puzzle Index

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`

---

## Context

The technology choice (sql.js, full download, all-numeric schema) is settled from research and user decisions. The options below address the **implementation strategy** — specifically, how to sequence the work across backend, frontend, and shard deletion given the clean-break constraint.

---

## Option Comparison

| Criterion | OPT-1: Schema-First (Frontend-Led) | OPT-2: Pipeline-First (Backend-Led) | OPT-3: Big-Bang (Simultaneous) |
|-----------|-------------------------------------|--------------------------------------|-------------------------------|
| **Approach** | Design schema → build frontend sql.js integration → seed DB with sample data → validate UX → then wire backend pipeline | Design schema → build backend DB generator → generate real DB from existing SGFs → then wire frontend | Design schema → build both backend + frontend in parallel → integrate → delete shards all at once |
| **First deliverable** | Working frontend with sample DB | Real DB from pipeline | Everything at once |
| **Shard deletion timing** | After frontend proven with real DB | After frontend wired | All at once |
| **Risk profile** | Low — frontend proven before backend changes | Low — real data validates schema early | High — large blast radius, hard to debug |
| **Testability** | Frontend unit tests with sample DB; backend tests independent | Backend tests validate DB content; frontend tests later | All tests must pass simultaneously |
| **Feedback loop** | Fast — sample DB in minutes, UX visible immediately | Medium — need pipeline run to see data | Slow — everything must work before anything works |
| **Daily generator** | Migrated in backend phase | Migrated alongside pipeline | Migrated in parallel |
| **Shard code alive during** | Frontend phase (backend still generates shards) | Frontend phase (shards exist but DB is primary) | Never — deleted immediately |
| **Parallel work possible** | ✅ Frontend dev independent of backend | ⚠️ Frontend blocked until DB exists | ✅ If two developers, otherwise no |
| **Complexity** | Low | Low | High |
| **Total effort** | ~8-10 tasks | ~8-10 tasks | ~8-10 tasks (same work, worse sequencing) |

---

## OPT-1: Schema-First (Frontend-Led)

### Summary
Start with the SQL schema and a Python script that generates a sample DB from a handful of existing SGF files. Wire the frontend to sql.js immediately. Validate all browse/filter/search patterns work in the browser with real puzzle data (just a subset). Then build the full backend pipeline integration and daily generator migration. Delete shards last.

### Execution Sequence
1. **Schema + sample DB seed** — Python script reads ~100 SGFs → generates `yengo-search.db`. No pipeline integration yet.
2. **Frontend sql.js integration** — Add sql.js, create `sqliteService.ts`, `puzzleQueryService.ts`. Replaces shard fetching.
3. **Frontend page updates** — Update all loaders, collections page FTS5, filter components.
4. **Backend pipeline integration** — Wire `db_builder.py` into publish stage. Daily generator migration.
5. **DB-2 content/dedup** — Backend-only. `content_db.py` with position hash.
6. **Shard deletion** — Remove all shard code/files/tests.
7. **Docs + Holy Law** — Documentation overhaul.

### Benefits
- Frontend UX can be validated in hours, not days
- Schema issues caught early (before full pipeline wire-up)
- Sample DB can be committed for frontend development/testing
- Frontend and backend work can be parallelized after step 1

### Drawbacks
- Sample DB is a temporary artifact (replaced by pipeline-generated DB)
- Short period where shards still exist alongside DB

---

## OPT-2: Pipeline-First (Backend-Led)

### Summary
Build the DB generator directly in the publish pipeline. Run a full publish to generate the real DB from all 9,059 SGFs. Then wire the frontend to consume it. Delete shards last.

### Execution Sequence
1. **Schema + db_builder.py** — Integrated into publish stage from the start.
2. **Run full publish** — Generate `yengo-search.db` with all 9K puzzles.
3. **DB-2 content/dedup** — Build alongside DB-1.
4. **Daily generator migration** — Migrate `daily/generator.py` to read from DB-1.
5. **Frontend sql.js integration** — Wire frontend against real DB.
6. **Shard deletion** — Remove all shard code/files/tests.
7. **Docs + Holy Law** — Documentation overhaul.

### Benefits
- Real DB from day one — no sample/subset artifacts
- Schema validated against full corpus immediately
- Backend team can work independently first

### Drawbacks
- Frontend blocked until backend produces DB (steps 1-4 sequential)
- Full publish required before any frontend development
- Schema mistakes discovered later (during frontend integration)

---

## OPT-3: Big-Bang (Simultaneous)

### Summary
Build everything at once: schema, backend, frontend, delete shards. Single large PR.

### Benefits
- One PR, one review cycle
- No transitional state

### Drawbacks
- Largest blast radius — if anything breaks, hard to isolate
- Cannot demo progress incrementally
- All tests must pass simultaneously
- Highest risk of merge conflicts if other work is in progress

---

## Recommendation

**OPT-1 (Schema-First / Frontend-Led)** is recommended.

| Criterion | Winner |
|-----------|--------|
| Fastest to first visible result | OPT-1 |
| Lowest risk | OPT-1 = OPT-2 |
| Best feedback loop | OPT-1 |
| Parallel work enablement | OPT-1 |
| Real data fidelity | OPT-2 |
| Simplest execution | OPT-3 (but highest risk) |

The user's original request confirms this preference: *"once the SQL design and the frontend is ready, we can ingest sample data and see everything is working. Then we can start ingesting through the pipeline."*

---

> **See also**:
> - [Charter](./00-charter.md) — Goals, non-goals, acceptance criteria
> - [Research](../20260313-research-sqlite-puzzle-index/15-research.md) — Full SQL schema, size estimates, governance opinions
