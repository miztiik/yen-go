# Tasks — KaTrain SGF Parser Swap (OPT-1)

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Selected Option**: OPT-1
**Last Updated**: 2026-03-13

---

## Phase A: Enrichment Lab

| task_id | title | file(s) | depends_on | parallel | status |
|---------|-------|---------|------------|----------|--------|
| T1 | Create `core/__init__.py` | `tools/puzzle-enrichment-lab/core/__init__.py` | — | [P] | not_started |
| T2 | Copy KaTrain parser into lab core | `tools/puzzle-enrichment-lab/core/sgf_parser.py` | T1 | [P] | not_started |
| T3 | Create tsumego analysis wrapper | `tools/puzzle-enrichment-lab/core/tsumego_analysis.py` | T2 | | not_started |
| T4 | Update `analyzers/stages/protocols.py` (type import) | `tools/puzzle-enrichment-lab/analyzers/stages/protocols.py` | T2 | [P] | not_started |
| T5 | Update `analyzers/query_builder.py` | `tools/puzzle-enrichment-lab/analyzers/query_builder.py` | T3 | [P] | not_started |
| T6 | Update `analyzers/solve_position.py` | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | T3 | [P] | not_started |
| T7 | Rewrite `analyzers/sgf_enricher.py` (remove sgfmill) | `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | T3 | | not_started |
| T8 | Update `analyzers/ascii_board.py` | `tools/puzzle-enrichment-lab/analyzers/ascii_board.py` | T3 | [P] | not_started |
| T9 | Update `analyzers/tsumego_frame_gp.py` | `tools/puzzle-enrichment-lab/analyzers/tsumego_frame_gp.py` | T3 | [P] | not_started |
| T10 | Update `analyzers/stages/parse_stage.py` | `tools/puzzle-enrichment-lab/analyzers/stages/parse_stage.py` | T3 | [P] | not_started |
| T11 | Update `analyzers/stages/solve_paths.py` | `tools/puzzle-enrichment-lab/analyzers/stages/solve_paths.py` | T3 | [P] | not_started |
| T12 | Update `analyzers/stages/difficulty_stage.py` | `tools/puzzle-enrichment-lab/analyzers/stages/difficulty_stage.py` | T3 | [P] | not_started |
| T13 | Update `analyzers/stages/validation_stage.py` | `tools/puzzle-enrichment-lab/analyzers/stages/validation_stage.py` | T3 | [P] | not_started |
| T14 | Update test imports and type references | `tools/puzzle-enrichment-lab/tests/*.py` | T3 | | not_started |
| T15 | Delete old `analyzers/sgf_parser.py` | `tools/puzzle-enrichment-lab/analyzers/sgf_parser.py` | T5-T14 | | not_started |
| T16 | Remove sgfmill from `requirements.txt` | `tools/puzzle-enrichment-lab/requirements.txt` | T7 | | not_started |
| T17 | Run enrichment lab test suite | — | T15, T16 | | not_started |

## Phase B: Backend Puzzle Manager

| task_id | title | file(s) | depends_on | parallel | status |
|---------|-------|---------|------------|----------|--------|
| T18 | Copy KaTrain parser into backend core | `backend/puzzle_manager/core/katrain_sgf_parser.py` | — | [P] with T1 | not_started |
| T19 | Rewrite `core/sgf_parser.py` internals | `backend/puzzle_manager/core/sgf_parser.py` | T18 | | not_started |
| T20 | Run backend test suite (`not cli or slow`) | — | T19 | | not_started |

## Documentation

| task_id | title | file(s) | depends_on | parallel | status |
|---------|-------|---------|------------|----------|--------|
| T21 | Update enrichment lab README | `tools/puzzle-enrichment-lab/README.md` | T17 | [P] | not_started |
| T22 | Create core README | `tools/puzzle-enrichment-lab/core/README.md` | T17 | [P] | not_started |
| T23 | Update CHANGELOG | `CHANGELOG.md` | T17, T20 | | not_started |
| T24 | Update teaching-comments concept doc | `docs/concepts/teaching-comments.md` | T17 | [P] | not_started |
| T25 | Update enrichment-config reference doc | `docs/reference/enrichment-config.md` | T17 | [P] | not_started |
| T26 | Update katago-enrichment-lab how-to | `docs/how-to/tools/katago-enrichment-lab.md` | T17 | [P] | not_started |
| T27 | Update backend architecture doc | `docs/architecture/backend/README.md` | T20 | [P] | not_started |

---

## Task Details

### T1: Create `core/__init__.py`
- Empty file to make `core/` a Python package
- Location: `tools/puzzle-enrichment-lab/core/__init__.py`

### T2: Copy KaTrain parser into lab core
- Download from `https://github.com/sanderland/katrain/blob/master/katrain/core/sgf_parser.py`
- Strip: `import chardet`, `parse_file()`, `parse_gib()`, `parse_ngf()`, entire NGF/GIB sections
- Keep: `Move`, `SGFNode`, `SGF`, `ParseError`, `SGF.parse_sgf()`, `_parse_branch()`, `place_handicap_stones()`
- Adjust internal imports if needed (KaTrain imports nothing outside stdlib)
- Save to: `tools/puzzle-enrichment-lab/core/sgf_parser.py`

### T3: Create tsumego analysis wrapper
- New file: `tools/puzzle-enrichment-lab/core/tsumego_analysis.py`
- Move these functions from old `analyzers/sgf_parser.py` (adapted for KaTrain SGFNode):
  - `extract_position(root: SGFNode) → Position`
  - `extract_correct_first_move(root: SGFNode) → str | None`
  - `extract_correct_first_move_color(root: SGFNode) → str | None`
  - `extract_wrong_move_branches(root: SGFNode) → list[dict]`
  - `extract_solution_tree_moves(root: SGFNode) → list[str]`
  - `count_solution_branches(root: SGFNode) → int`
- Import `infer_correctness` from `tools/core/sgf_correctness.py` (same importlib.util pattern)
- Import `Position`, `Stone`, `Color` from `models.position`
- Key adaptations:
  - `node.move` → KaTrain `Move` object: use `node.move.player` for color, `node.move.sgf(board_size)` for coord
  - `node.get("SZ")` → `node.get_property("SZ")`
  - `node.get_all("AB")` → `node.get_list_property("AB")`
  - `node.comment` → `node.get_property("C", "")`
  - For `compose_enriched_sgf()`: Replaced by building child SGFNodes + `root.sgf()` serialization

### T4-T13: Update consumer imports
- Pattern: Change `from analyzers.sgf_parser import X` → `from core.sgf_parser import SGFNode, SGF, Move` + `from core.tsumego_analysis import extract_position, ...`
- Update `SgfNode` references to `SGFNode`
- Update `.move` tuple access: `color, coord = node.move` → `move = node.move; color = move.player; coord = move.sgf(board_size)`
- Update `parse_sgf(text)` to return `SGFNode` directly: `SGF.parse_sgf(text)` returns root node

### T14: Update test imports and type references
- Update all test files that import from `analyzers.sgf_parser`
- Change `SgfNode` → `SGFNode`, update `.move` tuple access to `Move` object
- **IMPORTANT**: `test_sgf_enricher.py` has a **direct** `from sgfmill import sgf as sgfmill_sgf` import (line ~607) — this is NOT an `analyzers.sgf_parser` re-export. This direct sgfmill import must also be removed/replaced.

### T7: Rewrite sgf_enricher.py
- Remove `from sgfmill import sgf as sgfmill_sgf`
- Rewrite `_get_node_move_coord(node)`:
  - Old: `node.properties()` / `node.get_raw(color).decode()` (sgfmill API)
  - New: `node.move` → `Move` object → `.sgf(board_size)` for coord
- Rewrite `_append_node_comment(node, text)`:
  - Old: `node.get_raw("C").decode()` / `node.set_raw("C", text.encode())`
  - New: `node.get_property("C", "")` / `node.set_property("C", text)`
- Rewrite `_embed_teaching_comments(sgf_text, ...)`:
  - Old: `sgfmill_sgf.Sgf_game.from_bytes()` → navigate → mutate → `game.serialise()`
  - New: `SGF.parse_sgf(sgf_text)` → navigate `root.children[i]` → `set_property()` → `root.sgf()`
- Rewrite `_apply_patches(sgf_text, patches)`:
  - Old: `sgfmill_sgf.Sgf_game.from_bytes()` → `root.set_raw()` → `game.serialise()`
  - New: `SGF.parse_sgf(sgf_text)` → `root.set_property(key, value)` → `root.sgf()`

### T18: Copy KaTrain parser into backend core
- Same stripped file as T2
- Save to: `backend/puzzle_manager/core/katrain_sgf_parser.py`

### T19: Rewrite backend sgf_parser.py internals
- Keep: `SGFGame`, `SolutionNode`, `YenGoProperties`, `parse_sgf()`, `parse_root_properties_only()`
- Delete: `SGFParser` class entirely (methods `__init__`, `parse`, `_parse_game_tree`, `_parse_node`, `_parse_property_name`, `_parse_property_values`, `_parse_variations`, `_parse_node_tree`, `_props_to_node`, `_apply_root_properties`, `_skip_whitespace`)
- Add: `from backend.puzzle_manager.core.katrain_sgf_parser import SGF as KaTrainSGF, SGFNode as KaTrainNode, Move as KaTrainMove`
- Add: `_convert_katrain_tree(root: KaTrainNode) → SGFGame` function that:
  - Extracts board_size from `root.board_size`
  - Extracts stones from `root.placements` (AB/AW)
  - Converts root children to `SolutionNode` tree
  - Extracts `YenGoProperties` from root properties
  - Extracts metadata, root comment
- Rewrite `parse_sgf()` to: call `KaTrainSGF.parse_sgf(content)` then `_convert_katrain_tree()`
- Keep `parse_root_properties_only()` unchanged (regex-based, no sgfmill dependency)

---

## Dependency Graph

```
T1 ──┐
     ├── T2 ── T3 ──┬── T4  [P]
T18 ─┤               ├── T5  [P]
     │               ├── T6  [P]
     │               ├── T7  (sgf_enricher rewrite)
     │               ├── T8  [P]
     │               ├── T9  [P]
     │               ├── T10 [P]
     │               ├── T11 [P]
     │               ├── T12 [P]
     │               ├── T13 [P]
     │               └── T14 (tests)
     │                    │
     │               T15 ←┘ (delete old parser)
     │               T16 (remove sgfmill)
     │                │
     │               T17 (lab test suite)
     │                │
     ├── T19 ── T20 (backend test suite)
     │           │
     └──── T21, T22 [P] ── T23 (changelog)
```
