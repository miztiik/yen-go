# Research Brief: Enrichment-Lab Objective Matrix

## 1) Research Question And Boundaries

Question: In current repository state, which enrichment objectives are fully implemented end-to-end (code + config + tests + runtime wiring), and which remain partial/deferred versus the research corpus (gogogo findings, AI-solve plan/remediation, Kishimoto plan/tasks, and hinting transition docs)?

Boundaries:
- Scope constrained to tools/puzzle-enrichment-lab and enrichment-related docs in TODO and docs.
- No frontend/backend architecture expansion beyond direct enrichment-lab integration points.
- Evidence precedence: implementation > tests > config > plan checkbox status.
- "Fully met" requires runtime wiring and non-mock validation path availability, not only model/unit scaffolding.

## 2) Corpus Map (SRC)

| id | source_doc | key objectives proposed | notes |
|---|---|---|---|
| SRC-1 | TODO/initiatives/20260315-research-gogogo-tactics-patterns/00-charter.md | AC-1 multi-orientation detector tests >=12; AC-2 negative tests coverage; AC-3 instinct-to-hint mapping; explicit NG-1..NG-5 (F-4/F-6/F-7 deferred) | Canonical objective + non-goal baseline for this initiative |
| SRC-2 | TODO/initiatives/20260315-research-gogogo-tactics-patterns/15-research.md | F-4 urgency scoring, F-6 static life/death heuristic, F-7 feature-plane style evidence matrix, F-5 testing upgrades, F-9 entropy, F-14 tempting-wrong-move framing | Research recommends selective adoption; several items intentionally deferred |
| SRC-3 | TODO/initiatives/20260315-research-gogogo-tactics-patterns/10-clarifications.md | Governance clarified F-4/F-6/F-7 as explicit non-goals | Confirms defer intent was deliberate, not omission |
| SRC-4 | TODO/ai-solve-enrichment-plan-v3.md | Unified all-puzzle AI flow, A/B/C root allocation, AC levels, disagreement observability, stopping conditions | Design target for AI-solve path |
| SRC-5 | TODO/ai-solve-remediation-sprints.md | 20-gap closure across S1..S5 with many [x], but panel sign-off gates still open | Important for "implemented vs approved" distinction |
| SRC-6 | TODO/kishimoto-mueller-search-optimizations.md | KM-01 simulation, KM-02 transposition, KM-03 forced move, KM-04 proof-depth, L3 depth-dependent policy | Search optimization design contract |
| SRC-7 | TODO/kishimoto-mueller-tasks.md | Task-level completion claims for KM work, including benchmark/doc gates | Contains claimed completion and gate checklist |
| SRC-8 | TODO/hinting-unification-transition-plan-v1.md | Contract-first unification roadmap between lab/backend hinting | Draft transition plan, not completion evidence |
| SRC-9 | docs/architecture/backend/hint-architecture.md | Technique->Reasoning->Coordinate architecture, confidence-gated fallback | Production-facing architecture expectation |
| SRC-10 | docs/concepts/hints.md | YH format semantics and instinct/detection-evidence narration | Concept contract for hint consumers |

## 3) Internal Implementation Evidence (EVD)

| id | objective area | code wiring evidence | config evidence | test evidence | mock-free status |
|---|---|---|---|---|---|
| EVD-1 | Instinct stage wiring to teaching/hints | analyzers/stages/instinct_stage.py class InstinctStage writes ctx.instinct_results; analyzers/enrich_single.py includes InstinctStage in stage list; analyzers/hint_generator.py consumes instinct_results | config/teaching.py get_instinct_config used in stage/hints | tests/test_multi_orientation.py TestInstinctStage + instinct rotation tests | Partially mock-heavy (unit), runtime wired |
| EVD-2 | Detection evidence flow into Tier-2 hints | analyzers/stages/technique_stage.py sets ctx.detection_results; analyzers/stages/teaching_stage.py passes detection_results; analyzers/hint_generator.py uses dr.evidence | Uses existing teaching config; no extra key needed | tests/test_technique_classifier.py run_detectors + detector suites | Mostly unit; runtime wired |
| EVD-3 | Policy entropy + correct move rank computation | analyzers/estimate_difficulty.py compute_policy_entropy and find_correct_move_rank; analyzers/stages/difficulty_stage.py computes and stores ctx.policy_entropy + ctx.correct_move_rank | No dedicated persisted key | tests/test_multi_orientation.py entropy/rank unit tests | Partially wired: computed, but not fully surfaced downstream |
| EVD-4 | AI-solve root-tree allocation A/B/C | analyzers/stages/solve_paths.py loops max_refutation_root_trees and max_correct_root_trees after primary tree | config/solution_tree.py max_correct_root_trees and max_refutation_root_trees; config/katago-enrichment.json values present | tests/test_ai_solve_config.py bounds/default tests; tests/test_remediation_sprints.py references | Runtime wired |
| EVD-5 | AC level end-to-end to YQ | analyzers/stages/assembly_stage.py sets result.ac_level; analyzers/sgf_enricher.py _build_yq appends ac value | No extra config key required | tests/test_ai_solve_integration.py ac serialization tests; tests/test_remediation_sprints.py ac tests | Runtime wired |
| EVD-6 | Human-solution confidence + AI validation wiring | analyzers/stages/solve_paths.py sets state.human_solution_confidence and state.ai_solution_validated; analyzers/stages/assembly_stage.py propagates | Thresholds in ai_solve config path | tests/test_remediation_sprints.py and test_ai_solve_integration.py | Runtime wired |
| EVD-7 | KM-01..KM-04 + L3 algorithm hooks | analyzers/solve_position.py simulation, transposition cache, forced-move fast path, max_resolved_depth, depth_policy_scale pruning counter | config/solution_tree.py and config/difficulty.py include fields; config/katago-enrichment.json has v1.15+ keys | tests/test_solve_position.py covers simulation/transposition/forced/depth-policy/proof-depth mechanics; tests/test_difficulty.py proof-depth weighting | Mostly unit/mocked; live benchmark evidence absent in targeted test name |
| EVD-8 | Batch summary + disagreement sink runtime usage | analyzers/observability.py defines sinks/accumulator; cli.py _run_batch_async constructs DisagreementSink and BatchSummaryAccumulator and records per puzzle | disagreement sink path from ai_solve.observability | tests/test_remediation_sprints.py sink/summary tests; tests/test_ai_solve_integration.py disagreement serialization | Runtime wired in batch CLI |
| EVD-9 | F-4 urgency field on detections | models/detection.py DetectionResult has detected/confidence/tag_slug/evidence only; no urgency/priority field | No urgency key in solution tree/detection models | No urgency tests found | Not implemented |
| EVD-10 | F-6 static life/death weighted heuristic | No eye/liberty/group-size weighted formula found in analyzers | No dedicated config fields for static formula | No tests for weighted static formula | Not implemented |
| EVD-11 | F-7 feature-plane/detection-matrix output | Detection list exists, but no explicit activation-matrix artifact/output interface found | No matrix output schema key found | No matrix snapshot tests found | Partially implemented conceptually only |
| EVD-12 | Test strategy quality target from SRC-1 AC-1 | test_multi_orientation.py provides rotational coverage for push + ladder/ko/snapback/net/throw-in | N/A | Coverage remains below charter target >=12 detectors | Not fully met |
| EVD-13 | Mock-only caveat in integration-labeled AI-solve tests | tests/test_ai_solve_integration.py and tests/test_remediation_sprints.py explicitly state "Uses mock engines" | N/A | Mixed suite includes true integration elsewhere (test_correct_move.py, test_refutations.py) | Full no-mock evidence is uneven by objective |

## 4) Objective Status Matrix (OBJ)

| id | objective | source_doc | status | rationale | blocking gaps | recommended action |
|---|---|---|---|---|---|---|
| OBJ-1 | AC-1 multi-orientation detector coverage >=12 | SRC-1 | not_met | Multi-orientation infra exists, but detector-rotation coverage observed in fewer than target detector families | Additional detector rotation suites missing | Add rotation parametrized tests for 7+ additional detectors to reach >=12 |
| OBJ-2 | AC-2 negative test completeness | SRC-1 | partially_met | Broad negative tests exist across detector suites; prior gap was cutting positive completeness | Need explicit objective-level audit to confirm full 28/28 today | Add audit test enumerating all detector classes and asserting at least one negative case each |
| OBJ-3 | Instinct-to-hint pedagogical mapping | SRC-1/SRC-2 | partially_met | Instinct classification and Tier-1 prefix wiring are present; formal 8-instinct mapping table contract is doc-level, not asserted in contract tests | No explicit contract test for all 8 mappings | Add golden mapping test asserting each instinct phrase and fallback behavior |
| OBJ-4 | F-4 urgency/priority scoring on DetectionResult | SRC-2 (NG-1 in SRC-1) | not_met | DetectionResult schema has no urgency field; no ranking pipeline based on urgency | Schema + downstream ordering absent | Keep deferred unless approved as schema evolution (v3+) |
| OBJ-5 | F-6 static life/death weighted heuristic | SRC-2 (NG-2 in SRC-1) | not_met | No implementation of eye/liberty/group-size weighted confidence formula | No model/config/tests for formula | Keep deferred; only reconsider with calibration evidence against KataGo outputs |
| OBJ-6 | F-7 feature-plane style evidence matrix | SRC-2 (NG-3 in SRC-1) | partially_met | Detection evidence list exists and is consumed for hints, but no explicit activation matrix/debug artifact | Missing matrix serializer/output/test contract | If needed, add optional debug matrix output without changing runtime scoring |
| OBJ-7 | Unified AI-solve path for position-only and has-solution puzzles | SRC-4/SRC-5 | fully_met | SolvePathStage dispatch and dedicated path logic are wired; assembly reflects path outcomes | Governance approvals still open in docs | Preserve implementation; close governance gates with rerun evidence |
| OBJ-8 | AC level serialized to YQ ac:N | SRC-4/SRC-5 | fully_met | ac_level computed in AssemblyStage and written in _build_yq | None | Maintain with regression tests |
| OBJ-9 | KM-01..KM-04 and L3 search optimizations | SRC-6/SRC-7 | partially_met | Code/config/tests for simulation/transposition/forced/proof-depth/depth-policy are present | Live benchmark gate task (T059b) not evidenced by corresponding test symbol; gate sign-offs still unchecked in tasks doc | Add explicit live benchmark test artifact and close phase gate records |
| OBJ-10 | Batch summary + disagreement sink operational in batch flow | SRC-4/SRC-5 | fully_met | CLI batch path instantiates accumulator/sink, records puzzles, emits summary, writes JSONL disagreements | Single-puzzle path does not emit aggregate (by design) | Keep as-is; add docs clarifying batch-only scope |
| OBJ-11 | Hinting unification contract-first parity | SRC-8/SRC-9/SRC-10 | not_met | Transition plan is draft; no shared contract artifact demonstrated as implemented parity gate | Missing finalized shared contract + parity harness | Treat as future program; do not claim complete in current lab scope |
| OBJ-12 | Most-tempting-wrong-move pedagogy surfaced | SRC-2 | partially_met | Candidate identification is policy-sorted; however no explicit surfaced "most tempting wrong move" field/contract in result | UX-facing field and dedicated tests absent | Add explicit top_trap_move field and deterministic assertion tests |
| OBJ-13 | Policy entropy/rank as observability output | SRC-2 + tactical hints research lineage | partially_met | Entropy/rank computed in DifficultyStage; batch accumulator supports ranks, but CLI record_puzzle call omits rank parameter and no result serialization field for entropy | Missing propagation from ctx into result/accumulator inputs | Wire ctx.correct_move_rank and optional entropy snapshot into result + batch record |

## 5) Explicit NG Reassessment (NG-1..NG-5)

Context update applied: planning no longer constrained by no-browser-AI concern. Reassessment remains enrichment-lab scoped.

| ng_id | prior defer rationale | current evidence | reassessment now | recommendation |
|---|---|---|---|---|
| NG-1 | F-4 urgency was schema evolution risk | Still no urgency field; pipeline stable without it | Still defer for production-final unless new schema version is approved | Keep deferred; schedule as separate schema initiative |
| NG-2 | F-6 needed calibration vs KataGo baselines | No static heuristic implementation; ownership/KataGo path is mature | Defer remains valid | Keep deferred; require controlled calibration experiment before any adoption |
| NG-3 | F-7 seen as NN-feature-plane mismatch | Detection evidence plumbing now stronger; debug matrix is now a low-risk observability add-on | Reclassify from hard defer to optional debug enhancement | Consider a non-invasive debug matrix output (no scoring logic change) |
| NG-4 | New tags in taxonomy considered Level-5 change | No extraordinary evidence requiring taxonomy expansion found in this audit | No change | Keep deferred; do not expand tags in this pass |
| NG-5 | Alpha-beta parallel engine redundant with KataGo | KataGo pipeline + KM optimizations already in place | Still defer | Keep deferred; prioritize calibration/observability over new engine complexity |

## 6) External References (Public)

| id | reference | relevance to decisions |
|---|---|---|
| EXT-1 | Sensei's Library Basic Instinct page (https://senseis.xmp.net/?BasicInstinct) | Supports instinct taxonomy used in SRC-2 mapping and pedagogical framing |
| EXT-2 | Pytest marker guidance (https://docs.pytest.org/en/stable/example/markers.html) | Confirms marker-driven split between unit/integration paths used in lab tests |
| EXT-3 | SGF FF[4] specification (https://www.red-bean.com/sgf/) | Confirms SGF property compatibility expectations for YH/YQ/YR writeback decisions |

Note: Direct external retrieval for the Kishimoto/Muller AAAI paper through the guessed AAAI URL resolved to unrelated content in this session; therefore paper details here are taken from internal source docs (SRC-6/SRC-7) rather than treated as independently fetched proof.

## 7) Candidate Adaptations For Yen-Go (Accretive, Production-Final)

| id | opportunity | expected impact | risk |
|---|---|---|---|
| OPP-1 | Complete observability propagation for correct_move_rank and policy_entropy from stage context into result + batch accumulator callsite | Makes F-9/F-10 style analytics actionable; enables stronger post-run quality dashboards | Low |
| OPP-2 | Expand rotation tests from current subset to charter target (>=12 detector families) using existing multi-orientation harness | Closes a declared acceptance criterion with no runtime behavior risk | Low |
| OPP-3 | Add explicit non-invasive trap/detection debug artifact (top trap move + detector activation matrix export) | Improves explainability and planner confidence without touching core solving logic | Medium |

## 8) Risks, Compliance Notes, Rejection Reasons

| id | risk | impact | mitigation |
|---|---|---|---|
| RISK-1 | Docs show implementation checkboxes complete while governance gates remain unchecked | Overstates production readiness | Track technical completion and governance approval as separate statuses |
| RISK-2 | Key optimization validation appears mock-centric in local objective files | Real engine behavior may diverge | Add/retain integration benchmark evidence in CI or controlled nightly run |
| RISK-3 | Partial observability wiring (computed but not surfaced) can hide model-quality drift | Operational blind spots | Wire rank/entropy outputs and assert in batch summary tests |
| RISK-4 | Instinct and detector evidence text can regress silently without contract tests | Pedagogical inconsistency | Add golden contract tests for 8-instinct mapping and evidence formatting |
| RISK-5 | License contamination risk from external inspirations | Compliance breach | Keep concept-level adaptation only; no verbatim external code import |

Compliance/rejection notes:
- Rejected in this pass: taxonomy expansion (NG-4), alpha-beta parallel search (NG-5), static life/death heuristic without calibration (NG-2).
- Architecture boundary upheld: findings stay within tools/puzzle-enrichment-lab and docs; no backend/frontend structural overreach.

## 9) Planner Recommendations (Decision-Ready)

1. Promote OPP-1 immediately: close entropy/rank observability wiring so existing computation becomes operationally useful.
2. Promote OPP-2 in same cycle: satisfy AC-1 target with additive detector-rotation tests (low risk, high confidence gain).
3. Treat KM and remediation tracks as technically advanced but governance-incomplete: require explicit gate closure record before calling production-final.
4. Keep NG-1/NG-2/NG-4/NG-5 deferred; allow NG-3 only as optional debug observability (not core scoring logic).

## 10) Confidence And Planner Risk Update

- post_research_confidence_score: 88
- post_research_risk_level: medium
- rationale: Core AI-solve and KM wiring are materially present in code/config/tests, but objective-level completeness is reduced by (a) open governance gates in planning docs, (b) uneven mock-free evidence for some claimed benchmark outcomes, and (c) a few partially wired analytics outputs.

## 11) Verification Commands

Use these to validate high-risk claims from this brief:

1. python -m pytest tools/puzzle-enrichment-lab/tests/test_solve_position.py -q --no-header --tb=short
2. python -m pytest tools/puzzle-enrichment-lab/tests/test_difficulty.py tools/puzzle-enrichment-lab/tests/test_ai_solve_config.py -q --no-header --tb=short
3. python -m pytest tools/puzzle-enrichment-lab/tests/test_multi_orientation.py tools/puzzle-enrichment-lab/tests/test_technique_classifier.py -q --no-header --tb=short
4. python -m pytest tools/puzzle-enrichment-lab/tests/test_ai_solve_integration.py tools/puzzle-enrichment-lab/tests/test_remediation_sprints.py -q --no-header --tb=short
5. python -m pytest tools/puzzle-enrichment-lab/tests/test_correct_move.py tools/puzzle-enrichment-lab/tests/test_refutations.py -m integration -q --no-header --tb=short
# Research: PLNech/gogogo Full Repository Exploration — Applicability to Yen-Go Enrichment Lab

**Last Updated**: 2026-03-15 (Expanded: full repo exploration)

---

## 1. Research Question and Boundaries

**Question**: What techniques, patterns, and approaches from the FULL PLNech/gogogo repository can improve the Yen-Go puzzle enrichment lab — specifically technique detection (28 detectors), hint generation (3-tier), teaching comments, move quality classification, and difficulty estimation?

**Boundaries**:
- Scope: Full `training/` directory (45+ Python files) + `src/`, `tests/`, `scripts/`, documentation files
- No code copying — inspiration and concept adaptation only (see Clean-Room License Policy in charter)
- Must align with Yen-Go Holy Laws (zero runtime backend, static-first)
- Must respect existing tag taxonomy (config/tags.json v8.3, 28 canonical tags)
- Must preserve precision-over-recall philosophy
- KataGo is the analysis engine — board-simulation concepts adapted as KataGo signal interpreters, not independent detectors

---

## 1B. Complete File Inventory — PLNech/gogogo Repository

### Repository Overview

- **Tech Stack**: React 18 + TypeScript (60% Python, 27% TypeScript, 7% HTML, 4% CSS, 3% JS)
- **Purpose**: Incremental Go game with progressive AI (AlphaZero-style NN training)
- **License**: Repository front-matter says "MIT" in README, but `LICENSE` says "GPL-3.0"
- **Contributors**: PLNech + Claude (AI-assisted development)
- **Last Activity**: ~3 months ago (Dec 2025)

### Top-Level Directories

| DIR-ID | Directory | Purpose | Relevance to Enrichment Lab |
|--------|-----------|---------|----------------------------|
| D-1 | `training/` | Python NN training, tactical analysis, pattern detection | **HIGH** — core analysis code |
| D-2 | `src/` | React/TypeScript game UI and AI engine | LOW — browser game, not analysis |
| D-3 | `tests/` | Vitest test suite for TS code | LOW — different tech stack |
| D-4 | `scripts/` | CLI utilities (game viewers, visualizations) | LOW |
| D-5 | `blog/` | Jekyll blog posts about development | NONE |
| D-6 | `docs/` | Screenshots and documentation | LOW |
| D-7 | `public/` | Static assets | NONE |

### training/ Directory — Complete File Inventory (45+ files)

#### Core Engine Files

| FI-ID | File | Key Classes/Functions | Size Est. | Relevance | Concepts for Enrichment Lab |
|-------|------|----------------------|-----------|-----------|----------------------------|
| FI-1 | `board.py` | `Board` class: numpy board, groups, liberties, eyes, life/death, ownership_map, to_tensor(), zobrist_hash() | ~600 lines | **HIGH** | Ownership map calculation, eye detection algorithm, group_stats batch computation, true-eye diagonal check |
| FI-2 | `tactics.py` | `TacticalAnalyzer`: trace_ladder(), detect_snapback(), verify_capture(), evaluate_life_death(), is_tactical_position(), get_tactical_boost(), compute_tactical_planes() | ~700 lines | **HIGH** | Ladder diagonal-scan pre-check, snapback atari-first algorithm, alpha-beta capture search, life/death minimax, tactical position classifier |
| FI-3 | `instincts.py` | `InstinctAnalyzer`: 8 pattern detectors, get_instinct_boost(), analyze_position() | ~400 lines | **HIGH** | 8 Basic Instincts with move-level detection and boost stacking |
| FI-4 | `sensei_instincts.py` | `SenseiInstinctDetector`: board-scanning detectors for 8 instincts, priority hierarchy | ~500 lines | **HIGH** | Clean position-scan pattern detection, separate from NN-coupled InstinctAnalyzer |
| FI-5 | `instinct_loss.py` | `InstinctDetector`, `InstinctCurriculum`: adaptive auxiliary loss for instinct learning | ~400 lines | **MEDIUM** | Priority hierarchy concept (survival=3.0 → shape=1.0), instinct-opportunity aggregation, curriculum decay formula: λ(t) = max(λ_min, λ₀ × (1 - accuracy)) |
| FI-6 | `model.py` | `GoNet`: ResNet + global pooling + policy/value/ownership/score heads | ~300 lines | LOW | KataGo-inspired ownership head concept (361× more signal per game), soft policy head (temperature-based discrimination of lower-prob moves) |
| FI-7 | `config.py` | `Config` dataclass: board_size, NN params, MCTS params, KataGo A.4/A.5/A.6 settings | ~60 lines | LOW | Config pattern for shaped Dirichlet noise, root policy softmax temperature |
| FI-8 | `sgf_parser.py` | `parse_sgf_file()`, `load_sgf_dataset()`: parallel SGF loading with ownership/opponent/score targets | ~400 lines | LOW | WED (Weight by Episode Duration) sampling concept, has_tactical_activity() utility |
| FI-9 | `game_record.py` | `MoveStats`, `GameRecord`: per-move statistics (captures, liberties, MCTS insights, policy entropy) | ~350 lines | **MEDIUM** | MoveStats model: policy_entropy, chosen_move_prior, top5_moves — could inform difficulty estimation signals |
| FI-10 | `hybrid_mcts.py` | `HybridMCTS`: neural + symbolic MCTS with tactical policy/value adjustment | ~400 lines | **MEDIUM** | Neural-symbolic blending pattern: _adjust_policy() uses symbolic tactical boosts on NN policy prior, capped at 50% tactical influence |

#### Training Pipeline Files

| FI-ID | File | Key Classes/Functions | Size Est. | Relevance | Concepts |
|-------|------|----------------------|-----------|-----------|----------|
| FI-11 | `tactical_data.py` | `TacticalPosition`, position generators (capture, escape, ladder, net, snapback, connect) | ~500 lines | **MEDIUM** | Programmatic generation of tactical positions with ground-truth labels — could inform test fixture generation |
| FI-12 | `evaluate.py` | `TestPosition`, `evaluate_position()`, `run_evaluation()`: Top-1/3/5/10 accuracy metrics | ~400 lines | **HIGH** | Rank-based evaluation framework: top-k accuracy by category (capture, defense, life_death, joseki), phase-split analysis (opening/middle/endgame) |
| FI-13 | `compare_moves.py` | `analyze_game()`: compare network predictions vs pro moves | ~250 lines | **HIGH** | Rank-based move quality comparison: top-1/3/5/10 accuracy, phase statistics, disagreement tracking |
| FI-14 | `train.py` | Training loop with curriculum | ~200 lines | LOW | N/A |
| FI-15 | `train_supervised.py` | Supervised training with KataGo-style multi-head loss | ~150 lines | LOW | N/A |
| FI-16 | `train_curriculum.py` | Adaptive instinct curriculum integration | ~200 lines | LOW | Curriculum decay pattern: high weight early, decays as model masters fundamentals |
| FI-17 | `train_instincts.py` | Instinct-specific training loop | ~150 lines | LOW | N/A |
| FI-18 | `self_play.py` / `selfplay.py` | Self-play game generation | ~200 lines each | LOW | N/A |
| FI-19 | `curriculum_train.py` | Curriculum-based training | ~150 lines | LOW | N/A |
| FI-20 | `atari_go.py` | Atari Go simplified variant | ~100 lines | LOW | N/A |
| FI-21 | `atari_instinct_learner.py` | Instinct weight learning from Atari Go games | ~200 lines | **MEDIUM** | Empirical instinct weight learning: 2000-game evaluation results with % advantage per instinct |

#### Evaluation & Comparison Files

| FI-ID | File | Key Classes/Functions | Size Est. | Relevance | Concepts |
|-------|------|----------------------|-----------|-----------|----------|
| FI-22 | `compare_mcts.py` | MCTS variant comparison | ~200 lines | LOW | A/B testing patterns for analysis approaches |
| FI-23 | `compare_variants.py` | Model variant comparison | ~200 lines | LOW | N/A |
| FI-24 | `validate_game.py` | Game validation utilities | ~100 lines | LOW | N/A |
| FI-25 | `validate_benchmarks.py` | Benchmark validation | ~100 lines | LOW | N/A |
| FI-26 | `validate_selfplay_tactical.py` | Tactical self-play validation | ~100 lines | LOW | N/A |
| FI-27 | `benchmark.py` | Performance benchmarking suite | ~200 lines | LOW | N/A |
| FI-28 | `instinct_benchmark.py` | Instinct-specific benchmark with ASCII diagrams | ~200 lines | **MEDIUM** | Per-instinct performance measurement pattern |
| FI-29 | `export_model.py` | ONNX export pipeline | ~100 lines | NONE | N/A |

#### Visualization & Utilities

| FI-ID | File | Key Classes/Functions | Size Est. | Relevance | Concepts |
|-------|------|----------------------|-----------|-----------|----------|
| FI-30 | `visualize.py` | Board/policy visualization | ~150 lines | LOW | N/A |
| FI-31 | `viz_policy.py` | Policy heatmap visualization | ~100 lines | LOW | ASCII policy visualization could inform debug output |
| FI-32 | `viz_tactical.py` | Tactical feature visualization | ~100 lines | LOW | N/A |
| FI-33 | `watch_game.py` | Game replay watcher | ~100 lines | NONE | N/A |
| FI-34 | `watch_training.py` | Training progress watcher | ~100 lines | NONE | N/A |
| FI-35 | `create_summary.py` | Training log summarizer | ~100 lines | NONE | N/A |
| FI-36 | `introspect.py` | Network introspection utilities | ~100 lines | LOW | N/A |
| FI-37 | `probe_network.py` | Network probing utilities | ~100 lines | LOW | N/A |
| FI-38 | `generate_showcase_game.py` | Showcase game with SGF export | ~100 lines | NONE | N/A |
| FI-39 | `generate_before_after.py` | Before/after boards for blog | ~100 lines | NONE | N/A |
| FI-40 | `serve.py` | Model serving | ~100 lines | NONE | N/A |
| FI-41 | `download_ogs.py` | OGS game downloader | ~100 lines | NONE | N/A |
| FI-42 | `training_state.py` | Training state persistence | ~100 lines | NONE | N/A |

#### Test Files

| FI-ID | File | Key Pattern | Relevance |
|-------|------|-------------|-----------|
| FI-43 | `test_instincts.py` | Positive + negative tests, multi-orientation, boost stacking, neutral baseline | **HIGH** |
| FI-44 | `test_tactics.py` | TacticalAnalyzer tests (ladder, snapback, capture) | **MEDIUM** |
| FI-45 | `test_tactical_positions.py` | Tactical position generation validation | **MEDIUM** |
| FI-46 | `test_selfplay_tactical.py` | Self-play with tactical validation | LOW |
| FI-47 | `tests/` subdirectory | Additional test modules | LOW |

#### Documentation Files

| FI-ID | File | Content | Relevance |
|-------|------|---------|-----------|
| FI-48 | `README.md` | Quick start for training | NONE |
| FI-49 | `ARCH.md` / `ARCH.mermaid` | Architecture diagrams (Mermaid) | LOW |
| FI-50 | `DATA_FLOW.mermaid` / `DATA_FLOW.png` | Data flow diagrams | LOW |
| FI-51 | `NEUROSYMBOLIC.md` | Hybrid neural+symbolic MCTS documentation | **MEDIUM** |
| FI-52 | `TRAIN.md` | Training configuration guide | LOW |
| FI-53 | `LOG.md` / `SNAP.md` | Training logs and snapshots | LOW |
| FI-54 | `learned_instinct_weights.json` | Empirical weights from 2000 Atari Go games | **HIGH** — validated priority ranking |
| FI-55 | `learned_instinct_weights_v2.json` | Updated weights after pattern detection fixes | **HIGH** |

#### Top-Level Documentation

| FI-ID | File | Content | Relevance |
|-------|------|---------|-----------|
| FI-56 | `INSTINCTS.md` | Full 8 instincts with ASCII diagrams, Atari Go results (advantage %, times fired), pattern detection notes | **HIGH** |
| FI-57 | `SENSEI.md` | Sensei's Library integration guide: 14-lesson curriculum, 34 strategic concepts, 600+ problems, 3-school taxonomy | **MEDIUM** |
| FI-58 | `IMPROVEMENTS.md` | MCTS improvements documentation | LOW |
| FI-59 | `PLAN.md` | Project roadmap with instinct curriculum learnings | LOW |
| FI-60 | `CLAUDE.md` | Claude-specific development context | LOW |

### Files NOT Found (Searched but absent)

- `training/features.py` / `training/feature_planes.py` — tactical features embedded in `board.py::to_tensor()`
- `training/patterns.py` — pattern matching embedded in `tactics.py` and `instincts.py`
- `training/scoring.py` — scoring embedded in `board.py::score()` and `board.py::ownership_map()`
- `training/game_analysis.py` — game analysis in `evaluate.py` and `compare_moves.py`
- `go/board.py` — no separate `go/` directory; board is in `training/board.py`

---

## 2. Internal Code Evidence

### R-I1: Current Enrichment Lab Detectors

| R-ID | File/Module | Relevance |
|------|-------------|-----------|
| R-I1 | `tools/puzzle-enrichment-lab/analyzers/detectors/` (28 detector classes) | Each tag has a dedicated detector; detection uses KataGo analysis + board simulation |
| R-I2 | `backend/puzzle_manager/core/tagger.py` | Backend pipeline tagger — precision-first, comment-keyword dependent for many techniques |
| R-I3 | `config/tags.json` (v8.3) | 28 canonical tags with aliases; maps to tag IDs 10-82 |
| R-I4 | `config/katago-enrichment.json` | Config-driven thresholds for all enrichment lab detectors |
| R-I5 | `tools/puzzle-enrichment-lab/analyzers/detectors/ladder_detector.py` | Board-simulation ladder chase + 3×3 pattern matching + PV diagonal ratio |
| R-I6 | `tools/puzzle-enrichment-lab/analyzers/detectors/snapback_detector.py` | Policy/winrate delta signature + PV recapture pattern |
| R-I7 | `tools/puzzle-enrichment-lab/analyzers/detectors/double_atari_detector.py` | Simultaneous atari detection on 2+ groups |
| R-I8 | `tools/puzzle-enrichment-lab/analyzers/detectors/connection_detector.py` | Topology check: groups connected after move |
| R-I9 | `tools/puzzle-enrichment-lab/analyzers/detectors/cutting_detector.py` | Topology check: groups separated after move |

### R-I10: Current Test Coverage

| R-ID | Test File | Focus | Count |
|------|-----------|-------|-------|
| R-I10a | `test_detectors_high_frequency.py` | Ladder, Snapback, Ko, Life-and-death | 4 classes |
| R-I10b | `test_detectors_common.py` | Capture-race, Connection, Cutting, Throw-in, Net | 5 classes |
| R-I10c | `test_detectors_intermediate.py` | Seki, Nakade, Double-atari, Sacrifice, Escape | 5 classes |
| R-I10d | `test_detectors_lower_frequency.py` | 14 lower-frequency technique detectors | 14 protocol tests |

### R-I11: Known Gaps in Yen-Go Detection

| R-ID | Gap | Description |
|------|-----|-------------|
| R-I11a | Comment-only detection | Techniques like net, throw-in, sacrifice, nakade require author comments in backend tagger |
| R-I11b | No "instinct" classification | No concept of directional response patterns (hane vs tsuke, connect vs peep) |
| R-I11c | False-eye vs true-eye | Not distinguished in current detectors |
| R-I11d | Ladder variations | No ladder-breaker or anti-ladder detection |
| R-I11e | Move-response taxonomy | No classification of WHY a move is correct (survival, shape, cutting prevention) |
| R-I11f | Priority/urgency scoring | Detectors return confidence but not tactical urgency priority |

---

## 3. External References

### R-E1: PLNech/gogogo — `sensei_instincts.py`

**Source**: [Sensei's 8 Basic Instincts](https://senseis.xmp.net/?BasicInstinct)

| R-ID | Pattern | Japanese | Detection Method | Priority |
|------|---------|----------|------------------|----------|
| R-E1a | Extend from Atari | アタリから伸びよ | Group liberty=1 → extend | 3.0 (survival) |
| R-E1b | Hane vs Tsuke | ツケにはハネ | Unsupported adjacent attachment → diagonal wrap | 1.5 |
| R-E1c | Hane at Head of Two | 二子の頭にハネ | 2v2 parallel confrontation → play at head | 1.5 |
| R-E1d | Stretch from Kosumi | コスミから伸びよ | Diagonal attachment → extend away | 1.2 |
| R-E1e | Block the Angle | カケにはオサエ | Knight's move approach → diagonal block | 1.2 |
| R-E1f | Connect vs Peep | ノゾキにはツギ | Peep at cutting point → connect | 2.5 |
| R-E1g | Block the Thrust | ツキアタリには | Perpendicular thrust into wall → extend wall | 2.0 |
| R-E1h | Stretch from Bump | ブツカリから伸びよ | Supported attachment → stretch away | 1.0 |

**Key Design Patterns**:
- `InstinctResult` dataclass with `instinct` name, `moves` list, `priority` float
- Each detector returns `Optional[InstinctResult]` — None if not detected
- `detect_all()` runs all 8 and sorts by priority (survival highest)
- Board scanning: iterate all positions → check neighborhood → pattern match → validate response

### R-E2: PLNech/gogogo — `tactics.py`

| R-ID | Feature | Description | Implementation |
|------|---------|-------------|----------------|
| R-E2a | Ladder tracing | Diagonal scan + recursive fallback + zobrist caching | `trace_ladder()` with `_diagonal_ladder_check()` |
| R-E2b | Snapback detection | Throw-in + immediate recapture pattern | `detect_snapback()` returns stone count |
| R-E2c | Capture verification | Alpha-beta search for capture sequences | `verify_capture()` with depth parameter |
| R-E2d | Life/death analysis | Minimax search with eye counting + liberty heuristic | `evaluate_life_death()` returns -1.0 to +1.0 |
| R-E2e | Tactical feature planes | 6-plane tensor for NN: ladder-threat, ladder-breaker, snapback, capture-in-1, capture-in-2, dead-groups | `compute_tactical_planes()` |
| R-E2f | Move priority boosting | Multiplicative boost: capture(1.5×), snapback(2.5×), connect(1.7×), cut(1.7×), ladder(2.9×) | `get_tactical_boost()` |
| R-E2g | Instinct integration | Lazy-loads `InstinctAnalyzer` for 8 basic instinct boosts | `_get_instinct_boost()` |

### R-E3: PLNech/gogogo — `test_instincts.py`

| R-ID | Testing Pattern | Description |
|------|-----------------|-------------|
| R-E3a | Fixture-based board setup | `Board(9)` with manual stone placement via `board.board[r,c] = 1/-1` |
| R-E3b | Positive + negative tests | Each instinct tested for detection AND non-detection |
| R-E3c | Multi-orientation coverage | Horizontal + vertical variants for same pattern |
| R-E3d | Boost stacking test | Move satisfying multiple instincts gets combined boost > 2.0 |
| R-E3e | Neutral baseline test | Empty board move returns boost = 1.0 (no instinct) |
| R-E3f | Integration test | TacticalAnalyzer actually uses instinct boosts |
| R-E3g | Multi-move any() pattern | `any(analyzer.detect_X(board, m) for m in candidates)` for flexible validation |

### R-E4: PLNech/gogogo — `board.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E4a | `ownership_map()` | BFS territory ownership: +1 black, -1 white, 0 neutral. Used as NN auxiliary target (KataGo §4.1) | **HIGH** — concept mirrors our KataGo ownership analysis in detectors |
| R-E4b | `has_eye()` | True eye check: all 4 adjacent same color (or edge), ≥3/4 diagonals controlled | **MEDIUM** — independent eye verification algorithm |
| R-E4c | `count_eyes()` | Counts true eyes in a group by scanning adjacent empty points | LOW — KataGo ownership already handles this |
| R-E4d | `is_group_alive()` | Heuristic: 2+ eyes → alive, 6+ stones + 4+ libs → likely alive, 1 eye + ≤2 libs → dead | **MEDIUM** — simple heuristic could be a fast pre-filter |
| R-E4e | `group_stats` property | Single-pass computation of all groups, atari positions, liberty distribution | **MEDIUM** — efficient batch computation pattern |
| R-E4f | `to_tensor()` tactical planes | 10 extra planes: liberty counts (1/2/3+) per color, capture moves, self-atari, eye-like, edge distance | **LOW** — NN feature planes, not applicable to KataGo pipeline |
| R-E4g | `zobrist_hash()` | Position hashing for MCTS cache with stone positions + current player | LOW — our enrichment lab doesn't need position caching |
| R-E4h | `from_tensor()` | Inverse conversion: tensor → Board for instinct detection on NN output | LOW — tooling pattern |

### R-E5: PLNech/gogogo — `instinct_loss.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E5a | `InstinctDetector.detect_all()` | Combined tactical + instinct detection: capture, escape, atari, connect, plus 8 Sensei instincts | **HIGH** — aggregation pattern across detector types |
| R-E5b | Priority hierarchy | Empirically validated from 2000 Atari Go games: hane_vs_tsuke (+13.2%) > extend_from_atari (+9.7%) > block_thrust (+9.6%) > block_angle (+3.5%) > connect_vs_peep (+3.4%) > stretch_bump (+3.2%) > stretch_kosumi (+3.0%) > hane_at_head_of_two (+1.9%) | **HIGH** — validated priority ranking for hint ordering |
| R-E5c | `InstinctCurriculum` | Adaptive loss: λ(t) = max(λ_min, λ₀ × (1 - accuracy)). High weight early, decays as model masters | LOW — NN training concept, not applicable |
| R-E5d | Soft target distribution | Temperature-scaled softmax over instinct moves for auxiliary loss | LOW — NN training concept |

### R-E6: PLNech/gogogo — `game_record.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E6a | `MoveStats` dataclass | Per-move statistics: stone counts, group counts, captures, ko, atari counts, MCTS value/visits, policy entropy, top5 moves, min/avg liberties | **MEDIUM** — `policy_entropy` and `top5_moves` concepts could inform difficulty estimation |
| R-E6b | `GameRecord.to_sgf()` | Rich SGF export with per-move comments (value, captures, ko) | LOW — our SGF export handled by SgfBuilder |
| R-E6c | `compute_move_stats()` | Batch computation of all move statistics in one function | LOW — different context (self-play vs puzzle analysis) |

### R-E7: PLNech/gogogo — `hybrid_mcts.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E7a | `_adjust_policy()` | Multiply NN policy by symbolic tactical boost, re-normalize | **MEDIUM** — conceptual parallel to how enrichment lab could weight detector signals |
| R-E7b | `_adjust_value()` | Blend neural value with symbolic life/death assessment: `(1-blend) × nn_value + blend × tactical_value`, capped at 50% | **MEDIUM** — blending formula concept for confidence scoring |
| R-E7c | `NNCache` with zobrist keys | Cache NN evaluations by position hash | LOW — KataGo handles its own caching |
| R-E7d | Tactical position gating | Only apply symbolic adjustments when `is_tactical_position()` returns True | **MEDIUM** — selective application concept |

### R-E8: PLNech/gogogo — `evaluate.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E8a | `TestPosition` dataclass | Named positions with expected answers, by category (capture, defense, life_death, joseki) | **HIGH** — structured test position format |
| R-E8b | Rank-based accuracy | Top-1/3/5/10 accuracy metrics per category and overall | **HIGH** — move quality hierarchy concept |
| R-E8c | Position categorization | capture, defense, life_death, joseki categories with separate metrics | **MEDIUM** — maps to our tag categories |
| R-E8d | `visualize_policy()` | ASCII board with policy strength markers (#/+/./-) | LOW — debug utility |

### R-E9: PLNech/gogogo — `compare_moves.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E9a | Pro vs model comparison | Parse SGF, replay on board, get model policy at each move, find rank of actual move | **MEDIUM** — methodology for validating move quality classifications |
| R-E9b | Phase-split analysis | Opening (1-50), middle (51-150), endgame (151+) accuracy split | **MEDIUM** — game-phase difficulty correlation |
| R-E9c | Disagreement tracking | Log moves where model strongly disagrees with pro (rank >10, prob <1%) | **HIGH** — "interesting case" identification pattern applicable to puzzle difficulty |

### R-E10: PLNech/gogogo — `tactical_data.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E10a | Programmatic position generators | Functions that create capture, escape, ladder, net, snapback, connect positions with ground truth | **MEDIUM** — test fixture generation for detectors |
| R-E10b | Category-weighted sampling | Generators weighted by importance: captures 5×, ladders 4×, advanced 3× | LOW — NN training concern |
| R-E10c | Edge/corner/center variants | Separate generators for center, edge, corner capture positions | **MEDIUM** — multi-context test coverage |

### R-E11: PLNech/gogogo — `INSTINCTS.md` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E11a | ASCII diagrams for each instinct | Clear pattern diagrams showing trigger position and correct response | **HIGH** — documentation pattern for hint explanations |
| R-E11b | Empirical advantage data | Per-instinct: advantage %, times fired, verdict | **HIGH** — validated priority data (see R-E5b) |
| R-E11c | Pattern detection notes | Algorithmic hints for each instinct (liberty counting, adjacency checks, 2v2 confrontation) | **MEDIUM** — implementation guidance |

### R-E12: PLNech/gogogo — `model.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E12a | Ownership head | Per-point ownership prediction: +1 current player, -1 opponent | **LOW** — KataGo already provides ownership |
| R-E12b | Score distribution head | P(final_score = k) for k ∈ [-50, +50], 101 bins | LOW — KataGo already provides score |
| R-E12c | Opponent policy head | Predicts opponent's next move (KataGo: 1.30× speedup) | **MEDIUM** — opponent response prediction could inform refutation generation |
| R-E12d | Soft policy head (A.6) | Temperature-softened policy forces discrimination of lower-prob moves | **MEDIUM** — "most tempting wrong move" concept maps to our wrong-move ranking |
| R-E12e | GlobalPoolingBlock | KataGo-style: mean + max pooling → FC → broadcast. Captures non-local patterns (ko, ladders) | LOW — NN architecture detail |

### R-E13: PLNech/gogogo — `config.py` (NEW)

| R-ID | Feature | Description | Relevance |
|------|---------|-------------|-----------|
| R-E13a | Shaped Dirichlet noise (A.4) | Concentrates exploration noise on higher-logit moves | LOW — MCTS hyperparameter |
| R-E13b | Root policy temperature (A.5) | Temperature=1.1 counteracts MCTS sharpening, higher=1.25 in opening | LOW — MCTS hyperparameter |
| R-E13c | Soft policy temperature=4.0, weight=8.0 (A.6) | Forces discrimination of lower-probability moves | **MEDIUM** — weight=8× for "trap move" emphasis maps to our refutation importance |

---

## 4. Candidate Adaptations for Yen-Go

### Finding F-1: Move-Response Taxonomy (Instinct Classification Layer)

**What**: Add an optional "instinct" classification that explains WHY a puzzle's correct move is the right response — beyond WHAT technique is used.

| R-ID | Adaptation | Yen-Go Mapping | Effort |
|------|-----------|----------------|--------|
| F-1a | Map instincts to existing tags | `extend_from_atari` → enriches `life-and-death` evidence; `connect_vs_peep` → enriches `connection` confidence | Low |
| F-1b | Add instinct as hint context | "This move extends from atari" → YH hint generation inspiration | Low |
| F-1c | Priority hierarchy for detector ordering | Survival > Connectivity > Shape ordering in detector evaluation | Medium |

**Constraint**: Does NOT require new tags in `config/tags.json`. Maps to existing 28-tag taxonomy.

#### Instinct-to-Tag Mapping Table (RC-1)

| IM-ID | Instinct | Primary Tag (slug) | Secondary Tag | Ambiguity Resolution | Hint Template |
|-------|----------|--------------------|--------------|-----------------------|---------------|
| IM-1 | Extend from Atari | `life-and-death` | — | Atari escape is fundamentally life-and-death | "Your group is in atari — extend to gain liberties" |
| IM-2 | Hane vs Tsuke | `shape` | `tesuji` | Tsuke response is a shape-building move; `tesuji` only if the hane creates a tactical threat | "Opponent's unsupported attachment — wrap around with hane" |
| IM-3 | Hane at Head of Two | `tesuji` | — | Offensive move at head of two is a standard tesuji | "Play at the head of opponent's two-stone formation" |
| IM-4 | Stretch from Kosumi | `shape` | — | Diagonal attachment response is shape refinement | "Opponent attached diagonally — stretch away to maintain good shape" |
| IM-5 | Block the Angle | `connection` | — | Blocking knight's move approach prevents disconnection | "Opponent's knight's move approach — block diagonally to maintain connection" |
| IM-6 | Connect vs Peep | `connection` | `cutting` (if peep threatens specific cut) | Primary action is connecting; cutting is the threat being prevented | "Peep threatens to cut your groups — connect immediately" |
| IM-7 | Block the Thrust | `connection` | — | Thrust-block prevents opponent from splitting your wall | "Opponent thrusts into your formation — extend the wall to block" |
| IM-8 | Stretch from Bump | `shape` | — | Supported attachment response is shape-oriented stretching | "Opponent's supported attachment — stretch away rather than hane" |

**Pedagogical level targeting** (per GV-4 Ke Jie feedback): Instinct hints are most valuable for YG levels `elementary` through `upper-intermediate` (15k–5k). Expert-level puzzles rarely need instinct hints — the response is obvious to dan-level players.

### Finding F-2: Ladder Detection Enhancement

**What**: gogogo's diagonal-scan algorithm + zobrist caching could improve our `LadderDetector`.

| R-ID | Adaptation | Current State | Improvement |
|------|-----------|---------------|-------------|
| F-2a | Diagonal scan fast-path | Our detector uses board chase simulation | Add diagonal pre-check before full simulation = faster |
| F-2b | Zobrist hash caching | No caching in current LadderDetector | Cache ladder results for repeated analysis calls |
| F-2c | Ladder-breaker detection | Not explicitly detected | Add ladder-breaker as sub-detection returned alongside `ladder` tag |

**Benchmark gate (RC-3)**: Current LadderDetector already has `_simulate_ladder_chase()` with `max_steps=30` and `_diagonal_chase_ratio()` as PV confirmation. Optimization is speculative — a timing benchmark of current ladder detection on a representative test corpus (≥50 puzzles with `ladder` tag) MUST be completed before any implementation work. If current detection completes in <100ms per puzzle (likely, given offline-only context), the optimization adds code complexity without user-visible benefit.

### Finding F-3: Snapback Detection Validation

**What**: gogogo's snapback detection confirms our policy/winrate-delta approach is sound, but adds a complementary board-simulation path.

| R-ID | Adaptation | Description |
|------|-----------|-------------|
| F-3a | Board-simulation snapback | Complement KataGo-signal detection with board-level throw-in → capture → recapture verification |
| F-3b | Stone count return | Return number of captured stones in snapback for complexity scoring (YX enrichment) |

### Finding F-4: Priority/Urgency Scoring

**What**: gogogo uses a numeric priority hierarchy (3.0 survival → 1.0 shape). Yen-Go detectors return confidence but lack urgency ordering.

| R-ID | Adaptation | Description |
|------|-----------|-------------|
| F-4a | Add priority dimension to DetectionResult | Alongside `confidence`, add `urgency` field (survival=high, shape=low) |
| F-4b | Use priority for hint ordering | Higher-urgency detections get earlier hints in YH |

### Finding F-5: Test Case Improvements

**What**: gogogo's test patterns reveal several testing strategies our enrichment lab tests could adopt.

| R-ID | Adaptation | Description | Files Impacted |
|------|-----------|-------------|----------------|
| F-5a | Negative testing for all detectors | Currently some detectors only have positive tests; add "should NOT detect" tests | `test_detectors_*.py` |
| F-5b | Multi-orientation tests | Test same pattern in both horizontal/vertical/diagonal variants | `test_detectors_*.py` |
| F-5c | Boost stacking integration test | Verify that multiple detectors firing on same position produce combined evidence | New integration test |
| F-5d | Neutral baseline test | Empty/trivial position should return zero detections | New test |
| F-5e | Board fixture library | Create reusable position fixtures for common tactical situations | New fixture module |

#### Test Gap Quantification (RC-2)

| TG-ID | Detector | Test File | Positive | Negative | Multi-Orient | Quality |
|-------|----------|-----------|----------|----------|--------------|---------|
| TG-1 | capture_race_detector | test_detectors_common.py | ✅ | ✅ | ❌ | Full |
| TG-2 | clamp_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-3 | connection_detector | test_detectors_common.py | ✅ | ✅ | ❌ | Full |
| TG-4 | connect_and_die_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-5 | corner_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ✅ (TL vs center) | Full |
| TG-6 | cutting_detector | test_detectors_common.py | ⚠️ Incomplete | ✅ | ❌ | Protocol |
| TG-7 | dead_shapes_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-8 | double_atari_detector | test_detectors_intermediate.py | ✅ | ✅ | ❌ | Full |
| TG-9 | endgame_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-10 | escape_detector | test_detectors_intermediate.py | ✅ | ✅ | ❌ | Full |
| TG-11 | eye_shape_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-12 | fuseki_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ✅ (4 corners) | Full |
| TG-13 | joseki_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-14 | ko_detector | test_detectors_high_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-15 | ladder_detector | test_detectors_high_frequency.py | ✅ | ✅ | ✅ (diagonal+edge) | Full |
| TG-16 | liberty_shortage_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-17 | life_and_death_detector | test_detectors_high_frequency.py | ✅ | ❌ | ✅ (ownership) | Partial |
| TG-18 | living_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-19 | nakade_detector | test_detectors_intermediate.py | ✅ | ✅ | ❌ | Full |
| TG-20 | net_detector | test_detectors_common.py | ✅ | ✅ | ❌ | Full |
| TG-21 | sacrifice_detector | test_detectors_intermediate.py | ✅ | ✅ | ❌ | Full |
| TG-22 | seki_detector | test_detectors_intermediate.py | ✅ | ✅ | ✅ (ownership) | Full |
| TG-23 | shape_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-24 | snapback_detector | test_detectors_high_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-25 | tesuji_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-26 | throw_in_detector | test_detectors_common.py | ✅ | ✅ | ❌ | Full |
| TG-27 | under_the_stones_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |
| TG-28 | vital_point_detector | test_detectors_lower_frequency.py | ✅ | ✅ | ❌ | Full |

**Summary**: 27/28 detectors have both positive and negative tests. 1 detector (`cutting_detector`) has incomplete positive test. Only 5/28 have multi-orientation tests (`corner`, `fuseki`, `ladder`, `life_and_death`, `seki`). 23/28 detectors need multi-orientation test additions to reach AC-1 target of ≥12.

### Finding F-6: Life/Death Static Evaluation Heuristic

**What**: gogogo's `_static_life_eval()` formula: `eyes × 0.4 + liberties × 0.1 + size × 0.02` could inform our LifeAndDeathDetector's confidence scoring.

| R-ID | Adaptation | Description |
|------|-----------|-------------|
| F-6a | Weighted confidence formula | Use eye_count, liberty_count, group_size as factors in confidence scoring |
| F-6b | Ownership swing correlation | Validate gogogo's static eval against KataGo ownership deltas for calibration |

### Finding F-7: Tactical Feature Planes Concept

**What**: gogogo generates 6 binary feature planes (ladder-threat, snapback, capture-in-1, etc.) for NN input. the plane concept maps to multi-tag detection.

| R-ID | Adaptation | Description |
|------|-----------|-------------|
| F-7a | Multi-tag evidence layering | Each detected technique contributes a "layer" of evidence — composite scoring across layers |
| F-7b | Binary detection matrix | Create a debug output showing which detectors fire on each position (similar to feature planes) |

### Finding F-8: Rank-Based Move Quality Hierarchy (NEW — from evaluate.py, compare_moves.py)

**What**: gogogo evaluates move quality using top-k accuracy (top-1, top-3, top-5, top-10) per category, not just binary correct/wrong. Our enrichment lab uses delta-based classification (TE/BM/BM_HO/NEUTRAL) which is a binary threshold approach.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-8a | Rank-aware wrong-move classification | Instead of just "wrong move" (BM), classify wrong moves as "nearly correct" (rank 2-3), "reasonable alternative" (rank 4-10), or "blunder" (rank 10+) | Medium |
| F-8b | Wrong-move teaching granularity | `teaching_comments.py` wrong-move templates could vary by rank: a rank-2 wrong move gets "Close, but..." while rank-10+ gets "This fundamentally misreads the position" | Medium |
| F-8c | Phase-split difficulty correlation | Compare opening/middle/endgame difficulty distributions; puzzles where correct move has lower policy rank are harder | Low |

**Constraint**: Rank information is implicitly available in KataGo `moveInfos` array (moves are sorted by visits). No new KataGo query needed — just index into existing response.

### Finding F-9: Policy Entropy as Difficulty Signal (NEW — from game_record.py)

**What**: gogogo tracks `policy_entropy` per move position. High entropy = many plausible moves = harder to find the correct one. Low entropy = one obvious move.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-9a | Add policy entropy to difficulty estimation | `estimate_difficulty.py` already uses `policy_prior` and `visit_distribution`; adding entropy (Shannon entropy of policy vector) provides a single scalar signal for "how ambiguous is this position" | Low |
| F-9b | Entropy-based complexity metric | Could be a new component of `YX` complexity metrics — a position with 5 plausible moves (high entropy) is structurally more complex than one with a single dominant move | Low |

**KataGo mapping**: Entropy can be computed from `moveInfos[].prior` values in root analysis response. No additional engine query.

### Finding F-10: Disagreement Tracking for Trap Moves (NEW — from compare_moves.py)

**What**: gogogo logs "disagreement" moves where model's top choice differs significantly from the reference answer (rank >10, probability <1%). This concept maps to identifying "tempting but wrong" moves in puzzles.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-10a | Quantify trap-move attractiveness | For BM (wrong) moves, record KataGo's policy prior — higher prior = more tempting trap. Currently `solve_position.py` classifies BM but doesn't rank traps by attractiveness | Low |
| F-10b | "Most tempting wrong move" for hints | YH tier-2 hint could say "Beware of {!xy} — it looks appealing but..." for the highest-prior wrong move | Medium |
| F-10c | Refutation move ordering | YR property lists refutation moves; order by policy prior (most tempting first) instead of alphabetical | Low |

**Connection to R-E12d (soft policy head)**: gogogo's soft policy concept (temperature=4.0, weight=8.0) explicitly trains the model to discriminate between closely-ranked wrong moves. For our purposes, KataGo's raw policy already provides the discrimination we need.

### Finding F-11: Empirically Validated Priority Ranking (NEW — from instinct_loss.py, INSTINCTS.md)

**What**: gogogo validated instinct priorities via 2000 Atari Go games. The empirical win-rate advantage data provides an external reference point for our detector confidence weighting.

| R-ID | Empirical Ranking (gogogo) | Win-Rate Advantage | Enrichment Lab Mapping |
|------|---------------------------|-------------------|------------------------|
| F-11a | hane_vs_tsuke | +13.2% | `shape` / `tesuji` confidence boost |
| F-11b | extend_from_atari | +9.7% | `life-and-death` — validates high priority for survival moves |
| F-11c | block_thrust | +9.6% | `connection` — validates blocking as high-urgency |
| F-11d | block_angle | +3.5% | `connection` — lower-urgency connection |
| F-11e | connect_vs_peep | +3.4% | `connection` / `cutting` — moderate urgency |
| F-11f | stretch_bump | +3.2% | `shape` — low urgency |
| F-11g | stretch_kosumi | +3.0% | `shape` — low urgency |
| F-11h | hane_at_head_of_two | +1.9% | `tesuji` — minimal advantage, context-dependent |

**Adaptation**: Use these as reference weights in `TAG_PRIORITY` ordering within `technique_classifier.py`. Currently TAG_PRIORITY groups techniques by priority tier (1-5); this empirical data could inform intra-tier ordering within priority-1 techniques.

### Finding F-12: Structured Test Position Framework (NEW — from evaluate.py, tactical_data.py)

**What**: gogogo defines `TestPosition` dataclass with named positions, expected answers, and category labels. Their `tactical_data.py` generates positions programmatically with center/edge/corner variants.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-12a | Named test position catalog | Create a YAML/JSON catalog of test positions per detector, with expected tags, expected confidence ranges, and expected non-detections | Medium |
| F-12b | Multi-context position generation | For each detector, provide at least 3 position variants: center, edge, corner — mirrors gogogo's `tactical_data.py` approach | Medium |
| F-12c | Category-level regression reporting | Group test results by tag category (high-frequency, common, intermediate, lower-frequency) with per-category pass rates | Low |

### Finding F-13: Neural-Symbolic Blending Formula (NEW — from hybrid_mcts.py)

**What**: gogogo's `_adjust_value()` blends neural and symbolic signals: `(1-blend) × nn_value + blend × tactical_value`, capped at 50% symbolic influence.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-13a | Detector confidence blending | When multiple detectors agree (e.g., ladder + capture_race both fire), combine confidences with a blending formula rather than max() | Medium |
| F-13b | 50% cap principle | Any single signal should never dominate the final classification — prevents over-reliance on one detector | Low |

**Caveat**: Our current architecture uses KataGo as the authoritative signal source and detectors as interpreters. Blending applies within the detector layer, not between KataGo and detectors.

### Finding F-14: "Most Tempting Wrong Move" / Soft Policy Concept (NEW — from model.py, config.py)

**What**: gogogo trains a "soft policy" head with temperature=4.0 to force the model to discriminate among lower-probability moves. The concept of explicitly identifying the "most tempting mistake" is pedagogically valuable for teaching comments.

| R-ID | Adaptation | Description | Effort |
|------|-----------|-------------|--------|
| F-14a | Identify most-tempting wrong move | For each puzzle, identify the wrong move with highest KataGo policy prior — this is the "trap" students will fall into | Low |
| F-14b | Teaching comment for trap move | `teaching_comments.py` could generate a specific explanation for WHY the trap move fails: "After {!xy}, opponent responds with {!ab}, gaining a critical liberty advantage" | Medium |
| F-14c | Link to YR property | The first move in YR (refutation moves) should be the most-tempting wrong move, enabling frontend to show "This is the most common mistake" | Low |

**KataGo mapping**: Already available in `moveInfos` — the highest-prior move that is NOT in the correct sequence is the trap move.

### Finding F-15: Sensei's 34 Strategic Concepts for Hint Vocabulary (NEW — from SENSEI.md)

**What**: SENSEI.md documents 34 strategic concepts from Sensei's Library organized into 3 schools (Kitani Minoru/territorial, Go Seigen/balance, Modern/combat). These provide a rich vocabulary for teaching hints beyond our current 28 technique tags.

| R-ID | Concept Category (SENSEI.md) | Example Concepts | Enrichment Lab Usage | Effort |
|------|------------------------------|------------------|---------------------|--------|
| F-15a | Kitani school (territorial) | Thickness utilization, influence vs territory, moyo building | Hint vocabulary for fuseki/opening puzzles | Low |
| F-15b | Go Seigen school (balance) | Whole-board thinking, flexible response, aji preservation | Advanced hint vocabulary for upper-intermediate+ | Low |
| F-15c | Modern school (combat) | Fighting shapes, sente/gote exchange, invasion timing | Hint vocabulary for shape/tesuji puzzles | Low |
| F-15d | Curriculum structure | 14 progressive lessons with 3 concepts per lesson | Hint difficulty gating: basic concepts for lower levels, advanced for upper | Medium |

**Constraint**: This is hint vocabulary enrichment only — no new tags, no new detectors. Maps to existing `COORDINATE_TEMPLATES` in `hint_generator.py`.

---

### Cross-Reference Table: gogogo Concepts → Enrichment Lab Equivalents

| XR-ID | gogogo Concept | gogogo File(s) | Enrichment Lab Equivalent | Gap / Opportunity |
|-------|---------------|----------------|--------------------------|-------------------|
| XR-1 | 8 Basic Instincts | sensei_instincts.py, instincts.py | No equivalent — detectors classify WHAT, not WHY | **GAP**: Add instinct-derived hint context (F-1b) |
| XR-2 | Priority hierarchy (3.0→1.0) | instinct_loss.py, sensei_instincts.py | TAG_PRIORITY in technique_classifier.py (tiers 1-5) | **OPPORTUNITY**: Empirical win-rate data (F-11) can validate/refine TAG_PRIORITY ordering |
| XR-3 | Ladder tracing (diagonal scan) | tactics.py | LadderDetector._simulate_ladder_chase() | **SMALL GAP**: Our chase sim is adequate; diagonal pre-check is marginal improvement (F-2) |
| XR-4 | Snapback detection | tactics.py | SnapbackDetector (KataGo signal-based) | **COMPLEMENT**: Board-simulation path as secondary verification (F-3) |
| XR-5 | Life/death evaluation | board.py, tactics.py | LifeAndDeathDetector (KataGo ownership) | **OPPORTUNITY**: Static eval formula for confidence scoring (F-6) |
| XR-6 | Ownership map | board.py | KataGo ownership analysis in detectors | **EQUIVALENT**: Both compute per-point ownership; KataGo's is stronger |
| XR-7 | True eye detection | board.py (has_eye) | EyeShapeDetector | **MINOR GAP**: Independent eye algorithm could be validation cross-check |
| XR-8 | Tactical feature planes | board.py, tactics.py | 28 detector binary outputs | **CONCEPTUAL PARALLEL**: Feature planes ≈ detector activation matrix (F-7) |
| XR-9 | Top-k accuracy metrics | evaluate.py, compare_moves.py | Delta-based TE/BM classification | **GAP**: No rank-awareness in move quality (F-8) |
| XR-10 | Policy entropy | game_record.py | Not currently used | **GAP**: Missing difficulty signal (F-9) |
| XR-11 | Disagreement tracking | compare_moves.py | Not currently tracked | **GAP**: Trap move identification (F-10) |
| XR-12 | Soft policy (trap move emphasis) | model.py, config.py | Wrong-move teaching comments | **OPPORTUNITY**: Explicit most-tempting-wrong-move identification (F-14) |
| XR-13 | Positive + negative test pattern | test_instincts.py | Detector tests (27/28 have both) | **MOSTLY ALIGNED**: Only cutting_detector missing positive |
| XR-14 | Multi-orientation tests | test_instincts.py | Only 5/28 detectors | **GAP**: 23 detectors need multi-orientation coverage (F-5b) |
| XR-15 | Boost stacking / integration test | test_instincts.py | No multi-detector integration test | **GAP**: No combined-evidence testing (F-5c) |
| XR-16 | Board fixture generation | tactical_data.py | Ad-hoc mock_analysis fixtures | **OPPORTUNITY**: Structured position catalog (F-12a) |
| XR-17 | Neural-symbolic blending | hybrid_mcts.py | max() across detector confidences | **OPPORTUNITY**: Blending formula for multi-detector agreement (F-13) |
| XR-18 | Sensei's 34 strategic concepts | SENSEI.md | COORDINATE_TEMPLATES (18 technique templates) | **VOCABULARY GAP**: Richer hint language for fuseki/shape/tesuji (F-15) |
| XR-19 | MoveStats per-move data model | game_record.py | Per-move analysis in solve_position.py | **PARTIAL**: We have delta/classification but not entropy/rank statistics |
| XR-20 | TestPosition dataclass | evaluate.py | No structured test position catalog | **GAP**: Missing catalog-based test approach (F-12a) |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

### License Assessment

| R-ID | Item | Status |
|------|------|--------|
| L-1 | PLNech/gogogo license | README claims "MIT", but `LICENSE` file contains GPL-3.0 text. **Contradictory. Treat as GPL-3.0 (most restrictive interpretation).** |
| L-2 | Sensei's Library patterns | Public Go knowledge, not copyrightable (game rules and traditional patterns) |
| L-3 | Algorithm adaptations | Clean-room adaptation of tactical concepts is safe; direct code copying is NOT |
| L-4 | Empirical data (instinct weights) | Statistical results from game experiments are facts, not copyrightable expressions |
| L-5 | INSTINCTS.md / SENSEI.md content | Documentation content is copyrighted; extract only factual concepts (instinct names, empirical win-rates), not prose |

### Rejection Reasons

| R-ID | Finding | Rejection Reason |
|------|---------|------------------|
| RJ-1 | Instinct detection as new tag category | Would require expanding config/tags.json taxonomy beyond 28 tags — scope creep risk |
| RJ-2 | `Board` class integration | gogogo uses custom `Board` class with numpy arrays; Yen-Go uses sgfmill + KataGo — incompatible interfaces. No value in porting board simulation when KataGo provides stronger analysis |
| RJ-3 | NN feature planes as runtime input | Yen-Go allows AI — feature planes are irrelevant for runtime. However, the concept of a "detector activation matrix" is useful for debugging (see F-7b) |
| RJ-4 | Alpha-beta capture search | Yen-Go uses KataGo for tactical analysis — implementing a parallel search engine adds maintenance burden with no accuracy gain vs KataGo |
| RJ-5 | InstinctCurriculum / adaptive loss | NN training concept with no mapping to offline puzzle analysis |
| RJ-6 | Self-play / training pipeline | Entire training infrastructure (train.py, selfplay.py, curriculum_train.py, etc.) is irrelevant — Yen-Go doesn't train models |
| RJ-7 | MCTS implementation (hybrid_mcts.py) | The *code* is irrelevant; only the *concept* of neural-symbolic blending is useful (F-13) |
| RJ-8 | Zobrist hashing | Our enrichment lab processes puzzles once per pipeline run; no caching benefit |
| RJ-9 | Model architecture (ResNet, global pooling) | NN architecture details have no application in KataGo-based analysis |
| RJ-10 | Ownership map BFS implementation | KataGo provides more accurate ownership data than heuristic BFS |

### Risks

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|-----------|
| RK-1 | Over-engineering detectors | Medium | Keep adaptations as enrichments to existing detectors, not new modules. No new detector classes from this research. |
| RK-2 | Board simulation performance | Low | Ladder diagonal-scan is O(n) — acceptable for enrichment lab (offline only). Only relevant if F-2 is adopted. |
| RK-3 | False positive increase | Medium | Any new detection logic must maintain precision-over-recall philosophy. Measure FP rate before/after on representative corpus. |
| RK-4 | Unlicensed code risk | High | Adapt concepts only, never copy code verbatim. GPL-3.0 contamination would require relicensing. |
| RK-5 | Scope creep from 15 findings | Medium | Not all findings should be implemented. Planner should select ≤5 for immediate work. Others go to backlog. |
| RK-6 | Test suite bloat from F-5/F-12 | Low | Multi-orientation tests add test count but improve coverage. Keep each test focused (1 assertion principle). |

---

## 6. Planner Recommendations

### Tier 1: ADOPT (high confidence, low risk, clear ROI)

1. **ADOPT: Test pattern improvements (F-5)** — Highest ROI, lowest risk. Add multi-orientation tests to ≥12 of 28 detectors (currently only 5 have them), fix cutting_detector's incomplete positive test, add boost-stacking integration test + neutral baseline test. No production code changes needed. License-safe (testing patterns are non-copyrightable methodology). _Addresses: AC-1, XR-14, XR-15._

2. **ADOPT: Instinct-to-hint mapping (F-1b)** — Add instinct-derived hint templates to `COORDINATE_TEMPLATES` in `hint_generator.py`. The 8 Basic Instincts from Sensei's Library map directly to pedagogical YH hints for elementary through upper-intermediate puzzles. Maps to existing hint infrastructure without new tags. _Addresses: AC-2, XR-1._ See IM-1→IM-8 mapping table.

3. **ADOPT: Policy entropy as difficulty signal (F-9)** — Low-effort, high-value addition to `estimate_difficulty.py`. Computed from existing KataGo `moveInfos[].prior` values — no extra engine query. Shannon entropy provides a single scalar for "how ambiguous is this position." _Addresses: XR-10._

4. **ADOPT: Most-tempting wrong move identification (F-14a + F-10a)** — Identify the highest-policy-prior wrong move for each puzzle. Data already exists in KataGo response. Enables richer YR ordering and teaching comment specificity. _Addresses: XR-11, XR-12._

### Tier 2: EVALUATE (promising but needs validation)

5. **EVALUATE: Rank-based move quality (F-8a)** — Classify wrong moves by KataGo policy rank (near-miss vs blunder). Medium effort; requires changes to `solve_position.py` classification logic. Validate on a corpus of ≥20 puzzles with known wrong-move severity before committing. _Addresses: XR-9._

6. **EVALUATE: Empirical priority validation (F-11)** — Compare gogogo's win-rate-based priority ranking with our TAG_PRIORITY ordering. If discrepancies are found, propose reordering. Low effort analysis, medium effort if changes needed. _Addresses: XR-2._

7. **EVALUATE: Structured test position catalog (F-12a)** — Create YAML catalog of named test positions per detector with expected results. Medium effort but significantly improves test maintainability. Gate: prototype for 3 detectors first. _Addresses: XR-16, XR-20._

### Tier 3: DEFER (lower priority or blocked)

8. **DEFER: Snapback board-simulation complement (F-3a)** — Current SnapbackDetector works well with KataGo signals. Board-simulation adds redundancy with marginal accuracy gain. Revisit only if FP/FN data shows signal-based approach has blind spots.

9. **DEFER: Ladder detection optimization (F-2)** — Current LadderDetector already has board-chase simulation + PV confirmation + 3×3 pattern matching. Benchmark gate required before any work. No player-reported ladder mistagging.

10. **DEFER: Sensei's 34 strategic concepts (F-15)** — Vocabulary expansion for advanced hints. Valuable but low priority vs core detection improvements. Add to backlog for future hint quality pass.

11. **DEFER: Neural-symbolic blending formula (F-13)** — Interesting concept but our current max() aggregation in technique_classifier.py works. Revisit only if multi-detector false-positive patterns emerge.

### Not Recommended

- **F-6 (Life/death static eval formula)**: Our LifeAndDeathDetector already uses KataGo ownership, which is more accurate than heuristic `eyes × 0.4 + liberties × 0.1 + size × 0.02`. Would add code with no accuracy gain.
- **F-7 (Tactical feature planes concept)**: The debug output (F-7b) is occasionally useful but not worth a dedicated effort. Can be added organically during detector debugging.

---

## 7. Confidence and Risk Update for Planner

- **Post-research confidence score**: 85/100 (up from 78 — full repo analysis discovered 8 additional findings beyond original 7, with 4 high-value adoptable patterns)
- **Post-research risk level**: low
- **Rationale**: Full exploration of 60+ files confirms that (a) gogogo's core analysis concepts align with our KataGo-based approach but at a simpler level (custom NN vs KataGo), (b) the highest-value takeaways are pedagogical (instinct hints, trap move identification) and methodological (test patterns, policy entropy), not architectural. No Holy Law violations in any recommendation. License risk is manageable with strict clean-room adaptation — the contradictory MIT/GPL-3.0 situation in the repo is addressed by treating all content as GPL-3.0 and extracting only factual concepts.

### Acceptance Criteria Status

| AC-ID | Criterion | Status | Evidence |
|-------|-----------|--------|----------|
| AC-1 | ≥12 detectors gain multi-orientation tests from research | ✅ Ready | F-5 provides methodology; 23 detectors identified as needing coverage (TG table) |
| AC-2 | Instinct-to-tag mapping validated with ≥6 of 8 instincts | ✅ Ready | All 8 mapped (IM-1 through IM-8) with primary tags, secondary tags, and hint templates |
| AC-3 | Ladder detection evaluated with benchmark criteria | ✅ Ready | F-2 documented with benchmark gate; recommendation is DEFER unless <100ms gate fails |
| AC-4 | Research brief with ≥2 internal + ≥2 external references | ✅ Met | 11 internal references (R-I1 through R-I11), 13 external references (R-E1 through R-E13) |
| AC-5 | All recommendations map to repository constraints | ✅ Met | Every recommendation cross-referenced to Holy Laws, tag taxonomy freeze, precision-over-recall |

### Open Questions for Planner

| Q-ID | Question | Options | Recommended | Status |
|------|----------|---------|-------------|--------|
| Q1 | Should F-9 (policy entropy) be added to YX complexity metrics or used internally only for difficulty estimation? | A: Add to YX / B: Internal only / C: Both | B — Internal only (avoids schema change) | ❌ pending |
| Q2 | For F-14 (most-tempting wrong move), should YR ordering be changed from alphabetical to policy-prior ordering? | A: Yes, reorder YR / B: Keep alphabetical, add separate field / C: No change | A — Reorder YR (most natural for frontend "common mistake" display) | ❌ pending |
| Q3 | How many detectors should receive multi-orientation tests in the first implementation pass? | A: All 23 / B: 12 (AC-1 minimum) / C: Top 8 (high + common frequency) | C — Top 8 first, then expand | ❌ pending |
| Q4 | Should the instinct hint templates (IM-1→IM-8) be added to `config/katago-enrichment.json` or hardcoded in `hint_generator.py`? | A: Config / B: Code / C: Other | A — Config-driven (follows existing pattern) | ❌ pending |

---

## Enumerated Findings Summary Table

| F-ID | Finding | Source File(s) | Yen-Go Impact Area | Action | Priority |
|------|---------|---------------|---------------------|--------|----------|
| F-1 | Move-response taxonomy (8 instincts) | sensei_instincts.py | Hint generation, tag confidence | ADOPT hint templates (F-1b) | **High** |
| F-2 | Ladder diagonal-scan fast-path | tactics.py | LadderDetector performance | DEFER (benchmark gate) | Low |
| F-3 | Board-simulation snapback validation | tactics.py | SnapbackDetector accuracy | DEFER | Low |
| F-4 | Priority/urgency scoring | sensei_instincts.py | DetectionResult schema | DEFER to v3 | Low |
| F-5 | Test case methodology improvements | test_instincts.py | test_detectors_*.py robustness | ADOPT immediately | **High** |
| F-6 | Life/death static evaluation heuristic | tactics.py | LifeAndDeathDetector confidence | NOT RECOMMENDED | — |
| F-7 | Multi-tag evidence layering concept | tactics.py | Debug/observability output | NOT RECOMMENDED (organic) | — |
| F-8 | Rank-based move quality hierarchy | evaluate.py, compare_moves.py | solve_position.py classification | EVALUATE | Medium |
| F-9 | Policy entropy as difficulty signal | game_record.py | estimate_difficulty.py | ADOPT | **High** |
| F-10 | Disagreement tracking / trap moves | compare_moves.py | Wrong-move ranking, YR ordering | ADOPT (with F-14) | **High** |
| F-11 | Empirically validated priority ranking | instinct_loss.py, INSTINCTS.md | TAG_PRIORITY validation | EVALUATE | Medium |
| F-12 | Structured test position framework | evaluate.py, tactical_data.py | Test infrastructure | EVALUATE | Medium |
| F-13 | Neural-symbolic blending formula | hybrid_mcts.py | Multi-detector confidence | DEFER | Low |
| F-14 | Most-tempting wrong move (soft policy) | model.py, config.py | Teaching comments, YR | ADOPT | **High** |
| F-15 | Sensei's 34 strategic concepts | SENSEI.md | Hint vocabulary expansion | DEFER | Low |
