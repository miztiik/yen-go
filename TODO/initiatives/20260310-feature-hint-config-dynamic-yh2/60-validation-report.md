# Validation Report — Config-Driven YH1 + Dynamic YH2 Reasoning

**Initiative ID:** 20260310-feature-hint-config-dynamic-yh2  
**Last Updated:** 2026-03-10

---

## Test Execution Results

### Backend Pipeline Tests (In-Scope)

| VAL-1 | Command | Result |
|-------|---------|--------|
| VAL-1a | `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no` | **2065 passed, 44 deselected, 25 warnings in 82.68s** ✅ |
| VAL-1b | `pytest backend/puzzle_manager/tests/unit/test_enrichment.py -q --no-header --tb=no` | **226 passed in 0.40s** ✅ |

### Enrichment-Specific Feature Tests

| VAL-2 | Test | Result |
|-------|------|--------|
| VAL-2a | Config loading (happy path) | ✅ passed |
| VAL-2b | Config fallback (missing config) | ✅ passed |
| VAL-2c | Config-driven hint text (3 tag samples) | ✅ passed |
| VAL-2d | All 28 tags produce hints | ✅ passed |
| VAL-2e | Depth context (≥2) | ✅ passed |
| VAL-2f | Refutation count (>0) | ✅ passed |
| VAL-2g | Secondary tag context | ✅ passed |
| VAL-2h | No secondary for single tag | ✅ passed |
| VAL-2i | Refutation count helper | ✅ passed |
| VAL-2j | Secondary tag helper | ✅ passed |
| VAL-2k | R5 atari suppression (life-and-death) | ✅ passed |
| VAL-2l | R5 player atari suppression | ✅ passed |

### Out-of-Scope Failures (tools/ directory)

| VAL-3 | Test | Assessment |
|-------|------|------------|
| VAL-3a | `tools/core/tests/test_sgf_builder.py::test_invalid_board_size` | Pre-existing — not in backend pipeline |
| VAL-3b | `tools/puzzle-enrichment-lab/tests/` (13 tests) | Pre-existing — separate toolset, not modified by this initiative |

**Verdict**: All 14 tool failures are pre-existing and unrelated to hint config/dynamic YH2 changes. Zero backend pipeline regressions.

---

## Acceptance Criteria Verification

| VAL-4 | Criterion | Status | Evidence |
|-------|-----------|--------|----------|
| VAL-4a | `TECHNIQUE_HINTS` reads `hint_text` from `teaching-comments.json` | ✅ | `_try_tag_hint()` checks config first; 3 sample tests verify "shicho", "geta", "uttegaeshi" in output |
| VAL-4b | YH2 includes solution depth when depth ≥ 2 | ✅ | `test_reasoning_includes_depth_context` passes |
| VAL-4c | YH2 includes refutation count when refutations > 0 | ✅ | `test_reasoning_includes_refutation_count` passes |
| VAL-4d | YH2 includes secondary tag when 2+ tags | ✅ | `test_reasoning_includes_secondary_tag` passes (with `has_solution=True` fix) |
| VAL-4e | All existing tests pass | ✅ | 2065/2065 backend tests pass (0 failures) |
| VAL-4f | New tests cover dynamic reasoning paths | ✅ | 14 new tests added, all passing |
| VAL-4g | Documentation updated | ✅ | `docs/concepts/hints.md` updated with config-driven YH1, dynamic reasoning YH2, date 2026-03-10 |

---

## Ripple-Effects Validation

| VAL-5 | Expected Effect | Observed Effect | Result | Follow-up Task | Status |
|-------|-----------------|-----------------|--------|----------------|--------|
| VAL-5a | YH1 output changes from verbose English to concise Japanese terms | Config returns "Ladder (shicho)" instead of "Look for a ladder (shicho) pattern" | ✅ verified | R5 test assertions updated (T10) | ✅ verified |
| VAL-5b | Existing R5 atari gating preserved | `test_atari_suppressed_when_irrelevant` still passes with updated assertion | ✅ verified | None | ✅ verified |
| VAL-5c | Solution-aware fallback uses config names | `_try_solution_aware_hint()` checks config first | ✅ verified | None | ✅ verified |
| VAL-5d | Secondary tag name in YH2 uses config | `generate_reasoning_hint()` prefers config name for secondary tag | ✅ verified | None | ✅ verified |
| VAL-5e | No impact on YH3 coordinate hints | COORDINATE_TEMPLATES unchanged, separate from TECHNIQUE_HINTS | ✅ verified | None | ✅ verified |

---

## Documentation Verification

| VAL-6 | File | Updated | Evidence |
|-------|------|---------|----------|
| VAL-6a | `docs/concepts/hints.md` | ✅ | YH1 section says "Config-driven", YH2 has "Dynamic reasoning enrichment" subsection, date 2026-03-10 |

> **See also**: [Execution Log](./50-execution-log.md) — [Governance](./70-governance-decisions.md)
