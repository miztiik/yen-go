# Puzzle Enrichment Lab Review & Action Plan

This document summarizes a critical review of `tools/puzzle-enrichment-lab/analyzers` conducted from the perspective of a Principal/Staff Software Engineer and theoretical Go masters (Lee Sedol, Cho Chikun).

The pipeline demonstrates a strong structural foundation (Pydantic models, tag-aware routing, engine isolation), but its algorithmic choices suffer from theoretical oversights, "confident but wrong" AI traps, and overly rigid heuristics.

## 1. Validation Logic (`validate_correct_move.py`)

- **The "Phantom" Ownership Verification (Major Flaw):**
  The code promises "ownership-based thresholds" for Life-and-Death (L&D) and notes that center positions use reduced thresholds. However, the code _never actually reads KataGo's ownership grid_. It relies only on `winrate`, `policy`, and `visits`. Winrate is an evaluation of the _entire game state_, not local group survival.
- **Seki Validation is Fragile:**
  Seki uses three signals, one being `abs(response.root_score) < 5.0`. This misunderstands KataGo's Tromp-Taylor/territory scoring. Many sekis encompass large enclosed areas where the expected score delta could exceed 5 points depending on the cropped board's framing.
- **Solution Tree Validation is Permissive and Linear:**
  The check `expected_gtp.upper() in top_moves` permits the correct move to be merely in KataGo's top 3 moves. This is disastrously permissible since the #3 move might be a 5% winrate blunder. Furthermore, the function only traverses a single linear SGF line. Tsumego validation requires verifying responses against the _opponent's resistance_ (branching branches), not just a single happy path.

## 2. Dual Engine Escalation (`dual_engine.py`)

- **The "Confident but Wrong" Trap:**
  Escalation logic merely triggers if the Quick Engine returns an uncertain root winrate (e.g., `0.3 <= winrate <= 0.7`). However, when a low-visit MCTS suffers from the horizon effect, it doesn't return 0.5 winrate—it returns **0.0 winrate** with maximum confidence. Because 0.0 is "certain", no escalation occurs, and the pipeline will incorrectly reject entirely valid, brilliant SGF puzzles. Escalation _must_ be triggered if the engine disagrees with the curated `correct_move`.

## 3. Refutations Generation (`generate_refutations.py`)

- **PV Truncation Misinterpreted as Immediate Failure:**
  The code assumes `refutation_depth = len(pv_sgf)`. If KataGo's PV is truncated due to a lack of visits, the depth will be logged as `1`. This cascades directly into a logic bug in `teaching_comments.py`, which sees `ref_depth <= 1` and statically prints, _"This move is captured immediately."_ A 15-move complex net might act as an immediate capture due to this naive logic.
- **Delta Threshold Flaw:**
  Rigid delta checks fail given the non-binary nature of Ko evaluations. A puzzle might involve "Ko to kill", where initial winrate is 90% (KataGo thinks it has multiple ko threats), but a wrong move drops it to 10% or similar, varying contextually.

## 4. Difficulty Estimation (`estimate_difficulty.py`)

- **Statistical Double-Counting (Collinearity):**
  The pipeline calculates difficulty using independent weights for `policy_component`, `visits_component`, and `trap_density`. Mathematically, PUCT intimately couples visit counts to the network's `policy_prior`. This assigns ~80% of the difficulty score to a single underlying variable: KataGo's un-searched neural network bias.
- **AI Blindness to Human Difficulty:**
  A 15-move ladder is trivial for KataGo (99% policy prior) but mentally taxing for a human. The algorithm severely under-weights actual `structural` depth and branching (12% overall weight). Deep, forced tactical sequences will be rated as "Novice".

## 5. Teaching Comments & Hints (`teaching_comments.py`, `hint_generator.py`)

- **Extreme Rigidity and Lack of Context:**
  "AI-Generated Teaching" here is merely a lookup table mapping the puzzle's pre-existing tags to static paragraphs. `TECHNIQUE_HINTS["snapback"]` outputs a pre-baked response regardless of board state without explaining _why_, outlining danger stones, or evaluating liberties. It's essentially an `if-else` block wrapping KataGo.

## Action Plan for Next Agent

1.  **Fix the Escalation:** Trigger the 2000-visit engine whenever the 200-visit engine thinks the curated solution is bad, regardless of winrate "confidence".
2.  **Implement Real Ownership:** Re-write L&D validation to actually sweep KataGo's ownership grid coordinates for the target stones, matching the promised design.
3.  **Decouple Difficulty:** Re-weight difficulty to respect human topological depth (moves in sequence, number of forced choices) rather than letting KataGo's zero-shot intuition dominate the score.
4.  **Strengthen Validation:** Ensure solution tree validation accounts for branching (opponent's resistance), properly interprets KataGo scores during Seki, and ensures the correct move holds a primary winrate/policy position, not an arbitrary top 3 rank.
5.  **Dynamic Comments:** Develop contextual teaching comments that reference actual board coordinates and engine-specific reading mechanics, rather than static switch-case strings.
6.  **Fix PV Truncation:** Gracefully handle truncated PVs to stop mislabeling deep reads as "immediate captures."
