# Charter — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Level: 3 (Multiple Files)
> Last Updated: 2026-03-21

## Problem Statement

~22-33% of the puzzle corpus (~2K-3K out of ~9K puzzles) contains sub-variations where wrong player moves within correct solution lines lack correctness markers (`BM[1]` + `C[Wrong]`). This causes the frontend to default these moves to `isCorrect = true`, silently accepting wrong moves as correct during puzzle play.

### Root Cause

The most common convention on goproblems.com and other sources is: mark exactly 1 leaf as `C[RIGHT]` and leave wrong siblings completely unmarked. The three-layer correctness inference system (`core/correctness.py`) correctly identifies explicitly-marked nodes but returns `None` for unmarked siblings— which maps to `is_correct=True` (the default on `SolutionNode`).

### Impact

| Dimension | Impact |
|-----------|--------|
| Data quality | ~2K-3K puzzles with silently-wrong correctness data |
| User experience | Players making wrong moves get no "Wrong" feedback — puzzle appears to accept any move |
| Downstream metrics | `rc` (refutation count) and `avg_refutation_depth` undercount because `is_correct` is wrong |
| Sources affected | goproblems (~40-50%), xuanxuan qijing (~60-70%), eidogo (~30%), kisvadim (~20%), cho-chikun (~5-10%), sanderland (~15%) |

## Goals

| ID | Goal |
|----|------|
| G1 | Add `mark_sibling_refutations()` function to `core/correctness.py` that walks the solution tree and marks unmarked (`is_correct=None` → `True` default) sibling nodes as wrong (`BM[1]` + `C[Wrong]`) when exactly 1 sibling is explicitly correct |
| G2 | Integrate the function into the analyze stage pipeline, after `parse_sgf()` but before quality/complexity computation |
| G3 | Ensure the frontend correctly shows "Wrong" feedback for previously-unmarked moves |
| G4 | Unit tests for the heuristic including miai edge case and all node topology variants |
| G5 | Frontend regression test for `buildSolutionNodeFromSGF` with `BM[1]` + `C[Wrong]` markers |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | KataGo-based verification of the heuristic | Structural heuristic is sufficient for >95% cases; KataGo is for future edge-case work |
| NG2 | Frontend code changes | Frontend already handles `BM[1]` and `C[Wrong]` — only the data flowing in changes |
| NG3 | Re-publishing the entire corpus now | Pipeline will fix puzzles on next re-analyze run; bulk re-run is ops, not feature |
| NG4 | Modifying the `SolutionNode.is_correct` default from `True` to `None` | Would require extensive refactoring across the codebase; heuristic fix is simpler |
| NG5 | Handling transposition detection | Out of scope; pure structural sibling check is sufficient |

## Constraints

| ID | Constraint |
|----|------------|
| C1 | No new dependencies |
| C2 | No new files (function goes in existing `core/correctness.py`) |
| C3 | No changes to `deprecated_generator/` |
| C4 | No KataGo dependency for the structural heuristic (pure tree walk) |
| C5 | Must not break existing tests |
| C6 | Must handle edge cases: empty tree, single child, no markers at all, opponent-only nodes |
| C7 | Only mark player-move nodes — opponent response nodes don't carry correctness semantics |
| C8 | Miai guard: when ≥2 siblings marked correct, leave `None` siblings unchanged |

## Acceptance Criteria

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | `mark_sibling_refutations(root)` correctly marks wrong siblings with `BM[1]`, `C[Wrong]`, `is_correct=False` | Unit test: puzzle_14_net example with 3 unmarked wrong nodes |
| AC2 | Miai edge case: when 2+ siblings are correct, `None` siblings are left unchanged | Unit test: miai puzzle topology |
| AC3 | Edge cases pass: empty tree, single child, no markers, all marked, opponent nodes | Unit tests for each |
| AC4 | `count_refutation_moves()` returns higher count after marking | Integration assertion in test |
| AC5 | `compute_avg_refutation_depth()` returns non-zero after marking | Integration assertion in test |
| AC6 | Frontend `buildSolutionNodeFromSGF` correctly detects `BM[1]` + `C[Wrong]` as `isCorrect=false` | Vitest regression test |
| AC7 | Existing backend tests pass without regression | `pytest backend/ -m unit` |
| AC8 | Existing frontend tests pass without regression | `npx vitest run` |
| AC9 | Function called in analyze stage after parse, before quality/complexity | Code review / integration test |
