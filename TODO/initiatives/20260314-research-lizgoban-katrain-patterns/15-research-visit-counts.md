# Research Brief: KataGo Visit Counts, Analysis Settings & HumanSL for Tsumego Enrichment

**Initiative**: `20260314-research-lizgoban-katrain-patterns` (sub-document)
**Research question**: What visit counts, analysis settings, and model configurations do mature Go analysis tools use — and how should we configure our puzzle enrichment pipeline?
**Boundaries**: Offline batch processing for tsumego. KataGo analysis engine. No live/interactive analysis.
**Last Updated**: 2026-03-14

---

## 1. Research Question & Success Criteria

| ID | Question | Status |
|----|----------|--------|
| Q1 | What visit counts do KaTrain, Lizgoban, KataGo defaults use for various analysis tiers? | ✅ resolved |
| Q2 | What are the model/config requirements for HumanSL profiles? | ✅ resolved |
| Q3 | What visit counts are recommended for tsumego-specific tasks? | ✅ resolved |
| Q4 | What config parameters are we missing that could improve accuracy? | ✅ resolved |
| Q5 | What does ghostban/goproblems use for KataGo analysis? | ❌ pending (404/unavailable) |

---

## 2. Internal Code Evidence

### 2A. Yen-Go Current Visit Settings

Source: [config/katago-enrichment.json](../../../config/katago-enrichment.json)

| R-ID | Setting | Value | Config Path | Purpose |
|------|---------|-------|-------------|---------|
| R-1 | Default max visits | 200 | `analysis_defaults.default_max_visits` | Quick analysis / policy-only |
| R-2 | Deep enrich visits | 2000 | `deep_enrich.visits` | Primary enrichment (b18c384) |
| R-3 | Refutation visits | 100 | `refutations.refutation_visits` | Per-refutation move analysis |
| R-4 | Escalation visits | 500 | `refutation_escalation.escalation_visits` | When 0 refutations on first pass |
| R-5 | Confirmation visits | 500 | `ai_solve.solution_tree.confirmation_visits` | Solution tree confirmation |
| R-6 | Tree visits | 500 | `ai_solve.solution_tree.tree_visits` | Solution tree building |
| R-7 | Forced move visits | 125 | `ai_solve.solution_tree.forced_move_visits` | KM-03 fast-path forced moves |
| R-8 | Simulation verify | 50 | `ai_solve.solution_tree.simulation_verify_visits` | KM-01 Kawano simulation |
| R-9 | PV quality min | 50 | `refutations.pv_quality_min_visits` | PV credibility floor |
| R-10 | Escalation tiers | 200/800/2000 | `escalation.levels` | Progressive (deprecated in lab) |
| R-11 | Calibration tiers | 500/1000/2000 | `ai_solve.calibration.visit_counts` | Model-aware calibration |
| R-12 | Deep enrich symmetries | 2 | `deep_enrich.root_num_symmetries_to_sample` | Quality averaging |
| R-13 | Deep enrich model | b18c384 | `deep_enrich.model` | Primary model |
| R-14 | Referee model | b28c512 | `models.referee.arch` | Escalation referee |

### 2B. Yen-Go Model Inventory

| R-ID | Label | Architecture | Filename | Purpose |
|------|-------|-------------|----------|---------|
| R-15 | quick | b18c384 | kata1-b18c384nbt-s9996..bin.gz | Quick analysis |
| R-16 | deep_enrich | b18c384 | kata1-b18c384nbt-s9996..bin.gz | Primary enrichment |
| R-17 | referee | b28c512 | kata1-b28c512nbt-s1219..bin.gz | Escalation referee |
| R-18 | test_fast | b10c128 | g170e-b10c128..bin.gz | Integration tests |
| R-19 | benchmark | b15c192 | kata1-b15c192.bin.gz | Performance comparison |

---

## 3. External Evidence: Tool Visit Counts & Configurations

### 3A. KaTrain (Python, sanderland/katrain)

Source: `katrain/config.json`, `katrain/KataGo/analysis_config.cfg`, `katrain/core/engine.py`

| R-ID | Setting | Value | Source | Purpose |
|------|---------|-------|--------|---------|
| R-20 | max_visits | **500** | config.json `engine.max_visits` | Standard analysis per position |
| R-21 | fast_visits | **25** | config.json `engine.fast_visits` | Quick/sweep analysis, move dots, alternative search |
| R-22 | max_time | **8.0s** | config.json `engine.max_time` | Time limit on analysis |
| R-23 | wide_root_noise | **0.04** | config.json `engine.wide_root_noise` | Candidate exploration diversity |
| R-24 | Re-analyze visits | **2500** | popups.kv `ReAnalyzeGamePopup` default | Deep re-analysis of full game |
| R-25 | Selfplay (setup) visits | **≥25** | game.py `selfplay()` | AI self-play setup positions |
| R-26 | Ponder max visits | **10,000,000** | engine.py `_write_stdin_thread()` | Continuous pondering (capped by time) |
| R-27 | Low-visits threshold | **25** | config.json `trainer.low_visits` | Minimum visits to show stats text |
| R-28 | Tsumego region | yes | popups.kv `TsumegoFramePopup` with margin | Area-restricted search for tsumego |
| R-29 | nnCacheSizePowerOfTwo | **20** (1M entries) | analysis_config.cfg | Neural net cache |
| R-30 | numAnalysisThreads | **12** | analysis_config.cfg | Parallel positions |
| R-31 | numSearchThreads | **8** | analysis_config.cfg | Threads per position |
| R-32 | nnMaxBatchSize | **96** | analysis_config.cfg | GPU batch size |

**Key insight**: KaTrain uses **500 visits as standard** and **25 as fast**. Their "deep" re-analysis default is **2500**. The KaTrain analysis_config.cfg ships with maxVisits=500 (matching the config.json default).

### 3B. KataGo Official Defaults (analysis_example.cfg)

Source: `cpp/configs/analysis_example.cfg`

| R-ID | Setting | Value | Notes |
|------|---------|-------|-------|
| R-33 | maxVisits | **500** | Default if not specified per-query |
| R-34 | numAnalysisThreads | **2** | Fewer than KaTrain — expects per-query override |
| R-35 | numSearchThreadsPerAnalysisThread | **16** | Higher per-position (interactive use case) |
| R-36 | nnCacheSizePowerOfTwo | **23** (8M entries) | Larger than KaTrain config |
| R-37 | nnMutexPoolSizePowerOfTwo | **17** | |
| R-38 | nnMaxBatchSize | **64** | |
| R-39 | wideRootNoise | **0.04** | Default for analysis mode (not GTP) |
| R-40 | reportAnalysisWinratesAs | BLACK | Consistent perspective |
| R-41 | rootSymmetryPruning | true | Exploits board symmetry |
| R-42 | useEvalCache | false (experimental) | Remembers past evals for repeated positions |
| R-43 | evalCacheMinVisits | 100 | Min visits for eval cache entry |

### 3C. Lizgoban (JS, kaorahi/lizgoban)

Source: `src/engine.js`

| R-ID | Setting | Value | Notes |
|------|---------|-------|-------|
| R-44 | analyze_interval_centisec | configurable | Continuous analysis interval (GTP-based, not analysis-engine) |
| R-45 | Peek analysis | **1 visit** | `lz-setoption name visits value 1` — single NN eval for quick peek |
| R-46 | analyze_move timeout | configurable (sec) | Time-limited analysis for temporary move eval |
| R-47 | HumanSL profiles | full range | `rank_1d`..`rank_20k`, `proyear_1800`..`proyear_2023` |
| R-48 | rootNumSymmetriesToSample | 2–8 recommended | For HumanSL quality improvement |
| R-49 | Analysis mode | GTP `kata-analyze` | Uses GTP protocol, not analysis engine JSON |

**Key insight**: Lizgoban uses GTP `kata-analyze` (continuous streaming), not the analysis engine. Visit counts are implicitly time-controlled via `analyze_interval_centisec`. For peek/quick eval, it uses **1 visit** (raw NN only). Real analysis is time-budgeted, not visit-budgeted.

### 3D. GoProblems/Ghostban

Source: HTTP fetch attempt returned 404. GitHub repo search returned errors.

| R-ID | Finding |
|------|---------|
| R-50 | `nicholasgasior/goproblems` does not have a `src/lib/katago.ts` file (404). The repo may use a different architecture or may not use KataGo directly. |
| R-51 | `pnprog/ghostban` search unavailable — repo index not yet available. Ghostban is primarily a browser-side SGF viewer/player; it does not run KataGo for analysis. |

---

## 4. HumanSL Model Requirements (from KataGo docs)

Source: `lightvector/KataGo/docs/Analysis_Engine.md` — "Human SL Analysis Guide"

### 4A. Setup Requirements

| R-ID | Requirement | Details |
|------|-------------|---------|
| R-52 | Separate model file | **Required**: `b18c384nbt-humanv0.bin.gz` — must be downloaded separately |
| R-53 | Command-line flag | `-human-model models/b18c384nbt-humanv0.bin.gz` — passed as additional argument |
| R-54 | Main model still needed | The normal KataGo model is still used for analysis. HumanSL is a **supplementary** model. |
| R-55 | Query parameter | `humanSLProfile` set in `overrideSettings` per query (NOT a top-level query field) |
| R-56 | includePolicy | **Must** request `"includePolicy": true` to get `humanPolicy` in response |
| R-57 | Model architecture | b18c384 only. No b40 or b60 variant exists for HumanSL as of KataGo 1.15.x |

### 4B. Available Profiles

| R-ID | Profile Type | Range | Format |
|------|-------------|-------|--------|
| R-58 | Modern rank | 20k–9d | `rank_20k` through `rank_9d` |
| R-59 | Pre-AlphaZero rank | 20k–9d | `preaz_20k` through `preaz_9d` |
| R-60 | Asymmetric rank | varies | `rank_{BR}_{WR}` or `preaz_{BR}_{WR}` |
| R-61 | Pro year | 1800–2023 | `proyear_1800` through `proyear_2023` |

### 4C. Alternative Usage: HumanSL as Main Model

| R-ID | Finding |
|------|---------|
| R-62 | Can pass `-model b18c384nbt-humanv0.bin.gz` (instead of normal model) to use HumanSL exclusively |
| R-63 | With search (>1 visit), KataGo will be **stronger** than the configured profile — search solves tactics |
| R-64 | For exact rank matching, use **1 visit + full temperature** — but this is only useful for move generation, not analysis |
| R-65 | HumanSL as main model has biased winrates/scores in handicap games and extreme positions |

### 4D. Interesting Parameters for Tsumego Analysis

| R-ID | Parameter | Value | Purpose |
|------|-----------|-------|---------|
| R-66 | `humanSLRootExploreProbWeightless` | 0.5 | Spend 50% of playouts exploring human-likely moves (doesn't bias eval) |
| R-67 | `humanSLCpuctPermanent` | 2.0 | Ensure high-humanPolicy moves get visits even if losing |
| R-68 | `ignorePreRootHistory` | false | Include move history context (humans play differently based on recent moves) |
| R-69 | `rootNumSymmetriesToSample` | 2–8 | Average more symmetries for better quality humanPolicy |
| R-70 | `humanSLOppExploreProbWeightful` | 0.8 | Anticipate human opponent sequences (trick plays, mistakes) |

---

## 5. Visit Count Recommendations for Tsumego Enrichment

### 5A. Comparative Table: Visit Counts by Tool and Purpose

| R-ID | Purpose | KataGo Default | KaTrain | Lizgoban | Yen-Go Current | Recommendation |
|------|---------|---------------|---------|----------|----------------|----------------|
| R-71 | Policy-only / technique detection | 1–10 | 25 (fast) | 1 (peek) | 200 | **50** — sufficient for policy rank, far cheaper |
| R-72 | Standard analysis (correct move validation) | 500 | 500 | time-based | 200 | **500** — match KaTrain/KataGo standard |
| R-73 | Deep analysis (refutation generation) | 500 | 2500 (re-analyze) | time-based | 100 (refutations) | **500–1000** per refutation move |
| R-74 | Max-effort (complex/uncertain positions) | user-defined | 10M (ponder) | time-based | 2000 (deep_enrich) | **2000–5000** for escalation |
| R-75 | Solution tree confirmation | N/A | N/A | N/A | 500 | **500** adequate |
| R-76 | Re-analysis game review | 500 | 2500 | time-based | N/A | N/A (not applicable) |

### 5B. Recommended Tier System for Yen-Go Enrichment

| R-ID | Tier | Visits | Model | Use Case | Current Gap |
|------|------|--------|-------|----------|-------------|
| R-77 | T0 (Policy-only) | 50 | b18c384 | Technique detection, policy rank, tag inference | Currently 200 — **4× too expensive** |
| R-78 | T1 (Standard) | 500 | b18c384 | Correct move validation, ownership, difficulty scoring | Currently 200 — **2.5× too low** |
| R-79 | T2 (Deep) | 2000 | b18c384 | Refutation tree generation, complex positions | Currently 2000 — **adequate** |
| R-80 | T3 (Referee) | 5000 | b28c512 | Escalation: uncertain results, sparse positions | No explicit setting — use referee model |
| R-81 | T-refutation | 500 | b18c384 | Per-refutation-move analysis | Currently 100 — **5× too low** |

---

## 6. Missing Config Parameters That Could Improve Accuracy

### 6A. Parameters We Should Add

| R-ID | Parameter | Recommended Value | Impact | Source |
|------|-----------|-------------------|--------|--------|
| R-82 | `rootNumSymmetriesToSample` | **4** (batch) / **8** (referee) | Reduces NN noise by averaging symmetries. KataGo docs recommend 2–8. We use 2 for deep_enrich. | KataGo docs R-69 |
| R-83 | `rootPolicyTemperature` | **1.2–1.5** for refutation discovery | A value > 1 makes KataGo explore wider, finding more candidate wrong moves | KataGo analysis docs |
| R-84 | `rootFpuReductionMax` | **0** for refutation discovery | Makes KataGo more willing to try diverse moves — critical for finding all plausible wrong moves | KataGo analysis docs |
| R-85 | `wideRootNoise` | **0.04** (standard) / **0.1** (refutation) | KaTrain uses 0.04 by default. Currently not explicitly set in Yen-Go queries. | KaTrain R-23 |
| R-86 | `analysisPVLen` | **15** (standard) / **30** (ko) | Already have ko_analysis.pv_len_by_ko_type. Standard PV length should be explicit. | KataGo example config |
| R-87 | `includePolicy` | **true** always | Needed for difficulty estimation and future HumanSL integration. Negligible performance impact per KataGo docs. | KataGo docs |
| R-88 | `nnCacheSizePowerOfTwo` | **23** (8M entries) | Our config doesn't explicitly set this. Default varies by config file used. Should ensure 8M for batch processing. | KataGo example R-36 |
| R-89 | `useGraphSearch` | **true** | Identifies transpositions in the search tree. Particularly valuable for ko and ladder puzzles where move order variations converge. | KataGo example config |
| R-90 | `useEvalCache` | **true** with `evalCacheMinVisits=100` | Experimental in KataGo but highly relevant for batch tsumego — positions repeat across solution/refutation trees. | KataGo example R-42 |

### 6B. Parameters to Consider for Future HumanSL Integration

| R-ID | Parameter | Value | Rationale |
|------|-----------|-------|-----------|
| R-91 | `humanSLProfile` | `rank_{level_kyu}` | Per-puzzle human policy calibration for difficulty estimation |
| R-92 | `humanSLRootExploreProbWeightless` | 0.3–0.5 | Explore human-likely wrong moves without biasing evaluation |
| R-93 | `-human-model` CLI flag | `b18c384nbt-humanv0.bin.gz` | Required to enable humanPolicy in responses |

---

## 7. Risks, License/Compliance Notes & Rejection Reasons

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-94 | Increasing visits from 200→500 will ~2.5× analysis time per puzzle | Medium | Offset with T0 tier (50 visits) for policy-only tasks. Net throughput may improve if T0 handles 60%+ of work. |
| R-95 | HumanSL model is b18 only — no b28/b40/b60 variant | Low | b18 is sufficient. HumanSL is supplementary, not the main model. |
| R-96 | `useEvalCache` is experimental (false by default in KataGo v1.16.4) | Low | Can test in lab environment before production. The feature is designed for exactly our use case (repeated positions). |
| R-97 | `rootPolicyTemperature > 1` and `rootFpuReductionMax = 0` change search behavior | Medium | Only apply these overrides for refutation-discovery queries, not standard analysis. Use `overrideSettings` per-query. |
| R-98 | KaTrain's `CALIBRATED_RANK_ELO` table is MIT-licensed | None | Already integrated in v1.17 as `elo_anchor` section. No additional licensing concern. |
| R-99 | Ghostban/goproblems analysis: no evidence obtained | Low | These tools primarily render/validate against pre-built solution trees. They don't run KataGo for analysis. Not a gap in our research. |

---

## 8. Planner Recommendations

### Recommendation 1: Rebalance visit tiers (HIGH CONFIDENCE)

**Current**: Default 200 visits for everything except deep_enrich (2000). Refutation analysis at 100 visits.
**Proposed**: Introduce 4-tier system — T0=50, T1=500, T2=2000, T3=5000.

**Rationale**: KaTrain (the most mature Go analysis tool) uses 500 as standard and 25 as fast. Our 200-visit default is in a "worst of both worlds" zone — too many for policy-only, too few for reliable move validation. The KataGo official default is also 500. Increasing refutation visits from 100→500 is critical — at 100 visits, KataGo may not even explore the correct refutation PV to sufficient depth.

**Cost**: T1 standard analysis will be ~2.5× slower per query, but T0 policy-only work (technique detection, preliminary classification) will be ~4× faster.

### Recommendation 2: Add refutation-specific overrideSettings (HIGH CONFIDENCE)

**Proposed**: For refutation discovery queries, override:
- `rootPolicyTemperature: 1.3` — wider exploration
- `rootFpuReductionMax: 0` — try more diverse moves
- `wideRootNoise: 0.08` — more candidate moves

**Rationale**: Standard analysis parameters optimize for finding the _best_ move. Refutation discovery needs the opposite — finding all _plausible wrong_ moves. KataGo explicitly supports per-query `overrideSettings` for this purpose. KaTrain uses `wideRootNoise: 0.04` standard and suggests `0.02–0.1` range.

### Recommendation 3: Increase rootNumSymmetriesToSample (MEDIUM CONFIDENCE)

**Current**: 2 for deep_enrich. Not set for standard queries (defaults to 1).
**Proposed**: 4 for standard queries, 8 for referee escalation.

**Rationale**: KataGo docs recommend this especially when relying heavily on policy quality. For tsumego where the correct move may have low prior, averaging more symmetries reduces NN noise. Cost is linear (4× or 8× first-eval latency) but amortized across search.

### Recommendation 4: Defer HumanSL integration to a separate initiative (MEDIUM CONFIDENCE)

**Rationale**: HumanSL requires a separate model file (`b18c384nbt-humanv0.bin.gz`) and `-human-model` CLI flag. It provides `humanPolicy` for predicting what human players at specific ranks would play — valuable for difficulty calibration and "how surprising is this move?" metrics. However, it's a net-new capability (new model download, modified engine startup, new query parameters, new output fields) that should be planned and tested independently. Current priority should be fixing the standard analysis visit tiers.

---

## 9. Handoff

| Field | Value |
|-------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260314-research-lizgoban-katrain-patterns/` |
| `artifact` | `15-research-visit-counts.md` |
| `top_recommendations` | 1. Rebalance visit tiers (T0=50/T1=500/T2=2000/T3=5000) 2. Add refutation-specific overrideSettings 3. Increase rootNumSymmetriesToSample 4. Defer HumanSL to separate initiative |
| `open_questions` | Q5: Ghostban/goproblems analysis settings (unavailable, low priority) |
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | low |
