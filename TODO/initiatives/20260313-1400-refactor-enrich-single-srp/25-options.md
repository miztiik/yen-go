# Options: enrich_single.py SRP Refactor

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Last Updated:** 2026-03-13

---

## Stage Boundary Data (from research)

| Group | Lines | ~Count | Key extraction blocker |
|-------|-------|--------|----------------------|
| IMPORTS | 1–139 | 139 | Dual try/except pattern |
| RESULT_ASSEMBLY | 141–270 | 130 | None — pure functions |
| AI_SOLVE (3 paths) | 276–720 | 445 | Already param-injected |
| ORCHESTRATOR_SETUP (Steps 1-2) | 729–939 | 211 | Contains closure `_notify()` |
| QUERY_ANALYSIS (Steps 3-4) | 940–1085 | 146 | Reads `position`, `config`, `engine_manager` |
| VALIDATION (Steps 5-5.5) | 1086–1245 | 160 | Reads `response`, `correct_move_gtp`, `tags` |
| REFUTATIONS (Step 6) | 1246–1392 | 147 | Reads validation result, position, response |
| DIFFICULTY (Step 7) | 1393–1452 | 60 | Reads validation, refutation, solution_moves |
| ASSEMBLY (Step 8) | 1453–1600 | 148 | Reads everything upstream |
| TEACHING (Step 9) | 1601–1662 | 62 | Reads assembled result |
| SGF_OUTPUT (Step 10) | 1663–1726 | 64 | Reads assembled result + sgf_text |

**Cross-cutting:** 14 `_notify()` calls, 9 `timings[]` assignments scattered across all groups.

---

## Option OPT-1: Stage Runner Pattern (Recommended)

### Approach

Introduce a `PipelineContext` dataclass and a `StageRunner` that auto-wraps stages with notify/timing/error-handling. Each concern group becomes a stage function receiving and returning typed context.

### New File Structure

```
analyzers/
├── stages/
│   ├── __init__.py
│   ├── protocols.py          # Stage protocol + PipelineContext + StageResult
│   ├── stage_runner.py       # Auto-wrapping runner (notify, timing, error policy)
│   ├── parse_stage.py        # Steps 1-2: parse SGF, extract metadata/solution
│   ├── solve_paths.py        # AI-Solve: position-only, has-solution, standard paths
│   ├── query_stage.py        # Steps 3-4: build query, run analysis, uncrop
│   ├── validation_stage.py   # Steps 5-5a-5.5: validate move, tree validation, curated wrongs
│   ├── refutation_stage.py   # Step 6: generate refutations with escalation
│   ├── difficulty_stage.py   # Step 7: estimate difficulty
│   ├── assembly_stage.py     # Step 8: assemble AiAnalysisResult, AC level, goal inference
│   └── teaching_stage.py     # Steps 9-10: technique tags, comments, hints, SGF output
├── result_builders.py         # Extracted: _build_refutation_entries, _build_difficulty_snapshot, etc.
├── enrich_single.py           # Thin orchestrator (~120-150 lines): init → dispatch stages
└── (existing modules unchanged)
```

### Design Details

**`protocols.py`** (~80 lines):
```python
@dataclass
class PipelineContext:
    """Immutable + mutable state flowing through the pipeline."""
    # Immutable session context
    sgf_text: str
    config: EnrichmentConfig
    engine_manager: SingleEngineManager
    source_file: str
    run_id: str
    trace_id: str
    config_hash: str
    # Mutable pipeline state (populated by stages)
    root: Any = None
    metadata: dict = field(default_factory=dict)
    position: Any = None
    state: EnrichmentRunState = field(default_factory=EnrichmentRunState)
    # Stage outputs (typed, not dict)
    correct_move_gtp: str | None = None
    correct_move_sgf: str | None = None
    solution_moves: list[str] = field(default_factory=list)
    response: AnalysisResponse | None = None
    validation_result: CorrectMoveResult | None = None
    refutation_result: RefutationResult | None = None
    difficulty_estimate: DifficultyEstimate | None = None
    result: AiAnalysisResult | None = None

class ErrorPolicy(Enum):
    FAIL_FAST = "fail_fast"      # Return error result immediately
    DEGRADE = "degrade"          # Log warning, continue with defaults

@runtime_checkable
class EnrichmentStage(Protocol):
    """Single enrichment stage protocol."""
    name: str
    error_policy: ErrorPolicy
    async def run(self, ctx: PipelineContext) -> PipelineContext: ...
```

**`stage_runner.py`** (~60 lines):
```python
class StageRunner:
    """Executes stages with automatic notify/timing/error wrapping."""
    async def run_stage(self, stage, ctx, notify_fn, timings):
        timings_key = stage.name
        t_start = time.monotonic()
        await notify_fn(stage.name, {"puzzle_id": ctx.metadata.get("puzzle_id", "")})
        try:
            ctx = await stage.run(ctx)
        except Exception as e:
            if stage.error_policy == ErrorPolicy.FAIL_FAST:
                return ctx, _make_error_result(...)
            else:
                logger.warning("Stage %s degraded: %s", stage.name, e)
        timings[timings_key] = time.monotonic() - t_start
        return ctx, None
```

**`enrich_single.py`** (~120-150 lines): Init config/trace → parse stage → solve-path dispatch → run remaining stages via `StageRunner` → return result.

### Benefits
- **SRP:** Each stage module has exactly one reason to change
- **DRY:** `_notify`/timing/error logic written once in runner, not 14× inline
- **Testable by design:** Each stage is a pure function `PipelineContext → PipelineContext`
- **Protocol-ready:** `EnrichmentStage` protocol matches backend's pattern — backend can implement same protocol
- **Timing anomalies fixed:** Each stage gets its own timing key automatically

### Drawbacks
- Introduces new abstraction (`PipelineContext`) — team must learn it
- `PipelineContext` is a large dataclass (~20 fields) — risk of becoming a "God object"
- More files to navigate (12 new files vs 1 current)

### Risks & Mitigations
| Risk | Probability | Mitigation |
|------|------------|------------|
| PipelineContext becomes God object | Medium | Strict field ownership: each stage documents which fields it reads/writes |
| Inter-stage coupling through context | Low | Protocol enforces typed fields, not arbitrary dict |
| Test breakage from signature change | Low | Q1:B allows it; update test call-sites mechanically |

### SOLID/DRY/KISS/YAGNI Assessment
- **S (SRP):** ✅ Each module = one concern
- **O (Open/Closed):** ✅ New stages can be added without modifying runner
- **L (Liskov):** ✅ All stages substitutable via protocol
- **I (Interface Segregation):** ✅ Single focused protocol
- **D (Dependency Inversion):** ✅ Orchestrator depends on protocol, not concretions
- **DRY:** ✅ Notify/timing/error written once
- **KISS:** ⚠️ Slightly more complex than OPT-2 (runner abstraction layer)
- **YAGNI:** ✅ Protocol mirrors backend pattern (not speculative — intended for merger)

### Migration/Rollback
- **Migration:** Incremental — extract one stage at a time, run tests after each
- **Rollback:** Git branch; each extraction is a separate commit

---

## Option OPT-2: Flat Module Extraction (Simpler)

### Approach

Extract each concern group into a standalone async function in its own module. No runner abstraction — the orchestrator calls each function directly with explicit parameters. Notify/timing remain in the orchestrator.

### New File Structure

```
analyzers/
├── stages/
│   ├── __init__.py
│   ├── protocols.py          # Protocol ABCs only (for future backend integration)
│   ├── parse_stage.py        # Steps 1-2
│   ├── solve_paths.py        # AI-Solve paths (already extracted as functions)
│   ├── query_stage.py        # Steps 3-4
│   ├── validation_stage.py   # Steps 5-5.5
│   ├── refutation_stage.py   # Step 6
│   ├── difficulty_stage.py   # Step 7
│   ├── assembly_stage.py     # Step 8
│   └── teaching_stage.py     # Steps 9-10
├── result_builders.py         # Pure helper functions
├── enrich_single.py           # Orchestrator (~250-300 lines): init → call each stage function
└── (existing modules unchanged)
```

### Design Details

Each stage module exports a single async function:
```python
# validation_stage.py
async def run_validation(
    response: AnalysisResponse,
    correct_move_gtp: str,
    tags: list[int],
    corner: str,
    move_order: str,
    root,
    position,
    solution_moves: list[str],
    engine_manager: SingleEngineManager,
    config: EnrichmentConfig,
    puzzle_id: str,
    ko_type: str,
) -> tuple[CorrectMoveResult, list[dict], list[str] | None]:
    ...
```

Orchestrator calls each function explicitly:
```python
# enrich_single.py (~250-300 lines)
async def enrich_single_puzzle(...):
    # Step 1-2
    await _notify("parse_sgf", ...)
    t_start = time.monotonic()
    parse_result = await run_parse(sgf_text, source_file)
    timings["parse"] = time.monotonic() - t_start
    # ... etc for each stage
```

### Benefits
- **KISS:** No new abstractions — just function calls
- **SRP:** Each module still has one concern
- **Easy to understand:** Direct function calls, explicit parameters
- **Low risk:** Minimal conceptual overhead

### Drawbacks
- **NOT DRY:** Notify/timing boilerplate repeated 8× in orchestrator (~80 lines of boilerplate)
- **Long parameter lists:** Each function needs 5-12 explicit parameters (no context object)
- **Not protocol-ready:** Functions have bespoke signatures — backend can't easily implement a shared interface
- **Orchestrator still ~250-300 lines:** Larger than OPT-1 due to repeated boilerplate

### Risks & Mitigations
| Risk | Probability | Mitigation |
|------|------------|------------|
| Parameter list explosion | High | Group related params into small dataclasses per-stage |
| Boilerplate drift | Medium | Accept it as cost of simplicity |
| Future backend integration harder | Medium | Protocol ABCs exist but don't map to function signatures |

### SOLID/DRY/KISS/YAGNI Assessment
- **S (SRP):** ✅ Each module = one concern
- **O (Open/Closed):** ⚠️ Adding stages requires modifying orchestrator
- **L (Liskov):** N/A — no polymorphism
- **I (Interface Segregation):** N/A
- **D (Dependency Inversion):** ❌ Orchestrator depends directly on concrete functions
- **DRY:** ❌ Notify/timing repeated 8×
- **KISS:** ✅ Simplest possible approach
- **YAGNI:** ✅ No speculative abstractions

### Migration/Rollback
- Same as OPT-1 (incremental, git branch)

---

## Option OPT-3: Hybrid — Typed Context + Direct Calls (No Runner)

### Approach

Introduce `PipelineContext` (like OPT-1) but NO runner abstraction. The orchestrator calls stage functions with the context object directly. Notify/timing stay in orchestrator but are much shorter because they don't pass 12 parameters.

### New File Structure

Same as OPT-1 but without `stage_runner.py`.

### Design Details

```python
# Each stage is a simple function, not a class
async def run_validation(ctx: PipelineContext) -> PipelineContext: ...

# Orchestrator (~180-220 lines)
async def enrich_single_puzzle(...):
    ctx = PipelineContext(sgf_text=sgf_text, ...)
    
    await _notify("parse_sgf", ...)
    t = time.monotonic()
    ctx = await run_parse(ctx)
    timings["parse"] = time.monotonic() - t
    
    await _notify("validation", ...)
    t = time.monotonic()
    ctx = await run_validation(ctx)
    timings["validation"] = time.monotonic() - t
    ...
```

### Benefits
- **Typed context:** Eliminates parameter explosion (single `ctx` arg)
- **No runner overhead:** Direct calls are transparent
- **Protocol-close:** Functions taking/returning `PipelineContext` are close to a formal protocol
- **Moderate DRY:** Notify/timing still repeated but each is only 3 lines not 8

### Drawbacks
- **Partial DRY:** 3 lines × 8 stages = 24 lines of boilerplate (vs 0 in OPT-1, vs 80 in OPT-2)
- **PipelineContext still a large dataclass** (same risk as OPT-1)
- **No automatic error wrapping** — each stage must handle errors or orchestrator must wrap each call

### SOLID/DRY/KISS/YAGNI Assessment
- **S (SRP):** ✅ Each module = one concern
- **O (Open/Closed):** ⚠️ Modifying orchestrator to add stages (same as OPT-2)
- **D (Dependency Inversion):** ⚠️ Partial — context is shared, but no protocol enforcement
- **DRY:** ⚠️ Moderate — 24 lines boilerplate vs 0 (OPT-1) vs 80 (OPT-2)
- **KISS:** ✅ Simpler than OPT-1, slightly more complex than OPT-2
- **YAGNI:** ✅ Context is needed regardless; no speculative runner

### Migration/Rollback
- Same as OPT-1/2 (incremental, git branch)

---

## Comparison Matrix

| Dimension | OPT-1 (Stage Runner) | OPT-2 (Flat Functions) | OPT-3 (Hybrid) |
|-----------|----------------------|------------------------|-----------------|
| **Orchestrator size** | ~120-150 lines | ~250-300 lines | ~180-220 lines |
| **New files** | 12 | 11 | 11 |
| **DRY (notify/timing)** | ✅ Zero boilerplate | ❌ 80 lines repeated | ⚠️ 24 lines repeated |
| **SRP** | ✅ Best | ✅ Good | ✅ Good |
| **KISS** | ⚠️ Runner abstraction | ✅ Simplest | ✅ Simple |
| **Protocol-ready** | ✅ Full protocol | ❌ Bespoke signatures | ⚠️ Close but informal |
| **Backend merger readiness** | ✅ Best | ❌ Weakest | ⚠️ Moderate |
| **Error policy** | ✅ Declarative | ❌ Manual | ❌ Manual |
| **Risk** | Medium | Low | Low |
| **Complexity** | Higher (new patterns) | Lowest | Moderate |

## Recommendation

**OPT-1 (Stage Runner Pattern)** — Best SOLID compliance, best DRY, best backend merger readiness. The runner abstraction is a proven pattern (backend already uses `StageExecutor`). The slightly higher conceptual overhead is justified by the merger intent and the 14× notify + 9× timing elimination.

If the team values simplicity over protocol-readiness, **OPT-3 (Hybrid)** is a good compromise.
