# Clarifications — KaTrain SGF Parser Swap

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Last Updated**: 2026-03-13

---

## Round 1 — Decision-Critical Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Backward compatibility**: Is backward compatibility required for the `sgf_parser.py` public API (function signatures, return types), or can consumers be updated in the same PR? | A: Maintain exact same function signatures / B: Update all consumers to use KaTrain's native types directly / C: Other | **B** | **B** — No backward compat required. Update all consumers. | ✅ resolved |
| Q2 | **Scope boundary**: Is this change scoped to `tools/puzzle-enrichment-lab/` only, or should `backend/puzzle_manager/` also be migrated? | A: Enrichment-lab only / B: Both, but code stays independent / C: Other | **B** | **B** — Both subsystems. Code stays independent: lab code in lab, puzzle_manager code in puzzle_manager. No cross-imports. | ✅ resolved |
| Q3 | **Parser choice**: KaTrain's parser, `tools/core/sgf_parser.py`, or hybrid? | A: KaTrain (copy from GitHub) / B: tools/core / C: Hybrid | **A** | **A** — Copy KaTrain's parser directly. Do NOT use `tools/core/sgf_parser.py`. Just copy-paste KaTrain contents into lab once and backend once. Thin adapters/wrappers sit around it. | ✅ resolved |
| Q4 | **Position model**: Keep existing models or adopt KaTrain's `Move` class? | A: Keep as-is / B: Replace Stone+Color with Move / C: Full KaTrain types | **C** | **C** — Adopt KaTrain types as much as possible. Stay true to KaTrain so future updates can drop in. | ✅ resolved |
| Q5 | **sgfmill removal**: Remove from requirements.txt or keep? | A: Remove / B: Keep unused | **A** | **A** — Remove sgfmill. | ✅ resolved |
| Q6 | **Vendoring/placement**: Where does KaTrain parser file live? | A: In analyzers/ / B: In a new core/ per subsystem / C: pip dependency | **B** | **B** — Create `core/` in enrichment-lab for the KaTrain parser. Backend already has `core/`. One core per subsystem, making future merging easier. | ✅ resolved |
| Q7 | **Old code removal**: Delete old `sgf_parser.py` or keep? | A: Delete / B: Rename+deprecate | **A** | **A** — Remove old code. | ✅ resolved |

---

## Prior Research Reference

Existing research initiative: `TODO/initiatives/20260310-research-sgfmill-replacement/15-research.md`

Key findings:
- sgfmill has 12 API call sites across 2 files (parser: 5, enricher: 7)
- `tools/core/sgf_parser.py` has `dict[str, str]` properties (comma-joined multi-values) — format mismatch with enrichment lab's `dict[str, list[str]]`
- Net ~120-150 lines changed
- Complexity verdict: MEDIUM
