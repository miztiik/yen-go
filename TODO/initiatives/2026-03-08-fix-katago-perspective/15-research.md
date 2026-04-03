# Research: KataGo `reportAnalysisWinratesAs` Perspective Bug

**Initiative:** `2026-03-08-fix-katago-perspective`  
**Last Updated:** 2026-03-08  
**Researcher:** Feature-Researcher mode

---

## 1. Research Question and Boundaries

**Question:** The enrichment lab's KataGo config uses `reportAnalysisWinratesAs = BLACK`, but
the code was written assuming `SIDETOMOVE` semantics. Which fix is safest and smallest?

**Sub-questions answered:**

- Q1: What does each mode mean exactly, including `scoreLead` and `ownership`?
- Q2: Which of three candidate fix approaches has the lowest blast radius?
- Q3: Where does the winrate perspective flow from KataGo raw JSON to classification?
- Q4: What dead code exists and can be removed?
- Q5: What is current White-puzzle test coverage?

**Boundaries:**  
In scope: `tools/puzzle-enrichment-lab/` only — standalone tool, no `backend/puzzle_manager` imports.  
Out of scope: Frontend, backend pipeline, any other tool.

---

## 2. Internal Code Evidence

### 2.1 Config Mismatch (Primary Evidence)

**File:** [tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg](../../../tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg) — line 35

```ini
# Report winrates from Black's perspective (consistent with SGF convention)
reportAnalysisWinratesAs = BLACK
```

**File:** [tools/puzzle-enrichment-lab/katago/analysis_example.cfg](../../../tools/puzzle-enrichment-lab/katago/analysis_example.cfg) — line 23

```ini
# Report winrates for analysis as (BLACK|WHITE|SIDETOMOVE).
reportAnalysisWinratesAs = BLACK
```

Both configs default to `BLACK`. The comment in `tsumego_analysis.cfg` ("consistent with SGF convention") motivated an intentional but incorrect choice — SGF coordinates use the same orientation but winrate perspective is a separate concept.

### 2.2 Code Semantics Written for SIDETOMOVE

**File:** [tools/puzzle-enrichment-lab/analyzers/solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py) — line 65

```python
def normalize_winrate(winrate, reported_player, puzzle_player):
    """Normalize winrate to puzzle player perspective.

    KataGo reports winrate from the perspective of the move's color.  ← SIDETOMOVE assumption
    ...
    """
    if reported_player == puzzle_player:
        return winrate
    return 1.0 - winrate
```

The docstring explicitly states SIDETOMOVE semantics ("perspective of the move's color"). The three call sites contradict this by always passing `(raw_wr, puzzle_player, puzzle_player)` — a no-op:

| Line  | Call                                                           | Intent (SIDETOMOVE)                                    | Under BLACK mode                                     |
| ----- | -------------------------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| L268  | `normalize_winrate(move_wr_raw, puzzle_player, puzzle_player)` | Same perspective → no flip (correct for Black puzzles) | Wrong for White: raw value is Black's %, not White's |
| L801  | `normalize_winrate(best_wr, player_color, player_color)`       | Same → no flip                                         | Wrong for White puzzles                              |
| L1047 | `normalize_winrate(best_wr, player_color, player_color)`       | Same → no flip                                         | Wrong for White puzzles                              |

Line L242 (confirmation path) correctly passes `opponent_color` as `reported_player` — this is the ONLY correctly parameterized call:

```python
opponent_color = "W" if puzzle_player.upper() == "B" else "B"
confirmed_wr = normalize_winrate(opp_wr, opponent_color, puzzle_player)
```

But under BLACK mode, `opponent_color` is still wrong (should always be `"B"`).

### 2.3 generate_refutations.py — Perspective at L213

**File:** [tools/puzzle-enrichment-lab/analyzers/generate_refutations.py](../../../tools/puzzle-enrichment-lab/analyzers/generate_refutations.py) — line 211

```python
# Winrate from opponent's perspective → for puzzle player it's inverted   ← SIDETOMOVE comment
winrate_after = 1.0 - opp_best.winrate
```

| Mode       | Black puzzle                                                    | White puzzle                                             |
| ---------- | --------------------------------------------------------------- | -------------------------------------------------------- |
| SIDETOMOVE | ✅ `opp_best.winrate`=opponent(W)%, flip→Black(puzzle)%         | ✅ `opp_best.winrate`=opponent(B)%, flip→White(puzzle)%  |
| BLACK      | ❌ `opp_best.winrate`=always Black%, flip→White%≠Black(puzzle)% | ✅ `opp_best.winrate`=always Black%, flip→White(puzzle)% |

Under BLACK mode: line 213 is **correct for White puzzles, wrong for Black puzzles**.
Combined with the L268 bug (always wrong for White puzzles), the net result is:

- **Black puzzles**: L268 accidentally correct, L213 wrong (but L213 is only for refutations, not classification)
- **White puzzles**: L268 wrong, L213 accidentally correct

### 2.4 AnalysisResponse Stores Raw Values

**File:** [tools/puzzle-enrichment-lab/models/analysis_response.py](../../../tools/puzzle-enrichment-lab/models/analysis_response.py) — line 42 and 64

```python
@classmethod
def from_katago_json(cls, data: dict) -> "AnalysisResponse":
    ...
    winrate=mi.get("winrate", 0.5),         # stored raw — BLACK perspective, no transform
    ...
    root_winrate=root.get("winrate", 0.5),  # stored raw — BLACK perspective, no transform
```

No perspective transformation occurs at parse time. `AnalysisResponse.root_winrate` under BLACK mode for a White puzzle contains Black's winning probability, not White's.

### 2.5 Tree Builder Perspective (Secondary Issue)

**File:** [tools/puzzle-enrichment-lab/analyzers/solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py) — line 1047, `_build_tree_recursive`

At opponent-response nodes (`is_player_turn=False`), the engine is queried from the opponent's perspective. Under SIDETOMOVE, `best_wr` is opponent's winning probability, but `normalize_winrate(best_wr, player_color, player_color)` does not flip it. **This is a pre-existing perspective issue independent of BLACK/SIDETOMOVE.** However:

- Under `BLACK` mode + Black puzzle: `best_wr` = always Black% = puzzle player's perspective → accidentally correct
- Under `SIDETOMOVE` + Black puzzle: `best_wr` = opponent(W)%, no flip → used as Black% → WRONG semantically but doesn't trigger stopping conditions incorrectly because `delta = |opponent_wr - root_wr| >> 0` → tree keeps expanding as expected
- The `node.winrate` field stored in the SGF tree will be imprecise at opponent nodes under SIDETOMOVE, but stopping conditions (depth-cap, budget-cap, pass detection) dominate in practice

**Assessment:** This is a lower-severity secondary bug; it causes slightly imprecise `winrate` annotations in SGF opponent nodes but doesn't break puzzle solving logic. It exists under both modes and should be tracked separately.

---

## 3. External References

| R-ID | Source                                  | Finding                                                                                                                                                                                                                   |
| ---- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | KataGo `analysis_example.cfg` (in-repo) | `reportAnalysisWinratesAs = BLACK\|WHITE\|SIDETOMOVE` — three valid options with clear semantics                                                                                                                          |
| R-2  | KataGo README (analysis protocol)       | Under `SIDETOMOVE`, `rootInfo.winrate` and `moveInfos[j].winrate` are from the perspective of whoever is to move at that position. Under `BLACK`, all values are unconditionally from Black's perspective.                |
| R-3  | KataGo README (scoreLead)               | `scoreLead` follows the same perspective convention as `winrate` — positive means the perspective player is ahead. Under `BLACK`, positive always = Black leading. Under `SIDETOMOVE`, positive = current player leading. |
| R-4  | KataGo README (ownership)               | `ownership` is perspective-neutral: `+1.0 = Black likely owns this point`, `-1.0 = White likely owns this point`, regardless of mode. Ownership is not affected by `reportAnalysisWinratesAs`.                            |

**Key finding from R-4:** `ownership` data used in `validate_correct_move.py` is **not affected by this bug** — the life-and-death and seki validators are safe.

---

## 4. Candidate Adaptations for Yen-Go

### Approach A — Fix at Config: `reportAnalysisWinratesAs = SIDETOMOVE`

Change one line in `tsumego_analysis.cfg`. Zero code changes.

**Why the code already expects SIDETOMOVE:**

1. `normalize_winrate` docstring: "KataGo reports winrate from the perspective of the move's color" = SIDETOMOVE
2. `generate_refutations.py` L213 comment: "Winrate from opponent's perspective → for puzzle player it's inverted" = SIDETOMOVE
3. `analyze_position_candidates` L242: correctly identifies `opponent_color` as reported perspective = SIDETOMOVE design
4. All test comments explaining mock values assume SIDETOMOVE: `# root=0.90, move=0.48 → delta=0.02 < 0.05 → TE`

**Under SIDETOMOVE, at each query point:**

- Root-position query (puzzle player to move): `rootInfo.winrate` = puzzle player's % ✅
- Root `moveInfos[j].winrate` = puzzle player's % after playing move j ✅
- Confirmation query (after puzzle player's candidate, so opponent to move): `rootInfo.winrate` = opponent's % → L242 correctly flips ✅
- Refutation query (after wrong move, opponent to move): SIDETOMOVE gives opponent%; L213 `1 - winrate` flips to puzzle player% ✅

**Remaining issue after Approach A:** Opponent nodes in `_build_tree_recursive` (L1047) still use `normalize_winrate(best_wr, player_color, player_color)` — no-op. Under SIDETOMOVE, after puzzle player moved and opponent is to respond, the next query gives the opponent's % (SIDETOMOVE), but this is then stored as puzzle player's % in `node.winrate`. This is a pre-existing issue (§2.5) that affects winrate annotations in opponent SGF nodes but **not puzzle solving logic**. Track as a follow-up.

### Approach B — Fix at Boundary: Normalize in `from_katago_json()`

Add a puzzle-player parameter to `AnalysisResponse.from_katago_json()` and flip winrates for White puzzle players.

**Problems:**

- `AnalysisResponse` is a pure data model; injecting puzzle-player context violates SRP
- Would require propagating `puzzle_player` to every `engine.analyze()` call site
- Adds middleware coupling between data layer and domain layer
- More files changed than Approach A: `analysis_response.py`, `local_subprocess.py`, plus all callers
- Still doesn't fix the secondary tree-builder issue (§2.5)

### Approach C — Fix at Consumption: Hardcode `"B"` in All normalize_winrate Calls

Replace all `normalize_winrate(wr, puzzle_player, puzzle_player)` with `normalize_winrate(wr, "B", puzzle_player)`.

**Problems:**

- 23+ sites across 8 files must change
- Highest blast radius
- `generate_refutations.py` L213-214 needs a different fix (not a normalize call at all)
- `_enrich_curated_policy` needs both `root_wr` and per-move `wr` fixed
- Every change is a test regression risk: mocks simulate SIDETOMOVE, all assertions break
- Dead code: `normalize_winrate()` as currently structured becomes a `"B"` hardcoded wrapper

---

## 5. Risks, Compliance Notes, Rejection Reasons

| R-ID | Risk                                                          | Severity | Note                                                                                                                                                    |
| ---- | ------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | Approach B/C require touching mock data in all tests          | High     | Tests assume SIDETOMOVE semantics in every fixture                                                                                                      |
| R-2  | Approach A doesn't fix secondary L1047 tree opponent-node bug | Low      | Doesn't break correctness of solution tree logic; winrate annotations at opponent nodes are imprecise                                                   |
| R-3  | `scoreLead` sign convention under BLACK mode                  | Low      | `scoreLead` in `classify_move_quality` only used as metadata annotation (not gate); inversion wouldn't change puzzle solving for Black-dominant tsumego |
| R-4  | `ownership` is perspective-neutral — unaffected by bug        | None     | Life-and-death validation via ownership is safe under either mode                                                                                       |
| R-5  | `analysis_example.cfg` also defaults to BLACK                 | Medium   | If lab ever falls back to `analysis_example.cfg`, bug returns. Should also update that file or tighten the runtime enforcement                          |

---

## 6. Dead Code Inventory

| Item                                                                             | File                                                                                                                                    | Status                                                                                                                                              | Recommendation                                                                                |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `EnrichmentRunState`                                                             | [models/enrichment_state.py](../../../tools/puzzle-enrichment-lab/models/enrichment_state.py)                                           | **Actively used** — 20+ callsites in `enrich_single.py` and tests                                                                                   | Keep                                                                                          |
| `difficulty_result.py`                                                           | [models/difficulty_result.py](../../../tools/puzzle-enrichment-lab/models/difficulty_result.py)                                         | Backward-compat shim (3 lines), used only in `test_sprint1_fixes.py`                                                                                | Delete shim + update test import (Level 0)                                                    |
| `ai_solve.enabled` flag                                                          | [analyzers/enrich_single.py](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py) L783-784                                  | **Functional** but always `True` in production config; affects has-solution path gating                                                             | Keep — it's a behavior toggle, not dead code                                                  |
| `normalize_winrate()` call at L268 with `(raw_wr, puzzle_player, puzzle_player)` | [analyzers/solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py)                                         | Under Approach A this becomes correct; under Approach C becomes misleadingly named                                                                  | Under Approach A: keep as-is (correct by coincidence under SIDETOMOVE); annotate with comment |
| **`2026-03-06-fix-enrichment-lab-logging-scope`** initiative                     | [TODO/initiatives/2026-03-06-fix-enrichment-lab-logging-scope/](../../../TODO/initiatives/2026-03-06-fix-enrichment-lab-logging-scope/) | Research complete (`15-research.md` exists), execution never happened — tests `test_log_config.py` and `test_sprint5_fixes.py` likely still failing | Independent of this fix; complete separately                                                  |

---

## 7. White-Puzzle Test Coverage Assessment

### 7.1 Tests That Exist for White Puzzles

| File                           | Test                         | Covers                                                              |
| ------------------------------ | ---------------------------- | ------------------------------------------------------------------- |
| `test_query_builder.py:92`     | `test_white_to_play`         | SGF `PL[W]` → `initialPlayer=W` in query — pure parsing             |
| `test_sgf_parser.py:64`        | `test_extract_white_to_play` | `player_to_move == Color.WHITE` — pure parsing                      |
| `test_tsumego_frame.py:351`    | `test_white_to_play`         | Framed position preserves `player_to_move=WHITE` — pure geometric   |
| `test_solve_position.py:735`   | `test_white_to_play_nodes`   | "White-to-play produces W[] nodes" — SGF node color annotation only |
| `test_tight_board_crop.py:165` | (uses `Color.WHITE`)         | Crop preserves player color                                         |

### 7.2 Gaps: No White-puzzle Winrate Tests

**None of the following exist:**

- `TestAnalyzePositionCandidates` has `test_sign_adjustment_black_to_play` (L637) but **no** `test_sign_adjustment_white_to_play`
- No parametrized `@pytest.mark.parametrize("puzzle_player", ["B", "W"])` test for winrate classification
- No test fixture SGF with `PL[W]` + mock KataGo response to verify classification direction
- No test verifying that `root_winrate` is correct for White puzzles
- No test verifying that `delta = root_winrate - move_wr` has the correct sign for White puzzles

### 7.3 Why Tests Pass Today Despite the Bug

Under `reportAnalysisWinratesAs = BLACK`:

- Black puzzles (`puzzle_player = "B"`): `moveInfos[j].winrate` = Black's % = puzzle player's %. `normalize_winrate(wr, "B", "B")` = no flip = **accidentally correct**
- All unit tests use `puzzle_player = "B"` → all tests pass regardless of BLACK vs SIDETOMOVE mode

**Under the proposed fix (Approach A → SIDETOMOVE):** All current passing tests remain passing. New tests should be added for White puzzles.

---

## 8. Planner Recommendations

1. **Use Approach A: single-line config change.** Change `tsumego_analysis.cfg` line 35 from `reportAnalysisWinratesAs = BLACK` to `reportAnalysisWinratesAs = SIDETOMOVE`. Also update `analysis_example.cfg` (same line) for safety. Zero code changes. All code already implements SIDETOMOVE semantics — docstrings, comments, and confirmation-query logic are all written for SIDETOMOVE. This is a **Level 1** fix with near-zero blast radius.

2. **Add White-puzzle winrate tests (required, part of the same fix).** At minimum add `test_sign_adjustment_white_to_play` to `TestAnalyzePositionCandidates` and a parametrized variant of the core classification test. Without these, any future config drift will go undetected. The test should mock `analysis.root_winrate = 0.2` (White losing from SIDETOMOVE perspective = White at 20%) and verify `delta` signs are correct.

3. **Track the tree-builder opponent-node perspective as a follow-up (not blocking).** `_build_tree_recursive` at L1047 stores imprecise `winrate` at opponent nodes (SIDETOMOVE gives opponent's %, treated as puzzle player's %). This doesn't break tsumego solving but causes imprecise winrate annotations in the SGF tree. A separate initiative should fix this by either: (a) passing current-turn color into `_build_tree_recursive` and flipping at opponent nodes, or (b) always storing the perspective as "current player's probability" and annotating accordingly.

4. **Delete `difficulty_result.py` shim.** It's a 3-line re-export that exists only because of a rename. Update `test_sprint1_fixes.py` import to use `models.difficulty_estimate` directly. **Level 0** cleanup, zero behavior change.

---

## 9. Confidence and Risk

**post_research_confidence_score:** 92

**post_research_risk_level:** `low`

**Reasoning:** The evidence is unambiguous — all code comments, docstrings, and fix logic in the codebase assume SIDETOMOVE. The config mismatch is the sole root cause for White-puzzle bugs. Switching the config requires no code changes and no test changes, making regression risk near zero. The one uncertainty (tree-builder opponent-node perspective) is a secondary pre-existing issue that exists under both modes and is classified as non-blocking.

---

## Handoff

```
research_completed: true
initiative_path: TODO/initiatives/2026-03-08-fix-katago-perspective/
artifact: 15-research.md
top_recommendations:
  - Approach A: Change tsumego_analysis.cfg to SIDETOMOVE (0 code changes, Level 1)
  - Add White-puzzle winrate unit tests (required alongside the fix)
  - Track tree-builder opponent-node perspective as follow-up (not blocking)
  - Delete difficulty_result.py shim (Level 0 cleanup, independent)
open_questions:
  - Q1: Should opponent-node winrate imprecision in the tree builder be fixed in this same PR or a separate initiative?
  - Q2: Is analysis_example.cfg actively used anywhere other than as documentation reference?
post_research_confidence_score: 92
post_research_risk_level: low
```

---

---

## Post-Implementation Verification (2026-03-10)

> **Note**: `status.json` says "closeout/all approved" but all 21 task checkboxes in `40-tasks.md` are unchecked `[ ]`. This section verifies actual code state.

### Verification Table

| Task | Status | Evidence |
|------|--------|----------|
| **T1** | ✅ IMPLEMENTED | `katago/tsumego_analysis.cfg:44` and `katago/analysis_example.cfg:30` both have `reportAnalysisWinratesAs = SIDETOMOVE` |
| **T2** | ✅ IMPLEMENTED | `analyzers/generate_refutations.py:224–229` — SIDETOMOVE comment + `winrate_after = 1.0 - opp_best.winrate` |
| **T3** | ✅ IMPLEMENTED | `tests/test_solve_position.py:940–945` — `MockConfirmationEngine` retains `1.0 - data["winrate"]` **intentionally**, documented as "SIDETOMOVE: opponent perspective". Flip is correct for SIDETOMOVE semantics (after puzzle player moves, it's opponent's turn; KataGo reports opponent perspective). |
| **T4** | ✅ IMPLEMENTED | `tests/test_solve_position.py:2462–2580` — White-to-play test class (4 methods); `normalize_winrate` truth table at lines 68–81; `@pytest.mark.parametrize("puzzle_player", ["B", "W"])` at lines 2545, 2556; all 4 SIDETOMOVE cases covered |
| **T7** | ✅ IMPLEMENTED | `analyzers/solve_position.py` — 16 logger calls; decision-level detail: `"Puzzle %s: root_winrate=%.3f (puzzle_player=%s perspective)"` (line 196), confirmation-query count (line 233), classification summary (line 339) |
| **T8** | ✅ IMPLEMENTED | `analyzers/validate_correct_move.py` — 6 logger calls; line 221: `"dispatching to '%s' validator (tags=%s, ko_type=%s)"` with full decision context |
| **T9** | ⚠️ PARTIALLY | `analyzers/estimate_difficulty.py` — 3 logger calls total; miai prior logged (line 88); level result logged (line 259); warning (line 319). Missing: per-component score breakdown (`policy_component`, `visits_component`, `structural_component` values). |
| **T10** | ✅ IMPLEMENTED | `analyzers/technique_classifier.py` — 4 logger calls explicitly logging per-technique decisions: `"Technique %s: ko=%s"`, `"Technique %s: ladder=%s"`, `"Technique %s: snapback=%s"`, plus final result (lines 110–162) |
| **T11** | ⚠️ PARTIALLY | `analyzers/ko_validation.py` — 1 logger call at line 205. Ko detection result logged but no recurrence-pattern or adjacency-check details emitted. |
| **T12** | ✅ IMPLEMENTED | `analyzers/generate_refutations.py` — 11 logger calls; per-wrong-move winrate detail (line 234), refutation outcome summaries (lines 348, 362, 435) |
| **T13** | ✅ IMPLEMENTED | `analyzers/enrich_single.py` — 20+ logger calls (trace_id line 733, stage decisions, validate/technique/difficulty outcomes); `analyzers/query_builder.py` — 7 calls with query construction detail |
| **T14** | ⚠️ PARTIALLY | **cli.py ✓**: `run_id = generate_run_id()` (line 413) + `set_run_id(run_id)` (line 414). **conftest.py ✗**: inline `"test-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4).upper()` (line 45) instead of `"test-" + generate_run_id()` as specified in `40-tasks.md:101` |
| **T16** | ⚠️ PARTIALLY | `analyzers/ko_validation.py:144–168` — `_has_recapture_pattern()` checks coordinate recurrence + adjacency of intervening move (gap=2 + `_are_adjacent`). Uses adjacency **proxy** for capture, not board-state simulation. Spec required: "coordinate recurrence is ko ONLY if the recaptured intersection shows a stone being removed then placed." |
| **T17** | ✅ IMPLEMENTED | `config/katago-enrichment.json:47–50` — `policy_rank=15.0`, `visits_to_solve=15.0` (combined 30% < 40% ✓), `structural=45.0` (> 35% ✓), `trap_density=25.0` |
| **T18** | ✅ IMPLEMENTED | `config.py:47–65` — `DifficultyWeights` Pydantic defaults match JSON exactly (15/15/25/45); `config.py:489–492` — `SekiDetectionConfig.score_threshold: float = Field(default=5.0, ...)` present |
| **T19** | ✅ IMPLEMENTED | `models/difficulty_result.py` does not exist (deleted; renamed to `difficulty_estimate.py`). Only residual references are comments in `tests/test_sprint1_fixes.py:9,256` documenting the rename. `config/katago-enrichment.json:160` retains `level_mismatch` section. |
| **T20** | ⚠️ PARTIALLY | **config.py ✓**: `AiSolveConfig` has no `enabled: bool` field; docstring states "the `enabled` flag was removed as AI-Solve is mature and always-on". **JSON ✓**: `ai_solve` section has no `"enabled"` key. **enrich_single.py ✗**: `ai_solve_active = ai_solve_config is not None` (line 803) + conditional guards at lines 825, 1395, 1424, 1433 still present. In practice always-True (config.ai_solve is never None), but the gating variable was not removed as specified. |
| **T21** | ─ | Regression suite; test history shows passing runs, not individually verified here. |

### Summary

| Category | Tasks | Count |
|----------|-------|-------|
| ✅ FULLY IMPLEMENTED | T1, T2, T3, T4, T7, T8, T10, T12, T13, T17, T18, T19 | **12 / 20** |
| ⚠️ PARTIALLY IMPLEMENTED | T9, T11, T14, T16, T20 | **5 / 20** |
| ❌ NOT IMPLEMENTED | *(none)* | **0 / 20** |

**Verdict**: Initiative ~85% complete. No task is fully untouched. `status.json` "closeout/all approved" is broadly accurate but 5 tasks have remaining gaps.

### Open Gaps

| Gap | Task | Remaining work |
|-----|------|----------------|
| G1 | T9 | Add per-component score breakdown logging in `estimate_difficulty.py` |
| G2 | T11 | Add recurrence-detail + adjacency-result logging in `ko_validation.py:detect_ko_in_pv()` |
| G3 | T14 | Update `conftest.py:45` to `"test-" + generate_run_id()` (1-line fix) |
| G4 | T16 | Decision required: upgrade `detect_ko_in_pv()` to board-state capture simulation, or formally document adjacency proxy as accepted approximation |
| G5 | T20 | Remove `ai_solve_active` gating variable from `enrich_single.py` (or add comment explaining why None-guard is intentionally retained) |
