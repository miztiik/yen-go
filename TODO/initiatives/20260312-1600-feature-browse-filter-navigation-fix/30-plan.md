# Plan — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Selected Option:** A — `useBrowseParams` Hook  
**Last Updated:** 2026-03-12

---

## Architecture

### New Component: `useBrowseParams<T>` Hook

**File:** `frontend/src/hooks/useBrowseParams.ts`  
**Size:** ~60 lines  
**Dependencies:** None (pure browser API: `URLSearchParams`, `history.replaceState`, `popstate` event)

```typescript
// Signature
function useBrowseParams<T extends Record<string, string>>(
  defaults: T
): {
  params: T;
  setParam: (key: keyof T, value: string) => void;
  clearParams: () => void;
};
```

**Behavior:**
1. On mount: read `window.location.search` → parse via `URLSearchParams` → merge with defaults
2. On `setParam()`: **read-merge-write** — read current `URLSearchParams`, update only managed keys (those in `defaults`), write back ALL params via `history.replaceState` (preserves params managed by other hooks; RC-2)
3. On `popstate`: re-read params from URL **only if `pathname` is unchanged** (RC-1 path guard)
4. On unmount: remove `popstate` listener
5. On `clearParams()`: read-merge-write — delete only managed keys, preserve others

**RC-1 Path Guard (Mandatory):**
```typescript
const handlePopstate = useCallback(() => {
  if (window.location.pathname === pathnameRef.current) {
    // Same page — re-read params from URL
    setParams(readParamsFromUrl(defaults));
  }
  // Different page — ignore, let router handle it
}, [defaults]);
```

### Param Key Convention

| Page | Params | URL Example |
|------|--------|-------------|
| TechniqueFocusPage | `cat` (category), `s` (sort) | `/technique?cat=tesuji&s=difficulty` |
| TrainingSelectionPage | `cat` (category) | `/training?cat=life-and-death` |
| CollectionsPage | `q` (search) | `/collections?q=cho+chikun` |

Short, lowercase, collision-free with existing context params (`l`, `t`, `c`, `q`, `ct`).

**Note:** `q` is used for both browse search (CollectionsPage) and context quality filter. No collision because they live on different route paths (`/collections` vs `/contexts/...`).

---

## File-Level Changes

### 1. NEW: `frontend/src/hooks/useBrowseParams.ts`

- Generic hook: `useBrowseParams<T extends Record<string, string>>(defaults: T)`
- Reads `URLSearchParams` on mount
- Writes via `history.replaceState` on `setParam()`
- `popstate` listener with pathname guard (RC-1)
- Cleanup on unmount

### 2. MODIFY: `frontend/src/app.tsx`

- **Line ~525:** Change `onBack={handleBackToHome}` → `onBack` callback that navigates to `{ type: 'collections-browse' }`
- Impact: CollectionViewPage back button only; other context pages untouched

### 3. MODIFY: `frontend/src/pages/TechniqueFocusPage.tsx`

- Replace `useState('technique')` → `useBrowseParams({ cat: 'all', s: 'name' })` for category + sort
- Default category changes from `'technique'` to `'all'` (I-6 fix)
- Remove `<ContentTypeFilter />` JSX + import (I-5 fix — cosmetic, no counts)
- Keep `useCanonicalUrl` for level filter (it handles `l=` param on this route)

### 4. MODIFY: `frontend/src/pages/TrainingSelectionPage.tsx`

- Replace `useState<CategoryFilter>('all')` → `useBrowseParams({ cat: 'all' })` for category
- Remove `<ContentTypeFilter />` JSX + import (I-5 fix)
- Keep `useCanonicalUrl` for tag filter (it handles `t=` param)

### 5. MODIFY: `frontend/src/pages/CollectionsPage.tsx`

- Replace `useState('')` → `useBrowseParams({ q: '' })` for search
- Remove `<ContentTypeFilter />` JSX + import (I-2 fix — cosmetic CTF with zero effect)

### 6. MODIFY: `frontend/src/hooks/useCanonicalUrl.ts` (RC-3)

- Modify `writeToUrl` / `buildSearchString` to use **read-merge-write** URL pattern:
  1. Read current `URLSearchParams` from `window.location.search`
  2. Set/delete only canonical keys (`l`, `t`, `c`, `q`, `ct`, `offset`, `id`)
  3. Write back ALL params (preserves unmanaged keys like `cat`, `s`)
- Change is ~5 lines in `buildSearchString`: replace `new URLSearchParams()` with `new URLSearchParams(window.location.search)`, then set only canonical keys
- Impact: TechniqueFocusPage and TrainingSelectionPage where both hooks coexist

### 7. MODIFY: `frontend/src/lib/routing/routes.ts`

- Add 3 shorthand route patterns to `parseRoute()`:
  - `/collection/{slug}` → `{ type: 'context', dimension: 'collection', slug }`
  - `/training/{slug}` → `{ type: 'context', dimension: 'training', slug }`
  - `/technique/{slug}` → `{ type: 'context', dimension: 'technique', slug }`
- Implementation: 1 additional regex or 3 string matches before the fallback-to-home
- `serializeRoute()` unchanged — canonical output always uses `/contexts/...`

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `popstate` cross-page param leakage | Medium | RC-1 path guard: only re-read when pathname unchanged |
| Dual hooks on TechniqueFocusPage (`useCanonicalUrl` + `useBrowseParams`) | Medium | Both hooks use read-merge-write pattern (RC-2, RC-3): each reads current URLSearchParams, updates only its managed keys, writes back all. Dual-hook integration test in T9 verifies mutual preservation (RC-5). |
| `q` param name collision (browse search vs context quality) | None | Different route paths → never co-exist |
| Shorthand route regex interacts with existing CONTEXT_RE | Low | Shorthand patterns matched AFTER CONTEXT_RE in `parseRoute()` |
| ContentTypeFilter removal breaks page layout | Low | Visual inspection; CTF was a row element, not a layout anchor |

---

## Rollback Plan

Revert single branch containing:
1. Delete `useBrowseParams.ts`
2. Revert 6 page/route/hook files (5 pages + `useCanonicalUrl.ts`)
3. `useCanonicalUrl.ts` change (read-merge-write) is backward-compatible — preserving it post-revert is safe

---

## Documentation Plan

| doc_action | file | why |
|------------|------|-----|
| files_to_create | `docs/concepts/browse-url-params.md` | Document `useBrowseParams` pattern, param keys, difference from context filters |
| files_to_update | `docs/reference/url-routes.md` (if exists) | Add shorthand route aliases |
| files_to_update | `frontend/CLAUDE.md` | Add hook to conventions section (brief note only) |

### Cross-references

> **See also**:
> - [20-analysis.md](./20-analysis.md) — Ripple-effects and coverage
> - [40-tasks.md](./40-tasks.md) — Task decomposition
> - [25-options.md](./25-options.md) — Option selection rationale
