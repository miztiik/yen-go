# Board Rendering Architecture

**Last Updated**: 2026-02-11  
**Status**: Approved for Implementation  
**Decision**: Canvas rendering (default) via goban library, SVG available as fallback  
**Updated by**: Spec 132 (Board UI Visual Polish)

## Overview

The Go board is rendered using the [OGS goban library](https://github.com/online-go/goban) (v8.3.147+). **Canvas is the default renderer**, enabling Phong-shaded Shell/Slate stone rendering with realistic highlights and drop shadows. SVG is available as a user-configurable fallback but produces flat-fill stones without shading.

## Design Rationale

### Why Canvas over SVG (Spec 132)

| Aspect        | Canvas (goban)                                        | SVG (goban)                      | Decision    |
| ------------- | ----------------------------------------------------- | -------------------------------- | ----------- |
| Stone quality | Phong-shaded, Shell/Slate themes, specular highlights | Flat fills, uniform colors       | **Canvas**  |
| Board texture | Kaya wood grain via texture image                     | Solid color only                 | **Canvas**  |
| Dark mode     | "Night Play" built-in theme                           | Manual CSS overrides             | **Canvas**  |
| Performance   | Pre-rendered stone sprites, lazy updates              | DOM thrashing with many elements | **Canvas**  |
| Accessibility | goban provides keyboard nav + ARIA                    | Same (goban handles both)        | Neutral     |
| Debugging     | Opaque pixel buffer                                   | DOM inspection                   | SVG (minor) |

**Conclusion**: Canvas provides dramatically better visual quality through Phong-shaded stones and texture support. The goban library handles accessibility equally in both modes. Canvas is the default; users can switch to SVG via localStorage preference.

### Renderer Selection

```typescript
// frontend/src/hooks/useGoban.ts
function getRendererPreference(): RendererPreference {
  const stored = localStorage.getItem(RENDERER_PREFERENCE_KEY);
  if (stored === "svg" || stored === "canvas" || stored === "auto")
    return stored;
  return "canvas"; // Default: Canvas for Shell/Slate stone rendering
}
```

## Board Structure

### SVG Element Hierarchy

```
<svg viewBox="0 0 {width} {height}" width="100%" height="100%">
  <rect class="board-background" />          <!-- Board wood texture -->
  <g class="board-lines">                    <!-- Grid lines -->
    <rect class="outer-border" />
    <path class="inner-lines" />
  </g>
  <g class="hoshi-points" />                 <!-- Star points -->
  <g class="coordinate-labels" />            <!-- A-T, 1-19 labels -->
  <g class="shadow-layer" filter="blur" />   <!-- Stone shadows -->
  <g class="stone-layer" />                  <!-- Placed stones -->
  <g class="markup-layer" />                 <!-- Circles, squares, labels -->
  <g class="highlight-layer" />              <!-- Positional highlights -->
  <g class="hover-layer" opacity="0.35" />   <!-- Ghost stones on hover -->
  <g class="event-targets" />                <!-- Invisible click targets -->
</svg>
```

### ViewBox and Scaling

The SVG uses a fixed internal coordinate system via `viewBox`, allowing automatic scaling to any container size:

```typescript
const CELL_SIZE = 88; // Internal units per cell (including line width)
const COORD_MARGIN = 75; // Margin for coordinate labels
const EXTRA_MARGIN = 6; // Edge padding

function calculateViewBox(sizeX: number, sizeY: number, showCoords: boolean) {
  const margin = (showCoords ? COORD_MARGIN : 0) + EXTRA_MARGIN;
  const width = 2 * margin + sizeX * CELL_SIZE;
  const height = 2 * margin + sizeY * CELL_SIZE;
  return `0 0 ${width} ${height}`;
}
```

**Key Principle**: The SVG element uses `width="100%"` and `height="100%"` while `viewBox` defines the internal coordinate system. The browser handles all scaling automatically, maintaining aspect ratio.

## Viewport and Partial Board Support

### Region Types

Puzzles can specify a `region` property indicating which portion of the board to display:

```typescript
interface Region {
  corner: "TL" | "TR" | "BL" | "BR" | "T" | "B" | "L" | "R" | "C"; // Position
  width: number; // Columns to show (1-19)
  height: number; // Rows to show (1-19)
}
```

**Corner codes**:

- `TL` = Top-Left, `TR` = Top-Right, `BL` = Bottom-Left, `BR` = Bottom-Right
- `T` = Top-Center, `B` = Bottom-Center, `L` = Left-Center, `R` = Right-Center
- `C` = Center

### ViewBox Adjustment for Partial Boards

When a region is specified, the `viewBox` is adjusted to show only that portion:

```typescript
function calculatePartialViewBox(
  fullSizeX: number,
  fullSizeY: number,
  region: Region,
  showCoords: boolean,
): string {
  const margin = (showCoords ? COORD_MARGIN : 0) + EXTRA_MARGIN;

  // Calculate the starting position based on corner
  const startX = getStartX(region.corner, fullSizeX, region.width);
  const startY = getStartY(region.corner, fullSizeY, region.height);

  // ViewBox shows only the region
  const viewX = margin + (startX - 1) * CELL_SIZE;
  const viewY = margin + (startY - 1) * CELL_SIZE;
  const viewWidth = region.width * CELL_SIZE + 2 * EXTRA_MARGIN;
  const viewHeight = region.height * CELL_SIZE + 2 * EXTRA_MARGIN;

  return `${viewX} ${viewY} ${viewWidth} ${viewHeight}`;
}

function getStartX(
  corner: string,
  fullSize: number,
  regionWidth: number,
): number {
  switch (corner) {
    case "TL":
    case "BL":
    case "L":
      return 1;
    case "TR":
    case "BR":
    case "R":
      return fullSize - regionWidth + 1;
    case "T":
    case "B":
    case "C":
      return Math.floor((fullSize - regionWidth) / 2) + 1;
    default:
      return 1;
  }
}
```

### Edge Indicators

When showing a partial board, visual indicators show that the board extends beyond the viewport:

```typescript
function renderEdgeIndicators(region: Region, fullSizeX: number, fullSizeY: number) {
  const indicators: JSX.Element[] = [];

  // Add fade gradient on edges that have more board
  if (hasMoreLeft(region)) {
    indicators.push(<rect class="edge-fade-left" />);
  }
  if (hasMoreRight(region, fullSizeX)) {
    indicators.push(<rect class="edge-fade-right" />);
  }
  // ... similar for top/bottom

  return indicators;
}
```

## Stone Rendering

### SVG Stone Elements

```typescript
function svgStone(
  x: number,
  y: number,
  color: "black" | "white",
): SVGCircleElement {
  const className = color === "black" ? "stone-black" : "stone-white";
  return svgEl("circle", {
    cx: x,
    cy: y,
    r: 42, // Radius in viewBox units
    class: className,
  });
}
```

### CSS Styling for Stones

```css
.stone-black {
  fill: url(#black-gradient);
  stroke: none;
}

.stone-white {
  fill: url(#white-gradient);
  stroke: #333;
  stroke-width: 1;
}

/* Gradients for 3D appearance */
#black-gradient {
  /* Radial gradient from #555 at top-left to #000 at bottom-right */
}

#white-gradient {
  /* Radial gradient from #fff at top-left to #ccc at bottom-right */
}
```

### Stone Shadows

Shadows are rendered in a separate layer with blur filter:

```typescript
function svgShadow(x: number, y: number): SVGCircleElement {
  return svgEl("circle", {
    cx: x + 2, // Offset right
    cy: y + 4, // Offset down
    r: 43,
    fill: "black",
    opacity: 0.32,
    filter: "url(#blur)",
  });
}
```

## Positional Highlights

### Highlight Types

Positional highlights indicate areas of interest for hints or feedback:

| Type      | Visual               | Use Case                   |
| --------- | -------------------- | -------------------------- |
| Circle    | Empty circle outline | Mark a point               |
| Square    | Empty square outline | Mark a point (alternative) |
| Triangle  | Empty triangle       | Important point            |
| Cross (X) | X mark               | Wrong move / removal       |
| Plus (+)  | Plus mark            | Last move indicator        |
| Block     | Filled square        | Territory marker           |
| Label     | Text (A-Z, 1-99)     | Variation labels           |

### Implementation

```typescript
function svgCircle(x: number, y: number, color: string): SVGCircleElement {
  return svgEl("circle", {
    cx: x,
    cy: y,
    r: 27,
    stroke: color,
    "stroke-width": 8,
    fill: "none",
  });
}

function svgSquare(x: number, y: number, color: string): SVGRectElement {
  return svgEl("rect", {
    x: x - 23,
    y: y - 23,
    width: 46,
    height: 46,
    stroke: color,
    "stroke-width": 8,
    fill: "none",
  });
}

function svgLabel(
  x: number,
  y: number,
  color: string,
  label: string,
): SVGTextElement {
  const fontSize = label.length === 1 ? 72 : label.length === 2 ? 56 : 36;
  const element = svgEl("text", {
    x: x,
    y: y,
    dy: ".65ex", // Vertical centering
    "font-size": fontSize,
    "text-anchor": "middle",
    fill: color,
  });
  element.textContent = label;
  return element;
}
```

### Color Palette for Highlights

```typescript
const HIGHLIGHT_COLORS = {
  red: "#be0119", // Darker red (wrong move, marked variant)
  lightRed: "#ff474c", // Lighter red (auto-marked variant)
  blue: "#0165fc", // Bright blue (last move)
  purple: "#9a0eea", // Purple (variant + last move)
  grey: "#929591", // Neutral
  gold: "#dbb40c", // Tool selection
  turquoise: "#06c2ac", // Navigation selection
};
```

## Responsive Scaling

### Container CSS

```css
.board-container {
  width: 100%;
  max-width: min(85vh, 600px); /* Maintain aspect ratio */
  aspect-ratio: 1 / 1; /* Square for full board */
  margin: 0 auto;
}

.board-container svg {
  width: 100%;
  height: 100%;
}
```

### Automatic Scaling Behavior

1. **Desktop (landscape)**: Board fills available height, centered horizontally
2. **Mobile (portrait)**: Board fills available width, aspect ratio maintained
3. **Partial boards**: Aspect ratio adjusts to region dimensions

### Breakpoint Handling

```typescript
interface BoardLayoutProps {
  maxWidth?: string; // Default: 'min(85vh, 100%)'
  orientation?: "auto" | "landscape" | "portrait";
  transitionWidth?: number; // Default: 600px
}
```

## Event Handling

### Click Targets

Invisible rectangles cover each intersection for click detection:

```typescript
function addEventTargets(sizeX: number, sizeY: number) {
  for (let i = 1; i <= sizeX; i++) {
    for (let j = 1; j <= sizeY; j++) {
      const target = svgEl("rect", {
        x: svgPos(i) - CELL_SIZE / 2,
        y: svgPos(j) - CELL_SIZE / 2,
        width: CELL_SIZE,
        height: CELL_SIZE,
        opacity: 0,
      });
      target.addEventListener("click", handleClick(i, j));
      target.addEventListener("mouseover", handleHover(i, j));
      target.addEventListener("mouseout", handleHoverOut(i, j));
    }
  }
}
```

### Touch Interface Detection

```typescript
let isTouchInterface = false;

function detectTouch() {
  container.addEventListener(
    "touchstart",
    () => {
      isTouchInterface = true;
      // Remove hover layer for touch devices
      svg.removeChild(hoverGroup);
    },
    { once: true },
  );
}
```

## Performance Considerations

### Layer Updates

Only redraw layers that changed:

```typescript
function update(changes: ChangeSet) {
  if (changes.boardSize) {
    reinitializeBoard(); // Full redraw
  } else if (changes.stones) {
    redrawStones();
    redrawMarkup();
    redrawHover();
  } else if (changes.markup) {
    redrawMarkup();
    redrawHover();
  } else if (changes.tool) {
    redrawHover(); // Only update ghost stone layer
  }
}
```

### Stone Count Limits

Maximum elements for a 19x19 board:

- Stones: 361
- Shadows: 361
- Markup: ~50 (typical)
- Event targets: 361
- **Total**: ~1,200 SVG elements

This is well within SVG performance limits (issues typically start at 10,000+ elements).

## Migration Path

### Current State (Canvas)

The existing `Board.tsx` uses HTML Canvas (882 lines).

### Migration Steps

1. Create new `SvgBoard.tsx` component alongside existing Canvas board
2. Implement core rendering (stones, lines, hoshi)
3. Add markup layer (highlights, labels)
4. Add event handling (clicks, hover)
5. Add partial board support (viewBox adjustment)
6. Feature-flag switch between Canvas and SVG
7. Validate with visual regression tests
8. Remove Canvas implementation

### Backward Compatibility

During migration, both implementations can coexist:

```typescript
// Board selector based on feature flag
export function Board(props: BoardProps) {
  const useSvg = useFeatureFlag('svg-board');
  return useSvg ? <SvgBoard {...props} /> : <CanvasBoard {...props} />;
}
```

## See Also

- [Go Rules Engine](./go-rules-engine.md) - Capture, ko, and liberty calculation
- [Puzzle Solving Flow](./puzzle-solving.md) - How board state integrates with puzzles
- [Reference: Besogo](https://github.com/yewang/besogo) - Source of architecture patterns
