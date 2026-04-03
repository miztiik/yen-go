# Plan — Enrichment Lab V2 (OPT-3: Phased with Integrated Entropy)

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Selected Option**: OPT-3  
**Last Updated**: 2026-03-14

---

## 1. Architecture Decisions

### 1.1 Pipeline Restructuring Selection (MH-4)

**Selected**: Research Option 8.2 (Split Engine-Dependent vs Pure Stages) with elements of 8.1 (Minimal Cleanup).

**Rationale**: Option 8.1 fixes the top bugs but doesn't improve stage clarity. Option 8.3 (Annotate-Then-Assemble) is architecturally superior but requires parallel annotator execution which adds complexity. Option 8.2 formalizes solve-paths, isolates technique classification, and separates engine-dependent from pure computation stages — the best balance of clarity and risk.

**Resulting stage flow (Phase 1 target)**:

```
ParseStage → SolvePathStage → AnalyzeStage → ValidationStage → RefutationStage 
    → DifficultyStage → AssemblyStage → TechniqueStage → TeachingStage → SgfWritebackStage
```

Key changes from current:
1. `SolvePathStage` — formalized with StageRunner wrapping (fixes P-2.2)
2. `AnalyzeStage` — renamed from QueryStage, accepts `Position` directly (fixes P-3.1 double-parsing)
3. `TechniqueStage` — split from TeachingStage (isolates weakest link)
4. `SgfWritebackStage` — split from TeachingStage (SRP)
5. All stages use same framed position for queries (fixes P-5.1, F-X.2)

### 1.2 Board Region Strategy

**Remove**: `CroppedPosition`, `crop_to_tight_board()`, `uncrop_response()`, `uncrop_gtp()`, all coordinate back-translation.

**Add** (in separate files per SRP/MH-2):
- `entropy_roi.py` — Ownership entropy computation per intersection. `H((ownership+1)/2)` formula. Identifies contested region as bounding box of high-entropy intersections. Returns `allowMoves` coordinate list.
- `frame_adapter.py` — Kept as-is (routes to GP frame)
- `tsumego_frame_gp.py` — Kept as-is (active, battle-tested)

**Flow**: Parse → Frame (on full board) → Analyze → Extract ownership → Compute entropy ROI → Use ROI for refutation queries and downstream analysis.

**Fallback chain**: Frame + ROI → ROI only (if frame fails) → `allowMoves` from stone bounding box (if entropy unavailable).

### 1.3 KataGo Query Configuration

**Visit tiers** (config-driven in `katago-enrichment.json`):

| Tier | Visits | Purpose | When Used |
|------|--------|---------|-----------|
| T0 | 50 | Policy snapshot | Technique pre-classification, quick reject |
| T1 | 500 | Standard analysis | Correct move validation, difficulty estimation |
| T2 | 2000 | Deep analysis | Refutation generation, complex positions |
| T3 | 5000 | Referee | Disagreement resolution, escalation endpoint |

**New query parameters**:
- `reportAnalysisWinratesAs: "BLACK"` — explicit, always
- `rootNumSymmetriesToSample: 4` (standard), `8` (referee)
- Refutation-specific `overrideSettings`:
  - `rootPolicyTemperature: 1.3` (explore more candidates)
  - `rootFpuReductionMax: 0` (don't penalize unexplored moves)
  - `wideRootNoise: 0.08` (add exploration noise)

**Lizgoban-inspired quality config** (all config-toggleable):

| Config Key | Default | Source | Purpose |
|---|---|---|---|
| `refutations.tenuki_rejection.enabled` | `true` | Lizgoban `natural_pv_p` | Toggle tenuki PV rejection |
| `refutations.tenuki_rejection.manhattan_threshold` | `4.0` | Lizgoban R-7 | Max distance between wrong move and KataGo response |
| `refutations.candidate_scoring.mode` | `"temperature"` | KaTrain `ScoreLossStrategy` | `"policy_only"` for legacy, `"temperature"` for weighted |
| `refutations.candidate_scoring.temperature` | `1.5` | KaTrain R-68 adapted | Higher = more exploration of high-loss moves |
| `frame.entropy_quality_check.enabled` | `true` | Lizgoban `eval_with_persona` | Toggle ownership-based frame validation |
| `frame.entropy_quality_check.variance_threshold` | `0.15` | User spec | Ownership variance for "unresolved" intersections |
| `validation.curated_pruning.enabled` | `true` | Lizgoban `weak_move_candidates` | Toggle curated path pruning |
| `validation.curated_pruning.min_visit_ratio` | `0.01` | Lizgoban R-8 adapted | Below this = broken line, skip |
| `validation.curated_pruning.trap_threshold` | `0.02` | User spec | Above this = tricky trap, keep |
| `validation.curated_pruning.min_depth` | `2` | Panel consensus | Never prune first-moves |

### 1.4 Technique Detection Architecture

**Approach**: Hybrid — board-state pattern detectors + PV/policy confirmation.

Each detector is a standalone function in its own file under `analyzers/detectors/`:
```
analyzers/detectors/
  __init__.py
  ladder_detector.py      — 3×3 pattern + recursive extension (clean-room from Lizgoban description)
  ko_detector.py          — PV recapture + board ko_point check
  snapback_detector.py    — Liberty counting + sacrifice pattern
  throw_in_detector.py    — Edge position + liberty reduction verification
  net_detector.py         — Surrounding geometry check
  seki_detector.py        — Balanced ownership + mutual life
  capture_race_detector.py — Competing group liberty comparison
  connection_detector.py  — Group connectivity before/after move
  cutting_detector.py     — Group disconnection analysis
  eye_shape_detector.py   — Eye detection from liberty.py
  nakade_detector.py      — Interior vital point + eye count
  double_atari_detector.py — Two groups in atari after move
  sacrifice_detector.py   — Stone count decrease + winrate increase
  escape_detector.py      — Liberty increase / connection to safe group
  vital_point_detector.py — Existing vital_move.py wiring
  dead_shapes_detector.py — Known killable shape patterns
  liberty_shortage_detector.py — Liberty comparison pre/post move
  connect_and_die_detector.py — Connect then die pattern
  life_and_death_detector.py  — Default objective classification
  living_detector.py      — Group survival confirmation
  corner_detector.py      — Position-based (YC property)
  shape_detector.py       — Shape pattern catalog
  endgame_detector.py     — Edge/late-game heuristic
  tesuji_detector.py      — Meta-tag: any specific tesuji detected
  joseki_detector.py      — Heuristic: opening position + known patterns
  fuseki_detector.py      — Heuristic: whole-board opening context
  clamp_detector.py       — Clamp pattern (2nd line squeeze)
  under_the_stones_detector.py — Sacrifice then place inside pattern
```

Each detector implements: `detect(position, analysis_response, solution_tree) → DetectionResult(detected: bool, confidence: float, evidence: str)`

`technique_classifier.py` becomes a dispatcher that calls all detectors and merges results by priority.

### 1.5 Difficulty Estimation Enhancement

Add KaTrain complexity metric as 5th component:
```
complexity = Σ(prior × max(score_delta, 0)) / Σ(prior)
```

Updated formula weights (config-driven):
- Policy rank: 25% (was 30%)
- Visits to solve: 20% (was 30%)  
- Trap density: 20% (unchanged)
- Structural: 20% (was 20%)
- Complexity: 15% (new)

---

## 2. Data Model Impact

### 2.1 Models to Delete

| Model | File | Reason |
|-------|------|--------|
| `CroppedPosition` | `models/position.py` | Cropping removed (G-2) |

### 2.2 Models to Add

| Model | File | Purpose |
|-------|------|---------|
| `EntropyROI` | `models/entropy_roi.py` | Contested region coordinates + entropy grid |
| `DetectionResult` | `models/detection.py` | Per-detector output (detected, confidence, evidence, tag_slug). Lives in models layer to prevent inverse dependency (V-4 fix). |
| `TechniqueDetectionResult` | `models/technique_result.py` | Aggregated multi-detector output |
| `ValidationStatus`, `CorrectMoveResult` | `models/validation.py` | Extracted from `analyzers/validate_correct_move.py` to fix inverse dependency V-1 (model importing from analyzer). |
|-------|--------|
| `AnalysisRequest` | Add `reportAnalysisWinratesAs` field. Remove crop-related fields. |
| `Position` | Remove `crop_to_tight_board()`, `CroppedPosition` references |

---

## 3. Phase Breakdown

### Phase 1 — Foundation (G-2, G-3, G-4, G-5, G-6, G-10, G-13)

**Scope**: Remove cropping, add entropy ROI, fix refutation consistency, increase visit tiers, pipeline stage cleanup, enforce modular design, KataGo query improvements.

**Files touched/created**:
- Delete: `tsumego_frame.py` (BFS dead code), test file references
- Delete: `CroppedPosition` class, `crop_to_tight_board()`, `uncrop_response()`, `uncrop_gtp()`
- Create: `analyzers/entropy_roi.py`
- Create: `analyzers/stages/solve_path_stage.py` (formalize)
- Modify: `analyzers/stages/query_stage.py` → rename to `analyze_stage.py`, accept Position directly
- Modify: `analyzers/generate_refutations.py` — use framed position
- Modify: `analyzers/query_builder.py` — remove crop logic, single entry point
- Modify: `config.py` — add visit tier config, entropy thresholds
- Modify: `katago-enrichment.json` — visit tier values, new query params
- Modify: `models/analysis_request.py` — add `reportAnalysisWinratesAs`
- Modify: `models/position.py` — remove crop methods
- Split: `analyzers/stages/teaching_stage.py` → `technique_stage.py` + `teaching_stage.py` + `sgf_writeback_stage.py`
- Fix: 8 existing test failures (config schema drift)

**Test gate**: All existing passing tests still pass. New tests for entropy ROI, solve-path stage, visit tiers, query params.

### Phase 2 — Detection (G-1, G-7, G-8, G-9, G-11)

**Scope**: All 28 technique detectors, board-state analysis integration, pattern-based ladder, complexity metric, graceful degradation.

**Files created**:
- `analyzers/detectors/` directory with 28 detector files
- `analyzers/detectors/__init__.py` with `DetectionResult` and dispatcher
- Tests for each detector

**Files modified**:
- `analyzers/technique_classifier.py` — become dispatcher calling individual detectors
- `analyzers/estimate_difficulty.py` — add complexity metric (5th component)
- `config.py` — add detector thresholds, complexity weight
- `katago-enrichment.json` — detector thresholds

**Priority ordering** (MH-3: high-frequency tags first):
1. life-and-death, ko, ladder, snapback (most common in corpus)
2. capture-race, connection, cutting, throw-in, net (common techniques)
3. seki, nakade, double-atari, sacrifice, escape (intermediate frequency)
4. eye-shape, vital-point, liberty-shortage, dead-shapes, clamp (lower frequency)
5. living, corner, shape, endgame, tesuji, under-the-stones, connect-and-die (least frequent / context-dependent)
6. joseki, fuseki (heuristic quality only, documented limitations)

**Test gate**: Each detector has ≥1 positive and ≥1 negative test. Integration test confirming technique → hint → teaching comment flow.

### Phase 3 — Stretch (G-12)

**Scope**: HumanSL feature-gated interface.

**Files created/modified**:
- `analyzers/humansl_calibration.py` — query builder with `humanSLProfile` parameter
- `config.py` — HumanSL model path config, feature gate
- Tests with mock responses (no real model needed for unit tests)

**Test gate**: Feature gate works (model absent → gracefully skipped). Query format correct when model present.

---

## 4. Risks and Mitigations

| Risk | Level | Mitigation |
|------|-------|------------|
| Removing cropping changes policy distribution for all puzzles | Medium | Validate with 10-puzzle golden set before and after. ROI + frame should maintain policy focus. |
| 28 detector files is a lot of code to maintain | Medium | Shared `DetectionResult` contract. Each detector is independent — can be disabled individually via config. |
| Visit increase (200→500 standard) slows throughput ~2.5× | Low | T0 (50 visits) used for pre-classification. Only complex puzzles escalate to T2/T3. |
| GPL contamination from Lizgoban ladder algorithm | Medium | Clean-room: implement from algorithmic description (3×3 pattern, 8 symmetries, recursive extension, liberty checks). No JS code referenced during implementation. |
| Lizgoban concept integration (4 quality gates) | Low | All 4 concepts (tenuki rejector, temperature scoring, frame quality, curated pruning) are config-toggleable, ~255 lines total, golden-set validated in T30. Each can be individually disabled without code changes. |
| Entropy ROI computation requires ownership data | Low | Ownership already requested (`includeOwnership: true`). Entropy is a pure math transform on existing data. |

---

## 5. Documentation Plan

### Files to Create

| File | Content |
|------|---------|  
| `docs/how-to/backend/enrichment-lab.md` | Pipeline stage changes, new detectors, visit tiers |
| `docs/concepts/technique-detection.md` | 28-tag detection architecture, detector interface |
| `docs/concepts/entropy-roi.md` | Ownership entropy formula, ROI computation, fallback chain |
| `docs/concepts/detector-interface.md` | DetectionResult contract, how to add new detectors |
| `docs/reference/katago-enrichment-config.md` | Visit tiers, query params, detector thresholds |

### Files to Update

| File | Why Updated |
|------|-------------|
| `tools/puzzle-enrichment-lab/README.md` | Updated architecture, stage list, detector inventory |

### Cross-References

All new docs MUST include "See also" callouts per documentation rules:
- Entropy ROI → Architecture: board region strategy → Reference: config
- Detector interface → Concepts: technique detection → How-To: enrichment lab

---

## 6. Contracts / Interfaces

### 6.1 DetectionResult (new)

```python
@dataclass
class DetectionResult:
    detected: bool
    confidence: float  # 0.0-1.0
    tag_slug: str      # matches config/tags.json slug
    evidence: str      # human-readable explanation
```

### 6.2 Detector Protocol (new)

```python
class TechniqueDetector(Protocol):
    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult: ...
```

### 6.3 EntropyROI (new)

```python
@dataclass
class EntropyROI:
    entropy_grid: list[list[float]]  # board_size × board_size
    contested_region: list[str]      # GTP coordinates of high-entropy intersections
    bounding_box: tuple[int, int, int, int]  # min_row, min_col, max_row, max_col
    mean_entropy: float
```
