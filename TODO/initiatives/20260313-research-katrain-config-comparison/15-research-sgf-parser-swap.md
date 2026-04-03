# Research Brief: KaTrain SGF Parser Swap — Blast Radius & Type Mapping

**Last Updated:** 2026-03-13
**Initiative:** `20260313-research-katrain-config-comparison`
**Research Question:** What is the blast radius, dependency impact, and type mapping for replacing both the enrichment lab's sgfmill-based parser and the backend's hand-rolled SGFParser with KaTrain's `sgf_parser.py`?

---

## 1. KaTrain Dependency Audit

**Source:** [katrain/core/sgf_parser.py](https://github.com/sanderland/katrain/blob/master/katrain/core/sgf_parser.py)

| R-1 | Import | Stdlib? | Used In | Notes |
|-----|--------|---------|---------|-------|
| R-1.1 | `copy` | ✅ stdlib | `sgf_properties()` deep-copies properties | No pip dep |
| R-1.2 | `chardet` | ❌ **PyPI** | `parse_file()` only — encoding detection for file reads | **Only dep** |
| R-1.3 | `math` | ✅ stdlib | `place_handicap_stones()` — `ceil`, `sqrt`, `floor` | No pip dep |
| R-1.4 | `re` | ✅ stdlib | Property parsing, value escaping, SGF regex | No pip dep |
| R-1.5 | `collections.defaultdict` | ✅ stdlib | `SGFNode.properties` storage | No pip dep |
| R-1.6 | `typing` | ✅ stdlib | Type annotations only | No pip dep |

**Conclusion:** KaTrain's `sgf_parser.py` has exactly **one external dependency: `chardet`**. It is used exclusively inside `SGF.parse_file()`. Both Yen-Go subsystems read SGF as strings (not files), so `parse_file()` is unused. Two options:
1. Strip `import chardet` and `parse_file()` from the copied file (recommended — both subsystems call `parse_sgf(string)`)
2. Add conditional import: `try: import chardet except ImportError: chardet = None`

**Risk:** Low. `chardet` is not needed for any Yen-Go code path.

---

## 2. Backend Consumer Blast Radius

Every consumer of `backend/puzzle_manager/core/sgf_parser.py` was analyzed for which attributes/methods of `SGFGame` and `SolutionNode` they actually use.

### 2a. `SGFGame` consumers

| R-2 | Consumer File | SGFGame Properties Used | Notes |
|-----|---------------|------------------------|-------|
| R-2.1 | `core/classifier.py` | `.solution_tree`, `.board_size`, `.black_stones`, `.white_stones` | `.solution_tree.count_variations()`, `len(black/white_stones)` |
| R-2.2 | `core/complexity.py` | `.solution_tree`, `.has_solution`, `.black_stones`, `.white_stones` | Walks tree, `is_unique_first_move()` |
| R-2.3 | `core/content_classifier.py` | `.has_solution`, `.black_stones`, `.white_stones`, `.player_to_move`, `.solution_tree.children`, `.board_size`, `.root_comment` | Board construction, liberty analysis |
| R-2.4 | `core/quality.py` | `.solution_tree`, `.has_solution` | Traverses tree for refutations/comments |
| R-2.5 | `stages/analyze.py` | `.yengo_props` (full: `.pipeline_meta`, `.level_slug`, `.level`, `.tags`, `.collections`, `.quality`, `.complexity`, `.hint_texts`), `.root_comment`, `.has_solution`, `.solution_tree` | Heaviest consumer — reads all YenGo properties |
| R-2.6 | `stages/publish.py` | `.yengo_props` (`.pipeline_meta`, `.run_id`, `.level`, `.quality`, `.tags`, `.collections`, `.complexity`, `.source`), `.metadata["GN"]` | Builds compact entries |
| R-2.7 | `stages/ingest.py` | Return value of `parse_sgf()` only — `game` is used for validation downstream, not accessed directly in ingest | Calls `parse_sgf(content)` |
| R-2.8 | `adapters/local/adapter.py` | Return value of `parse_sgf()` — `game` used for stone extraction downstream | Calls `parse_sgf(content)` |
| R-2.9 | `core/puzzle_validator.py` | `.solution_tree`, `.board_size`, `.black_stones`, `.white_stones`, `.has_solution` | Calls `parse_sgf(content)` |
| R-2.10 | `core/enrichment/__init__.py` | `.metadata["GN"]`, `.black_stones`, `.white_stones`, `.board_size`, `.yengo_props.tags`, `.has_solution`, `.solution_tree` | Hint generation, move order, refutation |
| R-2.11 | `inventory/reconcile.py` | Uses `parse_root_properties_only()` — returns `dict[str, str]`, **not** SGFGame | Metadata-only fast path |

### 2b. `SolutionNode` consumers

| R-3 | Consumer File | SolutionNode Properties Used | Notes |
|-----|---------------|------------------------------|-------|
| R-3.1 | `core/classifier.py` | `.children`, `.move` (traversal) | Main-line depth calculation |
| R-3.2 | `core/complexity.py` | `.children`, `.is_correct`, `.move` | Depth, node count, avg refutation depth |
| R-3.3 | `core/quality.py` | `.children`, `.is_correct`, `.comment`, `.move` | Refutation counting, comment analysis |
| R-3.4 | `core/enrichment/hints.py` | `.children`, `.is_correct`, `.move`, `.comment` | First correct move, solution depth, refutation count |
| R-3.5 | `core/enrichment/ko.py` | `.children`, `.comment` | Ko detection from comments |
| R-3.6 | `core/enrichment/move_order.py` | `.children`, `.is_correct`, `.comment`, `.move` | Miai/flexible detection |
| R-3.7 | `core/enrichment/refutation.py` | `.children`, `.is_correct`, `.move` | Extract wrong first moves |
| R-3.8 | `core/enrichment/solution_tagger.py` | `.children`, `.is_correct`, `.move` | Technique inference |
| R-3.9 | `core/content_classifier.py` | `.children` (via `game.solution_tree.children`) | Trivial capture detection |

### 2c. Other exports

| R-4 | Export | Consumers | Notes |
|-----|--------|-----------|-------|
| R-4.1 | `parse_sgf(content: str) → SGFGame` | 6 files (ingest, analyze, publish, adapter, validator, test files) | Primary entry point |
| R-4.2 | `parse_root_properties_only(content: str) → dict` | `inventory/reconcile.py` | Fast metadata-only path |
| R-4.3 | `YenGoProperties` (dataclass) | Accessed via `game.yengo_props` | analyze.py, publish.py, enrichment/__init__.py |

**Conclusion:** The adapter layer must provide:
- **`SGFGame`-compatible wrapper** exposing: `board_size`, `black_stones`, `white_stones`, `player_to_move`, `solution_tree`, `metadata` (dict), `yengo_props` (YenGoProperties), `raw_sgf`, `root_comment`, `has_solution` (property)
- **`SolutionNode`-compatible wrapper** exposing: `move` (Point|None), `color` (Color|None), `comment` (str), `is_correct` (bool), `children` (list), `count_variations()`, `get_main_line()`, `add_child()`, `properties` (dict)
- **`parse_root_properties_only()`** — fast path, returns `dict[str, str]`
- **`YenGoProperties.from_sgf_props()`** — unchanged (pure data mapping)

---

## 3. Enrichment Lab Consumer Blast Radius

The lab's `SgfNode` is used via the functions exported from `analyzers/sgf_parser.py`.

### 3a. Direct `SgfNode` attribute usage

| R-5 | Consumer File | SgfNode Members Used | Notes |
|-----|---------------|----------------------|-------|
| R-5.1 | `analyzers/query_builder.py` | `parse_sgf()`, `extract_position()`, `extract_correct_first_move_color()` | Uses high-level functions, not raw SgfNode |
| R-5.2 | `analyzers/sgf_enricher.py` | `.children`, `.get("WV")`, `.get("BM")`, `.get("C")`, `.get("PL")`, `.get("YR")`, `.get("YG")`, `.get("YX")`, `.get("YQ")`, `.get("YT")`, `.get("YH")`, `.properties` (dict membership test) | **Phase 1-2 uses SgfNode**. Phase 3 uses **raw sgfmill TreeNode** (`node.properties()` method, `node.get_raw()`, `node.set_raw()`, `node[0]` child indexing) |
| R-5.3 | `analyzers/solve_position.py` | `SgfNode(properties=...)`, `.parent`, `.children` (append), `.move`, `.comment`, `.get(prop)`, `.properties` | Creates new SgfNode instances for AI-solve tree building |
| R-5.4 | `analyzers/stages/parse_stage.py` | `parse_sgf()`, `extract_position()`, `extract_correct_first_move()` | High-level functions only |
| R-5.5 | `analyzers/stages/difficulty_stage.py` | `count_solution_branches()` | High-level function only |
| R-5.6 | `analyzers/ascii_board.py` | `parse_sgf()`, `extract_position()` | High-level functions only |
| R-5.7 | `analyzers/tsumego_frame_gp.py` | `parse_sgf()`, `extract_position()` | High-level functions only |

### 3b. Exported functions from `analyzers/sgf_parser.py`

| R-6 | Function | Used By | SgfNode Members It Accesses |
|-----|----------|---------|----------------------------|
| R-6.1 | `parse_sgf(str) → SgfNode` | query_builder, sgf_enricher, stages, ascii_board, tests | sgfmill → SgfNode conversion |
| R-6.2 | `extract_position(root, ...)` | query_builder, stages/parse, ascii_board, scripts | `.get("SZ")`, `.get("PL")`, `.get_all("AB")`, `.get_all("AW")`, `.get("KM")` |
| R-6.3 | `extract_correct_first_move(root)` | stages/parse, tests | `.children`, `.move` |
| R-6.4 | `extract_correct_first_move_color(root)` | query_builder | `.children`, `.move` |
| R-6.5 | `extract_wrong_move_branches(root)` | tests | `.children`, `.move`, `.comment`, `.properties` |
| R-6.6 | `extract_solution_tree_moves(root)` | sgf_enricher | `.children`, `.move` |
| R-6.7 | `count_solution_branches(root)` | stages/difficulty | `.children` |
| R-6.8 | `compose_enriched_sgf(root, ...)` | sgf_enricher | `.properties`, `.children` |

### 3c. Critical finding: Dual-parser usage in `sgf_enricher.py`

The enricher uses **two different SGF object models**:
- **Phases 1-2** (refutation detection, property patching): Uses `SgfNode` from `analyzers/sgf_parser.py` — `.get()`, `.children`, `.properties` (dict)
- **Phase 3** (teaching comment embedding): Re-parses SGF with **raw sgfmill** — `sgfmill_sgf.Sgf_game.from_bytes()`, then uses sgfmill TreeNode API: `node.properties()` (method returning set), `node.get_raw()`, `node.set_raw()`, `node[0]` (child indexing)

**Implication:** Replacing sgfmill means Phase 3 of sgf_enricher.py also needs a rewrite. KaTrain's `SGFNode` uses `set_property()`/`get_property()` instead of `get_raw()`/`set_raw()`.

**Conclusion:** The lab blast radius is narrower than the backend's. Most consumers use high-level functions that encapsulate `SgfNode` access. The two critical consumers are `sgf_enricher.py` (dual-node-model) and `solve_position.py` (constructs `SgfNode` instances).

---

## 4. KaTrain `SGFNode` vs Lab `SgfNode` Type Mapping

| R-7 | Lab `SgfNode` | KaTrain `SGFNode` | Compatible? | Adapter Needed? |
|-----|---------------|-------------------|-------------|-----------------|
| R-7.1 | `.properties` → `dict[str, list[str]]` | `.properties` → `defaultdict(list)` | ✅ Structurally identical (dict of lists) | No — `defaultdict` is a dict subclass |
| R-7.2 | `.children` → `list[SgfNode]` | `.children` → `list[SGFNode]` | ✅ Same structure | No |
| R-7.3 | `.parent` → `SgfNode \| None` | `.parent` → `SGFNode \| None` (property with setter) | ✅ Same semantics | No — but KaTrain auto-appends to parent.children on `__init__` |
| R-7.4 | `.move` → `tuple[Color, str] \| None` | `.move` → `Move \| None` | ❌ **Different types** | **Yes** — Lab returns `(Color, sgf_coord_str)`, KaTrain returns `Move` object with `.player`, `.coords`, `.sgf()` |
| R-7.5 | `.comment` → `str` (property) | No direct `.comment` property | ❌ **Missing** | **Yes** — Use `get_property("C", "")` |
| R-7.6 | `.get(key, default="") → str` | `.get_property(key, default=None) → Any` | ⚠️ Signature differs | **Thin wrapper** — Lab's `.get()` returns first value; KaTrain's `.get_property()` returns first value. Default behavior differs slightly (lab: `""`, KaTrain: `None`) |
| R-7.7 | `.get_all(key) → list[str]` | `.get_list_property(key, default=None) → list` | ⚠️ Signature differs | **Thin wrapper** — Lab returns `[]` for missing; KaTrain returns `None` for missing |
| R-7.8 | `SgfNode(properties={...})` construction | `SGFNode(parent=None, properties={...})` | ⚠️ Side effect | **Careful** — KaTrain's `__init__` auto-appends to parent.children; lab does not |

**Critical difference: `.move` property**
- Lab: `(Color.BLACK, "cd")` — a tuple of `(Color enum, sgf_coord_string)`
- KaTrain: `Move` object with `.player` ("B"/"W" string), `.coords` (int tuple in display coords), `.sgf(board_size)` method, `.is_pass`
- Every consumer of `.move` must be adapted. In the lab, `move[0]` gives color, `move[1]` gives SGF coord.

---

## 5. KaTrain `SGFNode` vs Backend `SGFGame`/`SolutionNode` Type Mapping

### 5a. `SGFGame` ↔ KaTrain `SGFNode` (root)

| R-8 | Backend `SGFGame` | KaTrain `SGFNode` | Mapping Strategy |
|-----|-------------------|-------------------|-----------------|
| R-8.1 | `.board_size` → `int` | `.board_size` → `tuple[int, int]` | Thin wrapper: `root.board_size[0]` (assuming square boards; Yen-Go uses square only) |
| R-8.2 | `.player_to_move` → `Color` enum | `.initial_player` → `str` ("B"/"W") | Wrapper: `Color.BLACK if root.initial_player == "B" else Color.WHITE` |
| R-8.3 | `.black_stones` → `list[Point]` | `.placements` → `list[Move]` filtered by `move.player == "B"` | Wrapper: filter + convert `Move.coords` to `Point` |
| R-8.4 | `.white_stones` → `list[Point]` | `.placements` → `list[Move]` filtered by `move.player == "W"` | Wrapper: filter + convert `Move.coords` to `Point` |
| R-8.5 | `.solution_tree` → `SolutionNode` | `.children` → `list[SGFNode]` | **Heaviest mapping** — must convert KaTrain tree to `SolutionNode` tree recursively |
| R-8.6 | `.metadata` → `dict[str, Any]` | `.properties` → `defaultdict(list)` | Wrapper: extract `GN`, `PB`, `PW`, etc. from properties, apply property policy filter |
| R-8.7 | `.yengo_props` → `YenGoProperties` | No equivalent | **Preserved as-is** — call `YenGoProperties.from_sgf_props()` with flattened properties dict |
| R-8.8 | `.raw_sgf` → `str` | `.sgf()` method | Store original string passed to `parse_sgf()` |
| R-8.9 | `.root_comment` → `str` | `root.get_property("C", "")` | Direct mapping |
| R-8.10 | `.has_solution` → `bool` | `bool(root.children)` | Direct mapping |

### 5b. `SolutionNode` ↔ KaTrain `SGFNode` (tree nodes)

| R-9 | Backend `SolutionNode` | KaTrain `SGFNode` | Mapping Strategy |
|-----|------------------------|-------------------|-----------------|
| R-9.1 | `.move` → `Point \| None` | `.move` → `Move \| None` | Convert: `Point(move.coords[0], board_size - 1 - move.coords[1])` — KaTrain uses display coords (0-indexed, y from bottom) while SGF Point uses `(col, row)` from top |
| R-9.2 | `.color` → `Color \| None` | `.player` → `str` ("B"/"W") | `Color.BLACK if node.player == "B" else Color.WHITE` |
| R-9.3 | `.comment` → `str` | `node.get_property("C", "")` | Direct mapping |
| R-9.4 | `.is_correct` → `bool` | **No equivalent** | ❌ Must be inferred via `infer_correctness()` from `core/correctness.py` — this is the key adapter logic |
| R-9.5 | `.children` → `list[SolutionNode]` | `.children` → `list[SGFNode]` | Recursive tree conversion needed |
| R-9.6 | `.properties` → `dict[str, str]` | `.properties` → `defaultdict(list)` | Flatten: `{k: v[0] for k, v in props.items() if v}` |
| R-9.7 | `.count_variations()` | No equivalent | **Must be re-implemented** as utility function on adapter layer |
| R-9.8 | `.get_main_line()` | No equivalent | **Must be re-implemented** as utility function |
| R-9.9 | `.add_child(node)` | Auto-appended in `__init__` or manual `.children.append()` | Different creation pattern |

**Conclusion:** The `SGFGame` wrapper is medium-thick (10+ properties to map). The `SolutionNode` wrapper is thick because `.is_correct` must be computed during tree conversion by calling `infer_correctness()` — this is the current parser's behavior in `_props_to_node()`. Two viable approaches:
1. **Eager conversion**: Parse with KaTrain, then convert entire tree to `SGFGame`/`SolutionNode` (current backend approach preserved)
2. **Lazy adapter**: Wrap `SGFNode` with property accessors that compute on-demand (more invasive but avoids data duplication)

---

## 6. `chardet` Dependency Analysis

| R-10 | Subsystem | File Read Path | Uses `parse_file()`? | Needs `chardet`? |
|------|-----------|----------------|---------------------|-----------------|
| R-10.1 | Enrichment Lab | Receives SGF as `str` in all code paths (`parse_sgf(sgf_text: str)`) | No | **No** |
| R-10.2 | Backend Pipeline | Reads SGF files with `.read_text(encoding="utf-8")` everywhere (analyze.py L248, publish.py L158, reconcile.py L56, adapters) | No — already decodes to `str` before parsing | **No** |
| R-10.3 | External sources | Local adapter reads with `.read_text(encoding="utf-8")` | No | **No** |

**Conclusion:** Neither subsystem needs `chardet`. Both always pass decoded strings to `parse_sgf()`. The backend explicitly reads with `encoding="utf-8"`. KaTrain's `parse_file()` and `chardet` import can be safely removed from the copied file.

**Recommendation:** Strip `import chardet` and the `parse_file()` classmethod from the copy. Add a comment: `# parse_file() removed — Yen-Go reads SGF as str, not bytes`.

---

## 7. KaTrain's Property Normalization Impact

KaTrain normalizes property names by stripping lowercase letters:

```python
# In SGFNode.add_list_property():
normalized_property = re.sub("[a-z]", "", property)
# "SiZe" → "SZ", "GaMe" → "GM"
```

### 7a. Impact on Yen-Go SGF files

| R-11 | Source | Non-standard Names Found? | Risk |
|------|--------|--------------------------|------|
| R-11.1 | Test fixtures in `backend/puzzle_manager/tests/` | No — all use standard uppercase: `SZ`, `GM`, `FF`, `AB`, `AW`, `B`, `W`, `C`, `PB`, `PW` | None |
| R-11.2 | Test fixtures in `tools/puzzle-enrichment-lab/tests/` | No — all use standard uppercase | None |
| R-11.3 | Published SGF files in `yengo-puzzle-collections/` | All YenGo-produced SGFs use uppercase (schema v13 mandates it) | None |
| R-11.4 | External source SGFs (`external-sources/`) | **Possible** — non-standard SGF files from wild sources may have mixed-case properties (e.g., old `SiZe` format from SGF FF[1]/FF[2] era) | Low — normalization is **beneficial** here |

**Conclusion:** KaTrain's normalization is **safe and beneficial** for Yen-Go. All internal SGFs already use standard uppercase. For external sources, normalization fixes potential compatibility issues with old-format SGFs. No test fixtures need updating.

**⚠️ Important caveat:** KaTrain's normalization strips ALL lowercase letters from property names. This means custom YenGo properties with lowercase letters would be affected. However, all YenGo custom properties (`YV`, `YG`, `YT`, `YH`, `YQ`, `YX`, `YL`, `YM`, `YC`, `YK`, `YO`, `YR`) are already fully uppercase, so **no impact**.

---

## 8. Correctness Inference Integration

### 8a. Current correctness flow

| R-12 | Subsystem | How Correctness is Determined | Source File |
|------|-----------|-------------------------------|-------------|
| R-12.1 | Backend parser | `infer_correctness(comment, props)` called in `SGFParser._props_to_node()` during parse → sets `SolutionNode.is_correct` | `backend/puzzle_manager/core/correctness.py` |
| R-12.2 | Lab parser | `infer_correctness(comment, props)` called in `extract_wrong_move_branches()` for Layer 1-2 detection, plus Layer 3 structural fallback within the same function | `tools/core/sgf_correctness.py` (duplicated from backend) |
| R-12.3 | KaTrain parser | **No correctness inference** — `SGFNode` has no `is_correct` concept | N/A |

### 8b. `infer_correctness()` signature

Both copies have the same signature: `infer_correctness(comment: str | None, properties: dict[str, str]) → bool | None`

The function expects `properties` as `dict[str, str]` (flat). KaTrain's `SGFNode.properties` is `defaultdict(list)` → must be flattened: `{k: v[0] for k, v in node.properties.items() if v}`.

### 8c. Integration options

| R-13 | Option | Description | Pros | Cons |
|------|--------|-------------|------|------|
| R-13.1 | **Eager: during tree conversion** | When converting KaTrain `SGFNode` tree to `SolutionNode` tree, call `infer_correctness()` per node (same as current backend parser) | Preserves current behavior exactly; `SolutionNode.is_correct` populated at parse time | Requires full tree conversion; duplicates what KaTrain already parsed |
| R-13.2 | **Lazy: property on adapter wrapper** | Wrap `SGFNode` with `.is_correct` property that calls `infer_correctness()` on first access | No tree conversion needed; lighter adapter | More complex; cache invalidation if properties change |
| R-13.3 | **Post-parse pass** | Parse with KaTrain, then walk tree once to annotate `._is_correct` on each `SGFNode` | Single pass; can be shared between lab and backend | Monkeypatches KaTrain's class or requires subclass |

**Recommendation:** R-13.1 (eager conversion) for the backend — it already does this and all downstream consumers expect `SolutionNode.is_correct` to be pre-populated. R-13.3 (post-parse annotation) or R-13.2 for the lab where tree structure is lighter.

---

## Planner Recommendations

1. **Strip `chardet` and `parse_file()` from the KaTrain copy.** Zero external dependencies needed. Both subsystems pass decoded strings to `parse_sgf()`. This is a clean no-dependency copy.

2. **Backend: Keep `SGFGame`/`SolutionNode` as the consumer-facing API; implement an eager-conversion adapter.** 15 consumer files depend on `SGFGame` + `SolutionNode` + `YenGoProperties`. Rewriting all consumers is an L4+ change. Instead, `parse_sgf()` should internally call KaTrain's `SGF.parse_sgf()` then convert the result to `SGFGame`/`SolutionNode`. The adapter function replaces `SGFParser` internals only. `parse_root_properties_only()` can use KaTrain's parser with early termination or remain hand-rolled (it's a fast-path optimization).

3. **Lab: Replace `SgfNode` with KaTrain's `SGFNode` directly in `analyzers/sgf_parser.py`, and update the 3 critical consumers.** The lab has fewer consumers and most use high-level functions. The `.move` property difference (tuple vs `Move` object) is the biggest break — update `extract_position()`, `extract_correct_first_move()`, `extract_wrong_move_branches()`, and the `_create_sgf_move_node()` in `solve_position.py`. The `sgf_enricher.py` Phase 3 (teaching comments) currently uses raw sgfmill — must be rewritten to use KaTrain's `set_property()`/`get_property()`.

4. **Correctness inference is safe to wire into both subsystems with minimal changes.** The `infer_correctness()` function just needs a flattened property dict (`{k: v[0] for k, v in props.items()}`). For the backend, it stays in `_props_to_node()` equivalent. For the lab, it stays in `extract_wrong_move_branches()`.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should KaTrain's `Move` class be exposed to lab consumers, or should the adapter preserve the current `(Color, sgf_coord_str)` tuple interface? | A: Expose `Move` directly (simpler copy, but breaks all `.move[0]`/`.move[1]` access) / B: Wrap `.move` to return tuple (preserves consumer code) / C: Migrate consumers to `Move` API | B (wrap) for quick swap, C (migrate) if doing a full rewrite | | ❌ pending |
| Q2 | Should `parse_root_properties_only()` be reimplemented on KaTrain's parser or kept as the current hand-rolled fast-path? | A: Reimplement via KaTrain (drop hand-rolled code) / B: Keep hand-rolled (it's simple and 10-50x faster) | B (keep) — it's 20 lines, battle-tested, and optimized for reconciliation | | ❌ pending |
| Q3 | For the lab's `sgf_enricher.py` Phase 3 (teaching comments), should it re-parse with KaTrain and use `set_property()`, or should a serialization helper be added to the adapter? | A: Re-parse with KaTrain / B: String-level patching (current Phase 2 approach) / C: Add `set_comment()` helper to adapted node | A (re-parse with KaTrain) — aligns with full parser replacement | | ❌ pending |
| Q4 | The KaTrain `SGFNode.__init__` auto-appends to `parent.children`. `solve_position.py` manually appends to `.children`. Should we subclass `SGFNode` to disable auto-append, or update `solve_position.py`? | A: Subclass with no auto-append / B: Update solve_position.py / Other | B — adapt the 3-4 callsites to use KaTrain's constructor pattern | | ❌ pending |

---

## Confidence & Risk

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 82 |
| `post_research_risk_level` | medium |

**Risk rationale:** The dependency audit is clean (low risk). The backend blast radius is well-understood but wide (15+ files, medium risk). The lab's dual-parser in `sgf_enricher.py` (SgfNode + raw sgfmill) is the highest-risk area — it requires two different API migrations in one file. The `.move` type difference is pervasive but mechanical to fix.

---

> **See also:**
> - [Architecture: Backend Pipeline](../../docs/architecture/) — Pipeline stage design
> - [Concepts: SGF Properties](../../docs/concepts/) — Schema v13 property definitions
> - [CLAUDE.md](../../CLAUDE.md) — Project constraints and conventions
