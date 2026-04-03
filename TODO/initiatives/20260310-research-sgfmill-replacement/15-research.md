# Research Brief: sgfmill Replacement Complexity Assessment

**Initiative**: `20260310-research-sgfmill-replacement`
**Date**: 2026-03-10
**Researcher**: Feature-Researcher agent

---

## 1. Research Question and Boundaries

**Question**: Is replacing sgfmill with native code in the enrichment lab feasible at low/medium complexity, or does it present a fundamental capability gap?

**Scope**: Two files in `tools/puzzle-enrichment-lab/`:
- `analyzers/sgf_parser.py` (346 lines) — SGF parsing, tree traversal, composition
- `analyzers/sgf_enricher.py` (414 lines) — enrichment application (root patches, refutation branches, teaching comment embedding)

**Out of scope**: `backend/puzzle_manager/`, `tools/core/` (these are reference implementations, not subjects of change).

---

## 2. Internal Code Evidence

### 2.1 sgfmill API Calls in `analyzers/sgf_parser.py`

| ID  | Call site (line) | API used | Purpose |
|-----|-----------------|----------|---------|
| P-1 | 17 | `from sgfmill import sgf as sgfmill_sgf` | Import |
| P-2 | 80 | `sgfmill_sgf.Sgf_game.from_bytes(sgf_text.encode("utf-8"))` | Parse raw bytes into game object |
| P-3 | 84 | `game.get_root()` | Access root `Tree_node` |
| P-4 | 368 | `sgfmill_node[i]` | Indexed child access |
| P-5 | 368 | `len(sgfmill_node)` | Child count |
| P-6 | 381 | `sgfmill_node.properties()` | Iterate property identifiers |
| P-7 | 382 | `sgfmill_node.get_raw_list(prop_id)` | Get multi-value raw bytes list |

**sgfmill is used exclusively as the parsing substrate in `parse_sgf()`.** After parsing, the entire sgfmill tree is immediately converted to a custom `SgfNode` tree via `_convert_sgfmill_node()` (lines 363–374). All downstream logic operates only on `SgfNode`, never on sgfmill objects.

**Internal `SgfNode` format** (enrichment lab): `properties: dict[str, list[str]]` — preserves multiple values per property as a Python list (e.g., `AB[aa][bb]` → `{"AB": ["aa", "bb"]}`).

### 2.2 sgfmill API Calls in `analyzers/sgf_enricher.py`

| ID  | Call site (line) | API used | Purpose |
|-----|-----------------|----------|---------|
| E-1 | 31 | `from sgfmill import sgf as sgfmill_sgf` | Import |
| E-2 | 221–228 | `node.properties()`, `node.get_raw(color)` | Read move coord from Tree_node |
| E-3 | 232–237 | `"C" in node.properties()`, `node.get_raw("C")`, `node.set_raw("C", ...)` | Append comment text to a node |
| E-4 | 253–276 | `Sgf_game.from_bytes()`, `game.get_root()`, `len(root)`, `root[0]`, `root[i]`, `game.serialise()` | Full parse→mutate→serialize cycle for teaching comment embedding |
| E-5 | 516–525 | `Sgf_game.from_bytes()`, `game.get_root()`, `root_node.set_raw(prop_key, ...)`, `game.serialise()` | Full parse→mutate→serialize cycle for root property patching |

There are **two independent sgfmill usage clusters** in the enricher:
- `_embed_teaching_comments()` (lines 231–276, ~46 lines): parse → navigate children → mutate `C[]` on matching nodes → serialize
- `_apply_patches()` (lines 511–525, ~15 lines): parse → set arbitrary root property bytes → serialize

### 2.3 Native Parser Capabilities (`tools/core/sgf_parser.py`, 461 lines)

| Capability | Available? | Notes |
|------------|:----------:|-------|
| Parse SGF string to tree | ✅ | `parse_sgf(content) -> SgfTree` |
| Traverse children | ✅ | `SgfNode.children: list[SgfNode]` |
| Read properties | ✅ | `node.properties: dict[str, str]` |
| Read typed move / color / comment | ✅ | `node.move`, `node.color`, `node.comment` |
| Multi-value property preservation | ⚠️ | Values **comma-joined** into one string (`AB[aa][bb]` → `"aa,bb"`) |
| Mutate (set_raw) | ❌ | No mutation API |
| Serialize back to SGF string | ❌ | Not in this file |

### 2.4 Native Builder Capabilities (`tools/core/sgf_builder.py`, 485 lines)

| Capability | Available? | Notes |
|------------|:----------:|-------|
| Serialize SgfTree to SGF string | ✅ | `SGFBuilder.build()` |
| Round-trip from parsed SgfTree | ✅ | `SGFBuilder.from_tree()` |
| Preserve arbitrary move-node properties | ✅ | Round-trip mode in `_build_node()` |
| Set arbitrary root property by key | ❌ | Root props handled via typed fields only (`yengo_props`, `metadata`) |
| Inline string-based property injection | ❌ | No `set_raw()` API |

### 2.5 Critical Format Mismatch

The enrichment lab's `SgfNode.properties` is `dict[str, list[str]]`. The `tools/core` `SgfNode.properties` is `dict[str, str]` (multi-values comma-joined).

The enrichment lab's `_compose_node()` (lines 393–418) iterates properties treating each value as a list: `"".join(f"[{val}]" for val in values)`. This is incompatible with `tools/core` output without an adapter.

---

## 3. External References

| ID  | Reference | Relevance |
|-----|-----------|-----------|
| X-1 | [sgfmill PyPI](https://pypi.org/project/sgfmill/) — stable, maintained, MIT license | Current dependency; MIT permits unrestricted commercial/open-source use |
| X-2 | SGF standard (FF[4], [SGF specification](https://www.red-bean.com/sgf/)) | Defines multi-value properties (e.g., `AB[aa][bb]`) that must be preserved |
| X-3 | `backend/puzzle_manager/core/sgf_parser.py` — hand-rolled recursive descent | Proven alternative approach; same character-by-character design as `tools/core` |
| X-4 | `tools/core/sgf_parser.py` (internal, this repo) — 461-line standalone port | Nearest candidate for replacement; already used in other tools |

---

## 4. Candidate Adaptations

### Candidate A: Thin Adapter over `tools/core/sgf_parser`

Replace sgfmill in `parse_sgf()` with a call to `tools/core/sgf_parser.parse_sgf()`, then write a 30-line adapter that converts `SgfTree`/`SgfNode` (comma-joined properties) to the enrichment lab's `SgfNode` (list-valued properties).

| Aspect | Detail |
|--------|--------|
| Lines removed | ~35 (sgfmill adapter + `_convert_sgfmill_node` + `_extract_sgfmill_properties`) |
| Lines added | ~30 (adapter), no new parser code |
| Risk | Multi-value properties (AB, AW, LB) must be split on comma; assumes no commas inside coord values (safe for SGF coords, risky for LB label text) |
| Effort | ~1 hour |

### Candidate B: Direct rewrite of enricher mutation functions

Replace `_embed_teaching_comments()` and `_apply_patches()` in `sgf_enricher.py` to use `parse_sgf()` + direct `SgfNode.properties` dict mutation + `compose_enriched_sgf()` instead of sgfmill's parse-mutate-serialize cycle.

| Aspect | Detail |
|--------|--------|
| Lines removed | ~61 (the two functions + helpers `_get_node_move_coord`, `_append_node_comment`) |
| Lines added | ~45 (rewritten using our own SgfNode API) |
| Risk | Low — the enrichment lab already has working `compose_enriched_sgf()` for this purpose |
| Effort | ~1.5 hours |

### Candidate C: Port a minimal multi-value parser directly into `sgf_parser.py`

Write a self-contained ~80-line recursive descent parser directly inside `analyzers/sgf_parser.py` that produces `dict[str, list[str]]` natively, without dependency on sgfmill or tools/core.

| Aspect | Detail |
|--------|--------|
| Lines removed | ~35 (sgfmill adapter) |
| Lines added | ~70–80 (new parser, based on tools/core pattern) |
| Risk | New parser needs thorough testing with edge case SGF files from all 11 external sources |
| Effort | ~3–4 hours |

---

## 5. Risks, License Notes, and Rejection Reasons

| ID  | Risk | Severity | Mitigation |
|-----|------|----------|-----------|
| R-1 | Non-ASCII encoding (CJK in problem comments): sgfmill uses `latin-1`/`utf-8` carefully; native parser uses Python strings throughout | Medium | Verify encoding handling for fixtures from `external-sources/`; existing `test_sgf_parser.py` may not cover CJK |
| R-2 | `game.serialise()` is SGF-spec-compliant; `_compose_node()` is hand-rolled | Low | `_compose_node()` already tested via `test_sgf_enricher.py` regression suite |
| R-3 | Comma-split adapter (Candidate A) breaks LB property labels that contain commas | Medium | LB values (`LB[pm:16]`) don't contain commas; but this is fragile if new annotation types are added |
| R-4 | sgfmill is MIT license — no compliance pressure to remove it | None | No urgency; removal is optional dependency hygiene |
| R-5 | Tests cover the public API (`parse_sgf`, `enrich_sgf`) but not the internal sgfmill adapter functions | Low | Adapter functions (`_convert_sgfmill_node`, `_extract_sgfmill_properties`) have no direct tests; removal is safe |

**Rejection reasons for full removal in one shot**: No fundamental reason to reject, but doing A + B together risks introducing encoding regressions that only surface on real-world fixtures.

---

## 6. Planner Recommendations

1. **Start with Candidate B only (enricher mutation functions)** — This is the highest-value change: removes all mutable sgfmill usage (`set_raw`, `get_raw`) and makes `sgf_enricher.py` fully sgfmill-free. Estimated 40–60 lines changed, low risk, and immediately testable via `test_sgf_enricher.py`.

2. **Follow with Candidate A (thin adapter) to make `sgf_parser.py` sgfmill-free** — After B is validated, replace the sgfmill parsing substrate with a thin adapter over `tools/core/sgf_parser.py`. Risk is the LB comma edge case (R-3), which should be validated against fixture files before merging.

3. **Candidate C (full port) is not recommended unless Candidate A fails** — The thin adapter is simpler and leverages an already-tested component. A from-scratch parser in the enrichment lab would duplicate `tools/core/sgf_parser.py` unnecessarily (YAGNI / DRY violations).

4. **Do not remove sgfmill from `requirements.txt` until both A and B are validated** — The backend pipeline also uses sgfmill; this is a lab-local cleanup only.

---

## 7. Complexity Verdict

| Metric | Value |
|--------|-------|
| Total sgfmill API call sites | 12 (5 in parser, 7 in enricher) |
| Lines to remove | ~96 |
| Lines to add/modify | ~75 |
| **Net lines changed** | **~120–150** |
| **Complexity verdict** | **MEDIUM** (50–200 lines, some custom adaptation needed, no fundamental capability gap) |
| **Recommendation** | **Replace** — feasible in two phases: B first (enricher mutation), then A (parser substrate) |

---

## Handoff

- `research_completed`: true
- `initiative_path`: `TODO/initiatives/20260310-research-sgfmill-replacement/`
- `artifact`: `15-research.md`
- `top_recommendations`:
  1. Phase 1 — Rewrite `_embed_teaching_comments` + `_apply_patches` to use native `SgfNode` mutation + `compose_enriched_sgf` (Candidate B, ~60 lines changed)
  2. Phase 2 — Thin adapter over `tools/core/sgf_parser` to remove sgfmill from `parse_sgf()` (Candidate A, ~65 lines changed)
  3. Validate both phases against CJK-comment fixtures before removing sgfmill import
  4. Keep sgfmill in `requirements.txt` until both phases are green
- `open_questions`:
  - Q1: Is there a test fixture with non-ASCII (CJK) content in `tests/fixtures/`? If not, should one be added before this work?
  - Q2: Is sgfmill being removed from `backend/puzzle_manager` dependencies too, or only from the enrichment lab?
- `post_research_confidence_score`: 88
- `post_research_risk_level`: low
