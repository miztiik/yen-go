# Clarifications: enrich_single.py SRP Refactor

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Last Updated:** 2026-03-13

---

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Is backward compatibility required?** Should the public API of `enrich_single_puzzle()` remain identical (same signature + return type), or can we change it? | A: Keep exact signature / B: Allow new signature if tests updated / C: Other | B — Internal tool, no external consumers. Updating test call-sites is trivial and enables cleaner interface. | **B** — Allow new signature, update tests | ✅ resolved |
| Q2 | **Should old `enrich_single.py` be removed or kept as a facade?** After decomposition, should the original file remain as a thin re-export that delegates to the new modules, or be deleted entirely? | A: Delete entirely, update all imports / B: Keep as thin facade for backward compat / C: Other | A — Dead code policy says delete don't deprecate. Git preserves history. | **A** — Delete entirely | ✅ resolved |
| Q3 | **DRY strategy for lab↔backend overlapping modules** (property_policy, region, ko, move_order). The lab must NOT import from backend. Options: | A: Extract shared protocols to a new `tools/core/` shared package / B: Keep parallel implementations but align on same JSON config contract / C: Lab modules define Protocol ABCs that backend can later implement / D: Other | C — Lightest touch. Lab defines the Protocol, backend implements later. No shared package needed. Avoids coupling. | **C (modified)** — User initially wanted to import from `backend/core/`, but **research proved infeasible** (see 15-research.md): `core/__init__.py` eagerly imports `httpx`/`tenacity`/`filelock`, and project rule prohibits tools→backend imports. User directive: "IF THIS IS NOT POSSIBLE, KEEP MODULES MODULAR WITHIN LAB." → **Lab defines Protocol ABCs + keeps parallel implementations aligned on shared JSON config.** | ✅ resolved |
| Q4 | **Where should extracted stage modules live?** The decomposed stages need a home within the lab. | A: `analyzers/stages/` sub-package (new directory) / B: `analyzers/` flat (prefix convention, e.g. `stage_validate.py`) / C: New top-level `stages/` package in lab root / D: Other | A — `analyzers/stages/` groups related files, matches backend's `stages/` pattern, keeps `analyzers/` from growing unmanageable. | **A** — `analyzers/stages/` sub-package | ✅ resolved |
| Q5 | **What granularity for stage extraction?** Each numbered step in enrich_single could become its own module, or we could group related steps. | A: One module per numbered step (10 modules) / B: Group by concern (~5-6 modules: parse, ai_solve, validate+refutations, difficulty, teaching, sgf_output) / C: Other | B — Steps 5+5a+5.5+6 are tightly coupled (validation+refutations). Steps 9+10 are tightly coupled (teaching+SGF). Grouping by concern reduces inter-module chatter. | **B** — Group by concern (SRP + DRY) | ✅ resolved |
| Q6 | **Should the Protocol/ABC interfaces be in a separate `protocols.py` file or distributed?** | A: Single `protocols.py` with all stage protocols / B: Each stage module defines its own protocol / C: Separate `protocols/` package / D: Other | A — Single file is discoverable. Backend integration team reads one file to understand the contract. Matches backend's `stages/protocol.py` pattern. | **A** — Single `protocols.py` | ✅ resolved |
| Q7 | **Telemetry/observability extraction scope.** The `_notify()` callbacks and `timings{}` dict are woven throughout. Should the stage runner handle these automatically, or should stages opt-in? | A: Stage runner automatically wraps with notify+timing (stages are unaware) / B: Stages receive a context with notify/timing helpers but call them explicitly / C: Other | A — Eliminates ~40% of boilerplate. Stages become pure business logic. Runner pattern proven in backend's `StageExecutor`. | **A** — Automatic wrapping by runner | ✅ resolved |
| Q8 | **Error policy formalization.** Currently mixed: some stages fail-fast (return error result), others degrade (log warning + continue). Should this be explicit? | A: Each stage declares its error policy (fail_fast vs degrade) in its protocol / B: Orchestrator has a hardcoded error policy table / C: Config-driven error policy / D: Other | A — Stage-declared policy is self-documenting and testable. Avoids hidden coupling between orchestrator and stage internals. | **A** — Stage-declared policy | ✅ resolved |
| Q9 | **Test strategy for the refactor.** The lab has ~65 test files. How should we ensure zero regression? | A: Characterization tests first (snapshot current outputs), then refactor / B: Rely on existing test suite (already comprehensive) / C: Both — add integration snapshot test, then refactor / D: Other | B — Existing test suite is comprehensive (1,251+ tests in backend, 65 test files in lab). The refactor is internal restructuring with no behavior change. | **B** — Rely on existing suite | ✅ resolved |

## Mandatory Pre-Planning Question

> **Q1 resolved: B.** Signature can change, tests will be updated. Enables clean interface redesign.

## Q3 Research Outcome

User initially requested importing from `backend/puzzle_manager/core/`. Feature-Researcher investigation (see `15-research.md`) found this is **not feasible**:
1. `backend/puzzle_manager/core/__init__.py` eagerly imports `httpx`, `tenacity`, `filelock` — importing any `core.*` submodule triggers the full load chain.
2. Project architecture rule: "tools/ must NOT import from backend/" (`CLAUDE.md`, `analyzers/property_policy.py` header).
3. User directive: "IF THIS IS NOT POSSIBLE, KEEP MODULES MODULAR WITHIN LAB."

**Resolution:** Lab keeps parallel implementations, aligned on shared JSON config (`config/sgf-property-policies.json`, `config/tags.json`, etc.). Lab defines Protocol ABCs that the backend can implement when merger happens. The merger path is through future `core/__init__.py` lazy-import refactoring (separate initiative).
