# Options — Enrichment Lab GUI Update

**Initiative ID:** 20260311-feature-enrichment-lab-gui-update
**Last Updated:** 2026-03-11

---

## Option A: Overlay-on-BesoGo with DOM Relocation (Recommended)

**Summary:** Keep BesoGo as the board renderer. Create BesoGo with `panels: ['tree']`, then relocate the tree DOM node into a new right panel after initialization. Add a separate SVG overlay layer on top of the board for score dots, PV previews, and candidate highlights. Restructure the HTML layout to a 3-column CSS grid.

**Pros:**
- Zero risk to existing BesoGo functionality — tree still rendered by BesoGo, just moved in the DOM
- Overlays are independent — easy to toggle on/off, easy to test in isolation
- Layout changes are CSS + HTML only (grid restructure)
- Lowest code change surface area (~11 files)
- Follows the same pattern GoProblems.com uses (overlay on existing board renderer)

**Cons:**
- Coordinate mapping between BesoGo SVG and overlay SVG requires careful alignment and calibration
- Two SVG layers may have z-index edge cases (mitigated by `pointer-events: none`)
- DOM relocation of tree panel is a fragile pattern (BesoGo may re-render and create a new panel)

**Files touched:** ~11 files (9 modified, 2 new)
**Effort:** ~12-15h

---

## Option B: Replace BesoGo with GhostBan

**Summary:** Replace BesoGo entirely with GhostBan, which has built-in analysis overlay support and was previously used in GUI v2. Rebuild the tree panel using a custom implementation.

**Pros:**
- GhostBan has native analysis markup support (score overlays built-in)
- Cleaner long-term architecture — single library handles both board and overlays
- Initiative `20260308-1800-feature-enrichment-lab-ghostban-gui` already explored this

**Cons:**
- High risk — previous GUI iteration with GhostBan was abandoned (initiative `20260308-1800`)
- Tree panel must be rebuilt from scratch (BesoGo's tree panel code is well-tested)
- Stone placement / Go rules / capture logic must be re-tested
- ~30h+ effort with uncertain outcome

**Files touched:** ~15+ files (most of `gui/src/` rewritten)
**Effort:** ~30h+

---

## Option C: Custom Canvas Board with Integrated Overlays

**Summary:** Replace BesoGo with a custom HTML5 Canvas board renderer that has native overlay support.

**Pros:**
- Full control over rendering pipeline
- Native overlay integration — no second SVG layer needed
- Pixel-perfect coordinate mapping

**Cons:**
- Massive effort — rebuilding what BesoGo already does (board rendering, Go rules, captures, ko, tree)
- Violates CLAUDE.md "buy, don't build" principle
- 3 prior GUI failures were caused by over-engineering; this approach repeats that mistake
- No keyboard/mouse event handling infrastructure

**Files touched:** ~20+ files (complete rewrite)
**Effort:** ~50h+

---

## Tradeoff Matrix

| Criterion | Option A (Overlay) | Option B (GhostBan) | Option C (Canvas) |
|-----------|-------------------|---------------------|-------------------|
| Risk | Low | High | Very High |
| Effort | ~15h | ~30h+ | ~50h+ |
| Files changed | ~11 | ~15+ | ~20+ |
| Preserves existing functionality | Yes | Partial | No |
| BesoGo tree retained | Yes (relocated) | No (rebuild) | No (rebuild) |
| Overlay complexity | Medium (coordinate calibration) | Low (built-in) | None (integrated) |
| Go rules / captures tested | Already working | Must re-test | Must rebuild |
| Historical success probability | High (additive) | Low (prior attempt abandoned) | Very low (3 prior GUI failures from over-engineering) |

---

## Selected: Option A — Overlay-on-BesoGo with DOM Relocation

**Rationale:** Lowest risk, smallest change surface, preserves all existing working functionality. The overlay-on-existing-renderer approach is proven (GoProblems itself uses this pattern). The DOM relocation of the tree panel carries some fragility risk, but this is mitigated by creating BesoGo with `panels: ['tree']` (so BesoGo handles all tree rendering internals) and only moving the resulting DOM node to a different container.

The prior attempts at replacing BesoGo (Options B and C) have both been tried and abandoned in earlier initiatives, confirming that the incremental overlay approach is the pragmatic choice.
