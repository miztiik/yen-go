# Analysis — Publish Stage Cleanup (Option A)

> Last Updated: 2026-03-06

## Planning Confidence

- **Score:** 78/100
- **Risk Level:** medium
- **Research invoked:** No (sufficient internal codebase evidence)

## File Impact Analysis

| File                                | Change Type    | Lines Changed (est.) | Risk   |
| ----------------------------------- | -------------- | -------------------- | ------ |
| `stages/publish.py`                 | Major refactor | ~80 lines            | Medium |
| `models/publish_log.py`             | Field removal  | ~15 lines            | Low    |
| `tests/unit/test_publish_log.py`    | Update         | ~20 lines            | Low    |
| `tests/*/test_publish*.py`          | Update         | ~40 lines            | Medium |
| `tests/unit/test_strip_ym.py` (new) | New file       | ~40 lines            | Low    |

**Total:** 2 core files + 3-4 test files = **Level 3** (within charter constraint)

## Coverage Map

| Charter Goal              | Tasks                   | Files                                        |
| ------------------------- | ----------------------- | -------------------------------------------- |
| G1: Remove dead fields    | T01, T07                | `models/publish_log.py`, `stages/publish.py` |
| G2: Strip YM `f`          | T03                     | `stages/publish.py`                          |
| G3: Decouple snapshot     | T04, T05                | `stages/publish.py`                          |
| G4: Remove trace registry | T02                     | `stages/publish.py`                          |
| G5: Inventory at end      | (existing, T05 context) | `stages/publish.py`                          |
| G6: Audit entry           | T06                     | `stages/publish.py`                          |

## Findings

### Severity: CRITICAL — None

### Severity: HIGH — None

### Severity: MEDIUM

1. **YM `f` stripping changes content hash**: When `_strip_ym_filename` removes `f` from YM and the SGF is re-serialized, `generate_content_hash(content)` produces a DIFFERENT hash than if `f` were still present. This means re-publishing the same source puzzle will get a new `puzzle_id` and filename. **Mitigation:** This is intentional behavior — published SGFs should not contain source filenames. Existing files with `f` remain valid but won't deduplicate with the new hash-without-`f` output.

2. **trace_id population changes behavior**: Currently all publish log entries have `trace_id: ""`. After this change, they'll have the actual trace_id from YM. Any scripts or queries that filter on `trace_id == ""` would behave differently. **Mitigation:** No backward compatibility required. The correct behavior is to populate trace_id.

### Severity: LOW

3. **Periodic flush label change**: Currently logs say "Snapshot flush (periodic@100)". After removing snapshot from periodic, the label should NOT mention "snapshot". **Covered in T04** — rename to `_flush_periodic` and update log messages.

4. **trace_logger creation timing**: Currently `create_trace_logger` is called before the try block using trace_id from trace registry. After T02, trace_id is extracted inside the try block after `parse_sgf()`. The logger creation must move after extraction. If `parse_sgf()` fails, trace_id won't be available for the error log. **Mitigation:** Use the base `logger` for errors when trace_id isn't available.

## Unmapped Tasks

None — all charter goals have corresponding tasks.

## Consistency Check

| Artifact Pair                 | Consistent?                                              |
| ----------------------------- | -------------------------------------------------------- |
| Charter ↔ Clarifications      | ✅ All 6 goals traceable to clarification answers        |
| Charter ↔ Options             | ✅ Option A addresses all 6 goals                        |
| Charter ↔ Plan                | ✅ Plan addresses all 6 goals with specific code changes |
| Plan ↔ Tasks                  | ✅ All plan changes have corresponding tasks             |
| Tasks ↔ Tests (T08/T09)       | ✅ Test tasks cover all behavioral changes               |
| Must-hold constraints ↔ Tasks | ✅ All 6 constraints mapped to tasks                     |
