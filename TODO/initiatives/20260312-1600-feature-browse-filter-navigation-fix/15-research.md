# Research — UX Audit: Filter & Navigation Gaps (DDK + SDK Personas)

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Date:** 2026-03-12  
**Mode:** Feature-Researcher  
**Confidence after research:** 88 / 100  
**Risk level:** Medium  
**Source:** Copied from Feature-Researcher output (20260312-ux-audit-filter-navigation)

---

## 1. Research Question and Boundaries

**Question:** From the perspective of two learner personas (DDK casual player and SDK serious learner), what are the most impactful UX gaps in Yen-Go's filter system, navigation flow, and state persistence across the 5 main pages?

**In scope:** Filter correctness (wired vs. cosmetic), URL-sync behaviour, consistency across pages, navigation back-button destinations, state persistence, missing practice-workflow features, direct URL shareability.

**Out of scope:** Goban rendering, puzzle difficulty calibration, SGF content, backend/pipeline changes, PWA/offline features.

---

## 2. Internal Code Evidence Summary

| Evidence ID | File | Finding |
|-------------|------|---------|
| E-1 | app.tsx L522-526 | CollectionViewPage `onBack={handleBackToHome}` — goes Home, not /collections |
| E-2 | TechniqueFocusPage.tsx L74-75 | `categoryFilter` and `sortBy` are `useState` only — NOT URL-synced |
| E-3 | TrainingSelectionPage.tsx L114 | `categoryFilter` is `useState` only — NOT URL-synced |
| E-4 | CollectionsPage.tsx L246 | `searchTerm` is `useState` only, no level/tag/sort filters |
| E-5 | CollectionsPage, TechniqueFocusPage, TrainingSelectionPage | ContentTypeFilter rendered without `counts` prop (cosmetic) |
| E-6 | routes.ts L42-55 | No shorthand `/collection/{slug}` route — only `/contexts/...` |
| E-7 | App-wide search | No bookmarks/favorites/recently-played features |
| E-8 | CollectionViewPage.tsx L92-97 | No resume-last-position persistence |
| E-9 | CollectionsPage.tsx L345 | ContentTypeFilter changes global pref but CollectionsPage never reads it |
| E-10 | TechniqueFocusPage.tsx L74 | Default category `'technique'` hides tesuji and objective families |

## 3. External References

| R-id | Reference | Relevance |
|------|-----------|-----------|
| R-1 | NNGroup Filters vs Facets | Badge counts reduce "zero results" anxiety |
| R-2 | Duolingo streak/resume UX | Resume patterns improve 7-day retention |
| R-3 | Chess.com puzzle filter design | Technique × difficulty cross-filter is primary SDK learner pattern |
| R-4 | web.dev History API URL state | `replaceState` for filter sync is correct pattern (already used) |

## 4. Severity-Ranked Issue Table

| Issue ID | Severity | Page(s) | Description |
|----------|----------|---------|-------------|
| I-1 | **Critical** | CollectionViewPage | Back → Home instead of /collections |
| I-2 | **Critical** | CollectionsPage | ContentTypeFilter has zero functional effect |
| I-3 | **High** | TechniqueFocusPage, TrainingSelectionPage | Category/sort lost on back/forward |
| I-4 | **High** | CollectionsPage | Search not URL-synced |
| I-5 | **High** | 3 browse pages | ContentTypeFilter without counts (cosmetic) |
| I-6 | **High** | TechniqueFocusPage | Default 'technique' hides tesuji/objective |
| I-7 | **Medium** | CollectionsPage | No level/tag/sort filters |
| I-8 | **Medium** | CollectionViewPage | No resume-last-position |
| I-9 | **Medium** | Routing | No shorthand URLs |
| I-10 | **Low** | App-wide | No bookmarks/favorites |

## 5. DDK Casual Player Journey Friction

```
Home → Collections → "Cho Chikun..." → Back → HOME (not /collections) ← I-1
Home → Technique → default shows only 'technique' ← I-6 (tesuji hidden)
Home → Collections → ContentTypeFilter "Curated" → nothing happens ← I-2
```

## 6. SDK Serious Learner Journey Friction

```
Technique → Level "Upper-Int" + Category "Tesuji" + Sort "Puzzles" → enter puzzle → Back
  → Category & Sort RESET, only Level preserved ← I-3
Collections → search "Cho" → enter → Back → HOME + search gone ← I-1 + I-4
```

## 7. Recommendations (Quick Wins)

| Rec | Action | Change | Level |
|-----|--------|--------|-------|
| Rec-1 | Fix collection back button | app.tsx: `onBack → collections-browse` | L1 |
| Rec-2 | Remove cosmetic ContentTypeFilter from CollectionsPage | CollectionsPage.tsx: delete render | L0 |
| Rec-3 | Fix default category to 'all' | TechniqueFocusPage.tsx L74 | L0 |
| Rec-4 | URL-sync category+sort on browse pages | useCanonicalUrl extension + page updates | L2 |

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope
> - [10-clarifications.md](./10-clarifications.md) — Clarification log
