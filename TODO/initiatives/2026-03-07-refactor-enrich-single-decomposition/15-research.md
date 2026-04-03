# Research Brief: Decomposing `enrich_single.py` via SRP

**Initiative:** 2026-03-07-refactor-enrich-single-decomposition  
**Date:** 2026-03-07  
**Mode:** Feature-Researcher (read-only)

---

## 1. Research Question and Boundaries

**Question:** Which responsibilities inside `enrich_single_puzzle()` have clean extraction boundaries, which are coupled by shared mutable state, and what structural pattern (if any) exists in the codebase to guide stage composition?

**Success criteria:**

- Every distinct responsibility identified with line ranges
- State variable dependency graph reveals minimum data contract for any stage split
- Sibling inventory exposes duplicate config-loading that makes a shared `config_lookup.py` worthwhile
- Pipeline pattern precedent informs whether enrichment stages could follow the same protocol

**Boundaries:** Read-only. No runtime code modified. Analysis covers `tools/puzzle-enrichment-lab/analyzers/` and `backend/puzzle_manager/` only.

---

## 2. Internal Code Evidence

### 2.1 File read — `enrich_single.py`

- **Total lines:** 1,593
- **Helper block:** lines 118–507 (~390 lines, 9 private functions + 4 module-level caches)
- **Orchestrator function `enrich_single_puzzle()`:** lines 508–1,593 (~1,085 lines)
- The function contains an **inner `_notify()` closure** (lines 553–556), re-declared on each call — an immediate SRP smell that belongs in an observability helper.

### 2.2 State variable declaration site

All 9 tracking variables are declared at a single block, lines 620–631:

```python
_has_solution_path = False
_position_only_path = False
_ai_solve_failed = False
_solution_tree_completeness = None
_budget_exhausted = False
_queries_used = 0
_co_correct_detected = False
_human_solution_confidence: str | None = None
_ai_solution_validated = False
```

These are **not** passed between calls — they live only in the orchestrator's local scope and are consumed by the result-assembly block (lines 1,406–1,470). This is the hard coupling that creates the "too coupled" criticism.

### 2.3 Backend pipeline pattern — `protocol.py` + `executor.py`

- `StageRunner` is a `Protocol` with `name`, `run(context) → StageResult`, `validate_prerequisites() → list[str]`.
- `StageContext` is a `@dataclass` (pure data carrier, no logic). All paths derived from two root dirs.
- `StageExecutor` is a separate orchestrator that calls `stage.run(context)` in sequence.
- Pattern: **data-carrier context + stateless stage objects + separate executor** — the reference architecture in this repo.

### 2.4 Sibling config-loading duplication

Three files independently load `puzzle-levels.json`:

- `enrich_single.py` — `_load_level_id_map()` (lines 223–245)
- `estimate_difficulty.py` — `_load_levels_from_config()` (line 47)
- `sgf_enricher.py` — `_load_level_ids()` (line 65)

Two files independently load `tags.json`:

- `enrich_single.py` — `_load_tag_slug_map()` + `_load_tag_id_to_name()` (lines 172–220)
- `validate_correct_move.py` — `_get_tag_consts()` with lazy loader (lines 110–140)

Each implementation uses its own module-level `None`-sentinel cache and a `Path(__file__).resolve().parents[N]` chain with a different depth. This is a DRY violation across 4 files.

---

## 3. External References

| R-ID | Reference                                                                | Relevance                                                                                                                                                            |
| ---- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | Python docs — `dataclasses.dataclass`                                    | `StageContext` pattern; immutable value objects for stage input contracts                                                                                            |
| R-2  | _Clean Architecture_ (Martin) — Use Case Interactor pattern              | Responsibility = "a reason to change"; orchestrators should not know domain logic details                                                                            |
| R-3  | Python `asyncio` docs — `TaskGroup` / explicit coroutine chaining        | If AI-Solve paths are extracted as `async` functions, coroutine chaining requires no new library; `await` chains transfer naturally                                  |
| R-4  | `Protocol` (PEP 544)                                                     | The backend already uses `@runtime_checkable class StageRunner(Protocol)` — same pattern applicable to enrichment stages without adding a dependency                 |
| R-5  | Fowler _Refactoring_ — "Extract Function" + "Introduce Parameter Object" | The classic remedy for long functions that share too much local state: replace scattered local variables with a single parameter object (here: `EnrichmentRunState`) |

---

## 4. Candidate Adaptations for Yen-Go

Three decomposition patterns are viable, ordered from least to most invasive:

### Adaptation A — Extract-to-nested-async (minimal)

Extract the 3 code paths (position-only, has-solution, standard) as private `async` helper functions that **receive and return** a lightweight state object. They remain in `enrich_single.py`. The orchestrator reduces to ~200 lines of sequential `await` calls. No new files.

### Adaptation B — Config-lookup shared module (immediate DRY fix)

Create `analyzers/config_lookup.py` that owns all 4 module-level caches and loader functions. `enrich_single.py`, `estimate_difficulty.py`, `sgf_enricher.py`, and `validate_correct_move.py` all import from it. Can be done independently of any orchestrator restructuring.

### Adaptation C — Parameter object for orchestrator state (enables clean extraction later)

Introduce an `EnrichmentRunState` dataclass capturing the 9 tracking variables + `correct_move_gtp` + `solution_moves`. The orchestrator builds and mutates this object in-place, then reads it for result assembly. Any future extraction of a code path becomes a function that takes and returns `EnrichmentRunState` — the minimum data contract is explicit.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-ID | Risk                                                                                                             | Probability | Impact | Notes                                                                                                                                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | Test imports of private symbols break when symbols move                                                          | High        | Medium | `test_enrich_single.py` imports `_parse_tag_ids`, `_load_tag_slug_map`, `_TAG_SLUG_TO_ID`, `_extract_metadata` by name. Moving them to a new module without updating test imports causes `ImportError`.                                                  |
| R-2  | Module-level cache invalidation in tests breaks                                                                  | High        | Low    | Tests currently reset `_enrich_mod._TAG_SLUG_TO_ID = None` via `autouse` fixture. If cache moves to `config_lookup.py`, test reset target must change.                                                                                                   |
| R-3  | `_position_only_path` / `_ai_solve_failed` flags checked in result assembly after any code path fails mid-flight | High        | High   | If the three AI-Solve code paths are split into separate modules without a shared state carrier, partial failures (e.g., `_ai_solve_failed` set in the `except` block mid-path) must propagate back to the caller. This is the primary correctness risk. |
| R-4  | Nested `_notify()` closure — must be passed explicitly if paths are extracted                                    | Medium      | Low    | `_notify` captures `progress_cb` by closure. If code paths move to module-level functions, `_notify` must become a parameter or be recreated. The current pattern is not extractable without this plumbing.                                              |
| R-5  | Over-fragmentation — creating too many 50-line modules                                                           | Low         | Medium | The original criticism of "namesake" decomposition applies here too. Charter says the goal is "enable independent iteration," not maximize file count.                                                                                                   |

**License/compliance:** All candidates use stdlib or existing project dependencies only. No new packages required.

**Rejected options:**

- Full `StageRunner`-protocol port for enrichment stages: The backend `StageRunner` is synchronous (`def run()`); `enrich_single_puzzle` is `async`. Adopting the full backend protocol would require making the enrichment executor async-aware — an architectural change outside this refactor's scope.
- Keeping `_notify()` as inner closure AND moving code paths to separate modules: incompatible; closure cannot be shared across module boundaries without becoming a parameter.

---

## 6. Planner Recommendations

1. **Do Adaptation B (config_lookup) first, independently.** It is fully scope-isolated, fixes a real DRY violation across 4 files, and does not touch the orchestrator function at all. Line count savings: removes ~120 lines across the 4 affected files, consolidates 3 separate caching approaches into 1.

2. **Do Adaptation C (EnrichmentRunState dataclass) second.** Before extracting any code path to a new file, give the 9 tracking variables a named type. This single change (add a dataclass, update 9 assignment sites + 1 read site) is a ~40-line commit that makes every subsequent extraction clean and testable. Without it, any code-path extraction must thread 9+ variables as function arguments.

3. **Do Adaptation A (extract-to-nested-async) last, within enrich_single.py.** Each of the three branching code paths (~250 lines each) becomes a private `async def _run_position_only_path(state: EnrichmentRunState, ...) -> EnrichmentRunState`. The orchestrator collapses to configuration + routing + sequential `await` calls. No new public modules needed; test imports are unaffected.

4. **Update test imports after step 1.** After `config_lookup.py` exists, update `test_enrich_single.py` to import `_parse_tag_ids`, `_load_tag_slug_map`, and `_extract_metadata` from their canonical module homes. The `autouse` fixture's cache-reset target also updates at this point — one test file change with clear purpose.

---

## 7. Confidence and Risk Assessment

| Dimension                  | Score        | Notes                                                                                                                                                            |
| -------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Internal evidence quality  | High         | Full file read, all 1,593 lines analyzed                                                                                                                         |
| External precedent quality | Medium       | Standard refactoring patterns; no novel library needed                                                                                                           |
| Planner confidence score   | **72 / 100** | Deducted for: (a) unknown behavior of `_notify` in edge cases during extraction, (b) AI-Solve paths have 3 early-return branches that complicate state threading |
| Risk level                 | **Medium**   | Primary risk is state threading around partial failures in the AI-Solve paths                                                                                    |

---

## Appendix A — Responsibility Catalog (Output A)

| R-ID    | Responsibility                                       | Line Range | Variables Written                                                                                                                                           | Variables Read                                                                                                                             | Extractable                                                                       |
| ------- | ---------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| R-ES-01 | Config + trace init                                  | 540–558    | `config`, `config_hash`, `trace_id`, `_notify`                                                                                                              | —                                                                                                                                          | Yes / clean boundary                                                              |
| R-ES-02 | SGF parse + metadata                                 | 562–616    | `root`, `metadata`, `puzzle_id`, `tags`, `corner`, `move_order`, `ko_type`, `collection`, `position`, `board_size`                                          | `config`, `trace_id`                                                                                                                       | Yes / clean boundary                                                              |
| R-ES-03 | AI-Solve tracking var init                           | 617–631    | All 9 `_*` flags                                                                                                                                            | —                                                                                                                                          | Partial / becomes `EnrichmentRunState` constructor                                |
| R-ES-04 | Position-only AI-Solve path                          | 633–823    | `_position_only_path`, `_solution_tree_completeness`, `_budget_exhausted`, `_queries_used`, `correct_move_gtp`, `correct_move_sgf`, `solution_moves`        | All R-ES-02 vars, all 9 tracking flags                                                                                                     | Partial / needs state carrier                                                     |
| R-ES-05 | Has-solution + AI validation path                    | 824–975    | `_has_solution_path`, `_human_solution_confidence`, `_ai_solution_validated`, `_queries_used`, `_co_correct_detected`, `_ai_solve_failed`, `solution_moves` | All R-ES-02 vars, `ai_solve_config`                                                                                                        | Partial / needs state carrier                                                     |
| R-ES-06 | Standard path (no AI-Solve)                          | 976–990    | `correct_move_gtp`, `solution_moves`                                                                                                                        | `correct_move_sgf`, `board_size`                                                                                                           | Yes / trivial                                                                     |
| R-ES-07 | Structured start log + board notify                  | 991–1017   | `timings["parse"]`                                                                                                                                          | `puzzle_id`, `source_file`, `board_size`, `position`, `ko_type`, `sgf_text`                                                                | Yes / pure side-effect                                                            |
| R-ES-08 | Query building + crop                                | 1018–1066  | `query_result`, `request`, `cropped`, `effective_visits`, `timings["query_build"]`                                                                          | `config`, `sgf_text`, `ko_type`, `engine_manager.mode`                                                                                     | Yes / clean boundary                                                              |
| R-ES-09 | Engine analysis call                                 | 1067–1096  | `response`, `engine_model`, `engine_visits`                                                                                                                 | `request`, `engine_manager`, `puzzle_id`                                                                                                   | Yes / clean boundary                                                              |
| R-ES-10 | Coordinate back-translation                          | 1097–1110  | `response` (mutated)                                                                                                                                        | `cropped`, `response`                                                                                                                      | Yes / move to `query_builder.py`                                                  |
| R-ES-11 | Miai collection + move validation (Step 5)           | 1111–1201  | `correct_move_result`, `all_correct_gtp`                                                                                                                    | `response`, `correct_move_gtp`, `tags`, `corner`, `move_order`, `config`, `ko_type`, `position`                                            | Yes / delegates to `validate_correct_move`                                        |
| R-ES-12 | Tree validation skip-when-confident (Step 5a)        | 1202–1290  | `_skip_tree_validation`, mutates `correct_move_result`                                                                                                      | `config`, `response`, `correct_move_result`, `tags`, `ko_type`, `solution_moves`                                                           | Partial / modifies `correct_move_result` in place                                 |
| R-ES-13 | Wrong branch extraction + locality setup (Step 5.5)  | 1291–1327  | `curated_wrongs`, `nearby_moves`                                                                                                                            | `root`, `config`, `position`, `puzzle_id`                                                                                                  | Yes / clean boundary                                                              |
| R-ES-14 | Refutation generation + escalation (Step 6)          | 1328–1435  | `refutation_result`, `timings["refutation"]`                                                                                                                | `engine_manager`, `position`, `correct_move_gtp`, `response`, `config`, `nearby_moves`, `curated_wrongs`                                   | Yes / delegates to `generate_refutations`                                         |
| R-ES-15 | Difficulty estimation (Step 7)                       | 1436–1476  | `difficulty_estimate`, `timings["difficulty"]`                                                                                                              | `correct_move_result`, `refutation_result`, `solution_moves`, `branch_count`, `nearby_moves`, `_solution_tree_completeness`                | Yes / delegates to `estimate_difficulty`                                          |
| R-ES-16 | Result assembly + AC matrix + observability (Step 8) | 1477–1550  | `result`                                                                                                                                                    | All 9 `_*` flags, `difficulty_estimate`, `refutation_result`, `engine_model`, `engine_visits`, `config_hash`, `tags`, `trace_id`, `run_id` | No / the central accumulator; extraction only possible after state carrier exists |
| R-ES-17 | Teaching enrichment (Step 9)                         | 1551–1578  | `result.technique_tags`, `result.teaching_comments`, `result.hints`                                                                                         | `result`, `board_size`                                                                                                                     | Yes / delegates to classifiers                                                    |
| R-ES-18 | Timing finalization + final log                      | 1579–1593  | `timings["teaching"]`, `timings["total"]`, `result.phase_timings`                                                                                           | `timings`, `result`                                                                                                                        | Yes / pure side-effect                                                            |

---

## Appendix B — State Variable Dependency Graph (Output B)

```
R-ES-03 declares: _has_solution_path=F, _position_only_path=F, _ai_solve_failed=F,
                  _solution_tree_completeness=None, _budget_exhausted=F, _queries_used=0,
                  _co_correct_detected=F, _human_solution_confidence=None, _ai_solution_validated=F

R-ES-04 (position-only) writes:
  _position_only_path = True
  _solution_tree_completeness = solution_tree.tree_completeness
  _budget_exhausted = not budget.can_query()
  _queries_used = budget.used
  → correct_move_gtp, correct_move_sgf, solution_moves (out to main flow)

R-ES-05 (has-solution) writes:
  _has_solution_path = True
  _human_solution_confidence = human_confidence
  _ai_solution_validated = ai_validated
  _queries_used = budget.used
  _co_correct_detected = co_correct
  [on except]: _ai_solve_failed = True
  → solution_moves (out to main flow)

ALL 9 flags read only by R-ES-16 (result assembly):
  _ai_solve_failed       → ac_level = 0 (AI active but failed)
  _has_solution_path     → ac_level = 1 (enriched)
  _position_only_path    → ac_level = 1 or 2 (based on completeness)
  _solution_tree_completeness → ac_level 1 vs 2 decision, tree_truncated, max_resolved_depth (→ R-ES-15)
  _budget_exhausted      → tree_truncated, ac_level cap
  _queries_used          → result.queries_used
  _co_correct_detected   → result.co_correct_detected
  _human_solution_confidence → result.human_solution_confidence (only if has-solution + not failed)
  _ai_solution_validated → result.ai_solution_validated (only if has-solution + not failed)

Minimum data contract for a state carrier (EnrichmentRunState):
  Inputs (set by path):   _has_solution_path, _position_only_path, _ai_solve_failed,
                          _solution_tree_completeness, _budget_exhausted, _queries_used,
                          _co_correct_detected, _human_solution_confidence, _ai_solution_validated,
                          correct_move_gtp (str), solution_moves (list[str])
  Outputs (consumed by):  result assembly block (R-ES-16) and difficulty step (R-ES-15)
```

**Cross-responsibility flows that must remain in-module:**

- `correct_move_gtp` is written by R-ES-04/05/06 and read by R-ES-08/09/10/11/13/14/15/16/17 — it's the primary coordination variable and cannot be extracted without threading it explicitly.
- `response` is written by R-ES-09, mutated by R-ES-10, and read by R-ES-11/12/13/14/16 — tight coupling within steps 3–8.
- `correct_move_result` is written by R-ES-11, mutated by R-ES-12, and read by R-ES-15/16 — a sub-flow with in-place mutation.

---

## Appendix C — Sibling Module Inventory (Output C)

| File                       | Approx. Lines | Primary Responsibility                                             | Duplicate Config-Loading?                                          |
| -------------------------- | ------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `comment_assembler.py`     | ~175          | Build SGF `C[]` comment strings (correct/wrong/vital)              | No                                                                 |
| `enrich_single.py`         | 1,593         | **Orchestrator + metadata helpers + result assembly**              | **Yes** — tags.json (×2 variants) + puzzle-levels.json             |
| `estimate_difficulty.py`   | ~400          | Composite difficulty score → level ID                              | **Yes** — puzzle-levels.json (`_load_levels_from_config`, line 47) |
| `generate_refutations.py`  | ~450          | Generate wrong-move refutation sequences                           | No — receives `EnrichmentConfig` as param                          |
| `hint_generator.py`        | ~200          | Generate YH hint strings for compact puzzles                       | No                                                                 |
| `ko_validation.py`         | ~400          | Validate KataGo agreement for ko positions                         | No — receives config as param                                      |
| `observability.py`         | ~200          | Batch summary accumulation + disagreement JSONL sink               | No                                                                 |
| `property_policy.py`       | ~100          | Read `sgf-property-policies.json`; implement enrich/override rules | No — its own dedicated loader                                      |
| `query_builder.py`         | ~300          | Build KataGo analysis request + tight-board crop                   | No                                                                 |
| `refutation_classifier.py` | ~150          | Classify refutation type (snapback, ladder, net, etc.)             | No                                                                 |
| `sgf_enricher.py`          | ~200          | Apply enrichment results to SGF properties (YR, YG, YX)            | **Yes** — puzzle-levels.json (`_load_level_ids`, line 65)          |
| `sgf_parser.py`            | ~250          | Parse SGF strings; extract positions, moves, trees                 | No                                                                 |
| `single_engine.py`         | ~150          | `SingleEngineManager` lifecycle + `analyze()` dispatch             | No                                                                 |
| `solve_position.py`        | ~1,400        | AI-Solve: candidate analysis, tree building, injection             | No — receives config as param                                      |
| `teaching_comments.py`     | ~200          | Generate move-level teaching text                                  | No — receives config as param                                      |
| `technique_classifier.py`  | ~300          | Detect Go technique tags from analysis data                        | No — receives config on demand                                     |
| `tsumego_frame.py`         | ~120          | Add tsumego frame (stones) to KataGo queries                       | No                                                                 |
| `validate_correct_move.py` | ~920          | Tag-aware correct move validation; tree depth check                | **Yes** — tags.json (`_get_tag_consts`, lazy, line 110)            |
| `vital_move.py`            | ~60           | Detect the vital point from ownership data                         | No                                                                 |

**Summary of duplication:** 4 files implement their own lazy-loaded config cache for `tags.json` or `puzzle-levels.json`. All use `Path(__file__).resolve().parents[N]` with differing `N` values (3 or 4), creating fragile depth-dependent paths.

---

## Appendix D — Pipeline Pattern Precedent (Output D)

The backend uses a **three-layer composition pattern**:

| Layer         | Class                         | Responsibility                                                          |
| ------------- | ----------------------------- | ----------------------------------------------------------------------- |
| Data contract | `StageContext` (`@dataclass`) | Pure data carrier: config, paths, state, options. No logic.             |
| Stage logic   | `StageRunner` (`Protocol`)    | Stateless object with `name`, `run(ctx)`, `validate_prerequisites(ctx)` |
| Orchestration | `StageExecutor`               | Calls prerequisites → `run()` → records timing/state                    |
| Coordination  | `PipelineCoordinator`         | Sequences stages; not responsible for any stage's internal logic        |

**Key design decision in `protocol.py`:** `StageContext` carries _all_ cross-cutting data (staging dirs, run_id, source_id, config). No global vars. This is the pattern that would need to be adapted for `EnrichmentRunState` — an immutable input context + a mutable result accumulator.

**Critical difference** between backend and lab: backend stages are **synchronous** (`def run()`); `enrich_single_puzzle` is `async`. The `StageRunner` protocol cannot be directly adopted without an `AsyncStageRunner` variant.

**Applicable subset:** The `StageContext` data-carrier pattern is directly applicable. The `StageRunner` protocol shape (small named interface) is applicable as inspiration for the three code-path helpers. The `StageExecutor` separation is applicable once the orchestrator has ≥3 discrete async steps.

---

## Appendix E — Test Coupling Matrix (Output E)

| Test Class                        | Symbols Imported from `enrich_single`                     | Would Break if Moved?                                                         | Safe Target Module                                  |
| --------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------- |
| `TestSinglePuzzleProducesResult`  | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestResultContainsAllSections`   | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestErrorHandlingReturnsError`   | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestIdempotentEnrichment`        | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestParseTagIds`                 | `_parse_tag_ids`, `_load_tag_slug_map`, `_TAG_SLUG_TO_ID` | **Yes** — direct module attr access `_enrich_mod._TAG_SLUG_TO_ID = None`      | `config_lookup.py`                                  |
| `TestExtractMetadataYK`           | `_extract_metadata`                                       | **Yes** — also uses `_enrich_mod._TAG_SLUG_TO_ID = None` in `autouse` fixture | `enrich_metadata.py` or stays in `enrich_single.py` |
| `TestDifficultyFallback`          | `enrich_single_puzzle`, patches `estimate_difficulty`     | No (patches by dotted path, not import)                                       | —                                                   |
| `TestPositionOnlyAiSolveSuccess`  | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestPositionOnlyAiSolveFallback` | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestCorrectMovesOnlySgf`         | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |
| `TestRealPuzzleEnrichment`        | `enrich_single_puzzle` (public)                           | No                                                                            | —                                                   |

**Bottom line:** Only `TestParseTagIds` and `TestExtractMetadataYK` have hard import-address coupling to private symbols. The `autouse` fixture resets `_enrich_mod._TAG_SLUG_TO_ID` by attribute name — if this cache moves to `config_lookup.py`, the fixture must reset `_config_lookup_mod._TAG_SLUG_TO_ID` instead. This is a 3-line change in `conftest`/test setup, not a structural risk.

---

## Appendix F — Top 3 Risks (Output F)

**Risk 1: Partial-failure state threading across AI-Solve code paths (High probability / High impact)**  
The `_ai_solve_failed = True` assignment happens inside an `except` block within the has-solution code path (~line 968). If this block is extracted to a module-level function, the exception must be caught, the flag set, and the state object returned — all without re-raising. The current code structure silently sets the flag and falls through to normal processing. This "silent set + fall-through" pattern is easy to break if the code path is extracted as a function that the caller `await`s and then checks, rather than the flag being set in place. **Mitigation:** Introduce `EnrichmentRunState` before any extraction; make `_ai_solve_failed` a field on the state object returned by the helper.

**Risk 2: Module-level cache invalidation coupling in tests (High probability / Low impact)**  
The `autouse` fixture in `test_enrich_single.py` accesses `_enrich_mod._TAG_SLUG_TO_ID = None` directly. After splitting, test setup must know which module owns the cache. If a future developer adds a new test that resets the wrong module's cache (or does not reset it at all), tests will interfere with each other across test classes. **Mitigation:** After moving cache to `config_lookup.py`, expose a `clear_config_caches()` test helper in that module (analogous to `clear_cache()` already exported from `config.py`).

**Risk 3: `_notify` closure scope lost on extraction (Medium probability / Medium impact)**  
The inner `_notify` coroutine captures `progress_cb` from the outer function's closure. If any extracted helper needs to fire progress notifications, it must receive `_notify` as an explicit parameter — or implement its own notification call. Multiple small functions each accepting `_notify` as a parameter creates noisy signatures. **Mitigation:** Once `EnrichmentRunState` exists, attach `notify_fn: Callable | None` to it so it travels automatically without polluting every function signature.
