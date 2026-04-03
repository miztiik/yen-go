# Analysis: Collection Edition Detection

**Last Updated**: 2026-03-30  
**Planning Confidence Score**: 92  
**Risk Level**: low

---

## 1. Coverage Map

| Charter Goal | Plan Section | Task IDs | Status |
|-------------|-------------|----------|--------|
| G1: Cross-source puzzles not rejected | §3 (dedup bypass) | T5, T6, T7 | ✅ |
| G2: User can choose edition | §5 (frontend) | T15, T16, T17, T18 | ✅ |
| G3: Per-source ordering preserved | §4 (edition detection) | T11, T12, T14 | ✅ |
| G4: Automatic detection, no config | §2 + §4 (collection_slug + GROUP BY) | T1-T3, T11 | ✅ |

## 2. Comparison with Superseded Initiative

| Dimension | Old (`20260330-1400`) | New (this) |
|-----------|:---:|:---:|
| Tasks | 32 | **18** |
| New abstractions | 6 | **2** (`collection_slug` column, `create_editions()` function) |
| Config fields | 2 (`edition_policy`, `multi_source_policy`) | **0** |
| SRP violations | 1 god function (10 responsibilities) | **0** (single-purpose `create_editions()`) |
| Collection-type branching | Yes (author vs technique) | **No** (all types treated identically) |
| Richness scoring | Yes (5-variable formula, uncalibrated) | **No** (deferred to v2) |
| DB schema changes | 0 | **1** (add `collection_slug` column — additive) |

## 3. Findings

| F_ID | Severity | Finding | Resolution |
|------|----------|---------|------------|
| F1 | Medium | `_extract_collection_slug()` returns first slug only. A puzzle in 2+ collections (`YL[a,b]`) only triggers collision detection for slug `a`. | Acceptable for v1. The full `collection_ids` list on PuzzleEntry (from `sgf_to_puzzle_entry()`) handles multi-collection membership at publish. The `collection_slug` column is for collision detection, not membership resolution. |
| F2 | Medium | NULL `collection_slug` on legacy entries. If legacy entries overlap with new entries, collision detection misses them. | Legacy entries were ingested before collection embedding. Re-running `build_content_db()` with the embedder would populate the column. Add a note in docs. |
| F3 | Low | Edition labels `"Edition 1 (N puzzles)"` are functional but generic. | Acceptable for v1. Manual override via `attrs.label` in v1.1. |
| F4 | Low | Progress data keyed by parent `collection_id` becomes orphaned when editions are created. | Documented in EditionPicker UI: "Progress tracked per edition". |

## 4. Ripple Effects

| ID | Direction | Area | Risk | Mitigation | Status |
|----|-----------|------|------|------------|--------|
| RE1 | downstream | Rollback | High | `create_editions()` called by rollback, atomic swap for safety | ✅ |
| RE2 | downstream | Frontend progress | Medium | Document in UI. No migration. | ✅ |
| RE3 | downstream | Daily challenges | None | Daily puzzles selected by level/tag, not collection | ✅ |
| RE4 | upstream | Collection embedder | None | Embedder unchanged. YL[] semantics unchanged. | ✅ |
| RE5 | lateral | Enrichment lab | None | Operates on individual SGFs. Not affected. | ✅ |
| RE6 | downstream | Publish log search | Low | Synthetic editions not in publish logs. Document. | ✅ |

## 5. What We Decided NOT to Do (and Why)

| Decision | Why Not |
|----------|---------|
| Auto-best / richness scoring | No calibration data. YAGNI. All types get editions for v1. |
| Collection-type-specific strategies | KISS. One rule for all types: 2+ sources → editions. |
| Config fields (`edition_policy` etc.) | Detection is data-driven from content DB. No manual annotation needed. |
| Solution tree merging | Go-domain correctness risk. Different analysis depths = contradictory moves. |
| Manual preferred_source per collection | Doesn't scale to 500+ collections. |
| SHA-based edition IDs with 10M space + birthday collision math | Kept (simplest deterministic scheme). But removed the overcomplicated analysis. |
| `_generate_edition_label()` with Complete/Classic/500-threshold | Labels are just `"Edition {N} ({count} puzzles)"`. Simple. |

> **See also**:
> - [30-plan.md](30-plan.md) — Technical plan
> - [40-tasks.md](40-tasks.md) — Task decomposition
> - [00-charter.md](00-charter.md) — Goals and constraints
