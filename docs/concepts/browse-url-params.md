# Browse URL Parameters

**Last Updated**: 2026-03-13

Browse pages (Collections, Training, Technique Focus) persist user filter and search state in URL query parameters via the `useBrowseParams` hook. This allows shareable URLs and browser back/forward navigation through filter states.

---

## Hook: `useBrowseParams<T>`

**File:** `frontend/src/hooks/useBrowseParams.ts`

Generic hook that syncs a set of named URL parameters with component state.

```typescript
const { params, setParam, clearParams } = useBrowseParams({ cat: 'all', s: 'name' });
```

**Behavior:**
1. **Mount:** reads `URLSearchParams` from current URL, merges with defaults
2. **`setParam(key, value)`:** updates state + writes to URL via `history.replaceState`
3. **`clearParams()`:** resets managed keys to defaults, removes them from URL
4. **`popstate`:** re-reads params when browser navigates (back/forward)

### Read-Merge-Write Pattern

Both `useBrowseParams` and `useCanonicalUrl` use a read-merge-write strategy when updating the URL. Each hook reads the current `URLSearchParams`, modifies only its own managed keys, and writes back the full set. This prevents one hook from overwriting parameters managed by the other.

- `useBrowseParams` manages: keys defined in its `defaults` argument (e.g., `cat`, `s`, `q`)
- `useCanonicalUrl` manages: `l`, `t`, `c`, `q`, `ct`, `offset`, `id`, `match`

On pages where both hooks are active (TechniqueFocusPage, TrainingSelectionPage), neither hook clobbers the other's parameters.

### Pathname Guard (RC-1)

The `popstate` listener only re-reads parameters when `window.location.pathname` is unchanged. This prevents a route change from being misinterpreted as a parameter change on the current page.

---

## Parameter Keys by Page

| Page | Params | Example URL |
|------|--------|-------------|
| TechniqueFocusPage | `cat` (category), `s` (sort) | `/technique?cat=tesuji&s=difficulty` |
| TrainingSelectionPage | `cat` (category filter) | `/training?cat=life-and-death` |
| CollectionsPage | `q` (search query) | `/collections?q=cho+chikun` |

Keys are short, lowercase, and collision-free with canonical context params.

**Note:** `q` is used on both browse pages (CollectionsPage search) and context pages (quality filter). No collision occurs because they exist on different route paths.

---

## Shorthand Route Aliases

Three shorthand URL patterns resolve to context routes for cleaner shareable links:

| Shorthand | Canonical equivalent |
|-----------|---------------------|
| `/collection/{slug}` | `/contexts/collection/{slug}` |
| `/training/{slug}` | `/contexts/training/{slug}` |
| `/technique/{slug}` | `/contexts/technique/{slug}` |

`serializeRoute()` always produces the canonical `/contexts/...` form. Shorthand patterns are recognized by `parseRoute()` only.

---

> **See also**:
>
> - [Architecture: Frontend](../architecture/frontend/) — Frontend system design
> - [Concepts: Levels](./levels.md) — Level filter values
> - [Concepts: Tags](./tags.md) — Tag filter values
