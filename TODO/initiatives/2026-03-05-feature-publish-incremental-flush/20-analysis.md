# Analysis — Publish Stage Incremental Flush & Logging

> Last Updated: 2026-03-05

## Read-Only Consistency & Coverage Pass

### 1. Charter ↔ Clarifications Consistency

| Charter Goal             | Clarification Support       | Status     |
| ------------------------ | --------------------------- | ---------- |
| G1: Dual-level logging   | Q2: every 100 files         | ✅ Aligned |
| G2: Incremental snapshot | Q4: every 100, even if slow | ✅ Aligned |
| G3: Flush publish log    | Q3: yes, all 5 problems     | ✅ Aligned |
| G4: Wire flush_interval  | Q3: yes, all 5 problems     | ✅ Aligned |
| G5: Remove old behavior  | Q1: no backward compat      | ✅ Aligned |

### 2. Plan ↔ Charter Acceptance Criteria Coverage

| Acceptance Criterion                               | Plan Coverage                   | Task        |
| -------------------------------------------------- | ------------------------------- | ----------- |
| `trace_logger.info` → DETAIL per-file              | Plan §Conceptual Diff           | T1          |
| `logger.info("[publish] %d/%d")` every 100         | Plan §Conceptual Diff           | T2          |
| Snapshot rebuilt every 100 files                   | Plan §Conceptual Diff           | T4          |
| Publish log flushed every 100 files                | Plan §Conceptual Diff           | T4          |
| `BatchState.save()` every 100 files                | Plan §Conceptual Diff           | T4          |
| Existing tests updated                             | Plan §Files Changed             | T7, T9      |
| New test: crash at 150 preserves 100               | Plan §Risks                     | T8          |
| No `trace_logger.info("Published puzzle")` at INFO | Plan §Conceptual Diff           | T1          |
| `flush_interval` addressed                         | Plan §flush_interval Resolution | T9, comment |

All criteria covered. ✅

### 3. Task Graph ↔ Plan Consistency

| Plan Section                 | Tasks Covering It | Status |
| ---------------------------- | ----------------- | ------ |
| Per-file log level fix       | T1                | ✅     |
| Streaming progress           | T2                | ✅     |
| Pending buffer refactor      | T3                | ✅     |
| Periodic 100-file flush      | T4                | ✅     |
| Remove post-loop all-at-once | T5                | ✅     |
| DRY helper extraction        | T6                | ✅     |
| Existing test fixes          | T7                | ✅     |
| New tests                    | T8                | ✅     |
| flush_interval cleanup       | T9                | ✅     |
| Full validation              | T10               | ✅     |

### 4. Findings

#### Severity: Warning

**W1: SnapshotBuilder instantiated per flush**

T4/T5 instantiate `SnapshotBuilder` at each 100-file boundary. While correct (each call gets fresh state), this means `load_existing_entries()` reads the just-written snapshot — which includes entries from the current run's previous flushes. This is the intended incremental behavior, but should be documented in a code comment to avoid confusion about "why are we loading entries we just wrote?"

**Recommendation**: Add a brief comment at the flush call site explaining the incremental pattern.

#### Severity: Info

**I1: Pending log entries need careful buffer management**

`pending_log_entries` is cleared at each 100-file boundary. If we also keep `publish_log_entries` as a full-run list (for any post-run reporting), we'd have two lists. The plan in T3 correctly identifies using just `pending_log_entries` as the only buffer — no full-run list needed since entries are on disk.

**I2: Test file count implications**

Most existing tests use 3-5 files, which is well below the 100-file threshold. This means periodic flushes won't trigger in existing tests — only the end-of-loop remainder flush fires. The new T8 tests with 250 files specifically validate the periodic behavior.

**I3: `_create_valid_sgf` position uniqueness**

The test helper `_create_valid_sgf` generates unique SGF content via board position variations. With 250 files for T8 tests, we need 250 unique positions. The current helper uses `4 rows × 3 col-groups = 12 unique positions`. This is insufficient for 250 files — content hashes will collide, causing dedup skips. The helper needs to be extended.

**Recommendation**: T8 must extend `_create_valid_sgf` to support 250+ unique positions (e.g., add a comment line with the index to ensure unique content hashes).

#### Severity: Info

**I4: DRY extracion (T6) could be merged into T4/T5**

T6 extracts a helper that T4 and T5 both use. This could be done as part of T4/T5 directly rather than as a separate task. The executor may choose to combine these.

### 5. Coverage Map

| Source File          | Changed            | Test File                                                              | Tests                                       |
| -------------------- | ------------------ | ---------------------------------------------------------------------- | ------------------------------------------- |
| publish.py L214      | Log level fix      | test_publish_robustness.py `test_duplicate_skip_is_detail_level`       | Existing ✅                                 |
| publish.py L311-320  | Log level fix      | test_publish_robustness.py `test_per_file_log_is_detail_level`         | Existing ✅                                 |
| publish.py loop      | Streaming progress | —                                                                      | No dedicated test (matches sibling pattern) |
| publish.py loop      | Periodic flush     | test_publish_robustness.py `test_incremental_snapshot_every_100`       | New T8 ✅                                   |
| publish.py post-loop | Remove all-at-once | test_publish_robustness.py `test_publish_log_entries_written_per_file` | Existing (still works) ✅                   |
| publish.py post-loop | Remainder flush    | test_publish_robustness.py `test_crash_at_150_preserves_first_100`     | New T8 ✅                                   |

### 6. Unmapped Tasks

None. All tasks map to charter goals.

### 7. Risk Assessment

| Risk                           | Finding                                   | Severity                 |
| ------------------------------ | ----------------------------------------- | ------------------------ |
| Test helper position limit     | I3: 250 files exceeds 12 unique positions | Warning — must fix in T8 |
| SnapshotBuilder per-flush cost | W1: intentional, documented               | Info                     |
| Existing tests with <100 files | I2: only remainder flush tested           | Acceptable               |
