# Charter — Advanced Search Filters: Depth Presets + AC-Quality Integration

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Last Updated: 2026-03-14

## Goals

1. **Depth preset filter** — expose solution depth as a user-facing filter using three intuitive bucket presets (Quick / Medium / Deep) on browse-level pages.
2. **AC → Quality integration** — modify backend quality scoring to incorporate analysis completeness (ac) as an input signal, so verified/enriched puzzles naturally score higher quality.
3. **ac decoding** — decode `ac` field into frontend `DecodedEntry` for downstream programmatic use.

## Non-Goals

- No separate AC filter in the UI (AC is folded into quality scoring instead).
- No depth filter on Collection Solve page (preserves sequential study flow per Cho Chikun principle).
- No depth badge on puzzle cards or SolverView (spoils reading depth surprise — knowing move count changes how you approach the puzzle).
- No quality display redesign (stars/badges — separate initiative).
- No new filter dimensions beyond depth presets.
- No range slider UI — presets only.

## Constraints

- Frontend is static (GitHub Pages). All filtering is SQL queries against in-memory sql.js DB.
- `cx_depth` column already exists in DB-1. `minDepth`/`maxDepth` already wired in `buildWhereClause`.
- `ac` column already exists in DB-1 `PuzzleRow`. 
- Quality filter already fully functional (`p.quality >= ?` + pill bar UI).
- Depth bucket boundaries must be config-driven (not hardcoded).
- Must not break existing URL params or filter behavior (additive only).
- Backend quality scoring must be deterministic (same inputs → same quality score).
- AC → quality scoring: `ac` becomes a new config-driven threshold requirement in `puzzle-quality.json` (same pattern as `refutation_count_min` and `min_comment_level`). `compute_puzzle_quality_level()` reads ac from the existing YQ property. Pipeline sequencing: ac is set during enrichment, quality scoring runs after — the analyze stage already processes enrichment before quality computation.
- Zero/low-count depth pills: pills with count=0 are rendered but visually dimmed (disabled state). Pills with low count show the count badge normally. No hiding — users should see the full range even when sparse.

## Acceptance Criteria

| id | criterion |
|----|-----------|
| AC-1 | Depth preset pills (Quick 1-2 / Medium 3-5 / Deep 6+) visible on TrainingSelectionPage, TechniqueFocusPage, TrainingPage, RandomPage |
| AC-2 | Depth preset pills NOT visible on CollectionViewPage |
| AC-3 | Selecting a depth preset filters puzzles to matching `cx_depth` range |
| AC-4 | Depth preset selection persisted in URL params (canonical URL contract) |
| AC-5 | ~~Depth badge on puzzle cards~~ **REMOVED** — spoils reading depth surprise |
| AC-6 | Backend quality scoring incorporates `ac` level via new `min_ac` config requirement in `puzzle-quality.json` (e.g., quality 4+ requires `min_ac: 1`, quality 5 requires `min_ac: 2`). `compute_puzzle_quality_level()` reads ac from existing YQ property. |
| AC-7 | Quality filter continues to work as `p.quality >= ?` (no regression) |
| AC-8 | `ac` field present in `DecodedEntry` type |
| AC-9 | Count badges on depth preset pills show puzzle counts per bucket |
| AC-10 | All changes have unit tests |
| AC-11 | AGENTS.md updated for changed modules |

## Stakeholders

- Users: puzzle solvers ranging 30k to dan-level
- Frontend: Preact/TS app (services, hooks, pages, components)
- Backend: Python pipeline (quality scoring stage)

## References

- Research: [15-research.md](./15-research.md) — Lee Sedol & Cho Chikun consultation
- Clarifications: [10-clarifications.md](./10-clarifications.md)
- Existing depth query: [puzzleQueryService.ts](../../../frontend/src/services/puzzleQueryService.ts) `buildWhereClause`
- Existing quality filter: `usePuzzleFilters.ts` → `buildQualityOptions()`
- Quality config: `config/puzzle-quality.json`
