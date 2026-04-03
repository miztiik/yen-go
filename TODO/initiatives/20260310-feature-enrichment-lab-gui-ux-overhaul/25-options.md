# Options — Enrichment Lab GUI UX Overhaul

**Initiative ID:** 20260310-feature-enrichment-lab-gui-ux-overhaul
**Last Updated:** 2026-03-10

---

## Option A: Overlay-on-BesoGo (Recommended)

**Summary:** Keep BesoGo as the board renderer. Add a separate SVG overlay layer on top for score dots, PV previews, and candidate highlights. Restructure the HTML layout to a 3-column grid with the tree/analysis in a right panel.

**Pros:**
- Zero risk to existing BesoGo functionality
- Overlays are independent — easy to toggle on/off
- Layout changes are CSS-only (grid restructure)
- Smallest change surface area

**Cons:**
- Coordinate mapping between BesoGo SVG and overlay SVG requires careful alignment
- Two SVG layers may have z-index/click-through issues

**Files touched:** ~10 files (8 modified, 2 new)
**Effort:** ~15h

---

## Option B: Replace BesoGo with GhostBan

**Summary:** Replace BesoGo entirely with GhostBan board library, which has built-in analysis overlay support. Rebuild the tree panel.

**Pros:**
- GhostBan has native analysis markup support
- Cleaner long-term architecture

**Cons:**
- High risk — new library, new bugs, new learning curve
- Tree panel must be rebuilt from scratch
- Previous GUI initiative already evaluated and chose BesoGo for stability

**Files touched:** ~15+ files (most of gui/src/ rewritten)
**Effort:** ~30h+

---

## Option C: Custom Canvas Board

**Summary:** Replace BesoGo with a custom canvas-based board renderer that has native overlay support.

**Pros:**
- Full control over rendering
- No third-party library constraints

**Cons:**
- Massive effort — rebuilding what BesoGo already does
- Violates CLAUDE.md "buy, don't build" principle
- Previous GUI initiative explicitly rejected this approach

**Files touched:** ~20+ files
**Effort:** ~50h+

---

## Selected: Option A — Overlay-on-BesoGo

Rationale: Lowest risk, smallest change surface, preserves existing working functionality. The overlay approach is proven (GoProblems itself overlays analysis on its board renderer). Coordinate alignment is solvable by reading BesoGo's SVG viewBox dimensions.
