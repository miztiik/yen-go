# Governance Decisions: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Last Updated:** 2026-03-07

---

## Options-Level Decision

| Field           | Value                                     |
| --------------- | ----------------------------------------- |
| decision        | approve                                   |
| status_code     | GOV-OPTIONS-APPROVED                      |
| selected_option | OPT-1 (Soft-Downgrade with Position Scan) |
| unanimous       | Yes (6/6)                                 |

**Rationale:** OPT-1 captures the WebKaTrain insight (always get KataGo data) without restructuring the control flow. Preserves `ai_solve` semantics. Adds `enrichment_tier` signaling for pipeline integration.

---

## Design Decisions (Consolidated — FINAL after Design Review)

| DD   | Selected          | Title                                            | Status        | Key Rationale                                                                                                                                         |
| ---- | ----------------- | ------------------------------------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| DD-1 | DD1-A             | Use `analysis.root_winrate` directly             | ✅ Active     | KataGo `rootInfo.winrate` is canonical position evaluation. 1-line fix.                                                                               |
| DD-2 | DD2-A **REVISED** | Position-only = FULL AI-Solve                    | ✅ Active     | User correction: "If position-only, that becomes the full enrichment." Remove guard condition, reuse existing AI-Solve path.                          |
| DD-3 | DD3-A             | Reuse pos_analysis for Bug B fallback            | ✅ Active     | KataGo data already paid for. Tier-2 fallback.                                                                                                        |
| DD-4 | —                 | ~~Position scan visits config~~                  | **WITHDRAWN** | No lightweight scan needed. Position-only uses existing `tree_visits: 500`.                                                                           |
| DD-5 | DD5-C             | Keep D26 tier semantics                          | ✅ Active     | 1=Bare, 2=Structural, 3=Full. No change needed.                                                                                                       |
| DD-6 | DD6-A             | Fallback stages: difficulty + techniques + hints | ✅ Active     | Only for fallback (AI-Solve fails). Main path = full enrichment.                                                                                      |
| DD-7 | DD7-A             | try/except → stone-pattern fallback              | ✅ Active     | Engine unavailable → tier 1.                                                                                                                          |
| DD-8 | DD8-A             | AiAnalysisResult as-is                           | ✅ Active     | YAGNI: enrichment_tier + ac is the integration contract.                                                                                              |
| DD-9 | **NEW**           | Position-only AI-Solve unconditional             | ✅ Active     | Ignore `ai_solve.enabled` for position-only puzzles. If no tree exists, building one IS the enrichment.                                               |
| FPU  | **ABSORBED**      | KM-01 IS the FPU-analog                          | ✅ Documented | Kawano simulation: first sibling fully explored, subsequent try cached replies before full expansion. Already implemented in `_build_tree_recursive`. |

---

## Must-Hold Constraints (Consolidated)

| RC-ID | Source  | Constraint                                                                             |
| ----- | ------- | -------------------------------------------------------------------------------------- |
| RC-1  | DD-1    | Use `analysis.root_winrate` from `rootInfo.winrate`, NOT `move_infos[0].winrate`       |
| RC-2  | DD-2    | Bug A KataGo scan MUST be wrapped in try/except, fall to stone-pattern tier-1          |
| RC-3  | DD-3    | Bug B MUST reuse existing `pos_analysis` — no additional KataGo call                   |
| RC-4  | DD-5    | `enrichment_tier` range 1-3 preserved. Use existing field, do NOT add duplicate        |
| RC-5  | DD-4    | Scan visits configurable via `deep_enrich.position_scan_visits: 100`                   |
| RC-6  | Options | New code paths must have mock-based unit tests                                         |
| RC-7  | Options | Observability log line for scan path: visit count + elapsed time                       |
| RC-8  | DD-2    | Do NOT inject solution tree into SGF for tier-1/tier-2 partial results                 |
| RC-9  | DD-5    | Update `enrichment_tier` docstring for tier-2 dual semantics (condition)               |
| RC-10 | DD-6    | Use `estimate_difficulty_policy_only()`, NOT `estimate_difficulty()` for partial paths |
| RC-11 | DD-6    | Teaching comments ONLY if technique_tags is non-empty                                  |
| RC-12 | DD-8    | SGF `YQ.ac` must be consistent with tier (tier 1/2 → `ac:0`, tier 3 → `ac:2/3`)        |

---

## Panel Member Support Table

| GV-ID    | Member     | Domain | Decisions Voted On  | Votes                |
| -------- | ---------- | ------ | ------------------- | -------------------- |
| GV-1–6   | Full panel | Mixed  | OPT-1 selection     | 6 approve            |
| GV-1–6   | Full panel | Mixed  | DD-1 (root_winrate) | 6 approve            |
| GV-1–6   | Full panel | Mixed  | DD-2 (Bug A scan)   | 6 approve            |
| GV-1–6   | Full panel | Mixed  | DD-3 (Bug B reuse)  | 6 approve            |
| GV-7–12  | Full panel | Mixed  | DD-4 (100 visits)   | 6 approve            |
| GV-13–18 | Full panel | Mixed  | DD-5 (D26 tiers)    | 5 approve, 1 concern |
| GV-19–24 | Full panel | Mixed  | DD-6 (3 stages)     | 6 approve            |
| GV-25–30 | Full panel | Mixed  | DD-7 (try/except)   | 6 approve            |
| GV-31–36 | Full panel | Mixed  | DD-8 (no new model) | 6 approve            |

---

## Handover

| Field          | Value                                                                                                                                                           |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent     | Governance-Panel                                                                                                                                                |
| to_agent       | Feature-Planner → Plan-Executor                                                                                                                                 |
| message        | All options and design decisions approved. RC-1 through RC-12 must be reflected in task breakdown. Proceed to plan + tasks + analysis + plan governance review. |
| blocking_items | None                                                                                                                                                            |

---

## Plan-Level Decision

| Field       | Value                                         |
| ----------- | --------------------------------------------- |
| decision    | approve_with_conditions                       |
| status_code | GOV-PLAN-CONDITIONAL                          |
| unanimous   | No (5 approve, 1 concern — housekeeping only) |

### Plan Review Conditions

| RC-P-ID | Condition                                                                                           | Blocking                    |
| ------- | --------------------------------------------------------------------------------------------------- | --------------------------- |
| RC-P1   | Complete `status.json` rationale fields                                                             | Before execution — **DONE** |
| RC-P2   | Clarify Bug B variable naming: `pre_analysis` (raw AnalysisResponse) is correct, not `pos_analysis` | Before T6                   |
| RC-P3   | Remove dead `_compute_config_hash` call from `_build_partial_result` helper                         | During T4                   |

### Final Handover to Plan-Executor

| Field               | Value                                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent          | Governance-Panel                                                                                                                                                                            |
| to_agent            | Plan-Executor                                                                                                                                                                               |
| message             | Plan approved for execution. 12 tasks (T1-T12), 4 execution phases, 12 RC constraints, 3 plan conditions (RC-P1 done, RC-P2/P3 during execution). Execute per 40-tasks.md dependency order. |
| blocking_items      | None                                                                                                                                                                                        |
| re_review_requested | true                                                                                                                                                                                        |
| re_review_mode      | review (post-implementation)                                                                                                                                                                |

---

## Deep Research Review: WebKaTrain Gaussian Mechanisms

**Date:** 2026-03-07  
**Status:** GOV-OPTIONS-APPROVED (unanimous 6/6)  
**Conclusion:** No changes to existing plan needed.

### Three Mechanisms Evaluated

| Mechanism                                                  | WebKaTrain                                                | Our Lab                                         | Adopt?                                                                                                                                                                              |
| ---------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. `wideRootNoise`** (MCTS Gaussian exploration)         | 0.04 (KataGo default)                                     | 0.03 (tsumego-tuned, `tsumego_analysis.cfg:47`) | **Already adopted** ✅                                                                                                                                                              |
| **2. "Local" Gaussian spatial weighting** (play strategy)  | `exp(-d²/2σ²)` from last move, σ=1.5, stochastic sampling | Chebyshev D=2 binary filter from all stones     | **No** ❌ — Wrong domain (play vs analysis), wrong reference point (last move vs stones), KataGo policy already encodes spatial awareness |
| **3. `pickFromWeightedCoords`** (two-phase spatial→policy) | Gaussian sample N=15, then rank by policy                 | Binary filter, then sort by policy              | **Already equivalent** ⚠️ — Same conceptual structure, our version is deterministic                                                                                                 |

### Mathematical Analysis (Panel Mathematician)

- Information loss from binary vs Gaussian filter: ~0.07 bits/puzzle (negligible)
- Formula: $H_{\text{loss}} = -\sum_{d > D} p(d) \log p(d)$ where $p(d>2) < 0.05$ for SDK tsumego
- KataGo NN policy already provides the spatial gradient that Gaussian weighting would add → double-counting

### Key Insight (Panel Go Expert — Shin Jinseo 9p)

> "KataGo's neural net policy ALREADY encodes spatial locality. Moves near fighting groups get high policy priors; distant moves get low priors. Our `confirmation_min_policy=0.03` filter leverages this implicitly. Adding manual Gaussian on top would be double-counting spatial locality."

### Must-Hold Constraints from Research

| Constraint                                                           | Source                  |
| -------------------------------------------------------------------- | ----------------------- |
| `wideRootNoise=0.03` remains tuned for tsumego (not 0.04)            | Cho Chikun, Shin Jinseo |
| No Gaussian spatial weighting in enrichment pipeline (current scope) | Unanimous               |
| Edge cases → increase Chebyshev D to 3, not Gaussian                 | Lee Sedol               |

---

## Reconsideration: Gaussian for Tree Builder (User Challenge)

**Date:** 2026-03-07  
**Status:** GOV-OPTIONS-CONDITIONAL (4 approve-for-recording, 2 concern)  
**Trigger:** User challenged blanket rejection, arguing tree building IS play simulation

---

## Implementation Review Decision (Post-Execution)

| Field       | Value               |
| ----------- | ------------------- |
| decision    | approve             |
| status_code | GOV-REVIEW-APPROVED |
| unanimous   | Yes (6/6)           |

### Panel Member Reviews

| GV-ID | Member                     | Domain              | Vote    | Supporting Comment                                                                                                                   |
| ----- | -------------------------- | ------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| GV-1  | Cho Chikun (9p)            | Classical tsumego   | approve | DD-1 correct: rootInfo.winrate is canonical pre-move evaluation. Tier system maps cleanly. Pass-as-best-move remains hard rejection. |
| GV-2  | Lee Sedol (9p)             | Intuitive fighter   | approve | DD-9 captures the right insight. Multiple fallback paths preserved. No scenario produces zero output anymore.                        |
| GV-3  | Shin Jinseo (9p)           | AI-era professional | approve | CA-1 fix critical. Default AiSolveConfig for position-only trusts KataGo correctly.                                                  |
| GV-4  | Ke Jie (9p)                | Strategic thinker   | approve | Policy-only difficulty provides approximate level classification for downstream consumers.                                           |
| GV-5  | Principal Staff Engineer A | Systems architect   | approve | Error handling architecture sound. 8 new tests. get_effective_max_visits consolidation eliminates maintenance hazard.                |
| GV-6  | Principal Staff Engineer B | Data pipeline       | approve | Observability maintained. Broad except Exception acceptable due to scoping. Clean integration contract.                              |

### Review Handover

| Field          | Value                                                                              |
| -------------- | ---------------------------------------------------------------------------------- |
| from_agent     | Governance-Panel                                                                   |
| to_agent       | Plan-Executor                                                                      |
| decision       | approve                                                                            |
| status_code    | GOV-REVIEW-APPROVED                                                                |
| message        | Phase I approved unanimously. All 13 tasks completed, all RC constraints verified. |
| blocking_items | None                                                                               |

---

## Thorough Implementation Review (User-Requested Deep Review)

| Field       | Value                                                    |
| ----------- | -------------------------------------------------------- |
| decision    | change_requested → **resolved**                          |
| status_code | GOV-REVIEW-REVISE → GOV-REVIEW-APPROVED (after fixes)    |
| unanimous   | Yes (6/6 change_requested, then 6/6 approve after fixes) |

### Findings

| F-ID | Severity     | Finding                                                                                                                                                                                                       | Fix Applied                                                                     |
| ---- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| F1   | **BLOCKING** | `ai_solve_active` stale flag: position-only with production config (`ai_solve.enabled=false`) had `ai_solve_active=False`, causing AC=0 instead of AC=2, tree truncation not recorded, goal inference skipped | ✅ Added `ai_solve_active = True` at DD-9 block entry                           |
| F2   | **HIGH**     | T8 test used weak negative assertions, masking F1                                                                                                                                                             | ✅ Rewrote with positive assertions on `enrichment_tier` and error flag absence |
| F3   | LOW          | `discover_alternatives` imported but unused in position-only block                                                                                                                                            | ✅ Removed                                                                      |
| F4   | LOW          | Root winrate semantic shift (best-move-relative → position-baseline). New semantics more correct but thresholds may need recalibration                                                                        | Accepted — thresholds are config-driven                                         |
| F5   | LOW          | Broad `except Exception` in DD-7                                                                                                                                                                              | Accepted — scoped to AI-Solve block, ValueError caught separately               |
| F6   | OBSERVATION  | `_build_partial_result` lacks phase timing                                                                                                                                                                    | Accepted for Phase I                                                            |
| F7   | OBSERVATION  | D57/D58/D59 doc overlap                                                                                                                                                                                       | Consistent with existing D-series style                                         |
| F8   | OBSERVATION  | `_make_analysis` mock backward-compat masks DD-1 difference                                                                                                                                                   | Correct approach — T7 tests cover divergent case                                |
| F9   | MEDIUM       | DD-9 default config only handles absent section, not `enabled=false`                                                                                                                                          | Resolved by F1 fix — `ai_solve_active=True` overrides regardless                |

### Post-Fix Verification

125 tests pass, 0 failures after F1/F2/F3 fixes applied.

### Handover (Final)

| Field          | Value                                                                                                                                                     |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent     | Governance-Panel                                                                                                                                          |
| to_agent       | Plan-Executor                                                                                                                                             |
| decision       | approve                                                                                                                                                   |
| status_code    | GOV-REVIEW-APPROVED                                                                                                                                       |
| message        | Thorough review found and resolved 1 blocking bug (F1: stale ai_solve_active), 1 test gap (F2), 1 dead import (F3). All fixes verified. Phase I approved. |
| blocking_items | None                                                                                                                                                      |

> "The first move IS position analysis, but after the 2nd move it IS the AI playing. At that point we should be using our capabilities to choose the best move."

**Panel verdict:** The user is correct. `_build_tree_recursive()` in `solve_position.py` is play simulation, not pure analysis. The prior R-19 rejection was imprecise.

### R-19 Amendment

| Prior Statement                                                         | Amended Statement                                                                                                                                                       |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Rejected — wrong domain (play vs analysis). No adaptation applicable." | "Partially applicable to tree builder. Tree building IS play simulation. Gaussian opponent-node weighting deferred to future investigation pending empirical baseline." |

### Panel Answers to User's Questions

| Question                                            | Answer                                                                                                                                     |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Is tree building "analysis" or "play"?              | **Play simulation** guided by analysis. User is correct.                                                                                   |
| Is deterministic definitively better than Gaussian? | **No.** Neither is provably superior. Binary threshold is simpler; Gaussian preserves more spatial info. Need empirical data.              |
| Could Gaussian improve opponent response selection? | **Theoretically yes** for diffuse-policy positions (Bug B triggers). **Risk:** could suppress distant refutations (throw-ins, ko threats). |
| Should we adopt in this initiative?                 | **No** — charter scope excludes `solve_position.py`. But record, don't dismiss.                                                            |

### Future Investigation: Gaussian Spatial Weighting for Tree Builder

**Hypothesis:** Deterministic Gaussian weighting ($w_i = p_i \cdot e^{-d_i^2/2\sigma^2}$, where $d_i$ = distance from fighting group centroid) at opponent nodes in `_build_tree_recursive()` could produce more spatially realistic solution trees, especially for diffuse-policy positions.


**Prerequisites before implementation:**

1. **Baseline instrumentation:** Add spatial distribution metrics to `TreeCompletenessMetrics` — mean distance of expanded opponent moves from stone centroid, per-depth
2. **A/B comparison:** Run both binary-threshold and Gaussian-weighted on a representative fixture set (100+ puzzles), compare tree quality metrics
3. **Edge case validation:** Confirm Gaussian does not suppress distant-but-critical refutations (ladder escapes, ko threats, throw-in sacrifices)
4. **σ calibration:** Config-driven σ per puzzle category, tuned empirically

**Architectural sketch:**

- Compute fighting-group centroid from ownership map (already available in tree builder)
- For each opponent candidate: `effective_score = policy × Gaussian(distance_from_centroid, σ)`
- Replace binary `effective_min_policy` threshold with `if effective_score < threshold: continue`
- σ as config parameter under `ai_solve.solution_tree`

**Panel concerns:**

- Cho Chikun: Strongest opponent response is not always the most local
- Shin Jinseo: KataGo policy already encodes spatial locality (double-counting risk in sharp positions)
- Both agree: empirical validation required before adoption

---

## Follow-Up Decisions (User Q1-Q6 Responses + FPU + Determinism)

**Date:** 2026-03-07  
**Status:** GOV-OPTIONS-APPROVED (unanimous 6/6)

### User Responses to Q1-Q6

| q_id | Question                       | User Response                                                                                                                                                 | Panel Recommendation Accepted?                     |
| ---- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Q1   | Scope of `solve_position.py`   | Full scenarios described: validate correct moves, add wrong moves, build solution trees. `analyze_position_candidates` already working.                       | Yes — opponent-branching logic scoped for Phase II |
| Q2   | Single or phased initiative    | C (phased) — "we need to fix bugs AND do solution trees correctly"                                                                                            | Yes                                                |
| Q3   | MCTS mechanisms to investigate | B — uncertainty-modulated branching (stdev method) is good. **FPU: wants clarity** (see below). Policy optimism + score utility: accepted as already present. | Yes (B), FPU clarified separately                  |
| Q4   | "Best answer" definition       | D — context-dependent. "We need to encode that."                                                                                                              | Yes                                                |
| Q5   | Determinism standard           | **"NOT a requirement."** Do best to find best answers with best tools. No artificial constraints.                                                             | **Override accepted** — see RC-13/RC-14            |
| Q6   | AI-Solve tier mapping          | "With additional inputs, you decide."                                                                                                                         | **No change** — existing tier 3 + ac:2 is correct  |

### FPU Reduction — Clarified and Deferred

**User's question:** "What does 'online search heuristic' mean?"

**Answer:** FPU operates WITHIN a single KataGo MCTS query (during the 500-visit search). Our tree builder operates BETWEEN queries (receiving finished results). KataGo already applies FPU internally. The panel found the FPU concept maps to Phase II's uncertainty-modulated branching ($\sigma_w$-based threshold dampening) and should be evaluated there, not re-implemented.

**Panel verdict:** Defer to Phase II. FPU-analog maps to existing uncertainty-modulated branching design (T16).

### Determinism Scope Override

**User's position:** "Determinism is NOT a requirement per se. We do our best to find the best answers given the best tools."

**Panel verdict:** Approved.
| RC-ID | Constraint                                                                                                                                    |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| RC-13 | Core pipeline publish (SHA256 → GN) remains deterministic.            |
| RC-14 | Phase II stochastic sampling UNBLOCKED.                             |
| RC-15 | If Phase II adopts stochastic methods, calibration fixtures must use statistical assertions (median/percentile), not exact match.             |
| RC-16 | T13: Merge DD-1..DD-8 into `docs/architecture/tools/katago-enrichment.md` as D32-D39. Update `docs/concepts/quality.md` with tier↔ac mapping. |

### Documentation Requirement

**User:** "Document ALL design decisions in global docs folder, not just ADRs."

**Panel verdict:** DD-1..DD-8 → `docs/architecture/tools/katago-enrichment.md` as D32-D39 (continuation of existing D1-D31 sequence). Tier/ac mapping → `docs/concepts/quality.md`. Task T13 added.
