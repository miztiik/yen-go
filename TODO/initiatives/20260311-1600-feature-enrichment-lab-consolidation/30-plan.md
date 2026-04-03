# Plan — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

## Selected Option

**OPT-3: Interleaved Priority Sequence** (unanimous governance approval)

5 phases: Foundation fixes → Algorithms → Individual reviews → sgfmill replacement → Documentation

## Architecture

### Phase A: Foundation Fixes

**Target files** (all in `tools/puzzle-enrichment-lab/`):
- `analyzers/ko_validation.py` — add capture verification to `detect_ko_in_pv()`
- `analyzers/estimate_difficulty.py` — add per-component score breakdown logging
- `analyzers/enrich_single.py` — remove `ai_solve_active` gating variable
- `conftest.py` — use `generate_run_id()` format
- `config/katago-enrichment.json` — remove `level_mismatch` section

**Design decisions:**
- Ko capture verification: replay board state from PV to verify stone removal between repeated coordinates. Not just adjacency — actual capture-recapture cycle must be detected.
- `ai_solve_active` removal: inline the `ai_solve_config is not None` check at each usage site, then remove the variable entirely. Since config is always present, these checks become unconditionally True and can be simplified.
- `level_mismatch` removal: delete the section from JSON and any Pydantic model that references it.

**Doc stubs (RC-1):** Create placeholder sections in these files during Phase A:
- `docs/concepts/quality.md` — add `## Benson Gate` and `## Interior-Point Exit` section headers with "TBD — Phase B implementation pending"
- `docs/architecture/tools/katago-enrichment.md` — add `## Pre-Query Terminal Detection` section header
- `docs/reference/enrichment-config.md` — add `## Benson Gate Config` and `## Interior-Point Config` section headers

This ensures doc structure exists before the code, and Phase E fills in the content.

### Phase B: Algorithms

**New file:** `tools/puzzle-enrichment-lab/analyzers/benson_check.py` (~80-120 lines)

**Benson's Unconditional Life Gate (G1):**
- Implement `find_unconditionally_alive_groups(stones, board_size) -> set[frozenset[tuple[int,int]]]`
- Returns ALL unconditionally alive groups on the board. The caller determines whether the contest group (the group under attack in the puzzle) is among them.
- Algorithm: For each connected group, find "vital regions" — empty connected sets whose every cell is adjacent to the group. A group is unconditionally alive if it has ≥ 2 vital regions remaining after iterative elimination.
- **Scoping to contest group:** In tsumego, framework/surrounding stones ARE unconditionally alive by construction. The function returns all alive groups; `solve_position.py` checks whether the *specific contest group* (identified by the stones within tsumego_frame's `puzzle_region`) is in the alive set. Framework groups being alive is expected and must NOT trigger the gate.
- Integration point: `solve_position.py` → `_build_tree_recursive()` — before calling `engine.query()`, call `find_unconditionally_alive_groups()`, then check if the contest group's stones (the group within `puzzle_region`) are a subset of any returned alive group.
- If contest group is unconditionally alive: return synthetic terminal node (defender wins, `status="proven"`) without querying KataGo.
- **No YK property (C2):** The gate does NOT check YK. Benson's algorithm inherently handles ko — ko-dependent positions are NOT unconditionally alive, so they naturally fall through to KataGo.
- **Seki handling (C3):** Benson does NOT classify seki groups as alive (seki is not unconditional life). If Benson classifies a group as "dead" (not unconditionally alive), it falls through to KataGo for full evaluation. This is correct.
- Board state reconstruction: use the existing move sequence from `_build_tree_recursive()` context plus `SgfNode` initial stone data.

**Interior-Point Two-Eye Exit (G2):**
- Add `check_interior_point_death(stones, target_color, puzzle_region, board_size) -> bool` to `benson_check.py`
- Algorithm: within the `puzzle_region` (from `compute_regions(position, config).puzzle_region`), count empty cells not occupied by `target_color`. If ≤ 2 empty interior points and no two are orthogonally adjacent, defender cannot form two eyes.
- Integration: same pre-query check in `_build_tree_recursive()`, but for the "attacker wins" path.
- **Reuse tsumego_frame (C4):** call `compute_regions(position, config)` from `tsumego_frame.py` to get `FrameRegions.puzzle_region` as the bounded region. The `puzzle_region` is a `frozenset[tuple[int,int]]` of all cells inside the frame boundary.

**Data model impact:** None — these are pre-query filters that return existing `SolutionNode` types.

**Risks and mitigations:**

| risk | severity | mitigation |
|------|----------|-----------|
| Benson false positive (declares alive when not) | HIGH | Conservative: only trigger on clear two-vital-region configurations. Test against known seki/ko fixtures. |
| Interior-point false positive on non-enclosed positions | MEDIUM | Gate on tsumego_frame boundary validity — skip if boundary cannot be computed. |
| Board state reconstruction errors | MEDIUM | Unit test against known board positions from existing fixtures. |

### Phase C: Individual Reviews

**Review criteria template (RC-2):**

For each of the 26 reviews (6 KM + 20 remediation), the reviewer must verify:

1. **Code present:** Implementation exists at the specified file and location
2. **Tests present:** At least 1 test covers the feature; test passes
3. **Config alignment:** Any config parameters used are declared in both JSON and Pydantic model
4. **No dead code:** No commented-out alternatives or TODO markers remain
5. **Logging adequate:** Key decisions are logged (not just entry/exit)
6. **Edge cases:** At minimum, one happy-path and one boundary test exist

Each review produces a 1-line sign-off: `[x] TNNX reviewed: [pass/fail] — [1-line evidence]`

If any review FAILS: create a fix task in Phase C itself, execute the fix, re-review.

### Phase D: sgfmill Replacement

**Conditional on complexity (MHC-3).**

Two sub-phases from research:
1. Rewrite `_embed_teaching_comments()` and `_apply_patches()` in `sgf_enricher.py` to use enrichment lab's own `parse_sgf()` + `SgfNode.properties` dict mutation + `compose_enriched_sgf()` (~60 lines)
2. Replace sgfmill parsing substrate in `sgf_parser.py` with adapter over `tools/core/sgf_parser` (~65 lines)

**Drop criterion:** If Phase D sub-phase 2 reveals the `tools/core` parser cannot handle CJK comment encoding or `LB` label comma-split edge cases, Phase D is dropped and sgfmill is legitimized via `requirements.txt` entry instead.

### Phase E: Documentation

**Files to update:**
- `docs/concepts/quality.md` — fill Benson gate and interior-point sections, AC level definitions
- `docs/architecture/tools/katago-enrichment.md` — add pre-query terminal detection design decisions, Benson algorithm description, interior-point algorithm description
- `docs/how-to/tools/katago-enrichment-lab.md` — add Benson gate config knobs, interior-point usage
- `docs/reference/enrichment-config.md` — add benson_check config parameters, interior-point parameters

**Files to create:** None — all target files exist.

**Cross-references:** Each updated doc must include `> See also:` linking to the other three tiers per project documentation rules.

## Documentation Plan

| doc_action | file | what | why |
|------------|------|------|-----|
| update | `docs/concepts/quality.md` | Benson gate quality signal, interior-point quality signal, AC level updates | AC14 |
| update | `docs/architecture/tools/katago-enrichment.md` | Pre-query terminal detection architecture, Benson design decision, interior-point design decision | AC15 |
| update | `docs/how-to/tools/katago-enrichment-lab.md` | Benson config, interior-point config, ko capture verification usage | AC16 |
| update | `docs/reference/enrichment-config.md` | Benson config table, interior-point config table, updated ko_detection parameters | AC17 |

## Contracts and Interfaces

### New Public API: `benson_check.py`

```python
def find_unconditionally_alive_groups(
    stones: dict[tuple[int, int], str],  # (row, col) -> "B" | "W"
    board_size: int = 19,
) -> set[frozenset[tuple[int, int]]]:
    """Return all unconditionally alive groups on the board.

    Each group is a frozenset of (row, col) coordinates.
    Caller must check whether the contest group is in the returned set.
    Framework groups being alive is expected — do NOT use membership
    of framework groups as a terminal signal.
    """

def check_interior_point_death(
    stones: dict[tuple[int, int], str],
    target_color: str,                    # "B" | "W" (defender)
    puzzle_region: frozenset[tuple[int, int]],  # from compute_regions().puzzle_region
    board_size: int = 19,
) -> bool:
    """Return True if target_color cannot form two eyes within puzzle_region."""
```

### Integration Point: `solve_position.py`

In `_build_tree_recursive()`, BEFORE `engine.query()`, call `find_unconditionally_alive_groups()`, then check if the contest group (stones within `puzzle_region`) is a subset of any returned alive group.

```python
# Pre-query terminal detection (Benson gate)
board_state = _reconstruct_board(moves, initial_stones)
alive_groups = find_unconditionally_alive_groups(board_state, board_size)
contest_stones = {pos for pos in board_state if pos in puzzle_region and board_state[pos] == defender_color}
if any(contest_stones <= group for group in alive_groups):
    return SolutionNode(status="proven", ...)  # defender wins (contest group unconditionally alive)
if check_interior_point_death(board_state, defender_color, puzzle_region, board_size):
    return SolutionNode(status="proven", ...)  # attacker wins (cannot form two eyes)
# Fall through to KataGo query
```

## Rollout and Rollback

- Each phase is independently revertible via `git revert` of phase commits
- Phase D (sgfmill) is explicitly droppable (MHC-3)
- No database migrations or schema version bumps required
- All changes are in `tools/puzzle-enrichment-lab/` (isolated; no backend or frontend impact)
