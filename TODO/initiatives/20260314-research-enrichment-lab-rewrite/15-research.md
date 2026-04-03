# Research: Puzzle-Enrichment-Lab Architecture & State Assessment

**Initiative**: `20260314-research-enrichment-lab-rewrite`
**Research question**: What is the current architecture, health, and pain-point inventory of `tools/puzzle-enrichment-lab/` to inform a major refactor/rewrite?
**Last Updated**: 2026-03-14

---

## 1. Research Question & Boundaries

| ID | Question |
|----|----------|
| RQ-1 | What does each module in the enrichment lab do, and what is its health? |
| RQ-2 | What tests pass/fail and what areas have no coverage? |
| RQ-3 | What KataGo query parameters are sent, and where are they configured? |
| RQ-4 | How does the tsumego frame work, and what are its problems? |
| RQ-5 | How does board cropping interact with the frame, and what breaks? |
| RQ-6 | What is the pipeline stage execution order & data flow? |

---

## 2. Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLI / GUI Entry Points                         │
│                   cli.py  |  bridge.py  |  gui/                         │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR: enrich_single.py                        │
│  Config init → trace_id → dispatch solve-path → StageRunner.run()       │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
          ┌───────────┴───────────────────────────────┐
          │         STAGE RUNNER (stage_runner.py)     │
          │  Auto-wraps: timing, notify, error policy  │
          └───────────┬───────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────────────────────────────────┐
    │                 │        PIPELINE STAGES (ordered)             │
    │  ┌──────────────┴────────────────┐                            │
    │  │ 1. ParseStage (FAIL_FAST)     │                            │
    │  │    SGF → metadata + position  │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 2. solve_paths (dispatch)     │                            │
    │  │    position-only / has-soln / │                            │
    │  │    standard path              │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 3. QueryStage (FAIL_FAST)     │                            │
    │  │    crop → frame → KataGo req  │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 4. ValidationStage (DEGRADE)  │                            │
    │  │    correct move vs KataGo     │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 5. RefutationStage (DEGRADE)  │                            │
    │  │    wrong-move punishment seqs │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 6. DifficultyStage (DEGRADE)  │                            │
    │  │    structural + policy formula│                            │
    │  ├───────────────────────────────┤                            │
    │  │ 7. AssemblyStage (FAIL_FAST)  │                            │
    │  │    wire AiAnalysisResult      │                            │
    │  ├───────────────────────────────┤                            │
    │  │ 8. TeachingStage (DEGRADE)    │                            │
    │  │    technique + hints + SGF    │                            │
    │  └───────────────────────────────┘                            │
    └───────────────────────────────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────────────────────────────────┐
    │           ANALYZERS (domain logic)                             │
    │                                                               │
    │  query_builder.py ─── build_query_from_sgf/position           │
    │  validate_correct_move.py ─── tag-aware dispatch (7 validators)│
    │  generate_refutations.py ─── wrong-move candidates + PV       │
    │  estimate_difficulty.py ─── composite formula + elo gate      │
    │  technique_classifier.py ─── 8 detectors → tag list           │
    │  hint_generator.py ─── 3-tier progressive hints               │
    │  teaching_comments.py ─── V2 signal-enriched C[] embedding    │
    │  comment_assembler.py ─── Layer 1+2 composition engine        │
    │  sgf_enricher.py ─── policy-aligned SGF property writeback    │
    │  ko_validation.py ─── PV-based ko detection                   │
    │  frame_adapter.py ─── algorithm-agnostic frame API            │
    │  tsumego_frame_gp.py ─── GP count-based fill (ACTIVE)         │
    │  tsumego_frame.py ─── BFS flood-fill (INACTIVE, legacy)       │
    │  liberty.py ─── liberty counting, eye detection               │
    │  vital_move.py ─── decisive tesuji detector                   │
    │  refutation_classifier.py ─── 11-condition priority dispatch  │
    │  benson_check.py ─── unconditional life gate                  │
    │  single_engine.py ─── dual-engine manager (quick + referee)   │
    │  result_builders.py ─── AiAnalysisResult factory helpers      │
    │  config_lookup.py ─── config/tags.json + levels.json loaders  │
    │  property_policy.py ─── sgf-property-policies.json reader     │
    │  observability.py ─── AI-Solve disagreement logging           │
    │  ascii_board.py ─── debug board rendering                     │
    └───────────────────────────────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────────────────────────────────┐
    │           SUPPORTING LAYERS                                   │
    │                                                               │
    │  config.py ─── ~1200 lines, 40+ Pydantic models              │
    │      EnrichmentConfig (top-level, loads katago-enrichment.json)│
    │      AiSolveConfig (solve tree, classification, DD-1..DD-12)  │
    │      TeachingCommentsConfig (teaching-comments.json)           │
    │                                                               │
    │  engine/local_subprocess.py ─── KataGo stdin/stdout JSON      │
    │  engine/config.py ─── EngineConfig (binary, model, visits)    │
    │                                                               │
    │  core/sgf_parser.py ─── KaTrain SGF parser (MIT port)         │
    │  core/tsumego_analysis.py ─── position extraction, move trees │
    │                                                               │
    │  models/ ─── 8 Pydantic models                                │
    │    position.py ─── Position, Stone, Color, CroppedPosition    │
    │    analysis_request.py ─── AnalysisRequest → KataGo JSON      │
    │    analysis_response.py ─── KataGo response parsing           │
    │    ai_analysis_result.py ─── Top-level enrichment output      │
    │    solve_result.py ─── AI-Solve tree types                    │
    │    difficulty_estimate.py ─── DifficultyEstimate              │
    │    refutation_result.py ─── RefutationResult, Refutation      │
    │    enrichment_state.py ─── EnrichmentRunState                 │
    └───────────────────────────────────────────────────────────────┘
```

---

## 3. Module-by-Module Summary

### 3.1 Orchestration Layer

| R-ID | Module | Purpose | Key Functions | Lines (est.) | Health |
|------|--------|---------|---------------|-------------|--------|
| R-1 | `enrich_single.py` | Thin orchestrator — dispatches to StageRunner | `enrich_single_puzzle()` (main entry point) | ~200 | ✅ Good — recently refactored (SRP decomposition, 20260313) |
| R-2 | `stages/stage_runner.py` | Auto-wraps stages with timing/error/notify | `run_stage()`, `run_pipeline()` | ~80 | ✅ Good — clean, minimal |
| R-3 | `stages/protocols.py` | PipelineContext, SgfMetadata, ErrorPolicy | `PipelineContext` (mutable dataclass) | ~120 | ✅ Good — typed, documented |
| R-4 | `stages/parse_stage.py` | SGF parsing + metadata extraction | ParseStage.run() | ~80 | ✅ Good |
| R-5 | `stages/query_stage.py` | Crop → frame → KataGo query → back-translate | QueryStage.run() | ~100 | ✅ Good |
| R-6 | `stages/validation_stage.py` | Correct-move validation + tree validation | ValidationStage.run() | ~100 | ✅ Good — DEGRADE policy |
| R-7 | `stages/refutation_stage.py` | Refutation generation with escalation | RefutationStage.run() | ~80 | ✅ Good |
| R-8 | `stages/difficulty_stage.py` | Structural + policy-only difficulty | DifficultyStage.run() | ~80 | ✅ Good |
| R-9 | `stages/assembly_stage.py` | Wire AiAnalysisResult | AssemblyStage.run() | ~80 | ✅ Good |
| R-10 | `stages/teaching_stage.py` | Technique + hints + SGF writeback | TeachingStage.run() | ~80 | ✅ Good |
| R-11 | `stages/solve_paths.py` | 3 solve paths: position-only, has-solution, standard | `run_position_only_path()`, etc. | ~100 | ⚠️ Complex dispatch logic |

### 3.2 Analysis Modules

| R-ID | Module | Purpose | Key Functions | Health |
|------|--------|---------|---------------|--------|
| R-12 | `query_builder.py` | SGF → KataGo AnalysisRequest | `build_query_from_sgf()`, `build_query_from_position()`, `prepare_tsumego_query()`, `uncrop_response()` | ✅ Good — two entry points (SGF vs Position), centralized query prep |
| R-13 | `validate_correct_move.py` | Tag-aware correct-move validation (7 validators) | `validate_correct_move()` → dispatches to `_validate_life_and_death()`, `_validate_tactical()`, `_validate_capture_race()`, `_validate_connection()`, `_validate_seki()`, `_validate_miai()` + ko delegation | ✅ Good — config-driven thresholds, tag-ID lazy loading from config/tags.json |
| R-14 | `generate_refutations.py` | Wrong-move candidates + refutation PVs | `identify_candidates()`, `generate_single_refutation()`, `generate_refutations()` + curated policy enrichment | ✅ Good — score-based trap density (v1.17) |
| R-15 | `estimate_difficulty.py` | Composite difficulty formula | `estimate_difficulty()` (4-component weighted), `estimate_difficulty_policy_only()` (Tier 0.5), `_compute_trap_density()`, `_elo_anchor_gate()` | ✅ Good — all weights config-driven |
| R-16 | `technique_classifier.py` | 8 technique detectors | `classify_techniques()` → `_detect_ko()`, `_detect_ladder()`, `_detect_snapback()`, `_detect_throw_in()`, `_detect_seki()`, `_detect_net()`, `_detect_direct_capture()` | ⚠️ Fair — heuristic pattern matching on PV data only (no board state analysis). Missing: connection, cutting, eye-shape, capture-race, escape detectors |
| R-17 | `hint_generator.py` | 3-tier progressive hints (technique, reasoning, coordinate) | `generate_hints()`, `format_yh_property()` | ✅ Good — config-driven via teaching-comments.json |
| R-18 | `teaching_comments.py` | V2 two-layer composition for C[] embedding | `generate_teaching_comments()` — wires vital_move, refutation_classifier, comment_assembler | ✅ Good — recently rewritten (V2) |
| R-19 | `comment_assembler.py` | Layer 1 + Layer 2 composition engine | `assemble_correct_comment()`, `assemble_vital_comment()`, `assemble_wrong_comment()` | ✅ Good — 15-word cap, parenthetical counting |
| R-20 | `sgf_enricher.py` | Policy-aligned SGF property writeback | `enrich_sgf()` — writes YR, YG, YX, YH, refutation branches | ✅ Good — respects sgf-property-policies.json |
| R-21 | `ko_validation.py` | PV-based ko detection + ko-aware validation | `detect_ko_in_pv()`, `validate_ko_puzzle()` | ✅ Good — adjacency-based recapture detection |
| R-22 | `vital_move.py` | Decisive tesuji detection beyond first move | `detect_vital_move()` — walks solution tree for branching/ownership inflection | ✅ Good, simple |
| R-23 | `refutation_classifier.py` | 11-condition priority dispatch for wrong moves | `classify_refutation()` — first-match-wins over conditions like `immediate_capture`, `opponent_escapes`, `ko_involved`, etc. | ✅ Good |
| R-24 | `liberty.py` | Liberty counting, puzzle-stone protection, eye detection | `count_group_liberties()`, `would_harm_puzzle_stones()`, `is_eye()`, `has_frameable_space()` | ✅ Good — extracted from tsumego_frame for SRP |
| R-25 | `benson_check.py` | Unconditional life gate (Benson's algorithm) | Feature-flagged via `benson_gate` config | ⚠️ New (v1.16) — limited test coverage |

### 3.3 Frame Modules

| R-ID | Module | Purpose | Key Functions | Health |
|------|--------|---------|---------------|--------|
| R-26 | `frame_adapter.py` | Algorithm-agnostic frame API (facade) | `apply_frame()`, `remove_frame()`, `validate_frame()` | ✅ Good — clean facade (GP Frame Swap, 20260313) |
| R-27 | `tsumego_frame_gp.py` | **ACTIVE**: GoProblems count-based fill (KaTrain/ghostban port) | `apply_gp_frame()`, `_tsumego_frame_stones()` — border wall → outside fill → ko threat | ⚠️ Complex (~400 lines) — KaTrain port with flip/normalize recursion |
| R-28 | `tsumego_frame.py` | **INACTIVE**: BFS flood-fill algorithm (V3 rewrite) | `normalize_to_tl()`, `guess_attacker()`, `fill_frame()` | ❌ Legacy — superseded by GP frame, still present (~400 lines dead code) |
| R-29 | `frame_utils.py` | Shared frame geometry helpers | `compute_regions()`, `detect_board_edge_sides()` | ✅ Good |

### 3.4 Support Modules

| R-ID | Module | Purpose | Lines (est.) | Health |
|------|--------|---------|-------------|--------|
| R-30 | `config.py` | ~1200 lines, 40+ Pydantic models, loads katago-enrichment.json | 1200 | ⚠️ Bloated — monolithic config with models spanning enrichment, AI-solve, teaching, calibration, paths, elo, benson. Growing organically. |
| R-31 | `engine/local_subprocess.py` | KataGo stdin/stdout JSON driver | ~200 | ✅ Good — async start, JSON protocol |
| R-32 | `engine/config.py` | EngineConfig with path resolution | ~60 | ✅ Good |
| R-33 | `core/sgf_parser.py` | KaTrain SGF parser (MIT port) | ~400 | ✅ Stable — pure Python, no dependencies |
| R-34 | `core/tsumego_analysis.py` | Position extraction, solution tree, move branches | ~200 | ✅ Stable — thin wrapper over sgf_parser |
| R-35 | `models/` (8 files) | Pydantic data models | ~800 total | ✅ Good — clean types. `position.py` includes cropping logic (CroppedPosition) |
| R-36 | `single_engine.py` | Dual-engine manager (quick + referee) | ~200 | ✅ Good — escalation and tiebreaker logic |
| R-37 | `config_lookup.py` | Lazy loaders for tags.json, levels.json | ~100 | ✅ Good |
| R-38 | `property_policy.py` | sgf-property-policies.json reader | ~80 | ✅ Good |
| R-39 | `log_config.py` | Logging setup with per-run files | ~100 | ✅ Good |

---

## 4. Test Suite Health

### 4.1 Overall Numbers

| Metric | Value |
|--------|-------|
| Total unit tests collected (excluding perf/calibration/engine/CLI) | 1,628 |
| Passed | 1,523 |
| Failed | 8 |
| Skipped | 97 |
| Pass rate | **93.6%** (99.5% excluding skipped) |

### 4.2 Failing Tests (8 failures)

| R-ID | Test | Module | Failure Description |
|------|------|--------|---------------------|
| F-1 | `test_sprint4_fixes.py::TestStructuralWeightsFromConfig::test_structural_weights_sum_to_100` | estimate_difficulty | Structural weights config schema changed (proof_depth added in v1.15, test expects old 4-weight schema) |
| F-2 | `test_sprint4_fixes.py::TestStructuralWeightsFromConfig::test_custom_structural_weights` | estimate_difficulty | Same root cause — test fixture missing `proof_depth` field |
| F-3 | `test_teaching_comments_config.py::test_dead_shapes_has_alias_comments` | teaching_comments | Config `teaching-comments.json` schema change — dead-shapes entry missing `alias_comments` |
| F-4 | `test_teaching_comments_config.py::test_tesuji_has_alias_comments` | teaching_comments | Config schema change — tesuji entry missing `alias_comments` |
| F-5 | `test_teaching_comments_integration.py::test_empty_tags_uses_fallback` | teaching_comments | V2 rewrite changed return structure |
| F-6 | `test_tsumego_config.py::test_static_score_utility_factor` | config | KataGo tsumego analysis config field changed/removed |
| F-7 | `test_tsumego_config.py::test_dynamic_score_utility_factor` | config | Same — KataGo config field removed |
| F-8 | `test_tsumego_config.py::test_ignore_pre_root_history` | config | KataGo config field changed |

**Root cause pattern**: Most failures (6/8) are config-schema drift — tests reference old config shapes after rapid iteration (v1.15-v1.17). The remaining 2 are teaching-comments V2 return structure changes.

### 4.3 Skipped Tests (97)

Skipped tests are primarily:
- Tests requiring KataGo binary/model (engine integration tests)
- Tests requiring live puzzle fixtures (`yengo-puzzle-collections/sgf/`)
- Performance/calibration tests excluded by default

### 4.4 Test Coverage by Module

| Area | Test File(s) | Coverage |
|------|-------------|----------|
| Correct move validation | `test_correct_move.py`, `test_solve_position.py` | ✅ Good |
| Refutations | `test_refutations.py`, `test_refutation_classifier.py` | ✅ Good |
| Difficulty estimation | `test_difficulty.py`, `test_calibration.py` | ✅ Good (calibration tests skipped w/o engine) |
| Technique classification | `test_technique_classifier.py` | ✅ Fair |
| Hints | `test_hint_generator.py` | ✅ Good |
| Teaching comments | `test_teaching_comments.py`, `test_teaching_comments_config.py`, `test_teaching_comments_integration.py`, `test_teaching_comment_embedding.py` | ⚠️ Some failures |
| SGF enrichment | `test_sgf_enricher.py`, `test_sgf_parser.py` | ✅ Good |
| Ko validation | `test_ko_validation.py`, `test_ko_rules.py` | ✅ Good |
| Query builder | `test_query_builder.py` | ✅ Good |
| Frame (GP) | `test_frames_gp.py`, `test_frame_adapter.py`, `test_frame_utils.py` | ✅ Good |
| Frame (legacy BFS) | `test_tsumego_frame.py` | ⚠️ Tests exist but may reference inactive code |
| Cropping | `test_tight_board_crop.py` | ✅ Exists |
| Benson check | `test_benson_check.py` | ✅ Exists |
| Vital move | `test_vital_move.py` | ✅ Good |
| Config | `test_tsumego_config.py`, `test_enrichment_config.py`, `test_deep_enrich_config.py` | ⚠️ Some failures |
| Sprint regression | `test_sprint1_fixes.py` through `test_sprint5_fixes.py` | ⚠️ Sprint 4 has failures |
| AI-Solve integration | `test_ai_solve_integration.py`, `test_ai_solve_config.py`, `test_ai_analysis_result.py`, `test_ai_solve_calibration.py` | ✅ Good (calibration skipped w/o fixtures) |

---

## 5. KataGo Query Parameter Inventory

### 5.1 Parameters Sent Per Query

| R-ID | Parameter | Source | Default | Where Set |
|------|-----------|--------|---------|-----------|
| K-1 | `maxVisits` | `config.analysis_defaults.default_max_visits` or `config.deep_enrich.visits` | 200 (standard) / 2000 (deep enrich) | `AnalysisRequest.max_visits` → `to_katago_json()` |
| K-2 | `komi` | Always overridden to 0.0 for tsumego | 0.0 | `_TSUMEGO_KOMI` in `query_builder.py` line 42 |
| K-3 | `rules` | Per-ko-type from `config.ko_analysis.rules_by_ko_type` | `"chinese"` (none), `"tromp-taylor"` (ko) | `prepare_tsumego_query()` in `query_builder.py` |
| K-4 | `analysisPVLen` | Per-ko-type from `config.ko_analysis.pv_len_by_ko_type` | 15 (none), 30 (direct/approach ko) | `AnalysisRequest.analysis_pv_len` |
| K-5 | `includeOwnership` | Always true | `true` | `AnalysisRequest(include_ownership=True)` |
| K-6 | `includePVVisits` | Always true | `true` | `to_katago_json()` when `include_pv=True` |
| K-7 | `includePolicy` | Always true | `true` | `AnalysisRequest(include_policy=True)` |
| K-8 | `allowMoves` | Puzzle region (bbox + margin of stones) | Computed per puzzle | `Position.get_puzzle_region_moves(margin=2)` |
| K-9 | `initialPlayer` | From position player_to_move (or inferred from first correct move) | Varies | `to_katago_json()` |
| K-10 | `boardXSize` / `boardYSize` | From (possibly cropped) position.board_size | 9/13/19 | `to_katago_json()` |
| K-11 | `overrideSettings.rootNumSymmetriesToSample` | `config.deep_enrich.root_num_symmetries_to_sample` | 2 | `AnalysisRequest.override_settings` |
| K-12 | `maxTime` | `config.deep_enrich.max_time` | 0 (unlimited) | `AnalysisRequest.max_time` |
| K-13 | `initialStones` | Position stones converted to `[["B","D4"],["W","C5"]]` | Varies | `Position.to_katago_initial_stones()` |
| K-14 | `analyzeTurns` | Always `[len(moves)]` (analyze after last move) | `[0]` typically | `to_katago_json()` |

### 5.2 KataGo Config File Overrides (via `-override-config`)

| Parameter | Source |
|-----------|--------|
| `numAnalysisThreads` | `EngineConfig.num_threads` (default 2) |
| `nnMaxBatchSize` | Set equal to `num_threads` |
| `logDir` | `.lab-runtime/katago-logs/` |

### 5.3 Parameters NOT Sent (Rely on KataGo Defaults)

| Parameter | KataGo Default | Note |
|-----------|---------------|------|
| `reportAnalysisWinratesAs` | `BLACK` | Not explicitly set — relies on cfg file or KataGo default |
| `numSearchThreads` | 1 | Relies on KataGo config file default |
| `nnCacheSizePowerOfTwo` | 23 | Relies on config file |

---

## 6. Tsumego Frame Analysis

### 6.1 What the Frame Does

The tsumego frame fills empty areas of the board outside the puzzle region with additional stones to:
1. **Focus KataGo's policy** on the puzzle area (don't analyze far-away moves)
2. **Give ownership network context** — alive/dead groups need surrounding territory
3. **Create score-neutral territory** — 50/50 split so puzzle outcome alone determines winner

### 6.2 Two Implementations (Only GP is Active)

| Frame | File | Status | Algorithm |
|-------|------|--------|-----------|
| GP Frame | `tsumego_frame_gp.py` via `frame_adapter.py` | **ACTIVE** | GoProblems.com count-based fill (KaTrain port, MIT) |
| BFS Frame | `tsumego_frame.py` | **INACTIVE** | BFS flood-fill with normalization (original V3 rewrite) |

The GP frame (`tsumego_frame_gp.py`) is the active algorithm, routed through `frame_adapter.py`:

1. **Attacker detection**: Heuristic via stone-count ratio + edge-proximity + Lizzie bbox cover score
2. **Canonical normalization**: Flip/rotate so puzzle is in TL corner (recursive: normalize → fill → de-normalize)
3. **Border wall**: Solid attacker ring at `frame_range = bbox + margin`
4. **Outside fill**: Count-based half-and-half territory — attacker gets `offence_to_win` extra points (default 5), defender fills the rest. Checkerboard holes `(i+j)%2==0` only far from seam
5. **Ko-threat placement**: Optional ko-threat patterns from KaTrain
6. **Edge snapping**: `NEAR_TO_EDGE = 2` — snaps bbox to board edge when within 2 points

### 6.3 Board Sizes Supported

| Board Size | Cropping | Frame |
|------------|----------|-------|
| 5×5 to 8×8 | N/A (already small) | Applied (min size validation: `_MIN_FRAME_BOARD_SIZE = 5` in BFS; GP has no explicit minimum) |
| 9×9 | No crop | Applied |
| 10–12 | Cropped → 13×13 | Applied after crop |
| 13×13 | No crop | Applied |
| 14–18 | Not cropped (stays 19) | Applied |
| 19×19 | Cropped → 9 or 13 if stones fit | Applied after crop |

### 6.4 Known Frame Problems

| R-ID | Problem | Evidence |
|------|---------|----------|
| FP-1 | **Legacy BFS frame is dead code** (~400 lines) | `tsumego_frame.py` still exists, has tests (`test_tsumego_frame.py`), but `frame_adapter.py` routes only to GP frame |
| FP-2 | **Attacker detection heuristic fragile** | `guess_attacker()` in both frames uses stone-count ratio, edge proximity, Lizzie cover score — can misidentify attacker when puzzle is sparse or in center |
| FP-3 | **Recursive flip/normalize** | GP frame calls itself recursively with flipped board if not in canonical (TL) position — hard to debug, can double-process |
| FP-4 | **No frame validation in GP** | `validate_frame()` in `frame_adapter.py` checks connectivity of frame stones but is not called in the pipeline — validation is opt-in only |
| FP-5 | **GP frame ignores board sizes < 9** | No explicit guard for very small puzzles; KaTrain was designed for 19×19 with frame |

---

## 7. Board Cropping vs Region-of-Interest Analysis

### 7.1 How Cropping Works

`Position.crop_to_tight_board(margin=2)` in `models/position.py`:
1. Compute bounding box of all stones
2. Expand by `margin` in each direction
3. Snap up to nearest standard size: ≤9→9, 10–13→13, ≥14→19 (no crop)
4. Center the stones within the cropped board
5. Return `CroppedPosition` with offset for back-translation

### 7.2 Interaction with Frame

The pipeline flow is: **Crop → Frame → Analyze → Uncrop**

```
Original 19×19 → crop_to_tight_board() → 9×9 or 13×13
                                              ↓
                                    apply_frame() on cropped board
                                              ↓
                                    KataGo analyzes framed + cropped
                                              ↓
                                    uncrop_response() back to 19×19
```

### 7.3 Problems Caused by Cropping + Frame Interaction

| R-ID | Problem | Description |
|------|---------|-------------|
| CP-1 | **Policy dilution on 19×19** | When stones are sparse and cropping doesn't reduce board size (stays 19), KataGo's policy spreads across 361 intersections. Policy prior for the correct move becomes very low (0.001-0.01), inflating difficulty scores. Documented in changelog v1.10: "Expert panel S.0 identified policy dilution on 19×19 boards inflating elementary scores." |
| CP-2 | **Frame fills wrong area after crop** | After cropping, frame fills the smaller board. If crop centering places puzzle near edge of cropped board, the frame's "outside" region is smaller and the territory balance shifts unpredictably |
| CP-3 | **Coordinate back-translation complexity** | `CroppedPosition.uncrop_gtp()` and `uncrop_move()` translate between cropped and original boards. If the frame adds stones that get analyzed, those stone coordinates also need back-translation for logging/debugging |
| CP-4 | **Separate code paths for cropped vs uncropped** | `build_query_from_sgf()` crops by default; `build_query_from_position()` never crops (AI-Solve tree builder uses original coords). This creates two code paths with different frame behavior |
| CP-5 | **Stones can be dropped during crop** | If a stone falls outside the cropped region (logged as warning), it's silently dropped. This could occur with outlier stones far from the puzzle cluster |

---

## 8. Pipeline Stage Data Flow

### 8.1 Full Pipeline Sequence

```
Input: raw SGF string
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 1: ParseStage (FAIL_FAST)               │
    │  IN:  sgf_text, source_file                    │
    │  OUT: root (SGFNode), position (Position),     │
    │       metadata (SgfMetadata), correct_move_gtp,│
    │       solution_moves, puzzle_id                 │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  DISPATCH: solve_paths                          │
    │  position-only: no solution tree → limited      │
    │  has-solution: solution moves present            │
    │  standard: full SGF with tree                    │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 3: QueryStage (FAIL_FAST)               │
    │  IN:  position, metadata.ko_type, config       │
    │  INTERNAL: crop(19→9/13) → frame → build req   │
    │  ENGINE CALL: SingleEngineManager.analyze()     │
    │  OUT: response (AnalysisResponse), cropped,     │
    │       request                                   │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 4: ValidationStage (DEGRADE)            │
    │  IN:  response, correct_move_gtp, tags         │
    │  DISPATCH: tag-aware → 7 validators            │
    │    life-and-death: ownership thresholds         │
    │    tactical (ladder/net/snapback): PV matching  │
    │    capture-race: liberty comparison             │
    │    connection: group connectivity               │
    │    seki: 3-signal detection                     │
    │    ko: delegated to ko_validation module        │
    │    miai: multi-correct-move validation          │
    │  OUT: CorrectMoveResult (status, winrate,       │
    │       policy, flags, tree_validation)            │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 5: RefutationStage (DEGRADE)            │
    │  IN:  response, correct_move_gtp, position,    │
    │       nearby_moves, curated_wrongs              │
    │  FLOW: identify_candidates() → per-candidate   │
    │        engine query → refutation PV extraction  │
    │  ESCALATION: retry with higher visits if 0 refs │
    │  OUT: RefutationResult (refutations list with   │
    │       wrong_move, PV, winrate_delta, policy)    │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 6: DifficultyStage (DEGRADE)            │
    │  IN:  CorrectMoveResult, RefutationResult,     │
    │       solution_moves, branch_count, local_cands │
    │  FORMULA: policy(15%) + visits(15%) +           │
    │           trap_density(25%) + structural(45%)   │
    │  Score → level via score_to_level_thresholds    │
    │  ELO_GATE: optional cross-check vs policy level │
    │  OUT: DifficultyEstimate (score, level, ID)     │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 7: AssemblyStage (FAIL_FAST)            │
    │  IN:  all upstream results                      │
    │  FLOW: AC level decision, goal inference,       │
    │        tag resolution, field wiring              │
    │  OUT: AiAnalysisResult (full enrichment model)  │
    └───────────┬────────────────────────────────────┘
                │
    ┌───────────┴────────────────────────────────────┐
    │  STAGE 8: TeachingStage (DEGRADE)              │
    │  IN:  AiAnalysisResult (dict)                   │
    │  FLOW:                                          │
    │    1. classify_techniques() → tag list           │
    │    2. generate_teaching_comments() → V2 2-layer │
    │    3. generate_hints() → 3-tier YH property     │
    │    4. enrich_sgf() → write YG, YX, YH, YR +    │
    │       refutation branches to SGF tree            │
    │  OUT: AiAnalysisResult with enriched_sgf,       │
    │       technique_tags, hints, teaching_comments   │
    └───────────┬────────────────────────────────────┘
                │
Output: AiAnalysisResult (JSON-serializable enrichment payload)
```

---

## 9. Known Broken Areas (with Evidence)

| R-ID | Area | Severity | Evidence | Root Cause |
|------|------|----------|----------|------------|
| B-1 | Config schema drift (4 test failures) | Medium | `test_sprint4_fixes`, `test_tsumego_config` failures | Rapid config evolution (v1.15-v1.17) without test fixture updates |
| B-2 | Teaching comments V2 return structure (2 failures) | Low | `test_teaching_comments_config`, `test_teaching_comments_integration` | V2 rewrite changed API, old tests not updated |
| B-3 | KataGo config field changes (2 failures) | Low | `test_tsumego_config` failures on `score_utility_factor`, `ignore_pre_root_history` | KataGo analysis cfg updated externally |
| B-4 | Legacy BFS frame dead code (~400 lines) | Low | `tsumego_frame.py` still present + has test file `test_tsumego_frame.py` | GP Frame Swap didn't clean up old implementation |
| B-5 | Missing technique detectors | Medium | `technique_classifier.py` only has 8 detectors; connection, cutting, eye-shape, escape, capture-race are listed in docstring but not implemented | Incremental implementation, docstring ahead of code |
| B-6 | `reportAnalysisWinratesAs` not set | Low | Not found in any query code; relies on KataGo cfg file default | Implicit dependency on external config |

---

## 10. Candidate Adaptations & Recommendations

### Planner Recommendations

| Priority | Recommendation | Rationale |
|----------|---------------|-----------|
| **P1** | **Keep the stage pipeline architecture** | Clean decomposition (8 stages, error policies, DEGRADE/FAIL_FAST). The 20260313 SRP refactor made this well-structured. Don't rewrite — build on it. |
| **P2** | **Delete legacy BFS frame** (`tsumego_frame.py`) | 400 lines of dead code. GP frame is active and tested. Delete `tsumego_frame.py` + update/remove `test_tsumego_frame.py` tests that reference it. |
| **P3** | **Fix the 8 failing tests** (config schema drift) | Quick wins: update test fixtures to match v1.15-v1.17 config schemas (`proof_depth` in structural weights, teaching-comments alias structure, KataGo config fields). |
| **P4** | **Split `config.py`** (~1200 lines, 40+ models) | Biggest tech debt. Split into `config/enrichment.py`, `config/ai_solve.py`, `config/teaching.py`, `config/engine.py`. Each ~200-300 lines. The monolith makes navigation and testing painful. |
| **P5** | **Complete technique detectors** | Add missing detectors for connection, cutting, eye-shape, escape, capture-race. Current 8 detectors are heuristic on PV data only — consider adding board-state analysis (liberty counting, group connectivity from `liberty.py`). |
| **P6** | **Explicit `reportAnalysisWinratesAs=BLACK`** in query | Remove implicit dependency on KataGo config file. Set it explicitly in `AnalysisRequest.to_katago_json()` to avoid perspective bugs if cfg changes. |

### What to Keep (Do Not Rewrite)

| Component | Reason |
|-----------|--------|
| Stage pipeline (`stages/`) | Clean, recent refactor, well-tested |
| Query builder | Two clear entry points, centralized query prep |
| Validation dispatch | 7 tag-aware validators, config-driven |
| Difficulty formula | 4-component weighted, config-driven, elo gate |
| GP frame (`tsumego_frame_gp.py`) | Battle-tested KaTrain port, working |
| Model layer (`models/`) | Clean Pydantic types |
| Engine driver | Simple, correct stdin/stdout JSON |

### What to Rewrite/Refactor

| Component | Priority | Reason |
|-----------|----------|--------|
| `config.py` | High | Monolithic, 40+ models, ~1200 lines. Split by domain. |
| `tsumego_frame.py` (BFS) | Low | Delete — dead code |
| Technique classifier | Medium | Add missing detectors, consider board-state analysis |
| Teaching comments tests | Low | Fix test fixtures for V2 return structure |

---

## 11. Risks & Compliance Notes

| Risk | Level | Mitigation |
|------|-------|------------|
| KaTrain MIT license (frame + SGF parser) | Low | Already documented in source files. Attributions present. |
| Config bloat accelerating | Medium | Split config.py before adding more features |
| Frame heuristic misclassification | Medium | Log attacker detection decisions; add validation step to pipeline |
| Cropping drops outlier stones | Low | Rare case; logged as warning. Could add a hard check. |

---

## 12. Confidence & Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 85 |
| `post_research_risk_level` | low |

**Confidence justification**: Read all 25+ source files, collected test results, mapped every module. The architecture is well-structured after recent refactors. Main unknowns are in technique detection accuracy and the KataGo config file contents (`.cfg` not in repo).

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260314-research-enrichment-lab-rewrite/
artifact: 15-research.md
top_recommendations:
  - P1: Keep stage pipeline architecture (clean, tested)
  - P2: Delete legacy BFS frame (400 lines dead code)
  - P3: Fix 8 failing tests (config schema drift)
  - P4: Split config.py (1200 lines → 4-5 domain modules)
  - P5: Complete technique detectors (5 missing)
  - P6: Explicit reportAnalysisWinratesAs in query
open_questions:
  - Q1: KataGo analysis.cfg file contents — what's the numSearchThreads, nnCacheSizePowerOfTwo, etc.?
  - Q2: How accurate is technique detection vs human labels? No calibration data exists.
  - Q3: Should frame validation be mandatory in the pipeline?
post_research_confidence_score: 85
post_research_risk_level: low
```
