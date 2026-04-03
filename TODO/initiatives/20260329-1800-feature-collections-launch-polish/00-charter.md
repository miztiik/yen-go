# Charter: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Initiative ID

`20260329-1800-feature-collections-launch-polish`

## Problem Statement

Many puzzle sources (OGS, kisvadim-goproblems, gotools, eidogo, tasuki, etc.) have rich directory structures encoding collection membership and puzzle ordering. This metadata is never embedded into SGF files before pipeline ingest, so `YL[]` tags are missing and collection browse has no chapter/position ordering. The browse UI also needs usability improvements: section reorganization, per-section search, better sorting, and hover treatment.

## Goals

| goal_id | Goal | Acceptance Criteria |
|---------|------|---------------------|
| G1 | Build a pre-pipeline utility in `tools/core/` that embeds `YL[slug:chapter/position]` into SGF files based on directory structure | Utility runs against any source; OGS, kisvadim-goproblems, gotools processed; `YL` values match `config/collections.json` slugs |
| G2 | Consolidate 4 duplicated phrase-matching implementations into `tools/core/collection_matcher.py` | Single shared matcher used by embedder and existing tools; DRY compliance |
| G3 | Provide thin CLI wrappers per source (e.g., `tools/ogs embed-collections`) | OGS wrapper uses manifest lookup; kisvadim uses phrase matching; gotools uses filename pattern decoding |
| G4 | Frontend: merge 4 browse sections into 3 (technique+reference → Practice) | Learning Paths, Practice, Books |
| G5 | Frontend: Learning Paths sorted by difficulty order; Books sorted by tier→quality→puzzle_count | Learning Paths follows `config/puzzle-levels.json` order; Books: premier first, then curated |
| G6 | Frontend: hide <15 puzzle collections from browse; search still finds them | Browse sections show only substantial collections |
| G7 | Frontend: selective randomization — technique/training randomized per session; books/author keep sequence order | Toggleable backend config; not user-facing |
| G8 | Frontend: DB-scoped in-section search within each browse section | Small search box per section; queries scoped to section type |
| G9 | Frontend: "Show more" button repositioned to top of section; hover color treatment on all browse pages | UX expert consulted; works in both light/dark themes |
| G10 | Improve weak collection descriptions for browse cards | Vague descriptions like "taruc-practice" get meaningful text |

## Non-Goals

| ng_id | Non-Goal | Rationale |
|-------|----------|-----------|
| NG1 | Modify the pipeline (`analyze.py`, `trace_utils.py`, `sources.json`) | Shift-left: embedder handles collection assignment pre-pipeline |
| NG2 | Add `featured: boolean` to schema | Editorial tier rotation (68 collections, random 6) is sufficient |
| NG3 | Build content-hash dedup strategy | Not requested; pipeline handles dedup natively |
| NG4 | Remove community tier | Kept as future placeholder |
| NG5 | Un-consolidate 159 back to 738 | Consolidation was correct |
| NG6 | Modify `deprecated_generator/` | Archived |

## Constraints

- Published SGF `YL[]` values must remain valid (backward compatible)
- Utility lives in `tools/core/` (importable by all source tools)
- No new Python dependencies (uses existing `tools.core` modules)
- No pipeline changes — utility runs before ingest
- Follows tool development standards (`docs/how-to/backend/tool-development-standards.md`)
- Chapter 0 convention: sources without chapter concept use chapter `0` as synthetic default
- Minimal-edit SGF approach: embedder adds/updates `YL[]` only, preserves all other properties

## Scope Boundaries

- **Utility**: `tools/core/collection_embedder.py` + `tools/core/collection_matcher.py` (new shared modules)
- **CLI wrappers**: `tools/ogs/`, `tools/kisvadim-goproblems/` (if exists), `tools/gotools/` (if exists)
- **Frontend**: `CollectionsBrowsePage.tsx`, `CollectionViewPage.tsx`, `collectionService.ts`, `puzzleQueryService.ts`, `PuzzleCollectionCard.tsx`, technique/training browse pages
- **Config**: Description improvements in `config/collections.json` (no schema version bump)
- **Docs**: `docs/concepts/collections.md`, AGENTS.md files, CLAUDE.md
