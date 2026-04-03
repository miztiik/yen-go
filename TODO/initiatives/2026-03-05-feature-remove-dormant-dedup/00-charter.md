# Charter: Remove Dormant Dedup Infrastructure

**Initiative ID:** 2026-03-05-feature-remove-dormant-dedup  
**Type:** Feature (dead code removal)  
**Correction Level:** 3 (Multiple Files)  
**Last Updated:** 2026-03-05

## Goals

1. Remove all dormant position-fingerprint dedup code from the codebase
2. Remove the dormant `DedupRegistry` JSON persistence layer
3. Clean all associated tests, docs, and config references
4. Rename the content-hash idempotency log message to accurately reflect its purpose

## Non-Goals

- Modifying the content-hash naming scheme (`generate_content_hash()` stays)
- Modifying the `output_path.exists()` idempotency check (stays, but relabeled)
- Adding any new dedup infrastructure
- Modifying rollback/republish/rebuild (verified: zero dependency)
- Removing adapter-internal dedup (e.g., `local/adapter.py` tracking processed IDs)
- Removing legitimate "sorted, deduplicated" tag/collection operations

## Constraints

- Must not break any production pipeline stages (ingest, analyze, publish)
- Must not break rollback, inventory, daily challenge generation
- Must not break frontend (zero frontend dedup code references are affected)
- All existing tests (minus deleted dedup tests) must pass after removal

## Acceptance Criteria

1. `grep -r "dedup_registry\|position_fingerprint\|DedupRegistry\|DedupEntry\|DedupResult\|DedupStats" backend/` returns zero matches
2. `grep -r "fp(fingerprint)" config/ docs/` returns zero matches
3. `pytest -m "not (cli or slow)"` passes
4. Publish stage log message says "Skipping already-published" not "Skipping duplicate"
5. `trace_utils.build_pipeline_meta()` no longer accepts `fingerprint` parameter
6. `PipelineMeta` dataclass no longer has `fingerprint` field
7. `cleanup.py` no longer references `dedup-registry.json`

## User Decisions (Recorded)

| Decision                                   | Answer                             | Date       |
| ------------------------------------------ | ---------------------------------- | ---------- |
| Is backward compatibility required?        | **No.** Republish = website reset. | 2026-03-05 |
| Should old code be removed?                | **Yes.** Dead code policy applies. | 2026-03-05 |
| Are duplicates acceptable?                 | **Yes.** Filtering UX handles it.  | 2026-03-05 |
| Is GN identity stability needed?           | **No.** Just an identifier.        | 2026-03-05 |
| Is localStorage data loss on republish OK? | **Yes.**                           | 2026-03-05 |
| Are lost daily challenges on republish OK? | **Yes.** Daily publish is daily.   | 2026-03-05 |

> **See also:**
>
> - [Plan](30-plan.md) — Architecture and design decisions
> - [Tasks](40-tasks.md) — Execution checklist
> - [Governance](70-governance-decisions.md) — Panel verdict
