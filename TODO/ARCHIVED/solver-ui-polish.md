# Solver UI Polish — OGS-Aligned Board, Toolbar, Feedback & Sound

> **Created:** 2026-02-16
> **Updated:** 2026-02-17
> **Status:** Ready for implementation
> **Scope:** Frontend only — CSS, components, icons, audio logic
> **Reference:** OGS source: https://github.com/online-go/online-go.com
> **Verification:** Playwright pixel-comparison screenshots before/after
> **Test file:** `frontend/tests/e2e/specs/solver-ui-polish.spec.ts`

---

## Overview

13 tasks (T01–T12 active, T13 cancelled, T14 added) for the puzzle solver UI, informed by 1P Go professional and UI/UX expert review.
All changes target the shared `SolverView` component used by **both** technique/tag pages and collection pages.
No backend, pipeline, or architectural changes.

---

## Changes

### T01 — Board Shadow (OGS-style 3D elevation)
- [ ] **File:** `frontend/src/styles/app.css` → `.goban-container`
- [ ] Add subtle right+bottom box-shadow: `box-shadow: 2px 2px 6px rgba(0,0,0,0.15)`
- [ ] OGS applies a light shadow giving the board a "lifted off the page" feel
- [ ] Shadow must persist regardless of coordinate label toggle state
- [ ] Shadow lives on `.goban-container` (outer wrapper), NOT on internal canvas layers
- [ ] Dark mode: verify shadow remains visible (may need `rgba(0,0,0,0.3)` for dark theme)
- [ ] **Playwright:** Screenshot board area with and without coordinates toggled

### T02 — Remove Non-Standard Board Padding
- [ ] **File:** `frontend/src/styles/app.css` → `.Goban { padding: 4px }` (line ~538)
- [ ] Remove `padding: 4px` — this creates uneven gaps between grid edges and board boundary
- [ ] Goban's internal `computeMetrics()` handles proper stone/grid sizing at edges
- [ ] The half-square margin between outermost intersection and canvas edge is **standard Go board rendering** (same as OGS) — NOT a bug
- [ ] **Playwright:** Screenshot board edges to verify stones at J8/J9 are NOT clipped

### T03 — Toolbar → Single Horizontal Strip (OGS layout)
- [ ] **File:** `frontend/src/components/Transforms/TransformBar.tsx`
- [ ] **File:** `frontend/src/components/Solver/SolverView.tsx` (Section 1, lines ~464–493)
- [ ] Flatten ALL control buttons into one compact horizontal strip:
  `[FlipH] [FlipV] [FlipDiag] [RotateCCW] [RotateCW] [SwapColors] | [Coords] [Zoom] [Hint]`
- [ ] Reduce button size from 40×40px to ~32×32px (`w-8 h-8`)
- [ ] Remove the rounded box/card background from TransformBar
- [ ] Add consistent hover feedback: `hover:bg-[--color-accent]/10 hover:text-[--color-accent]`
- [ ] Use `gap-1` spacing (tighter than current `gap-2`)
- [ ] Accept new props for zoom toggle state and hint action, OR pass them into TransformBar
- [ ] Move Hint button from Section 2 into the strip as icon-only with `aria-label="Hint (N remaining)"`
- [ ] Keep the hint overlay/text display in Section 2 (just the button moves)
- [ ] **Playwright:** Screenshot toolbar strip at desktop and mobile widths

### T04 — Replace ZoomIcon with Expand/Maximize Icon
- [ ] **File:** `frontend/src/components/shared/icons/ZoomIcon.tsx`
- [ ] Replace magnifying glass SVG with OGS-style four-diagonal-arrows expand icon
- [ ] OGS uses a "fit to screen" / "maximize" cross-arrows icon for board zoom
- [ ] Keep the same `IconProps` interface (`size`, `className`)
- [ ] SVG: Four arrows pointing outward from center (or inward when zoomed)
- [ ] **Playwright:** Screenshot toolbar to verify new icon renders

### T05 — Replace CoordsIcon with "9A" Text Icon (OGS style)
- [ ] **File:** `frontend/src/components/shared/icons/CoordsIcon.tsx`
- [ ] Replace grid/crosshair SVG with text-based "9" + superscript "A" icon
- [ ] OGS shows `9` with small `A` in the top-right corner — compact coordinate indicator
- [ ] Implementation: SVG with `<text>` elements, `font-weight: bold`, `currentColor`
- [ ] Keep the same `IconProps` interface
- [ ] **Playwright:** Screenshot toolbar to verify new icon renders

### T06 — Remove Duplicate Sound on Puzzle Complete
- [ ] **File:** `frontend/src/hooks/usePuzzleState.ts` (lines ~298–314)
- [ ] Remove `audioService.play('complete')` call (the `pling.webm` sound)
- [ ] Remove the entire `completeTimeoutRef` setTimeout block that checks for terminal nodes
- [ ] Keep `dispatch({ type: 'PUZZLE_COMPLETE' })` — move it inline (no timeout needed for dispatch)
- [ ] Result: Only `audioService.play('correct')` plays on every correct move (including the final one)
- [ ] No double-sound on puzzle completion
- [ ] **Playwright:** Cannot verify audio via screenshot — manual verification required

### T07 — Answer Feedback Banner Styling
- [ ] **File:** `frontend/src/components/Solver/SolverView.tsx` (Section 4, lines ~582–598)
- [ ] **Correct banner** (line ~591): Already has `bg-[--color-success-bg] text-[--color-success]` with green tint ✓
- [ ] **Incorrect banner** (line ~583): Already has `bg-[--color-error-bg] text-[--color-error]` with red tint ✓
- [ ] **Verify via Playwright:** Take screenshots in both "correct" and "incorrect" states
- [ ] Confirm the green/red tints are clearly visible and contrast-compliant
- [ ] The SGF `C[Correct!]` comment display (line ~514) uses neutral styling — this is correct behavior (it's a comment, not a status banner)

### T08 — Board Message (Self-Atari Warning) → Amber/Warning Style
- [ ] **File:** `frontend/src/components/Solver/SolverView.tsx` (Section 3.5, lines ~572–580)
- [ ] **File:** `frontend/src/hooks/useGoban.ts` (line ~204) — currently auto-dismisses after 4 seconds
- [ ] Current styling: `bg-[--color-warning-bg] text-[--color-warning] border-[--color-warning-border]`
- [ ] Verify amber/warning theme tokens exist and render clearly
- [ ] Consider making the warning persist longer (e.g., 6s) or until next action instead of 4s auto-dismiss
- [ ] Ensure icon (info circle) is appropriate for warning context
- [ ] **Playwright:** Screenshot board message when self-atari is attempted (requires goban interaction)

### T09 — ProblemNav Consistency (Dots + Progress for All Puzzle Counts)
- [ ] **File:** `frontend/src/components/ProblemNav/ProblemNav.tsx`
- [ ] Current behavior: `totalProblems <= 20` → dots, `> 20` → text counter "N / M"
- [ ] Both modes already show: prev/next chevrons, progress bar, completion %, streak badge
- [ ] The visual difference is cosmetic: dots vs counter text — both fully functional
- [ ] For technique pages with 30+ puzzles, the "1 / 30" counter with chevrons is the correct UX
- [ ] For collections with ≤20 puzzles, clickable dots are the correct UX
- [ ] **No code change needed** — verify via Playwright that both modes render correctly
- [ ] Ensure the progress bar, completion %, and streak badge show in both modes
- [ ] **Playwright:** Screenshot `/technique/ko` (counter mode) and `/collections/cho-chikun-life-death-elementary` (dots mode)

### T10 — Sidebar Width + Board Right Padding
- [ ] **File:** `frontend/src/styles/app.css` (lines ~740–756, desktop media query)
- [ ] Current sidebar: `width: 360px; max-width: 400px`
- [ ] Increase to: `width: 400px; max-width: 440px` (or similar — evaluate visually)
- [ ] Add right-side spacing to the board column: `padding-right: 12px` or `gap` on parent
- [ ] The board has ample left-side space — redistributing some to the right panel improves balance
- [ ] **Squashed landscape** (lines ~759–770): `max-width: 350px` → increase to `380px`
- [ ] Verify mobile layout is not adversely affected (sidebar goes full-width below breakpoint)
- [ ] **Playwright:** Screenshot full solver layout at 1280×800 and 768×1024 viewports

### T11 — Solution Tree Padding
- [ ] **File:** `frontend/src/components/Solver/SolverView.tsx` (Section 5, lines ~613–622)
- [ ] Current: `p-2` (8px) padding inside the tree container
- [ ] Increase to: `p-3` (12px) or `p-4` (16px) for better visual breathing room
- [ ] The tree canvas renders very close to the container corners — needs more inset
- [ ] Add `mt-1` vertical separation from answer banner above
- [ ] **Playwright:** Screenshot solution tree in review mode

### T12 — Collection Icon Redesign
- [ ] **File:** `frontend/src/components/shared/icons/CollectionIcon.tsx`
- [ ] Current: Folder/directory SVG icon — looks like a file system folder
- [ ] Replace with: Stacked books, stacked cards, or a curated set icon
- [ ] Options (consult UI/UX expert):
  - Stacked horizontal lines (book spine view)
  - Grid of 4 small squares (curated set)
  - Book with bookmark
  - Cards fanning out (collection metaphor)
- [ ] Must work at 11px size (used in metadata badges) and 16px+ (used elsewhere)
- [ ] Keep `currentColor` fill/stroke for theme compatibility
- [ ] **Playwright:** Screenshot collection badge in sidebar metadata section

### ~~T13 — Thicker Board Grid Lines~~ **CANCELLED**
> Cancelled 2026-02-17. Canvas renderer hardcodes `ctx.lineWidth = 1` (goban.js L1510).
> Any fix requires goban source modification or post-construction hooks — both violate
> the "zero goban package changes" constraint. OGS gets thicker lines because they use
> the **SVG renderer** (proportional `ss * 0.02`) — see OGS `configure-goban.tsx`:
> `setGobanRenderer("svg")` is their default. Canvas is behind an experiment flag.
> May revisit if we switch to SVG renderer in a future task.

### T14 — Unify Solution Tree Branch Colors
- [ ] **File:** `frontend/src/hooks/useGoban.ts` or `frontend/src/lib/goban-init.ts`
- [ ] The solution tree currently draws branch lines in 7 cycling colors:
  `#ff0000` (red), `#00ff00` (green), `#0000ff` (blue), `#00ffff` (cyan),
  `#ffff00` (yellow), `#FF9A00` (orange), `#9200FF` (purple)
- [ ] This rainbow effect is distracting — branches should use a single muted tone
- [ ] **Approach:** Override the static property at runtime after importing from goban:
  ```ts
  import { MoveTree } from "goban";
  MoveTree.line_colors = ["#9ca3af","#9ca3af","#9ca3af","#9ca3af","#9ca3af","#9ca3af","#9ca3af"];
  ```
- [ ] Use a neutral gray (`#9ca3af` — Tailwind gray-400) for all branch lines
- [ ] Trunk lines remain black (`#000000`) — this is hardcoded in goban and correct
- [ ] Ring colors (green=correct, red=wrong, blue=comment) are hardcoded inside methods — NOT overridable
- [ ] Isobranch colors (`MoveTree.isobranch_colors`) can also be unified if desired:
  `MoveTree.isobranch_colors = { strong: "#6b7280", weak: "#d1d5db" };`
- [ ] **Constraint:** This is a runtime property override, NOT a goban file modification — compliant with project rules
- [ ] **Note — Straight lines and vertical layout:** Branch lines use `quadraticCurveTo` (curved) and layout
  is always horizontal (left-to-right). Both are hardcoded in goban's `move_tree_drawPath()` and
  `MoveTree.layout()` methods — not configurable without goban source changes. We accept curves as-is.
- [ ] **Playwright:** Screenshot solution tree in review mode to verify uniform branch color

---

## Files Summary

| File | Changes |
|------|---------|
| `frontend/src/styles/app.css` | T01 shadow, T02 padding removal, T10 sidebar width |
| `frontend/src/components/Solver/SolverView.tsx` | T03 toolbar integration, T11 tree padding |
| `frontend/src/components/Transforms/TransformBar.tsx` | T03 strip layout, smaller buttons, new props |
| `frontend/src/components/shared/icons/ZoomIcon.tsx` | T04 expand icon |
| `frontend/src/components/shared/icons/CoordsIcon.tsx` | T05 "9A" text icon |
| `frontend/src/components/shared/icons/CollectionIcon.tsx` | T12 redesign |
| `frontend/src/hooks/usePuzzleState.ts` | T06 remove complete sound |
| `frontend/src/hooks/useGoban.ts` | T08 warning duration (optional), T14 branch color override |
| `frontend/src/components/ProblemNav/ProblemNav.tsx` | T09 verify only |

---

## Playwright Verification Strategy

**Test file:** `frontend/tests/e2e/specs/solver-ui-polish.spec.ts`
**Config:** Uses `playwright.e2e.config.ts` (Vite dev server at `:5173`)

### Screenshot Capture Points

| Test Name | URL | What to capture | Viewport |
|-----------|-----|-----------------|----------|
| Board shadow | `/technique/ko` | `.goban-container` element | 1280×800 |
| Board edges | `/technique/ko` | Board canvas (check stone clipping at edges) | 1280×800 |
| Toolbar strip | `/technique/ko` | `[data-section="transforms"]` | 1280×800 |
| Toolbar mobile | `/technique/ko` | `[data-section="transforms"]` | 375×667 |
| Correct banner | `/technique/ko` | `[data-testid="answer-banner"]` after solving | 1280×800 |
| Incorrect banner | `/technique/ko` | `[data-testid="answer-banner"]` after wrong move | 1280×800 |
| Board message | `/technique/ko` | `[data-testid="board-message"]` after self-atari | 1280×800 |
| ProblemNav counter | `/technique/ko` | `[data-testid="puzzle-nav-slot"]` | 1280×800 |
| ProblemNav dots | `/collections/cho-chikun-life-death-elementary` | `[data-testid="puzzle-nav-slot"]` | 1280×800 |
| Full sidebar | `/technique/ko` | `.solver-sidebar-col` | 1280×800 |
| Solution tree | `/technique/ko` (review mode) | `[data-testid="solution-tree-container"]` | 1280×800 |
| Collection icon | `/technique/ko` | Metadata badge area | 1280×800 |
| Layout desktop | `/technique/ko` | Full page | 1280×800 |
| Layout tablet | `/technique/ko` | Full page | 768×1024 |
| Tree branch colors | `/technique/ko` (review mode) | `[data-testid="solution-tree-container"]` | 1280×800 |

### Test Approach

1. **Before screenshots:** Captured at current state before any code changes
2. **After screenshots:** Captured after each change, compared pixel-by-pixel
3. **Pixel comparison:** Use Playwright's `toHaveScreenshot()` with `maxDiffPixelRatio` threshold
4. **Interactive states:** Use Playwright actions (click wrong move, click correct move) to trigger answer banners

---

## Dependencies & Constraints

- **No goban package modifications** — all changes via CSS, config, callbacks, runtime property overrides
- **No new npm dependencies** — pure SVG icons, CSS changes, audio logic
- **No backend changes** — frontend-only scope
- **OGS alignment checked** — shadow, toolbar, icons reference OGS patterns
- **Dark mode verified** — all CSS tokens have dark mode counterparts
- **Responsive verified** — mobile, tablet, desktop, squashed landscape breakpoints tested

---

## Implementation Order

1. T06 (sound fix) — smallest, isolated, no visual impact
2. T01 + T02 (board shadow + padding) — CSS only, high visual impact
3. T04 + T05 (icon replacements) — SVG files only
4. T12 (collection icon) — SVG file only
5. T03 (toolbar strip) — component refactor, medium complexity
6. T10 (sidebar width) — CSS media query adjustment
7. T11 (solution tree padding) — minor Tailwind class change
8. T14 (tree branch colors) — one-liner runtime override
9. T07 + T08 + T09 (verify feedback banners + warning + nav) — verification pass
10. Playwright before/after screenshots throughout

---

## OGS Reference Notes

### Renderer Selection
OGS defaults to **SVG renderer** (`setGobanRenderer("svg")`). Canvas is behind `experiments.canvas` flag.
See: `online-go.com/src/lib/configure-goban.tsx`

### Implications
- SVG renderer: proportional grid lines (`ss * 0.02`), CSS-targetable DOM elements
- Canvas renderer (yen-go default): 1px hardcoded grid lines, pixel-based rendering
- Switching renderer is a future consideration — not in scope for this plan

---

## Expert Consultation Notes

### 1P Go Professional Review
- Grid lines stopping at outermost intersections = standard Go board rendering (correct)
- Half-square kaya margin beyond edge intersections = standard (correct)
- Star points (hoshi) must remain visible and correctly placed
- Board shadow is aesthetic and does not affect game mechanics
- Stone placement at board edges (J-column on 9×9) must not be visually clipped

### UI/UX Expert Review
- OGS toolbar strip is compact, icon-only, with subtle hover states — follow this pattern
- "9A" coordinate icon is immediately recognizable; grid/crosshair is ambiguous
- Expand/maximize icon (four arrows) is standard for zoom-to-fit; magnifying glass implies search
- Right panel width of 360px is tight for progress bars + dots + metadata — 400px recommended
- Solution tree needs breathing room (12–16px padding) to avoid "cramped" feel
- Answer feedback banners should have clear color coding: green success, red error, amber warning
- Board message (self-atari) auto-dismiss at 4s is too fast — consider 6s or until next interaction
- Collection icon should evoke "curated set" not "file system" — stacked books or cards preferred
