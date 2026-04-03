# Clarifications — Config Panel + Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Last Updated**: 2026-03-14

---

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required for the bridge API? | A: Yes, optional field / B: No, breaking change OK | A | **B** — No backward compat needed. Breaking change to `EnrichRequest` is fine. | ✅ resolved |
| Q2 | Should old code be removed? (hardcoded `visits: 200`, fixed `EnrichRequest`) | A: Yes, replace / B: Keep both paths | A | **B** — Keep old code if not blocking. Don't force removal. | ✅ resolved |
| Q3 | Config panel scope — which parameter groups in MVP? | A: All 45 / B: MVP 21 / C: Just Analysis (9) | B | **A** — All 45 parameters. Fill with default values from config files. Everything comes from config. | ✅ resolved |
| Q4 | Config panel placement | A: Left sidebar / B: Horizontal strip / C: Right panel | A | **A (enhanced)** — Left sidebar below SGF. Also: remove the horizontal pill bar from the top and replace with an intuitive vertical flow in the sidebar showing stage progress. Consult UI/UX expert. | ✅ resolved |
| Q5 | Per-stage re-run scope | A: Engine-free only / B: Full re-run / C: Don't build | A | Not explicitly answered. Default to recommendation: **A** — engine-free stages first. | ✅ resolved |
| Q6 | Analyze button visits | A: Uses config panel / B: Own dropdown / C: Both | B | **B** — Own dropdown (200/500/1000/2000/5000) for quick iteration. | ✅ resolved |
| Q7 | Config persistence across reloads | A: localStorage / B: Server defaults / C: Export/import | A | **A** — Save to localStorage. | ✅ resolved |
| Q8 | Difficulty weight sliders (sum=100) | A: Independent + validation / B: Linked sliders / C: Defer | C | **A** — Independent sliders with validation. If sum ≠ 100, fall back to old/default values. Make it visually polished. Consult governance for UI/UX/CSS. | ✅ resolved |

## Additional User Directives

1. **Tailwind**: User believes the project uses Tailwind. Research confirmed: the *frontend app* uses Tailwind CSS v4, but the *enrichment lab GUI* uses hand-written CSS (no build step, served by FastAPI). UX research recommends continuing hand-written CSS (REJ-1 in research).
2. **UI/UX quality**: "Do not make it ugly." — Explicit requirement for polished dark-theme developer tool aesthetic.
3. **Governance review**: User wants governance panel consulted for UI/UX and CSS decisions.

---

> **See also**:
> - [15-research.md](./15-research.md) — Stage/config parameter catalog
> - [15-research-ux.md](./15-research-ux.md) — UI/UX patterns and widget designs
