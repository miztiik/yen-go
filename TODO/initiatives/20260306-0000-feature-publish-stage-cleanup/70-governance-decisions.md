# Governance Decisions — Publish Stage Cleanup

> Last Updated: 2026-03-06

## Options Election — 2026-03-06

**Decision:** approve  
**Status Code:** GOV-OPTIONS-APPROVED  
**Unanimous:** Yes (6/6)

### Selected Option

- **Option ID:** A
- **Title:** Snapshot-at-End with Lightweight Periodic Flush
- **Rationale:** Maximum performance (~20x speedup) with minimum complexity (removes code). Correctly decouples durability (log flush) from query (snapshot build). KISS/YAGNI compliant. Within Level 3 scope.

### Must-Hold Constraints

1. Periodic flush (every 100 files): ONLY publish log + batch state — no snapshot
2. Snapshot built exactly ONCE after main loop completes
3. trace_id extracted from YM via `parse_pipeline_meta()` — no trace registry
4. `source_file`/`original_filename` removed from PublishLogEntry (deleted, not deprecated)
5. `f` field stripped from YM JSON before writing published SGF
6. `write_audit_entry` called at end of successful publish

### Member Votes

| Member           | Domain              | Vote    |
| ---------------- | ------------------- | ------- |
| Cho Chikun (9p)  | Tsumego authority   | approve |
| Lee Sedol (9p)   | Fighting GO         | approve |
| Shin Jinseo (9p) | AI-era professional | approve |
| Ke Jie (9p)      | Strategic thinking  | approve |
| Staff Engineer A | Systems architect   | approve |
| Staff Engineer B | Pipeline engineer   | approve |

### Rejected Options

- **Option B (Tiered Flush):** YAGNI — tiered scheduling adds complexity for unused mid-run snapshots
- **Option C (Incremental Snapshots):** Violates charter Level 3 constraint; over-engineering for batch pipeline

---

## Plan Review — 2026-03-06

**Decision:** approve  
**Status Code:** GOV-PLAN-APPROVED  
**Unanimous:** Yes (6/6)

### Verification Summary

- All 6 charter goals mapped to tasks: confirmed
- All 6 must-hold constraints traceable: confirmed
- Level 3 file scope verified: 2 core + 3-4 test files
- No CRITICAL/HIGH analysis findings
- No blocking ambiguities
- Rollback: single commit revert, no data migration
- Test plan covers all behavioral changes + negative cases

### Member Votes

| Member           | Domain              | Vote    | Comment                                                                       |
| ---------------- | ------------------- | ------- | ----------------------------------------------------------------------------- |
| Cho Chikun (9p)  | Tsumego authority   | approve | Clean removal of dead code, canonical published representation                |
| Lee Sedol (9p)   | Fighting GO         | approve | Direct approach, crash-recovery model sound; YAGNI correct                    |
| Shin Jinseo (9p) | AI-era professional | approve | parse_pipeline_meta extraction is strictly superior; 20x speedup well-founded |
| Ke Jie (9p)      | Strategic thinking  | approve | Structural clarity improvement; task dependency graph well-ordered            |
| Staff Engineer A | Systems architect   | approve | No new abstractions; Level 3 confirmed; backward compat explicitly waived     |
| Staff Engineer B | Pipeline engineer   | approve | Performance claim validated; batch state durability preserved on crash        |

### Handover (Governance → Executor)

| Field              | Value                                                                                                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **from_agent**     | Governance-Panel                                                                                                                                                                                         |
| **to_agent**       | Plan-Executor                                                                                                                                                                                            |
| **decision**       | approve                                                                                                                                                                                                  |
| **status_code**    | GOV-PLAN-APPROVED                                                                                                                                                                                        |
| **message**        | Execute tasks T01-T09 in dependency order per `40-tasks.md`. T01+T02 parallel, T08+T09 parallel. All 6 must-hold constraints must be verified. Run `pytest -m "not (cli or slow)"` after implementation. |
| **blocking_items** | (none)                                                                                                                                                                                                   |

---

## Implementation Review — 2026-03-06

**Decision:** approve  
**Status Code:** GOV-REVIEW-APPROVED  
**Unanimous:** Yes (6/6)

### Verification Summary

- All 6 must-hold constraints independently verified via code reads and grep
- 0 dangling references to removed code (trace registry, dead fields, `_flush_incremental`)
- No scope drift — 2 production files + 2 test files, matching plan
- Test evidence: 11 new + 4 updated tests pass; full suite 2051 pass, 2 pre-existing failures
- No new abstractions, dependencies, or config changes

### Member Votes

| Member           | Domain              | Vote    | Comment                                                                 |
| ---------------- | ------------------- | ------- | ----------------------------------------------------------------------- |
| Cho Chikun (9p)  | Tsumego authority   | approve | Clean published SGF representation, deterministic build preserved       |
| Lee Sedol (9p)   | Fighting GO         | approve | Direct approach, crash-recovery sound, YAGNI correct                    |
| Shin Jinseo (9p) | AI-era professional | approve | parse_pipeline_meta strictly superior, ~20x speedup well-founded        |
| Ke Jie (9p)      | Strategic thinking  | approve | Structural clarity improved, responsibilities clarified                 |
| Staff Engineer A | Systems architect   | approve | No new abstractions, Level 3 scope respected, defensive coding correct  |
| Staff Engineer B | Pipeline engineer   | approve | Batch flow correct, crash-recovery model sound, observability preserved |

### Handover (Governance → Executor)

| Field              | Value                                                                                                            |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **from_agent**     | Governance-Panel                                                                                                 |
| **to_agent**       | Plan-Executor                                                                                                    |
| **decision**       | approve                                                                                                          |
| **status_code**    | GOV-REVIEW-APPROVED                                                                                              |
| **message**        | Proceed to closeout. Update status.json and finalize. 2 pre-existing test failures should be tracked separately. |
| **blocking_items** | (none)                                                                                                           |
