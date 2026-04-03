# Analysis — Externalize TECHNIQUE_REGISTRY (OPT-1)

Last Updated: 2026-03-22

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 75 → 85 (post-clarification) |
| Risk Level | low |
| Research Invoked | No |
| Rationale | All clarifications resolved. Format decided (JSON). Scope well-bounded. Existing test suite provides strong regression coverage. |

## Consistency Checks

| finding_id | severity | category | finding | resolution |
|------------|----------|----------|---------|------------|
| F1 | LOW | terminology | Charter says "8 existing tests" but plan says "3 unit + 5 parametrized". Both correct — 3 unit + 5 parametrized = 8 test methods total. | Consistent. No action. |
| F2 | LOW | coverage | T10 (legacy removal) overlaps with T4 (replace dict with loader). In practice, T4 deletes the dict when replacing with loader. T10 is a verification step. | Clarified in tasks notes. T10 is a verification gate, not a separate edit. |
| F3 | MEDIUM | ordering | T6 (regen script) depends on T1 (JSON file) and is marked [P] with T3. But T6 also needs to know the JSON schema structure. Must confirm T1 defines the schema before T6 starts. | T1 creates the full JSON structure. T6 reads that structure. Dependency is correctly modeled. |
| F4 | LOW | completeness | No explicit test for JSON file loadability. GV-4 recommended a "structural validation test". | Covered by existing `test_all_tags_have_registry_entry()` which iterates TECHNIQUE_REGISTRY — if JSON fails to load, this test crashes at import time. Additional test is advisory, not required. |
| F5 | LOW | constitution | Project guidelines say "Every feature change must include tests." This refactor doesn't add new tests but existing tests provide full coverage. | No new behavior added — existing tests are the coverage. Consistent with "updated tests for modified code" requirement. |

## Coverage Map

| goal_id | Goal | Covered by Task(s) | Status |
|---------|------|--------------------|--------|
| G-1 | Externalize data | T1, T2, T3, T4, T10 | ✅ covered |
| G-2 | Maintain test compatibility | T5, T11 | ✅ covered |
| G-3 | Enable independent data updates | T1 (JSON file is editable independently) | ✅ covered |
| G-4 | Enable regeneration | T6, T7, T8 | ✅ covered |
| G-5 | Improve git history clarity | T1, T4 (data in JSON, logic in .py) | ✅ covered |

## Unmapped Tasks

None — all tasks trace to goals.

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | `test_technique_calibration.py` imports | Low — only internal test file imports change | `_load_registry()` returns identical dict type | T3, T4 | ✅ addressed |
| RE-2 | lateral | `test_fixture_coverage.py` | None — has its own `ALL_TAG_FIXTURES` list, completely independent | No changes needed | — | ✅ addressed |
| RE-3 | lateral | `test_golden5.py` | None — has its own `GOLDEN5_PUZZLES` dict, different scope | No changes needed | — | ✅ addressed |
| RE-4 | lateral | `conftest.py` | None — provides MockEngineManager, not calibration data | No changes needed | — | ✅ addressed |
| RE-5 | upstream | `config/tags.json` | None — read-only SSOT, not modified | Existing `test_all_tags_have_registry_entry()` validates sync | T5 | ✅ addressed |
| RE-6 | lateral | `AGENTS.md` | Low — needs update for new files | Explicit task T9 | T9 | ✅ addressed |
| RE-7 | lateral | Git workflows / CI | None — JSON file is just another file tracked by git | No CI changes needed | — | ✅ addressed |
| RE-8 | downstream | pytest test discovery | Low — if JSON fails to load, `TECHNIQUE_REGISTRY` won't exist → all 8 tests fail at collection time with clear error | Loader includes descriptive error message | T3 | ✅ addressed |
| RE-9 | lateral | `scripts/` directory | None — regen script is additive, doesn't modify existing scripts | Self-contained, no imports from other scripts | T6 | ✅ addressed |

## Constitution/Project Guideline Compliance

| check_id | Guideline | Compliance | Notes |
|----------|-----------|------------|-------|
| CC-1 | YAGNI | ✅ | Regen script requested by user (Q5:A), not speculative. No JSON Schema. No TOML. |
| CC-2 | KISS | ✅ | Loader is ~15 lines. JSON is standard. No custom parsing library. |
| CC-3 | DRY | ✅ | Single source of calibration truth (JSON). TypedDict defines structure once. |
| CC-4 | SRP | ✅ | Test file tests. JSON holds data. Script regenerates. |
| CC-5 | Tests required | ✅ | Existing 8 tests provide full coverage. No new behavior = no new tests required. |
| CC-6 | Docs required | ✅ | AGENTS.md update (T9). JSON self-documents with metadata header. |
| CC-7 | Config-driven | ✅ | Calibration data moves to data file, similar to config/*.json pattern. |
| CC-8 | No backend imports | ✅ | Script uses `enrich_single_puzzle()` from enrichment lab, not backend/. |
| CC-9 | Git safety | ✅ | No git stash, no reset --hard, no destructive operations. Selective staging. |
| CC-10 | 3-tier docs pattern | ✅ | No user-facing docs changes needed (internal test infrastructure). AGENTS.md is agent-facing. |
