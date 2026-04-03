# Charter: Refutation Tree Quality Improvements

> Initiative: `20260315-2000-feature-refutation-quality`
> Type: Feature
> Last Updated: 2026-03-15

---

## Summary

Improve the puzzle-enrichment-lab's refutation tree generation by applying KataGo training paper insights to inference-time search configuration and algorithms. The core gap: refutation discovery is too single-pass and too winrate-threshold-centric, while ownership, score-lead, and adaptive visit allocation signals are already available but underused.

## Scope

- **In-scope**: `tools/puzzle-enrichment-lab/` (analyzers, config models) + `config/katago-enrichment.json`
- **Out-of-scope**: Frontend, backend pipeline, model training, network architecture changes

## Goals

1. Higher wrong-move recall — catch refutations missed by winrate-only thresholds
2. Better refutation quality — ownership-based "teaching refutations" that show group status change
3. Compute efficiency — adaptive visits + model routing to reduce batch processing time
4. Broader candidate discovery — find hidden tesuji and low-policy traps

## Non-Goals

1. No model training or network architecture changes (DF-1, explicitly deferred — fundamentally different scope)
2. No frontend changes
3. No changes to `backend/puzzle_manager/`

## Constraints

- All changes MUST be feature-gated with config defaults matching current behavior (v1.14 pattern)
- Absent config key = current behavior (zero behavior change)
- Must not bloat SGF output
- Must not increase per-puzzle wall-time without opt-in
- All new signals must emit structured log events matching `observability.disagreement_sink_path` pattern

## Acceptance Criteria

1. All 12 "To Implement" features have config keys in `katago-enrichment.json`
2. Each feature defaults to disabled/current-behavior
3. All existing tests pass with no regressions
4. New unit tests cover each feature gate
5. AGENTS.md updated in same commit as structural changes

---

## Consolidated Findings (Deduplicated from 3 Agent Reports)

The raw research contained 3 overlapping agent reports with ~30 findings total. After deduplication, 14 unique concepts were identified and classified into 3 categories below.

---

### Table 1: Already Implemented (No Action Required)

| ID | Finding | Config Evidence | Code Evidence | Paper Section |
|----|---------|----------------|---------------|---------------|
| AI-1 | **FPU Reduction** — `root_fpu_reduction_max=0` for refutation queries (unexplored moves get parent value, no penalty) | `refutation_overrides.root_fpu_reduction_max: 0` | Wired in `generate_refutations.py` via `override_settings` | Sec 2, footnote 3 |
| AI-2 | **Ko-Aware Rules Override** — per-ko-type rules switching (tromp-taylor for ko puzzles enables recapture exploration) | `ko_analysis.rules_by_ko_type: {none: chinese, direct: tromp-taylor, approach: tromp-taylor}` | Wired in `query_builder.py` ko_type dispatch | Sec 2 + Appendix D |
| AI-3 | **Temperature Candidate Scoring** — diversified refutation candidates beyond strict policy ranking | `refutations.candidate_scoring: {mode: temperature, temperature: 1.5}` | `identify_candidates()` in `generate_refutations.py` uses KaTrain-style `exp(-temp * points_lost) * policy` | Sec 2, Appendix D |
| AI-4 | **Seki Detection** — winrate band + score lead heuristic as tree-building stopping condition | `ai_solve.seki_detection: {winrate_band_low: 0.45, winrate_band_high: 0.55, score_lead_seki_max: 2.0}` | Stopping condition #3 in `_build_tree_recursive()` in `solve_position.py` | Sec 4.1 ownership+score |

**Governance note**: Seki detection is config+code wired. Behavioral verification (are seki-tagged puzzles produced?) is a planning-phase check (RC-7).

---

### Table 2: Deferred or Rejected

| ID | Finding | Reason | Decided By | Future Tracking |
|----|---------|--------|------------|-----------------|
| DF-1 | **Training-level model changes** — network architecture, retraining, new model families | Out of scope for inference-time lab. High cost, low near-term leverage. No training infrastructure exists. | All 7 panel members, Principal Staff Eng A ("stay inference-side") | Not tracked — fundamentally different scope |
| DF-2 | **Player-side alternative exploration** — branch to try alternative player moves at intermediate tree depths (`player_alternative_rate`) | Risks polluting single-answer tsumego solution trees with noise. Would need `rate=0.0` default anyway. | Cho Chikun (9p): "In tsumego there is typically ONE correct answer. Exploring player alternatives could pollute the solution tree." All pros agreed on default=off. | Config key proposed (`player_alternative_rate: 0.0`). May revisit for special collections only. |
| DF-3 | **Opponent policy for teaching comments** — use KataGo's opponent_policy head as a refutation quality signal and teaching comment enrichment | Genuine future value (Ke Jie: "natural punishment", Hana Park: "dramatically improve learning experience") but all reports rated P3/LOW. Current teaching comments are functional via winrate thresholds. | All reports consensus: P3/LOW. Ke Jie and Hana Park support future implementation. | **Deferred with player-impact note** — tracked for future sprint. Has real pedagogical value. |
| DF-4 | **Surprise-weighted calibration set** — weight calibration data by difficulty to improve threshold tuning for rare tactical motifs | Algorithm-driven calibration pipeline change. Needs reproducible sampling and seed discipline. | 6/7 panel support but classified as calibration infrastructure, not search quality. | Track as calibration improvement backlog item. |
| DF-5 | **Best-resistance line generation** — generate strongest opponent resistance as first-class objective | Compute cost concerns (5/7 support). Should come after cost controls are in place (F-1, F-9). | 5/7 panel support with compute cost cap requirement. | Revisit after adaptive visits and model routing reduce baseline cost. |

---

### Table 3: Plan to Implement (8 Items, Priority Ordered)

| ID | Finding | Description | Type | Effort | Impact | Config Key(s) | Code Location |
|----|---------|-------------|------|--------|--------|---------------|---------------|
| PI-1 | **Ownership delta for refutation scoring** | Use ownership change between moves as refutation quality signal. A move causing ownership flip from +0.7 to -0.7 is a "teaching refutation" even if winrate delta < 0.08. | Config + ~50 LOC | Low | HIGH — catches refutations missed by winrate alone | `refutations.ownership_delta_weight: 0.0` | `generate_refutations.py` + `solve_position.py` (`_get_ownership()` exists but unused for scoring) |
| PI-2 | **Adaptive visit allocation per tree depth** | Branch decision points get full visits (500), forced/inner continuation nodes get fewer (125). Matches how humans read: deep at branches, fast through forced sequences. | Config + algorithm | Medium | HIGH — 30-50% deeper trees within same query budget | `solution_tree.visit_allocation_mode: "fixed"`, `branch_visits: 500`, `continuation_visits: 125` | `solve_position.py` `_build_tree_recursive()` — currently fixed `tree_visits=500` for all non-forced nodes |
| PI-3 | **Score-lead delta for refutation identification** | Promote score delta from suboptimal_branches fallback to main refutation scoring. Score-lead is more stable than winrate for tsumego (20pt loss = clearly bad even if winrate oscillates). | Config + ~20 LOC | Low | MEDIUM — more stable refutation detection | `refutations.score_delta_enabled: false`, `score_delta_threshold: 5.0` | `generate_refutations.py` — `_get_score_lead()` exists in `solve_position.py`, `suboptimal_branches.score_delta_threshold=2.0` exists but isolated |
| PI-4 | **Model routing by puzzle complexity** | b10c128 for entry-level puzzles (novice/beginner, depth ≤ 3), b18c384 for core, b28c512 for strong. Identical move ordering for simple life-and-death. | Config mapping | Low | HIGH — 2-4x batch throughput for easy puzzles | `ai_solve.model_by_category: {entry: "test_fast", core: "quick", strong: "referee"}` | `config/ai_solve.py` + `analyzers/single_engine.py` — `test_fast: b10c128` already in models config |
| PI-5 | **Board-size-scaled Dirichlet noise** | Scale `wide_root_noise` by board size: `noise = base * 361 / legal_moves`. Fixed 0.08 is too diluted on 19x19 and too concentrated on 9x9. Paper formula: α₉ₓ₉ ≈ 0.27 vs α₁₉ₓ₁₉ ≈ 0.05. | Config formula | Low | MEDIUM — better candidate discovery on cropped boards | `refutation_overrides.noise_scaling: "fixed"`, `noise_base: 0.03`, `noise_reference_area: 361` | `config/refutations.py` `RefutationOverridesConfig` — currently fixed `wide_root_noise=0.08` |
| PI-6 | **Forced minimum visits per refutation candidate** | Force engine to explore low-policy moves using `nforced(c) = (k * P(c) * sum)^0.5`. Many vital tsumego moves have near-zero policy (sacrifices, throw-ins). | Algorithm | Medium | MEDIUM — discovers hidden refutations with near-zero policy | `refutations.forced_min_visits_formula: false`, `forced_visits_k: 2.0` | `generate_refutations.py` `generate_single_refutation()` — FPU is correct but forced-playout allocation absent |
| PI-7 | **Branch-local disagreement escalation** | Escalate compute per-branch, not per-puzzle. Spend more on ambiguous branches where model/search disagree, less on easy ones. | Config + algorithm | Medium | MEDIUM — better reliability per unit of compute | `solution_tree.branch_escalation_enabled: false`, `branch_disagreement_threshold: 0.10` | `solve_position.py` — escalation currently puzzle-level via `refutation_escalation` |
| PI-8 | **Diversified root candidate harvesting** | Multi-pass candidate discovery: initial scan, then secondary scan with different noise/temperature to find human-tempting wrong moves missed by first pass. | Config + algorithm | Medium | MEDIUM — higher wrong-move recall for tesuji-like decoys | `refutations.multi_pass_harvesting: false`, `secondary_noise_multiplier: 2.0` | `generate_refutations.py` `identify_candidates()` — currently single initial scan |
| PI-9 | **Player-side alternative exploration (auto-detect)** | At intermediate tree depths, explore player alternatives to discover co-correct paths and trick moves. Auto-detect puzzle type: enable for position-only and multi-solution puzzles, skip for curated single-answer. Uses existing `run_position_only_path()` and `co_correct_min_gap` infrastructure. | Config + algorithm | Medium | HIGH — essential for position-only and multi-solution puzzles | `solution_tree.player_alternative_rate: 0.0`, `player_alternative_auto_detect: true` | `solve_position.py` `_build_tree_recursive()` — player nodes currently never branch. `solve_paths.py` already has `run_position_only_path()` dispatch. |
| PI-10 | **Opponent policy for teaching comments** | Request KataGo's opponent_policy head and use it to generate concrete teaching comments: "After your mistake at D4, White naturally plays E5 to capture." Replaces abstract winrate-loss messages. | Config + ~40 LOC | Low | MEDIUM — significantly better teaching comment quality | `teaching.use_opponent_policy: false` | `comment_assembler.py` — teaching comment infrastructure exists. KataGo can output opponent policy but it's currently unrequested. |
| PI-11 | **Surprise-weighted calibration** | Weight calibration data by surprise (engine disagreement/difficulty) to improve threshold tuning for rare tactical motifs and blind-spot positions. | Algorithm | Medium | MEDIUM — better thresholds for heterogeneous internet puzzles | `calibration.surprise_weighting: false`, `surprise_weight_scale: 2.0` | `config/infrastructure.py` `CalibrationConfig` + calibration pipeline. `.lab-runtime/calibration-results/` already exists. |
| PI-12 | **Best-resistance line generation** | For each refutation, search for the opponent response that maximizes punishment. For position-only puzzles, this IS how solutions are discovered. Compute-capped by config. | Algorithm | Medium | HIGH — more realistic refutation trees, essential for position-only solve | `refutations.best_resistance_enabled: false`, `best_resistance_max_candidates: 3` | `generate_refutations.py` `generate_single_refutation()` — currently takes engine's first response, not strongest. |

---

## Governance Synthesis (Cross-Report Consensus)

| GV-ID | Member | Vote | Key Position |
|-------|--------|------|-------------|
| GV-1 | Cho Chikun (9p) | Approve with concern | Ownership delta (PI-1) is the top priority. Warns against noisy branches. Player alternatives must default off. |
| GV-2 | Lee Sedol (9p) | Approve | Diversified harvesting (PI-8) finds hidden tesuji. Suggests promoting PI-8 to rank 5. Supports adaptive visits. |
| GV-3 | Shin Jinseo (9p) | Approve | Model routing (PI-4) is highest ROI for compute. Noise scaling (PI-5) needed for cropped boards. |
| GV-4 | Ke Jie (9p) | Approve | Ownership delta and score delta improve teaching quality. F-8 (deferred) has real value. |
| GV-5 | Principal Staff Eng A | Approve with constraint | All changes feature-gated. v1.14 pattern. No new dependencies. |
| GV-6 | Principal Staff Eng B | Approve with measurement | Explicit metrics required: wrong-move recall, zero-refutation rate, avg queries/puzzle, wall-time. |
| GV-7 | Hana Park (1p) | Approve with UX constraint | Fewer but clearer wrong branches. F-8 should be tracked as deferred-with-player-impact. |

**Charter governance decision**: `GOV-CHARTER-CONDITIONAL` (approve with conditions: RC-7 seki behavioral verification, RC-8 F-8 tracking). Both conditions are non-blocking and addressed above.

---

## Cross-Reference Mapping (3 Reports → Consolidated IDs)

This table maps the overlapping IDs from the 3 original agent reports to the consolidated finding IDs used in this charter.

| Consolidated ID | Report 1 (F1-F6) | Report 2 (F-1 to F-12) | Report 3 (1-8) | Description |
|-----------------|-------------------|--------------------------|-----------------|-------------|
| AI-1 | — | F-6 | — | FPU Reduction |
| AI-2 | — | F-10 | 5 (partial) | Ko-Aware Rules |
| AI-3 | — | F-11 | — | Temperature Scoring |
| AI-4 | — | F-12 | — | Seki Detection |
| DF-1 | F6 | — | — | Training-level changes |
| DF-2 | — | F-7 | — | Player alternatives |
| DF-3 | — | F-8 | 8 (partial) | Opponent policy |
| DF-4 | — | — | 6 | Surprise-weighted calibration |
| DF-5 | — | — | 8 | Best-resistance objective |
| PI-1 | F2 | F-3 | 4 | Ownership delta |
| PI-2 | F1 | F-1 | 2 | Adaptive visits |
| PI-3 | F3 | F-4 | 3, 5 | Score-lead delta |
| PI-4 | — | F-9 | — | Model routing |
| PI-5 | — | F-5 | — | Noise scaling |
| PI-6 | F4 | F-2 | 1, 7 | Forced visits / candidate diversity |
| PI-7 | F5 | — | — | Branch-local disagreement |
| PI-8 | F4 | — | 7 | Diversified harvesting |

> **See also**:
> - [Research: 15-research.md](../starter/15-research.md) — Feature-Researcher codebase audit (59 findings)
> - [Config: katago-enrichment.json](../../config/katago-enrichment.json) — Current config source of truth
> - [AGENTS.md](../../tools/puzzle-enrichment-lab/AGENTS.md) — Lab architecture map
