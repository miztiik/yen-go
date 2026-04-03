# Renderer Analysis: Canvas vs SVG (Goban Library)

**Last Updated**: 2026-02-17  
**Status**: Implemented — SVG is now the default renderer  
**Decision**: Switch default renderer from Canvas to SVG  
**Supersedes**: Previous rationale in `svg-board.md` (Spec 132)

> **Important Discovery**: The SVG renderer uses **Shadow DOM** (`attachShadow({ mode: 'open' })`)  
> for style isolation. SVG elements are not accessible via regular `document.querySelector()` — they  
> live inside `.goban-board-container.shadowRoot`. The move tree SVG is similarly inside the  
> inner container's shadow root. External CSS selectors targeting `svg` or `canvas` inside  
> the goban containers will not apply (the goban library handles its own styling internally  
> via `adoptedStyleSheets`).

> **See also**:
>
> - [Reference: Go Board JS Libraries](../../reference/go-board-js-libraries-analysis.md) — Full library comparison
> - [Reference: Solution Tree Visualization](../../reference/solution-tree-visualization-analysis.md) — Tree renderer deep dive
> - [Architecture: Goban Integration](goban-integration.md) — How goban is wired into our app
> - [Architecture: Board Rendering](svg-board.md) — Board element hierarchy

---

## 1. Context

We use the OGS [goban library](https://github.com/online-go/goban) v8.3.147 for board rendering and puzzle interaction. The library ships **two renderers** with identical APIs:

- **`GobanCanvas`** — Canvas 2D with stacked `<canvas>` layers (our current default)
- **`SVGRenderer`** — SVG DOM with `<g>`/`<use>` elements and Shadow DOM

Our code already supports both via `getRendererPreference()` in `useGoban.ts`, with Canvas as default and SVG as opt-in fallback.

## 2. Key Finding: OGS Uses SVG as Production Default

From OGS production source (`ThemePreferences.tsx`):

```tsx
<PreferenceLine title={_("Use old canvas goban renderer")}>
  <Toggle
    checked={canvas_enabled === "enabled"}
    onChange={(tf) => {
      if (tf) {
        setGobanRenderer("canvas");
      } else {
        setGobanRenderer("svg");
      }
    }}
  />
</PreferenceLine>
```

**OGS labels Canvas as "old"**. SVG is their production default. Canvas is a legacy toggle for users who prefer it.

## 3. Technical Comparison

### 3.1 Rendering Architecture

| Aspect               | GobanCanvas (current)                                    | SVGRenderer (recommended)                   |
| -------------------- | -------------------------------------------------------- | ------------------------------------------- |
| Board element        | 3 stacked `<canvas>` (Shadow, Stone, Pen)                | Single `<svg>` with `<g>` layers            |
| Stone rendering      | Pre-rendered off-screen canvas → `drawImage()`           | SVG `<defs>` gradients → `<use>` references |
| Grid lines           | Redrawn per cell per `drawSquare()`                      | Single `<path>`, cached until `force_clear` |
| Text (labels, marks) | `ctx.fillText()` — bitmap, blurs on zoom                 | SVG `<text>` — vector, scales perfectly     |
| Incremental updates  | Hash-string comparison → full cell clear+redraw          | `GCell` memoization → surgical DOM updates  |
| HDPI                 | `createDeviceScaledCanvas()` + pixel ratio math          | Native — infinite resolution by design      |
| iOS support          | `allocateCanvasOrError()` for canvas pixel budget limits | No pixel budget limits                      |
| Style isolation      | None (external CSS can interfere)                        | Shadow DOM auto-detected                    |
| Move tree            | Canvas `<canvas>` element                                | SVG `<svg>` element                         |

### 3.2 What We Gain

1. **Crisp text at all sizes** — Coordinate labels, move numbers render as vectors (no bitmap blur)
2. **No iOS canvas allocation failures** — SVG has no pixel budget limits
3. **Better incremental rendering** — GCell memoization, only changed intersections update
4. **Shadow DOM isolation** — Prevents app CSS from interfering with goban internals
5. **OGS bug-fix alignment** — Development effort upstream focuses on SVG renderer
6. **Better accessibility** — SVG elements in DOM tree, accessible to screen readers

### 3.3 What We Lose

1. **Initial render speed** — SVG builds ~361 `<g>` elements for 19×19 (negligible for tsumego)
2. **Memory profile** — SVG DOM nodes vs Canvas pixel buffers (negligible for tsumego)
3. **Canvas-specific CSS becomes dead** — `.ShadowLayer`, `.StoneLayer`, `.PenLayer` rules match nothing (harmless)

### 3.4 Theme & Stone Quality

Previous rationale (Spec 132) claimed Canvas has "Phong-shaded" stones while SVG has "flat fills". **This is incorrect.** Both renderers use the same theme system:

- Shell/Slate themes call `preRenderBlackSVG()`/`preRenderWhiteSVG()` for SVG, which create gradient-based stone defs with specular highlights via SVG `<radialGradient>` elements
- The visual quality is equivalent — both renderers produce realistic stone shading
- Custom board colors (`customBoardColor`, `customBoardLineColor`) work identically in both

## 4. What Goban Is Used For (Functional Surface)

Goban provides exactly **two capabilities** we consume:

| Function            | Goban APIs Used                                                                                                                                                                                                                                                                                  | Renderer-Specific?                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------- |
| **Board rendering** | Constructor, `setSquareSizeBasedOnDisplayWidth()`, `computeMetrics()`, `redraw()`, `setColoredCircles()`, `draw_*_labels`, `setLabelPosition()`                                                                                                                                                  | No — all on shared `Goban` base class |
| **Puzzle engine**   | `on('puzzle-correct-answer')`, `on('puzzle-wrong-answer')`, `on('puzzle-place')`, `on('update')`, `showFirst()`, `showNext()`, `showPrevious()`, `prevSibling()`, `nextSibling()`, `enableStonePlacement()`, `disableStonePlacement()`, `engine.cur_move`, `engine.move_tree`, `engine.jumpTo()` | No — all on shared `Goban` base class |

**Zero APIs are renderer-specific.** The config interfaces are literally identical (`CanvasRendererGobanConfig === SVGRendererGobanConfig === GobanConfig`).

## 5. Our Customizations — All Renderer-Agnostic

| Customization            | Location                                                  | Works with SVG?                       |
| ------------------------ | --------------------------------------------------------- | ------------------------------------- |
| Dark/light board colors  | `goban-init.ts` (`customBoardColor` callback)             | ✅ Yes                                |
| Shell/Slate stones       | `goban-init.ts` (`getSelectedThemes`)                     | ✅ Yes                                |
| Unified gray tree colors | `goban-init.ts` (`MoveTree.line_colors`)                  | ✅ Yes                                |
| Sound config             | `goban-init.ts` (`getSoundEnabled`, `getSoundVolume`)     | ✅ Yes                                |
| Responsive resize        | `GobanContainer.tsx` (`setSquareSizeBasedOnDisplayWidth`) | ✅ Yes                                |
| Board centering          | `GobanContainer.tsx` (`computeMetrics`)                   | ✅ Yes                                |
| Label toggle             | `SolverView.tsx` (`setLabelPosition`)                     | ✅ Yes                                |
| Hint marks               | `SolverView.tsx` (`setColoredCircles`)                    | ✅ Yes                                |
| Canvas layer CSS         | `app.css` (`.ShadowLayer`, `.StoneLayer`, `.PenLayer`)    | 🟡 Dead CSS (harmless, cleanup later) |

## 6. Changes Made

### 6.1 Default Renderer (`useGoban.ts`)

```typescript
// BEFORE
return "canvas";

// AFTER
return "svg";
```

### 6.2 CSS Tree Container Selector (`app.css`)

```css
/* BEFORE */
[data-testid="solution-tree-container"] canvas { ... }

/* AFTER — added SVG selector as fallback for non-Shadow-DOM browsers */
[data-testid="solution-tree-container"] canvas,
[data-testid="solution-tree-container"] svg { ... }
```

Note: In browsers supporting Shadow DOM (all modern browsers), the goban SVG lives inside a shadow root, so the external CSS selector doesn't apply. The goban library manages SVG styling internally via `adoptedStyleSheets`. The CSS fallback is harmless.

### 6.3 Unit Test Description (`useGoban.test.ts`)

Updated misleading test name from `should return "auto"` to `should default to "svg"`.

### 6.4 Doc Comment (`useGoban.ts`)

Updated hook JSDoc to document SVG as defaults and Shadow DOM behavior.

## 7. Downstream Impacts

| Area                      | Impact                                                         |
| ------------------------- | -------------------------------------------------------------- |
| Puzzle solving            | None — events fire identically                                 |
| Move tree                 | None — rendered as SVG `<svg>` instead of Canvas `<canvas>`    |
| Hints                     | None — `setColoredCircles()` works on both                     |
| Transforms                | None — transforms modify SGF before goban                      |
| Auto-viewport/zoom        | None — `bounds` config shared                                  |
| Sound                     | None — callbacks shared                                        |
| Layout/theming            | None — our CSS controls layout; goban controls board internals |
| Visual tests (Playwright) | **Screenshots will differ** — update baselines                 |
| Unit tests                | None — tests mock goban                                        |

## 8. GoProblems.com Comparison

GoProblems.com uses a **fully proprietary** Canvas 2D engine (not a reusable library). Their solution tree is tightly coupled to their engine and cannot be extracted.

No alternative JS library offers Goban's combination of: puzzle mode, TypeScript types, active maintenance (252 releases), Apache 2.0 license.

**Recommendation**: Keep goban, switch to SVG renderer, enhance tree visualization within goban's APIs or via custom Preact component reading `goban.engine.move_tree`.

## 9. Solution Tree Enhancement Roadmap

| Phase   | Description                                          | Approach                                                       |
| ------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| Phase 1 | Switch to SVG renderer                               | Config change only                                             |
| Phase 2 | Enhance tree colors (correct=green, wrong=red paths) | `MoveTree.line_colors` override + CSS                          |
| Phase 3 | Custom tree component (GoProblems-style)             | Preact SVG reading `MoveTreeJson`, keep goban for board+engine |

---

_This analysis supersedes the Canvas-preference rationale in Spec 132 / `svg-board.md`._
