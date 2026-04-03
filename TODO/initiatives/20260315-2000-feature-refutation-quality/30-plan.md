# Plan: Refutation Tree Quality Improvements (OPT-3 Parallel Tracks, Expanded)

> Initiative: `20260315-2000-feature-refutation-quality`
> Selected Option: OPT-3 (Parallel Tracks) — expanded with DF-2/3/4/5 reclassification
> Last Updated: 2026-03-15

---

## Phase A Status: COMPLETE (GOV-CLOSEOUT-APPROVED)

All 4 items (PI-1, PI-3, PI-4, PI-10) implemented, tested (39+ tests), governance-approved. Config v1.18.

## Execution State Snapshot (Pre-Planning)

Phase B code changes were partially applied to the working tree before proper planning. Current state:

| Item | Config Model | Algorithm Code | JSON Key | Tests | State |
|------|-------------|---------------|----------|-------|-------|
| PI-2 | Committed | Uncommitted (correct) | Missing | Missing | Needs: JSON, tests, AGENTS.md |
| PI-5 | Committed | Uncommitted (correct) | Missing | Missing | Needs: JSON, tests, AGENTS.md |
| PI-6 | Committed | Uncommitted (correct) | Missing | Missing | Needs: JSON, tests, AGENTS.md |
| PI-9 | Committed | Uncommitted (tree) + Committed (auto-detect) | Missing | Missing | Needs: JSON, tests, AGENTS.md |
| PI-7 | Not started | Not started | Not started | Not started | Phase C |
| PI-8 | Not started | Not started | Not started | Not started | Phase C |
| PI-12 | Not started | Not started | Not started | Not started | Phase C |
| PI-11 | Not started | Not started | Not started | Not started | Phase D |

---

## Phase Structure (Revised)

| Phase | Items | Focus | Dependency |
|-------|-------|-------|------------|
| **A** | PI-1, PI-3, PI-4, PI-10 | Signal quality + compute quick wins + teaching comments | None (independent) |
| **B** | PI-2, PI-5, PI-6, PI-9 | Tree depth + exploration breadth + player alternatives | After Phase A stable |
| **C** | PI-7, PI-8, PI-12 | Compute allocation + candidate discovery + best resistance | After Phase B stable |
| **D** | PI-11 | Surprise-weighted calibration infrastructure | After C (needs data from all signals) |

**Scope change note**: PI-10 (opponent policy) added to Phase A because it's low effort (~40 LOC) and the `comment_assembler.py` infrastructure is ready. PI-9 (player alternatives) in Phase B because it modifies `_build_tree_recursive()` alongside PI-2. PI-12 (best resistance) in Phase C alongside PI-7/PI-8. PI-11 (calibration) in Phase D because it needs data from all prior signals to be meaningful.

---

## Phase A: Architecture & Design

### PI-1: Ownership Delta for Refutation Scoring

**What changes**:
- Add `ownership_delta_weight: float = 0.0` to `RefutationsConfig` in `config/refutations.py`
- Add `ownership_delta_weight` to `refutations` section of `katago-enrichment.json`
- In `generate_refutations.py`, modify candidate scoring to compute `ownership_delta` from the initial analysis response
- Composite scoring: `effective_delta = wr_delta * (1 - w) + ownership_delta * w` where `w = ownership_delta_weight`
- Ownership delta = max |ownership_before[i] - ownership_after[i]| for stones in puzzle region

**Data flow**:
```
KataGo analysis → AnalysisResponse.move_infos[].ownership → compute_ownership_delta() → weighted score → candidate ranking
```

**Extension point**: `_enrich_curated_policy()` already extracts ownership data from initial analysis — same pattern.

**Risk**: Ownership data shape may vary with board size. Mitigated by normalizing to puzzle region only.

---

### PI-3: Score-Lead Delta for Refutation Identification

**What changes**:
- Add `score_delta_enabled: bool = False` and `score_delta_threshold: float = 5.0` to `RefutationsConfig`
- In `identify_candidates()`, add score delta as a complementary filter alongside `delta_threshold` (winrate)
- A candidate qualifies if EITHER winrate delta > `delta_threshold` OR score delta > `score_delta_threshold`

**Data flow**:
```
AnalysisResponse.move_infos[].score_lead → abs(root_score - move_score) → compare vs score_delta_threshold → include as candidate
```

**Foundation**: `suboptimal_branches.score_delta_threshold=2.0` already uses this pattern in isolation. PI-3 promotes it to main refutation path.

**Risk**: Score delta may over-capture in endgame positions. Mitigated by keeping score_delta_enabled=false default.

---

### PI-4: Model Routing by Puzzle Complexity

**What changes**:
- Add `model_by_category: dict[str, str] = {}` to `AiSolveConfig` in `config/ai_solve.py`
- In `SingleEngineManager` or `single_engine.py`, add model selection logic: if `model_by_category` is set and level category is known, use the mapped model
- Config example: `{entry: "test_fast", core: "quick", strong: "referee"}`
- Must flag model in YM metadata (Hana Park requirement)

**Data flow**:
```
puzzle level → get_level_category(level) → model_by_category[category] → engine selection
```

**Foundation**: `config/helpers.py` already has `get_level_category()` and `LEVEL_CATEGORY_MAP`. Models section already defines `test_fast: b10c128`.

**Risk**: b10 may produce different classifications. Mitigated by integration test requirement (Staff Eng A condition).

---

### PI-10: Opponent Policy for Teaching Comments (Phase A)

**What changes**:
- Add `use_opponent_policy: bool = False` to `TeachingConfig` in `config/teaching.py`
- In `comment_assembler.py`, when `use_opponent_policy=True`, append a condition-specific opponent-response phrase to the wrong-move comment using PV[0] from the refutation analysis
- Add `voice_constraints` to `config/teaching-comments.json` design_principles section
- Add `opponent_response_templates` to `config/teaching-comments.json` with 12 condition-keyed templates (5 active, 7 suppressed)
- Fix existing wrong-move templates that violate the voice principles (9 of 12 need cleanup)
- Add `_count_words()` guard to `assemble_wrong_comment()` (currently only enforced on correct-move path)
- Implement conditional dash rule (~5 LOC in `assemble_wrong_comment()`)
- Reshape `capturing_race_lost` wrong-move template from 9w to 3w for word budget compliance

#### Voice Principles (VP-1 through VP-5)

Established by Cho Chikun (9p) governance consultation. Sensei teaching voice — action, consequence, precision.

| # | Principle | Rule | Test |
|---|-----------|------|------|
| VP-1 | **Board speaks first** | Show opponent's action + board consequence. Never narrate the student's error. | Template must NOT contain: "your mistake", "your error", "you played", "after you" |
| VP-2 | **Action → consequence** | Structure: `{who} {action} — {result}.` Dash separates cause from effect. | Template has `—` separator with action before, consequence after |
| VP-3 | **Verb-forward, article-light** | Drop "The", "A", "This" when subject is obvious. Start with actor or action. | First word is NOT "The"/"A"/"This" unless grammatically required |
| VP-4 | **15 words maximum** | Hard cap. Parentheticals = 1 word. Coordinate tokens = 1 word. | `_count_words(template) <= 15` for combined wrong-move + opponent-response |
| VP-5 | **Warm on near-misses, neutral on errors** | Only `almost_correct` gets warmth. All others: zero sentiment, just board truth. | Only `almost_correct` uses positive adjectives |

**Forbidden words** (config-enforceable):
```json
"voice_constraints": {
  "forbidden_starts": ["The ", "This ", "A ", "Your "],
  "forbidden_phrases": ["your mistake", "your error", "after you", "you played", "unfortunately"],
  "allowed_warmth_conditions": ["almost_correct"],
  "max_words": 15
}
```

#### Composition Formula (Refined)

**Architecture**: Each wrong-move comment is composed of two parts:
1. **Wrong-move template** (condition-specific, always present) — describes the board consequence
2. **Opponent-response template** (condition-specific, optional) — names the opponent's punishing action + mechanism

**Opponent-response formula**: `{opponent_color} {!opponent_move} — {consequence_verb} {target}.`

- Active verbs: "captures", "fills", "claims" — not passive "captured", "lost", "collapsed"
- Name the target: "the stone" not vague "group" (stones > groups for student clarity)
- **Conditional dash rule**: If the wrong-move template already contains `—`, the opponent-response uses NO additional dash (one dash per comment maximum). If the wrong-move template has no dash, the opponent-response uses `—`.
- Implementation: ~5 LOC in `assemble_wrong_comment()` — check if WM output contains `—`, if so omit dash from opponent-response.

**Suppress mechanism**: 7 of 12 conditions suppress opponent-response because the wrong-move template already fully describes the opponent's action, mechanism, AND coordinate. Adding more is noise. Config-driven via `enabled_conditions` array.

#### Full 12-Condition Template Set

| # | Condition | Wrong-Move Template (VP-3 revised) | WM Words | Opponent-Response Template | OR Words | Emit? | Combined Total |
|---|-----------|-------------------------------------|----------|---------------------------|----------|-------|----------------|
| 1 | `immediate_capture` | "Captured immediately." | 2 | `{opponent_color} {!opponent_move} — captures the stone.` | 6 | ✅ | **8** |
| 2 | `opponent_escapes` | "Opponent escapes at {!xy}." | 4 | *(suppress — WM already describes action + coord)* | 0 | ❌ | **4** |
| 3 | `opponent_lives` | "Opponent makes two eyes — lives." | 6 | *(suppress — WM already describes full consequence)* | 0 | ❌ | **6** |
| 4 | `capturing_race_lost` | "Loses the race." *(reshaped from 9w)* | 3 | `{opponent_color} {!opponent_move} — fills the last liberty.` | 7 | ✅ | **10** |
| 5 | `opponent_takes_vital` | "Opponent takes vital point {!xy} first." | 6 | *(suppress — WM already describes action + coord)* | 0 | ❌ | **6** |
| 6 | `opponent_reduces_liberties` | "Opponent reduces liberties at {!xy}." | 5 | *(suppress — WM already describes action + coord)* | 0 | ❌ | **5** |
| 7 | `self_atari` | "Ends in atari." | 3 | `{opponent_color} {!opponent_move} — captures the stone.` | 6 | ✅ | **9** |
| 8 | `shape_death_alias` | "Creates {alias} — unconditionally dead." | 5 | *(suppress — shape name IS the mechanism)* | 0 | ❌ | **5** |
| 9 | `ko_involved` | "Leads to ko — direct path avoids it." | 8 | *(suppress — advisory is the value, not punishment)* | 0 | ❌ | **8** |
| 10 | `wrong_direction` | "Doesn't address the key area." | 5 | `{opponent_color} {!opponent_move} — claims the vital area.` | 7 | ✅ | **12** |
| 11 | `almost_correct` | "Good instinct — {!xy} is slightly better." | 7 | *(suppress — warmth + redirect sufficient)* | 0 | ❌ | **7** |
| 12 | `default` | "Opponent has a strong response." | 5 | `{opponent_color} {!opponent_move} — responds decisively.` | 5 | ✅ | **10** |

All 12 combinations validated ≤ 15 words (VP-4). Maximum combined: 12 words (`wrong_direction`).

#### Config Schema Extension

```json
"opponent_response_templates": {
  "enabled_conditions": ["immediate_capture", "capturing_race_lost", "self_atari", "wrong_direction", "default"],
  "templates": [
    {"condition": "immediate_capture", "template": "{opponent_color} {!opponent_move} — captures the stone."},
    {"condition": "capturing_race_lost", "template": "{opponent_color} {!opponent_move} — fills the last liberty."},
    {"condition": "self_atari", "template": "{opponent_color} {!opponent_move} — captures the stone."},
    {"condition": "wrong_direction", "template": "{opponent_color} {!opponent_move} — claims the vital area."},
    {"condition": "default", "template": "{opponent_color} {!opponent_move} — responds decisively."}
  ],
  "conditional_dash_rule": "Omit dash from opponent-response when wrong-move template already contains em-dash"
}
```

#### Wrong-Move Template Reshaping (1 template)

| Condition | Old (9w) | New (3w) | Rationale |
|-----------|---------|---------|-----------|
| `capturing_race_lost` | "Loses the capturing race — opponent has more liberties." | "Loses the race." | Frees 6w budget for opponent-response: "fills the last liberty" (mechanism) |

#### Example Compositions (All 5 Active Conditions)

| Condition | Combined Comment | Total |
|-----------|-----------------|-------|
| `immediate_capture` | "Captured immediately. White E4 — captures the stone." | 8 |
| `capturing_race_lost` | "Loses the race. White B3 — fills the last liberty." | 10 |
| `self_atari` | "Ends in atari. White D2 — captures the stone." | 9 |
| `wrong_direction` | "Doesn't address the key area. White F5 — claims the vital area." | 12 |
| `default` | "Opponent has a strong response. White C4 — responds decisively." | 10 |

#### Tracked Follow-Up (RC-2, Non-Blocking)

Lee Sedol proposed reshaping ALL opponent-action wrong-move templates from "what opponent does" to "what student failed to do" (e.g., "Fails to seal." instead of "Opponent escapes at {!df}."), which would allow opponent-response on ALL 12 conditions. Deferred to a future iteration — accepted as non-blocking follow-up.

**Data flow**:
```
Refutation analysis → ClassifiedRefutation.refutation_coord (PV[0]) → opponent_response_move
                    → ClassifiedRefutation.condition → enabled_conditions lookup
                    → if enabled: _substitute_tokens(template, opponent_move, opponent_color) → append to WM comment
```

**Foundation**: `comment_assembler.py` already has template substitution with `{!xy}` coordinate tokens via `_substitute_tokens()`. PV data is already returned by KataGo. The opponent's first response is `pv[0]` in the refutation analysis, already available as `ClassifiedRefutation.refutation_coord`.

**Template token design**: PI-10 reuses the existing `_substitute_tokens()` mechanism. New tokens:
- `{!opponent_move}` — opponent's response coordinate, same format as `{!xy}`
- `{opponent_color}` — "Black" or "White" based on side-to-move after wrong move

**Risk**: Minimal — PV[0] is always populated for analyzed moves. Default off (`use_opponent_policy=False`).

**Cross-initiative note** (Initiative `20260315-1700-feature-enrichment-lab-tactical-hints`, delivered):
Tactical hints delivered `instinct_phrase` to `assemble_correct_comment()`. PI-10 targets `assemble_wrong_comment()` — separate functions, no conflict. The executor should verify `record_puzzle()` signature in `observability.py` includes the existing `correct_move_rank` kwarg before adding new kwargs.

---

## Phase B: Architecture & Design

### PI-2: Adaptive Visit Allocation per Tree Depth (Phase B)

**What changes**:
- Config fields already exist: `SolutionTreeConfig.visit_allocation_mode` ("fixed" default), `branch_visits` (500), `continuation_visits` (125) in `config/solution_tree.py` (L138, L144, L148)
- Algorithm injected at solve_position.py L946-951 (branch nodes) and L1211-1215 (continuation nodes)
- When `visit_allocation_mode == "adaptive"`: branch decision points get `branch_visits` (compute-intensive, multiple options), forced/inner continuation nodes get `continuation_visits` (cheaper, single forced move)
- Feature gate: `visit_allocation_mode = "fixed"` means all non-forced nodes get current fixed `tree_visits=500`

**Data flow**:
```
_build_tree_recursive() → is_branch_node? → effective_visits = branch_visits (500)
                        → is_continuation? → effective_visits = continuation_visits (125)
                        → mode == "fixed"? → effective_visits = tree_visits (current behavior)
```

**Branch vs continuation classification**: A node is a "branch" if the opponent has >1 plausible response (based on policy threshold). Otherwise it's a "continuation" (single forced sequence). The classification uses existing move_info filtering already happening in the tree builder.

**Impact**: 30-50% deeper trees within same query budget for puzzles with long forced sequences. No change to total KataGo queries per puzzle — same budget, smarter allocation.

**Risk**: Classification heuristic may misidentify branches as continuations. Mitigated by minimum `continuation_visits=125` (still sufficient to verify forced sequences) and feature gate.

---

### PI-5: Board-Size-Scaled Dirichlet Noise (Phase B)

**What changes**:
- Config fields already exist: `RefutationOverridesConfig.noise_scaling` ("fixed" default), `noise_base` (0.03), `noise_reference_area` (361) in `config/refutations.py` (L42, L47, L52)
- Algorithm injected at generate_refutations.py L643-651
- When `noise_scaling == "board_scaled"`: `effective_noise = noise_base * noise_reference_area / board_area`
- Feature gate: `noise_scaling = "fixed"` means current `wide_root_noise=0.08` is used unchanged

**Data flow**:
```
generate_refutations() → if noise_scaling == "board_scaled":
    board_area = board_size * board_size (e.g., 81 for 9×9, 361 for 19×19)
    effective_noise = noise_base * noise_reference_area / board_area
    → override_settings["wide_root_noise"] = effective_noise
```

**Scaling examples** (noise_base=0.03, noise_reference_area=361):
- 9×9: `0.03 * 361 / 81 = 0.134` (more exploration on small boards)
- 13×13: `0.03 * 361 / 169 = 0.064`
- 19×19: `0.03 * 361 / 361 = 0.030` (less noise on large boards — already well-explored)

**Paper basis**: KataGo training paper Sec 2 — Dirichlet noise α inversely proportional to legal moves. α₉ₓ₉ ≈ 0.27 vs α₁₉ₓ₁₉ ≈ 0.05 during self-play.

**Risk**: Excessive noise on small boards may produce false refutation candidates. Mitigated by temperature scoring (AI-3) already filtering poor candidates + configurable `noise_base`.

---

### PI-6: Forced Minimum Visits per Refutation Candidate (Phase B)

**What changes**:
- Config fields already exist: `RefutationsConfig.forced_min_visits_formula` (False default), `forced_visits_k` (2.0) in `config/refutations.py` (L171, L177)
- Algorithm injected at generate_refutations.py L333-345
- When `forced_min_visits_formula == True`: `nforced(c) = sqrt(k * P(c) * total_visits)` where P(c) is the candidate's policy probability and total_visits is the analysis visit count
- This forces the engine to explore low-policy moves that are still viable wrong moves (sacrifices, throw-ins that have near-zero policy but are humanly tempting)

**Data flow**:
```
generate_single_refutation() → if forced_min_visits_formula:
    for candidate c in refutation_candidates:
        min_visits = sqrt(forced_visits_k * policy(c) * total_visits)
        if candidate.visits < min_visits:
            re-query with minVisits override
```

**Why this matters for tsumego**: Many vital tsumego moves (sacrificing stones, throw-ins, approach moves) have near-zero neural-net policy because the training data emphasizes strong moves, not pedagogically important wrong moves. FPU reduction (AI-1) helps at the root, but forced visit allocation ensures candidates with low initial exploration still get evaluated.

**Risk**: Extra queries per refutation candidate. Mitigated by: (a) only applied when `forced_min_visits_formula=True`, (b) only candidates that already passed initial filtering get forced visits, (c) the sqrt formula grows sub-linearly.

---

### PI-9: Player-Side Alternative Exploration (Phase B)

**What changes**:
- Add `player_alternative_rate: float = 0.0` and `player_alternative_auto_detect: bool = True` to `SolutionTreeConfig`
- In `_build_tree_recursive()`, at player-move nodes: if auto-detect is on AND the puzzle is position-only (no SGF solution) or multi-solution, explore the top N player alternatives with configurable probability
- Auto-detection logic: `run_position_only_path()` already identifies position-only puzzles. Multi-solution detection uses existing `co_correct_min_gap` — if 2+ moves pass the co-correct threshold, the puzzle is multi-solution
- When `player_alternative_auto_detect=True`: the tree builder checks puzzle type and sets effective rate automatically (e.g., 0.05 for position-only, 0.0 for single-answer curated)

**Data flow**:
```
SolvePathStage dispatch → position-only? → set player_alternative_rate=0.05 auto
                        → has solution + co-correct? → set rate=0.05 auto
                        → single-answer curated? → rate=0.0 (skip)
```

**Foundation**: `run_position_only_path()` and `run_has_solution_path()` already distinguish puzzle types. `co_correct_min_gap=0.02` detects alternative correct moves.

**Risk**: May generate larger trees for position-only puzzles. Mitigated by `max_total_tree_queries` budget cap (already at 50).

---

## Phase C: Architecture & Design

### PI-7: Branch-Local Disagreement Escalation (Phase C)

**What changes**:
- Add `branch_escalation_enabled: bool = False` and `branch_disagreement_threshold: float = 0.10` to `SolutionTreeConfig`
- In `_build_tree_recursive()`, at opponent-move nodes: after evaluating a branch, compare policy vs search outcome. If disagreement exceeds threshold, escalate visits for that specific branch
- Current escalation is puzzle-level via `refutation_escalation` in `generate_refutations.py`. PI-7 makes it branch-local — spend more on ambiguous branches, less on clear ones
- Builds on PI-2's adaptive visit allocation: escalation is applied as a multiplier on `branch_visits`

**Data flow**:
```
_build_tree_recursive() at opponent node:
    → evaluate branch at base visit count (branch_visits from PI-2)
    → compute disagreement = |policy_preferred_move - search_preferred_move|
    → if disagreement > branch_disagreement_threshold:
        → re-evaluate with escalated visits (branch_visits * escalation_factor)
        → log escalation event
```

**Injection point**: solve_position.py opponent branch loop (L1380+), after initial evaluation but before commit to tree.

**Dependency**: PI-2 (adaptive visits) must be stable — PI-7 modifies branch visit counts that PI-2 introduces.

**Risk**: Escalation could double compute for disagreement-heavy puzzles. Mitigated by: (a) per-branch escalation cap, (b) `max_total_tree_queries` budget, (c) default disabled.

---

### PI-8: Diversified Root Candidate Harvesting (Phase C)

**What changes**:
- Add `multi_pass_harvesting: bool = False` and `secondary_noise_multiplier: float = 2.0` to `RefutationsConfig`
- In `identify_candidates()`, after initial candidate scan, run a secondary scan with different noise/temperature settings to find human-tempting wrong moves missed by the first pass
- The secondary pass uses `noise * secondary_noise_multiplier` to explore further from the policy distribution
- Results from both passes are merged, deduplicated, and ranked by composite score

**Data flow**:
```
identify_candidates():
    → Pass 1: standard noise/temperature → candidate_set_1
    → if multi_pass_harvesting:
        → Pass 2: noise * secondary_noise_multiplier → candidate_set_2
        → merged = deduplicate(candidate_set_1 ∪ candidate_set_2)
        → re-rank by composite score (PI-1 ownership + PI-3 score delta)
```

**Injection point**: generate_refutations.py after L660, inside `identify_candidates()`, after the initial candidate identification loop.

**Dependency**: PI-5 (noise scaling) must be stable — PI-8 applies multiplier on top of PI-5's board-scaled noise.

**Why this matters**: Single-pass candidate discovery misses human-tempting wrong moves that have zero neural-net policy but high strategic appeal (e.g., "obvious but wrong" tesuji that beginners always try). The secondary pass with higher noise forces exploration of these moves.

**Risk**: Doubles the candidate discovery queries. Mitigated by: (a) default disabled, (b) secondary pass only adds `maxMoves=N` worth of candidates (bounded), (c) Phase C sequencing after PI-2/PI-4 reduce baseline cost.

---

### PI-12: Best-Resistance Line Generation (Phase C)

**What changes**:
- Add `best_resistance_enabled: bool = False` and `best_resistance_max_candidates: int = 3` to `RefutationsConfig`
- In `generate_single_refutation()`, after getting the initial refutation PV, evaluate up to N alternative opponent responses and select the one that maximizes punishment (highest score delta or ownership flip)
- For position-only puzzles (where this is how solutions are discovered), best-resistance search is essential — the "correct" move is the one where even the best opponent resistance fails

**Data flow**:
```
Wrong move played → query position after wrong move → get top N opponent responses → 
evaluate each → pick the one with highest punishment signal → use as refutation PV
```

**Injection point**: generate_refutations.py after L357 in `generate_single_refutation()`, after initial PV retrieval.

**Dependency**: PI-6 (forced visits) should be stable — best-resistance ranking benefits from forced minimum visits ensuring all candidate responses are adequately explored.

**Foundation**: `generate_single_refutation()` already queries the position after a wrong move. Currently takes `pv[0]` (first response). Extension: evaluate `pv[0..N]` and rank by punishment quality.

**Risk**: Compute cost: up to `best_resistance_max_candidates` extra queries per refutation. Mitigated by config cap and Phase C sequencing after PI-2/PI-4 reduce baseline cost.

---

### PI-11: Surprise-Weighted Calibration (Phase D)

**What changes**:
- Add `surprise_weighting: bool = False` and `surprise_weight_scale: float = 2.0` to `CalibrationConfig`
- In the calibration pipeline, weight positions by "surprise" — how much the engine disagrees with itself across visits tiers, or how rare the tactical motif is
- Positions where the engine was wrong or uncertain get higher weight in threshold tuning

**Data flow**:
```
Calibration batch → per-puzzle surprise score = |T0_winrate - T2_winrate| → 
weight = 1 + surprise_weight_scale * surprise_score → 
scaled contribution to threshold optimization
```

**Foundation**: `.lab-runtime/calibration-results/` directory exists with calibration data. `CalibrationConfig` exists in `config/infrastructure.py`. Visit tiers T0/T1/T2 already produce different signals.

**Risk**: Requires sufficient calibration data from diverse sources. Phase D sequencing ensures all signals (ownership, score, alternatives) contribute to calibration.

---

## Risks and Mitigations (All Phases)

| risk_id | Phase | Risk | Likelihood | Impact | Mitigation |
|---------|-------|------|-----------|--------|------------|
| R-1 | A | Ownership delta weight needs calibration | Medium | Medium | Default to 0.0 (disabled). Calibrate against gold-standard puzzles in Phase B. |
| R-2 | A | Score delta over-captures in endgame | Low | Low | Default disabled. Score_delta_threshold configurable. |
| R-3 | A | b10 ≠ b18 for edge-case puzzles | Medium | Medium | Integration test proving identical is_correct for entry-level. Metadata flagging. |
| R-4 | All | Config schema drift | Low | Low | Pydantic validation. Version bump at each phase boundary. |
| R-5 | B | Player alternatives create oversized trees | Medium | Medium | `max_total_tree_queries` budget cap. Auto-detect limits to position-only/multi-solution. |
| R-6 | C | Best-resistance increases compute per refutation | Medium | Low | Phase C after compute savings from PI-2/PI-4. Config cap `best_resistance_max_candidates`. |
| R-7 | D | Calibration data insufficiency | Low | Medium | Phase D sequencing ensures all signals available. Seed discipline required. |
| R-8 | B | Adaptive visits misclassifies branches as continuations | Medium | Medium | Minimum `continuation_visits=125` ensures forced moves still verified. Feature gate disables. |
| R-9 | B | Excessive noise on small boards (PI-5) | Low | Low | Temperature scoring (AI-3) already filters poor candidates. Configurable `noise_base`. |
| R-10 | B | Phase B touches tree builder — regression risk | Medium | High | Feature gates default off. Regression suite (`pytest -m "not (cli or slow)"`) after each PI-2/PI-9 change. |
| R-11 | C | Multi-pass harvesting doubles candidate queries | Low | Low | Default disabled. Bounded by `maxMoves` per pass. |
| R-12 | C | Disagreement escalation + best-resistance compound compute | Medium | Medium | `max_total_tree_queries` cap. Phase C sequenced after PI-2/PI-4 reduce baseline. |

---

## Must-Hold Constraints (Phase B/C/D)

Constraints from Gate 4 (MH-1 through MH-5) carry forward. New constraints from Gate 9 charter review:

| mh_id | Phase | Constraint | Source | Verification |
|-------|-------|-----------|--------|-------------|
| MH-1 | All | `ownership_delta_weight` defaults to 0.0 | Gate 2 (Cho Chikun) | ✅ Verified in Phase A |
| MH-2 | A | PI-4 needs integration test (b10=b18 for entry) | Gate 2 (Staff Eng A) | ✅ Verified in Phase A (TS-3) |
| MH-3 | All | Absent key = current behavior (v1.14 pattern) | Gate 2 (Staff Eng A) | ✅ Verified in Phase A (TS-4) |
| MH-4 | B | PI-9 must-hold safeguard: zero alternatives explored when `player_alternative_rate=0.0` | Gate 4 (Hana Park) | TS-7 in T11a |
| MH-5 | All | AGENTS.md updated in same commit as structural changes | Gate 2 | T7 (done), T16c, T16f, T16i |
| MH-6 | B | Regression test (`pytest -m "not (cli or slow)"`) MUST pass after EACH PI-2/PI-9 commit touching `_build_tree_recursive()` | Gate 9 (Staff Eng A, RC-1) | T16b |
| MH-7 | C | Per-puzzle compute tracking (total queries dispatched) MUST be added to `BatchSummaryAccumulator` BEFORE PI-7+PI-12 are enabled simultaneously | Gate 9 (Staff Eng B, RC-2) | T16f scope |
| MH-8 | C | PI-8 multi-pass harvesting candidates MUST pass composite score re-ranking (ownership delta + score delta) before entering tree | Gate 9 (Hana Park, RC-3) | TS-12 in T13c |

---

## Documentation Plan

| doc_id | Phase | Action | File | Why |
|--------|-------|--------|------|-----|
| D-1 | A | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | PI-1/PI-3/PI-4/PI-10 methods and config keys | ✅ Done |
| D-2 | A | Update | `config/katago-enrichment.json` changelog | Version bump v1.17→v1.18 with Phase A keys | ✅ Done |
| D-3 | — | No change | `docs/` | Internal tool changes, no user-facing docs impact |
| D-4 | B | Update | `config/katago-enrichment.json` | Version bump v1.18→v1.19: add PI-2/PI-5/PI-6/PI-9 keys |
| D-5 | B | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | PI-2/PI-5/PI-6/PI-9 injection points and config models |
| D-6 | B | Create | `tests/test_refutation_quality_phase_b.py` | Phase B unit+integration tests (TS-7/TS-8/TS-9) |
| D-7 | C | Update | `config/katago-enrichment.json` | Version bump v1.19→v1.20: add PI-7/PI-8/PI-12 keys |
| D-8 | C | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | PI-7/PI-8/PI-12 methods and config keys |
| D-9 | C | Create | `tests/test_refutation_quality_phase_c.py` | Phase C unit tests (TS-10/TS-11/TS-12) |
| D-10 | D | Update | `config/katago-enrichment.json` | Version bump v1.20→v1.21: add PI-11 keys |
| D-11 | D | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | PI-11 calibration config and method |
| D-12 | D | Create | `tests/test_calibration.py` | Phase D calibration tests (TS-13) |

### Config Version Track

| Phase | Config Version | New Keys |
|-------|---------------|----------|
| A | v1.18 (✅ done) | `ownership_delta_weight`, `score_delta_enabled`, `score_delta_threshold`, `model_by_category`, `use_opponent_policy` |
| B | v1.19 | `visit_allocation_mode`, `branch_visits`, `continuation_visits`, `noise_scaling`, `noise_base`, `noise_reference_area`, `forced_min_visits_formula`, `forced_visits_k`, `player_alternative_rate`, `player_alternative_auto_detect` |
| C | v1.20 | `branch_escalation_enabled`, `branch_disagreement_threshold`, `multi_pass_harvesting`, `secondary_noise_multiplier`, `best_resistance_enabled`, `best_resistance_max_candidates` |
| D | v1.21 | `surprise_weighting`, `surprise_weight_scale` |

---

## Test Strategy

| test_id | Scope | File | What |
|---------|-------|------|------|
| TS-1 | PI-1 unit | `tests/test_generate_refutations.py` | Ownership delta scoring with weight=0, weight=0.5, weight=1.0 |
| TS-2 | PI-3 unit | `tests/test_generate_refutations.py` | Score delta filter: enabled/disabled, threshold edge cases |
| TS-3 | PI-4 integration | `tests/test_ai_solve_config.py` | Model routing by category: entry→test_fast, core→quick, empty→default |
| TS-4 | Config | `tests/test_ai_solve_config.py` | New config keys parse, default values, absent-key behavior |
| TS-5 | PI-10 unit | `tests/test_comment_assembler.py` | Opponent-response: (a) 5 active conditions produce opponent-response, 7 suppressed do not. (b) Conditional dash rule: WM with `—` → no dash in OR; WM without → dash in OR. (c) Combined word count ≤ 15 for all 12 pairings. (d) VP-3 compliance: no template starts with "The"/"This"/"A"/"Your". (e) VP-5: only `almost_correct` uses positive adjectives. (f) Token substitution: `{opponent_color}`, `{!opponent_move}` resolved. (g) `_count_words()` guard on wrong-move path. (h) Feature gate: `use_opponent_policy=False` → no opponent-response appended. |
| TS-6 | Regression | Full test suite | `pytest -m "not (cli or slow)"` passes |
| TS-7 | PI-9 integration | `tests/test_solve_position.py` | Auto-detect: position-only→rate>0, curated single-answer→rate=0.0, zero alternatives explored (must-hold #4 safeguard) |
| TS-8 | PI-5 unit | `tests/test_generate_refutations.py` | Board-size-scaled noise: 9x9 vs 19x19 vs default |
| TS-9 | PI-6 unit | `tests/test_generate_refutations.py` | Forced visits formula: enabled/disabled, k parameter |
| TS-10 | PI-12 unit | `tests/test_generate_refutations.py` | Best resistance: single vs multi-candidate, compute cap enforcement |
| TS-11 | PI-7 unit | `tests/test_solve_position.py` | Branch-local escalation: disagree→escalate, agree→skip |
| TS-12 | PI-8 unit | `tests/test_generate_refutations.py` | Multi-pass harvesting: second pass finds candidates missed by first |
| TS-13 | PI-11 unit | `tests/test_calibration.py` (new) | Surprise weighting: uniform vs surprise-weighted threshold outputs |

> **See also**:
> - [Charter: 00-charter.md](00-charter.md) — Scope and classification tables
> - [Options: 25-options.md](25-options.md) — OPT-3 selection rationale
> - [Tasks: 40-tasks.md](40-tasks.md) — Dependency-ordered task breakdown
