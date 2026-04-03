# Learnings & Expert Review: Browser Engine (Option B)

**Created:** 2026-02-26  
**Last Updated:** 2026-02-27  
**Status:** Review complete  
**Purpose:** Document learnings from external sources, expert reviews, and plan updates

---

## Part 1: Learnings from External Sources

### Source A: Dingdong-LIU/katrain-modified

**What it is:** A fork of sanderland/KaTrain (the premier Go analysis GUI) modified for a human-computer interaction (HCI) user study. Adds a "DeepGo" external prediction server and cost-of-intervention analysis.

**Key Learnings:**

| # | Learning | Relevance to Yen-Go | Impact on Plan 004 |
|---|---------|--------------------|--------------------|
| 1 | **Policy-only AI is a legitimate tier.** KaTrain's `AI_POLICY` mode uses the raw policy network output (no MCTS) to generate moves. This is orders of magnitude faster than full MCTS and already plays at ~SDK level for straightforward positions. | For tsumego, the correct first move's *policy prior* alone is a powerful difficulty signal. A single forward pass (~50ms WASM) can answer "how obvious is this move?" without any MCTS at all. | **Phase 3 can deliver value immediately.** We can have a "Tier 0.5" mode: load model → extract features → single NN forward pass → read policy prior for correct move → instant difficulty estimate. No MCTS needed for this sub-task. |
| 2 | **Calibrated Rank Bot formula maps policy priors to kyu/dan ranks.** KaTrain's `AI_RANK` uses a calibrated formula (`orig_calib_avemodrank = 0.063015 + 0.7624 * board_squares / (10^(-0.05737 * kyu_rank + 1.9482))`) to translate policy behavior into ranked play. | We can adapt this calibration to map policy_prior of the *correct first move* directly to Yen-Go's 9-level difficulty system. | **Validates our difficulty rating approach** from Section 5.3 of the research doc. The policy prior → difficulty mapping is not novel — KaTrain already proved it works at scale. |
| 3 | **`cognitive_depth = top_node_visits / average_visits`** — a simple ratio metric from Dingdong's modifications quantifies how much "thought" the engine devoted to the top move vs. alternatives. | Direct application to tsumego difficulty: puzzles where the correct move requires unusually many visits relative to average are "harder to read." | **New difficulty metric** we should compute during MCTS and store alongside YX complexity metrics. |
| 4 | **External prediction server pattern** (Flask-based `DeepGo`). KaTrain sends game state to an HTTP endpoint, receives predicted human moves back. The server runs a separate pre-trained model. | We already have this pattern with our `bridge.py` → KataGo local engine. But the idea of a *separate human-move prediction model* is interesting for generating teaching comments ("a common mistake here is..."). | **Future Phase B consideration.** Not for Phase A, but the architecture of "separate model predicting human moves" could power template-based teaching comments. |
| 5 | **Tsumego Frame** (`tsumego_frame.py`) — KaTrain already has code that fills the *outside* of a tsumego position with offense/defense stones so KataGo analyzes the local position correctly. This is exactly our "full board input, local output" technique from Section 4.1. | Validates our approach. KaTrain's tsumego frame even handles corner/edge detection, flip normalization, and ko threat placement — problems we will need to solve. | **We should study and potentially adapt this algorithm** for our browser engine. The tsumego frame logic (176 LOC Python) handles: (a) detecting puzzle region, (b) filling rest of board correctly, (c) adding ko threats, (d) normalizing orientation. |
| 6 | **`game_report()` function computes complexity as `sum(max(d["pointsLost"], 0) * d["prior"]) / sum(d["prior"])`** — a weighted average of point loss by policy prior across candidate moves. | This is a principled complexity score: positions where multiple "tempting" wrong moves exist (high policy prior but high pointsLost) are more complex. | **Adopt this complexity formula** for enriching our `YX` complexity metrics. Currently our complexity has `d/r/s/u` components — add a "trap density" component `t` based on this formula. |
| 7 | **Ownership-based scoring with threshold bands.** KaTrain's `manual_score` function uses ownership values with `lo_threshold = 0.15` and `hi_threshold = 0.85` to classify intersections as territory, captures, dame, or unknown. | We will need similar thresholding when interpreting ownership output for tsumego validation (is the target group alive or dead?). | **Use the 0.15/0.85 ownership threshold bands** from KaTrain as starting values for our "is group alive" detection in Phase 4 MCTS. |

### Source B: blacktoplay.com/js/estimator.js

**What it is:** A pure JavaScript territory estimator (~700 LOC) written by Robin Nilsson for blacktoplay.com. No neural network, no WASM — pure algorithmic estimation using heuristic rules.

**Key Learnings:**

| # | Learning | Relevance to Yen-Go | Impact on Plan 004 |
|---|---------|--------------------|--------------------|
| 8 | **Tier 0: Pure JS scoring is viable.** The BTP estimator works entirely without any ML model. It uses: (a) liberty counting → capture detection, (b) influence propagation from stones to adjacent empty points, (c) closed-group detection (groups with <7 stones fully surrounded), (d) territory filling (flood fill areas surrounded by one color), (e) edge/corner heuristics for 1st and 2nd line. | This is a **third tier** we hadn't considered. Between "no scoring" and "NN-based scoring (Tier 1 WASM, Tier 2 TF.js)" there is "heuristic JS scoring" — 0 KB model, instant, ~80% accurate for simple positions. | **Add as "Tier 0" fallback for the browser engine.** Useful for: (a) quick ownership estimation during user puzzle solving, (b) fallback when TF.js fails to load, (c) validating simple life-and-death without NN. |
| 9 | **`is_group_closed()` algorithm.** BTP implements a "is this group enclosed and dead?" check: flood fill from a stone, track boundaries, count own stones (<7 for single group, <4 for multiple groups). If the group is small and fully enclosed by opponent stones/territory, it's captured. | Directly applicable to tsumego validation. For "kill" puzzles: after correct sequence, check if target group is closed. For "live" puzzles: verify the target group is NOT closed. | **Port `is_group_closed()` logic** into our Phase 2 board logic (fast-board.js). This gives us a non-NN way to validate simple life/death results, and can serve as an initial/fast check before running the full NN. |
| 10 | **`toggle_group_status()` as interactive dead-stone marking.** BTP lets users click groups to mark them as dead/alive, then recalculates territory. The UI pattern of "click to toggle, recalculate" is exactly what OGS's score estimator does. | While not directly for our enrichment lab, this pattern is useful for: (a) the main frontend's score estimation feature (Feature 134), (b) a potential "manual verification" mode in the enrichment lab. | **Reference for Feature 134** (separate from Plan 004). The toggle pattern with territory recalculation is well-implemented here. |
| 11 | **Viewport support.** BTP estimator takes an optional `viewport` parameter to limit analysis to a sub-section of the board. `estimate(position, viewport=9)` would analyze only the top-left 9x9 region. | For tsumego, we want to focus on the puzzle region. The viewport concept maps to our "puzzle bounding box" analysis. | **Adopt viewport concept** for our heuristic scoring fallback — analyze only the puzzle region, not the full 19x19 board. |
| 12 | **Influence propagation via numbered cells.** BTP assigns numeric territory values (-4 to 4) radiating from stones/captures. Empty points adjacent to b/w stones get values like ±1, those one step further ±2, etc. This creates a "territory heatmap" without any neural network. | Simple but effective for visualizing territory claims. Could be used as a lightweight visual overlay during puzzle solving. | **Consider as visual hint** for the enrichment lab — show "territory influence" overlay on the board without needing KataGo ownership head. |

### Source C: MachineKomi/Infinite_AI_Tsumego_Miner

**What it is:** An autonomous "mining rig" that generates tsumego puzzles from AI self-play games. Uses 11+ KataGo neural networks as adversarial "personalities," detects puzzles via winrate drops (blunders), and grades difficulty.

**Key Learnings:**

| # | Learning | Relevance to Yen-Go | Impact on Plan 004 |
|---|---------|--------------------|--------------------|
| 13 | **"The Delta" — puzzle detection via winrate drop.** A position becomes a puzzle when one player's winrate drops sharply (99% → 10%) as judged by a *separate* referee engine. The threshold of ~75% winrate delta is the blunder threshold. | We can use this *in reverse*: for existing puzzles, verify that playing the wrong move causes a sufficient Delta. If the Delta is <75%, the "wrong" move isn't really wrong (puzzle quality issue). | **Add Delta validation** to our Task 2 (refutation generation). A refutation is only valid if it produces a Delta > threshold. |
| 14 | **Randomized Temperature (0.8-1.5) + Visits (20-300)** produces diverse puzzle styles. Higher temperature = more creative/unusual mistakes. Lower visits = more "human-like" blunders. | While we don't generate puzzles, the Temperature/Visits variation concept applies to our difficulty calibration: analyze the same puzzle at different visit counts to measure how visit-sensitive the correct answer is. | **Novel calibration technique:** analyze each puzzle at visits=[50, 100, 200, 400]. If correct move appears at 50 visits → easy. If only at 400 → hard. This gives us a "reading depth" metric independent of policy prior. |
| 15 | **Dual-engine validation** (Generator engine vs. Referee engine). The generator is weaker/randomized, the referee is stronger/deterministic. This ensures puzzle quality. | We have a natural dual-engine setup: browser engine (b6c96, weaker) vs. local engine (b28c512, strongest). Use local as referee to validate browser analysis. | **Already in our architecture.** The enrichment lab already supports local engine; browser engine will be the "generator" tier. Validation by cross-referencing both. |
| 16 | **Rich source of patterns.** Infinite_AI_Tsumego_Miner implements Delta detection (winrate drop threshold), dual-engine referee validation, randomized temperature/visits for diverse puzzle styles, and kyu/dan difficulty grading. All valuable patterns to study and reimplement. | We can study their Delta detection, dual-engine pattern, temperature/visits variation, and difficulty grading approach. We rewrite all code ourselves. | **Study, rewrite, adapt.** The concepts (Delta threshold, referee pattern, personality randomization) are valuable patterns to learn from and reimplement. |

---

## Part 2: Principal Systems Architect Review

> **Reviewer persona:** Principal/Staff Systems Architect with 15+ years experience in system design, performance engineering, and browser-based applications.

### Architecture Assessment

**2.1 The Tier Hierarchy is Correct but Incomplete**

The original Plan 004 identified two tiers (Tier 1: Monte Carlo WASM, Tier 2: NN + MCTS). The research has revealed a more complete picture:

| Tier | Technique | Model Size | Latency | Accuracy for Tsumego | Implementation Effort |
|------|-----------|-----------|---------|---------------------|----------------------|
| **Tier 0** | Heuristic JS (BTP-style) | 0 KB | <1ms | ~60% (simple positions) | 1 day |
| **Tier 0.5** | Policy-only NN (no MCTS) | 3-4 MB | 50-100ms | ~75% (obvious moves) | 2 days |
| **Tier 1** | Monte Carlo WASM (OGS) | 29 KB | ~200ms | ~70% (ownership only) | 0.5 days |
| **Tier 2** | NN + MCTS (full analysis) | 3-11 MB | 1-10s | ~95% | 3-5 days |

**Recommendation:** Implement Tier 0.5 *first* as a quick win. A policy-only forward pass is:
- Simpler than MCTS (skip Phase 4 entirely for this tier)
- Still valuable (difficulty estimation, quick validation)
- A natural checkpoint before committing to the full MCTS implementation

**2.2 Tsumego Frame is a Critical Dependency**

KaTrain's `tsumego_frame.py` solves a problem we *must* solve: preparing the full 19×19 board from an isolated puzzle position. This is not optional ornamentation — **KataGo will produce garbage output if the rest of the board is empty**, because:
- Empty board defaults to ~7.5 komi → one side is "winning by komi"
- Policy distribution spreads across the entire empty board
- Ownership head shows everything as "dame"

The tsumego frame algorithm:
1. Detects puzzle region (corner/edge/center)
2. Fills the *outside* with offense/defense stones balanced to achieve ~0 score
3. Adds ko threats if needed
4. Normalizes orientation (flip/rotate to standard position)

**This must be Phase 0.5, not deferred.** Without it, Phases 1-4 produce incorrect results.

**2.3 Memory and Latency Budget**

For the enrichment lab (developer tool, not user-facing), the memory/latency budget is generous:
- b6c96 model: 3.7 MB (acceptable for a lab tool)
- TF.js WASM backend: ~50-100ms per forward pass
- MCTS with 100 visits: ~5-10s (acceptable for batch analysis)

However, if we ever want to run this in the *main frontend* (not currently planned), we'd need:
- Lazy loading (no model download until user requests analysis)
- Web Worker (non-blocking main thread)
- Progressive result display (show policy immediately, MCTS results as they arrive)

**For the enrichment lab, the current architecture is sound.**

**2.4 OGS WASM vs BTP Heuristic Estimator Comparison**

Research confirms these are at very different levels:

| Dimension | **OGS WASM** (29 KB, Monte Carlo) | **BTP Heuristic** (0 KB, pure JS) |
|-----------|----------------------------------|-----------------------------------|
| Territory accuracy | ~70% | ~60% |
| Dead stone detection | Statistical (playout survival) | Structural (`is_group_closed`, <7 stones enclosed) |
| Latency | <500ms | <1ms |
| Life/death judgment | Moderate (random playouts) | Good for simple cases, fails on complex shapes |
| Edge handling | Implicit | Explicit 1st/2nd line heuristics |

**For the enrichment lab:** Neither replaces KataGo. But BTP's `is_group_closed()` is a useful instant pre-filter (zero-cost structural check before expensive NN analysis).

**For Feature 134 (main frontend):** OGS WASM is the right choice — already in our dependencies, proven API, better accuracy.

**Key takeaway:** OGS WASM and BTP are complementary — OGS for territory scoring (statistical), BTP for quick capture/life-death structural checks (deterministic). Both are far below KataGo tier.

**2.5 BTP Estimator: Valuable but Scope-Sensitive**

The BTP heuristic estimator is ~700 LOC of pure JS. Its value for our plan:

| Use Case | Value | Effort |
|----------|-------|--------|
| Enrichment lab fallback | Low — we have KataGo local engine | 0 |
| Main frontend Tier 0 scoring | Medium — before Feature 134 WASM | 1 day |
| Browser engine fallback | Medium — when TF.js fails | 0.5 day |

**Recommendation:** Port `isGroupClosed()` to Phase 2 board logic. Defer the rest of BTP to Feature 134. If we ever need a non-NN fallback in the enrichment lab, it's a 0.5-day effort to adapt the full estimator.

**2.5 Complexity Formula Adoption**

KaTrain's complexity formula (`sum(pointsLost * prior) / sum(prior)`) is well-designed:
- Weighted by policy prior → "tempting" wrong moves contribute more
- Bounded by point loss → actual consequences matter
- Cheap to compute → already available from KataGo analysis output

**Recommendation:** Adopt this formula when we have MCTS results. Map it to:
- `YX.t` (new "trap density" component, or augment existing `r` refutation count)

**2.6 Cognitive Depth Metric**

Dingdong's `cognitive_depth = top_node_visits / average_visits` metric is clever but noisy for tsumego because:
- Tsumego positions often have only 1-3 "reasonable" moves (small denominator)
- The ratio is sensitive to visit allocation policy

**Better alternative for tsumego:** `visits_at_first_consensus` — the visit count at which the top move first stabilized. This directly measures "how much reading is needed to be sure."

### Risks & Mitigations (Architect Perspective)

| Risk | Severity | Mitigation |
|------|---------|------------|
| Tsumego frame missing → garbage NN output | **Critical** | Port `tsumego_frame.py` to JS as Phase 0.5 (before any NN work) |
| TF.js model format incompatibility | Medium | Verify b6c96.bin.gz can be loaded by our custom parser; test with dummy inference |
| MCTS correctness (subtle bugs in UCB/PUCT) | Medium | Side-by-side comparison with local KataGo on 20 reference puzzles |
| Scope creep (adding all tiers) | Medium | Strict Phase A scope: Tier 0.5 (policy only) + Tier 2 (MCTS). Skip Tier 0 heuristic for now |

---

## Part 3: Cho Chikun 1P Professional Go Review

> **Reviewer persona:** Cho Chikun (趙治勲), 1P Professional Go player. 75 title wins. Author of "Cho Chikun's Encyclopedia of Life and Death." Expert in tsumego composition and difficulty grading.

### Go Domain Assessment

**3.1 Policy Prior as Difficulty — Mostly Valid, with Caveats**

A professional would confirm: the policy network's "first instinct" does correlate with difficulty for most tsumego. When I (Cho Chikun) look at a problem, my first instinct is:
- **Strong first instinct (policy > 0.5):** Simple problem. I see the vital point immediately. This maps to novice/beginner.
- **Moderate instinct (0.1-0.5):** Requires some reading. The shape doesn't immediately suggest the answer. Elementary/intermediate.
- **Weak instinct (< 0.05):** The correct move is surprising. It requires deep reading or knowledge of a specific technique (throw-in, under-the-stones, etc.). Dan-level.

**However**, there are important exceptions:
1. **Tesuji that look normal.** Some problems have a correct move at a natural-looking point (high policy prior) but the *reason* it works requires deep reading. The policy says "play here" but doesn't know *why* it works. These would be rated "easy" by policy prior but are actually hard to understand.
2. **Miai positions.** When two moves are equally correct (YO=miai), the policy splits between them. Each gets a lower prior (~0.25 each) even though the problem is easy. Miai puzzles should not be marked as harder just because the prior is split.
3. **Approach-move problems.** Problems where the first move is NOT in the vital area (e.g., play elsewhere to make the sequence work) are extremely hard for humans but the NN might assign high policy because it "sees" the long-range connection. These don't follow the policy → difficulty mapping.

**Recommendation from Go domain perspective:**
- Flag puzzles with `YO=miai` and apply a 2x policy prior correction (combine both miai moves' priors)
- Flag approach-move puzzles (where correct first move is >5 intersections from the puzzle center) for manual review
- Don't use policy prior alone — always combine with `visits_to_solve` for the final difficulty rating

**3.2 Refutation Quality — The "Move Order" Problem**

When generating refutations (wrong-move analysis), a professional notes:
- **Correct refutation order matters.** In tsumego, the *opponent's* response to a wrong move must be the *strongest* refutation. KataGo's top response is usually strongest, but occasionally:
  - KataGo plays a "slightly better" refutation that is harder for humans to understand
  - The "obvious" refutation (the one a human teacher would show) is KataGo's 2nd or 3rd choice
  
- **Refutation depth matters.** A wrong move is "obviously wrong" if the refutation is 1 move (immediate capture/death). It's "subtly wrong" if the refutation requires 4-6 moves. Short refutations are better for teaching beginners; long refutations prove the depth of the problem.

**Recommendation:** For each refutation, record:
- `refutation_depth` (number of moves until the group is confirmed dead/alive)
- `refutation_type` (immediate_capture, shortage_of_liberties, eye_destruction, ko, etc.)
- Prefer shorter refutations for lower-level puzzles

**3.3 Tsumego Frame — Corner Placement is Critical**

The tsumego frame algorithm from KaTrain is correct in principle, but a professional has specific concerns:

1. **Opening/fuseki-like positions mislead KataGo.** If the frame creates a position that looks like a real game opening, KataGo may allocate policy to "game-like" moves outside the puzzle region. The frame should use an *unnatural* stone arrangement that clearly signals "this is not a real game."

2. **Corner positions (TL/TR/BL/BR) are easiest** for KataGo because the corner walls provide natural boundaries. **Edge positions (E)** are harder because the frame must extend further. **Center positions (C)** are hardest because the frame must surround the entire puzzle.

3. **Ko threat placement is critical.** KaTrain's dual ko-threat pattern (offence + defence) is correct. Without ko threats, KataGo misevaluates all ko-related puzzles, which are ~15-20% of typical tsumego collections.

**3.4 Ownership for Life and Death — Very Reliable**

KataGo's ownership head is *extremely reliable* for life-and-death judgment:
- Alive group: ownership > 0.8 for the group's stones
- Dead group: ownership < -0.8 (opposite sign)
- Seki: ownership ≈ 0.0 for both groups
- Unsettled: ownership between 0.3-0.7 (needs more reading/visits)

KaTrain's thresholds of 0.15/0.85 for Japanese scoring are conservative. For tsumego validation:
- Use 0.7 as the "alive" threshold (we care about clear life/death, not territory scoring)
- Positions where ownership is between 0.3-0.7 should be flagged for manual review or more visits

**3.5 Technique Detection — What KataGo Actually Reveals**

A professional can identify techniques from KataGo's output:

| Technique | KataGo Signal | Detection Method |
|-----------|--------------|------------------|
| **Snapback** | PV shows: capture → recapture → net gain of ≥2 stones | Parse PV for capture, same-location recapture pattern |
| **Ladder** | PV shows alternating atari-escape pattern, >6 moves | Detect alternating adjacent plays, linear progression |
| **Net (geta)** | PV is short (1-2 moves), capturing stone not adjacent to target | Policy spreads to 2-3 diagonal/knight's-move points |
| **Ko** | PV alternates captures at same point | Direct detection from move history in PV |
| **Throw-in** | First move is a sacrifice (placed where it can be immediately captured) | Correct move has 0 or 1 liberty after placement |
| **Under-the-stones** | PV sequence: sacrifice multiple stones → recapture larger group | PV shows multiple stones captured then space filled |
| **Seki** | After a sequence, ownership shows ≈0 for both groups | Both groups alive but with shared liberties |
| **Capturing race (semeai)** | PV shows both players filling liberties | Liberty count decreases for multiple groups simultaneously |

**This is feasible** for Phase B template engine. The detection methods are all computable from KataGo's PV (principal variation) and ownership outputs.

### Go Domain Risks

| Risk | Severity | Professional Assessment |
|------|---------|----------------------|
| Model too weak (b6c96) for dan-level puzzles | **Medium** | b6c96 reads ~10-15 moves deep. Most tsumego up to 5d are solvable. For 6d+ problems (>15-move solutions), use b10c128 or local engine |
| Ko evaluation incorrect without proper setup | **High** | KataGo needs proper ko threats on the board. Without them: direct ko → overvalued, approach ko → incorrectly evaluated. Tsumego frame with ko threat placement is mandatory |
| Seki false positives | **Low** | KataGo's ownership head handles seki well. The 0.0 ownership signal is distinctive |
| Approach-move puzzles misgraded | **Medium** | ~5-10% of puzzles. Flag any puzzle where the correct first move is >5 intersections from the group under attack for manual difficulty review |

---

## Part 4: Consolidated Recommendations for Plan 004

Based on all three reviews, the following updates are recommended:

### 4.1 Add Phase 0.5: Tsumego Frame (NEW — Critical Path)

Before any NN work, port KaTrain's `tsumego_frame.py` to JavaScript. Without this, all NN analysis produces garbage. ~176 LOC Python → ~200 LOC JS.

### 4.2 Reorder Phases for Incremental Value

| Phase | Original | Updated | Rationale |
|-------|----------|---------|-----------|
| Cleanup | Same | Same | |
| Phase 0 | TF.js setup | Same | |
| **Phase 0.5** | — | **Tsumego Frame (JS port)** | Critical dependency for correct NN output |
| Phase 1 | Model loader | Same | |
| Phase 2 | Board logic | Same, **add `is_group_closed()`** from BTP estimator | Heuristic life/death check |
| Phase 3 | Features | Same, **add "policy-only" mode** | Tier 0.5: instant difficulty estimate |
| Phase 4 | MCTS | Same, **add KaTrain complexity formula** | Adopt `sum(pointsLost * prior) / sum(prior)` |
| Phase 5 | Integration | Same, **add dual-engine comparison view** | Show browser vs local results side-by-side |

### 4.3 New Difficulty Calibration Approach

Combine three signals (validated by all three reviews):

```
difficulty_score = w1 * (1 - policy_prior_of_correct_move)   # "how surprising"
                 + w2 * log(visits_to_solve / 50)             # "how deep to read"
                 + w3 * trap_density                           # "how tempting are wrong moves"
```

Where:
- `policy_prior_of_correct_move` from single NN forward pass (Tier 0.5)
- `visits_to_solve` from MCTS (Tier 2) — visit count when top move stabilizes
- `trap_density` = `sum(pointsLost * prior) / sum(prior)` from KaTrain formula

### 4.4 Miai Puzzle Handling

When `YO=miai` or `YO=flexible`, sum the policy priors of ALL correct first moves before computing difficulty. This prevents miai puzzles from being graded harder than they are.

### 4.5 Browser vs Local Architecture Clarification

The browser engine and local engine are **independent, parallel systems** — not counterbalances to each other:

- **Browser engine** = lightweight, interactive, quick-check tool for developers in the lab UI
- **Local engine** = production workhorse for batch enrichment of 194K+ puzzles
- **Dual-engine referee** = two *local* KataGo instances (Quick + Referee model), not browser vs local

The browser engine will never be the "counterbalance" to local analysis. It's a convenience tool for interactive exploration.

### 4.6 BTP Estimator — Port `isGroupClosed()`, Defer Rest

Port BTP's `isGroupClosed()` to Phase 2 board logic. Defer full BTP estimator to Feature 134.

### 4.7 Cross-Reference: Puzzle Quality Scorer

The Puzzle Quality Scorer (`core/tactical_analyzer.py`) provides **symbolic** tactical analysis (ladder, snapback, eye counting) that complements KataGo enrichment. They run in sequence:
1. Quality Scorer first (6ms/puzzle, structural patterns, in-pipeline)
2. KataGo Enrichment second (200ms/puzzle, neural reading, external tool)
3. KataGo results override symbolic results where they differ

Both feed into the same SGF properties (YT, YG, YX, YH, YQ).

### 4.8 Updated Effort Estimate

| Phase | Original | Updated | Delta |
|-------|----------|---------|-------|
| Cleanup | 1-2 hours | 1-2 hours | — |
| Phase 0 | 2-3 hours | 2-3 hours | — |
| **Phase 0.5** | — | **0.5 days** | +0.5 days |
| Phase 1 | 1 day | 1 day | — |
| Phase 2 | 0.5 days | 0.75 days | +0.25 (add `is_group_closed`) |
| Phase 3 | 0.5 days | 0.75 days | +0.25 (add policy-only mode) |
| Phase 4 | 1-2 days | 1-2 days | — |
| Phase 5 | 0.5 days | 0.75 days | +0.25 (dual-engine view) |
| **Total** | **3.5-5.5 days** | **4.5-7 days** | +1-1.5 days |

---

## Part 5: Decision Log Updates

| Decision | Chose | Over | Reason |
|----------|-------|------|--------|
| Add Tsumego Frame phase | Phase 0.5 (before NN) | Defer to Phase 4 | Without tsumego frame, all NN analysis produces garbage — validated by KaTrain code and professional Go review |
| Tiered difficulty estimation | 3-signal combination | Policy-prior-only | Professional review confirmed policy prior has blind spots for miai, approach moves, and "looks normal but hard" positions |
| BTP heuristic estimator | Port `isGroupClosed()` to Phase 2; defer rest to F134 | Include full BTP in Plan 004 | Only `isGroupClosed()` needed for enrichment lab; rest is for F134 |
| Tsumego Miner patterns | Study, rewrite, adapt freely | Ignore | Delta detection, dual-engine, temperature/visits are valuable patterns to reimplement |
| Browser vs Local | Independent parallel tools | Browser counterbalances local | Browser = lightweight quick-check. Local = production workhorse. Dual-engine referee is local-only |
| KaTrain complexity formula | Adopt | Custom formula | Battle-tested in production KaTrain; exactly what we need for trap density |
| Cognitive depth metric | `visits_at_first_consensus` | `top_visits / avg_visits` | Dingdong's ratio is noisy for tsumego with few candidate moves; visit-to-consensus is more meaningful |
| Miai handling | Sum policy priors of correct moves | Use max prior only | Professional review: miai splits priors artificially, inflating perceived difficulty |

---

> **See also:**  
> - [004-plan-browser-engine-option-b.md](004-plan-browser-engine-option-b.md) — Parent plan (to be updated)  
> - [001-research-browser-and-local-katago-for-tsumego.md](001-research-browser-and-local-katago-for-tsumego.md) — Original research  
> - [KaTrain source: tsumego_frame.py](https://github.com/sanderland/katrain/blob/master/katrain/core/tsumego_frame.py) — Tsumego frame reference  
> - [KaTrain source: ai.py](https://github.com/sanderland/katrain/blob/master/katrain/core/ai.py) — Policy-based AI strategies  
> - [BTP estimator.js](https://blacktoplay.com/js/estimator.js) — Heuristic JS scoring reference  
> - [Infinite AI Tsumego Miner](https://github.com/MachineKomi/Infinite_AI_Tsumego_Miner) — Puzzle mining patterns (Delta detection, dual-engine, difficulty grading)
