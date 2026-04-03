# Clarifications — config.py Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Resolution Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Backward compat — re-export facade or rewrite all imports? | A) Facade / B) Rewrite all / C) Other | A (lower risk) | **B — "Just make it clean — we don't need bandages"** | ✅ resolved |
| Q2 | Delete old config.py or keep as shim? | A) Delete, replace with package / B) Keep shim / C) Other | A | **A — "Deleting old code is fine. But we still need a config.py to load configs."** Resolved: `config/__init__.py` provides loader functions. | ✅ resolved |
| Q3 | Replace global cache pattern? | A) `lru_cache` / B) `ConfigRegistry` / C) Leave as-is | C | **C — Leave as-is.** User confirmed: converting to package doesn't force caching refactor. Orthogonal concern. | ✅ resolved |
| Q4 | Move business logic (get_effective_max_visits, get_level_category) out of config? | A) Move to analyzers / B) Keep in config/helpers.py / C) Leave as-is | B | **B** | ✅ resolved |
| Q5 | How many sub-modules? | A) 6-7 fine-grained / B) 3-4 coarse / C) Other | A | **"Do what is right, consult governance — no limit."** Deferred to options + governance election. | ✅ resolved |
| Q6 | Update tests in same initiative? | A) Same PR / B) Follow-up / C) Other | A | **A — Required by Q1=B (rewrite).** All 30+ test files updated atomically. | ✅ resolved |

## Key Decisions Captured

1. **No backward compatibility shim.** All `from config import X` imports across 100+ sites will be rewritten.
2. **Monolith `config.py` deleted.** Replaced with `config/` package. `config/__init__.py` exposes loader functions.
3. **Global cache pattern preserved.** Decomposed into respective sub-modules but not redesigned.
4. **Business logic isolated** in `config/helpers.py`, not moved to analyzers.
5. **Sub-module granularity** deferred to options phase.
6. **Tests updated atomically** within this initiative.
