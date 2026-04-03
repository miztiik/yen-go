# Puzzle-Enrichment-Lab — Agent Architecture Map

> Agent-facing reference. Not for human docs. Update in same commit as structural code changes.
> _Last updated: 2026-03-26 | Trigger: Initiative 20260326-1400-feature-llm-teaching-enrichment — teaching signal payload + schema v10_

---

### 1. Directory Structure

- `log-viewer/` — Standalone HTML+JS JSONL log viewer dashboard (no build step, open index.html directly). Files: `index.html`, `app.js`, `styles.css`, `sample.jsonl`, `README.md`. Reads JSONL log files and renders interactive diagnostic dashboard with Chart.js charts, SVG pipeline journey, search, and glossary.
- `cli.py` — Typer CLI: `enrich`, `apply`, `validate`, `batch`, `calibrate` subcommands. Shared flags via `_add_common_args()`. Uses `bootstrap()` for centralized run_id + logging init.
- `bridge.py` — FastAPI ASGI server; SSE-streaming enrichment for web-katrain GUI; `GET /api/config` returns defaults; `POST /api/enrich` accepts optional `config_overrides` dict
- `bridge_config_utils.py` — Config override utilities: `unflatten_dotted_paths()`, `deep_merge()`, `apply_config_overrides()` (applies GUI overrides to `EnrichmentConfig`)
- `config/` — Python package (was `config.py`). Domain-organized sub-modules:
  - `__init__.py` — `EnrichmentConfig` composition root + loaders (`load_enrichment_config`, `clear_cache`, `resolve_path`, etc.)
  - `difficulty.py` — `DifficultyConfig`, `ValidationConfig`, `OwnershipThresholds`, `EloAnchorConfig`, etc. (17 models)
  - `refutations.py` — `RefutationsConfig`, `RefutationEscalationConfig`, `CandidateScoringConfig`, etc. (5 models)
  - `technique.py` — `TechniqueDetectionConfig`, `KoDetectionConfig`, per-detector configs (12 models)
  - `solution_tree.py` — `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, etc. (6 models)
  - `ai_solve.py` — `AiSolveConfig`, `AiSolveThresholds`, etc. (6 models); imports from `solution_tree`
  - `teaching.py` — `TeachingConfig`, `TeachingCommentsConfig`, `TeachingSignalConfig`, `load_teaching_comments_config` (10 models)
  - `analysis.py` — `AnalysisDefaultsConfig`, `DeepEnrichConfig`, `ModelsConfig`, etc. (11 models)
  - `infrastructure.py` — `PathsConfig`, `CalibrationConfig` (incl. PI-11 surprise weighting fields), `LoggingExtraConfig`, `TestDefaultsConfig` (4 models) + `compute_surprise_weight()` pure function
  - `helpers.py` — `get_effective_max_visits()`, `get_level_category()`, `LEVEL_CATEGORY_MAP`, path constants (`LAB_DIR`, `KATAGO_PATH`, `TSUMEGO_CFG`, `MODELS_DIR`), `model_path(label)` D42 model resolution via `_get_cfg()` `@lru_cache`, config-driven test defaults (`TEST_STARTUP_TIMEOUT`, `TEST_QUERY_TIMEOUT`, `TEST_MAX_VISITS`, `TEST_NUM_THREADS`)
- `log_config.py` — structured JSON logging; `setup_logging()`, `get_run_id()`, `bootstrap()` (centralized 3-step ceremony: generate_run_id → setup_logging → set_run_id)
- `requirements.txt` — pinned deps (pydantic, fastapi, uvicorn, tenacity)
- `conftest.py` — shared pytest fixtures (`MockEngineManager`, sample SGFs)
- `core/sgf_parser.py` — KaTrain-derived SGF parser; `SGF.parse_sgf()` → `SGFNode` tree
- `core/tsumego_analysis.py` — high-level SGF helpers: `parse_sgf()`, `extract_position()`, `compose_enriched_sgf()`
- `engine/local_subprocess.py` — `LocalEngine`: KataGo subprocess via JSON stdin/stdout
- `engine/config.py` — `EngineConfig`: paths, visits, threads
- `models/ai_analysis_result.py` — `AiAnalysisResult` (schema v10); final pipeline output; `RefutationEntry` includes `score_delta`, `wrong_move_policy`, `ownership_delta`; `teaching_signals: dict | None` field
- `models/analysis_request.py` — `AnalysisRequest` KataGo query payload
- `models/analysis_response.py` — `AnalysisResponse` parsed KataGo JSON
- `models/position.py` — `Position`, `Stone`, `Color` board state
- `models/solve_result.py` — `SolveTree`, `SolveNode` AI-solve tree
- `models/enrichment_state.py` — `EnrichmentRunState` mutable pipeline state
- `models/detection.py` — `Detection` single detector output
- `models/difficulty_estimate.py` — `DifficultyEstimate` score + level slug
- `models/validation.py` — `CorrectMoveResult`, `ValidationStatus`, `ConfidenceLevel`
- `models/refutation_result.py` — `RefutationResult` wrong-move branches
- `models/diagnostic.py` — `PuzzleDiagnostic` per-puzzle enrichment diagnostic (G10): stages_run, signals_computed, goal_agreement, phase_timings, qk_score, ac_level, enrichment_tier
- `analyzers/enrich_single.py` — top orchestrator: `enrich_single_puzzle()` async
- `analyzers/single_engine.py` — `SingleEngineManager` config-driven visits escalation. Supports `async with` context manager protocol. Contains `resolve_katago_config()` (centralized KataGo config resolution).
- `analyzers/query_builder.py` — `build_query_from_position()` / `build_query_from_sgf()` → `QueryResult` (no cropping; uses original board size)
- `analyzers/solve_position.py` — `analyze_position_candidates()` delta-based classification
- `analyzers/sgf_enricher.py` — `enrich_sgf()` writes YG/YX/YH/YQ/YR to SGF
- `analyzers/hint_generator.py` — 3-tier progressive hints from PV + board region
- `analyzers/instinct_classifier.py` — `classify_instinct()` from position geometry
- `analyzers/generate_refutations.py` — `generate_refutations()` wrong-move branch generation
- `analyzers/validate_correct_move.py` — correct-move SGF verification
- `analyzers/estimate_difficulty.py` — heuristic from PV depth + policy score
- `analyzers/technique_classifier.py` — aggregates all detectors → tag list
- `analyzers/frame_adapter.py` — tsumego frame: offense/defense stone fill
- `analyzers/property_policy.py` — when to write/skip/override SGF properties per `sgf-property-policies.json`
- `analyzers/config_lookup.py` — centralized tag/level config loaders (reads `config/`)
- `analyzers/observability.py` — `BatchSummary`, disagreement tracking
- `analyzers/teaching_signal_payload.py` — `build_teaching_signal_payload()`: builds structured teaching signal dict (Option B schema: version/correct_move/position/wrong_moves) from KataGo response + pipeline context. Config-driven thresholds via `TeachingSignalConfig`
- `analyzers/comment_assembler.py` — teaching comment assembly
- `analyzers/teaching_comments.py` — comment templates + formatting
- `analyzers/result_builders.py` — `make_error_result()`, `compute_config_hash()`
- `analyzers/entropy_roi.py` — `EntropyROI` region-of-interest from entropy
- `analyzers/ko_validation.py` — ko rule validation utilities
- `analyzers/liberty.py` — liberty-counting board helpers
- `analyzers/ascii_board.py` — ASCII board renderer (debug)
- `analyzers/benson_check.py` — Benson's unconditional life check
- `analyzers/vital_move.py` — vital point computation
- `analyzers/frame_utils.py` — frame helper utilities
- `analyzers/tsumego_frame_gp.py` — game-perspective frame builder
- `analyzers/refutation_classifier.py` — classify wrong-move types
- `analyzers/debug_export.py` — `export_debug_artifact()`: writes per-puzzle debug JSON (trap moves + 28-detector activation matrix) to `.lab-runtime/debug/{run_id}/`. Triggered by `--debug-export` CLI flag
- `analyzers/diagnostic.py` — `build_diagnostic_from_result()`: constructs `PuzzleDiagnostic` from `AiAnalysisResult`. Called in batch mode to write per-puzzle diagnostic JSON to `.lab-runtime/diagnostics/{run_id}/`
- `analyzers/stages/stage_runner.py` — `StageRunner.run_pipeline()` / `run_stage()` with timing+notify+error policy
- `analyzers/stages/protocols.py` — `EnrichmentStage` protocol, `PipelineContext`, `SgfMetadata`, `StageResult`, `ErrorPolicy`
- `analyzers/stages/parse_stage.py` — `SGFNode` + `Position` extraction
- `analyzers/stages/validation_stage.py` — correct-move existence check
- `analyzers/stages/query_stage.py` — builds `AnalysisRequest` via `query_builder.py`
- `analyzers/stages/analyze_stage.py` — KataGo call → `SolveResult`
- `analyzers/stages/technique_stage.py` — runs all detectors → tags
- `analyzers/stages/difficulty_stage.py` — `DifficultyEstimate` computation
- `analyzers/stages/refutation_stage.py` — wrong-move branch generation
- `analyzers/stages/teaching_stage.py` — assemble hints + teaching comments
- `analyzers/stages/assembly_stage.py` — build `AiAnalysisResult` from stage outputs
- `analyzers/stages/sgf_writeback_stage.py` — write SGF properties (YG, YT, YH, YQ, YR, YX, YC, YK, YO)
- `analyzers/stages/instinct_stage.py` — `InstinctStage` pipeline stage (name="instinct_classification", error_policy=DEGRADE)
- `analyzers/stages/solve_path_stage.py` — dispatch to appropriate solve path
- `analyzers/stages/solve_paths.py` — `run_position_only_path()`, `run_has_solution_path()`, `run_standard_path()`
- `analyzers/detectors/` — 28 `TechniqueDetector` subclasses: `LifeAndDeathDetector`, `KoDetector`, `LadderDetector`, `SnapbackDetector`, `NetDetector`, `ConnectionDetector`, `CuttingDetector`, `CaptureRaceDetector`, `ThrowInDetector`, `NakadeDetector`, `SekiDetector`, `SacrificeDetector`, `DoubleAtariDetector`, `ClampDetector`, `EscapeDetector`, `EyeShapeDetector`, `DeadShapesDetector`, `LibertyShortageDetector`, `VitalPointDetector`, `ConnectAndDieDetector`, `CornerDetector`, `EndgameDetector`, `FusekiDetector`, `JosekiDetector`, `LivingDetector`, `ShapeDetector`, `TesujiDetector`, `UnderTheStonesDetector`
- `scripts/` — maintenance/batch scripts
- `tests/` — pytest suite (unit + integration; `MockEngineManager` from `conftest.py`)
- `tests/_sgf_render_utils.py` — shared SGF regex parsing utilities (`parse_sgf_properties`, `parse_all_stones`, `parse_first_move`). Used by `render_fixtures.py` and `generate_review_report.py`.
- `tests/test_refutation_quality.py` — consolidated refutation quality tests (Phases A-D merged). 19 classes covering PI-1 through PI-12: ownership delta, score delta filter, model routing, adaptive visits, Dirichlet noise, forced min visits, player alternatives, branch escalation, multi-pass harvesting, best resistance, surprise-weighted calibration, integration tests (disagreement metric, merge re-ranking, noise helper, max queries).
- `tests/test_config_loading.py` — config infrastructure tests: file existence, JSON parsing, Pydantic validation, round-trip serialization, backward-compat (missing keys), KataGo .cfg parsing, teaching comments loader, KM config extension. 12 classes.
- `tests/test_config_values.py` — config value assertion tests: thresholds, level IDs, ownership regions, rank bands, difficulty estimation, deep enrich visits/model, tsumego settings, AI-solve defaults, depth profiles, level-category mapping. 17 classes.
- `tests/test_technique_calibration.py` — per-technique calibration test suite. `TechniqueSpec` TypedDict + `TECHNIQUE_REGISTRY` loaded from `tests/fixtures/technique-benchmark-reference.json` (OPT-1: JSON + Thin Loader). 25 active entries keyed by tag slug, each with `stability_tier` (green/yellow/red). 5 parametrized integration tests (correct_move, technique_tags with tier-dependent xfail for RED, difficulty_range, refutations, teaching_comments) + 3 unit tests (config cross-check, fixture existence, excluded-tag guard). Markers: `@pytest.mark.slow`, `@pytest.mark.integration`. `EXCLUDED_NON_TSUMEGO_TAGS = {joseki, fuseki, endgame}`.
- `tests/fixtures/technique-benchmark-reference.json` — externalized ground truth for technique calibration. 25 entries with calibration dimensions + `stability_tier` field (green/yellow/red per KataGo non-determinism sensitivity). `_metadata` block tracks schema version and last_updated. Regenerate with `scripts/regenerate_benchmark_reference.py`.
- `tests/fixtures/extended-benchmark/` — difficulty-stratified SGFs for top-5 techniques (life-and-death, ko, snapback, ladder, nakade). 13 SGFs with naming `{technique}_{level}_{source_id}.sgf`. Sourced from goproblems. Validated by `test_fixture_integrity.py::TestExtendedBenchmarkPopulation`.
- `tests/fixtures/instinct-calibration/` — 134 human-labeled SGFs for instinct classifier calibration. Naming: `{instinct}_{level}_{serial:03d}.sgf`. Labels in `labels.json` (multi-dimensional: instinct_primary, instinct_labels[], technique_tag, objective, human_difficulty). Sources: Sakata Eio (~110), Lee Changho (~16), Cho Chikun (~8). 6 instinct categories: cut, hane, descent, extend, push, null.
- `tests/test_instinct_calibration.py` — instinct classifier calibration suite. `TestGoldenCalibration` (existing golden-calibration/ tests, KataGo-dependent). `TestInstinctCalibration` (new instinct-calibration/ tests, no KataGo): AC-1 macro accuracy (≥70%), AC-2 per-instinct (≥60%), AC-3 HIGH-tier precision (≥85%), AC-4 null false-positive (0%). All 4 AC tests marked `xfail(strict=False)` — baseline calibration measurement.
- `scripts/regenerate_benchmark_reference.py` — re-derives expected calibration values by enriching all 25 technique fixtures through the pipeline. Modes: `--dry-run` (diff only) and write (updates JSON + timestamp). Uses `enrich_single_puzzle()` + `quick_only` mode.
- `pyproject.toml` — pytest local config: `testpaths=["tests"]`, `norecursedirs` excludes `.lab-runtime`, `models-data`, `tests/fixtures/scale` (8K+ SGF files — never scanned by pytest)
- `tests/test_bridge_config.py` — 11 unit tests for `bridge_config_utils.py` (unflatten, deep_merge, apply_config_overrides)

---

### 2. Core Entities

| Name | Module | Primary Responsibility | Key Fields/Properties |
|------|--------|----------------------|-----------------------|
| `AiAnalysisResult` | `models/ai_analysis_result.py` | Final enrichment output (schema v10) | `puzzle_id`, `level_slug`, `tags: list[str]`, `hints: list[str]`, `correct_move: str`, `refutations: list[str]`, `quality_metrics`, `complexity_metrics`, `validated: bool`, `confidence: ConfidenceLevel`, `goal_confidence_reason: str`, `teaching_signals: dict \| None` |
| `TeachingSignalConfig` | `config/teaching.py` | Teaching signal payload configuration | `enabled: bool` (default False), `max_wrong_moves: int` (3), `instructiveness_threshold: float` (0.05), `seki_closeness_threshold: float` (0.9), `ownership_delta_threshold: float` (0.3) |
| `PipelineContext` | `analyzers/stages/protocols.py` | Mutable state flowing between all pipeline stages | `sgf_text`, `root: SGFNode`, `position: Position`, `response: AnalysisResponse`, `analysis_result: AiAnalysisResult`, `engine_manager: SingleEngineManager`, `config: EnrichmentConfig`, `notify_fn`, `timings: dict`, `detection_results: list[DetectionResult] \\| None`, `instinct_results: list[InstinctResult] \\| None`, `policy_entropy: float`, `correct_move_rank: int`, `teaching_signals: dict \\| None` |
| `Position` | `models/position.py` | Board state with stone placement and coord helpers | `size: int`, `black_stones`, `white_stones`, `to_move: str`; methods: `get_puzzle_region_moves(margin)`, `to_katago_initial_stones()` |
| `AnalysisRequest` | `models/analysis_request.py` | KataGo JSON query payload | `id: str`, `rules: str`, `komi: float`, `board_size_x/y: int`, `initial_stones`, `moves`, `allowed_moves: list[str]`, `max_visits: int` |
| `AnalysisResponse` | `models/analysis_response.py` | Parsed KataGo JSON response | `id: str`, `root_info` (winrate, visits), `move_infos: list[MoveInfo]` |
| `EnrichmentConfig` | `config/__init__.py` | Pipeline configuration loaded from `config/katago-enrichment.json`. Composes all sub-config models. | `difficulty`, `refutations`, `ai_solve`, `models`, `deep_enrich`, etc. |
| `SgfMetadata` | `analyzers/stages/protocols.py` | Typed SGF metadata container (replaces bare dict) | `puzzle_id`, `tags: list[int]`, `corner`, `move_order`, `ko_type`, `collection`; supports `__getitem__`/`.get()` |
| `SGFNode` | `core/sgf_parser.py` | SGF tree node | `children: list[SGFNode]`, `properties: dict`, `move: str \| None`; root via `SGF.parse_sgf()` |
| `QueryResult` | `analyzers/query_builder.py` | AnalysisRequest + crop metadata | `request: AnalysisRequest`, `original_board_size: int`, `approach_ko_pv_may_truncate: bool` |
| `Detection` | `models/detection.py` | Single technique detector output | `detected: bool`, `confidence: float`, `tag: str`, `evidence: str` |
| `DifficultyEstimate` | `models/difficulty_estimate.py` | Heuristic difficulty result | `score: float`, `level_slug: str`, `confidence: ConfidenceLevel`, `confidence_reason: str` |
| `CorrectMoveResult` | `models/validation.py` | Correct-move validation output | `status: ValidationStatus`, `move: str`, `confidence: ConfidenceLevel`; flags include `rank_band:top3\|top10\|top20\|outside_top20`, `source_trust_rescue`, `semeai_ownership_polarized` |
| `RefutationResult` | `models/refutation_result.py` | Wrong-move SGF branches | `branches: list[dict]`, `refutation_moves: list[str]` |
| `InstinctResult` | `models/instinct_result.py` | Move intent classification | `instinct: str`, `confidence: float`, `evidence: str` |
| `PuzzleDiagnostic` | `models/diagnostic.py` | Per-puzzle enrichment diagnostic (G10) | `puzzle_id`, `stages_run`, `stages_skipped`, `signals_computed` (policy_entropy, correct_move_rank, trap_density), `goal_agreement`, `phase_timings`, `qk_score`, `ac_level`, `enrichment_tier` |
| All 28 detector classes | `analyzers/detectors/*.py` | `TechniqueDetector` subclasses — one per technique | `detect(position, context) -> Detection` |

---

### 3. Key Methods & Call Sites

- **`enrich_single_puzzle(sgf_text, engine_manager, config, ...) → AiAnalysisResult`**
  (`analyzers/enrich_single.py`) — Top-level async orchestrator. Builds `PipelineContext`, generates `trace_id`, dispatches solve path via `SolvePathStage`, calls `StageRunner.run_pipeline()`, finalizes timings.
  → _Called by_: `cli.py enrich`, `bridge.py POST /api/enrich`

- **`StageRunner.run_pipeline(stages, ctx) → (ctx, results)`**
  (`analyzers/stages/stage_runner.py`) — Executes ordered `EnrichmentStage` list; wraps each in `run_stage()` for timing, notify, and `ErrorPolicy` (FAIL_FAST vs CONTINUE).
  → _Called by_: `enrich_single_puzzle()` only

- **`build_query_from_sgf(sgf_text, ...) → QueryResult`**
  (`analyzers/query_builder.py`) — Parses SGF, extracts position, applies tsumego frame, restricts `allowed_moves` to puzzle region. All analysis on original board size (no cropping).
  → _Called by_: `AnalyzeStage.run(ctx)` inside `analyze_stage.py`

- **`analyze_position_candidates(query_result, engine_manager, ...) → SolveResult`**
  (`analyzers/solve_position.py`) — Sends `AnalysisRequest` to KataGo via `engine_manager`, classifies moves by winrate delta (TE/BM/NEUTRAL), optionally confirms top move with second query.
  → _Called by_: `AnalyzeStage.run(ctx)` inside `analyze_stage.py`

- **`enrich_sgf(sgf_text, result) → str`**
  (`analyzers/sgf_enricher.py`) — Applies enrichment to SGF tree: writes `YG`, `YX`, `YH`, `YQ`, `YR`; inserts refutation branches as child variations. Respects `sgf-property-policies.json` (`enrich_if_absent`, `override`, `enrich_if_partial`).
  → _Called by_: `SgfWritebackStage.run(ctx)` inside `sgf_writeback_stage.py`

- **`classify_instinct(position, correct_move_gtp, config) → list[InstinctResult]`**
  (`analyzers/instinct_classifier.py`) — Classifies move intent (push, hane, cut, descent, extend) from position geometry. Zero engine queries.
  → _Called by_: `InstinctStage.run(ctx)` inside `instinct_stage.py`

- **`compute_policy_entropy(move_infos, top_k) → float`**
  (`analyzers/estimate_difficulty.py`) — Shannon entropy of top-K policy priors; higher = more candidate moves = harder.
  → _Called by_: `DifficultyStage.run(ctx)`

- **`find_correct_move_rank(move_infos, correct_move_gtp) → int`**
  (`analyzers/estimate_difficulty.py`) — Rank of correct move in KataGo's policy prior ordering (0-indexed).
  → _Called by_: `DifficultyStage.run(ctx)`

- **`Position.rotate(degrees) → Position`**
  (`models/position.py`) — Returns a new Position rotated by 90/180/270 degrees.

- **`Position.reflect(axis) → Position`**
  (`models/position.py`) — Returns a new Position reflected along the specified axis.

- **`build_teaching_signal_payload(response, correct_move_gtp, policy_entropy, correct_move_rank, result, board_size, config) → dict | None`**
  (`analyzers/teaching_signal_payload.py`) — Builds Option B structured payload from KataGo response + pipeline context. Returns None if response is None. Includes correct-move signals (log_policy, score_lead_rank, play_selection_value), position signals (closeness, entropy, instructive gate), and wrong-move enrichments (score_delta, policy, refutation PV, conditional ownership).
  → _Called by_: `AssemblyStage.run(ctx)` inside `assembly_stage.py`

- **`generate_refutations(sgf_text, result, engine_manager) → RefutationResult`**
  (`analyzers/generate_refutations.py`) — For each wrong first-move, queries KataGo for refutation sequence; builds SGF child branches with `C[Wrong.]` comments.
  → _Called by_: `RefutationStage.run(ctx)` inside `refutation_stage.py`

- **`compute_ownership_delta(root_ownership, move_ownership, board_size) → float`**
  (`analyzers/generate_refutations.py`) — PI-1: Max absolute ownership change across all intersections. Used in composite refutation scoring when `ownership_delta_weight > 0`. Handles flat and nested ownership arrays.
  → _Called by_: `identify_candidates()` when ownership_delta_weight > 0

- **`SingleEngineManager.get_model_for_level(level_slug) → str | None`**
  (`analyzers/single_engine.py`) — PI-4: Resolves model filename for a puzzle's level category via `model_by_category` routing table. Returns None when routing inactive.
  → _Called by_: Future Phase B engine switching logic

- **`SingleEngineManager.model_label_for_routing(level_slug) → str`**
  (`analyzers/single_engine.py`) — PI-4: Returns model arch label for observability/metadata. Falls back to default when routing inactive.

- **`_assemble_opponent_response(condition, opponent_move, opponent_color, wrong_move_comment) → str`**
  (`analyzers/comment_assembler.py`) — PI-10: Assembles condition-keyed opponent-response phrase. 5 active conditions, 7 suppressed. Applies conditional dash rule (omit dash when WM already has em-dash).
  → _Called by_: `assemble_wrong_comment()` when `use_opponent_policy=True`

- **`SGF.parse_sgf(sgf_text) → SGFNode`**
  (`core/sgf_parser.py`) — Low-level KaTrain-derived parser. Returns root `SGFNode`. Raises `ParseError` on malformed SGF.
  → _Called by_: `core/tsumego_analysis.parse_sgf()` (entry point for all stages needing the tree)

- **`build_query_from_position(position, ...) → QueryResult`**
  (`analyzers/query_builder.py`) — Builds query directly from a `Position` object (no re-parsing). Uses framed position if available.
  → _Called by_: `AnalyzeStage.run(ctx)` inside `analyze_stage.py`

---

### 4. Data Flow

```
CLI/bridge.py receives sgf_text
  │
  ▼ enrich_single_puzzle() builds PipelineContext
  │   (engine_manager injected, trace_id generated)
  │
  ▼ StageRunner.run_pipeline() executes stages in order:
  ├── parse_stage        SGFNode + Position extracted from sgf_text
  ├── analyze_stage      AnalysisRequest built + KataGo called via engine_manager → SolveResult
  │                        (original board size; allowed_moves restricted via ROI)
  ├── validation_stage   correct-move existence checked; ValidationStatus set
  ├── refutation_stage   wrong-move branches generated (one KataGo call per refutation)
  ├── difficulty_stage   DifficultyEstimate + policy_entropy + correct_move_rank computed
  ├── assembly_stage     AiAnalysisResult built from all stage outputs + teaching_signals payload
  ├── technique_stage    28 Detectors run → tag slug list; stores ctx.detection_results
  ├── instinct_stage     classify_instinct() → ctx.instinct_results (zero engine queries)
  ├── teaching_stage     reads detection_results, instinct_results, level_category → hints + comments
  └── sgf_writeback_stage  SGF properties written:
                             YG (level), YT (tags), YH (hints),
                             YQ (quality), YR (refutations),
                             YX (complexity), YC (corner),
                             YK (ko), YO (move order)
  │
  ▼ AiAnalysisResult returned to caller
```

**Coordinate boundary**: All KataGo communication uses GTP coords (`"C16"`). SGF read/write uses SGF coords (`"ab"`). Conversion happens in `query_builder.py` on input and response parsing. No cropping — all analysis on original board size.

---

### 5. Coordinate Systems & Gotchas

- **SGF coords**: two-char lowercase `"ab"` — col=`a`=0, row=`b`=1, origin = top-left of board
- **GTP coords**: `"C16"` — column letter (skips `'I'`), row number counts from BOTTOM (row 1 = bottom row)
- **Conversion**: `Position.to_katago_initial_stones()` returns GTP-format list; `Stone.gtp_coord_for(board_size)` converts a single stone; `Stone.from_sgf(color, coord)` parses SGF coord
- **No board cropping**: All analysis runs on the original board size (V2 removed cropping). Region of interest is controlled via `allowMoves` from entropy ROI or stone bounding box
- **`engine_manager` is injected, never imported directly**: `SingleEngineManager` wraps `LocalEngine` (KataGo subprocess). Never instantiate `LocalEngine` inside stages — always receive via `PipelineContext.engine_manager`
- **All stages are `async`**: `StageRunner.run_stage()` is the timing/error boundary. Blocking I/O inside a stage will stall the entire pipeline
- **`_TSUMEGO_KOMI = 0.0`** hardcoded in `query_builder.py` — tsumego is life-and-death; scoring irrelevant; non-zero komi biases winrate thresholds
- **`ErrorPolicy.FAIL_FAST` vs `CONTINUE`**: `parse_stage` and `validation_stage` are `FAIL_FAST` (broken SGF aborts pipeline). Analysis/technique stages are `CONTINUE` (partial results still serialized)
- **Solve path dispatch**: `SolvePathStage` routes to one of three paths — `run_position_only_path()` (no solution in SGF), `run_has_solution_path()` (solution present, skip solve), `run_standard_path()` (default)
- **Tests use `MockEngineManager`** — never real KataGo in unit tests; `conftest.py` provides fixture; integration tests marked `@pytest.mark.integration`
- **`SgfMetadata` has `__getitem__`/`.get()`** for backward compat; new code accesses fields directly (`ctx.metadata.puzzle_id`, not `ctx.metadata["puzzle_id"]`)
- **`AI_ANALYSIS_SCHEMA_VERSION = 10`** in `models/ai_analysis_result.py` — bump when output schema changes; downstream consumers use this to detect stale cached results
- **28 detector files exist** in `analyzers/detectors/` — one per technique tag in `config/tags.json`
- **Teaching comment voice principles (VP-1 through VP-5)** govern all teaching comment templates (D73 ADR). Key rules: (1) VP-1: board speaks first — never narrate student's error, (2) VP-2: action→consequence with `—` separator, (3) VP-3: verb-forward, drop leading articles unless grammatically required, (4) VP-4: 15-word hard cap on combined wrong-move + opponent-response, (5) VP-5: warmth only for `almost_correct`, zero sentiment elsewhere
- **Opponent-response composition**: Wrong-move comments have optional opponent-response appended. 12 conditions keyed 1:1 — 5 emit opponent-response (immediate_capture, capturing_race_lost, self_atari, wrong_direction, default), 7 suppress (WM already describes opponent action). Conditional dash rule: if WM contains `—`, OR omits dash. Config-driven via `opponent_response_templates.enabled_conditions` in `config/teaching-comments.json`. Feature-gated: `use_opponent_policy=False` in `TeachingConfig` disables entirely. Raw teaching config cache lives in `config/teaching.py` (`load_raw_teaching_config()`), cleared by `clear_teaching_cache()`.
- **PI-1 Ownership delta scoring**: `compute_ownership_delta()` in `generate_refutations.py` computes max ownership change per candidate. Composite scoring in `identify_candidates(board_size=)`: `wr_delta * (1-w) + ownership_delta * w` where `w = ownership_delta_weight`. Default 0.0 = winrate-only (no behavior change). `board_size` parameter passed from `generate_refutations()` via `position.board_size` — enables correct ownership delta on 9×9 and 13×13 boards. Config: `refutations.ownership_delta_weight` in `RefutationsConfig`.
- **PI-3 Score delta rescue**: In `identify_candidates()`, when `score_delta_enabled=True`, moves excluded by `min_policy` can be rescued if `abs(root_score - score_lead) >= score_delta_threshold`. Default disabled. Config: `refutations.score_delta_enabled`, `refutations.score_delta_threshold` in `RefutationsConfig`.
- **PI-4 Model routing by complexity**: `SingleEngineManager.get_model_for_level(level_slug)` uses `ai_solve.model_by_category` + `get_level_category()` from `config/helpers.py` to route puzzles to appropriate model (e.g., b10c128 for entry, b18c384 for core). `model_label_for_routing()` returns arch label. Default: `{"strong": "referee"}` (routes advanced/expert to b28).
- **`voice_constraints` in config** forbids templates starting with "The "/"This "/"A "/"Your " and phrases containing "your mistake"/"your error"/"after you". Enforced in tests.
- **Phase A refutation quality config keys (v1.18)**: `refutations.ownership_delta_weight` (PI-1, default 0.0), `refutations.score_delta_enabled` + `score_delta_threshold` (PI-3, default false/5.0), `ai_solve.model_by_category` (PI-4, default empty dict), `teaching.use_opponent_policy` (PI-10, default false). All feature-gated: absent key = current behavior.
- **Phase B refutation quality config keys (v1.19)**: `solution_tree.visit_allocation_mode` (PI-2, default "fixed"), `solution_tree.branch_visits` (PI-2, default 500), `solution_tree.continuation_visits` (PI-2, default 125), `refutation_overrides.noise_scaling` (PI-5, default "fixed"), `refutation_overrides.noise_base` (PI-5, default 0.03), `refutation_overrides.noise_reference_area` (PI-5, default 361), `refutations.forced_min_visits_formula` (PI-6, default false), `refutations.forced_visits_k` (PI-6, default 2.0), `solution_tree.player_alternative_rate` (PI-9, default 0.0), `solution_tree.player_alternative_auto_detect` (PI-9, default true). All feature-gated: absent key = current behavior.
- **PI-2 adaptive visit allocation**: In `_build_tree_recursive()` (solve_position.py ~L946), when `visit_allocation_mode=="adaptive"`, branch (decision-point) nodes use `branch_visits` (500), continuation/forced nodes use `continuation_visits` (200). Feature gate: `"fixed"` = all nodes get `tree_visits` (current behavior). **Note (v1.26)**: adaptive mode compounds edge-case boosts (corner_visit_boost, ladder_visit_boost) with `branch_visits` — `build_solution_tree()` starts from `branch_visits` as base, then applies boosts multiplicatively: `effective_visits = branch_visits * boost_factor`. In fixed mode, boosts are applied to `tree_visits` as before.
- **PI-5 board-size-scaled noise**: In `generate_refutations()` (generate_refutations.py ~L643), when `noise_scaling=="board_scaled"`, `effective_noise = noise_base * noise_reference_area / board_area`. 9×9 gets more noise (~0.134), 19×19 gets less (~0.030). Feature gate: `"fixed"` = `wide_root_noise=0.08` used unchanged.
- **PI-6 forced minimum visits**: In `generate_single_refutation()` (generate_refutations.py ~L333), when `forced_min_visits_formula=True`, `nforced(c) = sqrt(k * P(c) * total_visits)`. Forces low-policy sacrifice/throw-in moves to get adequate exploration. Feature gate: `False` = no forced visits.
- **PI-9 player alternative exploration**: In `_build_tree_recursive()` (solve_position.py ~L1317), at player nodes, explores up to 2 alternatives with probability `player_alternative_rate`. Auto-detect in `run_position_only_path()` (solve_paths.py ~L103) sets rate=0.05 for position-only puzzles. Feature gate: `rate=0.0` = no alternatives explored (must-hold #4 safeguard).
- **Phase C refutation quality config keys (v1.20)**: `solution_tree.branch_escalation_enabled` (PI-7, default false), `solution_tree.branch_disagreement_threshold` (PI-7, default 0.10), `refutations.multi_pass_harvesting` (PI-8, default false), `refutations.secondary_noise_multiplier` (PI-8, default 2.0), `refutations.best_resistance_enabled` (PI-12, default false), `refutations.best_resistance_max_candidates` (PI-12, default 3). All feature-gated: absent key = current behavior.
- **PI-7 branch-local disagreement escalation**: In `_build_tree_recursive()` (solve_position.py), at opponent nodes after evaluating a branch, compares child winrate against first (policy-top) sibling's winrate. If `abs(child.winrate - first_child_winrate) > branch_disagreement_threshold`, re-evaluates with escalated visits (2x). Capped by `max_total_tree_queries`. Feature gate: `branch_escalation_enabled=False` = no escalation.
- **PI-8 diversified root candidate harvesting**: In `generate_refutations()` (generate_refutations.py), after initial `identify_candidates()`, runs a secondary analysis pass with `noise * secondary_noise_multiplier`. Merges, deduplicates, re-sorts by `policy_prior`, and caps at `candidate_max_count`. Uses shared `_calculate_effective_noise()` helper for board-scaled noise. Feature gate: `multi_pass_harvesting=False` = single pass.
- **PI-12 best-resistance line generation**: In `generate_single_refutation()` (generate_refutations.py), after getting opponent response, evaluates top N alternative responses and selects the one with highest punishment signal (`abs(1 - opp_wr - initial_wr)`). Feature gate: `best_resistance_enabled=False` = uses top-visited response.
- **PI-1 ownership delta scoring**: `compute_ownership_delta()` computes max |root_own[i] - move_own[i]| across all intersections. Composite scoring: `wr_delta * (1-w) + ownership_delta * w`. Weight=0.0 = winrate-only (current behavior).
- **PI-3 score delta**: Complementary filter in `generate_single_refutation()`. Candidate qualifies if EITHER winrate delta OR score delta exceeds threshold. Checked BEFORE suboptimal_branches fallback.
- **PI-4 model routing**: `get_model_for_level()` maps level→category→model. Phase A is query-only (no engine restart). Phase B will use this for actual engine switching.
- **Observability: `opponent_response_emitted`**: Counter in `BatchSummary` and `BatchSummaryAccumulator.record_puzzle()`. Tracks puzzles where opponent-response was appended (PI-10, `use_opponent_policy=True` and condition is in `enabled_conditions`).
- **Observability: `max_queries_per_puzzle`** (MH-7): Field in `BatchSummary` tracking the maximum engine queries consumed by any single puzzle in a batch. Accumulated via `BatchSummaryAccumulator`. Used for compute monitoring before PI-7/PI-12 activation.
- **Teaching signal payload (Option B schema)**: `build_teaching_signal_payload()` in `analyzers/teaching_signal_payload.py` emits structured signals for future LLM consumption. Schema: `{version: 1, correct_move: {gtp_coord, log_policy_score, score_lead_rank, play_selection_value}, position: {position_closeness, board_size, policy_entropy, instructive (gated by threshold)}, wrong_moves: [{gtp_coord, score_delta, wrong_move_policy, refutation_depth, refutation_pv, refutation_type, ownership_delta_max (conditional)}]}`. Thresholds driven by `TeachingSignalConfig`. Built in `AssemblyStage` after refutations are wired. Stored on `ctx.teaching_signals` then persisted to `result.teaching_signals`.
- **RefutationEntry enriched fields**: `score_delta: float` (score change from correct line), `wrong_move_policy: float` (KataGo policy prior for the wrong move), `ownership_delta: float` (max ownership swing from root). All default to 0.0. Populated in `build_refutation_entries()` from `Refutation` internal model. Used by teaching signal payload for wrong-move enrichment.
- **Phase D refutation quality config keys (v1.21)**: `calibration.surprise_weighting` (PI-11, default false), `calibration.surprise_weight_scale` (PI-11, default 2.0). Feature-gated: absent key = current behavior (uniform weighting).
- **PI-11 surprise-weighted calibration**: `compute_surprise_weight()` in `config/infrastructure.py` computes `weight = 1 + scale * |T0_winrate - T2_winrate|`. Positions where the engine disagrees with itself across visit tiers T0 (50v policy snapshot) vs T2 (2000v deep analysis) get higher calibration weight. Used by calibration pipeline (scripts/run_calibration.py) for threshold optimization. Feature gate: `surprise_weighting=False` = all positions weight 1.0 (uniform).

---

### 6. External Dependencies

| Library | Used For |
|---------|----------|
| `pydantic` | Config models (`EnrichmentConfig`, `EngineConfig`), request/response validation (`AnalysisRequest`, `AnalysisResponse`, `Position`, `AiAnalysisResult`) |
| `sgfmill` | **NOT used here** — `tools/puzzle-enrichment-lab` uses its own KaTrain-derived parser in `core/sgf_parser.py` |
| `fastapi` + `uvicorn` | `bridge.py` GUI server; SSE streaming (`/api/enrich`), `GET /api/config`, REST endpoints |
| `asyncio` | Engine communication via `LocalEngine` stdin/stdout; stage pipeline execution |
| `KataGo` (subprocess) | `engine/local_subprocess.py` spawns `KataGo.exe`/`katago`; communicates via JSON analysis protocol on stdin/stdout |
| `typer` | CLI argument parsing in `cli.py` |
| `tenacity` | Retry logic on KataGo engine failures (transient crashes, timeouts) |
| `pytest` | Test suite; markers: `unit`, `integration`, `slow`, `golden5`, `calibration` — from repo root: `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short` |

**Engine manager pattern**: `SingleEngineManager` is injected; stages never call KataGo directly. Engine is only referenced in `analyze_stage.py` via `engine_manager.analyze(request)`.

---

## 5. External Dependencies

| Library | Used For |
|---------|----------|
| `pydantic` | Config models (`config.py`), all models in `models/` |
| `typer` | CLI (`cli.py`) |
| `fastapi` + `uvicorn` | Web bridge (`bridge.py`) |
| `sgfmill` | NOT used here — this module uses its own `core/sgf_parser.py` (KaTrain-MIT port) |
| `asyncio` | All engine calls are `async` |

---

## 6. Known Gotchas

- **`.cfg v2 audit (2026-03-20)`**: 4 unused keys removed (`allowSelfAtari`, `analysisWideRootNoise`, `cpuctExplorationAtRoot`, `scoreUtilityFactor`), exploration params restored to KataGo defaults, `staticScoreUtilityFactor=0.1` added for seki detection. See initiative `20260320-2200` changelog.
- **Coordinate systems**: SGF `"ab"` ≠ GTP `"C16"`. Conversion is in `query_builder.py`. Never pass GTP coords to SGF functions or vice versa.
- **No cropping**: Board cropping was removed in V2. All analysis runs on original board size. Region restriction uses `allowMoves` via entropy ROI.
- **Engine manager is async**: All engine calls must be awaited. `SyncEngineAdapter` in `solve_position.py` bridges sync callers (tree builder) to the async engine. Uses `asyncio.get_running_loop()` to detect context and `asyncio.run()` for worker-thread-safe execution.
- **Curated-aware teaching comments**: `refutation_type` ("curated", "ai_generated", etc.) propagates from `generate_refutations.py` → `RefutationEntry` → `ClassifiedRefutation` → `teaching_comments.py`. Curated wrongs (authored by puzzle creator) bypass the `almost_correct_threshold` gate — the author's "Wrong" judgment takes precedence over KataGo's near-zero delta. Non-curated (AI-generated) wrongs still benefit from the "Close, but not the best move." label when delta is below threshold.
- **Terse label replacement**: `_embed_teaching_comments()` in `sgf_enricher.py` uses `_is_terse_correctness_label()` (backed by canonical `tools/core/sgf_correctness.py`) to detect bare correctness markers ("Wrong", "Incorrect.", "-", "+", etc.). Terse labels are *replaced* by richer teaching comments; substantive author comments are preserved via append. This prevents doubled prefixes like `C[Wrong\n\nWrong. ...]`.
- **Canonical correctness detection**: `sgf_enricher.py` imports `infer_correctness_from_comment()` from `tools/core/sgf_correctness.py` (the single source of truth for all correctness markers across 80K+ SGF files). This replaces the former `_WRONG_COMMENT_PREFIXES` tuple and ensures consistent detection of all conventions: wrong/incorrect/-, correct/right/+.
- **Delta-based classification**: `solve_position.py` uses `root_winrate - move_winrate` delta, NOT absolute thresholds. Thresholds are in `EnrichmentConfig` (`t_good`, `t_bad`, `t_hotspot`).
- **`komi = 0.0` for tsumego**: Hard-coded in `query_builder.py` (`_TSUMEGO_KOMI`). Overrides any SGF komi.
- **Three solve paths**: Puzzles with existing SGF solution trees use `HasSolutionSolvePath`; sparse position-only puzzles use `PositionOnlySolvePath`. Path selected in `solve_path_stage.py`.
- **`enrich_sgf()` caches config**: Call `clear_enricher_cache()` between tests or config changes.
- **`_count_existing_refutation_branches(root) → int`**: Counts wrong-move root children (WV, BM, or Wrong comment). Used for cap budget calculation.
- **`_collect_existing_wrong_coords(root) → set[str]`**: Collects SGF coords of curated wrong branches. Used for dedup and YR derivation.
- **`_load_max_refutation_root_trees() → int`**: Reads `ai_solve.solution_tree.max_refutation_root_trees` from config (default 3).
- **Detector interface**: All detectors inherit `TechniqueDetector` (ABC). Method is `detect(position: Position) -> Detection`. No engine access in detectors — purely board-based.
- **InstinctStage depends on position geometry, NOT KataGo analysis** (C-1: zero new engine queries). Classification uses stone adjacency/direction patterns.
- **Detection evidence flows through to Tier 2 hints**: `TechniqueStage` stores `ctx.detection_results`; `TeachingStage` reads them for evidence-enriched reasoning instead of generic depth text.
- **Level-adaptive hints**: `TeachingStage` keys on `get_level_category()` from `config/helpers.py`. Level-adaptive branching is implemented directly in `_generate_reasoning_hint()` in `hint_generator.py` (entry/core/strong paths).
- **New config models**: `InstinctConfig` (confidence thresholds + instinct phrases) in `config/teaching.py`.
- **`PuzzleDiagnostic` model**: `models/diagnostic.py` — Pydantic model capturing stages_run, stages_skipped, signals_computed (policy_entropy, correct_move_rank, trap_density), goal_agreement, phase_timings, qk_score (0-5), ac_level (0-3), enrichment_tier (0-3). Built by `build_diagnostic_from_result()` in batch mode. Aggregated by `BatchSummaryAccumulator.record_diagnostic()`.
- **Debug export**: `analyzers/debug_export.py` — `export_debug_artifact()` writes trap_moves (top-5) + detector_matrix (28 booleans) to `.lab-runtime/debug/{run_id}/{puzzle_id}.debug.json`. Triggered by `--debug-export` CLI flag. Non-critical: failures are caught and logged at WARNING.
- **`_compute_qk()` in `sgf_enricher.py`**: Quality score (0-5) = `round(qk_raw * 5)` where `qk_raw = 0.40*trap_density + 0.30*norm(avg_depth) + 0.20*norm(clamp(rank)) + 0.10*entropy`. Visit gate: `rank_min_visits=500`, `low_visit_multiplier=0.7`. Weights from `QualityWeightsConfig` in `config/difficulty.py`, loaded from `config/katago-enrichment.json` → `quality_weights`.
- **Extended `_build_yx()`**: YX property now includes `w:` (weighted complexity) field in addition to `d:depth;r:refutations;s:solution_length;u:unique`. The `a:` field carries avg refutation depth.
- **Extended `_build_yq()`**: YQ property includes `qk:` field (quality score 0-5) computed by `_compute_qk()`. Format: `q:{q};rc:{rc};hc:{hc};ac:{ac};qk:{qk}`.
- **Hint generator atari gating**: `ATARI_SKIP_TAGS` in `hint_generator.py` suppresses atari hints for `capture-race`, `ko`, `sacrifice`, `snapback`, `throw-in`. `TIER3_DEPTH_THRESHOLD=3` gates coordinate outcome text. `TIER3_TACTICAL_SUPPRESS_TAGS` suppresses Tier 3 coordinate hints for tags where the first move IS the answer (`net`, `ladder`, `snapback`, `throw-in`, `oiotoshi`) — regardless of depth.
- **Wrong-move prefix enforcement**: `_embed_teaching_comments()` ensures ALL wrong-move comments start with canonical `"Wrong."` prefix. No special-casing for "Close" or other template outputs. This guarantees `infer_correctness_from_comment()` always detects wrong branches.
- **Almost-correct template is spoiler-free**: The `almost_correct` teaching template is `"Close, but not the best move."` (no coordinate token). `teaching_comments.py` passes `coord=""` for almost-correct moves to prevent leaking correct-move coordinates.
- **Curated+AI refutation cap**: AI branches are added alongside existing curated wrongs, capped by `max_refutation_root_trees` (default 3). `_count_existing_refutation_branches(root)` counts curated wrongs; `budget = max(0, cap - existing_count)`. AI branches are deduped against curated wrong coords via `_collect_existing_wrong_coords(root)`. YR property indexes ALL wrong-move coords in the tree (curated + AI combined). When cap is reached and no AI branches added, YR indexes curated wrong coords only.
- **Net tag priority**: `TAG_PRIORITY["net"] == 1` in `technique_classifier.py`. Net (geta) is a high-priority tactical pattern that wins over generic life-and-death detection.
- **Level mismatch strict threshold**: `_enrich_sgf_properties()` uses `distance > threshold` (strict greater-than) for level overwrite. Distance == threshold preserves the curated level.
- **Hint generator solution-aware fallback**: `infer_technique_from_solution()` uses `InferenceConfidence` enum (LOW/MEDIUM/HIGH). Only HIGH+ triggers technique hints. `HintOperationLog` dataclass captures per-tier decisions for observability.
- **Observability extended fields**: `BatchSummary` tracks `opponent_response_emitted` (PI-10 counter), `max_queries_per_puzzle` (MH-7 compute monitoring). `PipelineContext` carries `policy_entropy: float` and `correct_move_rank: int` from `DifficultyStage`.
- **Config v1.22-v1.24 changes**: `quality_weights` section (v1.22), feature activation Phase 1a-1c (v1.23: PI-1/PI-3/PI-5/PI-6/PI-10/PI-11/PI-12 enabled), Phase 2 (v1.24: PI-2/PI-7/PI-8/PI-9 enabled with C7 budget constraints).
