# Options: enrich_single.py SRP Decomposition

**Last Updated:** 2026-03-07  
**Planning Confidence Score:** 72 (post-research)  
**Risk Level:** Medium

---

## SRP Violations Found (from research)

The orchestrator function has **18 distinct responsibilities** (see 15-research.md Appendix A). Currently:

- Config lookup is duplicated across 4 files (DRY violation)
- 9 mutable tracking variables couple AI-Solve paths to result assembly with no data contract
- The orchestrator is 1,085 lines doing: parsing, routing, 3 AI-Solve paths, querying, validating, refuting, scoring, assembling, goal-inferring, teaching, and timing
- `_uncrop_response` lives in the orchestrator file but belongs with the cropping concern

---

## Option Comparison

| ID                          | OPT-1: Layered SRP Extraction                                                                                                                                                                                                                  | OPT-2: Pipeline Stage Protocol                                                                                                                                                                                         | OPT-3: Minimal State Carrier Only                                                                                                                    |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**                | 4-phase extraction: (1) shared `config_lookup.py`, (2) `EnrichmentRunState` dataclass, (3) extract 3 AI-Solve code paths as private async functions, (4) move `_uncrop_response` to `query_builder.py`. Orchestrator becomes ~200-line router. | Port backend's `StageRunner` protocol to async: `AsyncStageRunner(Protocol)` with `run(ctx) → StageResult`. Each step (parse, validate, refute, score, teach) becomes a stage class. `StageContext` carries all state. | Only introduce `EnrichmentRunState` and `config_lookup.py`. No code-path extraction. Orchestrator stays monolithic but with explicit state contract. |
| **New files**               | 1 new (`config_lookup.py`), 0 new for code paths (stay in `enrich_single.py`)                                                                                                                                                                  | 3+ new (protocol, stage classes, async executor)                                                                                                                                                                       | 1 new (`config_lookup.py`)                                                                                                                           |
| **Files modified**          | 6 (enrich_single, query_builder, estimate_difficulty, sgf_enricher, validate_correct_move, test_enrich_single)                                                                                                                                 | 8+ (all above + new stage files + cli caller changes)                                                                                                                                                                  | 4 (enrich_single, estimate_difficulty, sgf_enricher, validate_correct_move)                                                                          |
| **Orchestrator size after** | ~200 lines (dispatch + sequential awaits)                                                                                                                                                                                                      | ~80 lines (stage executor loop)                                                                                                                                                                                        | ~1,085 lines (unchanged structure)                                                                                                                   |
| **SRP compliance**          | **Full** — each function has one responsibility, config is centralized, code paths isolated                                                                                                                                                    | **Full** — each stage is a named class with single `run()`                                                                                                                                                             | **Partial** — config DRY fixed, state contract explicit, but orchestrator still does everything inline                                               |
| **SOLID score**             | S:✅ O:✅ L:n/a I:✅ D:✅                                                                                                                                                                                                                      | S:✅ O:✅ L:✅ I:✅ D:✅                                                                                                                                                                                               | S:⚠️ O:✅ L:n/a I:✅ D:✅                                                                                                                            |
| **DRY**                     | ✅ Config consolidated across 4 files                                                                                                                                                                                                          | ✅ Config consolidated + stage contracts formalized                                                                                                                                                                    | ✅ Config consolidated only                                                                                                                          |
| **KISS**                    | ✅ No new abstractions beyond a dataclass                                                                                                                                                                                                      | ⚠️ Introduces Protocol, StageResult, AsyncStageRunner, StageExecutor — 4 new abstractions                                                                                                                              | ✅ Minimal change                                                                                                                                    |
| **YAGNI**                   | ✅ Solves exactly the stated problem                                                                                                                                                                                                           | ⚠️ Stage protocol adds extensibility not yet needed (no planned new stages)                                                                                                                                            | ⚠️ Doesn't solve the core complaint (orchestrator too big)                                                                                           |
| **Migration risk**          | Medium — test import updates, 4-file config consolidation                                                                                                                                                                                      | High — async protocol is novel pattern in lab, every test that patches must be updated                                                                                                                                 | Low — no structural changes                                                                                                                          |
| **Rollback**                | Per-phase: each of 4 phases is independently revertible                                                                                                                                                                                        | All-or-nothing: protocol adoption is cross-cutting                                                                                                                                                                     | Trivial: 2 commits to revert                                                                                                                         |
| **Independent iteration**   | ✅ Config, metadata, each code path, result assembly, teaching — all independently editable                                                                                                                                                    | ✅ Each stage independently editable                                                                                                                                                                                   | ❌ Still one monolith                                                                                                                                |
| **Test impact**             | 2 test classes need import update + fixture target change                                                                                                                                                                                      | All test classes need refactoring (stage-based test structure)                                                                                                                                                         | 0 test changes needed                                                                                                                                |

---

## Detailed Option Descriptions

### OPT-1: Layered SRP Extraction (Recommended)

**Phase 1 — `config_lookup.py` (DRY fix, independent)**

- Create `analyzers/config_lookup.py` with: `load_tag_slug_map()`, `load_tag_id_to_name()`, `load_level_id_map()`, `resolve_tag_names()`, `resolve_level_info()`, `parse_tag_ids()`, `clear_config_caches()`
- Update 4 consumer files to import from it
- Update test imports + `autouse` fixture to reset via `clear_config_caches()`

**Phase 2 — `EnrichmentRunState` dataclass (state contract)**

- Add dataclass to `models/` or top of `enrich_single.py` with 11 fields (9 tracking vars + `correct_move_gtp` + `solution_moves`)
- Include `notify_fn: Callable | None` to carry progress callback
- Replace 9 bare local variables with state object mutations

**Phase 3 — Extract code paths (SRP for orchestrator)**

- `_run_position_only_path(state, root, position, ...) → EnrichmentRunState`
- `_run_has_solution_path(state, root, position, ...) → EnrichmentRunState`
- `_run_standard_path(state, ...) → EnrichmentRunState`
- Orchestrator becomes: parse → route to path → query → validate → refute → score → assemble → teach

**Phase 4 — Move `_uncrop_response` (cohesion fix)**

- Move to `query_builder.py` as `uncrop_response()` (public, since orchestrator imports it)
- `query_builder` now owns full crop lifecycle: crop + uncrop

**Benefits:**

- Each phase is independently deployable and testable
- No new abstractions beyond a simple dataclass
- Follows established project patterns (dataclass carriers)
- Orchestrator drops from 1,085 to ~200 lines

**Risks:**

- 4-file config consolidation may surface subtle differences in cache behavior
- `_notify` closure must be threaded through state carrier
- Partial failure in AI-Solve paths must set state correctly and fall through

---

### OPT-2: Pipeline Stage Protocol

**Approach:** Adopt the backend's `StageRunner` pattern as an async variant.

Each enrichment step becomes a class:

```python
class ParseStage(AsyncStageRunner):
    async def run(self, ctx: EnrichmentContext) -> StageResult: ...

class AiSolveStage(AsyncStageRunner):
    async def run(self, ctx: EnrichmentContext) -> StageResult: ...
```

**Benefits:**

- Maximum formalization — each stage is named, testable, composable
- Could enable future stage-level retry, metrics, conditional skipping
- Consistent with backend architecture

**Risks:**

- YAGNI: no planned new stages, no stage-level retry needed
- Async protocol is a new pattern in the lab codebase
- Requires rewriting all integration tests
- 3-4 new files minimum
- Backend stages are synchronous; async variant is untested in this repo

---

### OPT-3: Minimal State Carrier Only

**Approach:** Only create `config_lookup.py` + `EnrichmentRunState`. No code-path extraction. The orchestrator keeps its current structure but with explicit state and deduplicated config.

**Benefits:**

- Lowest risk — smallest diff
- Fixes DRY violation
- Makes state flow visible

**Risks:**

- Doesn't address the core complaint: "orchestrator is doing too much"
- No improvement in independent iteration capability for code paths
- Still 1,085 lines in one function

---

## Recommendation

**OPT-1 (Layered SRP Extraction)** — it directly addresses every user concern:

1. "Too much in one file" → 4-phase extraction reduces orchestrator to ~200 lines
2. "Each module should be SRP compliant" → each extracted function has one responsibility
3. "Independent iteration" → config, metadata, each code path, result assembly independently editable
4. "Not namesake decomposition" → driven by responsibility analysis, not naming

OPT-2 is over-engineered for the problem (YAGNI). OPT-3 doesn't solve the problem.

> **See also:**
>
> - [Research](./15-research.md) — SRP audit, state dependency graph, sibling inventory
> - [Clarifications](./10-clarifications.md) — Locked decisions
> - [Charter](./00-charter.md) — Scope and constraints
