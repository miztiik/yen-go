# Tasks — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

Selected option: **OPT-3 Interleaved Priority Sequence**

All file paths relative to `tools/puzzle-enrichment-lab/` unless otherwise noted.

---

## Phase A: Foundation Fixes

> Dependency: None. Phase A tasks are parallelizable unless noted.

| task | title | files | AC | parallel |
|------|-------|-------|-----|----------|
| T1 | Fix estimate_difficulty per-component logging | `analyzers/estimate_difficulty.py` | AC7 | [P] |
| T2 | Fix ko_validation recurrence logging | `analyzers/ko_validation.py` | AC8 | [P] |
| T3 | Fix conftest run_id format | `conftest.py` | AC9 | [P] |
| T4 | Add ko capture verification | `analyzers/ko_validation.py` | AC6 | |
| T5 | Remove `ai_solve_active` gating variable | `analyzers/enrich_single.py` | AC10 | [P] |
| T6 | Remove `level_mismatch` config section | `config/katago-enrichment.json`, `analyzers/sgf_enricher.py`, Pydantic model | AC11 | [P] |
| T7 | Create doc stubs for Phase B content | `docs/concepts/quality.md`, `docs/architecture/tools/katago-enrichment.md`, `docs/reference/enrichment-config.md` | — | [P] |
| T8 | Phase A regression — all existing tests pass | tests/ | AC19 | |

### T1: Fix estimate_difficulty per-component logging

**What:** Add `logger.debug(...)` calls that log individual component scores (policy_rank, visits_to_solve, trap_density, structural) after they are computed, before the weighted sum.

**Where:** `analyzers/estimate_difficulty.py` — look for the weighted combination section.

**Test:** Verify log output contains per-component breakdown when running a known fixture.

### T2: Fix ko_validation recurrence logging

**What:** Add `logger.debug(...)` calls at: (a) recurrence detection point with the repeated coordinates, (b) adjacency check with the two coordinates and result, (c) overall verdict of `detect_ko_in_pv()`.

**Where:** `analyzers/ko_validation.py` — `detect_ko_in_pv()` function around L117-170, `_are_adjacent()` around L88.

**Test:** Verify log output contains coordinate details when processing a known ko fixture.

### T3: Fix conftest run_id format

**What:** Replace inline run_id generation in `conftest.py` with a call to `generate_run_id()` from the appropriate module, matching the format used in `cli.py`.

**Where:** `conftest.py` — look for run_id assignment.

### T4: Add ko capture verification

**What:** In `detect_ko_in_pv()`, after detecting coordinate recurrence and adjacency, replay the principal variation on a board state to verify that a stone is actually captured (removed) between the repeated coordinates. This replaces the adjacency-only proxy.

**Where:** `analyzers/ko_validation.py` — `detect_ko_in_pv()` and helper `_has_recapture_pattern()`.

**Design:** Board replay approach:
1. Start with initial board state from SGF
2. Play moves from PV in sequence
3. At each recurrence point, verify the intermediate move captured exactly one stone at the recurrence coordinate (or that the stone was removed)
4. If no capture occurred, it is NOT a ko recapture — it is a different situation

**Test:** Write tests for: (a) true ko recapture detected, (b) false positive rejected (same coordinate but no capture), (c) multi-step ko. Use existing ko fixtures.

**Depends on:** None (T2 can be done in parallel since T2 is logging-only).

### T5: Remove `ai_solve_active` gating variable

**What:** The `ai_solve_active` variable in `enrich_single.py` (lines ~803, 813, 825, 1395, 1424, 1433) is always `True` in practice because `ai_solve_config` is always present. Remove the variable and simplify the conditional branches.

**Where:** `analyzers/enrich_single.py` — all 6 references to `ai_solve_active`.

**Design:** For each `if ai_solve_active:` block, replace with unconditional execution (since config is always present). For each `if not ai_solve_active:` block, remove the dead branch.

**Test:** Existing tests must pass with no behavior change.

### T6: Remove `level_mismatch` config section

**Pre-step (RE-9):** Run `grep -r "level_mismatch" tools/ config/ backend/` and verify only expected references exist. If unexpected external references are found, STOP and escalate.

**What:** Delete the `level_mismatch` section from `config/katago-enrichment.json` (around L160) and remove any references in the Pydantic config model. Also remove the `mismatch_cfg = data.get("level_mismatch", {})` reference in `analyzers/sgf_enricher.py` (L83).

**Where:** `config/katago-enrichment.json`, `analyzers/sgf_enricher.py`, and any Pydantic model file that loads `level_mismatch`.

**Test:** Existing tests must pass. Config loading must succeed without the section.

### T7: Create doc stubs

**What:** Add placeholder section headers in existing docs so the structure is ready for Phase E content.

**Stubs to add:**
- `docs/concepts/quality.md`: `## Benson Gate` and `## Interior-Point Exit` sections with "TBD — Phase B implementation pending"
- `docs/architecture/tools/katago-enrichment.md`: `## Pre-Query Terminal Detection` section
- `docs/reference/enrichment-config.md`: `## Benson Gate Config` and `## Interior-Point Config` sections

### T8: Phase A regression test

**What:** Run the full enrichment lab test suite and verify all existing tests pass. Fix any regressions introduced by T1-T6.

**Command:** `cd tools/puzzle-enrichment-lab && python -m pytest tests/ --cache-clear -x --tb=short`

---

## Phase B: Algorithms

> Dependency: Phase A complete (MHC-1).

| task | title | files | AC | parallel |
|------|-------|-------|-----|----------|
| T9 | Implement Benson's unconditional life check | `analyzers/benson_check.py` (new) | AC1, AC2, AC3 | |
| T10 | Implement interior-point two-eye death check | `analyzers/benson_check.py` | AC4, AC5 | |
| T11 | Integrate both gates into solve_position.py | `analyzers/solve_position.py` | AC1, AC2, AC4 | |
| T12 | Write unit tests for Benson gate | `tests/test_benson_check.py` (new) | AC20 | [P] with T13 |
| T13 | Write unit tests for interior-point check | `tests/test_benson_check.py` | AC20 | [P] with T12 |
| T14 | Phase B regression — all tests pass | tests/ | AC19 | |

### T9: Implement Benson's unconditional life check

**What:** Create `analyzers/benson_check.py` with `find_unconditionally_alive_groups(stones, board_size) -> set[frozenset[tuple[int,int]]]`.

Returns ALL unconditionally alive groups on the board. The caller (solve_position.py) determines whether the *contest group* (the group under attack, identified by stones within `puzzle_region`) is among them. Framework/surrounding groups being alive is expected and must NOT trigger the terminal gate.

**Algorithm (Benson 1976):**
1. Identify all connected groups of each color
2. For each group, find "vital regions" — empty connected sets whose every cell is adjacent to the group
3. Remove any region that touches another color's living stone
4. A group is unconditionally alive if it has ≥ 2 vital regions remaining after elimination
5. Iterate: if a previously-alive group loses vital regions, re-evaluate

**No YK usage (C2).** Ko-dependent groups are inherently NOT unconditionally alive — they won't pass the ≥ 2 vital regions test because the ko fight means the region is not unconditionally enclosed.

**Seki handling (C3):** Seki groups typically don't have 2 unconditionally vital regions. Benson returns empty/excludes them → falls through to KataGo. This is correct and safe.

### T10: Implement interior-point two-eye death check

**What:** Add `check_interior_point_death(stones, target_color, puzzle_region, board_size) -> bool` to `benson_check.py`.

**Algorithm:**
1. Compute the `puzzle_region` via `compute_regions(position, config).puzzle_region` from `tsumego_frame.py` (returns `frozenset[tuple[int,int]]`)
2. Filter to empty cells within `puzzle_region` NOT occupied by `target_color` stones
3. If empty cell count ≤ 2 AND no two empty cells are orthogonally adjacent: return True (cannot form two eyes)
4. Otherwise: return False (uncertain — fall through to KataGo)

**Reuses tsumego_frame.py (C4).** Import `compute_regions` from `tsumego_frame`, call with position and config, use `FrameRegions.puzzle_region` as the bounded region.

### T11: Integrate both gates into solve_position.py

**What:** In `_build_tree_recursive()`, add pre-query terminal detection BEFORE the `engine.query()` call.

**Integration pattern:**
```python
# Pre-query terminal detection (Benson gate)
board_state = _reconstruct_board(moves, initial_stones)
alive_groups = find_unconditionally_alive_groups(board_state, board_size)
contest_stones = {pos for pos in board_state if pos in puzzle_region and board_state[pos] == defender_color}
if any(contest_stones <= group for group in alive_groups):
    return SolutionNode(status="proven", result="defender_wins")  # contest group unconditionally alive
if check_interior_point_death(board_state, defender_color, puzzle_region, board_size):
    return SolutionNode(status="proven", result="attacker_wins")
# Existing engine.query() call follows
```

**Critical:** The gate checks whether the *contest group* (stones of defender_color within `puzzle_region`) is unconditionally alive — NOT whether any group of that color is alive. Framework groups are expected to be alive and must be filtered out.

**Where:** `analyzers/solve_position.py` — `_build_tree_recursive()`, approximately L986+.

**Board state reconstruction:** Use the move sequence accumulated in the recursive call stack + initial stone positions from SGF root.

### T12-T13: Unit tests

**Fixtures needed:**
- Unconditionally alive 2-eye contest group (Benson returns group in alive set)
- **Framework false-positive rejection:** board with alive framework group + dead contest group — Benson returns framework as alive but contest group is NOT in the alive set, so gate does NOT fire
- Ko-dependent contest group (Benson does not return it as alive, falls through)
- Seki contest group (Benson does not return it as alive, falls through)
- Group with ≤ 2 interior empty points in puzzle_region, no adjacent pair (death True)
- Group with 3+ interior empty points in puzzle_region (death False)
- Group with 2 adjacent empty interior points in puzzle_region (death False)

---

## Phase C: Individual Reviews

> Dependency: Phase B complete (MHC-2).
> Each review is a separate task (MHC-4, C6).

**Review criteria template (RC-2):**
1. Code present at specified location
2. Tests present and passing
3. Config alignment (JSON ↔ Pydantic)
4. No dead code or TODOs
5. Logging adequate
6. Edge cases covered (≥ 1 happy-path + 1 boundary test)

If any criterion fails: create an inline fix sub-task, execute, re-review.

### KM Gate Reviews (6 tasks)

| task | review target | source |
|------|--------------|--------|
| T15 | KM Phase 2: Config Extension (T017a) | KM tasks doc |
| T16 | KM Phase 3: Transposition (T027a) | KM tasks doc |
| T17 | KM Phase 4: Simulation (T039a) | KM tasks doc |
| T18 | KM Phase 5: Forced Move (T048a) | KM tasks doc |
| T19 | KM Phase 6: Proof-Depth (T058a) | KM tasks doc |
| T20 | KM Phase 7 Final: Benchmarks + Docs (T063a) | KM tasks doc |

All Phase C KM reviews are [P] (parallelizable — no dependency between them).

### Remediation Sign-offs (20 tasks)

| task | review target | source |
|------|--------------|--------|
| T21 | S1-G16: Per-candidate confirmation queries | Remediation sprints |
| T22 | S1-G15: classify_move_quality signature | Remediation sprints |
| T23 | S1-G1: Ownership convergence stopping | Remediation sprints |
| T24 | S1-G12: Corner/ladder visit boosts | Remediation sprints |
| T25 | S1-G14: Co-correct detection score gap | Remediation sprints |
| T26 | S2-G2: Multi-root tree building | Remediation sprints |
| T27 | S2-G3: Has-solution path validate+discover | Remediation sprints |
| T28 | S2-G5: human_solution_confidence wiring | Remediation sprints |
| T29 | S2-G6: ai_solution_validated wiring | Remediation sprints |
| T30 | S2-G17: discover_alternatives async+tree | Remediation sprints |
| T31 | S2-G13: Parallel alternative tree building | Remediation sprints |
| T32 | S3-G4: AC level wiring to AiAnalysisResult | Remediation sprints |
| T33 | S3-G7: Roundtrip assertion STR-5 | Remediation sprints |
| T34 | S3-G11: Goal inference implementation | Remediation sprints |
| T35 | S4-G8: BatchSummary emitter wiring | Remediation sprints |
| T36 | S4-G9: DisagreementSink class | Remediation sprints |
| T37 | S4-G10: Collection-level disagreement monitoring | Remediation sprints |
| T38 | S5-G20: Missing plan-specified tests | Remediation sprints |
| T39 | S5-G19: Missing documentation deliverables | Remediation sprints |
| T40 | S5-G18: Threshold calibration validation | Remediation sprints |

> **Note on T40 (S5-G18):** This is the calibration item. Per user directive D3: EXCLUDE from scope. The review confirms S5-G18 is deferred. Sign-off records: "Deferred — calibration excluded per D3."

All 20 remediation reviews are [P] (parallelizable).

---

## Phase D: sgfmill Conditional Replacement

> Dependency: Phase C complete.
> This phase is droppable (MHC-3).

| task | title | files | AC | parallel |
|------|-------|-------|-----|----------|
| T41 | Replace sgfmill mutation in sgf_enricher.py | `analyzers/sgf_enricher.py` | AC18 | |
| T42 | Replace sgfmill parsing in sgf_parser.py | `analyzers/sgf_parser.py` | AC18 | |
| T43 | Remove sgfmill from dependencies | `requirements.txt` or equivalent | AC18 | |
| T44 | Phase D regression — all tests pass | tests/ | AC19 | |

### T41: Replace sgfmill mutation in sgf_enricher.py

**What:** Replace `node.set_raw(prop, value)` calls with dict-based property mutation on the enrichment lab's `SgfNode.properties` dict + `compose_enriched_sgf()` for serialization.

**Drop criterion:** If CJK comment encoding or `LB` label comma-split edge cases surface, drop T41-T43 and instead add explicit `sgfmill` to `requirements.txt`.

### T42: Replace sgfmill parsing in sgf_parser.py

**What:** Replace `sgfmill.sgf.Sgf_game.from_string()` with enrichment lab's own `parse_sgf()` or adapter over `tools/core/sgf_parser`.

**Note:** Must handle the `dict[str, list[str]]` vs `dict[str, str]` format mismatch between enrichment lab `SgfNode` and tools/core `SgfNode`.

### T43: Remove sgfmill dependency

**What:** Remove `sgfmill` from dependency declarations. Verify no remaining imports.

### T44: Phase D regression

**What:** Full test suite pass after sgfmill removal.

---

## Phase E: Documentation

> Dependency: Phase D complete (or skipped if dropped).

| task | title | files | AC | parallel |
|------|-------|-------|-----|----------|
| T45 | Update docs/concepts/quality.md | `docs/concepts/quality.md` | AC14 | [P] |
| T46 | Update docs/architecture/tools/katago-enrichment.md | `docs/architecture/tools/katago-enrichment.md` | AC15 | [P] |
| T47 | Update docs/how-to/tools/katago-enrichment-lab.md | `docs/how-to/tools/katago-enrichment-lab.md` | AC16 | [P] |
| T48 | Update docs/reference/enrichment-config.md | `docs/reference/enrichment-config.md` | AC17 | [P] |
| T49 | Cross-reference verification | All 4 doc files | AC15 | |
| T50 | Final regression — full test suite | tests/ | AC19 | |

### T45: docs/concepts/quality.md

**Content to add:**
- Benson gate as quality signal: unconditional life detection means puzzle is trivially solved (defender already alive)
- Interior-point exit as quality signal: attacker has guaranteed kill (≤ 2 non-adjacent interior points)
- Updated AC level definitions with new hc/ac values from these gates

### T46: docs/architecture/tools/katago-enrichment.md

**Content to add:**
- Pre-query terminal detection architecture decision: why we short-circuit before engine query
- Benson algorithm description and integration point
- Interior-point algorithm description and tsumego_frame reuse rationale
- Ko capture verification design change (from adjacency proxy to board replay)

### T47: docs/how-to/tools/katago-enrichment-lab.md

**Content to add:**
- How to configure Benson gate parameters (if any config knobs)
- How to configure interior-point exit parameters
- Updated ko detection usage notes

### T48: docs/reference/enrichment-config.md

**Content to add:**
- Benson gate config parameter table
- Interior-point config parameter table
- Updated ko_detection parameters (if any new ones from capture verification)

### T49: Cross-reference verification

**What:** Ensure each of the 4 updated docs includes `> See also:` callouts linking to the other three tiers per project documentation rules.

---

## Task Dependency Graph

```
Phase A: T1 T2 T3 T5 T6 T7 [all parallel]
         T4 (independent but not parallel — involves board replay logic)
         T8 (depends on T1-T7)

Phase B: T9 → T10 → T11 → T12/T13 [parallel] → T14
         (MHC-1: Phase A complete)

Phase C: T15-T20 [all parallel] + T21-T40 [all parallel]
         (MHC-2: Phase B complete)

Phase D: T41 → T42 → T43 → T44
         (MHC-3: droppable)

Phase E: T45 T46 T47 T48 [all parallel] → T49 → T50
```

## Total: 50 tasks

| Phase | Tasks | Parallel-safe | Sequential |
|-------|-------|--------------|------------|
| A | T1-T8 | T1,T2,T3,T5,T6,T7 | T4,T8 |
| B | T9-T14 | T12,T13 | T9,T10,T11,T14 |
| C | T15-T40 | All 26 | None |
| D | T41-T44 | None | All 4 |
| E | T45-T50 | T45,T46,T47,T48 | T49,T50 |
