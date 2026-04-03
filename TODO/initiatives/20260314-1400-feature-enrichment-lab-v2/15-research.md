# Research: Enrichment Lab Pipeline Stage Decomposition

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Research question**: What pipeline stages are necessary, redundant, or need to be more granular? What is the optimal stage flow?  
**Last Updated**: 2026-03-14

---

## 1. Research Question & Boundaries

| ID | Question | Status |
|----|----------|--------|
| RQ-1 | What does each stage do (inputs, outputs, error policy, analyzer calls)? | ✅ resolved |
| RQ-2 | What data flows between stages (what context does each stage need from upstream)? | ✅ resolved |
| RQ-3 | Is each stage necessary? Could it be merged with another? | ✅ resolved |
| RQ-4 | Is any stage doing too much? Should it be split? | ✅ resolved |
| RQ-5 | What are the actual failure modes per stage? | ✅ resolved |
| RQ-6 | Full technique tag list vs classifier detection capability (gap analysis)? | ✅ resolved |
| RQ-7 | What is the proposed optimized stage flow? | ✅ resolved |

---

## 2. Current Stage Inventory (Exhaustive)

### 2.1 Stage Definition Table

| R-ID | Stage | Class/Function | File | Error Policy | Engine Calls | Lines (est.) |
|------|-------|----------------|------|-------------|--------------|-------------|
| S-1 | Parse SGF | `ParseStage` | [parse_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/parse_stage.py) | FAIL_FAST | 0 | ~80 |
| S-2 | Solve-path dispatch | `run_position_only_path()`, `run_has_solution_path()`, `run_standard_path()` | [solve_paths.py](../../tools/puzzle-enrichment-lab/analyzers/stages/solve_paths.py) | DEGRADE | 1-20+ (position-only builds trees) | ~500 |
| S-3 | Query + Analysis | `QueryStage` | [query_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/query_stage.py) | FAIL_FAST | 1 (+ possible escalation) | ~170 |
| S-4 | Validation | `ValidationStage` | [validation_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/validation_stage.py) | DEGRADE | 0-N (tree validation uses engine) | ~180 |
| S-5 | Refutations | `RefutationStage` | [refutation_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/refutation_stage.py) | DEGRADE | N (one per candidate + escalation) | ~160 |
| S-6 | Difficulty | `DifficultyStage` | [difficulty_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/difficulty_stage.py) | DEGRADE | 0 | ~100 |
| S-7 | Assembly | `AssemblyStage` | [assembly_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/assembly_stage.py) | FAIL_FAST | 0 | ~180 |
| S-8 | Teaching | `TeachingStage` | [teaching_stage.py](../../tools/puzzle-enrichment-lab/analyzers/stages/teaching_stage.py) | DEGRADE | 0 | ~130 |

---

## 3. Stage-by-Stage Deep Analysis

### 3.1 S-1: ParseStage

**What it does:**
1. Parses raw SGF text into node tree (`parse_sgf()`)
2. Extracts metadata via `config_lookup.extract_metadata()` → `SgfMetadata` (puzzle_id, tags, corner, move_order, ko_type, collection)
3. Falls back to source filename as puzzle_id if GN absent
4. Extracts correct first move (`extract_correct_first_move()`)
5. Extracts board position (`extract_position()`)

**Inputs:** `ctx.sgf_text`, `ctx.source_file`  
**Outputs:** `ctx.root`, `ctx.metadata`, `ctx.position`, `ctx.correct_move_sgf`  
**Engine calls:** 0  
**Analyzer modules called:** `core.tsumego_analysis.parse_sgf`, `extract_position`, `extract_correct_first_move`, `config_lookup.extract_metadata`

**Is it necessary?** Yes — foundational. Every downstream stage depends on parsed data.  
**Should it be split?** No — SGF parsing, metadata extraction, and position extraction are tightly coupled and fast (~0ms, no I/O).  
**Could it be merged?** No — it must run first and is already minimal.

**Failure modes:**

| F-ID | Failure | Cause | Consequence |
|------|---------|-------|-------------|
| F-1.1 | Invalid SGF syntax | Malformed file | Pipeline aborts (FAIL_FAST) — correct |
| F-1.2 | No stones in position | Empty board SGF | `extract_position` raises ValueError → abort |
| F-1.3 | No correct move found | Position-only SGF | `correct_move_sgf = None` → dispatches to position-only path (handled) |
| F-1.4 | Missing PL property | Color ambiguous | Inferred from first correct move color (handled in query_builder) |

**Verdict: ✅ Keep as-is. No changes needed.**

---

### 3.2 S-2: Solve-Path Dispatch (NOT a formal stage)

**What it does:** Three code paths dispatched by orchestrator (`enrich_single.py`) BETWEEN ParseStage and QueryStage:

| Path | Condition | What Happens | Engine Calls |
|------|-----------|-------------|--------------|
| `run_position_only_path()` | `correct_move_sgf is None` | AI-Solve builds entire solution tree from scratch (A/B/C priority allocation, tree building, injection into SGF) | 1 pre-analysis + N tree queries (up to `max_total_tree_queries`) |
| `run_has_solution_path()` | `correct_move_sgf is not None` AND `ai_solve_config is not None` | Validates human solution against AI, discovers alternative correct roots, injects alternatives | 1 pre-analysis + N discovery queries |
| `run_standard_path()` | `correct_move_sgf is not None` AND `ai_solve_config is None` | Simply extracts moves from existing tree — no engine calls | 0 |

**Inputs:** `ctx.root`, `ctx.position`, `ctx.correct_move_sgf`, `ctx.metadata`, engine_manager, config  
**Outputs:** `ctx.correct_move_gtp`, `ctx.correct_move_sgf` (updated), `ctx.solution_moves`, `ctx.state` (EnrichmentRunState with flags)

**Is it necessary?** Yes — the three paths represent fundamentally different processing needs.  
**Should it be split?** **This is the messiest part.** `solve_paths.py` is ~500 lines containing 3 large async functions that each do:
  - Build their own query (duplicating query_builder logic)
  - Run their own engine call (bypassing QueryStage)
  - Manipulate the SGF tree directly
  - Set flow-through state variables  

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-2.1 | **position-only and has-solution paths build their own query** using `build_query_from_position()`, completely bypassing QueryStage's crop+frame+uncrop flow. This means they get different query behavior (no cropping) | High |
| P-2.2 | **Solve paths run engine calls outside the stage runner** — no timing/notify/error-policy wrapping for these calls | Medium |
| P-2.3 | **State coupling**: solve paths write to `EnrichmentRunState` AND set `ctx` fields, creating a dual-state problem (state vs ctx) | Medium |
| P-2.4 | **position-only path is ~200 lines** handling tree building with its own budget, inject logic, roundtrip assertions | Low (complex but correct) |
| P-2.5 | **Metadata passed as dict** via `.to_dict()` — the solve paths support both dict and SgfMetadata with `isinstance` checks everywhere | Low (tech debt) |

**Verdict: ⚠️ Needs restructuring.** The solve-path dispatch is the #1 source of pipeline complexity. See Section 8 for proposals.

---

### 3.3 S-3: QueryStage

**What it does:**
1. Logs puzzle context header (one-time session metadata)
2. Notifies GUI with board state
3. Gets effective max visits from config (mode-aware)
4. Builds analysis query via `build_query_from_sgf()`:
   - Parses SGF (redundant — already parsed in S-1)
   - Extracts position (redundant — already extracted in S-1)
   - Crops 19×19 to tight board
   - Overrides komi to 0
   - Computes puzzle region moves
   - Applies tsumego frame via `frame_adapter.apply_frame()`
   - Resolves ko-aware rules and PV length
5. Runs engine analysis via `SingleEngineManager.analyze()`
6. Back-translates cropped coordinates via `uncrop_response()`

**Inputs:** `ctx.position`, `ctx.metadata`, `ctx.sgf_text`, `ctx.engine_manager`, `ctx.config`  
**Outputs:** `ctx.response`, `ctx.cropped`, `ctx.engine_model`, `ctx.engine_visits`, `ctx.effective_visits`

**Analyzer modules called:** `query_builder.build_query_from_sgf()`, `uncrop_response()`, `SingleEngineManager.analyze()`

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-3.1 | **Double parsing**: `build_query_from_sgf()` re-parses the SGF and re-extracts position, even though ParseStage already did this | Medium (wasted work, potential divergence) |
| P-3.2 | **Query builder has two entry points**: `build_query_from_sgf()` (used by QueryStage) and `build_query_from_position()` (used by solve paths). Both call `prepare_tsumego_query()` but with different cropping behavior | Medium |
| P-3.3 | **Cropping is embedded inside query building** — not a separate concern. Tests can't test frame without also cropping | Low |

**Is it necessary?** Yes — this is where KataGo analysis happens.  
**Should it be split?** Possibly. Crop → Frame → Query → Analyze could be 4 distinct steps, but they're tightly sequential with no independent utility. Current grouping is pragmatic.  
**Could it be merged?** No — it's the heaviest stage (engine latency dominates).

**Verdict: ⚠️ Fix double-parsing. Consider accepting Position directly instead of re-parsing SGF.**

---

### 3.4 S-4: ValidationStage

**What it does:**
1. Collects all correct moves for miai handling
2. Calls `validate_correct_move()` — tag-aware dispatch to 7 specialized validators:
   - `_validate_life_and_death()`: ownership thresholds + winrate rescue
   - `_validate_tactical()`: PV forcing sequence check
   - `_validate_capture_race()`: stricter timing-sensitive validation
   - `_validate_connection()`: group connectivity + standard ranking
   - `_validate_seki()`: 3-signal detection (winrate, score, move reasonableness)
   - Ko → delegates to `ko_validation.validate_ko()`
   - `_validate_miai()`: multi-correct-move validation (any correct in top-N)
3. Deep solution tree validation (`validate_solution_tree_depth()`):
   - Uses engine to validate N moves deep into solution tree
   - Can be skipped when confident (winrate > threshold AND in top-N)
   - Capped at `quick_only_depth_cap` in quick mode
4. Extracts curated wrong branches from SGF (`extract_wrong_move_branches()`)
5. Computes nearby moves for spatial locality filter

**Inputs:** `ctx.response`, `ctx.correct_move_gtp`, `ctx.metadata`, `ctx.position`, `ctx.root`, `ctx.solution_moves`, `ctx.engine_manager`, `ctx.config`  
**Outputs:** `ctx.validation_result` (CorrectMoveResult), `ctx.curated_wrongs`, `ctx.nearby_moves`  
**Engine calls:** 0-N (tree validation depth checks, each is a separate engine call)

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-4.1 | **Tree validation engine calls are inside ValidationStage** — these are full KataGo queries (one per depth level), not just data transformations | Medium |
| P-4.2 | **Curated wrongs extraction has nothing to do with validation** — it's data extraction from SGF for the refutation stage | Low (doesn't break anything, just SRP violation) |
| P-4.3 | **Nearby moves computation is a utility** — spatial locality belongs to position concern, not validation | Low |
| P-4.4 | **Validators are mostly identical**: 5 of 7 validators use `_classify_move()` → `_status_from_classification()` → flags. Only seki and ko have meaningfully different logic | Medium (code smell, not broken) |

**Is it necessary?** Yes — validation is the core correctness check.  
**Should it be split?** *Curated wrongs* and *nearby moves* could be extracted. Tree validation could be a separate stage (it makes engine calls). But the benefit is marginal.  
**Could it be merged?** No — distinct logical concern.

**Verdict: ✅ Keep. Minor SRP: curated wrongs + nearby moves could move to a pre-processing step.**

---

### 3.5 S-5: RefutationStage

**What it does:**
1. Calls `generate_refutations()` orchestrator:
   a. Builds curated refutations from SGF wrong branches
   b. Enriches curated moves with KataGo policy/winrate from initial analysis
   c. If curated meet count → skip AI generation
   d. Else: `identify_candidates()` → per-candidate `generate_single_refutation()` (1 engine call each)
   e. Merges curated + AI refutations, caps at `refutation_max_count`
2. Refutation escalation loop: if too few refutations found:
   a. Retries with lower thresholds and higher visits
   b. Up to `max_escalation_attempts` retries

**Inputs:** `ctx.response`, `ctx.correct_move_gtp`, `ctx.position`, `ctx.nearby_moves`, `ctx.curated_wrongs`, `ctx.engine_manager`, `ctx.config`  
**Outputs:** `ctx.refutation_result` (RefutationResult)  
**Engine calls:** N (one per candidate wrong move) + M (escalation retries)

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-5.1 | **Refutation queries use UNFRAMED position** — `generate_single_refutation()` builds an `AnalysisRequest` directly from `position` without applying tsumego frame | High — KataGo analyzes different board state than QueryStage |
| P-5.2 | **No puzzle region restriction on refutation queries** — unlike the main query which uses `allowed_moves`, refutation queries allow all moves | Medium — wastes KataGo policy on irrelevant areas |
| P-5.3 | **Escalation creates modified config copy** — `ctx.config.model_copy(update={...})` for each escalation attempt | Low (correct but creates temporary objects) |

**Is it necessary?** Yes — refutations are core to puzzle teaching value.  
**Should it be split?** The escalation loop is ~50 lines within the stage — not worth a separate stage.  
**Could it be merged?** No.

**Verdict: ⚠️ Fix P-5.1 (unframed position). The refutation queries should use the same frame/region as the main analysis.**

---

### 3.6 S-6: DifficultyStage

**What it does:**
1. Sets validation context fields (puzzle_id, visits_used, confidence)
2. Computes structural signals (branch count, local candidates, max resolved depth)
3. Calls `estimate_difficulty()` — 4-component weighted formula:
   - Policy rank (30%): `(1.0 - policy_prior) × weight`
   - Visits to solve (30%): `log2(visits/base) / log2(max/base) × weight`
   - Trap density (20%): score-based formula from refutations
   - Structural (20%): depth + branches + local_candidates + refutation_count + proof_depth
4. Maps raw score to level via `score_to_level_thresholds`
5. Elo-anchor gate: cross-checks composite level against policy-based level
6. Falls back to `estimate_difficulty_policy_only()` on exception

**Inputs:** `ctx.validation_result`, `ctx.refutation_result`, `ctx.solution_moves`, `ctx.root`, `ctx.nearby_moves`, `ctx.state`, `ctx.position`, `ctx.metadata`  
**Outputs:** `ctx.difficulty_estimate` (DifficultyEstimate)  
**Engine calls:** 0

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-6.1 | **Sets fields on `ctx.validation_result`** that should have been set by ValidationStage (puzzle_id, visits_used, confidence) | Low (coupling between stages) |
| P-6.2 | **`count_solution_branches()`** traverses the SGF tree — a read operation from `ctx.root` that has nothing to do with difficulty math | Low |

**Is it necessary?** Yes — difficulty estimation is core output.  
**Should it be split?** No — it's a pure computation stage.  
**Could it be merged?** Could theoretically merge into AssemblyStage (both are pure data), but difficulty has its own fallback path, so separation is cleaner.

**Verdict: ✅ Keep as-is.**

---

### 3.7 S-7: AssemblyStage

**What it does:**
1. Creates `AiAnalysisResult` via `from_validation()` factory
2. Populates refutations via `build_refutation_entries()`
3. Populates difficulty via `build_difficulty_snapshot()`
4. AC level decision matrix (5 conditions based on solve path, tree completeness, budget)
5. Goal inference (`infer_goal()` from score deltas + ownership)
6. Wires observability fields (queries_used, tree_truncated, co_correct_detected)
7. Humanizes level info (name, range from config)
8. Level mismatch logging (existing YG vs computed level)

**Inputs:** ALL upstream context fields  
**Outputs:** `ctx.result` (AiAnalysisResult)  
**Engine calls:** 0

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-7.1 | **Goal inference makes its own engine data lookups** — iterates `ctx.response.move_infos` to find score/ownership for correct move, duplicating work that ValidationStage already did | Low |
| P-7.2 | **AC level logic is complex but correct** — 5-way conditional that depends on `state.position_only_path`, `state.has_solution_path`, `state.solution_tree_completeness`, `state.budget_exhausted`, `state.ai_solve_failed` | Low (inherent complexity) |
| P-7.3 | **Level mismatch detection loads level map** — calls `load_level_id_map()` which re-reads config | Negligible |

**Is it necessary?** Yes — this is where the final output model is assembled.  
**Should it be split?** Goal inference could be its own stage, but it's ~20 lines and doesn't warrant it.  
**Could it be merged?** No — FAIL_FAST policy is appropriate (no result = complete failure).

**Verdict: ✅ Keep as-is.**

---

### 3.8 S-8: TeachingStage

**What it does:**
1. `classify_techniques()` — 8 heuristic detectors → tag list
2. `generate_teaching_comments()` — V2 two-layer composition (vital_move + refutation_classifier + comment_assembler)
3. `generate_hints()` — 3-tier progressive hints with coordinate tokens
4. `enrich_sgf()` — writes YG, YX, YH, YR, refutation branches, teaching comments into SGF

**Inputs:** `ctx.result` (AiAnalysisResult), `ctx.sgf_text`, `ctx.position`  
**Outputs:** `ctx.result` mutated with `.technique_tags`, `.teaching_comments`, `.hints`, `.enriched_sgf`

**Problems identified:**

| P-ID | Problem | Severity |
|------|---------|----------|
| P-8.1 | **Does 4 distinct things**: technique classification, teaching comments, hints, SGF writeback. These are independent concerns | Medium (SRP violation) |
| P-8.2 | **`classify_techniques()` receives analysis as dict** (`result.model_dump()`) instead of typed model — loses type safety | Low |
| P-8.3 | **SGF writeback is the only part that modifies the SGF tree** — conceptually different from tag generation | Low |
| P-8.4 | **Technique classifier only has 8 of 28 tags** (see Section 6) — massive gap | High (functional gap) |

**Is it necessary?** Yes — teaching output is a key deliverable.  
**Should it be split?** Reasonable candidate: split into TechniqueStage + TeachingStage + SgfWritebackStage. But all are DEGRADE and sequential, so the benefit is mostly clarity.  
**Could it be merged?** No.

**Verdict: ⚠️ Consider splitting. Technique classification is the weakest link and deserves isolation for testing/iteration.**

---

## 4. Current Stage Flow Diagram (with Data Dependencies)

```
┌──────────────────────────────────────────────────────────────────┐
│ INPUT: sgf_text, engine_manager, config, source_file             │
└──────────────────────┬───────────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-1: ParseStage (FAIL_FAST)         │
    │ Reads: sgf_text, source_file        │
    │ Writes: root, metadata, position,   │
    │         correct_move_sgf            │
    │ Engine: 0                           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-2: solve_paths [NOT A STAGE]      │
    │ Reads: root, position, metadata,    │
    │        correct_move_sgf,            │
    │        engine_manager, config       │
    │ Writes: correct_move_gtp,           │
    │         solution_moves, state       │
    │ Engine: 0..20+ (path dependent)     │ ← Runs OUTSIDE StageRunner
    │                                     │
    │  if correct_move_sgf is None:       │
    │    position_only_path (AI-Solve)    │
    │    → builds own query (NO CROP)     │
    │    → runs engine calls directly     │
    │    → injects solution into SGF      │
    │                                     │
    │  elif ai_solve_config not None:     │
    │    has_solution_path (validate)      │
    │    → builds own query (NO CROP)     │
    │    → discovers alternatives          │
    │                                     │
    │  else:                              │
    │    standard_path (extract only)      │
    │    → 0 engine calls                 │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-3: QueryStage (FAIL_FAST)         │
    │ Reads: sgf_text(!), metadata,       │ ← Re-parses SGF (P-3.1)
    │        position(!), config,         │ ← Re-extracts position
    │        engine_manager               │
    │ Writes: response, cropped,          │
    │         engine_model, engine_visits  │
    │ Engine: 1 (+ possible escalation)   │
    │                                     │
    │ Flow: parse SGF → extract position  │ ← REDUNDANT with S-1
    │       → crop → frame → analyze      │
    │       → uncrop response             │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-4: ValidationStage (DEGRADE)      │
    │ Reads: response, correct_move_gtp,  │
    │        metadata, position, root,    │
    │        solution_moves, config,      │
    │        engine_manager               │
    │ Writes: validation_result,          │
    │         curated_wrongs, nearby_moves│
    │ Engine: 0..N (tree validation)      │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-5: RefutationStage (DEGRADE)      │
    │ Reads: response, correct_move_gtp,  │
    │        position, nearby_moves,      │
    │        curated_wrongs, config,      │
    │        engine_manager               │
    │ Writes: refutation_result           │
    │ Engine: N (per-candidate + escal.)  │
    │                                     │
    │ ⚠ Uses UNFRAMED position (P-5.1)   │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-6: DifficultyStage (DEGRADE)      │
    │ Reads: validation_result,           │
    │        refutation_result,           │
    │        solution_moves, root,        │
    │        nearby_moves, state,         │
    │        position, metadata           │
    │ Writes: difficulty_estimate         │
    │ Engine: 0                           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-7: AssemblyStage (FAIL_FAST)      │
    │ Reads: ALL upstream results +       │
    │        response, state, metadata,   │
    │        correct_move_gtp, config     │
    │ Writes: result (AiAnalysisResult)   │
    │ Engine: 0                           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ S-8: TeachingStage (DEGRADE)        │
    │ Reads: result, sgf_text, position   │
    │ Writes: result.technique_tags,      │
    │         result.teaching_comments,   │
    │         result.hints,               │
    │         result.enriched_sgf         │
    │ Engine: 0                           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │ OUTPUT: AiAnalysisResult            │
    │ (with enriched_sgf, timings, etc.)  │
    └─────────────────────────────────────┘
```

---

## 5. Failure Mode Inventory

### 5.1 Per-Stage Failure Modes

| F-ID | Stage | Failure Mode | Likelihood | Consequence | Current Handling |
|------|-------|-------------|------------|-------------|-----------------|
| F-1.1 | S-1 Parse | Invalid SGF syntax | Medium (external sources) | Pipeline aborts | FAIL_FAST → error result ✅ |
| F-1.2 | S-1 Parse | No stones in SGF | Low | Pipeline aborts | ValueError → error result ✅ |
| F-1.3 | S-1 Parse | Missing PL property | Medium | Wrong player color | Inferred from first move ✅ |
| F-2.1 | S-2 Solve | AI-Solve finds no correct moves | Medium | Tier-2 fallback | `build_partial_result()` ✅ |
| F-2.2 | S-2 Solve | Engine unavailable | Low | Tier-1 fallback | `build_partial_result()` ✅ |
| F-2.3 | S-2 Solve | Budget exhausted before tree complete | Medium | Incomplete tree | Logged, `tree_truncated=True` ✅ |
| F-2.4 | S-2 Solve | Pass-as-best-move rejection | Low | Error result | ValueError → `make_error_result()` ✅ |
| F-3.1 | S-3 Query | Board size < 5 or > 19 | Rare | Pipeline aborts | ValueError guard (R.0.2) ✅ |
| F-3.2 | S-3 Query | Engine timeout | Low | Pipeline aborts | FAIL_FAST → propagated ⚠️ |
| F-3.3 | S-3 Query | Cropping drops outlier stones | Rare | Silent data loss | WARNING logged ⚠️ |
| F-4.1 | S-4 Validate | Correct move not in analysis | Medium | REJECTED status | `rank=0` → REJECTED with flags ✅ |
| F-4.2 | S-4 Validate | Tree validation engine error | Low | `not_validated` | Exception caught, continues ✅ |
| F-4.3 | S-4 Validate | Wrong validator dispatched | Low (config error) | Incorrect thresholds | Config-driven, testable ✅ |
| F-5.1 | S-5 Refute | No candidates above policy threshold | Medium | Empty refutations | Escalation triggered ✅ |
| F-5.2 | S-5 Refute | Escalation exhausted | Medium | Zero refutations | WARNING logged, continues ✅ |
| F-5.3 | S-5 Refute | Engine error mid-refutation | Low | Partial refutations | Per-candidate try/except ✅ |
| F-6.1 | S-6 Difficulty | All signals at defaults | Low | Meaningless score | Falls back to `estimate_difficulty_policy_only()` ✅ |
| F-7.1 | S-7 Assembly | Missing upstream results | Low (code bug) | AttributeError | FAIL_FAST → error result ✅ |
| F-7.2 | S-7 Assembly | Goal inference failure | Low | `goal=None` | Exception caught ✅ |
| F-8.1 | S-8 Teaching | SGF writeback failure | Low | No enriched SGF | Exception caught, WARNING ✅ |
| F-8.2 | S-8 Teaching | No techniques detected | Medium | Empty tag list | Returns `[]` with WARNING ⚠️ |

### 5.2 Cross-Stage Failure Modes

| F-ID | Failure Mode | Stages Affected | Severity |
|------|-------------|-----------------|----------|
| F-X.1 | **Solve paths and QueryStage use different queries** — position-only/has-solution paths call `build_query_from_position()` (no crop), QueryStage uses `build_query_from_sgf()` (with crop). The `ctx.response` from QueryStage is for a DIFFERENT board than what solve paths analyzed | S-2, S-3 | **High** — policy priors, winrates, and PV moves from QueryStage may not match what solve paths found |
| F-X.2 | **Refutation queries use unframed position** while QueryStage uses framed position. KataGo may produce different policy distributions | S-3, S-5 | **High** — refutation results may be inconsistent with main analysis |
| F-X.3 | **Double-parsing divergence risk** — if ParseStage and QueryStage parse the same SGF differently (e.g., due to encoding), downstream results could be inconsistent | S-1, S-3 | **Low** (same parser, but unnecessary code path) |
| F-X.4 | **EnrichmentRunState and PipelineContext are dual state** — solve_paths writes to state, then orchestrator copies fields to ctx. If copying is missed, downstream stages see stale data | S-2, all | **Medium** |

---

## 6. Technique Tag Gap Analysis

### 6.1 Full Tag Inventory from `config/tags.json` (28 tags)

| R-ID | Slug | ID | Category | Classifier Detects? | Detection Method |
|------|------|----|----------|---------------------|-----------------|
| T-1 | `life-and-death` | 10 | objective | ❌ Not detected (falls back) | Default fallback only |
| T-2 | `living` | 14 | objective | ❌ | Not implemented |
| T-3 | `ko` | 12 | objective | ✅ | PV recapture pattern + refutation type |
| T-4 | `seki` | 16 | objective | ✅ | Balanced winrate + zero refutations + accepted status |
| T-5 | `capture-race` | 60 | technique | ❌ | Not implemented |
| T-6 | `escape` | 66 | technique | ❌ | Not implemented |
| T-7 | `snapback` | 30 | tesuji | ✅ | Low policy + high winrate + large refutation delta |
| T-8 | `throw-in` | 38 | tesuji | ✅ | Correct move on 1st/2nd line (ANY edge) |
| T-9 | `ladder` | 34 | tesuji | ✅ | Diagonal chase pattern in PV |
| T-10 | `net` | 36 | tesuji | ✅ | High policy + high winrate + uniform refutation deltas |
| T-11 | `liberty-shortage` | 48 | tesuji | ❌ | Not implemented |
| T-12 | `connect-and-die` | 44 | tesuji | ❌ | Not implemented |
| T-13 | `under-the-stones` | 46 | tesuji | ❌ | Not implemented |
| T-14 | `double-atari` | 32 | tesuji | ❌ | Not implemented |
| T-15 | `vital-point` | 50 | tesuji | ❌ | Not implemented (vital_move.py exists but not wired to classifier) |
| T-16 | `clamp` | 40 | tesuji | ❌ | Not implemented |
| T-17 | `eye-shape` | 62 | technique | ⚠️ Partial | Only if existing tags contain "eye" (passthrough) |
| T-18 | `dead-shapes` | 64 | technique | ❌ | Not implemented |
| T-19 | `nakade` | 42 | tesuji | ❌ | Not implemented |
| T-20 | `connection` | 68 | technique | ⚠️ Partial | Only if existing tags contain "connection" (passthrough) |
| T-21 | `cutting` | 70 | technique | ⚠️ Partial | Only if existing tags contain "cutting" (passthrough) |
| T-22 | `corner` | 74 | technique | ❌ | Not implemented |
| T-23 | `sacrifice` | 72 | technique | ❌ | Not implemented |
| T-24 | `shape` | 76 | technique | ❌ | Not implemented |
| T-25 | `endgame` | 78 | technique | ❌ | Not implemented |
| T-26 | `tesuji` | 52 | tesuji | ❌ | Not implemented |
| T-27 | `joseki` | 80 | technique | ❌ | Not implemented |
| T-28 | `fuseki` | 82 | technique | ❌ | Not implemented |

### 6.2 Gap Summary

| Metric | Count |
|--------|-------|
| Total tags in config | 28 |
| Actively detected by classifier | 6 (ko, seki, snapback, throw-in, ladder, net) |
| Partial passthrough only | 3 (eye-shape, connection, cutting — only if already in existing tags) |
| Direct capture detected | 1 (but maps to "capture", not a config tag) |
| **Not detected at all** | **18 tags (64%)** |

### 6.3 Detection Method Quality Assessment

| Tag | Quality | Notes |
|-----|---------|-------|
| ko | ✅ Good | PV recapture is reliable signal |
| ladder | ⚠️ Fair | Diagonal ratio heuristic works for classic ladders, misses diagonal-shift and edge ladders |
| snapback | ⚠️ Weak | Policy < threshold AND winrate > threshold is very loose — many false positives possible (any sacrifice-then-win pattern triggers it) |
| net | ⚠️ Weak | High policy + high winrate + uniform delta spread is coincidental — doesn't actually check surrounding geometry |
| throw-in | ⚠️ Weak | Only checks if move is on edge — many edge moves are NOT throw-ins |
| seki | ⚠️ Weak | Balanced winrate + zero refutations + accepted status — too many false triggers on trivially-alive positions |
| capture (non-config) | ❌ Maps to wrong slug | Detected but "capture" is not in the 28-tag config. Should be life-and-death or capture-race |

### 6.4 Detectors that require board-state analysis (not just PV patterns)

These tags CANNOT be reliably detected from PV/policy/winrate alone — they need liberty counting, group connectivity, or eye shape analysis from `liberty.py`:

| Tag | Requires |
|-----|----------|
| liberty-shortage | Liberty count comparison before/after move |
| capture-race | Liberty count of competing groups |
| connect-and-die | Group connectivity before/after entire PV |
| nakade | Interior point detection + eye count |
| dead-shapes | Shape pattern matching against known killable shapes |
| eye-shape | Eye detection (`is_eye()` already in liberty.py) |
| double-atari | Atari detection on two groups simultaneously |
| vital-point | Already partially implemented in `vital_move.py` |
| sacrifice | Stone count decrease after correct move |
| escape | Group liberty increase / connection to safe group |
| connection | Group connectivity graph before/after move |
| cutting | Group disconnection detection |

---

## 7. Data Dependency Matrix

Shows what each stage reads from PipelineContext (R = reads, W = writes).

| Field | S-1 Parse | S-2 Solve | S-3 Query | S-4 Valid | S-5 Refute | S-6 Diff | S-7 Assemble | S-8 Teach |
|-------|-----------|-----------|-----------|-----------|------------|----------|-------------|-----------|
| `sgf_text` | R | | R(!) | | | | | R |
| `root` | W | R | | R | | R | | |
| `metadata` | W | R | R | R | | R | R | R |
| `position` | W | R | R(!) | R | R | R | | R |
| `correct_move_sgf` | W | R/W | | | | | | |
| `correct_move_gtp` | | W | | R | R | | R | |
| `solution_moves` | | W | | R | | R | | |
| `state` | | W | | | | R | R | |
| `response` | | | W | R | R | | R | |
| `cropped` | | | W | | | | | |
| `engine_model` | | | W | | | | R | |
| `engine_visits` | | | W | | | | R | |
| `validation_result` | | | | W | | R | R | |
| `curated_wrongs` | | | | W | R | | | |
| `nearby_moves` | | | | W | R | R | | |
| `refutation_result` | | | | | W | R | R | |
| `difficulty_estimate` | | | | | | W | R | |
| `result` | | | | | | | W | R/W |

**Key observations:**
- `sgf_text` is read by S-1 AND S-3 (double-parsing, P-3.1)
- `position` is read by S-1 AND re-extracted in S-3 (P-3.1)
- S-2 (solve paths) reads `root` and `position` from S-1 but builds its own query, bypassing S-3
- S-7 (Assembly) reads from nearly every upstream stage — it's the gathering point
- S-8 (Teaching) reads `result` from S-7 and modifies it in-place

---

## 8. Proposed Optimized Stage Flow

### 8.1 Option A: Minimal Cleanup (Low risk, modest improvement)

**Rationale**: Fix the biggest problems without restructuring. Keep existing stage boundaries.

| Change | What | Why |
|--------|------|-----|
| A-1 | Make QueryStage accept `Position` directly instead of re-parsing SGF | Eliminates P-3.1 (double parsing) |
| A-2 | Formalize solve-paths as a proper stage (`SolvePathStage`) with StageRunner wrapping | Gives timing/error-policy to the most complex dispatch |
| A-3 | Apply frame to position BEFORE passing to RefutationStage | Fixes P-5.1 (unframed refutation queries) |
| A-4 | Extract curated_wrongs + nearby_moves computation to a utility called at end of ParseStage | Fixes S-4 SRP for these unrelated concerns |

**Resulting flow:**
```
ParseStage → SolvePathStage → QueryStage → ValidationStage → RefutationStage → DifficultyStage → AssemblyStage → TeachingStage
```
(Same order, just cleaner boundaries)

### 8.2 Option B: Split Engine-Dependent vs Pure Stages (Medium risk, better clarity)

**Rationale**: Separate stages that make engine calls from pure computation stages. This makes it clear where latency lives and enables potential parallelization.

| New Stage | From | What |
|-----------|------|------|
| `ParseStage` | S-1 | Unchanged |
| `SolvePathStage` | S-2 | Formalized with error policy |
| `FrameAndQueryStage` | S-3 (renamed) | Position → crop → frame → query → analyze → uncrop |
| `ValidationStage` | S-4 (split) | Correct-move validation only (no tree validation) |
| `TreeValidationStage` | S-4 (split) | Deep tree validation (engine calls) |
| `RefutationStage` | S-5 | Uses framed position from FrameAndQueryStage |
| `ScoringStage` | S-6 + S-7 merged | Difficulty + Assembly (both pure computation) |
| `TechniqueStage` | S-8 (split) | `classify_techniques()` only — isolate weakest link |
| `TeachingStage` | S-8 (split) | Comments + hints |
| `SgfWritebackStage` | S-8 (split) | `enrich_sgf()` — final output |

```
ParseStage → SolvePathStage → FrameAndQueryStage → ValidationStage → TreeValidationStage → RefutationStage → ScoringStage → TechniqueStage → TeachingStage → SgfWritebackStage
```

### 8.3 Option C: Fundamental Reshape — Annotate-Then-Assemble (Higher risk, best architecture)

**Rationale**: Current pipeline is "run analysis → validate → refute → score → assemble → teach". This is inherited from the original monolith. A cleaner architecture:

1. **Parse & Prepare** — Parse SGF, extract position, determine solve path, compute frame
2. **Analyze** — Run KataGo (one query, unified frame for ALL downstream use)
3. **Annotate** — Run all independent annotators in parallel or sequence:
   - Correct-move validation (reads analysis)
   - Tree validation (reads analysis + solution tree)
   - Refutation generation (reads analysis + position)
   - Technique classification (reads analysis + position + solution tree)
4. **Score** — Difficulty estimation (reads all annotations)
5. **Assemble** — Wire AiAnalysisResult
6. **Emit** — Teaching comments, hints, SGF writeback

```
PrepareStage → AnalyzeStage → [ValidationAnnotator, RefutationAnnotator, TechniqueAnnotator] → ScoreStage → AssembleStage → EmitStage
```

**Key insight**: Validation, refutation, and technique classification are INDEPENDENT — they all read from the same analysis response and don't depend on each other. Currently they run sequentially because of stage ordering, but they could be parallelized.

**Problem**: Refutation queries currently make ADDITIONAL engine calls per candidate. In Option C, these would need to be batched or the "Annotate" phase would need sub-stages with engine access.

---

## 9. Specific Recommendations

### 9.1 Planner-Ready Bullets

| Priority | Recommendation | Effort | Risk |
|----------|---------------|--------|------|
| **R-1** | **Fix P-5.1: Framed position for refutation queries.** RefutationStage currently uses raw `ctx.position`. Pass `ctx.cropped.position` (or framed position) so refutation queries match the main analysis. This is the highest-impact correctness fix. | Small | Low |
| **R-2** | **Fix P-3.1: Eliminate double-parsing in QueryStage.** Change `build_query_from_sgf()` to accept a `Position` object, or add `build_query_from_parsed()` that takes `(position, config, ko_type)`. This eliminates redundant SGF parsing. | Small | Low |
| **R-3** | **Formalize solve-paths as a stage.** Wrap `solve_paths` in a `SolvePathStage` class implementing `EnrichmentStage` protocol. This gives it timing/notify/error-policy and removes the dual-state (state + ctx) problem. | Medium | Low |
| **R-4** | **Isolate technique classification.** Move `classify_techniques()` out of TeachingStage into its own `TechniqueStage`. This separates the weakest link (6/28 tags detected, heuristic quality) from the well-functioning teaching system. Enables focused iteration on technique detection without touching teaching code. | Small | Low |
| **R-5** | **Build board-state technique detectors.** Wire `liberty.py` (already exists: group liberties, eye detection) into technique classifier. Add detectors for: liberty-shortage (comparing liberties), capture-race (group liberty comparison), nakade (interior vital point + eye count), double-atari (checking two groups in atari after move). This addresses the 64% detection gap. | Large | Medium |
| **R-6** | **Unify query paths.** The three solve paths and QueryStage use different query-building entry points. Create a single `prepare_enrichment_query(position, config, ko_type, crop)` function that all paths call. Position-only path passes `crop=False`, QueryStage passes `crop=True`. Both get frame + komi + region + ko rules. | Medium | Medium |

### 9.2 What NOT to Change

| Component | Reason to Keep |
|-----------|---------------|
| StageRunner pattern | Clean, minimal, correct — timing/error/notify wrapping works well |
| PipelineContext dataclass | Typed, documented — good contract between stages |
| Validation dispatch (7 validators) | Config-driven, tag-aware — well-tested |
| Difficulty formula (4 components) | Config-driven weights, elo gate — production-ready |
| GP frame (`tsumego_frame_gp.py`) | Battle-tested KaTrain port — working |
| Single engine manager | Escalation logic is clean and correct |

---

## 10. Open Questions for Planner

| Q-ID | Question | Options | Recommended | Status |
|------|----------|---------|-------------|--------|
| Q1 | Should solve-path dispatch move BEFORE or AFTER the main KataGo query? Currently before (builds own queries). If after, position-only path would use the same analysis as downstream stages. | A: Before (current), B: After (unified analysis), C: Hybrid (standard positions use after, position-only stays before) | C: Hybrid — position-only genuinely needs its own analysis-then-tree-build flow, but has-solution and standard paths could share the QueryStage analysis | ❌ pending |
| Q2 | How aggressive should the TeachingStage split be? | A: Keep as-is (4 things in 1 stage), B: Split to 2 (technique + everything else), C: Split to 3 (technique + teaching + SGF writeback) | B: Split to 2 — technique isolation gives most value for least disruption | ❌ pending |
| Q3 | Should Option C (Annotate-Then-Assemble) be pursued now or deferred? | A: Option A (minimal cleanup) first, then C later, B: Jump to C directly | A: Do Option A first — it's low-risk and addresses the top 3 problems. Option C is a bigger redesign that should be validated after A is stable | ❌ pending |
| Q4 | Should refutation queries use the full framed board or just puzzle-region restriction? | A: Full framed board (match main analysis exactly), B: Puzzle region restriction only (no frame), C: Framed + puzzle region | A: Full framed board — consistency is more important than theoretical purity | ❌ pending |

---

## 11. Confidence & Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 90 |
| `post_research_risk_level` | medium |

**Confidence justification**: Read every stage file, every analyzer module, the full config tags, and the existing research. Data dependency matrix is complete. Gap analysis is comprehensive (28 tags enumerated). The two highest-severity cross-stage bugs (P-5.1, F-X.1) are well-characterized.

**Risk justification**: Medium because the solve-paths / QueryStage query divergence (F-X.1) and unframed refutation queries (P-5.1) are production-affecting correctness issues. The technique detection gap (64% undetected) limits enrichment quality but doesn't cause incorrect results.

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260314-1400-feature-enrichment-lab-v2/
artifact: 15-research.md
top_recommendations:
  - R-1: Fix refutation queries to use framed position (correctness bug)
  - R-2: Eliminate double-parsing in QueryStage
  - R-3: Formalize solve-paths as a proper stage
  - R-4: Isolate technique classification from TeachingStage
  - R-5: Build board-state technique detectors (address 64% detection gap)
  - R-6: Unify query paths (single prepare function)
open_questions:
  - Q1: Solve-path dispatch timing (before/after unified query)
  - Q2: TeachingStage split granularity
  - Q3: Option A (cleanup) vs Option C (annotate-then-assemble)
  - Q4: Refutation query framing strategy
post_research_confidence_score: 90
post_research_risk_level: medium
```
