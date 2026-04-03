# Research Brief: KataGo-LLM-Team Repository Analysis for Yen-Go Puzzle Enrichment

> **Initiative**: 20260326-research-katago-llm-team-analysis
> **Date**: 2026-03-26
> **Status**: research_completed

---

## 1. Research Question and Boundaries

**Primary question**: What patterns, signals, and architectures from the KataGo-LLM-Team repository (BrightonLiu-zZ/KataGo-LLM-Team) can improve Yen-Go's puzzle enrichment pipeline — specifically teaching comment quality, technique classification accuracy, and KataGo signal utilization?

**Boundaries**:
- In scope: KataGo eval analysis, engine management, reward design, LLM integration patterns, signal gaps
- Out of scope: GRPO training infrastructure itself (Yen-Go is offline-first, no runtime LLM), model fine-tuning replication, GTP proxy / Lizzie deployment
- Constraint: Yen-Go is zero-runtime-backend; any LLM usage would be offline pipeline-only (build-time enrichment, not inference-time)

---

## 2. Internal Code Evidence

### IR-1: Current KataGo Signal Capture (bridge.py, solve_position.py)

| Ref | File | Signal | How Used |
|-----|------|--------|----------|
| IR-1a | `tools/puzzle-enrichment-lab/bridge.py` L246-257 | `winRate`, `winRateLost`, `scoreLead`, `visits`, `prior` (policy_prior), `pv`, `ownership` | Per-move info passed to JS GUI and enrichment stages |
| IR-1b | `tools/puzzle-enrichment-lab/bridge.py` L266-267 | `rootWinRate`, `rootScoreLead`, `rootVisits` | Root position stats for delta classification |
| IR-1c | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | `winrate delta = root_winrate - move_winrate` → TE/BM/NEUTRAL classification | Primary move quality signal |
| IR-1d | `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py` | `policy_entropy` (Shannon entropy of top-K priors), `correct_move_rank` (rank of correct move in policy ordering) | Difficulty estimation, stored in `PipelineContext` |

### IR-2: Teaching Comment Assembly (comment_assembler.py)

| Ref | File | Pattern | Limitation |
|-----|------|---------|------------|
| IR-2a | `analyzers/comment_assembler.py` L55-109 | 3-layer composition: instinct_phrase + technique_phrase + signal_phrase. 15-word cap. Uses template substitution. | "Mechanical" — templates produce uniform output like "{technique_phrase} — {signal_phrase}." No reasoning about WHY a move works. |
| IR-2b | `analyzers/comment_assembler.py` L82 | V1 fallback: if no signal_phrase, emit v1_comment verbatim | Fallback is even more generic |
| IR-2c | `analyzers/detectors/*.py` | 28 technique detectors. Each returns `Detection(detected: bool, confidence: float, tag: str, evidence: str)` | Detection is binary; evidence field is brief. No explanation of game-theoretic reasoning. |

### IR-3: KataGo Engine Management (local_subprocess.py, single_engine.py)

| Ref | File | Pattern |
|-----|------|---------|
| IR-3a | `engine/local_subprocess.py` L85-86 | `numAnalysisThreads={num_threads}`, `nnMaxBatchSize={num_threads}` — ties batch size to thread count |
| IR-3b | `analyzers/single_engine.py` | Config-driven visits escalation, model routing by level category, `resolve_katago_config()` |
| IR-3c | `models/analysis_request.py` L88-94 | `maxVisits`, `analysisPVLen` per-request overrides |
| IR-3d | `config/analysis.py` L70-77 | `pv_len_by_ko_type` — per-ko-type PV length override |

### IR-4: Configuration Architecture

| Ref | File | Detail |
|-----|------|--------|
| IR-4a | `config/katago-enrichment.json` | Schema v1.28, extensive config: difficulty thresholds, refutation params, visit tiers, quality weights, calibration settings |
| IR-4b | `config/teaching.py` | `TeachingCommentsConfig`, `TeachingCommentEntry`, `load_teaching_comments_config` — configurable template system |
| IR-4c | `config/technique.py` | Per-detector configs: `min_pv_length`, ko detection params, ladder configs |

---

## 3. External References (KataGo-LLM-Team)

### ER-1: Repository Overview

| Ref | Detail |
|-----|--------|
| ER-1a | **Project**: GRPO-Aligned 9×9 Go AI. Trains Qwen3-8B (v4) / Qwen2.5-7B (v1 legacy) to play 9×9 Go using KataGo as teacher. |
| ER-1b | **Architecture**: SGF → KataGo → JSONL pipeline → GRPO training → LoRA merge → GGUF quantization → edge deployment via LM Studio + C++ GTP proxy |
| ER-1c | **Key insight**: KataGo is used ONLY at data-generation time, not at inference. LLM learns to internalize KataGo's evaluation. |
| ER-1d | **Models**: Qwen3-8B (v4, current), Qwen2.5-7B-Instruct (v1, legacy). Both fine-tuned with LoRA (r=16, alpha=32). |
| ER-1e | **Board scope**: 9×9 only. Uses `KataGo18b9x9.gz` specialized model. |
| ER-1f | **License**: No license file observed in repository. |

### ER-2: KataGo Eval Analysis (analyze_katago_evals.py)

| Ref | Finding |
|-----|---------|
| ER-2a | **Fields extracted**: `policy`, `winrate`, `scoreLead` per move from `katago_evals` dict |
| ER-2b | **Statistical methods**: Summary stats (mean, median, std, Q1, Q3, min, max) + 3-panel histograms |
| ER-2c | **Data structure**: JSONL with per-game records, each containing `katago_evals: {move_coord: {policy, winrate, scoreLead}}` |
| ER-2d | **Visualization**: matplotlib histograms with mean/median overlay — simple but effective for distribution understanding |
| ER-2e | **What they DON'T analyze that we do**: ownership, PV sequences, policy_entropy, correct_move_rank |
| ER-2f | **What they analyze that we could adopt**: Per-move scoreLead distribution across entire dataset, policy distribution shape (heavy-tailed) |

### ER-3: KataGo Engine Management (run_katago_analysis.py)

| Ref | Finding |
|-----|---------|
| ER-3a | **Protocol**: JSON Analysis protocol (same as ours) — `asyncio.create_subprocess_exec` with `stdin/stdout/stderr` pipes |
| ER-3b | **Config**: `analysis.cfg` — 9×9 specialized: `numAnalysisThreads=12`, `numSearchThreads=6`, `maxVisits=500`, `nnMaxBatchSize=64`, `nnCacheSizePowerOfTwo=16`, `analysisPVLen=15`, `reportAnalysisWinratesAs=SIDETOMOVE` |
| ER-3c | **Crash recovery**: `MAX_RESTARTS=9999`, `MAX_ROW_CRASHES=5` (skip row after 5 consecutive crashes), `RESTART_INTERVAL=1000` (proactive restart every 1000 rows to flush GPU/shm state) |
| ER-3d | **Performance**: Streaming input (generator), no full-file load. Resume via `START_LINE`. Appends to output file. |
| ER-3e | **Query format**: `rootPolicyTemperature=2.5`, `maxVisits=2000`, `includePolicy=True`, 9×9 board |
| ER-3f | **Key difference from us**: They use `rootPolicyTemperature=2.5` to soften policy distribution for training diversity. We don't use policy temperature. |
| ER-3g | **Ownership**: NOT requested in their queries (`includeOwnership` absent). We request it when configured. |
| ER-3h | **Memory**: Lazy streaming + line-by-line output append. We batch through pipeline stages. |

### ER-4: Reward Design (reward_design.md + train_grpo_v4.py)

| Ref | Component | Formula | Weight |
|-----|-----------|---------|--------|
| ER-4a | **Gate: Format + Legality** | Regex for REASONING: + MOVE:, thinking consistency check, legal-move validation. −1.0 (format fail), −0.5 (occupied/illegal), 0.0 (valid) | Gating (binary pass/fail) |
| ER-4b | **R_policy (v3)** | Direct KataGo policy prior P ∈ [0,1] for chosen move | 0.5 |
| ER-4c | **R_score (v3)** | ΔS = S_actual − S_best, clipped at −8.0, normalized: R_score = max(ΔS, −8.0) / 8.0 ∈ [−1, 0] | 0.3 |
| ER-4d | **R_winrate (v3)** | ΔW = W_actual − W_best ∈ [−1, 0] | 0.2 |
| ER-4e | **R_policy_log (v4)** | log10(max(P, 1e-6)) + 4.0) / 4.0 → smooth [0,1]: P=1e-4→0.0, P=0.01→0.5, P=0.1→0.75, P=1.0→1.0 | Adaptive |
| ER-4f | **R_rank (v4)** | Percentile rank by scoreLead among all evaluated legal moves. Best=1.0, worst=0.0 | Adaptive |
| ER-4g | **Adaptive mixing (v4)** | closeness = 1.0 − 2.0×|root_winrate − 0.5|. w_rank = 0.5 + 0.3×closeness. w_policy = 1.0 − w_rank. Close games → heavier rank. Lopsided → heavier policy. | Combined |
| ER-4h | **Total (v3)** | Valid_Flag × (0.5×R_policy + 0.3×R_score + 0.2×R_winrate) | — |
| ER-4i | **Total (v4)** | gate_penalty + w_policy×R_policy_log + w_rank×R_rank | — |

### ER-5: Data Pipeline & Training Format

| Ref | Finding |
|-----|---------|
| ER-5a | **Training data**: JSONL with fields: `id`, `rules`, `komi`, `initialStones`, `moves`, `analyzeTurns`, `user_prompt`, `katago_evals` (per-move dict), `root_winrate`, `root_scoreLead` |
| ER-5b | **Data augmentation**: D4 symmetry group (8 rotations/reflections) × color flip = 16× augmentation |
| ER-5c | **Dataset balancing**: v4 downsamples lopsided positions (root_winrate > 0.95 or < 0.05) to 30% |
| ER-5d | **Prompt format**: ASCII board ('.'=empty, 'X'=Black, 'O'=White) + valid-coordinates list + REASONING/MOVE format instruction |
| ER-5e | **v4 dataset**: ~113k rows from ~270k augmented (after lopsided downsampling + valid-coords restoration) |

### ER-6: Move Distribution Analysis (total_move_histogram.py)

| Ref | Finding |
|-----|---------|
| ER-6a | **Purpose**: Simple SGF move-count histogram — counts total moves per game file |
| ER-6b | **Method**: Regex `;\s*[BW]\[[^\]]*\]` on raw bytes, counts matches per file |
| ER-6c | **Relevance to us**: Minimal. This is full-game analysis, not tsumego-specific. Our puzzles have fixed move trees. |

---

## 4. Candidate Adaptations for Yen-Go

### CA-1: Log-Scaled Policy Signal for Teaching Comments

| Ref | Adaptation | Source | Impact |
|-----|-----------|--------|--------|
| CA-1a | Use ER-4e's log-scaled policy formula to classify move "intuition" quality in teaching comments. A move with policy 0.8 → "Natural first instinct" vs policy 0.001 → "Hidden tesuji — requires deep reading" | `train_grpo_v4.py::_compute_r_policy_log` | HIGH — directly addresses "mechanical" comment problem |
| CA-1b | Use ER-4f's percentile-rank-by-scoreLead as a "punish severity" signal. Worst-ranked move → "This loses X points because..." | `train_grpo_v4.py::_compute_r_rank` | HIGH — enables quantified wrong-move explanations |
| CA-1c | Adaptive closeness weighting (ER-4g) to adjust comment tone: close positions → "Critical move", lopsided → "Good technique" | `train_grpo_v4.py::katago_composite_reward_func` | MEDIUM — enriches comment vocabulary |

### CA-2: LLM-Assisted Teaching Comment Generation

| Ref | Adaptation | Source | Impact |
|-----|-----------|--------|--------|
| CA-2a | Feed KataGo signals as structured context to an LLM API for natural-language teaching comment generation at build time | ER-1c (offline-only pattern) | HIGH — transforms comments from templates to explanations |
| CA-2b | Use ER-5d's ASCII board prompt format as input to an LLM for position understanding | `train_grpo_v4.py::SYSTEM_PROMPT` | MEDIUM — proven board representation format |
| CA-2c | Structure a "teaching prompt" that includes: ASCII board, correct move, wrong moves + their rank/scoreLead deltas, detected techniques, ownership map summary | Novel combination of ER-4 + IR-1 + IR-2 | HIGH — comprehensive context for LLM |

### CA-3: Signal Gap Closure

| Ref | Signal | They Capture | We Capture | Gap |
|-----|--------|-------------|------------|-----|
| CA-3a | `rootPolicyTemperature` | 2.5 (softens policy for diversity) | Not used | Consider for refutation candidate diversity — softened policy could reveal more wrong-move candidates |
| CA-3b | `policy` as flat 82-element array | Yes (map_policy_to_coords) | Only per-moveInfo `prior` | We could capture the full policy array for entropy analysis and "what does the neural net think about every intersection" |
| CA-3c | `scoreLead percentile rank` | Yes (R_rank) | Not computed; we use score delta only | Add rank-among-evaluated-moves as a signal for "how bad is this wrong move" |
| CA-3d | `log-scaled policy` | Yes (R_policy_log) | Raw policy_prior only | Log transform reveals more about marginal moves |
| CA-3e | `closeness` metric | 1.0 − 2×|rwr − 0.5| | Not computed | Useful for comment tone adaptation |
| CA-3f | `rootScoreLead` | Yes, stored per record | We have `root_score` but don't use it for comment generation | Could enhance "this move costs X points" explanations |

### CA-4: Engine Management Improvements

| Ref | Adaptation | Source | Impact |
|-----|-----------|--------|--------|
| CA-4a | Proactive engine restart every N queries (ER-3c: RESTART_INTERVAL=1000) | `run_katago_analysis.py` | LOW — our SingleEngineManager already handles restarts, but proactive restart could prevent GPU memory leaks in batch mode |
| CA-4b | Skip-on-crash per-puzzle policy (ER-3c: MAX_ROW_CRASHES=5) | `run_katago_analysis.py` | LOW — we already have error policy CONTINUE/FAIL_FAST per stage |
| CA-4c | `nnCacheSizePowerOfTwo=16` (64K cache entries) | `analysis.cfg` | LOW — may already be in our tsumego.cfg; worth auditing |
| CA-4d | `analysisPVLen=15` for deeper reading | `analysis.cfg` | MEDIUM — we use per-ko-type PV length but could extend default for teaching comment generation |

### CA-5: Eval Analysis Tooling

| Ref | Adaptation | Source | Impact |
|-----|-----------|--------|--------|
| CA-5a | Build similar policy/winrate/scoreLead distribution analysis for our puzzle corpus | `analyze_katago_evals.py` | MEDIUM — would reveal calibration insights (e.g., what does policy distribution look like for correct vs wrong moves across difficulty levels) |
| CA-5b | Histogram of "correct move policy prior" by difficulty level — would validate whether our difficulty estimation correlates with KataGo confidence | Novel | MEDIUM |

---

## 5. Risks, License/Compliance, and Rejection Reasons

### Risks

| Ref | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| RK-1 | **9×9 vs general board**: Their entire pipeline is 9×9 only; we handle 9×9 through 19×19. Policy temperature, visit counts, and thresholds may not transfer to larger boards. | HIGH | All adapted thresholds must be validated against our technique calibration suite across board sizes |
| RK-2 | **Full-game vs tsumego**: Their training data is full games, not isolated positions. KataGo eval distributions will differ fundamentally (tsumego has extreme winrate swings, full games are gradual). | HIGH | Our existing delta-based classification already handles this, but any borrowed thresholds need recalibration |
| RK-3 | **LLM latency**: Adding LLM API calls to the enrichment pipeline introduces latency and cost. At ~500ms per API call and ~9K puzzles, that's 75 minutes of additional pipeline time. | MEDIUM | Batch-parallelize LLM calls; use as optional enhancement stage; cache results |
| RK-4 | **LLM hallucination**: LLM may generate plausible but incorrect Go reasoning (e.g., wrong liberty count, incorrect capturing sequence). | HIGH | Validate LLM output against KataGo signals (e.g., if LLM says "captures" but ownership doesn't change, flag). Use structured constraints. |
| RK-5 | **rootPolicyTemperature=2.5 for enrichment**: High temperature flattens the policy distribution, making all moves look more equally probable. Good for training diversity, potentially misleading for technique detection. | MEDIUM | Use temperature only for refutation candidate discovery, not for correct-move analysis |
| RK-6 | **No license**: Repository has no LICENSE file. Code patterns should be treated as inspiration only, never verbatim copy. | LOW | We adapt concepts, not code |

### Rejection Reasons

| Ref | Rejected Item | Reason |
|-----|--------------|--------|
| RJ-1 | Importing their training pipeline or GRPO framework | Yen-Go is offline-first static site; no runtime LLM inference; training is out of scope |
| RJ-2 | Their GTP proxy / Lizzie integration | Not relevant to our pipeline architecture |
| RJ-3 | D4 data augmentation for training | We already handle rotation/reflection in our `Position.rotate()`/`Position.reflect()` for analysis, but we don't train models |
| RJ-4 | `total_move_histogram.py` | Full-game metric, not applicable to tsumego positions |
| RJ-5 | Their `map_policy_to_coords()` for 9×9 only | Our enrichment already handles arbitrary board sizes |

---

## 6. Planner Recommendations

### R-1: Implement Computed Signal Enhancements (NO LLM required)

**Impact: HIGH | Effort: LOW | Risk: LOW**

Add three derived signals from KataGo data we already capture, inspired by their reward design:

1. **`log_policy_score`**: `(log10(max(prior, 1e-6)) + 4.0) / 4.0` — smooth [0,1] intuition measure. Feed into comment assembler: policy > 0.75 → "Natural move"; policy < 0.25 → "Requires deep reading".
2. **`score_lead_rank`**: Percentile rank of each move's scoreLead among all evaluated moves. Enables "This is the Nth worst move, losing ~X points" in wrong-move comments.
3. **`position_closeness`**: `1.0 - 2.0 * abs(root_winrate - 0.5)` — adapts comment urgency. Near 0.5 → "Critical — the game hangs on this move"; near 0/1 → "Good technique to finish".

These require zero new KataGo queries — they're computed from existing `move_infos` data. Implementation touches `analyzers/estimate_difficulty.py` and `analyzers/comment_assembler.py`.

### R-2: Build LLM Teaching Comment Stage (Pipeline Extension)

**Impact: HIGH | Effort: MEDIUM | Risk: MEDIUM**

Add an optional `TeachingLLMStage` after the existing teaching_stage:

```
Input payload to LLM:
{
  "board_ascii": "9x9 ASCII board",
  "correct_move": "D4",
  "correct_move_signals": {
    "winrate": 0.95, "score_lead": 12.3, "policy_prior": 0.72,
    "log_policy": 0.86, "rank": 1, "pv": ["D4", "E5", "F6"]
  },
  "wrong_moves": [
    {"move": "C3", "winrate": 0.45, "score_lead": -3.2, "rank": 5, "pv": [...]}
  ],
  "detected_techniques": ["snapback", "liberty-shortage"],
  "position_closeness": 0.85,
  "player_to_move": "black",
  "difficulty_level": "intermediate"
}
```

System prompt: "You are a Go teacher explaining a tsumego puzzle. Given the board position and KataGo analysis signals, write a 1-2 sentence teaching comment explaining WHY the correct move works. Reference the detected technique. Do not hallucinate move sequences — only reference the provided PV."

**Key constraints**: Build-time only (Holy Law #1: zero runtime backend). Cache LLM responses per content_hash. Feature-gated via config. Validate against existing template-based comments for regression.

### R-3: Add Eval Analysis Tooling for Calibration

**Impact: MEDIUM | Effort: LOW | Risk: LOW**

Build a script similar to `analyze_katago_evals.py` that profiles our enrichment corpus:
- Policy prior distribution for correct vs wrong moves, stratified by difficulty level
- Score delta distribution by technique tag
- Winrate swing histogram by puzzle type

This would reveal whether our difficulty estimation thresholds (in `katago-enrichment.json`) are well-calibrated and where technique detectors are failing.

### R-4: Experiment with rootPolicyTemperature for Refutation Discovery

**Impact: MEDIUM | Effort: LOW | Risk: MEDIUM**

Their use of `rootPolicyTemperature=2.5` is interesting for our refutation generation. Currently, our refutation candidates come from KataGo's default policy (concentrated on top moves). A softened policy could surface more diverse wrong-move candidates, improving the `generate_refutations()` output. Add as a per-request override when `includePolicy=True` for refutation queries only.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260326-research-katago-llm-team-analysis/` |
| `artifact` | `15-research.md` |
| `post_research_confidence_score` | 82 |
| `post_research_risk_level` | medium |

### Top Recommendations (ordered by expected value)

1. **R-1**: Computed signal enhancements (log_policy, score_lead_rank, position_closeness) — HIGH impact, LOW effort, no new dependencies
2. **R-2**: LLM teaching comment stage — HIGH impact, MEDIUM effort, requires API dependency and validation infrastructure
3. **R-3**: Eval analysis tooling — MEDIUM impact, LOW effort, improves calibration understanding
4. **R-4**: rootPolicyTemperature for refutations — MEDIUM impact, LOW effort, needs careful testing

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Which LLM provider/model should the TeachingLLMStage target? | A: OpenAI GPT-4o-mini (cheapest), B: Claude Haiku (fast), C: Local GGUF via llama.cpp (no API cost, slower), D: Other | A (GPT-4o-mini — best cost/quality for short outputs) | — | ❌ pending |
| Q2 | Should the LLM stage replace or augment existing template comments? | A: Replace entirely, B: Augment (LLM comment stored in separate field, template kept as fallback), C: A/B test both | B (augment — safe rollback, compare quality) | — | ❌ pending |
| Q3 | What's the budget ceiling for LLM API calls per pipeline run? | A: $0 (local only), B: <$5 per 1K puzzles, C: <$20 per 1K puzzles, D: Other | B (<$5 per 1K — GPT-4o-mini at ~$0.15/1M input tokens) | — | ❌ pending |
| Q4 | Should R-1 (computed signals) be implemented independently before R-2 (LLM stage), or as part of the same initiative? | A: R-1 first (validate signals, then feed to LLM), B: Together (LLM stage uses computed signals from day one) | A (R-1 first — validates the signal-to-comment mapping without LLM dependency) | — | ❌ pending |

---

## Appendix: Signal Gap Analysis Summary

| Signal | KataGo-LLM-Team | Yen-Go Enrichment | Status |
|--------|-----------------|-------------------|--------|
| winrate per move | ✅ | ✅ | Parity |
| scoreLead per move | ✅ | ✅ | Parity |
| policy prior per move | ✅ | ✅ | Parity |
| visits per move | ✅ | ✅ | Parity |
| PV sequences | ✅ (15 moves) | ✅ (per-ko-type length) | Parity |
| ownership per intersection | ❌ (not requested) | ✅ | **Yen-Go ahead** |
| policy_entropy | ❌ | ✅ | **Yen-Go ahead** |
| correct_move_rank | ❌ | ✅ | **Yen-Go ahead** |
| log-scaled policy | ✅ | ❌ | **Gap** |
| scoreLead percentile rank | ✅ | ❌ | **Gap** |
| position closeness (adaptive) | ✅ | ❌ | **Gap** |
| rootPolicyTemperature | ✅ (2.5) | ❌ | **Gap** |
| full policy array (all intersections) | ✅ (82-element) | ❌ (per-moveInfo only) | **Gap** |
| root_scoreLead in comments | ✅ (stored) | ✅ (captured, unused in comments) | Parity (untapped) |
| score delta 8-point clipping | ✅ | ❌ | **Gap** (useful for comment severity) |
| D4 augmentation | ✅ (16× training) | ✅ (Position.rotate/reflect) | Parity (different use) |
| lopsided position filtering | ✅ (>0.95/<0.05 at 30%) | ❌ | Not applicable (we analyze all puzzles) |
