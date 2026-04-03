# Options — KaTrain SGF Parser Swap

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Last Updated**: 2026-03-13

---

## sgf_enricher.py Integration Proof (RC-2 Mandate)

Before comparing options, we validate that KaTrain's `SGFNode` can replace both sgfmill clusters:

### Cluster 1: `_embed_teaching_comments` (parse → navigate → mutate C[] → serialize)

| sgfmill API | KaTrain Equivalent | Compatible? |
|-------------|-------------------|-------------|
| `Sgf_game.from_bytes(text.encode("utf-8"))` | `SGF.parse_sgf(text)` → returns root `SGFNode` | ✅ |
| `game.get_root()` → root node | `SGF.parse_sgf()` already returns root | ✅ |
| `len(root)` → child count | `len(root.children)` | ✅ |
| `root[0]` → first child | `root.children[0]` | ✅ |
| `root[i]` → i-th child | `root.children[i]` | ✅ |
| `color in node.properties()` → check move | `color in node.properties` (defaultdict) | ✅ |
| `node.get_raw(color).decode("utf-8")` → move coord | `node.get_property(color)` | ✅ |
| `node.get_raw("C").decode("utf-8")` → comment | `node.get_property("C", "")` | ✅ |
| `node.set_raw("C", text.encode("utf-8"))` → write comment | `node.set_property("C", text)` | ✅ |
| `game.serialise().decode("utf-8")` → output SGF | `root.sgf()` | ✅ |

**Verdict**: Full 1:1 mapping. KaTrain's `SGFNode` handles all mutation operations natively.

### Cluster 2: `_apply_patches` (parse → set root props → serialize)

| sgfmill API | KaTrain Equivalent | Compatible? |
|-------------|-------------------|-------------|
| `Sgf_game.from_bytes(text.encode("utf-8"))` | `SGF.parse_sgf(text)` | ✅ |
| `root_node.set_raw(key, value.encode("latin-1"))` | `root.set_property(key, value)` | ✅ |
| `game.serialise().decode("latin-1")` | `root.sgf()` | ✅ |

**Verdict**: Direct replacement. KaTrain's string-based API is simpler than sgfmill's byte-based API.

---

## Option Comparison

### OPT-1: Full KaTrain Adoption — Replace Core Types

**Approach**: Copy KaTrain's parser (stripped of chardet/file parsers) into `core/sgf_parser.py` in both subsystems. In the enrichment lab, replace `SgfNode` with KaTrain's `SGFNode` and `Move` everywhere. In backend, replace internal `SGFParser` class with KaTrain but keep `SGFGame`/`SolutionNode`/`YenGoProperties` as a thin conversion layer.

| Aspect | Detail |
|--------|--------|
| **Lab changes** | New `core/sgf_parser.py` (KaTrain copy, ~400 lines). New `core/tsumego_analysis.py` (thin wrapper, ~200 lines) with extract_position, extract_correct_first_move, etc. Delete old `analyzers/sgf_parser.py`. Update ~10 consumers: change `SgfNode` → `SGFNode`, `.move` tuple → `Move` object, `.get()` → `.get_property()`, `.get_all()` → `.get_list_property()`. Rewrite `sgf_enricher.py` to use KaTrain `SGFNode` mutation + `sgf()`. |
| **Backend changes** | New `core/katrain_sgf_parser.py` (KaTrain copy). Rewrite `core/sgf_parser.py` internals: `SGFParser.__init__`/`parse()`/`_parse_game_tree` calls KaTrain's `SGF.parse_sgf()` then converts `SGFNode` tree → `SGFGame`/`SolutionNode`. All consumers unchanged (facade maintained). |
| **Benefits** | KaTrain fidelity maximized (Q4). Future KaTrain updates drop in. No sgfmill anywhere. Clean separation: parsing (KaTrain) vs tsumego analysis (wrapper). |
| **Drawbacks** | ~10 consumer file updates in lab. `.move` type change is pervasive. |
| **Risks** | `.move` type migration catches — some tests may use tuple unpacking `color, coord = node.move`. Medium risk, caught by type errors at test time. |
| **Complexity** | Medium-High. ~18 files total across both subsystems. |
| **Test impact** | Lab: all tests need re-run. Backend: `pytest -m "not (cli or slow)"` covers facade. |
| **Rollback** | Per-subsystem phased commits. Each independently revertible. |

### OPT-2: KaTrain Core + Compatibility Shim

**Approach**: Same KaTrain copy into `core/`, but instead of updating all lab consumers, provide a backward-compatible shim that wraps KaTrain `SGFNode` as the old `SgfNode` interface. Backend same as OPT-1 (facade already exists).

| Aspect | Detail |
|--------|--------|
| **Lab changes** | New `core/sgf_parser.py` (KaTrain). New `core/tsumego_analysis.py` (wrapper). New `analyzers/sgf_parser.py` **rewritten as shim** — same function signatures (`parse_sgf`, `extract_position`, etc.) but internally delegates to KaTrain + wrapper. Consumer files **unchanged**. |
| **Backend changes** | Same as OPT-1. |
| **Benefits** | Zero consumer file changes in lab. Lower blast radius. Faster to implement. |
| **Drawbacks** | Permanent translation layer (shim) contradicts Q1 ("no backward compat") and Q4 ("adopt KaTrain fully"). The shim would wrap KaTrain's `Move` back into old `(Color, str)` tuples — undoing the type richness we want. Tech debt from day 1. |
| **Risks** | Shim becomes permanent. Type mismatch bugs hidden by translation. Future feature work still touches old types. |
| **Complexity** | Medium. ~8 files total. |
| **Test impact** | Lab: most tests unchanged (shim preserves interface). Backend: same as OPT-1. |
| **Rollback** | Same phased approach. |

### OPT-3: KaTrain in Lab Only — Backend Deferred

**Approach**: Full KaTrain adoption in enrichment lab (same as OPT-1 lab side). Backend keeps its hand-rolled parser unchanged. Backend migration deferred to a future initiative.

| Aspect | Detail |
|--------|--------|
| **Lab changes** | Same as OPT-1. |
| **Backend changes** | None. |
| **Benefits** | Halves the scope. Lab gets full KaTrain benefits now. Backend (which doesn't use sgfmill) has less urgency. |
| **Drawbacks** | Contradicts Q2 ("include both subsystems"). Two different parser architectures persist. Future backend migration becomes a separate initiative. Backend misses out on KaTrain's richer `Move` type and `play()` API. |
| **Risks** | Backend migration may be indefinitely deferred. Divergence grows over time. |
| **Complexity** | Medium. ~14 files (lab only). |
| **Test impact** | Lab tests only. |
| **Rollback** | Single-subsystem revert. |

---

## Evaluation Matrix

| Criterion | OPT-1 (Full Adoption) | OPT-2 (Compat Shim) | OPT-3 (Lab Only) |
|-----------|:---------------------:|:--------------------:|:-----------------:|
| KaTrain fidelity (Q4) | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ (lab) / ❌ (backend) |
| Scope coverage (Q2) | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| No backward compat (Q1) | ⭐⭐⭐ | ⭐ (violates Q1) | ⭐⭐⭐ |
| Blast radius | Medium-High | Low | Medium |
| Future maintenance | Best | Worst (shim tech debt) | Split (two architectures) |
| Implementation effort | ~18 files | ~8 files | ~14 files |
| Architecture compliance | ✅ Clean | ⚠️ Translation layer | ⚠️ Asymmetric |
| sgfmill removal | ✅ Full | ✅ Full | ✅ Full (lab only) |
| Rollback safety | Per-subsystem phased | Per-subsystem phased | Single subsystem |

---

## Recommendation

**OPT-1 (Full KaTrain Adoption)** is the recommended option.

**Rationale**: It directly fulfills all clarification decisions (Q1-Q7), maximizes KaTrain fidelity for future drop-in updates, and avoids tech debt from translation layers or deferred migrations. The extra ~4 files of consumer updates (vs OPT-2) are mechanical find-and-replace operations caught by test failures. The backend facade strategy shields 15+ consumers while still gaining KaTrain internally. The per-subsystem phased commit strategy provides safe rollback.

OPT-2 is rejected because it contradicts Q1 and Q4 and creates permanent tech debt. OPT-3 is rejected because it contradicts Q2.
