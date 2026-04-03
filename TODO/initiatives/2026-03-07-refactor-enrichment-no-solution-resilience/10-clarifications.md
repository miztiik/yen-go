# Clarifications: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Last Updated:** 2026-03-07

## Bug Root Cause Analysis

### Traced Control Flow in `enrich_single_puzzle()`

```
Step 2: Extract correct first move
  ├── correct_move_sgf = extract_correct_first_move(root)
  │
  ├── IF correct_move_sgf is None AND ai_solve NOT active:
  │     └── HARD EXIT → _make_error_result("No correct first move")  ← BUG A
  │
  ├── IF correct_move_sgf is None AND ai_solve IS active:
  │     ├── AI-Solve: analyze_position_candidates()
  │     ├── IF no correct_moves found:
  │     │     └── HARD EXIT → _make_error_result("AI-Solve found no correct moves")  ← BUG B
  │     └── ELSE: builds solution tree → continues to enrichment ← WORKING
  │
  ├── IF correct_move_sgf is NOT None AND ai_solve IS active:
  │     └── has-solution path: validates + discovers alternatives ← WORKING
  │
  └── ELSE (correct_move_sgf is NOT None, ai_solve NOT active):
        └── sets correct_move_gtp, solution_moves → continues ← WORKING
```

**Bug A** (`enrich_single.py:546-555`): When `ai_solve` is disabled, position-only SGFs get `REJECTED` immediately. No partial enrichment (difficulty, techniques, hints) is attempted.

**Bug B** (`enrich_single.py:595-604`): When `ai_solve` IS active but KataGo finds no correct moves (e.g., already-dead position, or insufficient visits), the puzzle is also hard-rejected. The position analysis, ownership data, and policy information that KataGo DID return are discarded.

### Why "Correct-moves-only, no wrong moves" Works Today

For the user's first question: SGFs with only correct moves (no wrong branches) DO get full enrichment today. The flow:

1. `extract_correct_first_move()` → returns the move ✅
2. `extract_wrong_move_branches()` → returns `[]` (empty)
3. `generate_refutations()` → KataGo identifies candidate wrong moves from its own analysis, generates AI refutations ✅
4. Full enrichment pipeline runs ✅

This scenario is **not a bug** — it's working as designed.

## Clarification Questions

| q_id | question                                                                                                                                                                                                                 | options                                                                                                                                                                                         | recommended                                                                                                                                                                 | user_response                                                                                                                                                                                                                                                                                                                                                             | status                |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| Q1   | Is backward compatibility required for `AiAnalysisResult` JSON output? (Do existing JSON outputs need to remain parseable?)                                                                                              | A: Yes — add fields only, no removals / B: No — can break existing schema / C: Other                                                                                                            | A — Add `enrichment_tier` field with backward-compat default; existing consumers see no change                                                                              | `A` (inferred from user's pipeline integration concern)                                                                                                                                                                                                                                                                                                                   | ✅ resolved           |
| Q2   | Should old hard-exit code be removed, or kept behind a config flag?                                                                                                                                                      | A: Remove hard exits, always do partial enrichment / B: Add config flag `reject_no_solution: true/false` / C: Other                                                                             | A — Remove. Never waste a KataGo call. Hard exits become soft downgrades to lower enrichment tiers.                                                                         | A                                                                                                                                                                                                                                                                                                                                                                         | ✅ resolved           |
| Q3   | For Bug A (no ai_solve, no solution): What enrichment is expected?                                                                                                                                                       | A: Position analysis only (board complexity, technique tags from patterns) / B: Full KataGo analysis (send position, AI recommends first move, use as pseudo-correct for difficulty) / C: Other | B — Run KataGo analysis on position, use top move as pseudo-correct for difficulty estimation, but mark `enrichment_tier=1` and DO NOT inject a solution tree into the SGF. | **Escalated to Governance** — User asked to consult panel. WebKaTrain evidence shows B18 model can always find moves. Key sub-question: why does our `analyze_position_candidates()` ever return zero correct moves? Root cause found: `confirmation_min_policy=0.03` pre-filter + deriving root_winrate from `move_infos[0]` instead of `AnalysisResponse.root_winrate`. | ❌ pending governance |
| Q4   | For Bug B (ai_solve active, no correct found): What enrichment is expected?                                                                                                                                              | A: Return partial result with position analysis data already obtained / B: Retry with higher visits before downgrading / C: Other                                                               | A — We already have the KataGo response. Use it for difficulty estimation and technique classification. Mark `enrichment_tier=1`. Don't inject solution tree.               | A                                                                                                                                                                                                                                                                                                                                                                         | ✅ resolved           |
| Q5   | Should the enrichment tier be reflected in the output SGF (e.g., in YQ property's `ac` field)?                                                                                                                           | A: Yes — `ac:0` for tier 1 (bare), `ac:1` for tier 2, `ac:2` for tier 3 / B: No — tier is only in AiAnalysisResult JSON / C: Other                                                              | A — The existing `ac` field in YQ already maps: 0=untouched, 1=enriched. Tier 1 partial → `ac:0` (no solution tree changes). This is already compatible.                    | A                                                                                                                                                                                                                                                                                                                                                                         | ✅ resolved           |
| Q6   | When thinking about future pipeline integration, should `enrich_single_puzzle()` return a structured "enrichment contract" that `backend/puzzle_manager` can consume, or continue returning the full `AiAnalysisResult`? | A: Keep current AiAnalysisResult (pipeline reads what it needs) / B: Add a new slim EnrichmentContract model / C: Other                                                                         | A — AiAnalysisResult already has all fields. Adding `enrichment_tier` is sufficient for the pipeline to decide what to trust. No new model needed (YAGNI).                  | A (inferred)                                                                                                                                                                                                                                                                                                                                                              | ✅ resolved           |

## Research Findings (from Feature-Researcher)

### Root Cause: Why KataGo "Can't Find" Correct Moves

**Confirmed**: This is NOT a KataGo limitation. KataGo ALWAYS returns candidate moves with policy priors and winrates for any valid position. The failure is in our classification gate:

1. **`ai_solve.enabled=false` in config** → Position-only SGFs hit hard-exit WITHOUT EVER QUERYING KataGo
2. **`confirmation_min_policy=0.03` pre-filter** → Can exclude ALL candidates in diffuse positions
3. **`root_winrate` derived from `move_infos[0].winrate`** instead of `AnalysisResponse.root_winrate` (which comes from KataGo's `rootInfo.winrate` directly)

### WebKaTrain Comparison

WebKaTrain has **no classification gate**. It returns every move KataGo returns, with their policy/winrate. The "KaTrain local" Gaussian sampling is an **AI play strategy** (not analysis) — it weights where the AI plays based on proximity to the last move. **Not applicable** to enrichment.

### Verified: `AnalysisResponse.root_winrate` is populated correctly

`AnalysisResponse.from_katago_json()` reads `rootInfo.winrate` directly from KataGo's response (file: `models/analysis_response.py:73`). The engine layer uses this parser (`engine/local_subprocess.py:200`). This field is reliable and should be used instead of deriving from `move_infos[0]`.

## Pre-Answered Clarifications

| q_id | question                                                 | answer                                                                                                                                                                                                                                       | source                                                                                               |
| ---- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| PA1  | "I thought we fixed it" — What was the previous fix?     | The AI-Solve feature (Phase 7) was the fix for position-only SGFs. It builds solution trees from scratch using KataGo. But it only works when `ai_solve.enabled=true` in config, and even then it hard-exits when AI finds no correct moves. | Code trace: `enrich_single.py:524-560`                                                               |
| PA2  | Does "correct-moves-only, no wrong moves" scenario work? | YES — this is working correctly today. KataGo generates AI refutations even when the SGF has no wrong branches.                                                                                                                              | Code trace: `generate_refutations.py` always runs, uses `identify_candidates()` from KataGo analysis |
| PA3  | Will changes break the SGF output format?                | No — the SGF output is always valid. Partial enrichment adds fewer properties (maybe no YR, no refutation branches), but the SGF remains valid. The `enrich_sgf()` function already handles empty refutations gracefully.                    | Code trace: `sgf_enricher.py:enrich_sgf()`                                                           |
