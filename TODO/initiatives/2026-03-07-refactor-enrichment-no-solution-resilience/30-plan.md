# Plan: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Selected Option:** OPT-1 REVISED (Full AI-Solve for Position-Only)  
**Last Updated:** 2026-03-07 (design review revision)

---

## Design Philosophy (User-Corrected)

> "If the input is position-only, that becomes the FULL enrichment. It's not partial."
> "Determinism is not a requirement. We do our best to find the best answers given the best tools."

Position-only puzzles get FULL AI-Solve, not a lightweight scan. The "partial enrichment" (tier 2) is only a FALLBACK when AI-Solve fails, not the primary path.

---

## Complete Enrichment Flow

```
INPUT: SGF puzzle file
├── Has solution tree (correct moves exist)?
│   ├── YES → Standard enrichment path
│   │   ├── Validate correct move against KataGo
│   │   ├── Add missing refutation branches
│   │   ├── Difficulty, techniques, hints, teaching comments
│   │   └── Result: tier 3, ac:1 or ac:3
│   └── NO (position-only) → FULL AI-Solve (DD-2 revised, DD-9)
│       ├── Always run AI-Solve regardless of ai_solve.enabled flag
│       ├── analyze_position_candidates() → find correct move
│       ├── build_solution_tree() → full solution tree
│       ├── inject_solution_into_sgf() → embed in SGF
│       ├── generate_refutations() → wrong move branches
│       ├── Difficulty, techniques, hints, teaching comments
│       ├── SUCCESS → tier 3, ac:2 (ai_solved)
│       ├── FAIL (no correct moves) → FALLBACK (DD-3)
│       │   ├── Reuse KataGo analysis data for difficulty/techniques
│       │   └── Result: tier 2, ac:0
│       └── ENGINE UNAVAILABLE → FALLBACK (DD-7)
│           ├── Stone-pattern analysis only
│           └── Result: tier 1, ac:0
```

---

## Design Decisions (Consolidated)

| DD   | Title                           | Status                    | Summary                                                                                                                                                                         |
| ---- | ------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DD-1 | Root winrate derivation         | ✅ Active                 | Use `analysis.root_winrate` (from `rootInfo.winrate`)                                                                                                                           |
| DD-2 | Bug A: position-only enrichment | **REVISED**               | Run FULL AI-Solve, not lightweight scan. Existing ai_solve code path handles this.                                                                                              |
| DD-3 | Bug B: AI-Solve fails           | ✅ Active                 | Reuse `pre_analysis` data for tier-2 fallback                                                                                                                                   |
| DD-4 | Position scan visits config     | **WITHDRAWN**             | No longer needed — position-only uses existing `tree_visits: 500`                                                                                                               |
| DD-5 | Tier semantics                  | ✅ Active                 | D26 unchanged: 1=Bare, 2=Structural, 3=Full                                                                                                                                     |
| DD-6 | Partial enrichment stages       | ✅ Active (fallback only) | `difficulty_policy_only + techniques + hints` — for FALLBACK tier-2 only                                                                                                        |
| DD-7 | Error handling                  | ✅ Active                 | try/except → stone-pattern fallback (tier 1)                                                                                                                                    |
| DD-8 | Pipeline integration            | ✅ Active                 | AiAnalysisResult as-is with enrichment_tier                                                                                                                                     |
| DD-9 | Position-only AI-Solve gate     | **NEW**                   | Position-only AI-Solve is UNCONDITIONAL — ignores `ai_solve.enabled` flag. Flag only gates AI enrichment for puzzles that already have solutions.                               |
| FPU  | FPU-analog in tree builder      | **ABSORBED**              | KM-01 (Kawano simulation) IS the FPU-analog — first sibling fully explored, subsequent siblings try cached replies before full expansion. Already implemented. Document in T13. |

---

## Transformation Summary

| Target File                    | Change                                                                         | DD Source          | Lines Affected                             |
| ------------------------------ | ------------------------------------------------------------------------------ | ------------------ | ------------------------------------------ |
| `analyzers/solve_position.py`  | Fix root_winrate derivation                                                    | DD-1               | ~189-190 (2 lines)                         |
| `analyzers/enrich_single.py`   | Remove Bug A hard-exit; enable AI-Solve for position-only regardless of config | DD-2 revised, DD-9 | ~546-555 (remove guard, ~10 lines)         |
| `analyzers/enrich_single.py`   | Replace Bug B hard-exit with fallback tier-2 assembly                          | DD-3, DD-6         | ~595-604 (replace 10 lines with ~30 lines) |
| `models/ai_analysis_result.py` | Update enrichment_tier docstring                                               | DD-5, RC-9         | ~182-193 (docstring only)                  |
| `tests/test_enrich_single.py`  | Tests for full AI-Solve + fallback paths                                       | RC-6               | ~100-150 lines                             |
| `tests/test_solve_position.py` | Test CA-1 fix                                                                  | RC-6               | ~20 lines                                  |

**Removed from plan:**

- ~~`config/katago-enrichment.json` — `position_scan_visits` key~~ (DD-4 WITHDRAWN)
- ~~`config.py` — parse new config key~~ (DD-4 WITHDRAWN)
- ~~`_build_partial_result()` helper for Bug A main path~~ (DD-2 REVISED — uses existing AI-Solve)

---

## Detailed Transformations

### Phase 1: CA-1 Root Winrate Fix (DD-1)

**File:** `analyzers/solve_position.py:189-190`

```python
# BEFORE:
raw_root_wr = _get_winrate(best_move_info)
root_winrate = normalize_winrate(raw_root_wr, puzzle_player, puzzle_player)

# AFTER:
root_winrate = analysis.root_winrate
```

### Phase 2: Bug A — Full AI-Solve for Position-Only (DD-2 revised, DD-9)

**File:** `analyzers/enrich_single.py:546-555`

The hard-exit block:

```python
if correct_move_sgf is None and not ai_solve_active:
    logger.error("No correct first move found in SGF for puzzle %s", puzzle_id)
    return _make_error_result(...)
```

**Becomes:** Remove the `not ai_solve_active` guard. Position-only puzzles ALWAYS enter the AI-Solve path (the block starting at line 560: `if correct_move_sgf is None and ai_solve_active:`). The fix is to make this path unconditional for position-only SGFs:

```python
if correct_move_sgf is None:
    # DD-9: Position-only → always run AI-Solve (regardless of ai_solve.enabled)
    # If no solution tree exists, building one IS the enrichment
    logger.info("Puzzle %s: position-only SGF, running AI-Solve", puzzle_id)
    # ... existing AI-Solve path (lines 560-730) runs here ...
```

This is primarily a guard condition change (~5 lines), not new code. The existing AI-Solve code path already handles everything.

### Phase 3: Bug B — AI-Solve Fails Fallback (DD-3, DD-6)

**File:** `analyzers/enrich_single.py:595-604`

When `pos_analysis.correct_moves` is empty after AI-Solve:

```python
if not pos_analysis.correct_moves:
    # DD-3: AI-Solve found no correct moves — fallback to partial enrichment
    logger.warning("Puzzle %s: AI-Solve found no correct moves, falling back", puzzle_id)

    top_move = pre_analysis.top_move
    pseudo_correct_policy = top_move.policy_prior if top_move else 0.0

    difficulty_estimate = estimate_difficulty_policy_only(
        policy_prior=pseudo_correct_policy,
        move_order=move_order, puzzle_id=puzzle_id,
    )
    return _build_partial_result(
        puzzle_id=puzzle_id, position=position, config=config,
        difficulty_estimate=difficulty_estimate,
        scan_response=pre_analysis,
        source_file=source_file, trace_id=trace_id, run_id=run_id,
        tags=tags, corner=corner, move_order=move_order,
        board_size=board_size, enrichment_tier=2,
    )
```

### Phase 4: Partial Result Helper (Fallback Only)

`_build_partial_result()` is needed ONLY for the fallback case (Bug B fail + engine-unavailable). Runs DD-6 stages: difficulty(policy_only) + techniques + hints. Teaching comments only if technique tags non-empty.

---

## Risks and Mitigations

| Risk                                                                     | Mitigation                                                                                       |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| AI-Solve fails for many position-only puzzles                            | Fallback produces tier-2 (not REJECTED). Existing ai_solve code already handles many edge cases. |
| `ai_solve.enabled=false` in config but code ignores it for position-only | DD-9: document explicitly. The flag retains meaning for has-solution puzzles.                    |
| Engine unavailable                                                       | DD-7: try/except → tier-1 stone-pattern fallback                                                 |

## Rollback Strategy

1. Phase 1 (CA-1): Revert 2 lines in `solve_position.py`
2. Phase 2 (Bug A): Restore the `not ai_solve_active` guard condition
3. Phase 3 (Bug B): Restore hard-exit block
4. Phase 4 (helper): Remove `_build_partial_result()` function

## SOLID/DRY/KISS/YAGNI

| Principle | Assessment                                                                                 |
| --------- | ------------------------------------------------------------------------------------------ |
| **SRP**   | Simplified: Bug A REUSES existing AI-Solve path instead of building a parallel "scan" path |
| **DRY**   | `_build_partial_result()` only for fallback — no duplicate logic with main path            |
| **KISS**  | Simpler than original plan: removing a guard condition vs. adding 50 lines of scan code    |
| **YAGNI** | DD-4 (position_scan_visits config) WITHDRAWN — not needed                                  |

        )
        t_scan_start = time.monotonic()
        scan_response = await engine_manager.analyze(query_result.request)
        scan_elapsed = time.monotonic() - t_scan_start

        # Back-translate if cropped
        if query_result.cropped.is_cropped:
            scan_response = _uncrop_response(scan_response, query_result.cropped)

        # DD-6: Use top move by VISITS as pseudo-correct for difficulty estimation
        top_move = scan_response.top_move
        pseudo_correct_gtp = top_move.move if top_move else "A1"
        pseudo_correct_policy = top_move.policy_prior if top_move else 0.0

        # RC-7: Observability log
        logger.info(
            "Position scan complete: puzzle_id=%s, visits=%d, elapsed=%.3fs, "
            "top_move=%s, root_wr=%.3f",
            puzzle_id, scan_visits, scan_elapsed,
            pseudo_correct_gtp, scan_response.root_winrate,
        )

        # DD-6: Run partial enrichment stages
        # 1. Difficulty (policy-only)
        difficulty_estimate = estimate_difficulty_policy_only(
            policy_prior=pseudo_correct_policy,
            move_order=move_order, puzzle_id=puzzle_id,
        )
        # 2. Build partial result
        result = _build_partial_result(
            puzzle_id=puzzle_id, position=position, config=config,
            difficulty_estimate=difficulty_estimate,
            scan_response=scan_response, pseudo_correct_gtp=pseudo_correct_gtp,
            source_file=source_file, trace_id=trace_id, run_id=run_id,
            tags=tags, corner=corner, move_order=move_order,
            board_size=board_size, enrichment_tier=2,
        )
        return result

    except Exception as e:
        # DD-7: Fallback to stone-pattern enrichment
        logger.warning(
            "Position scan failed for puzzle %s: %s (falling back to stone-pattern enrichment)",
            puzzle_id, e,
        )
        return _build_partial_result(
            puzzle_id=puzzle_id, position=position, config=config,
            difficulty_estimate=None, scan_response=None,
            pseudo_correct_gtp=None,
            source_file=source_file, trace_id=trace_id, run_id=run_id,
            tags=tags, corner=corner, move_order=move_order,
            board_size=board_size, enrichment_tier=1,
        )

````

### Phase 3: Bug B — Reuse pos_analysis (DD-3)

**File:** `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`

**Replace lines 595-604** (the hard-exit in AI-Solve path) with:

```python
if not pos_analysis.correct_moves:
    # DD-3: No correct moves found, but we have KataGo analysis data
    logger.warning(
        "Puzzle %s: AI-Solve found no correct moves — "
        "falling back to partial enrichment (tier 2)",
        puzzle_id,
    )
    # Use top move from pre_analysis for pseudo-correct
    top_move = pre_analysis.top_move
    pseudo_correct_gtp = top_move.move if top_move else "A1"
    pseudo_correct_policy = top_move.policy_prior if top_move else 0.0

    difficulty_estimate = estimate_difficulty_policy_only(
        policy_prior=pseudo_correct_policy,
        move_order=move_order, puzzle_id=puzzle_id,
    )
    return _build_partial_result(
        puzzle_id=puzzle_id, position=position, config=config,
        difficulty_estimate=difficulty_estimate,
        scan_response=pre_analysis, pseudo_correct_gtp=pseudo_correct_gtp,
        source_file=source_file, trace_id=trace_id, run_id=run_id,
        tags=tags, corner=corner, move_order=move_order,
        board_size=board_size, enrichment_tier=2,
    )
````

### Phase 4: Partial Result Assembly Helper

**File:** `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`

**New function** (DRY: shared by Bug A and Bug B paths):

```python
def _build_partial_result(
    puzzle_id, position, config, difficulty_estimate, scan_response,
    pseudo_correct_gtp, source_file, trace_id, run_id,
    tags, corner, move_order, board_size, enrichment_tier,
) -> AiAnalysisResult:
    """Build a partial AiAnalysisResult for tier-1 or tier-2 enrichment.

    DD-6: Runs difficulty(policy_only) + technique_classifier + hint_generator.
    Teaching comments only if technique tags non-empty. No solution tree injection.
    """
    config_hash = _compute_config_hash(config)

    # Validation: FLAGGED (not REJECTED, not ACCEPTED)
    validation = MoveValidation(
        status=ValidationStatus.FLAGGED,
        flags=["partial_enrichment:no_solution_tree"],
    )

    result = AiAnalysisResult(
        puzzle_id=puzzle_id, trace_id=trace_id, run_id=run_id,
        source_file=source_file, validation=validation,
        enrichment_tier=enrichment_tier, ac_level=0,
    )

    # Difficulty
    if difficulty_estimate:
        result.difficulty = _build_difficulty_snapshot(difficulty_estimate)

    # Technique classification
    analysis_dict = result.model_dump()
    result.technique_tags = classify_techniques(analysis_dict, board_size=board_size)

    # Hints (using pseudo-correct coordinate if available)
    if pseudo_correct_gtp and scan_response:
        result.hints = generate_hints(analysis_dict, result.technique_tags, board_size=board_size)

    # Teaching comments (DD-6: only if technique tags detected)
    if result.technique_tags:
        result.teaching_comments = generate_teaching_comments(
            analysis_dict, result.technique_tags
        )

    # Level info
    if result.difficulty:
        level_name, level_range = _resolve_level_info(result.difficulty.suggested_level_id)
        result.suggested_level_name = level_name
        result.suggested_level_range = level_range

    return result
```

### Phase 5: Config + Model Updates

**File:** `config/katago-enrichment.json` — Add under `deep_enrich`:

```json
"position_scan_visits": 100
```

**File:** `tools/puzzle-enrichment-lab/config.py` — Add field to `DeepEnrichConfig`:

```python
position_scan_visits: int = Field(default=100, ge=10, le=1000, description="Visits for position-only scan (DD-4)")
```

**File:** `tools/puzzle-enrichment-lab/models/ai_analysis_result.py` — Update docstring (RC-9):

```python
enrichment_tier: int = Field(
    default=3, ge=1, le=3,
    description=(
        "D26 enrichment tier: 1=Bare (no KataGo data, stone-pattern only), "
        "2=Structural (KataGo position scan OR legacy v2 migration, "
        "    disambiguate via status field: FLAGGED=partial enrichment, ACCEPTED=legacy), "
        "3=Full (complete KataGo analysis with solution tree validation). "
        "Sentinel values (-1.0) for KataGo-specific fields in tier 1/2."
    ),
)
```

---

## Risks and Mitigations

| Risk                                                  | Probability | Impact | Mitigation                                                              |
| ----------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------- |
| CA-1 fix changes classification for edge-case puzzles | Low         | Low    | Best-move delta shift < 0.005 at typical visits; no threshold crossings |
| Position scan fails (engine unavailable)              | Medium      | Low    | DD-7: try/except → tier-1 fallback with stone-pattern enrichment        |
| Merge conflicts with concurrent enrichment lab work   | Low         | Medium | Phase 1 (CA-1) is independent and mergeable first                       |
| `position_scan_visits` config key not loaded          | Low         | Low    | Pydantic default=100; even if config unchanged, defaults work           |

## Rollback Strategy

Each phase is independently revertible:

1. CA-1: Revert 2 lines in `solve_position.py`
2. Bug A: Revert `enrich_single.py` replacement block → restores hard-exit
3. Bug B: Revert `enrich_single.py` replacement block → restores hard-exit
4. Helper: Remove `_build_partial_result()` function
5. Config: Remove `position_scan_visits` key

All changes are within a single branch. `git revert` on the merge commit is sufficient.

## SOLID/DRY/KISS/YAGNI Compliance

| Principle | Assessment                                                                                                    |
| --------- | ------------------------------------------------------------------------------------------------------------- |
| **SRP**   | `_build_partial_result()` has one job: assemble tier-1/2 output. Separate from full enrichment.               |
| **OCP**   | `ai_solve` config semantics unchanged. New scan path is additive.                                             |
| **DRY**   | Shared helper prevents duplicating partial assembly logic between Bug A and Bug B.                            |
| **KISS**  | No new abstractions, no new models, no new engine modes. Three function calls (difficulty, technique, hints). |
| **YAGNI** | Only `enrichment_tier` + `position_scan_visits` added. No speculative features.                               |
