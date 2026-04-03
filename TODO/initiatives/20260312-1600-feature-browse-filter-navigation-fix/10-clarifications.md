# Clarifications — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Last Updated:** 2026-03-12

---

## Clarification Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required for existing URL bookmarks (e.g., `/contexts/collection/{slug}` must keep working if we add `/collection/{slug}`)? | A: Yes, both old and new URLs must work / B: No, we can redirect only / C: Other | A — keep old `/contexts/` URLs working and add aliases as additional routes | From conversation: user wants both shorthands AND existing URLs | ✅ resolved |
| Q2 | Should old cosmetic ContentTypeFilter be removed from CollectionsPage, or wired to actually filter? | A: Remove it (Quick Win) / B: Wire it to filter collections + show counts / C: Keep it cosmetic | A — remove from CollectionsPage until a meaningful mapping exists; don't mislead users | From conversation: user prioritises fixing broken things over adding new complexity | ✅ resolved |
| Q3 | Should CollectionsPage get full level/tag/sort filters (strategic improvement) in this initiative, or is it deferred? | A: Include in this initiative / B: Defer to follow-up / C: Other | B — defer strategic improvements; focus on navigation bugs + filter state persistence | From conversation: user wants to audit what is broken first, fix path | ✅ resolved |
| Q4 | For TechniqueFocusPage, should default category change from `'technique'` to `'all'`? | A: Yes, default to 'all' / B: Keep 'technique' default / C: Other | A — `'all'` ensures DDK users see all categories on first visit | From conversation: user flagged this as broken UX | ✅ resolved |
| Q5 | Should "resume last position" per collection be included in this initiative? | A: Yes / B: Defer / C: Other | B — defer to a follow-up; this initiative focuses on filter persistence and navigation | Inferred from scope: user focused on filters and navigation | ✅ resolved |
| Q6 | Is backward compatibility required, and should old code be removed? | A: Backward compat required, keep old code / B: No compat needed, remove old code / C: Other | A — existing `/contexts/` URLs must keep working; old code paths stay; new shorthand routes added as aliases | From conversation context: existing bookmarks and shared links must not break | ✅ resolved |

## Clarification Round 2 — Agent-Resolved (Recommended Defaults)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q7 | Should `ContentTypeFilter` counts be added to browse pages (TechniqueFocusPage, TrainingSelectionPage) in this initiative, or deferred? | A: Include — load shard meta / aggregate index data to provide counts / B: Defer — keep current cosmetic pills / C: Other | A — pills without counts are confusing per NNGroup research (R-1) | Agent-resolved: A — include counts to differentiate from cosmetic state; defers to governance if challenged | ✅ resolved |
| Q8 | Should `sortBy` on TechniqueFocusPage also be URL-synced, or just `categoryFilter`? | A: Sync both category + sort / B: Sync category only, defer sort / C: Other | A — both are in-memory state that gets lost; URL-syncing both is same complexity | Agent-resolved: A — sync both; minimal additional effort | ✅ resolved |
| Q9 | For URL shorthand routes, which shorthands should we add? | A: `/collection/{slug}` + `/training/{slug}` only / B: Also `/technique/{slug}` / C: All three / D: Other | C — all three for consistency; same code pattern, 3 route aliases | Agent-resolved: C — all three for consistency | ✅ resolved |

---

> **See also**:
> - [15-research.md](./15-research.md) — UX Expert Persona Audit findings
> - [00-charter.md](./00-charter.md) — Feature scope definition
