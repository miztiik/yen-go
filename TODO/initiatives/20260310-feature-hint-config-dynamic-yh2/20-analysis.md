# Analysis — Config-Driven YH1 + Dynamic YH2 Reasoning

**Initiative ID:** 20260310-feature-hint-config-dynamic-yh2  
**Last Updated:** 2026-03-10

---

## Planning Metadata

| Field | Value |
|-------|-------|
| `planning_confidence_score` | 90 |
| `risk_level` | low |
| `research_invoked` | No (internal change, well-understood) |

---

## 1. Charter ↔ Implementation Coverage

| Charter Item | Implemented | Evidence |
|---|---|---|
| Config-driven YH1 | ✅ | `_load_teaching_comments()` reads `config/teaching-comments.json`, `_try_tag_hint()` and `_try_solution_aware_hint()` prefer config |
| Dynamic YH2 depth | ✅ | `generate_reasoning_hint()` appends depth when ≥ 2 |
| Dynamic YH2 refutations | ✅ | `_count_refutations()` + singular/plural formatting |
| Dynamic YH2 secondary tag | ✅ | `_get_secondary_tag()` + "Also consider" with config-driven name |
| All 28 tags produce hints | ✅ | Fallback to `TECHNIQUE_HINTS` if config entry missing |
| Backward compatibility | ✅ | `generate_yh2` alias unchanged; existing tests pass |
| Documentation | ✅ | `docs/concepts/hints.md` updated |

---

## 2. Ripple Effects

| impact_id | direction | area | risk | mitigation | status |
|-----------|-----------|------|------|------------|--------|
| RE-1 | upstream | config/teaching-comments.json | Read-only dependency. No changes to config file. | Graceful fallback if missing | ✅ addressed |
| RE-2 | downstream | enrichment/__init__.py | enrich_puzzle calls HintGenerator unchanged | No interface changes | ✅ addressed |
| RE-3 | lateral | frontend | YH format unchanged (string in YH property) | No frontend changes needed | ✅ addressed |
| RE-4 | lateral | publish stage | GN/YH property format unchanged | No publish changes needed | ✅ addressed |

---

## 3. Findings

| finding_id | severity | description |
|------------|----------|-------------|
| F1 | HIGH | D-1: `test_reasoning_includes_secondary_tag` missing `has_solution=True` — **FIXED** |
| F2 | MEDIUM | D-2: `test_reasoning_no_secondary_for_single_tag` missing `has_solution=True` — **FIXED** |
| F3 | INFO | Module-level `_teaching_comments_cache` never reset between tests. Acceptable since all tests read same config file. |
| F4 | INFO | 14 new tests cover: config-driven YH1 (3), dynamic YH2 (7), helpers (4) |
