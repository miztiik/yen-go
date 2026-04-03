# Research Brief: WebKatrain vs Yen-Go Enrichment Lab — KataGo Position Analysis

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Research Agent:** Feature-Researcher  
**Date:** 2026-03-07  
**Research Question:** How does WebKatrain/yen-go-sensei handle position analysis without a solution tree, and what can we learn to fix the enrichment lab's hard-rejection failure modes?

---

## 1. Research Question and Boundaries

**Core Question:** WebKatrain successfully analyzes ANY position and returns candidate moves with policy/winrate. Our enrichment lab hard-rejects position-only SGFs and also rejects when AI-Solve finds no "correct" moves. What is the architectural difference, and how can we close the gap?

**Boundaries:**

- Internal: `tools/yen-go-sensei/` (WebKatrain port), `tools/puzzle-enrichment-lab/`
- External: WebKatrain architecture (sir-teo.github.io), KataGo MCTS algorithm
- Out of scope: Backend pipeline changes, config threshold tuning, new engine modes

---

## 2. Internal Code Evidence

### 2.1 WebKatrain / yen-go-sensei Analysis Pipeline

| R-ID | File                                                           | Symbol                             | Finding                                                                                                                                                                                                                                                                                                                                                         |
| ---- | -------------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-01 | `tools/yen-go-sensei/src/engine/katago/client.ts:32–107`       | `KataGoEngineClient.analyze()`     | Calls KataGo, returns a raw `KataGoAnalysisPayload`. Takes `topK`, `visits`, `board`, `currentPlayer`. No classification of moves — all returned moves pass through.                                                                                                                                                                                            |
| R-02 | `tools/yen-go-sensei/src/engine/katago/types.ts:39–72`         | `KataGoAnalysisPayload`            | Payload contains: `rootWinRate`, `rootScoreLead`, `policy` (len 362, all legal moves), and `moves[]` with per-move `{ x, y, winRate, winRateLost, scoreLead, visits, prior, pv }`. Every returned move includes `winRateLost` = `rootWinRate - m.winRate`, which is conceptually identical to our `delta`.                                                      |
| R-03 | `tools/yen-go-sensei/src/store/gameStore.ts:1357–1400`         | `buildAnalysisResult()`            | ALL moves from KataGo are stored directly into `node.analysis.moves`. No policy threshold pre-filter. No "correct/wrong" classification gate. The UI renders candidate dots for every returned move.                                                                                                                                                            |
| R-04 | `tools/yen-go-sensei/src/store/gameStore.ts:2140–2200`         | `'local' strategy in makeAiMove()` | The Gaussian sampling is an **AI play** strategy, NOT an analysis feature. After receiving analysis, move selection for AI opponent weights `policy_prior` per move by a Gaussian centered on the last played stone: `weight = exp(-0.5 * (dx² + dy²) / variance)`. Tenuki = `1 - gaussian`. This controls WHERE the AI plays to simulate "natural" play style. |
| R-05 | `tools/yen-go-sensei/src/engine/katago/analyzeMcts.ts:250–330` | `expandNode()`                     | MCTS tree expansion uses softmax policy logits to assign `prior` to each legal move (pass included), then keeps the top `maxChildren` by prior. The `prior` values here correspond to raw NN policy output. No threshold gate — a move with policy 0.001 still gets an edge if it's in the top K.                                                               |

**Key Architectural Insight (R-03):** WebKatrain's design contract is: "KataGo analysis always returns useful data; show all of it." There is no concept of "no valid candidates" — if KataGo returns a move list, every move is displayable.

### 2.2 Enrichment Lab Failure Modes

| R-ID | File                                                              | Lines                           | Failure                                                                                                                                                                                                       | Condition                                                                                                        |
| ---- | ----------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| R-06 | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`          | ~546–555                        | **Hard-exit A**: Returns `REJECTED`, "No correct first move found in SGF"                                                                                                                                     | `correct_move_sgf is None AND ai_solve_active is False` — position-only SGF without ai_solve enabled             |
| R-07 | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`          | ~595–604                        | **Hard-exit B**: Returns `REJECTED`, "AI-Solve found no correct moves"                                                                                                                                        | `ai_solve_active is True` but `pos_analysis.correct_moves == []` after analysis                                  |
| R-08 | `tools/puzzle-enrichment-lab/analyzers/solve_position.py:140–170` | `analyze_position_candidates()` | Pre-filter gate: `if move_policy < confirmation_min_policy: continue`                                                                                                                                         | Config: `confirmation_min_policy = 0.03`. Any move with policy < 0.03 is silently dropped before classification. |
| R-09 | `tools/puzzle-enrichment-lab/analyzers/solve_position.py:170–200` | `analyze_position_candidates()` | Root winrate derivation: `root_winrate = normalize_winrate(best_move_info[0].winrate)`. Delta for best move = 0 by definition ≤ 0.05 → should be TE. BUT the best move itself can fail the pre-filter (R-08). | IF `move_infos[0].policy_prior < 0.03`, best move is filtered out, leaving `correct_moves=[]`.                   |
| R-10 | `config/katago-enrichment.json:168–210`                           | `ai_solve` section              | **Feature-gated off**: `"enabled": false`. Position-only SGFs hit R-06 without ever calling KataGo.                                                                                                           | All ai_solve logic, including path to R-07, is unreachable until someone sets `enabled: true`.                   |

### 2.3 The `confirmation_min_policy = 0.03` Failure Conditions

By R-08 and R-09, zero correct moves can result from four distinct conditions:

| R-ID | Condition                                      | Real-world trigger                                                                                                                                                                                              |
| ---- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-11 | Best move (rank 0) has `policy_prior < 0.03`   | Highly diffuse position: many nearly-equal options. Average policy ≈ 1/N legal moves. For N > 33, average is below threshold. Tsumego rarely reach N > 33 candidates, but unusual seki/endgame positions might. |
| R-12 | PASS is rank-0 move                            | EDGE-4: already-resolved position. Raises `ValueError`; caught by surrounding `try/except`; sets `_ai_solve_failed = True`.                                                                                     |
| R-13 | All legal moves are in globally-diffuse policy | With `topK=10` and a 19×19 position where KataGo has no strong signal (e.g., position is invalid/ambiguous), all 10 returned moves may be below 0.03.                                                           |
| R-14 | Insufficient visits for confidence             | At low visit counts, KataGo's policy is noisy. Even the correct tsumego move may have estimated policy < 0.03 if visit budget is too low.                                                                       |

### 2.4 What HAS Solution Tree Does vs. Doesn't Need

The charter (00-charter.md) correctly identifies that partial enrichment is possible without a solution tree:

| Enrichment Stage                           | Needs Solution Tree | Needs KataGo    | Needs Correct Move |
| ------------------------------------------ | ------------------- | --------------- | ------------------ |
| Technique classification                   | No                  | No (stonecraft) | No                 |
| Teaching comments                          | No                  | Partially       | No                 |
| Difficulty estimation (policy-only)        | No                  | Yes             | No                 |
| Difficulty estimation (MCTS composite)     | No                  | Yes             | No                 |
| Hint generation (from position heuristics) | No                  | Partially       | No                 |
| Refutation branches                        | Yes                 | Yes             | Yes                |
| Solution validation                        | Yes                 | Yes             | Yes                |

Source: `tools/puzzle-enrichment-lab/analyzers/` directory listing confirms these are independent analyzers.

---

## 3. External References

| R-ID | Source                                                                                                                 | Relevance                                                                                                                                                                                                                                                                                                                          |
| ---- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-15 | KataGo analysis format (GTP extension protocol, github.com/lightvector/KataGo/blob/master/docs/Analysis_GTP_README.md) | KataGo's `analyze` command ALWAYS returns `rootInfo` (position-level stats) separate from `moveInfos` (per-move). `rootInfo.winrate` is a direct estimate, not derived from best move. This is NOT used in our current Python engine layer — we derive root winrate from `move_infos[0].winrate`, which is a subtle approximation. |
| R-16 | KaTrain source (github.com/sanderland/katrain) — the project yen-go-sensei is ported from                              | KaTrain uses `analysis["rootInfo"]["winrate"]` directly for root winrate, not `moveInfos[0].winrate`. The `winRateLost` per move is then `rootInfo.winrate - moveInfo.winrate`. This eliminates the failure condition in R-11/R-09: even if no moves pass a threshold, `rootInfo` always has a valid winrate.                      |
| R-17 | WebKatrain (sir-teo.github.io/web-katrain/) — the WASM port yen-go-sensei is based on                                  | Runs full MCTS in browser WASM; returns `rootWinRate` as a first-class field in `KataGoAnalysisPayload` (see R-02). This is the MCTS root node value, not derived from any child move. Our Python engine layer should have an equivalent: `AnalysisResponse.root_winrate`.                                                         |
| R-18 | Thomsen lambda-search / proof-number search literature                                                                 | Our `branch_min_policy` + `depth_policy_scale * depth` (CHANGELOG) already references Thomsen. The key insight: in lambda-search, a position can be classified as "unknown" without rejection — the tree builder continues from an unknown root. This principle supports "partial enrichment without correct move classification". |

---

## 4. Candidate Adaptations for Yen-Go

### CA-1: Use `AnalysisResponse.root_winrate` Instead of Deriving from `move_infos[0]`

**Problem:** The current `root_winrate = normalize_winrate(best_move_info[0].winrate)` fails when `move_infos[0]` is PASS or has very low policy.  
**Adaptation:** `AnalysisResponse` already has a `root_winrate` field (see `tools/puzzle-enrichment-lab/models/analysis_response.py`). This should be used directly. This mirrors KaTrain (R-16) and WebKatrain (R-17).  
**Risk:** Low. If `AnalysisResponse.root_winrate` is already populated from the KataGo response, this is a one-line change in `analyze_position_candidates()`.

### CA-2: Remove Pre-Filter Gate from Partial-Enrichment Path

**Problem:** `confirmation_min_policy = 0.03` can block ALL candidates in unusual positions (R-11–R-14).  
**Adaptation:** When the goal is partial enrichment (tier 1), skip the `confirmation_min_policy` pre-filter. Instead, use policy as a ranking signal (sort by policy desc), not a yes/no gate. Take the top-1 move by visits as the "pseudo-correct" for difficulty estimation without injecting it as a solution.  
**Risk:** Low for partial enrichment path. The pre-filter exists for tree-building quality (DD-2), which doesn't apply to tier-1 partial output.

### CA-3: Soft-Downgrade Hard-Exits to `enrichment_tier=1` Returns

**Problem:** Both BUG A (R-06) and BUG B (R-07) use `_make_error_result()` which returns `REJECTED`. This discards ALL information.  
**Adaptation:** Replace both hard-exits with a partial-enrichment path that:

1. Continues the pipeline through technique classification, hint generation, difficulty estimation (policy-only at minimum)
2. Sets `enrichment_tier=1` on `AiAnalysisResult`
3. Does NOT inject a solution tree into the SGF
4. Sets `ac:0` in YQ (untouched solution, but position-level enrichment present)  
   **Architecture alignment:** Matches charter goals and the D26 tier system (00-charter.md:18–19). No new KataGo engine modes required.

### CA-4: For BUG B Path — Reuse Already-Obtained KataGo Analysis

**Problem:** When ai_solve is active, a KataGo query was already executed before the `no correct moves` rejection (R-07). This data is discarded.  
**Adaptation:** Capture the `pos_analysis` result before the empty-correct-moves check. Pass it to difficulty estimation (policy-only path uses `pos_analysis.all_classifications` which may still have candidates). This matches WebKatrain's philosophy (R-03): "If KataGo returned anything, use it."  
**Risk:** Low. The `pos_analysis.all_classifications` list is already populated even when `correct_moves == []` (R-08 filters correct but not all).

### CA-5: For BUG A Path — Run KataGo Analysis Before Early Return

**Problem:** BUG A (R-06) exits WITHOUT ever calling KataGo. Policy-only difficulty estimation cannot run without any engine call.  
**Adaptation:** For position-only SGFs when `ai_solve` is inactive, add a lightweight KataGo "position scan" at low visits (e.g., 100–200 visits) to obtain:

- `root_winrate` → difficulty confidence context
- `policy[]` → technique classifier can use policy distribution to detect tactical patterns
- Top-1 move by visits → drives policy-only difficulty estimate  
  **Risk:** Medium. Adds a KataGo call for every previously-rejected position-only SGF. Volume impact depends on how many such SGFs exist in the pipeline. Recommend making this configurable: `partial_enrichment_scan_visits: 100`.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-ID | Item                                                        | Risk Level                                                                                                                                                                                                  | Note                                                                                                                                                                                                                         |
| ---- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-19 | yen-go-sensei Gaussian sampling relevance                   | **Rejected**                                                                                                                                                                                                | This is an AI play style feature (R-04), not analysis. It uses policy priors to select WHERE the AI plays, not to identify correct/wrong moves. No adaptation applicable to enrichment lab.                                  |
| R-20 | Removing `confirmation_min_policy` entirely                 | **Rejected for full-enrichment path**                                                                                                                                                                       | DD-2 documentation justifies the pre-filter for tree quality: low-policy moves in tight tsumego are likely noise. Keep for tree-building; remove/bypass only for partial enrichment (CA-2).                                  |
| R-21 | Using top-1 move as "pseudo-correct" and injecting into SGF | **Rejected**                                                                                                                                                                                                | Charter explicitly says: position-only SGF without ai_solve → `enrichment_tier=1` AND "DO NOT inject a solution tree into the SGF" (10-clarifications.md Q3 inferred answer). Pseudo-correct for difficulty estimation only. |
| R-22 | License: yen-go-sensei / WebKatrain                         | No code copying needed. All adaptations are architectural patterns, not literal code from yen-go-sensei. KaTrain is Apache-2.0 licensed; WebKatrain is MIT. Neither applies since we adapt ideas, not code. |
| R-23 | `AnalysisResponse.root_winrate` field availability          | Low risk. The field must be verified populated by the engine layer before CA-1 can be applied. Check `tools/puzzle-enrichment-lab/models/analysis_response.py` and the `single_engine.py` response parser.  |

---

## 6. Planner Recommendations

1. **Fix root_winrate derivation first (CA-1):** Switch from `move_infos[0].winrate` to `AnalysisResponse.root_winrate` in `analyze_position_candidates()`. This eliminates R-09/R-11: the best-move-below-threshold failure. This is a 1-line/1-test change and should be done independently before the main refactor.

2. **Replace BUG A hard-exit with position-scan + tier-1 result (CA-3 + CA-5):** For `ai_solve` inactive position-only SGFs, run a lightweight scan (100–200 visits), feed results to difficulty/technique estimators, return `AiAnalysisResult` with `enrichment_tier=1`. This is the highest-value change: it converts 100% of currently-rejected position-only SGFs into partially-enriched outputs.

3. **Replace BUG B hard-exit with reuse of existing analysis (CA-3 + CA-4):** When `pos_analysis.correct_moves == []`, fall through to partial enrichment using the `pos_analysis` data already in hand (all_classifications, root_winrate, policy). Cap the commit to `enrich_single.py` and `models/ai_analysis_result.py`. No solver changes needed (`solve_position.py` is working correctly per charter out-of-scope).

4. **Gaussian weighting: partially applicable to tree builder (R-19 AMENDED):**
   - **For enrichment analysis** (position scan, move classification): NOT applicable — play strategy, not analysis
   - **For tree builder** (`_build_tree_recursive` opponent nodes): POTENTIALLY applicable — tree building IS play simulation. Deterministic Gaussian weighting ($w_i = p_i \cdot e^{-d_i^2/2\sigma^2}$) could improve opponent response spatial realism for diffuse-policy positions. Deferred to future investigation per governance reconsideration (2026-03-07).
   - **R-19 amendment:** Prior blanket rejection overturned. User correctly identified that move 2+ in `build_solution_tree` is play simulation, not analysis. See `70-governance-decisions.md` "Future Investigation" section.

---

## 7. Confidence and Risk Update

| Metric                             | Value | Reasoning                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **post_research_confidence_score** | 88    | Both external code bases fully read; failure conditions traced to exact lines; AnalysisResponse.root_winrate availability needs 1 more file read to confirm (R-23).                                                                                                                                                          |
| **post_research_risk_level**       | low   | All three failure modes are localized to `enrich_single.py`; KISS adaptations avoid new abstractions; `solve_position.py` and all other analyzers are confirmed out-of-scope and untouched. The main implementation risk is verifying that `AnalysisResponse.root_winrate` is reliably populated by the engine layer (R-23). |

**Open Questions for Planner:**

| q_id | question                                                                                                                                                          | options                                                                                               | recommended                                                                      | status     |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------- |
| Q1   | Is `AnalysisResponse.root_winrate` populated from the KataGo `rootInfo.winrate` field, or is it derived?                                                          | A: Populated from `rootInfo.winrate` directly / B: Derived from moveInfos / C: Unknown                | A — read `tools/puzzle-enrichment-lab/models/analysis_response.py` to confirm    | ❌ pending |
| Q2   | What is the expected volume of position-only SGFs that currently hit BUG A? Is a lightweight scan per-puzzle acceptable, or should scanning be opt-in per source? | A: Scan always / B: Scan opt-in via source config / C: Scan only if `partial_enrichment.enabled=true` | B — source-level config matches existing pattern of per-source `ai_solve` gating | ❌ pending |
| Q3   | Should `enrichment_tier` be an integer (1/2/3) or an enum slug (`bare`/`structural`/`full`) in `AiAnalysisResult`?                                                | A: Integer (1/2/3) / B: Slug enum / C: Both (int + string label)                                      | A: Integer — simpler, maps to D26 directly, no new enum class needed             | ❌ pending |

---

## Handoff Summary

```
research_completed: true
initiative_path: TODO/initiatives/2026-03-07-refactor-enrichment-no-solution-resilience/
artifact: 15-research.md
top_recommendations:
  1. Switch root_winrate derivation to AnalysisResponse.root_winrate (CA-1, 1-line fix)
  2. BUG A: position-scan + tier-1 result (CA-3 + CA-5)
  3. BUG B: reuse existing pos_analysis data, fall through to partial enrichment (CA-3 + CA-4)
  4. Reject Gaussian sampling as irrelevant to enrichment (R-19)
open_questions: [Q1, Q2, Q3]
post_research_confidence_score: 88
post_research_risk_level: low
```
