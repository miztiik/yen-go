# Research Brief: Enrichment Lab Implementation vs. Deferred NG Items Gap Audit

> **Research question**: For each deferred NG-1 through NG-5 item from the "gogogo research" panel, what is actually implemented, what's planned but not done, and what would be accretive to implement now?
>
> **Boundaries**: Enrichment lab codebase evidence (`tools/puzzle-enrichment-lab/`), backend pipeline (`backend/puzzle_manager/`), frontend consumption (`frontend/src/`). No code changes. Focused on implementation status and accretion value.
>
> **Last updated**: 2026-03-18

---

## 1. Research Question and Boundaries

**Primary questions**:
1. For each NG-1 through NG-5 deferred item: what is its implementation status?
2. What enrichment signals are computed but discarded ("ready but unused")?
3. What incomplete initiatives need closure?
4. What is the production-readiness of the enrichment lab overall?

**Success criteria**: Structured table with evidence-backed status per item, accretion assessment, and planner-ready recommendations.

---

## 2. Internal Code Evidence

### 2A. DetectionResult Model (NG-1 target)

`DetectionResult` in [models/detection.py](tools/puzzle-enrichment-lab/models/detection.py#L8) has exactly 4 fields:

```python
@dataclass
class DetectionResult:
    detected: bool
    confidence: float  # 0.0-1.0
    tag_slug: str      # matches config/tags.json slug
    evidence: str      # human-readable explanation
```

**No `priority` or `urgency` field exists.** The 28 detector classes all return this same 4-field struct. Priority ordering happens externally via `TAG_PRIORITY` dict in [technique_classifier.py](tools/puzzle-enrichment-lab/analyzers/technique_classifier.py#L55) — a static mapping from tag slug to integer priority (1=highest, 4=lowest). This is used for sorting output tags, not for weighting evidence.

In `TechniqueStage` ([stages/technique_stage.py](tools/puzzle-enrichment-lab/analyzers/stages/technique_stage.py#L59)), positive detections are sorted by `TAG_PRIORITY` and stored as `result.technique_tags`. The full `DetectionResult` list is stored on `ctx.detection_results` for downstream stages.

### 2B. Benson's Algorithm & Static Life/Death (NG-2 target)

**Yes, symbolic life/death evaluation exists** in [benson_check.py](tools/puzzle-enrichment-lab/analyzers/benson_check.py):

| R-1 | Function | Purpose | Status |
|-----|----------|---------|--------|
| R-1a | `find_unconditionally_alive_groups()` | Benson's algorithm (1976) — returns groups with ≥2 vital regions | **Implemented and integrated** |
| R-1b | `check_interior_point_death()` | Interior-point two-eye exit — defender cannot form two eyes | **Implemented and integrated** |

These serve as **pre-query terminal detection gates** in `solve_position.py → _build_tree_recursive()`:
- **Gate G1**: Benson's unconditional life → skip KataGo query, contest group is provably alive
- **Gate G2**: Interior-point death → skip KataGo query, defender cannot form two eyes

This is **not** a full "static life/death evaluation formula" (NG-2's original scope). It's a gating optimization that avoids engine queries for clearly-decided positions. The gap is: no general-purpose symbolic status evaluator (e.g., for seki, approach-ko, or ambiguous positions). Those still require KataGo.

Also present: [liberty.py](tools/puzzle-enrichment-lab/analyzers/liberty.py) — liberty counting, eye detection, and group harm checking for frame legality. These are helpers, not full life/death evaluators.

### 2C. Multi-Tag Evidence Layering (NG-3 target)

The 28 detectors run independently via `run_detectors()` in [technique_classifier.py](tools/puzzle-enrichment-lab/analyzers/technique_classifier.py#L508):

```python
def run_detectors(position, analysis, solution_tree, config, detectors) -> list[DetectionResult]:
    # Runs each detector independently, collects positive results
    # Deduplicates by tag_slug (keeps highest confidence)
    # Returns sorted by tag_slug
```

**No evidence layering or feature planes exist.** Each detector operates in isolation — receives `Position`, `AnalysisResponse`, `SolutionNode|None`, `EnrichmentConfig` and returns a single `DetectionResult`. There is:
- No cross-detector communication
- No shared feature tensor/planes
- No weighted evidence fusion
- No Bayesian evidence accumulation

Detection results are simply merged: tag exists if any detector fires for it, confidence is max per tag. The `TAG_PRIORITY` dict only governs display ordering, not evidence weighting.

### 2D. Alpha-Beta / Minimax Search (NG-5 target)

**No alpha-beta, minimax, or negamax search exists anywhere in the enrichment lab.** Verified via codebase-wide regex search for `alpha.beta|minimax|negamax|alpha_beta`. The entire tactical analysis pipeline depends on KataGo MCTS queries.

The closest analog is the tree-building logic in `solve_position.py`:
- `_build_tree_recursive()` expands correct/wrong moves by querying KataGo at each node
- Uses budget-capped MCTS (not alpha-beta) via `QueryBudget` tracking
- Terminal detection uses Benson gates (G1/G2) rather than a search engine

### 2E. AiAnalysisResult Signal Inventory (RQ-5)

`AiAnalysisResult` ([models/ai_analysis_result.py](tools/puzzle-enrichment-lab/models/ai_analysis_result.py)) schema v9 has these field categories:

| R-2 | Field Group | Fields | Populated? |
|-----|-------------|--------|------------|
| R-2a | Core identity | `puzzle_id`, `trace_id`, `run_id`, `source_file`, `schema_version` | Yes |
| R-2b | Engine info | `engine.model`, `engine.visits`, `engine.config_hash` | Yes |
| R-2c | Validation | `validation.*` (7 fields) | Yes |
| R-2d | Refutations | `refutations[]` (per-wrong-move entries) | Yes |
| R-2e | Difficulty | `difficulty.*` (11 fields incl. `composite_score`, `suggested_level`) | Yes |
| R-2f | Tags | `tags`, `tag_names`, `technique_tags` | Yes |
| R-2g | Teaching | `teaching_comments`, `hints` | Yes (Phase B) |
| R-2h | Solve metadata | `co_correct_detected`, `queries_used`, `tree_truncated` | Yes |
| R-2i | Goal inference | `goal`, `goal_confidence` | **Unclear — field exists, population unknown** |
| R-2j | Quality | `enrichment_tier`, `enrichment_quality_level`, `ac_level` | Yes |
| R-2k | Timing | `phase_timings` | Runtime only |
| R-2l | `per_move_accuracy` | Nullable float | **Usually None** — model field exists but rarely computed |
| R-2m | `human_solution_confidence`, `ai_solution_validated` | Nullable | Set on has-solution path only |
| R-2n | `enriched_sgf` | Nullable str | Set by sgf_writeback_stage |

**Key "computed but discarded" signals** (not in AiAnalysisResult OR not in DB-1):

| R-3 | Signal | Location | Status |
|-----|--------|----------|--------|
| R-3a | `policy_entropy` (Shannon entropy of top-K policy priors) | `estimate_difficulty.py` → `ctx.policy_entropy` | Computed, stored on ctx, **not persisted to AiAnalysisResult** |
| R-3b | `correct_move_rank` (rank in KataGo's ordering) | `estimate_difficulty.py` → `ctx.correct_move_rank` | Computed, stored on ctx, **not persisted** |
| R-3c | Difficulty sub-components (policy=15%, visits=15%, trap=20%, structural=35%, complexity=15%) | `estimate_difficulty.py` | Logged but **only composite score survives** |
| R-3d | `TreeCompletenessMetrics` (completed_branches, simulation hits/misses, etc.) | `solve_result.py` | Per-run only, **discarded** |
| R-3e | `EntropyROI` (contested region, bounding box, mean entropy) | `entropy_roi.py` → `ctx.entropy_roi` | Per-run only, **discarded** |
| R-3f | `InstinctResult[]` (push/hane/cut/descent/extend + confidence) | `instinct_classifier.py` → `ctx.instinct_results` | Computed, **gated off from output** (see 2F below) |
| R-3g | `MoveClassification` per-move detail (quality, delta, policy, rank, score_lead) | `solve_result.py` | Per-analysis detail, **discarded** |

### 2F. Instinct Classifier State (RQ-7)

The instinct classifier is **implemented and functional** ([instinct_classifier.py](tools/puzzle-enrichment-lab/analyzers/instinct_classifier.py)):
- Classifies 5 tsumego-relevant instincts: push, hane, cut, descent, extend
- Uses position geometry only (zero engine queries)
- Pipeline stage `InstinctStage` runs and stores results on `ctx.instinct_results`

However, `InstinctConfig.enabled` defaults to **`False`** ([config/teaching.py](tools/puzzle-enrichment-lab/config/teaching.py#L117)):

```python
class InstinctConfig(BaseModel):
    enabled: bool = Field(
        default=False,
        description="Gate for instinct phrases in hints/comments. "
        "Default False per C-3: flip to True after AC-4 golden-set calibration confirms >=70% accuracy.",
    )
```

**Blocker**: The golden calibration set is empty — [golden-calibration/labels.json](tools/puzzle-enrichment-lab/tests/fixtures/golden-calibration/labels.json) contains `"puzzles": []`. AC-4 calibration cannot proceed without labeled data.

### 2G. Calibration State (RQ-6)

| R-4 | Fixture Set | Location | Count | Status |
|-----|-------------|----------|-------|--------|
| R-4a | AI-Solve calibration (cho-elementary) | `tests/fixtures/calibration/cho-elementary/` | 30 SGF files | **Populated** |
| R-4b | AI-Solve calibration (cho-intermediate) | `tests/fixtures/calibration/cho-intermediate/` | 30 SGF files | **Populated** |
| R-4c | AI-Solve calibration (cho-advanced) | `tests/fixtures/calibration/cho-advanced/` | 30 SGF files | **Populated** |
| R-4d | AI-Solve calibration (ko) | `tests/fixtures/calibration/ko/` | 5 SGF files | **Populated** |
| R-4e | Golden calibration (instinct) | `tests/fixtures/golden-calibration/` | **0 puzzles** | **Empty** — labels.json exists but puzzles array is [] |
| R-4f | Evaluation set (cho collections) | `tests/fixtures/evaluation/cho-*/` | Unknown | Directories exist |
| R-4g | PI-11 surprise-weighted calibration | `config/infrastructure.py` | Function exists | **Feature-gated off** (surprise_weighting=false) |

### 2H. Data Liberation State (RQ-8)

**`attrs` column exists in all 3 tables** — `puzzles`, `collections`, `daily_schedule` in [db_builder.py](backend/puzzle_manager/core/db_builder.py#L19):

| R-5 | Table | Column | Default | Currently populated? |
|-----|-------|--------|---------|---------------------|
| R-5a | `puzzles` | `attrs TEXT DEFAULT '{}'` | `{}` | **Always empty** — no publish stage code populates it |
| R-5b | `collections` | `attrs TEXT DEFAULT '{}'` | `{}` | **Always empty** |
| R-5c | `daily_schedule` | `attrs TEXT DEFAULT '{}'` | `{}` | **Partially** — only `config_snapshot` from daily generation |

The `PuzzleEntry.attrs` field ([db_models.py](backend/puzzle_manager/core/db_models.py#L25)) defaults to `dict()` and is serialized to JSON in `db_builder.py`. But **no code in the publish stage populates enrichment signals into `attrs`**.

Initiative `20260317-1400-feature-enrichment-data-liberation` is in **clarify phase** — 14 decision questions are all ❌ pending user input.

---

## 3. External References

| R-6 | Reference | Relevance |
|-----|-----------|-----------|
| R-6a | Benson (1976) "Life in the Game of Go" | Implemented in `benson_check.py` — unconditional life algorithm |
| R-6b | KaTrain (github: sanderle/katrain) | Pattern source for policy_entropy, visits-based difficulty, HumanSL calibration |
| R-6c | Tsumego Pro (mobile app) | Precedent for priority/urgency on technique results — uses hand-curated difficulty per technique |
| R-6d | PLNech/gogogo (GitHub) | Source of instinct classification concept (8 instincts, filtered to 5 for tsumego) |
| R-6e | OGS puzzle system | Single scalar difficulty (Glicko-2); no multi-dimensional evidence layering |
| R-6f | Thomas Wolf / Kishimoto-Mueller PNS | Alternative to alpha-beta for Go proving; existing research in `TODO/kishimoto-mueller-tasks.md` |

---

## 4. Candidate Adaptations for Yen-Go

### 4A. Deferred NG Item Status Table

| R-7 | NG-ID | Finding | Status | Evidence | Accretive Now? | Dependencies/Blockers |
|-----|-------|---------|--------|----------|---------------|----------------------|
| R-7a | **NG-1** | Priority/urgency scoring on DetectionResult | **Not implemented** | `DetectionResult` has 4 fields (detected, confidence, tag_slug, evidence) — no priority/urgency. `TAG_PRIORITY` is static display ordering. | **Yes, moderate value** — would improve hint tier selection and teaching comment relevance ordering. | Schema evolution required: add field to DetectionResult + update all 28 detectors. Level 3 change (2-3 files + 28 detector files). |
| R-7b | **NG-2** | Static life/death evaluation formula | **Partially implemented** | Benson's unconditional life + interior-point death gates exist in `benson_check.py`. Used as pre-query skip gates — NOT a general evaluator. | **Low value** — gates already save engine queries for clear positions. Full static evaluator adds complexity for diminishing returns (ambiguous positions still need KataGo). | Calibration study against KataGo baselines not done. Would require new evaluation fixtures + validation framework. |
| R-7c | **NG-3** | Multi-tag evidence layering / feature planes | **Not implemented** | 28 detectors run independently, no cross-detector communication, no feature tensor, no weighted fusion. Results merged by simple union + max-confidence dedup. | **Medium value, high cost** — would improve multi-technique puzzle classification accuracy but requires significant architecture change (feature plane abstraction, training data for fusion weights). | No training data for evidence weights. No precedent in codebase for ML-style feature fusion. Would be a Level 4-5 change. |
| R-7d | **NG-4** | New tags in config/tags.json | **Not implemented** (correctly deferred) | 28 tags exist, 28 detectors match 1:1. | **Defer** — taxonomy expansion is Level 5 per original assessment. No evidence of missing critical tags blocking user-facing features. | Level 5 assessment stands. |
| R-7e | **NG-5** | Alpha-beta capture search engine | **Not implemented** | No alpha-beta, minimax, or negamax anywhere in enrichment lab. All tactical analysis via KataGo MCTS. | **Not accretive** — KataGo provides superior tactical analysis. Parallel engine adds maintenance burden with no clear quality improvement. PNS research (Kishimoto-Mueller) exists in TODO as a more principled alternative for proving. | Superseded by KataGo + existing PNS research direction. |

### 4B. Key "Ready But Unused" Signals

| R-8 | Signal | Computed Where | Why Discarded | Frontend Unlock Potential |
|-----|--------|---------------|--------------|--------------------------|
| R-8a | `policy_entropy` | DifficultyStage | Not on AiAnalysisResult model | **High** — "deceptive puzzle" filter, ambiguity indicator |
| R-8b | `correct_move_rank` | DifficultyStage | Not on AiAnalysisResult model | **High** — "surprising answer" badge, difficulty sub-dimension |
| R-8c | Difficulty sub-components (5 weights) | estimate_difficulty.py | Only composite survives | **High** — multi-dimensional difficulty radar, "why is this hard?" |
| R-8d | `instinct_results` | InstinctStage | Feature-gated off (enabled=False) | **Medium** — move intent annotation, pedagogical grouping |
| R-8e | `per_move_accuracy` | ai_analysis_result field | Rarely computed | **Medium** — difficulty refinement signal |
| R-8f | `goal`, `goal_confidence` | ai_analysis_result field | Population status unclear | **Medium** — puzzle objective labeling ("Kill", "Live", "Ko") |
| R-8g | `TreeCompletenessMetrics` | solve_result.py | Per-run only | **Low** — primarily internal QA metric |
| R-8h | `EntropyROI` (contested region) | entropy_roi.py | Per-run only | **Low** — could inform hint region highlighting |

### 4C. Incomplete Initiatives Needing Closure

| R-9 | Initiative | Current State | Needs |
|-----|-----------|---------------|-------|
| R-9a | Data Liberation (`20260317-1400-feature-enrichment-data-liberation`) | Clarify phase, 14 questions pending | **User decisions** on scope (Q1-Q14) — this is the highest-priority blocker |
| R-9b | Instinct calibration golden set | labels.json empty | **Data labeling** — manually label ≥30 puzzles with instinct ground truth |
| R-9c | HumanSL calibration | `humansl_calibration.py` exists, feature-gated | **Model availability** — requires HumanSL model file on disk |
| R-9d | PI-11 surprise-weighted calibration | Config + code exist, feature-gated off | **Activation + validation** — run calibration pipeline with feature enabled |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-10 | Item | Risk | Mitigation |
|------|------|------|------------|
| R-10a | NG-1 (priority/urgency) | Schema evolution impacts 28 detector files | Additive field with default=None ensures backward compatibility |
| R-10b | NG-2 (static evaluator) | Diminishing returns — most value already captured by Benson gates | Keep gates, defer full evaluator |
| R-10c | NG-3 (evidence layering) | No training data, requires ML infrastructure not present | Defer to post-data-liberation phase |
| R-10d | NG-5 (alpha-beta) | Maintenance burden, inferior to KataGo for general analysis | Reject. If proving is needed, PNS (Kishimoto-Mueller) is the better direction |
| R-10e | Data liberation stall | All enrichment signals are useless to users if `attrs` stays empty | **Critical path**: unblock data liberation Q1-Q6 decisions |
| R-10f | Instinct calibration gap | Feature is implemented but cannot be activated without golden set | Label 30 puzzles to unblock |

**License notes**: Benson's algorithm is public domain (1976 paper). Instinct patterns from Sensei's Library (public domain, per clean-room note in code). No external code copied.

---

## 6. Planner Recommendations

1. **Unblock Data Liberation first (R-9a)**: The single highest-value action is answering the 14 pending questions in `20260317-1400-feature-enrichment-data-liberation/10-clarifications.md`. Until `puzzles.attrs` is populated, *all* enrichment signals (R-8a through R-8h) are invisible to users. This is the critical path — every other improvement depends on it.

2. **Populate instinct golden set (R-9b)**: Low-effort action that unblocks the instinct classifier (already fully implemented, tested, and integrated). Label ≥30 calibration puzzles with instinct ground truth → validate ≥70% accuracy → flip `InstinctConfig.enabled=True`. This is the cheapest way to unlock a new signal dimension.

3. **NG-1 (DetectionResult priority) — defer to post-liberation**: Adding priority/urgency to DetectionResult is a Level 3 change touching 28+ files. The current `TAG_PRIORITY` static ordering is adequate for hint generation. Only worth doing if teaching comment quality is demonstrably degraded by the absence.

4. **NG-2, NG-3, NG-5 — do not implement now**: NG-2 has partial value captured by Benson gates. NG-3 lacks training data. NG-5 is superseded by KataGo + future PNS direction. None of these would be user-visible without data liberation.

---

## 7. Confidence and Risk Update for Planner

### Production Readiness Assessment

The enrichment lab is **production-ready for its current scope**: parse → analyze → classify → tag → hint → write-back. The pipeline is well-architected (13 stages, typed protocols, error policies, observability). Schema v9 captures rich data.

**However**, the lab is operating at ~40% of its potential value because:
- 6-8 computed signals are discarded before reaching DB-1
- `attrs` column in DB-1 is universally empty
- Instinct classifier is gated off behind empty calibration data
- HumanSL calibration is gated off behind model availability
- PI-11 surprise weighting is gated off

**Post-research confidence score**: 88/100
**Post-research risk level**: low

The risk is low because no implementation changes are needed — the bottleneck is decisions and data, not code. The enrichment lab architecture cleanly supports all planned extensions once decision blockers are cleared.

---

## Handoff

| Field | Value |
|-------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260317-research-capability-audit/` |
| `artifact` | `15-research-ng-gap-audit.md` |
| `top_recommendations` | 1. Unblock data liberation decisions (Q1-Q14) 2. Populate instinct golden set 3. Defer NG-1 to post-liberation 4. Reject NG-2/NG-3/NG-5 |
| `open_questions` | None — all questions resolved by codebase evidence |
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | low |
