# Analysis: Remove Dormant Dedup Infrastructure

**Last Updated:** 2026-03-05

## Blast Radius Summary

| Category                 | Files  | Severity                              |
| ------------------------ | ------ | ------------------------------------- |
| Delete (dormant modules) | 5      | Safe — zero production imports        |
| Edit (production code)   | 3      | Low — parameter/field removal only    |
| Edit (tests)             | 2      | Low — removing tests for deleted code |
| Edit (config)            | 1      | Low — description text only           |
| Edit (docs)              | 1      | Low — removing phantom log references |
| Edit (log message)       | 1      | Low — text change, no behavior change |
| **Total**                | **13** |                                       |

## Findings

### CRITICAL: Zero Production Imports

`dedup_registry.py` and `position_fingerprint.py` are imported ONLY by unit test files:

- `test_dedup_registry.py`
- `test_dedup_metadata_merge.py`
- `test_position_fingerprint.py`

No production stage (`ingest.py`, `analyze.py`, `publish.py`) imports them. No pipeline module (`coordinator.py`, `cleanup.py`) imports them. The code is fully dormant.

### HIGH: trace_utils.py fingerprint field is passthrough-only

`analyze.py:592` passes `fingerprint=existing.fingerprint` — but since `existing.fingerprint` is always empty (never computed in production), this is a no-op passthrough. Removing it changes nothing.

### MEDIUM: cleanup.py dedup-registry.json handling

`cleanup.py` lines 424-436 attempt to delete `.pm-runtime/state/dedup-registry.json` during collection cleanup. Since the file is never created in production, this block never executes. Removing it is safe.

### LOW: Config policy description

`config/sgf-property-policies.json` line 46 lists `fp(fingerprint)` as a YM sub-field. This is documentation-only — the JSON schema doesn't enforce sub-field presence.

### LOW: Logging docs describe phantom log messages

`docs/architecture/backend/logging.md` documents `Dedup: skipping {file}` as a DETAIL-level publish log message. This message doesn't exist in the current publish.py codebase. It was planned but never implemented.

### SAFE: Rollback has zero dependency

`rollback.py` — grepped for `dedup`, `fingerprint`, `registry` — zero matches. Rollback operates via publish-log entries and filesystem operations only.

## Coverage Map

| Task      | File(s)                        | Covered? |
| --------- | ------------------------------ | -------- |
| T001-T005 | 5 dormant files                | ✅       |
| T006      | trace_utils.py                 | ✅       |
| T007      | analyze.py                     | ✅       |
| T008      | cleanup.py                     | ✅       |
| T009      | test_pipeline_meta_extended.py | ✅       |
| T010      | test_cleanup.py                | ✅       |
| T011      | sgf-property-policies.json     | ✅       |
| T012      | logging.md                     | ✅       |
| T013      | publish.py (log message)       | ✅       |
| T014-T016 | Verification                   | ✅       |

## Unmapped References (intentionally excluded)

| File                            | Reference                                     | Why excluded                          |
| ------------------------------- | --------------------------------------------- | ------------------------------------- |
| `adapters/local/adapter.py:57`  | "Track processed IDs for deduplication"       | Adapter-internal ID tracking, legit   |
| `daily/standard.py:134`         | "Track selected puzzle IDs for deduplication" | Daily selection dedup, legit          |
| `stages/publish.py:518,544,584` | "Dedupe by path"                              | View generation path dedup, legit     |
| `inventory/check.py:81`         | "Track processed paths to deduplicate"        | Inventory dedup, legit                |
| `docs/` various                 | "sorted, deduplicated" for tags/collections   | Tag/collection list operations, legit |
| `TODO/puzzle-quality-strategy/` | Historical planning docs                      | Archive material, not active code     |
| `TODO/puzzle-quality-scorer/`   | Historical planning docs                      | Archive material, not active code     |

## Risk Assessment

| Risk                                            | Likelihood | Impact | Mitigation                                            |
| ----------------------------------------------- | ---------- | ------ | ----------------------------------------------------- |
| Hidden import missed by grep                    | Very Low   | Medium | T015 verification grep catches it                     |
| Test failure from parameter removal             | Low        | Low    | T014 pytest run catches it                            |
| Docs reference stale info                       | Low        | Low    | T012 + T016 verification                              |
| `.pm-runtime/state/dedup-registry.json` on disk | Low        | None   | File is orphaned; harmless. User can manually delete. |
