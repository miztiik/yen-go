# Clarifications: Remove Dormant Dedup Infrastructure

**Last Updated:** 2026-03-05

## Clarification Questions & Answers

### Q1: Is backward compatibility required, and should old code be removed?

**Answer:** No backward compatibility required. Old code should be removed.

**Rationale:** User stated:

- "It's just an identifier. Not necessary."
- "Duplicates are OK because people are going to filter by levels and techniques"
- "Rewriting the user local storage is not a problem"
- "When we republish, more or less the slices get lost as well"
- "Daily publish is supposed to be daily publish"

### Q2: Should the `fp` field in YM metadata be preserved for existing published SGFs?

**Answer:** No. The `fp` field is an optional JSON field that was never populated in production (the fingerprint was never computed at runtime). Removing the parsing support is safe — `parse_pipeline_meta_extended()` will simply ignore unknown JSON keys.

### Q3: Does rollback/republish/rebuild depend on dedup infrastructure?

**Answer:** No. Verified by grep: `rollback.py` has zero references to dedup, fingerprint, or registry. Rollback operates via publish-log entries and filesystem operations only.

### Q4: Should adapter-internal dedup tracking be removed?

**Answer:** No. Comments like "Track processed IDs for deduplication" in `local/adapter.py` and `daily/standard.py` are about adapter-level ID tracking — legitimate operational logic, not the fingerprint infrastructure.

### Q5: What about TODO/ planning documents that reference fingerprint/dedup?

**Answer:** Leave as-is. These are historical planning artifacts (`puzzle-quality-strategy/`, `puzzle-quality-scorer/`). They document decisions made and are not active code.
