# Research Brief — KaTrain SGF Parser Swap

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Date**: 2026-03-13
**Source**: Feature-Researcher agent + prior research (`20260310-research-sgfmill-replacement`)

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Pre-research score | 45 |
| Post-research score | 82 |
| Risk level | medium |
| Research trigger | Score < 70, risk medium |

---

## 1. KaTrain Dependency Audit

KaTrain's `sgf_parser.py` imports:

| Import | Type | Required? |
|--------|------|-----------|
| `copy` | stdlib | Yes — used in `sgf_properties()` |
| `chardet` | **external** | No — only used in `parse_file()` for encoding detection |
| `math` | stdlib | Yes — used in `place_handicap_stones()` |
| `re` | stdlib | Yes — core parsing regex |
| `collections.defaultdict` | stdlib | Yes — `SGFNode.properties` storage |

**Conclusion**: Strip `chardet` import and `parse_file()` method. Zero external dependencies remain. Both subsystems parse strings, not files.

---

## 2. Backend Consumer Blast Radius

Backend uses `SGFGame`, `SolutionNode`, `YenGoProperties`, `parse_sgf()`, `parse_root_properties_only()`.

| Consumer | Imports | Key Properties Used |
|----------|---------|---------------------|
| `core/classifier.py` | `SGFGame`, `SolutionNode` | `.board_size`, `.solution_tree`, `.children`, `.move`, `.color`, `.is_correct` |
| `core/complexity.py` | `SGFGame`, `SolutionNode` | `.solution_tree`, `.get_main_line()`, `.children`, `.move`, `.count_variations()` |
| `core/content_classifier.py` | `SGFGame` | `.board_size`, `.black_stones`, `.white_stones`, `.solution_tree`, `.yengo_props` |
| `core/quality.py` | `SGFGame`, `SolutionNode` | `.solution_tree`, `.children`, `.comment`, `.is_correct`, `.move` |
| `stages/ingest.py` | `parse_sgf` | Returns `SGFGame` |
| `stages/analyze.py` | `parse_sgf`, `SGFGame` | `.raw_sgf`, `.yengo_props`, `.solution_tree` |
| `stages/publish.py` | `parse_sgf` | `.metadata`, `.yengo_props`, `.root_comment` |
| `adapters/local/adapter.py` | `parse_sgf` | Full `SGFGame` |
| `inventory/reconcile.py` | `parse_root_properties_only` | Returns `dict[str, str]` |
| ~10 test files | Various | All types |

**Conclusion**: Backend consumers depend on the `SGFGame`/`SolutionNode` facade heavily. The recommended approach is to **keep the facade types** and replace only the internal `SGFParser` class with KaTrain's `SGF.parse_sgf()` + conversion. This shields all 15+ consumers from type changes.

---

## 3. Enrichment Lab Consumer Blast Radius

| Consumer | Imports from sgf_parser | Key Properties Used |
|----------|------------------------|---------------------|
| `query_builder.py` | `parse_sgf`, `extract_position`, `extract_correct_first_move_color` | `SgfNode.move` (tuple), `SgfNode.get()`, `SgfNode.get_all()` |
| `sgf_enricher.py` | `parse_sgf`, `extract_solution_tree_moves`, `compose_enriched_sgf` + direct `sgfmill_sgf` | Two parser APIs in use |
| `stages/parse_stage.py` | `parse_sgf`, `extract_position`, `extract_correct_first_move` | Standard SgfNode API |
| `stages/solve_paths.py` | `extract_correct_first_move`, `extract_solution_tree_moves` | Standard |
| `stages/difficulty_stage.py` | `count_solution_branches` | Standard |
| `stages/validation_stage.py` | `extract_wrong_move_branches` | Standard |
| `solve_position.py` | `SgfNode` | `.children`, `.move`, `.properties`, `.comment` |
| `ascii_board.py` | `parse_sgf`, `extract_position` | Standard |
| `tsumego_frame_gp.py` | `parse_sgf`, `extract_position` | Standard |

**Critical point**: `sgf_enricher.py` uses TWO parser APIs:
1. Our `SgfNode` tree (for `compose_enriched_sgf`)
2. Raw `sgfmill_sgf` (for `_embed_teaching_comments` and `_apply_patches` — parse/mutate/serialize)

Both must be replaced with KaTrain's `SGFNode` which supports native mutation + `sgf()` serialization.

---

## 4. Type Mapping: Lab SgfNode → KaTrain SGFNode

| Current (Lab) | KaTrain Equivalent | Notes |
|---------------|-------------------|-------|
| `SgfNode.properties: dict[str, list[str]]` | `SGFNode.properties: defaultdict(list)` | **Compatible** — both list-valued |
| `SgfNode.move → (Color, str) \| None` | `SGFNode.move → Move \| None` | **Breaking** — tuple vs object. Move has `.player`, `.sgf()`, `.gtp()`, `.coords`, `.is_pass` |
| `SgfNode.comment` | `SGFNode.get_property("C")` | Requires property lookup |
| `SgfNode.get(key)` | `SGFNode.get_property(key)` | Name change only |
| `SgfNode.get_all(key)` | `SGFNode.get_list_property(key)` | Name change only |
| `SgfNode.children` | `SGFNode.children` | **Same** |
| `SgfNode.parent` | `SGFNode.parent` | **Same** |

---

## 5. Type Mapping: Backend SGFGame/SolutionNode → KaTrain SGFNode

| Current (Backend) | KaTrain Equivalent | Notes |
|-------------------|-------------------|-------|
| `SGFGame.board_size: int` | `SGFNode.board_size: (int, int)` | Tuple vs int — wrapper needed |
| `SGFGame.player_to_move: Color` | `SGFNode.initial_player: str` | Enum vs string — wrapper |
| `SGFGame.black_stones: list[Point]` | `SGFNode._expanded_placements("B")` | Different extraction |
| `SGFGame.white_stones: list[Point]` | `SGFNode._expanded_placements("W")` | Different extraction |
| `SGFGame.solution_tree: SolutionNode` | `SGFNode.children` | Wrapper converts children |
| `SGFGame.metadata: dict[str, Any]` | `SGFNode.properties` | Extract specific keys |
| `SGFGame.yengo_props: YenGoProperties` | N/A | **Must keep** — YenGo-specific |
| `SGFGame.raw_sgf: str` | `SGFNode.sgf()` | Method call vs stored string |
| `SGFGame.root_comment: str` | `SGFNode.get_property("C")` | Property lookup |
| `SolutionNode.move: Point` | `SGFNode.move: Move` | Type change |
| `SolutionNode.color: Color` | `SGFNode.move.player: str` | Nested access |
| `SolutionNode.is_correct: bool` | N/A | **Must add** via correctness inference |
| `parse_root_properties_only()` | N/A | **Must keep** — performance optimization |

---

## 6. chardet Dependency

`chardet` is used only in `SGF.parse_file()` for encoding auto-detection. Neither subsystem uses file-based parsing:
- Enrichment lab: `parse_sgf(sgf_text: str)` — string input
- Backend: `parse_sgf(content: str)` — string input

**Conclusion**: Strip `parse_file()`, `parse_gib()`, `parse_ngf()` (multi-format parsers that read files). Keep only `SGF.parse_sgf()` (string-based).

---

## 7. Property Normalization

KaTrain's `add_list_property()` strips lowercase: `re.sub("[a-z]", "", property)`. This handles old SGF compat (`SiZe` → `SZ`).

No non-standard property names found in test fixtures across the project. Safe to adopt.

---

## 8. Correctness Inference Integration

| Subsystem | Current Source | Integration Point |
|-----------|---------------|-------------------|
| Enrichment Lab | `tools/core/sgf_correctness.py` (imported via importlib spec loading) | Will be called from the thin wrapper's tsumego analysis functions |
| Backend | `backend/puzzle_manager/core/correctness.py` | Will be called from the `SGFGame` construction wrapper |

Both need `infer_correctness(comment: str, props: dict[str, str])`. KaTrain `SGFNode.properties` is `dict[str, list[str]]`. Flattening: `{k: v[0] for k, v in props.items() if v}`.

**Conclusion**: Mechanical change. Both correctness modules remain as-is; only the calling site in the wrapper needs a dict flattening step.

---

## Summary

| Decision Point | Recommendation |
|----------------|----------------|
| What to copy from KaTrain | `Move`, `SGFNode`, `SGF.parse_sgf()`, `SGF.__init__()`, `SGF._parse_branch()` |
| What to strip | `parse_file()`, `parse_gib()`, `parse_ngf()`, `chardet` import, `place_handicap_stones()` (optional) |
| Backend integration | Keep `SGFGame`/`SolutionNode`/`YenGoProperties` facade; replace internal `SGFParser` with KaTrain |
| Lab integration | Replace `SgfNode` with KaTrain `SGFNode`; move tsumego-specific functions to wrapper |
| Highest-risk area | `sgf_enricher.py` — uses dual parser APIs (sgfmill + SgfNode), both must migrate |
| Test strategy | Backend: run `pytest -m "not (cli or slow)"` (~1000 tests). Lab: run full test suite |
