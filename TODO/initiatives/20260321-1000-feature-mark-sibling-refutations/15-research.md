# Research Brief — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Planning Confidence Score

Starting at 100:
- Architecture seams/ownership boundaries: **clear** — `core/correctness.py` is the right home, `stages/analyze.py` is the call site. No deduction.
- Viable approaches: **one clear winner** (structural sibling heuristic) confirmed by KataGo expert + governance panel. `-0`.
- External precedent: **not needed** — this is a standard tree-walk pattern, no novel algorithms. `-0`.
- Quality/performance/security: **well-understood** — pure in-memory tree walk, no I/O, no security surface. `-0`.
- Test strategy: **clear** — unit tests for the function + frontend regression test. `-0`.
- Rollout/rollback: **clear** — pipeline processes during next re-analyze run, reversible by re-running without the heuristic. `-0`.

**Planning Confidence Score: 100**
**Risk Level: low**

## Research Decision

Research NOT triggered (score ≥ 70, risk level low, no unclear extension points).

## Prior Expert Consultations (Pre-Resolved)

### KataGo Tsumego Expert Assessment

- The sibling heuristic pattern (1 leaf marked `C[RIGHT]`, wrong siblings unmarked) is the **most common convention on goproblems.com** (~40-50% of puzzles from that source).
- All 3 unmarked sub-variations in the `puzzle_14_net` example are **definitively wrong** from Go domain perspective.
- ~22-33% of the total corpus (~2K-3K puzzles) is affected.
- **Miai guard** recommended: only mark siblings wrong when exactly 1 sibling is explicitly correct.
- Source prevalence: goproblems (~40-50%), xuanxuan qijing (~60-70%), eidogo (~30%), kisvadim (~20%), cho-chikun (~5-10%), sanderland (~15%).

### Architecture Review (Codebase Analysis)

Key findings from codebase exploration:

1. **`SolutionNode` dataclass** (`core/sgf_parser.py:179`): `is_correct: bool = True` — default is `True`, meaning `None` from `infer_correctness()` maps to the default `True`.

2. **`_convert_katrain_node()`** (`core/sgf_parser.py:303`): Only sets `is_correct` when `infer_correctness()` returns non-`None`. Unmarked nodes keep `is_correct=True`.

3. **`infer_correctness()`** (`core/correctness.py:22`): Returns `True`, `False`, or `None`. Three layers: SGF markers → comment text → (nothing; returns None).

4. **`count_refutation_moves()`** (`core/quality.py:81`): Counts `is_correct=False` nodes. Already has a Layer 3 structural fallback for root-level only.

5. **`compute_avg_refutation_depth()`** (`core/complexity.py:91`): Walks tree collecting depths of `is_correct=False` subtrees.

6. **`standardize_move_comment()`** (`core/text_cleaner.py:350`): Generates `Wrong` or `Correct` prefix with pedagogical suffix preservation.

7. **Frontend `buildSolutionNodeFromSGF()`** (`frontend/src/lib/sgf-solution.ts:76`): `isCorrect = !hasBadMoveProperty && !hasWrongComment` — already handles `BM[]` and `C[Wrong]`.

8. **Analyze stage** (`stages/analyze.py:222`): Calls `parse_sgf()` → classify → tag → `compute_quality_metrics()` → `compute_complexity_metrics()` → enrich → build SGF. The new function fits between parse and quality computation.

### Call Site Analysis

The new function should be called in `_analyze_puzzle()` after `parse_sgf()` (which builds the `SolutionNode` tree) and before `compute_quality_metrics()` / `compute_complexity_metrics()` (which read `is_correct`). The call site is around line 270 of `stages/analyze.py`, after `game = parse_sgf(content)`.

However, a key insight: the heuristic operates on the `SolutionNode` tree (in-memory), but the analyze stage ultimately builds a **new SGF** via `SGFBuilder`. The modified `is_correct`, `properties['BM']`, and `comment` on `SolutionNode` must flow through to the SGF output. Need to verify that `_enrich_sgf()` preserves solution tree node properties.

### SGF Builder Flow

The `_enrich_sgf()` method in analyze.py uses `SGFBuilder` which reconstructs the SGF from the game object. Need to confirm it writes `BM` and `C` properties from `SolutionNode.properties` and `SolutionNode.comment`.
