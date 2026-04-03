# Clarifications — Advanced Search Filters

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Last Updated: 2026-03-14

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Which filter dimensions to expose in UI? | A) All 6 / B) ac + cx_depth only / C) ac + cx_depth + cx_refutations / D) Other | B | **B** (defaults accepted) | ✅ resolved |
| Q2 | Quality filter: keep `>=` or switch to exact? | A) Keep >= / B) Exact / C) Both | A | **A** (defaults accepted) | ✅ resolved |
| Q3 | UI control style for `ac` filter? | A) Pill FilterBar / B) FilterDropdown / C) Checkbox toggle / D) Other | A | **A** (defaults accepted) | ✅ resolved |
| Q4 | UI control style for depth? | A) Range slider / B) Preset pills / C) No UI / D) Other | B | **B** (defaults accepted) | ✅ resolved |
| Q5 | Which pages get filters? | A) All filter-bearing / B) Collection/browse only / C) New page / D) Other | A | **A** (defaults accepted) | ✅ resolved |
| Q6 | Backward compat + old code removal? | A) Additive only, no compat needed / B) Migration needed | A | **A** (defaults accepted) | ✅ resolved |
| Q7 | Add `ac` to DecodedEntry? | A) Yes + badge / B) Yes, no badge / C) No | B | **B** (defaults accepted) | ✅ resolved |

## Round 2 (Post-Research)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q8 | AC as user-facing filter? Research says defer. | A) Defer AC entirely, fold into quality scoring / B) Binary toggle / C) Full pill bar / D) Other | A | **A** — fold AC into quality score, no separate AC filter | ✅ resolved |
| Q9 | Exclude depth filter from Collection Solve page? | A) Yes / B) No | A | **A** — sequential study principle respected | ✅ resolved |
| Q10 | Add depth as informational badge on puzzle cards? | A) Yes / B) No / C) Badge only, no filter | A | **A** — depth badge + filter | ✅ resolved |
| Q11 | Include quality display redesign in scope? | A) Yes / B) Keep separate | B | **B** — separate initiative | ✅ resolved |

## Decisions

- **Backward compatibility**: Not required (additive feature, old URLs work as-is)
- **Legacy code removal**: N/A — no old code to replace
- **AC strategy**: Fold AC into quality score (backend pipeline change). No separate AC filter UI.
- **Feature scope**:
  1. Depth preset pills (Quick 1-2 / Medium 3-5 / Deep 6+) on Browse/Random/Training pages
  2. Depth informational badge on puzzle cards
  3. AC → quality scoring integration (backend)
  4. `ac` field decoded into `DecodedEntry` (frontend, no display yet)
- **Exclusions**: No AC filter UI; no depth filter on Collection Solve; no quality display redesign
