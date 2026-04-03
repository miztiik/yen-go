# Plan — KaTrain SGF Parser Swap (OPT-1)

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Selected Option**: OPT-1 (Full KaTrain Adoption — Replace Core Types)
**Last Updated**: 2026-03-13

---

## Architecture Overview

```
BEFORE:
  Enrichment Lab                       Backend Puzzle Manager
  ┌─────────────────────────┐          ┌──────────────────────────┐
  │ analyzers/sgf_parser.py │          │ core/sgf_parser.py       │
  │ ├── SgfNode (custom)    │          │ ├── SGFParser (hand-rolled)│
  │ ├── parse_sgf() → sgfmill│         │ ├── SGFGame              │
  │ ├── extract_position()   │         │ ├── SolutionNode         │
  │ ├── extract_correct_*()  │         │ ├── YenGoProperties      │
  │ └── compose_enriched_*() │         │ └── parse_sgf()          │
  │                          │         │                          │
  │ analyzers/sgf_enricher.py│         │                          │
  │ └── sgfmill (direct)     │         │                          │
  └─────────────────────────┘          └──────────────────────────┘

AFTER:
  Enrichment Lab                       Backend Puzzle Manager
  ┌─────────────────────────┐          ┌──────────────────────────────┐
  │ core/sgf_parser.py      │          │ core/katrain_sgf_parser.py   │
  │ ├── Move (KaTrain)      │          │ ├── Move (KaTrain)           │
  │ ├── SGFNode (KaTrain)   │          │ ├── SGFNode (KaTrain)        │
  │ └── SGF (KaTrain)       │          │ └── SGF (KaTrain)            │
  │                          │         │                              │
  │ core/tsumego_analysis.py │         │ core/sgf_parser.py (rewritten)│
  │ ├── extract_position()   │         │ ├── SGFGame (facade, kept)    │
  │ ├── extract_correct_*()  │         │ ├── SolutionNode (kept)       │
  │ ├── extract_wrong_*()    │         │ ├── YenGoProperties (kept)    │
  │ ├── count_branches()     │         │ ├── parse_sgf() (KaTrain based)│
  │ └── compose_enriched_*() │         │ └── parse_root_props_only()   │
  │                          │         │                              │
  │ analyzers/sgf_enricher.py│         │                              │
  │ └── uses SGFNode natively│         │                              │
  └─────────────────────────┘          └──────────────────────────────┘
```

## Phase A: Enrichment Lab

### A.1 — Copy KaTrain Parser

Create `tools/puzzle-enrichment-lab/core/sgf_parser.py` with KaTrain's `Move`, `SGFNode`, `SGF` classes.

**Stripping checklist** (items to remove from KaTrain copy):
- `import chardet` → remove
- `parse_file()` class method → remove entirely
- `parse_gib()` class method → remove entirely
- `parse_ngf()` class method → remove entirely
- `place_handicap_stones()` method → **keep** (used by some SGF files with HA[] property)

**Additions**:
- `core/__init__.py` — empty init

### A.2 — Create Tsumego Analysis Wrapper

Create `tools/puzzle-enrichment-lab/core/tsumego_analysis.py` containing all tsumego-specific functions that currently live in `analyzers/sgf_parser.py`:

| Function | Source | Notes |
|----------|--------|-------|
| `extract_position(root: SGFNode) → Position` | Current `sgf_parser.py` | Converts KaTrain `SGFNode` placements → lab `Position` model |
| `extract_correct_first_move(root: SGFNode) → str \| None` | Current | Uses RIGHT-marker logic |
| `extract_correct_first_move_color(root: SGFNode) → str \| None` | Current | Returns "B"/"W" string (KaTrain convention) |
| `extract_wrong_move_branches(root: SGFNode) → list[dict]` | Current | Uses `infer_correctness` from tools/core |
| `extract_solution_tree_moves(root: SGFNode) → list[str]` | Current | Follows correct path |
| `count_solution_branches(root: SGFNode) → int` | Current | Counts branching points |
| `compose_enriched_sgf(root: SGFNode, refutation_branches) → str` | Current | **Replaced** — use `root.sgf()` with branches added via `SGFNode.play()` or direct child manipulation |

**Key adaptation**: The wrapper functions accept KaTrain `SGFNode` instead of old `SgfNode`. Internal logic uses:
- `node.move` → `Move` object (not tuple)
- `node.get_property("C")` → comment
- `node.children` → children (same)
- `node.properties` → `defaultdict(list)` (same semantics as old `dict[str, list[str]]`)
- `node.set_property("C", text)` → mutation
- `node.sgf()` → serialization (replaces `compose_enriched_sgf`)

### A.3 — Update Lab Consumers

Update all files that import from `analyzers.sgf_parser`:

| File | Changes |
|------|---------|
| `analyzers/query_builder.py` | Change imports to `core.sgf_parser` + `core.tsumego_analysis`. Update `.move` access. |
| `analyzers/sgf_enricher.py` | Remove `from sgfmill import sgf`. Change imports. Rewrite `_embed_teaching_comments` and `_apply_patches` to use KaTrain `SGFNode`. |
| `analyzers/solve_position.py` | Change `SgfNode` import to `SGFNode`. Update `.move` tuple access to `Move` object. |
| `analyzers/ascii_board.py` | Change imports. |
| `analyzers/tsumego_frame_gp.py` | Change imports. |
| `analyzers/stages/parse_stage.py` | Change imports. |
| `analyzers/stages/solve_paths.py` | Change imports. |
| `analyzers/stages/difficulty_stage.py` | Change imports. |
| `analyzers/stages/validation_stage.py` | Change imports. |
| `analyzers/stages/protocols.py` | Change `SgfNode` type to `SGFNode`. |
| `tests/*.py` | Update test imports and type references. |

### A.4 — Rewrite sgf_enricher.py sgfmill code

Replace two functions:

**`_embed_teaching_comments`**: Currently parses with sgfmill, navigates children, mutates `C[]` via `set_raw()`, serializes with `serialise()`. New version:
```
parse_sgf(sgf_text) → root SGFNode
root.children[0].set_property("C", comment)  # correct comment
root.children[i].set_property("C", comment)  # wrong comments
root.sgf()  # serialize back
```

**`_apply_patches`**: Currently parses with sgfmill, sets root properties via `set_raw()`. New version:
```
parse_sgf(sgf_text) → root SGFNode
root.set_property(key, value)
root.sgf()
```

### A.5 — Delete Old Parser + Remove sgfmill

- Delete `analyzers/sgf_parser.py`
- Remove `sgfmill>=2.1.1` from `requirements.txt`

---

## Phase B: Backend Puzzle Manager

### B.1 — Copy KaTrain Parser

Create `backend/puzzle_manager/core/katrain_sgf_parser.py` — same stripped KaTrain copy as Phase A.

### B.2 — Rewrite sgf_parser.py Internals

Replace internal `SGFParser` class with KaTrain-based conversion:

- `parse_sgf(content)` → calls `SGF.parse_sgf(content)` to get KaTrain `SGFNode` tree, then converts to `SGFGame`/`SolutionNode`/`YenGoProperties` via new `_convert_katrain_tree()` function
- `SGFGame`, `SolutionNode`, `YenGoProperties` classes **unchanged** (facade preserved)
- `parse_root_properties_only()` — **keep as-is** (performance optimization, regex-based, doesn't depend on sgfmill)
- Delete old `SGFParser.__init__`, `_parse_game_tree`, `_parse_node`, `_parse_property_name`, `_parse_property_values`, `_parse_variations`, `_parse_node_tree`, `_props_to_node`, `_apply_root_properties`, `_skip_whitespace` methods

### B.3 — Test Validation

- Run `pytest -m "not (cli or slow)"` to validate all backend consumers work through facade
- No consumer file changes expected

---

## Documentation Plan

| doc_id | Action | File | Why |
|--------|--------|------|-----|
| D-1 | Update | `tools/puzzle-enrichment-lab/README.md` | Note parser migration, remove sgfmill reference |
| D-2 | Create | `tools/puzzle-enrichment-lab/core/README.md` | Brief description of KaTrain parser copy and tsumego wrapper |
| D-3 | Update | `CHANGELOG.md` | Note sgfmill removal and KaTrain adoption |
| D-4 | Update | `docs/concepts/teaching-comments.md` | Replace sgfmill reference with KaTrain |
| D-5 | Update | `docs/reference/enrichment-config.md` | Update dependency table, remove sgfmill note |
| D-6 | Update | `docs/how-to/tools/katago-enrichment-lab.md` | Remove sgfmill prerequisite |
| D-7 | Update | `docs/architecture/backend/README.md` | Replace sgfmill in parsing row |

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| `.move` type migration: tests use `color, coord = node.move` tuple unpacking | High | Search all test files for tuple unpacking pattern; update to `node.move.player`, `node.move.sgf()` |
| KaTrain serialization differs from sgfmill (whitespace, ordering) | Medium | Run SGF round-trip tests; verify enriched output is valid SGF; content correctness matters, not byte-identical output |
| `compose_enriched_sgf` API change (tree mutation vs string composition) | Medium | Build refutation branches by creating child `SGFNode` objects with `SGFNode(parent=root, move=Move(...))` then `root.sgf()` |
| CJK encoding in comments | Low | KaTrain uses Python strings throughout; `set_property`/`get_property` are string-based. No byte-level encoding issues. |
| `parse_root_properties_only` performance regression | None | Kept as-is — regex-based, independent of KaTrain |

---

## Rollback Strategy

Phased per-subsystem commits:
1. **Phase A commit**: All enrichment lab changes in one commit. Revert: `git revert <phase-A-sha>`
2. **Phase B commit**: All backend changes in one commit. Revert: `git revert <phase-B-sha>`

No shared state between phases. Each independently revertible.

> **See also**:
> - [Charter](./00-charter.md) — Goals, constraints, acceptance criteria
> - [Options](./25-options.md) — OPT-1 selected, integration proof
> - [Research](./15-research.md) — Dependency audit, consumer blast radius
