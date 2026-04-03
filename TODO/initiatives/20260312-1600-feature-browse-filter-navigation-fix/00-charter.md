# Charter — Browse Page Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Last Updated:** 2026-03-12

---

## Goals

1. **Fix navigation bugs** — CollectionViewPage back button must return to `/collections`, not Home.
2. **Fix filter state persistence** — Category and sort filters on TechniqueFocusPage and TrainingSelectionPage must survive back/forward navigation via URL-sync.
3. **Fix cosmetic/misleading filters** — Remove or wire ContentTypeFilter on CollectionsPage (currently purely cosmetic). Fix default category on TechniqueFocusPage from `'technique'` to `'all'`.
4. **URL-sync Collections search** — Persist search term in URL so it survives back navigation.
5. **Add shorthand URL routes** — Support `/collection/{slug}`, `/training/{slug}`, `/technique/{slug}` as aliases for the full `/contexts/...` paths. Keep existing paths working.
6. **Cross-page filter consistency** — Ensure ContentTypeFilter on browse pages either has counts (functional) or is removed (not misleading).

## Non-Goals

- Adding new filter types to CollectionsPage (level/tag/sort filters) — deferred to follow-up
- Resume-last-position per collection (localStorage cursor) — deferred
- Bookmarks/favorites feature — deferred
- Backend/pipeline changes — frontend-only initiative
- Content type → collection type mapping (complex taxonomy alignment) — deferred

## Constraints

- **Backward compatibility required** — existing `/contexts/` URLs must keep working
- **Frontend-only** — no backend or pipeline changes
- **Local-first** — all state in URL params or localStorage
- **Zero new dependencies** — use existing hooks (`useCanonicalUrl`, `useContentType`)
- **Dead code policy** — if ContentTypeFilter is removed from CollectionsPage, delete the rendering code

## Design Decisions for Options Phase

> **Open question (per Governance RC-2):** `useCanonicalUrl` currently handles only **numeric array params** (`l`, `t`, `c`, `q`, `ct`) on **context routes** (`/contexts/{dim}/{slug}?...`). Browse pages (`/collections`, `/technique`, `/training`) need string params (`cat`, `s`, `q`). The URL-sync approach for browse pages is an **open architectural question** to be resolved in options phase.
>
> Candidate approaches:
> - (a) Lightweight custom hook using `URLSearchParams` directly
> - (b) Extend `useCanonicalUrl` to support string params on any route
> - (c) Minimal per-page inline `URLSearchParams` (no hook abstraction)
>
> The I-5 ContentTypeFilter "counts vs. remove" decision is also carried forward as an explicit options tradeoff.

## Acceptance Criteria

| AC | Description | Verification |
|----|-------------|-------------|
| AC-1 | CollectionViewPage → Back → lands on `/collections` browse page | Manual + Playwright |
| AC-2 | TechniqueFocusPage category filter persists via URL `cat` param across back/forward | Manual + unit test |
| AC-3 | TechniqueFocusPage sort filter persists via URL `s` param across back/forward | Manual + unit test |
| AC-4 | TrainingSelectionPage category filter persists via URL `cat` param across back/forward | Manual + unit test |
| AC-5 | CollectionsPage search term persists via URL `q` param | Manual + unit test |
| AC-6 | CollectionsPage ContentTypeFilter is either removed or functionally wired | Visual inspection |
| AC-7 | TechniqueFocusPage defaults to `'all'` category on fresh visit (no URL params) | Manual + unit test |
| AC-8 | `/collection/{slug}` URL navigates to CollectionViewPage | Routing unit test |
| AC-9 | `/training/{slug}` URL navigates to TrainingPage | Routing unit test |
| AC-10 | `/technique/{slug}` URL navigates to TechniqueFocusPage context | Routing unit test |
| AC-11 | Existing `/contexts/collection/{slug}` URLs still work | Routing unit test (regression) |
| AC-12 | All existing vitest tests pass (no regression) | `npm test` |

## Issue Inventory (from UX Audit)

| Issue ID | Severity | Page | Description | Research Evidence |
|----------|----------|------|-------------|-------------------|
| I-1 | **Critical** | CollectionViewPage | Back → Home instead of /collections | E-1 |
| I-2 | **Critical** | CollectionsPage | ContentTypeFilter has zero functional effect | E-4, E-9 |
| I-3 | **High** | TechniqueFocusPage, TrainingSelectionPage | Category/sort filters lost on back/forward | E-2, E-3 |
| I-4 | **High** | CollectionsPage | Search term not URL-synced, lost on back | E-4 |
| I-5 | **High** | CollectionsPage, TechniqueFocusPage, TrainingSelectionPage | ContentTypeFilter renders without counts | E-5 |
| I-6 | **High** | TechniqueFocusPage | Default category `'technique'` hides tesuji/objective | E-10 |
| I-9 | **Medium** | Routing | No shorthand /collection/{slug} URL | E-6 |

---

> **See also**:
> - [10-clarifications.md](./10-clarifications.md) — Clarification log
> - [15-research.md](./15-research.md) — UX Audit (DDK + SDK personas)
