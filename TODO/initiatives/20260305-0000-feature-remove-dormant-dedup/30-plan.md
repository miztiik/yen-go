# Plan: Remove Dormant Dedup Infrastructure

**Last Updated:** 2026-03-05

## Decision

**Remove all dormant position-fingerprint dedup infrastructure.** Governance panel unanimous 6/6 approve.

## Architecture Impact

### What's removed

1. **Position fingerprint module** (`core/position_fingerprint.py`) — D4 dihedral group transforms, canonical representation, SHA256 fingerprint computation. ~155 lines. Zero production callers.

2. **Dedup registry module** (`core/dedup_registry.py`) — Persistent JSON registry mapping fingerprint → entry with quality-based winner selection. ~260 lines. Zero production callers.

3. **Fingerprint field in pipeline metadata** — `fp` sub-field in YM property, `fingerprint` parameter in `build_pipeline_meta()`, `fingerprint` field in `PipelineMeta` dataclass. Never populated in production.

4. **Dedup-registry.json cleanup** — `cleanup.py` block that deletes the registry file. File is never created in production.

5. **Associated tests** — 3 test files testing the dormant modules, fingerprint-related assertions in 2 additional test files.

### What stays (unchanged)

- `generate_content_hash()` — content-addressable filename generation. Active production code.
- `output_path.exists()` check — same-run idempotency. Active. Log message renamed to clarify purpose.
- Adapter-internal dedup tracking — legitimate operational logic.
- Tag/collection "sorted, deduplicated" operations — standard list processing.

### Data model impact

The `YM` property sub-field `fp` is removed from the schema policy description. Since `fp` was never populated in production SGFs, no existing published files are affected. The `parse_pipeline_meta_extended()` function will silently ignore any `fp` field in old SGFs (standard JSON behavior — unknown keys are ignored by the parser because it uses `data.get("fp", "")` which defaults gracefully).

## Risks & Mitigations

| Risk                  | Mitigation                                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------------------- |
| Hidden callers missed | Terminal grep verification (T015)                                                                          |
| Test breakage         | pytest run (T014)                                                                                          |
| Future need for dedup | Git history preserves code; at 500K+ scale, JSON registry wouldn't work anyway — would need proper storage |

> **See also:**
>
> - [Charter](00-charter.md) — Goals, non-goals, acceptance criteria
> - [Tasks](40-tasks.md) — Execution checklist
> - [Analysis](20-analysis.md) — Blast radius and coverage map
