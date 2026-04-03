# Research Brief: KaTrain Reuse vs Enrichment Lab

**Initiative**: `20260308-1400-feature-katrain-reuse-enrichment-lab`  
**Research Date**: 2026-03-08  
**Researcher Mode**: Feature-Researcher  
**License**: KaTrain MIT (sanderland/katrain) — free reuse with attribution  

---

## 1. Research Question and Boundaries

**Question**: Which KaTrain backend/non-UI modules offer 1:1 or partial-match reuse for the `tools/puzzle-enrichment-lab`, and where must we preserve local delta?

**Scope in KaTrain** (included):
- `katrain/core/tsumego_frame.py` — frame filling
- `katrain/core/engine.py` — KataGo subprocess driver
- `katrain/core/sgf_parser.py` — SGF/GIB/NGF parser + `Move` coordinate class
- `katrain/core/game.py` — capture rules, ko, legal-move validation (`BaseGame`)
- `katrain/core/ai.py` — move selection strategies, ELO rank calibration
- `katrain/core/utils.py` — `var_to_grid`, `evaluation_class`, `weighted_selection_without_replacement`
- `katrain/core/constants.py` — calibration grids

**Scope excluded**: `katrain/gui/`, `katrain/__main__.py`, `katrain/i18n/`, contrib engine, Kivy widgets.

**Enrichment-lab target modules** (evaluated):
- `analyzers/tsumego_frame.py`, `analyzers/solve_position.py`, `analyzers/estimate_difficulty.py`
- `analyzers/validate_correct_move.py`, `analyzers/ko_validation.py`, `analyzers/sgf_parser.py`
- `engine/local_subprocess.py`, `engine/config.py`
- `models/position.py`, `models/analysis_request.py`, `models/analysis_response.py`

**Key constraint discovered**: KaTrain's `core/engine.py`, `core/game.py`, and `core/game_node.py` **directly import `kivy`** at the module level (`from kivy.utils import platform as kivy_platform`, `from kivy.clock import Clock`). This makes vendoring whole modules impossible without stripping those imports.

---

## 2. Internal Code Evidence

### 2.1 Tsumego Frame

**KaTrain** (`katrain/core/tsumego_frame.py`, lines 0–290, ported from lizgoban by kaorahi):
- `tsumego_frame_stones(stones, komi, black_to_play_p, ko_p, margin)` — main entry
- `snap0()`/`snapS()` — edge-snapping for corner detection (`near_to_edge = 2`)
- `need_flip_p()`, `flip_stones()` — normalizes position to top-left corner
- `put_border()`, `put_outside()`, `put_ko_threat()` — stone placement strategies
- Ko-threat patterns: hardcoded `offense_ko_threat` and `defense_ko_threat` ASCII patterns
- Stone representation: `{"stone": True, "black": bool, "tsumego_frame": True}`
- Entry: `tsumego_frame_from_katrain_game(game, komi, black_to_play_p, ko_p, margin)` → `(played_node, katrain_region)` — KaTrain-specific

**Enrichment lab** ([analyzers/tsumego_frame.py](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py)):
```python
# Header: "Adapted from KaTrain's tsumego_frame.py approach."
# Works with Position/Stone/Color Pydantic models instead of dict-based stones
def apply_tsumego_frame(position: Position, margin: int = 2, offense_color: Optional[Color] = None) -> Position
```
- Uses `_PUZZLE_MARGIN = 2`, `_MIN_FRAME_BOARD_SIZE = 5`
- Builds `occupied` set from `Position.black_stones`/`Position.white_stones`
- Returns a new `Position` (immutable Pydantic model via `model_copy(deep=True)`)

**Gap**: The KaTrain version includes `put_ko_threat()` with offset patterns and `flip_stones()` normalization for arbitrary board position. The local version omits these — no evidence the local `apply_tsumego_frame` performs flip normalization or places ko-threat safety stones.

### 2.2 KataGo Engine Driver

**KaTrain** (`katrain/core/engine.py`, lines 96–480):
- `KataGoEngine`: 3-thread model — `_write_stdin_thread`, `_analysis_read_thread`, `_read_stderr_thread`
- Priority-ordered query queue (`write_queue = queue.Queue()`)
- Pondering support (`_kt_continuous` ponder key)
- Region-of-interest filtering via `avoidMoves` in the query payload
- `request_analysis()` builds the full KataGo JSON query including `overrideSettings`
- `terminate_query(query_id)` support for cancellation
- Tightly coupled: `from kivy.utils import platform as kivy_platform`; `self.katrain.log()` throughout; uses `find_package_resource()` for model path lookup

**Enrichment lab** ([engine/local_subprocess.py](../../../tools/puzzle-enrichment-lab/engine/local_subprocess.py)):
- `LocalEngine`: async/await API via `asyncio`, single response-ID dict
- No priority queuing, no pondering, no ROI filtering
- Uses `threading.Lock` for concurrent request dispatch
- Independent of Kivy, pydantic-typed request/response models
- Builds query from `AnalysisRequest` pydantic model → KataGo JSON

**Gap**: KaTrain's pondering, priority queue, and `terminate_query` are whole-game features not needed for batch puzzle enrichment. The 3-thread model is relevant inspiration but cannot be imported due to Kivy coupling.

### 2.3 SGF Parsing

**KaTrain** (`katrain/core/sgf_parser.py`, lines 0–713):
- `Move` class: `from_gtp()`, `from_sgf()`, `gtp()`, `sgf()`, handles `tt=pass`, board size 52+, player opponent flipping
- `SGFNode`: properties dict, placement expansion (range format `aa:ee`), `nodes_from_root`, `next_player`, `initial_player`, handicap stone placement, komi/ruleset accessors
- `SGF.parse_sgf()`, `parse_ngf()`, `parse_gib()` — multi-format support including GIB (Tygem) and NGF
- FoxGo server komi correction in `parse_sgf()`

**Enrichment lab** ([analyzers/sgf_parser.py](../../../tools/puzzle-enrichment-lab/analyzers/sgf_parser.py)):
```python
# "Uses sgfmill (proper SGF grammar parser) internally"
from sgfmill import sgf as sgfmill_sgf
@dataclass
class SgfNode:
    properties: dict[str, list[str]]
    children: list[SgfNode]
    parent: SgfNode | None
```
- Uses sgfmill for grammar correctness; wraps into `SgfNode` dataclass
- Imports `infer_correctness` from `tools/core/sgf_correctness.py` via dynamic import
- Does NOT support GIB/NGF formats — only SGF

**Move conversion** handled by `models/position.py:Stone`:
```python
@property
def sgf_coord(self) -> str:
    return chr(ord('a') + self.x) + chr(ord('a') + self.y)
def gtp_coord_for(self, board_size: int) -> str:
    letters = "ABCDEFGHJKLMNOPQRST"
    ...
@classmethod
def from_sgf(cls, color: Color, sgf_coord: str) -> "Stone":
    x = ord(sgf_coord[0]) - ord('a')
    y = ord(sgf_coord[1]) - ord('a')
```

### 2.4 Legal Move / Rules Validation

**KaTrain** (`katrain/core/game.py:BaseGame._validate_move_and_update_chains()`):
- Full Python capture engine: chain tracking, ko detection (`ko_or_snapback`), suicide rules (ruleset-aware: tromp-taylor/newzealand allow group suicide, Japanese/Chinese don't)
- `IllegalMoveException` if ko, occupied, suicide
- `_calculate_groups()` replays from root on every `set_current_node()`
- Designed for **interactive whole-game play**

**Enrichment lab** ([analyzers/ko_validation.py](../../../tools/puzzle-enrichment-lab/analyzers/ko_validation.py)):
- Ko detection from **KataGo PV analysis** — detects repeated moves in PV sequences
- `KoPvDetection.ko_detected`, `KoPvDetection.repeated_moves`
- Does not maintain a board state engine; delegates legality to KataGo
- `KoValidationResult.status: ValidationStatus` (ACCEPTED/FLAGGED/REJECTED)

**Enrichment lab** ([analyzers/validate_correct_move.py](../../../tools/puzzle-enrichment-lab/analyzers/validate_correct_move.py)):
- Tag-aware dispatch table; routes to specialized handlers by puzzle tag ID
- Uses KataGo `winrate`/`policy_prior`/`ownership` signals, not rules engine

### 2.5 Strength/ELO Estimation

**KaTrain** (`katrain/core/ai.py:ai_rank_estimation()` + `constants.py` grids):
- Calibrated ELO grids: `AI_PICK_ELO_GRID`, `AI_TENUKI_ELO_GRID`, `AI_LOCAL_ELO_GRID` — 2D interpolation over `(pick_frac, pick_n)`
- `CALIBRATED_RANK_ELO` — maps ELO to kyu (e.g. `(-21.68, 18)` through `(3200, -9)`)
- `ai_rank_estimation(strategy, settings)` → dan rank as integer
- Purpose: **estimate playing strength of weakened AI agents** for interactive training

**Enrichment lab** ([analyzers/estimate_difficulty.py](../../../tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py)):
- `estimate_difficulty_policy_only(policy_prior, move_order, correct_move_priors)` → `DifficultyEstimate`
- Composite difficulty: KataGo signals primary (≥80%), structural secondary (≤20%)
- Maps to Yen-Go 9-level system via thresholds from `config/katago-enrichment.json`
- Purpose: **estimate tsumego puzzle difficulty** from neural net signals

### 2.6 Search Semantics — Policy/Visit Heuristics

**KaTrain** (`katrain/core/ai.py`, key functions):
- `policy_weighted_move(policy_moves, lower_bound, weaken_fac)` — selects a move from policy distribution with `pv ** (1/weaken_fac)` weighting
- `var_to_grid(array_var, size)` in `utils.py` — converts flat 361-element policy array to `grid[y][x]` (note KaTrain calls this grid format not the raw flat format)
- `PickBasedStrategy.handle_endgame()` — detects endgame by `cn.depth > settings["endgame"] * board_squares`
- `RankStrategy.get_n_moves()` — calibrated polynomial formula for number of moves to consider

**Enrichment lab** ([analyzers/solve_position.py](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py)):
- `normalize_winrate(winrate, reported_player, puzzle_player)` — perspective normalization (KaTrain uses `"reportAnalysisWinratesAs": "BLACK"` override instead)
- `classify_move_quality()` — delta-based classification from winrate drop
- `analyze_position_candidates()` — pre-filtering with category-aware depth profiles

### 2.7 `var_to_grid` Utility

**KaTrain** (`katrain/core/utils.py`, lines 14–20):
```python
def var_to_grid(array_var: List[T], size: Tuple[int, int]) -> List[List[T]]:
    ix = 0
    grid = [[]] * size[1]
    for y in range(size[1] - 1, -1, -1):  # NOTE: iterates y from top-down
        grid[y] = array_var[ix : ix + size[0]]
        ix += size[0]
    return grid
```
- Converts flat ownership/policy to `grid[y][x]` where y=0 is bottom row
- Used in `game_node.py:policy_ranking` and throughout `ai.py`

**Enrichment lab**: The `AnalysisResponse.move_infos[*].ownership` is already a `list[list[float]]` (pre-structured by `from_katago_json()`). The flat policy array is referenced in `solve_position.py` but KaTrain's grid utility is not imported.

---

## 3. External References

| R-ID | Source | Relevance |
|------|--------|-----------|
| R-1 | [KaTrain `core/tsumego_frame.py`](https://github.com/sanderland/katrain/blob/main/katrain/core/tsumego_frame.py) — ported from [lizgoban](https://github.com/kaorahi/lizgoban) | Canonical tsumego frame algorithm including flip normalization and ko-threat pattern |
| R-2 | [KaTrain `core/engine.py`](https://github.com/sanderland/katrain/blob/main/katrain/core/engine.py) | 3-thread KataGo subprocess model; priority queuing; full analysis JSON protocol |
| R-3 | [KaTrain `core/sgf_parser.py`](https://github.com/sanderland/katrain/blob/main/katrain/core/sgf_parser.py) | Complete `Move` class with GTP/SGF interop; `SGFNode` tree with range-expansion |
| R-4 | [KaTrain `core/ai.py`](https://github.com/sanderland/katrain/blob/main/katrain/core/ai.py) | `ai_rank_estimation()`, calibration grids, `var_to_grid` usage, policy strategy |
| R-5 | [KaTrain `core/game.py`](https://github.com/sanderland/katrain/blob/main/katrain/core/game.py) | `BaseGame._validate_move_and_update_chains()` — full Go rules engine |
| R-6 | [KaTrain README — Tsumego Frame](https://github.com/sanderland/katrain/blob/main/README.md#L171-L174) | User-facing description of intended frame use case |
| R-7 | [MIT License](https://github.com/sanderland/katrain/blob/main/LICENSE) | Permissive MIT; requires copyright notice and license in derived works |
| R-8 | [sgfmill PyPI](https://github.com/mattheww/sgfmill) | Already a dependency of enrichment lab; used as the parsing substrate |

---

## 4. Candidate Adaptations for Yen-Go

### 4.1 Tsumego Frame — Fill in Missing Algorithms

**From** `katrain/core/tsumego_frame.py`:
- Port `put_ko_threat()` with `offense_ko_threat`/`defense_ko_threat` ASCII patterns
- Port `flip_stones()` + `need_flip_p()` + `snap0()`/`snapS()` for position normalization
- Adapt interface: replace KaTrain dict-based stone model with `Stone/Position` Pydantic models

**Recommended approach**: **Adapter layer** — extract pure algorithmic functions (no Game/GameNode dependencies in `tsumego_frame.py`), adapt coordinate system. KaTrain uses `(i=row, j=col)` = (y, x); enrichment lab uses `(x, y)`.

### 4.2 `var_to_grid` Utility — Direct Vendor

**From** `katrain/core/utils.py` (5 lines):
- Pure function, no dependencies on Kivy or game state
- Directly vendorable to `tools/puzzle-enrichment-lab/analyzers/` or `tools/utils.py`
- Required attribution: "adapted from sanderland/katrain (MIT)"

**Note**: KaTrain iterates `y` from `size[1]-1` downward. Verify enrichment lab coordinate orientation before using.

### 4.3 `Move` Coordinate Class — Inspiration Only

**From** `katrain/core/sgf_parser.py`:
- KaTrain `Move.sgf()` uses `board_size[1] - coords[1] - 1` for row flipping
- Enrichment lab `Stone.gtp_coord_for(board_size)` already handles this correctly
- GTP skips 'I': `GTP_COORD = list("ABCDEFGHJKLMNOPQRST...") `
- No reuse needed; local implementation is equivalent. **Inspiration-only**.

### 4.4 Engine Driver — Inspiration Only

**From** `katrain/core/engine.py`:
- 3-thread model (stdin writer, stdout reader, stderr reader) is a valid pattern
- Priority queue pattern (`write_queue.put((query, callback, ...))`) is useful for multi-puzzle batch
- Cannot vendor: hard `from kivy.utils import platform as kivy_platform` and `from katrain.core.lang import i18n` imports throughout; `self.katrain.log()` calls replace standard logging
- **Delta to preserve**: enrichment lab's async/await model is architecturally cleaner for batch use; priority queue pattern can be locally added if needed

### 4.5 Rules Engine (`BaseGame`) — Not Applicable

**From** `katrain/core/game.py`:
- Ko/capture/suicide rules engine is whole-game oriented
- Enrichment lab correctly delegates rule validation to KataGo (`ko_validation.py`)
- Adding a Python rules engine would create dual-source-of-truth for legality
- **Reject**: No migration path warranted; KataGo is authoritative for puzzle legal-move decisions

### 4.6 ELO/Rank Calibration Data — Inspiration Only

**From** `katrain/core/constants.py` + `ai.py`:
- `CALIBRATED_RANK_ELO` maps playing-strength ELO to kyu/dan (e.g. calibrated against GnuGo, Pachi)
- `ai_rank_estimation()` is entirely about weakened AI playing strength for interactive use
- Enrichment lab's `estimate_difficulty_policy_only()` maps **neural net policy confidence → puzzle difficulty level**; these are orthogonal
- Could use the `interp1d`/`interp2d` interpolation helper functions as utility inspiration
- **Inspiration-only**: conceptual similarity only; data tables are not applicable to puzzle leveling

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-ID | Area | Risk | Notes |
|------|------|------|-------|
| R-1 | Tsumego Frame Ko-threat | **Medium** — ASCII patterns (`offense_ko_threat`, `defense_ko_threat`) assume 19×19 board geometry; need validation for smaller cropped boards | Test on 9×9 and 13×13 board sizes |
| R-2 | Engine Kivy coupling | **High** — `from kivy.utils import platform` is a hard import; any vendor attempt pulls in Kivy as a runtime dependency | Do NOT vendor engine.py in full |
| R-3 | Coordinate axis convention | **Medium** — KaTrain `tsumego_frame.py` uses `(i=row, j=col)` order (opposite of enrichment lab `(x=col, y=row)`); silently wrong outputs if mismatched | Require explicit axis mapping in adapter |
| R-4 | License | **Low** — MIT with attribution; must retain copyright notice `# tsumego frame ported from lizgoban by kaorahi` in any ported code; also note KaTrain's own credit | Add `# Adapted from katrain/core/tsumego_frame.py (MIT, sanderland) — original ported from lizgoban by kaorahi` |
| R-5 | Tight coupling risk | **Low–Medium** — Vendoring only pure functions (no Game/GameNode deps) limits coupling; `tsumego_frame.py` itself has minimal deps (`GameNode`, `Move` only, which are excluded from the port) | Port pure functions only |
| R-6 | Update strategy | **Low** — KaTrain v1.x is stable; tsumego frame logic is well-established Go theory unlikely to change | No automated sync needed; copy-and-adapt once |
| R-7 | `var_to_grid` y-axis | **Low** — KaTrain iterates `y` from `size[1]-1` downward matching KataGo's coordinate convention; ensure consistent use | Verify against `AnalysisResponse` flat policy field |

**Blanket rejection criteria**:
- Any KaTrain module that imports `kivy` — cannot vendor without major Kivy removal surgery
- `game.py` `BaseGame` and `game_node.py` `GameNode` — whole-game UI state machines, not applicable to batch puzzle processing
- `ai.py` strategy classes (`PickBasedStrategy`, etc.) — tournament/interactive play patterns, mismatched problem domain

---

## 6. Area-by-Area Migration Recommendations Matrix

| Area | KaTrain Module | Enrichment Lab Module | Fit | Expected Benefit | Migration Risk | Recommended Action |
|------|---------------|----------------------|-----|-----------------|----------------|-------------------|
| Tsumego Frame (core algorithm) | `core/tsumego_frame.py` — `tsumego_frame_stones()`, `put_border()`, `put_outside()` | `analyzers/tsumego_frame.py` | **Partial** | Complete flip normalization + ko-threat placement currently missing | Medium (axis convention) | **P1**: Adapter layer — port pure functions, adapt coordinate system |
| Tsumego Frame (ko-threat pattern) | `core/tsumego_frame.py` — `put_ko_threat()`, ASCII patterns | `analyzers/tsumego_frame.py` | **Partial** | Ko-puzzle quality signals currently absent | Medium (board-size bounds) | **P1**: Port alongside core frame |
| `var_to_grid` utility | `core/utils.py` — `var_to_grid()` | Not present; `analysis_response.py` handles ownership only | **Exact match** | Enables flat policy array → grid conversion if needed | Low | **P2**: Vendor 5-line pure function with attribution |
| KataGo engine driver | `core/engine.py` — `KataGoEngine` | `engine/local_subprocess.py` — `LocalEngine` | **Mismatch** (Kivy coupled) | Priority queue, terminate-query patterns useful in theory | **High** (Kivy dependency) | **Inspiration only**: borrow queue pattern locally if needed |
| SGF parsing | `core/sgf_parser.py` — `SGF`, `SGFNode`, `Move` | `analyzers/sgf_parser.py` (sgfmill wrapper) | **Partial** | GIB/NGF formats, range-expansion support | Low–Medium | **P3**: Only port NGF/GIB parsers if new source adapters need them; keep sgfmill for core SGF |
| Move coordinate class | `core/sgf_parser.py` — `Move` | `models/position.py` — `Stone` | **Partial** | GTP 52+ board support; `tt=pass` aliasing | Low | **Inspiration only**: local implementation already covers 19×19 correctly |
| Legal move / rules | `core/game.py` — `BaseGame._validate_move_and_update_chains()` | `analyzers/ko_validation.py`, `analyzers/validate_correct_move.py` | **Mismatch** | N/A — approaches are fundamentally different | High (breaks KataGo-first architecture) | **Reject**: Do not port; keep KataGo-delegated approach |
| ELO/rank calibration | `core/ai.py` — `ai_rank_estimation()`, `constants.py` grids | `analyzers/estimate_difficulty.py` | **Mismatch** (different domain) | N/A — one is playing strength, one is puzzle difficulty | N/A | **Reject**: Orthogonal use cases |
| Policy-weighted selection | `core/ai.py` — `policy_weighted_move()` | `analyzers/solve_position.py` — `classify_move_quality()` | **Partial** (different consumer) | Normalizing visit/policy weighting logic | Low | **P3**: Inspiration for future difficulty signal refinement |
| `interp1d`/`interp2d` | `core/ai.py` — `interp1d`, `interp2d` | Not present | **Exact match** (pure math) | Generic interpolation for threshold tables | Low | **P2**: Could vendor if config threshold interpolation is needed |

---

## 7. Planner Recommendations

- **P1 — Port KaTrain tsumego frame core algorithms into adapter layer** (`analyzers/tsumego_frame.py`): Extract `put_ko_threat()`, `flip_stones()`/`need_flip_p()`, `snap0()`/`snapS()` from `katrain/core/tsumego_frame.py`. Adapt coordinate system from KaTrain `(i=row, j=col)` to enrichment lab `(x=col, y=row)`. Add attribution comment. This directly fills the identified gap (missing flip normalization + ko-threat stones) with tested, battle-proven code. Estimated scope: Level 2 (1 file, ~50–80 lines).

- **P2 — Vendor `var_to_grid()` pure utility with attribution**: If flat policy-to-grid conversion is ever needed (currently handled at `AnalysisResponse` construction time via `from_katago_json()`), the 5-line KaTrain helper is a direct candidate. Low-risk, zero-dependency. Estimated scope: Level 0.

- **P3 — No engine vendoring; preserve current `LocalEngine` architecture**: The enrichment lab's async model is better suited to batch puzzle processing than KaTrain's Kivy-coupled, interactive-game-oriented engine. Borrow priority-queue pattern locally if throughput becomes a bottleneck. No code migration.

- **P4 — Do not migrate rules validation or ELO estimation**: The approach gap is fundamental, not an interface gap. Enrichment lab delegates legality to KataGo (correct); KaTrain embeds a Python rules engine for UI responsiveness (different problem). ELO grids are calibrated for playing-strength weakening, not puzzle leveling.

---

## 8. Confidence and Risk Update for Planner

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260308-1400-feature-katrain-reuse-enrichment-lab/` |
| `artifact` | `15-research.md` |
| `top_recommendations` | P1 (tsumego frame algorithms), P2 (var_to_grid), P3 (no engine vendor), P4 (no rules/ELO migration) |
| `open_questions` | Q1: Does the current `apply_tsumego_frame` in enrichment lab intentionally omit flip normalization (i.e., puzzles are always pre-normalized to top-left corner), or is this a gap? If intentional, P1 scope narrows to ko-threat only. |
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | low |

**Risk qualifier**: The one unresolved uncertainty (Q1) affects P1 scope sizing only. The core finding — that the enrichment lab already adapted KaTrain's frame approach but is missing flip normalization and ko-threat placement — is well-evidenced by both codebases. Kivy coupling as a blocking factor for engine/game/AI classes is definitive.

---

*Last Updated: 2026-03-08*
