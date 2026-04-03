# Clarifications: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Pre-processing utility: one-time batch or re-run on new imports? | A: One-time / B: Re-run / C: Both | A | A — One-time per source. Shift-left to download time. | ✅ resolved |
| Q2 | Utility location and logging? | A: tools/core generic + thin wrappers per source / B: Per-source only | A | A — Generic in `tools/core/`, thin wrappers in `tools/ogs/` etc. Pedantic JSONL logging to `external-sources/{source}/logs/`. Continue on mismatch, log unmatched folders. | ✅ resolved |
| Q3 | Chapter/position encoding? | A: Slug only / B: Slug + position from file order / C: Slug + position from manifest | B+C | B for phrase-match sources (file ordering), C for OGS (manifest `puzzles` array). Chapter 0 convention documented. | ✅ resolved |
| Q4 | Improve weak descriptions? | A: Yes for browse cards / B: Skip | A | A — Improve for browse UX. Search uses slugs, not descriptions. | ✅ resolved |
| Q5 | Random puzzle order within collections? | A: SQL random / B: Client shuffle / C: Research first | Research done | Client-side shuffle on loaded `puzzles` array. Selective: technique/training only, not books/author. Toggleable backend config. | ✅ resolved |
| Q6 | Learning Paths sort order? | A: puzzle-levels.json order / B: Manual / C: Other | A | A — Use `config/puzzle-levels.json` difficulty ordering (novice → expert). | ✅ resolved |
| Q7 | Books/Author sort order? | A: Tier→alpha / B: Tier→puzzle_count / C: Other | B expanded | Tier (premier first) → quality → puzzle_count. | ✅ resolved |
| Q8 | In-section search scope? | A: Client-side filter / B: DB-scoped | B | B — DB-scoped search within each section by collection type. | ✅ resolved |
| Q9 | Backward compatibility required? | A: Yes / B: No | A | A — Published SGFs `YL[]` values valid. No pipeline changes at all. | ✅ resolved |
| Q10 | Which sources need embedder? | A: All / B: OGS + obvious / C: User specifies | A | A — Audit all 15 dirs. Priority: OGS (42K), kisvadim (3K), gotools (5K). Flat sources get no benefit. | ✅ resolved |
| Q11 | Randomization selectivity? | A: Global toggle / B: Per-type policy | B | B — `{ graded: false, author: false, technique: true, reference: true }`. Toggleable config, not user-facing. | ✅ resolved |
| Q12 | "Show more" and hover treatment scope? | A: Collections only / B: All browse pages | B | B — All browse pages (collections, technique, training). UX expert to finalize colors. | ✅ resolved |
| Q13 | Puzzle offset/jump navigation? | Research needed | Research done | Route supports `offset`, `CollectionViewPage` accepts `startIndex`. Filter+offset interaction to verify during implementation. | ✅ resolved |
| Q14 | Sanderland migration to embedder? | A: Keep current / B: Migrate | A | A — Already works via dedicated adapter. No change. | ✅ resolved |
