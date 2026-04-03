# Clarifications: model_paths.py Decomposition

**Initiative**: 20260325-refactor-model-paths-decomposition
**Date**: 2026-03-24

---

## Clarification Round 1

| q_id | question | options | recommended | user_response | status |
|---|---|---|---|---|---|
| Q1 | Is backward compatibility required? Should `model_paths.py` remain as a re-export shim or be deleted entirely? | A: Keep shim permanently / B: Keep shim temporarily, delete in Phase 2 / C: Delete immediately, update all 20+ importers in one go | B — temporary shim reduces blast radius | **B** — Keep temporarily, delete after everything is tested working | ✅ resolved |
| Q2 | Should old code be removed? (the stale `tests/_model_paths.py` and eventually the re-export shim) | A: Yes, remove all legacy / B: Keep shim indefinitely | A — dead code policy says "delete, don't deprecate" | **A** — Remove all dead code | ✅ resolved |
| Q3 | Should Phase 0 (lazy import fix) be shipped as a standalone commit before the full decomposition? | A: Yes, ship independently / B: Bundle with Phase 1 | A — Phase 0 is a 1-line fix with zero risk; can be merged immediately | **Bundle** — Do all phases as needed, no artificial separation | ✅ resolved |
| Q4 | Where should TEST_* defaults live after decomposition? | A: `tests/conftest.py` as module constants / B: New `tests/test_defaults.py` module / C: Keep in config/infrastructure.py only (access via config object) | A — conftest already imports them and provides fixtures; centralizing there follows pytest conventions | **A** — conftest.py | ✅ resolved |
| Q5 | Should we update all 20+ import sites to use direct imports (`from config.helpers import model_path`) as part of this initiative, or defer that to a separate cleanup? | A: Update all imports now / B: Defer to Phase 2 (separate PR) | B — the shim handles backward compat; updating 20 files is mechanical and can be batched later | **A** — Update all now. Full decomposition, NOT a facade. | ✅ resolved |

## Additional Direction (from user)

- **Approach**: CR-Beta decomposition (NOT CR-Alpha facade). model_paths.py is the temporary shim during development only, deleted once verified.
- **Confidence target**: Plan must achieve ≥ 90-95% confidence before execution.
- **All phases executed**: No artificial phase separation — do everything required in this initiative.
