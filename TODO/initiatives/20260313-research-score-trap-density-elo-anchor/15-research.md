# Research Brief: Score-Based Trap Density & Elo-Anchor Validation

**Last Updated**: 2026-03-13
**Initiative**: `20260313-research-score-trap-density-elo-anchor`
**Status**: Research complete

---

## 1. Research Questions & Boundaries

### RQ-1: Score-based trap density
Can we replace the current `|winrate_delta| × policy` proxy in `_compute_trap_density()` with actual `scoreLead` / `pointsLost` per candidate move for a more calibrated trap density signal?

### RQ-2: Elo-anchor validation
Can we add an Elo-anchor validation layer that maps the correct move's policy prior to an external Elo lookup table, cross-checking the config-driven `score_to_level` mapping?

### Boundaries
- Research only covers `tools/puzzle-enrichment-lab/` (enrichment lab tool, NOT `backend/puzzle_manager/`)
- No runtime code changes proposed
- Focused on data availability; architecture and implementation are planner-scoped

---

## 2. Internal Code Evidence

### 2.1 Current `_compute_trap_density()` — Full Formula

| ID  | File | Lines |
|-----|------|-------|
| R-1 | [analyzers/estimate_difficulty.py](tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py#L298-L340) | `_compute_trap_density()` |

**Current formula:**
```
trap_density = Σ(|winrate_delta_i| × wrong_move_policy_i) / Σ(wrong_move_policy_i)
```

Where for each refutation `ref`:
- `points_lost = abs(ref.winrate_delta)` — approximates pointsLost via winrate delta
- `prior = ref.wrong_move_policy` — how tempting the NN thinks the wrong move is

**Explicitly documented gap (line 305-306):**
> "pointsLost is approximated by |winrate_delta| (how much the wrong move loses)"

The docstring itself acknowledges this is an approximation. True `pointsLost` would use `scoreLead` differentials.

### 2.2 Data Source for `winrate_delta` and `wrong_move_policy`

| ID  | File | Fields |
|-----|------|--------|
| R-2 | [models/refutation_result.py](tools/puzzle-enrichment-lab/models/refutation_result.py#L1-L45) | `Refutation` model |
| R-3 | [analyzers/generate_refutations.py](tools/puzzle-enrichment-lab/analyzers/generate_refutations.py#L41-L100) | `_enrich_curated_policy()` |

**`Refutation` model fields:**
- `wrong_move_policy: float` — NN policy prior for the wrong move
- `winrate_delta: float` — drop from initial winrate (negative = bad)
- `winrate_after_wrong: float` — puzzle-player's winrate after wrong move + response

**Missing from `Refutation` model:**
- ❌ No `score_lead` field
- ❌ No `points_lost` field (only approximated via `|winrate_delta|`)

**However**, the upstream data **does contain `score_lead`** per candidate move:

| ID  | File | Evidence |
|-----|------|----------|
| R-4 | [models/analysis_response.py](tools/puzzle-enrichment-lab/models/analysis_response.py#L7-L10) | `MoveAnalysis.score_lead: float = 0.0` |
| R-5 | [models/solve_result.py](tools/puzzle-enrichment-lab/models/solve_result.py#L171-L175) | `MoveClassification.score_lead: float = 0.0` |
| R-6 | [analyzers/solve_position.py](tools/puzzle-enrichment-lab/analyzers/solve_position.py#L108-L113) | `classify_move_quality()` receives `score_lead` param (S1-G15) |

**Key finding:** `score_lead` is available on every `MoveAnalysis` from KataGo and flows into `MoveClassification`, but is **never propagated to the `Refutation` model**. The refutation pipeline in `generate_refutations.py` uses `winrate` but drops `score_lead`. The enrichment function `_enrich_curated_policy()` (R-3) enriches winrate but not score_lead.

### 2.3 `bridge.py` Already Computes `pointsLost`

| ID  | File | Lines |
|-----|------|-------|
| R-7 | [bridge.py](tools/puzzle-enrichment-lab/bridge.py#L230-L251) | GUI bridge response builder |

The bridge.py (GUI integration layer) computes `pointsLost` as `abs(top_score - mi.score_lead)` for the JS client. This proves `score_lead` is available from the engine response — it just doesn't flow into the refutation model.

### 2.4 Difficulty Estimation Pipeline (Full)

| ID  | File | Role |
|-----|------|------|
| R-8 | [analyzers/estimate_difficulty.py](tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py#L1-L380) | Composite difficulty formula |
| R-9 | [analyzers/stages/difficulty_stage.py](tools/puzzle-enrichment-lab/analyzers/stages/difficulty_stage.py#L1-L85) | Pipeline stage orchestration |
| R-10 | [config/katago-enrichment.json (L45-101)](config/katago-enrichment.json#L45) | Config-driven thresholds & weights |

**Composite formula (4 components, sum=100):**

| Component | Weight | Source |
|-----------|--------|--------|
| `policy_component` = `(1.0 - policy_prior) × w.policy_rank` | 15% | KataGo NN policy |
| `visits_component` = `log2(visits/base) / log2(max/base) × w.visits_to_solve` | 15% | Per-move visits |
| `trap_component` = `trap_density × w.trap_density` | 25% | Refutation model |
| `structural_component` = `blend(depth, branches, candidates, refutations, proof_depth) × w.structural` | 45% | SGF tree + KM search |

**Score → Level mapping** (`_score_to_level`): 9 thresholds in `katago-enrichment.json`:
`[0,40]→novice, (40,50]→beginner, ... (96,100]→expert`

**Policy → Level mapping** (`_policy_to_level`, Tier 0.5 fallback): 9 thresholds:
`[0.50,∞)→novice, [0.30,0.50)→beginner, ... [0.0,0.005)→expert`

### 2.5 Observability & Logging Infrastructure

| ID  | File | Purpose |
|-----|------|---------|
| R-11 | [log_config.py](tools/puzzle-enrichment-lab/log_config.py#L1-L100) | Structured JSON logging (dual: stderr + rotating file) |
| R-12 | [analyzers/observability.py](tools/puzzle-enrichment-lab/analyzers/observability.py#L1-L190) | `BatchSummaryAccumulator` + `DisagreementSink` (JSONL) |

**Logging architecture:**
- **Structured JSON formatter** (`_StructuredJsonFormatter`): every record is `{ts, level, logger, run_id, msg, ...extras}`
- **Dual output**: stderr + rotating file in `.lab-runtime/logs/`
- **Lab namespace filter**: only enrichment-lab modules pass (`analyzers.*`, `engine.*`, `models.*`, `config.*`, etc.)
- **Human-readable mode**: `LOG_FORMAT=human` for interactive console
- **Per-run log files**: configurable `_per_run_files` flag
- **Workspace-relative paths**: configurable `_use_relative_paths`

**Batch observability:**
- `BatchSummaryAccumulator`: per-puzzle outcomes → `BatchSummary`
- `DisagreementSink`: JSONL records for AI-vs-human disagreements
- Per-collection disagreement rate monitoring with WARNING threshold (S4-G10)

### 2.6 Data Model — Full Field Inventory

| ID  | File | Key for Research |
|-----|------|-----------------|
| R-13 | [models/ai_analysis_result.py](tools/puzzle-enrichment-lab/models/ai_analysis_result.py#L1-L270) | Complete output schema |
| R-14 | [models/difficulty_estimate.py](tools/puzzle-enrichment-lab/models/difficulty_estimate.py#L1-L45) | Difficulty estimate fields |
| R-15 | [models/analysis_response.py](tools/puzzle-enrichment-lab/models/analysis_response.py#L1-L50) | KataGo response fields |

**`AiAnalysisResult.DifficultySnapshot` fields:**
- `policy_prior_correct: float` ✅ Available for Elo lookup
- `visits_to_solve: int` ✅
- `trap_density: float` ✅ Current proxy
- `composite_score: float` ✅ Raw 0-100 score
- `suggested_level / suggested_level_id` ✅ Score → level output
- `confidence: str` ✅

**`MoveAnalysis` (from KataGo) fields:**
- `winrate: float` ✅ per move
- `score_lead: float` ✅ per move — **this is the missing data for score-based trap**
- `policy_prior: float` ✅ per move
- `visits: int` ✅ per move
- `pv: list[str]` ✅ principal variation

### 2.7 Test Coverage for Difficulty Estimation

| ID  | Test File | Covers |
|-----|-----------|--------|
| R-16 | [tests/test_difficulty.py](tools/puzzle-enrichment-lab/tests/test_difficulty.py) | Policy-only mapping (A.3.1), composite formula (A.3.2), trap density, visits, config compliance, proof-depth signal (KM-04) |
| R-17 | [tests/test_calibration.py](tools/puzzle-enrichment-lab/tests/test_calibration.py) | End-to-end calibration vs Cho Chikun reference collections (slow, requires KataGo) |
| R-18 | [tests/test_ai_solve_calibration.py](tools/puzzle-enrichment-lab/tests/test_ai_solve_calibration.py) | AI-Solve threshold constraints, fixture integrity, classification consistency |

**`test_difficulty.py` coverage breakdown:**
- `TestPolicyOnlyEasyPuzzle` / `TestPolicyOnlyHardPuzzle` — Tier 0.5 boundary mapping
- `TestPolicyOnlyMiaiMaxPrior` — miai max(priors) not sum
- `TestPolicyOnlyLevelSlugValid` / `TestPolicyOnlyLevelIdsFromConfig` — config compliance
- `TestVisitsToSolveEasy` / `TestVisitsToSolveHard` — visits multiplier when disagree
- `TestTrapDensityNoTraps` / `TestTrapDensityManyTraps` — trap density bounds
- `TestCompositeScoreMonotonic` — easy < medium < hard
- `TestCompositeWeightsFromConfig` — weight validation (PUCT < 40%, structural > 35%)
- `TestProofDepthSignal` (4 tests) — KM-04 proof-depth affects/caps difficulty

---

## 3. External References

| ID  | Reference | Relevance |
|-----|-----------|-----------|
| R-19 | KaTrain trap density formula | Current implementation cites "KaTrain-style trap density". KaTrain uses `Σ(pointsLost × prior) / Σ(prior)` where `pointsLost` is actual score-based, not winrate-based |
| R-20 | KataGo analysis response format | `scoreLeadByDelta` / `scoreLead` are per-move fields natively available in analysis JSON; `pointsLost` must be derived as `bestScoreLead - moveScoreLead` |
| R-21 | Elo-policy empirical mapping (KataGo network calibration) | Various Go AI papers map NN policy priors to approximate Elo ranges. KataGo's b18/b40 models have different calibration curves |
| R-22 | No existing `katago-enrichment.schema.json` | config/schemas/ does NOT contain a schema for katago-enrichment.json — validation is via Pydantic models in config.py only |

---

## 4. Candidate Adaptations for Yen-Go

### Adaptation A: Score-Based Trap Density (Feature 1)

**What changes:**
1. Add `score_lead: float` field to `Refutation` model
2. Propagate `score_lead` from `MoveAnalysis` → `Refutation` in `generate_refutations.py`
3. Update `_enrich_curated_policy()` to also enrich `score_lead` from initial analysis
4. Modify `_compute_trap_density()` to use `abs(root_score - ref.score_lead)` instead of `abs(ref.winrate_delta)`
5. Config: add `trap_density_mode: "winrate" | "score"` to allow A/B comparison

**Data availability:** ✅ `score_lead` is available on `MoveAnalysis` from KataGo. Bridge.py already computes `pointsLost = abs(top_score - mi.score_lead)`. The data exists — it just doesn't flow to `Refutation`.

**Scope:** Level 2 (1-2 files logic, ~60 lines, explicit behavior change)

### Adaptation B: Elo-Anchor Validation (Feature 2)

**What changes:**
1. Add Elo lookup table to `config/katago-enrichment.json` mapping policy-prior bands to approximate Elo ranges
2. Add `elo_anchor_check()` function that compares `estimated_level_id` against Elo-derived level
3. Emit observability warning when anchor diverges > N steps
4. Add `elo_range` field to `DifficultySnapshot` (informational, not gating)

**Data availability:**
- ✅ `policy_prior_correct` is in `AiAnalysisResult.DifficultySnapshot`
- ✅ `correct_move_policy` is on `CorrectMoveResult` (validation stage output)
- ✅ Observability infrastructure (structured logging + disagreement sink) exists
- ⚠️ Elo-policy mapping is model-dependent (b18 vs b40 calibration differs)

**Scope:** Level 2-3 (config + 1 new function + observability hook, ~80 lines)

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| ID  | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| R-23 | Score-based trap density changes calibration curve — all `score_to_level_thresholds` may need re-tuning | Medium | Add config flag for A/B mode; run calibration suite before switching |
| R-24 | Elo-policy mapping is model-specific (b18 ≠ b40) — table must be versioned per model | Medium | Key Elo table by `EngineSnapshot.model` |
| R-25 | `score_lead` sign convention differs between puzzle player perspectives — must normalize | Low | Follow existing `normalize_winrate()` pattern; `bridge.py` already handles this |
| R-26 | Curated branches (no KataGo analysis) will still have `score_lead=0` — sentinel value needed | Low | Mirror existing sentinel pattern from `DifficultySnapshot` (D3: -1.0 = unavailable) |
| R-27 | No `katago-enrichment.schema.json` exists — adding new config fields has no JSON Schema validation | Info | Pydantic models in `config.py` provide runtime validation; schema file is optional |
| R-28 | KaTrain's actual `pointsLost` uses `scoreLead` from self-play, not just single-position analysis | Low | Our per-candidate confirmation queries (S1-G16) already provide precise per-move `score_lead` — sufficient quality |

---

## 6. Planner Recommendations

1. **Feature 1 (Score-Based Trap Density):** Implement as a config-togglable enhancement. Add `score_lead` to `Refutation` model, propagate from `MoveAnalysis` in `generate_refutations.py`, and add `trap_density_mode` config key for A/B calibration. The data pipeline already has `score_lead` at the `MoveAnalysis` level — it's a ~60-line threading exercise. Run `test_calibration.py` before/after to validate calibration stability.

2. **Feature 2 (Elo-Anchor Validation):** Implement as an observability-only check initially (WARNING log, not gating). The correct-move policy prior is already surfaced in `DifficultySnapshot.policy_prior_correct`. Add a simple lookup table to `katago-enrichment.json` keyed by model name, with policy-prior → approximate Elo bands. This is informational and non-blocking — zero risk to production scoring.

3. **Config schema gap:** Consider creating `config/schemas/katago-enrichment.schema.json` to formalize the growing config surface (currently ~900 lines in config.py). Not blocking, but reduces drift risk as features expand.

4. **Test strategy:** Both features should reuse existing calibration infrastructure (`test_difficulty.py` + `test_calibration.py`). Score-based trap density needs regression tests against the monotonicity and bounds tests. Elo-anchor needs a new test class verifying lookup table coverage and warning emission.

---

## 7. Confidence & Risk Update

```
post_research_confidence_score: 92
post_research_risk_level: low
```

**Rationale:** Both features have clear data availability, well-defined insertion points, and existing test infrastructure. The main risk is calibration threshold re-tuning for Feature 1, which is mitigated by the A/B config toggle approach. Feature 2 is pure observability — zero-risk to scoring.

---

## Handoff

| Key | Value |
|-----|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260313-research-score-trap-density-elo-anchor/` |
| `artifact` | `15-research.md` |
| `top_recommendations` | 1. Thread `score_lead` from `MoveAnalysis` → `Refutation` (Feature 1); 2. Add observability-only Elo-anchor lookup (Feature 2); 3. Consider `katago-enrichment.schema.json`; 4. Reuse calibration test suite |
| `open_questions` | (none — all data availability confirmed) |
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |
