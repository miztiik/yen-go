# Solution Tree / Move Tree Visualization — Deep Analysis

> **Last Updated**: 2026-02-17  
> **Purpose**: Deep technical analysis of how Go/Tsumego solution trees are rendered across major implementations, with actual rendering code, layout algorithms, and comparison for Yen-Go's tree visualization feature.

> **See also**:
>
> - [Reference: Go Board JS Libraries](go-board-js-libraries-analysis.md) — Board library comparison
> - [Architecture: Frontend](../architecture/frontend/) — Yen-Go frontend design decisions
> - [Concepts: SGF Properties](../concepts/sgf-properties.md) — Custom SGF property definitions

---

## Table of Contents

1. [Goban (OGS) Move Tree](#1-goban-yengo-source-move-tree)
2. [BesoGo Tree Panel](#2-besogo-tree-panel)
3. [Sabaki Game Graph](#3-sabaki-game-graph)
4. [yengo-source Solution Tree](#4-goproblemscoms-solution-tree)
5. [Comparison Matrix](#5-comparison-matrix)
6. [Recommendations for Yen-Go](#6-recommendations-for-yen-go)

---

## 1. Goban (OGS) Move Tree

**Source**: `goban` npm package (v8.3.x), `GobanCanvas` class + `MoveTree` class  
**Rendering**: HTML5 Canvas 2D  
**Used by**: [online-go.com](https://online-go.com/)

### 1.1 Architecture Overview

The yengo-source move tree is a **Canvas 2D** renderer with a three-phase pipeline:

1. **Layout** — `MoveTree.layout()` assigns grid positions to every node
2. **Path Drawing** — `move_tree_recursiveDrawPath()` draws connecting lines
3. **Node Drawing** — `move_tree_drawRecursive()` draws stones + labels

The tree renders inside a scrollable container with a single canvas that repositions itself to match the visible viewport (virtual scrolling pattern).

### 1.2 Data Structure

```typescript
class MoveTree {
  // Identity
  id: number; // Unique auto-incremented ID
  x: number; // Board position x (-1 for pass)
  y: number; // Board position y
  player: number; // 1=Black, 2=White
  move_number: number;
  pretty_coordinates: string; // e.g. "D4", "pass"

  // Tree links
  parent: MoveTree | undefined;
  trunk_next: MoveTree | undefined; // Main line continuation
  branches: MoveTree[]; // Variation branches

  // Layout (computed)
  layout_x: number; // Grid column
  layout_y: number; // Grid row
  layout_cx: number; // Pixel center X
  layout_cy: number; // Pixel center Y
  line_color: number; // Index into line_colors array

  // Puzzle annotations
  correct_answer: boolean; // Green ring
  wrong_answer: boolean; // Red ring
  text: string; // Comment text → blue ring

  // Active path tracking
  active_path_number: number; // For highlighting current path

  // Isobranch detection (transposition links)
  isobranches: MoveTree[]; // Nodes with identical board states
  isobranch_hash: string; // Board state hash for detection
}
```

**Key design**: The tree distinguishes between `trunk_next` (main line, always rendered left-to-right at y=0) and `branches` (variations, laid out below). This ensures the main game line is always a straight horizontal line at the top.

### 1.3 Layout Algorithm

The layout is a **recursive column-allocation** algorithm. It assigns each node a `(layout_x, layout_y)` grid position, where X is the move depth (left→right) and Y is the variation index (top→bottom). The trunk always occupies y=0.

```javascript
// MoveTree.layout(x, min_y, layout_hash, line_color)
layout(x, min_y, layout_hash, line_color) {
    // Ensure the layout vector exists for this column
    if (!this.engine.move_tree_layout_vector[x]) {
        this.engine.move_tree_layout_vector[x] = 0;
    }

    // Reset line colors at root
    if (x === 0 && min_y === 0) {
        MoveTree.current_line_color = 0;
    }

    // min_y must be at least one past the highest occupied row in this column
    min_y = Math.max(this.engine.move_tree_layout_vector[x] + 1, min_y);

    // Trunk continuation gets priority: laid out at y=0 in the next column
    if (this.trunk_next) {
        this.trunk_next.layout(x + 1, 0, layout_hash,
            (this.move_number + 1) % MoveTree.line_colors.length);
    }

    // Assign line color if not set
    if (this.line_color === -1) {
        this.line_color = line_color;
    }

    // Lay out each branch below the trunk
    let next_line_color = this.line_color + this.move_number;
    for (let i = 0; i < this.branches.length; ++i) {
        next_line_color %= MoveTree.line_colors.length;
        // Prevent neighboring branches from having the same color
        if (i && next_line_color === this.line_color) {
            next_line_color += 2;
            next_line_color %= MoveTree.line_colors.length;
        }
        const by = this.branches[i].layout(x + 1, min_y, layout_hash,
            i === 0 ? this.line_color : next_line_color++);
        if (i === 0) {
            min_y = Math.max(min_y, by - 1);
        }
        next_line_color++;
    }

    // Trunk nodes are always at y=0
    if (this.trunk) {
        min_y = 0;
    }

    // Assign final position
    this.layout_x = x;
    this.layout_y = min_y;
    layout_hash[x + "," + min_y] = this;

    // Convert grid position to pixel position
    this.layout_cx = Math.floor((this.layout_x + 0.5) * MoveTree.stone_square_size) + 0.5;
    this.layout_cy = Math.floor((this.layout_y + 0.5) * MoveTree.stone_square_size) + 0.5;

    // Update the layout vector (highest occupied row per column)
    this.engine.move_tree_layout_vector[x] =
        Math.max(min_y, this.engine.move_tree_layout_vector[x]);

    // Allocate space for branch lines in the parent column
    if (x) {
        this.engine.move_tree_layout_vector[x - 1] =
            Math.max(min_y - 1, this.engine.move_tree_layout_vector[x - 1]);
    }

    return min_y;
}
```

**Key properties**:

- `move_tree_layout_vector[x]` tracks the highest occupied Y for each column X, preventing overlaps
- Trunk always at y=0, branches fill in below
- `layout_hash` stores `"x,y" → node` mapping for click/hover lookup
- Branch lines are allocated space in the parent column (`x-1`) to prevent line crossings

### 1.4 Static Configuration

```javascript
MoveTree.stone_radius = 11; // Pixels
MoveTree.stone_padding = 3; // Pixels between stones
MoveTree.stone_square_size = (11 + 3) * 2; // = 28 pixels per grid cell

MoveTree.line_colors = [
  "#ff0000", // Red
  "#00ff00", // Green
  "#0000ff", // Blue
  "#00ffff", // Cyan
  "#ffff00", // Yellow
  "#FF9A00", // Orange
  "#9200FF", // Purple
];

MoveTree.isobranch_colors = {
  strong: "#C100FF", // Magenta/purple
  weak: "#A582A3", // Muted purple
};
```

### 1.5 Path Drawing (Quadratic Bezier Curves)

Paths from parent to child are drawn as **quadratic Bezier curves**. The control point is placed at `(child_x - half_cell, child_y)`, creating a smooth curve from the parent position to the child.

```javascript
move_tree_drawPath(ctx, node, viewport) {
    if (node.parent) {
        // Viewport culling for performance
        if (/* ...bounds checks... */) return;

        ctx.beginPath();
        // Trunk lines are black; branch lines use assigned color
        ctx.strokeStyle = node.trunk
            ? "#000000"
            : MoveTree.line_colors[node.line_color];

        const ox = viewport.offset_x;
        const oy = viewport.offset_y;

        // Start at parent center
        ctx.moveTo(node.parent.layout_cx - ox, node.parent.layout_cy - oy);

        // Quadratic Bezier to child center
        // Control point: (child_cx - half_cell, child_cy)
        ctx.quadraticCurveTo(
            node.layout_cx - MoveTree.stone_square_size * 0.5 - ox,
            node.layout_cy - oy,
            node.layout_cx - ox,
            node.layout_cy - oy
        );
        ctx.stroke();
    }
}
```

**Isobranch (transposition) lines** use a different Bezier curve:

```javascript
move_tree_drawIsoBranchTo(ctx, from_node, to_node, viewport) {
    // Determine strong (leaf→interior) vs weak (both interior) direction
    const strong = A.trunk_next == null && A.branches.length === 0
                && (B.trunk_next !== null || B.branches.length !== 0);

    ctx.strokeStyle = MoveTree.isobranch_colors[strong ? "strong" : "weak"];
    ctx.lineWidth = 2;

    // Draw curve with midpoint control
    ctx.moveTo(B.layout_cx - ox, B.layout_cy - oy);
    const my = strong ? B.layout_cy : (A.layout_cy + B.layout_cy) / 2;
    const mx = (A.layout_cx + B.layout_cx) / 2 + MoveTree.stone_square_size * 0.5;
    ctx.quadraticCurveTo(mx - ox, my - oy, A.layout_cx - ox, A.layout_cy - oy);
    ctx.stroke();
}
```

### 1.6 Node Drawing (Themed Stones)

Each node is drawn as a **themed stone** (using pre-rendered stone images from the board theme) with a **move number label** and optional **colored ring** for puzzle annotations.

```javascript
move_tree_drawStone(ctx, node, active_path_number, viewport) {
    const cx = node.layout_cx - viewport.offset_x;
    const cy = node.layout_cy - viewport.offset_y;
    const color = node.player;
    const on_path = node.active_path_number === active_path_number;

    // Off-path nodes are rendered at 40% opacity
    if (!on_path) {
        ctx.save();
        ctx.globalAlpha = 0.4;
    }

    // Draw stone using theme's pre-rendered images
    if (color === 1) {  // Black
        this.theme_black.placeBlackStone(ctx, null, stone, cx, cy,
            MoveTree.stone_radius);
    } else if (color === 2) {  // White
        this.theme_white.placeWhiteStone(ctx, null, stone, cx, cy,
            MoveTree.stone_radius);
    }

    // Label: move number, coordinates, or nothing
    const text_color = color === 1
        ? this.theme_black_text_color
        : this.theme_white_text_color;
    ctx.fillStyle = text_color;
    ctx.fillText(node.label, xx, yy);

    if (!on_path) ctx.restore();

    // Puzzle annotation rings
    let ring_color = null;
    if (node.text)           ring_color = "#3333ff";  // Blue: has comment
    if (node.correct_answer) ring_color = "#33ff33";  // Green: correct
    if (node.wrong_answer)   ring_color = "#ff3333";  // Red: wrong

    if (ring_color) {
        ctx.beginPath();
        ctx.strokeStyle = ring_color;
        ctx.lineWidth = 2.0;
        ctx.arc(cx, cy, MoveTree.stone_radius, 0, 2 * Math.PI, true);
        ctx.stroke();
    }
}
```

### 1.7 Active Path Highlighting

The current path (from root to the current move) is marked by a **colored rectangle background**:

```javascript
move_tree_hilightNode(ctx, node, color, viewport) {
    const sx = Math.round(node.layout_cx - MoveTree.stone_square_size * 0.5)
               - viewport.offset_x;
    const sy = Math.round(node.layout_cy - MoveTree.stone_square_size * 0.5)
               - viewport.offset_y;
    ctx.rect(sx, sy, MoveTree.stone_square_size, MoveTree.stone_square_size);
    ctx.fillStyle = color;
    ctx.fill();
}
```

Colors:

- `#6BAADA` (light blue) — Current move path
- `#6BDA6B` (light green) — Review move path (during game review)

### 1.8 Scrolling and Virtual Rendering

The canvas uses a **virtual scrolling** pattern:

- An inner container is sized to hold the entire tree
- The canvas is only as large as the visible viewport
- On scroll, the canvas repositions its CSS `top`/`left` and redraws only visible nodes
- Viewport culling skips nodes outside the visible rectangle

```javascript
// Viewport bounds check for culling
if (
  !viewport ||
  (node.layout_cx >= viewport.minx &&
    node.layout_cx <= viewport.maxx &&
    node.layout_cy >= viewport.miny &&
    node.layout_cy <= viewport.maxy)
) {
  this.move_tree_drawStone(ctx, node, active_path_number, viewport);
}
```

### 1.9 Click Interaction

Click/touch events are converted to grid coordinates by dividing pixel position by `stone_square_size`, then looked up in the `layout_hash`:

```javascript
const i = Math.floor(pos.x / MoveTree.stone_square_size);
const j = Math.floor(pos.y / MoveTree.stone_square_size);
const node = this.engine.move_tree.getNodeAtLayoutPosition(i, j);
if (node) {
  this.engine.jumpTo(node);
  this.redraw();
}
```

### 1.10 Summary

| Aspect             | Detail                                                        |
| ------------------ | ------------------------------------------------------------- |
| **Rendering**      | Canvas 2D with virtual scrolling                              |
| **Layout**         | Recursive column-allocation (trunk at y=0, branches below)    |
| **Nodes**          | Themed stones (pre-rendered images) with move number labels   |
| **Paths**          | Quadratic Bezier curves, color-coded per branch               |
| **Correct/Wrong**  | Green/Red ring around stone (`correct_answer`/`wrong_answer`) |
| **Active Path**    | Blue rectangle highlight, off-path nodes at 40% opacity       |
| **Transpositions** | Isobranch detection + purple Bezier curves                    |
| **Custom Moves**   | Full variation tree support via trunk/branches model          |
| **Scalability**    | Viewport culling + virtual scroll = handles large trees       |
| **Click**          | Grid-based lookup via `layout_hash` → `jumpTo(node)`          |
| **Standalone**     | No — tightly coupled to GobanCanvas + GoEngine                |

---

## 2. BesoGo Tree Panel

**Source**: [github.com/yewang/besogo](https://github.com/yewang/besogo) — `js/treePanel.js`  
**Rendering**: SVG  
**Used by**: BesoGo SGF editor

### 2.1 Architecture Overview

BesoGo's tree panel is a **pure SVG** renderer that draws the game tree as a navigable visualization. It consists of:

1. An SVG root element with computed `viewBox` and scaled `width`/`height`
2. Three rendering layers: bottom (current marker), paths, and nodes
3. A recursive tree builder that assigns grid positions

### 2.2 Constants and Sizing

```javascript
var SCALE = 0.25; // Tree display is 25% of SVG coordinate size
var GRIDSIZE = 120; // Each grid cell is 120 SVG units
// Visible pixel size = 120 * 0.25 = 30px per cell
```

`svgPos(x)` converts grid coordinates to SVG coordinates: `x * 120 + 60` (center of cell).

### 2.3 Layout Algorithm

The layout uses a **recursive depth-first approach** with a `nextOpen` array tracking the first available Y position in each column:

```javascript
function recursiveTreeBuild(node, x, y, nextOpen) {
  var children = node.children;
  var position, path, childPath;

  if (children.length === 0) {
    // Leaf: start SVG path at this position
    path = "m" + svgPos(x) + "," + svgPos(y);
  } else {
    // First available spot in next column, at least level with current y
    position = nextOpen[x + 1] || 0;
    position = position < y ? y : position;

    // Don't let first child drop more than 1 row below current
    if (y < position - 1) {
      y = position - 1;
    }

    // Place first child and extend path back to current node
    path =
      recursiveTreeBuild(children[0], x + 1, position, nextOpen) +
      extendPath(x, y, nextOpen);

    // Place other children (branches)
    for (var i = 1; i < children.length; i++) {
      position = nextOpen[x + 1];
      childPath =
        recursiveTreeBuild(children[i], x + 1, position, nextOpen) +
        extendPath(x, y, nextOpen, position - 1);
      // Each branch gets its own SVG path element
      pathGroup.appendChild(finishPath(childPath, "black"));
    }
  }

  // Draw the node icon (stone or setup marker)
  svg.appendChild(makeNodeIcon(node, x, y));
  addSelectionMarker(node, x, y);

  // Claim this grid position
  nextOpen[x] = y + 1;
  return path;
}
```

**Key difference from yengo-source**: BesoGo does NOT distinguish trunk vs branches during layout — all children are treated equally. The first child is the continuation, and others are branches. There's no concept of "trunk always at y=0".

### 2.4 Path Drawing (SVG Path Commands)

Paths use SVG `<path>` elements built from relative move commands. The `extendPath` function generates lines from child back to parent:

```javascript
function extendPath(x, y, nextOpen, prevChildPos) {
  var childPos = nextOpen[x + 1] - 1; // Position of the child

  if (childPos === y) {
    return "h-120"; // Horizontal line (same row)
  } else if (childPos === y + 1) {
    return "l-120,-120"; // Single diagonal drop
  } else if (prevChildPos && prevChildPos !== y) {
    // Extend back to previous child drop line
    return "l-60,-60v-" + 120 * (childPos - prevChildPos);
  } else {
    // Double-bend: diagonal + vertical + diagonal
    return "l-60,-60v-" + 120 * (childPos - y - 1) + "l-60,-60";
  }
}

function finishPath(path, color) {
  return besogo.svgEl("path", {
    d: path,
    stroke: color,
    "stroke-width": 8,
    fill: "none",
  });
}
```

**Path geometry**:

- Same-row → horizontal line (`h-120`)
- 1-row drop → 45° diagonal (`l-120,-120`)
- Multi-row drop → diagonal + vertical + diagonal (double-bend)

### 2.5 Node Icons

Nodes are rendered as SVG stone elements with labels:

```javascript
function makeNodeIcon(node, x, y) {
  var element, color;

  switch (node.getType()) {
    case "move":
      color = node.move.color;
      element = besogo.svgEl("g");
      element.appendChild(besogo.svgStone(svgPos(x), svgPos(y), color));
      // Label is the move number, drawn in contrast color
      color = color === -1 ? "white" : "black";
      element.appendChild(
        besogo.svgLabel(svgPos(x), svgPos(y), color, "" + node.moveNumber),
      );
      break;
    case "setup":
      element = besogo.svgEl("g");
      element.appendChild(besogo.svgStone(svgPos(x), svgPos(y))); // Grey
      element.appendChild(besogo.svgPlus(svgPos(x), svgPos(y), besogo.RED));
      break;
    default:
      element = besogo.svgStone(svgPos(x), svgPos(y)); // Grey
  }

  node.navTreeIcon = element;
  node.navTreeX = x;
  node.navTreeY = y;
  return element;
}
```

### 2.6 Selection and Current Marker

Each node gets a turquoise (`besogo.TURQ`) selection rectangle. The **current node** marker is always visible (opacity 1), while other markers are invisible (opacity 0) and show at 50% on hover:

```javascript
function addSelectionMarker(node, x, y) {
  var element = besogo.svgEl("rect", {
    x: svgPos(x) - 55,
    y: svgPos(y) - 55,
    width: 110,
    height: 110,
    fill: besogo.TURQ,
  });

  element.onclick = function () {
    editor.setCurrent(node);
  };

  node.navTreeMarker = element;
  setSelectionMarker(element);
}

function setCurrentMarker(marker) {
  marker.setAttribute("opacity", 1); // Always visible
  marker.onmouseover = null;
  marker.onmouseout = null;
  bottomLayer.appendChild(marker); // Background layer
  currentMarker = marker;
}

function setSelectionMarker(marker) {
  marker.setAttribute("opacity", 0); // Normally hidden
  marker.onmouseover = function () {
    marker.setAttribute("opacity", 0.5); // Show on hover
  };
  marker.onmouseout = function () {
    marker.setAttribute("opacity", 0);
  };
  svg.appendChild(marker); // Foreground layer
}
```

### 2.7 Auto-Scroll to Current Node

When the current node changes, the container scrolls to keep it visible:

```javascript
function setCurrentMarker(marker) {
  var markX = (marker.getAttribute("x") - 5) * SCALE;
  var markY = (marker.getAttribute("y") - 5) * SCALE;
  var GRIDSIZE = 120 * SCALE; // 30px

  // Horizontal scroll
  if (markX < container.scrollLeft) {
    container.scrollLeft = markX;
  } else if (markX + GRIDSIZE > container.scrollLeft + container.clientWidth) {
    container.scrollLeft = markX + GRIDSIZE - container.clientWidth;
  }

  // Vertical scroll
  if (markY < container.scrollTop) {
    container.scrollTop = markY;
  } else if (markY + GRIDSIZE > container.scrollTop + container.clientHeight) {
    container.scrollTop = markY + GRIDSIZE - container.clientHeight;
  }
}
```

### 2.8 Tree Update Strategy

The panel listens for editor events:

```javascript
function treeUpdate(msg) {
  if (msg.treeChange) {
    // Tree structure changed → full rebuild
    rebuildNavTree();
  } else if (msg.navChange) {
    // Only navigation changed → update marker
    updateCurrentMarker();
  } else if (msg.stoneChange) {
    // Stone at current node changed → update icon
    updateCurrentNodeIcon();
  }
}
```

Full rebuild creates a new SVG and replaces the old one. Navigation changes only move the marker element.

### 2.9 Summary

| Aspect            | Detail                                                      |
| ----------------- | ----------------------------------------------------------- |
| **Rendering**     | SVG elements (paths, circles, rects)                        |
| **Layout**        | Recursive depth-first with `nextOpen[]` column tracker      |
| **Nodes**         | SVG stones (circles) with move number labels                |
| **Paths**         | SVG `<path>` with straight lines and diagonals (not Bezier) |
| **Correct/Wrong** | No built-in support (no puzzle mode)                        |
| **Active Node**   | Turquoise rectangle highlight (full opacity)                |
| **Hover**         | Semi-transparent turquoise rectangle on hover               |
| **Custom Moves**  | Full editing support (add/remove nodes)                     |
| **Scalability**   | Full SVG rebuild on tree change; container overflow scroll  |
| **Click**         | Direct `onclick` on each node's SVG rectangle               |
| **Standalone**    | No — integrated with BesoGo editor                          |

---

## 3. Sabaki Game Graph

**Source**: [github.com/SabakiHQ/Sabaki](https://github.com/SabakiHQ/Sabaki) — `src/components/sidebars/GameGraph.js`  
**Rendering**: SVG (Preact components)  
**Used by**: Sabaki desktop Go editor (Electron)

### 3.1 Architecture Overview

Sabaki's GameGraph is a **Preact-based SVG renderer** with three component classes:

1. **`GameGraphNode`** — Individual node rendering (circles, squares, diamonds, bookmarks)
2. **`GameGraphEdge`** — Lines connecting parent to child
3. **`GameGraph`** — Container managing layout, viewport, and interaction

### 3.2 Layout Algorithm (Matrix Dict)

Sabaki uses a **matrix-based layout** computed by `gametree.getMatrixDict(tree)`:

```javascript
export function getMatrixDict(tree) {
  let matrix = [...Array(tree.getHeight() + 1)].map((_) => []);
  let dict = {};

  let inner = (node, matrix, dict, xshift, yshift) => {
    let sequence = [...tree.getSequence(node.id)];
    let hasCollisions = true;

    // Shift right until no collisions in the column
    while (hasCollisions) {
      hasCollisions = false;
      for (let y = 0; y <= sequence.length; y++) {
        if (xshift >= matrix[yshift + y].length - (y === sequence.length))
          continue;
        hasCollisions = true;
        xshift++;
        break;
      }
    }

    // Place entire sequence vertically at column xshift
    for (let y = 0; y < sequence.length; y++) {
      matrix[yshift + y][xshift] = sequence[y].id;
      dict[sequence[y].id] = [xshift, yshift + y];
    }

    // Recursively place children, offsetting xshift by child index
    let lastNode = sequence.slice(-1)[0];
    for (let k = 0; k < lastNode.children.length; k++) {
      let child = lastNode.children[k];
      inner(child, matrix, dict, xshift + k, yshift + sequence.length);
    }

    return [matrix, dict];
  };

  return inner(tree.root, matrix, dict, 0, 0);
}
```

**Key design difference**: Sabaki's layout is **Y-vertical** (moves go downward, variations go rightward), while yengo-source is **X-horizontal** (moves go rightward, variations go downward). This is a fundamental UX difference — Sabaki resembles a typical SGF editor tree, while yengo-source resembles a timeline.

### 3.3 Node Shapes

Sabaki renders four node shapes as SVG paths:

```javascript
render({position: [left, top], type, current, fill, nodeSize}, {hover}) {
    return h('path', {
        d: (() => {
            let nodeSize2 = nodeSize * 2;
            if (type === 'square') {         // Pass move
                return `M ${left - nodeSize} ${top - nodeSize}
                        h ${nodeSize2} v ${nodeSize2} h ${-nodeSize2} Z`;
            } else if (type === 'circle') {  // Normal move
                return `M ${left} ${top} m ${-nodeSize} 0
                        a ${nodeSize} ${nodeSize} 0 1 0 ${nodeSize2} 0
                        a ${nodeSize} ${nodeSize} 0 1 0 ${-nodeSize2} 0`;
            } else if (type === 'diamond') { // Non-move node (setup)
                let ds = Math.round(Math.sqrt(2) * nodeSize);
                return `M ${left} ${top - ds}
                        L ${left - ds} ${top} L ${left} ${top + ds}
                        L ${left + ds} ${top} Z`;
            } else if (type === 'bookmark') { // Hotspot
                return `M ${left - nodeSize} ${top - nodeSize * 1.3}
                        h ${nodeSize2} v ${nodeSize2 * 1.3}
                        l ${-nodeSize} ${-nodeSize}
                        l ${-nodeSize} ${nodeSize} Z`;
            }
        })(),
        class: classNames({hover, current}, 'node'),
        fill,
    });
}
```

| Node Type  | Shape         | When Used               |
| ---------- | ------------- | ----------------------- |
| `circle`   | Circle        | Normal stone placement  |
| `square`   | Square        | Pass move               |
| `diamond`  | Diamond       | Setup node (no move)    |
| `bookmark` | Bookmark/flag | Hotspot (`HO` property) |

### 3.4 Node Colors (Semantic)

```javascript
let fillRGB =
  node.data.BM != null
    ? [240, 35, 17] // Bad move: RED
    : node.data.DO != null
      ? [146, 39, 143] // Doubtful: PURPLE
      : node.data.IT != null
        ? [72, 134, 213] // Interesting: BLUE
        : node.data.TE != null
          ? [89, 168, 15] // Good (tesuji): GREEN
          : commentProperties.some((x) => node.data[x] != null)
            ? [255, 174, 61] // Has comment: ORANGE
            : [238, 238, 238]; // Default: LIGHT GRAY

let opacity = onCurrentTrack ? 1 : 0.5; // Off-path nodes fade
let fill = `rgb(${fillRGB.map((x) => x * opacity).join(",")})`;
```

| SGF Property  | Color                | Meaning            |
| ------------- | -------------------- | ------------------ |
| `BM`          | Red (#F02311)        | Bad move           |
| `DO`          | Purple (#922B8F)     | Doubtful move      |
| `IT`          | Blue (#4886D5)       | Interesting move   |
| `TE`          | Green (#59A80F)      | Tesuji (good move) |
| `C`/`GC`/etc. | Orange (#FFAE3D)     | Has comment        |
| none          | Light gray (#EEEEEE) | Default            |

### 3.5 Edge Drawing (Polylines)

Edges are SVG `<polyline>` elements:

```javascript
render({positionAbove: [left1, top1], positionBelow: [left2, top2],
        length, gridSize, current}) {
    let points;

    if (left1 === left2) {
        // Same column: straight vertical line
        points = `${left1},${top1} ${left1},${top2 + length}`;
    } else {
        // Different column: bend via intermediate point
        points = `${left1},${top1} ${left2 - gridSize},${top2 - gridSize}
                  ${left2},${top2} ${left2},${top2 + length}`;
    }

    return h('polyline', {
        points,
        fill: 'none',
        stroke: current ? '#ccc' : '#777',  // Current path lighter
        'stroke-width': current ? 2 : 1,
    });
}
```

**Edge style**: Straight lines with a single bend point at branch junctions. Current path uses lighter color (#ccc, 2px) vs non-current (#777, 1px).

### 3.6 Drag-to-Pan Navigation

Sabaki uses CSS transform-based panning rather than native scrolling:

```javascript
// Camera position tracked in state
this.state = {
  cameraPosition: [-props.gridSize, -props.gridSize],
  viewportSize: [0, 0],
  viewportPosition: [0, 0],
};

// Mouse drag updates camera position
if (this.drag) {
  this.setState({
    cameraPosition: [cx - movementX, cy - movementY],
  });
}

// Applied via CSS transform on all SVG children
`#graph svg > * {
    transform: translate(${-cx}px, ${-cy}px);
}`;
```

### 3.7 Auto-Center on Current Node

When the tree position changes, the camera pans to center on the current node with a configurable delay:

```javascript
updateCameraPosition() {
    let [x, y] = dict[treePosition];
    let [width, padding] = gametree.getMatrixWidth(y, matrix);

    let relX = width === 1 ? 0 : 1 - (2 * (x - padding)) / (width - 1);
    let diff = ((width - 1) * gridSize) / 2;
    diff = Math.min(diff, this.state.viewportSize[0] / 2 - gridSize);

    this.setState({
        cameraPosition: [
            x * gridSize + relX * diff - this.state.viewportSize[0] / 2,
            y * gridSize - this.state.viewportSize[1] / 2,
        ].map(z => Math.round(z)),
    });
}
```

### 3.8 Viewport-Based Rendering

Sabaki only renders nodes within the visible viewport area (±2 grid cells buffer):

```javascript
let [minX, minY] = [cx, cy].map((z) =>
  Math.max(Math.ceil(z / gridSize) - 2, 0),
);
let [maxX, maxY] = [cx, cy].map(
  (z, i) => (z + [width, height][i]) / gridSize + 2,
);
minY -= 3;
maxY += 3;

for (let x = minX; x <= maxX; x++) {
  for (let y = minY; y <= maxY; y++) {
    if (matrix[y] == null || matrix[y][x] == null) continue;
    // Render node...
  }
}
```

### 3.9 Summary

| Aspect            | Detail                                                    |
| ----------------- | --------------------------------------------------------- |
| **Rendering**     | SVG via Preact components                                 |
| **Layout**        | Matrix-dict with collision avoidance (vertical main line) |
| **Nodes**         | SVG paths: circles, squares, diamonds, bookmarks          |
| **Paths**         | SVG polylines (straight + bend), styled by current-ness   |
| **Correct/Wrong** | SGF annotations (BM/DO/IT/TE) → semantic colors           |
| **Active Path**   | Brighter fill + thicker edge stroke                       |
| **Custom Moves**  | Full variation support                                    |
| **Scalability**   | Viewport culling, CSS transform panning                   |
| **Click**         | Grid-coordinate calculation from mouse position           |
| **Standalone**    | Partially — depends on `@sabaki/immutable-gametree`       |

---

## 4. yengo-source Solution Tree

**Source**: [yengo-source](_(redacted)_)  
**Rendering**: Lazy-loaded webpack chunk (not directly inspectable)  
**Used by**: yengo-source puzzle platform

### 4.1 What We Know

From prior analysis of the yengo-source.com JavaScript bundles:

1. **The tree component is lazy-loaded** — The component (`p.bY`) is code-split and loaded on demand when the user opens the tree view
2. **It receives pre-processed data**:
   - `baseSgf` — The base SGF string
   - `rightCompressedPaths` — Correct solution paths (compressed)
   - `wrongCompressedPaths` — Incorrect answer paths
   - `questionCompressedPaths` — Intermediate/question paths
   - `commentCompressedPaths` — Paths with pedagogical comments
   - `autoScrollToCurrentNode` — Auto-scroll behavior flag
   - `options: { minHeight }` — Layout options

3. **Compressed path encoding** — Solution paths are compressed into string tokens via `v.FU()`. This is more efficient than full SGF trees for transmission.

4. **Correctness annotations** — Stored in SGF `C[]` property using keywords: `RIGHT`, `FORCE`, `NOTTHIS`, `CHOICE`

5. **Canvas 2D rendering stack** — The parent board engine uses 6 layered canvases. The tree component likely uses Canvas 2D as well (consistent with the codebase).

### 4.2 User-Reported Features

Based on user description of the yengo-source.com tree:

| Feature            | Detail                                             |
| ------------------ | -------------------------------------------------- |
| **Visual quality** | "Very nice and beautiful"                          |
| **Custom moves**   | Allows adding custom exploratory moves to the tree |
| **Path coding**    | Correct paths visually distinct from wrong paths   |
| **Interactivity**  | Click on tree node → board jumps to that position  |

### 4.3 What We Can Infer

Given the site's architecture (React + webpack + Canvas 2D board):

- **Likely Canvas 2D** for the tree as well (consistency with board engine)
- **Color-coded paths** based on the compressed path sets (right=green, wrong=red, question=yellow)
- **Node styling** probably uses the same stone textures as the board for visual consistency
- **Scroll/pan** for large trees with auto-scroll to current position
- **Click-to-navigate** with coordinate-based hit testing (standard pattern)

### 4.4 Summary

| Aspect            | Detail                                             |
| ----------------- | -------------------------------------------------- |
| **Rendering**     | Likely Canvas 2D (matches board engine)            |
| **Layout**        | Unknown (code is minified & lazy-loaded)           |
| **Nodes**         | Likely themed stones (same as board)               |
| **Paths**         | Color-coded: right/wrong/question/comment          |
| **Correct/Wrong** | SGF `C[RIGHT]`/`C[NOTTHIS]` + compressed path sets |
| **Custom Moves**  | Yes — exploratory moves can be added               |
| **Scalability**   | Auto-scroll to current node                        |
| **Standalone**    | No — proprietary, not extractable                  |

---

## 5. Comparison Matrix

### 5.1 Technical Comparison

| Feature              | Goban (OGS)                                    | BesoGo                                  | Sabaki                                       | yengo-source                 |
| -------------------- | ---------------------------------------------- | --------------------------------------- | -------------------------------------------- | -------------------------- |
| **Rendering Tech**   | Canvas 2D                                      | SVG                                     | SVG (Preact)                                 | Canvas 2D (likely)         |
| **Layout Direction** | Horizontal (L→R moves, T→B variations)         | Horizontal (L→R)                        | Vertical (T→B moves, L→R variations)         | Unknown                    |
| **Layout Algorithm** | Recursive column-allocation with layout vector | Recursive DFS with nextOpen[]           | Matrix-dict with collision avoidance         | Unknown                    |
| **Node Size**        | 28px cells (11px radius + 3px padding)         | 30px cells (120 SVG units × 0.25 scale) | Configurable `gridSize` prop                 | Unknown                    |
| **Node Shape**       | Themed stones (pre-rendered images)            | SVG circles (black/white/grey)          | SVG path shapes (circle/square/diamond/flag) | Unknown                    |
| **Move Labels**      | Move number or coordinates (configurable)      | Move number always                      | None (color only)                            | Unknown                    |
| **Branch Lines**     | Quadratic Bezier curves                        | SVG paths (straight + diagonal)         | SVG polylines (straight + bend)              | Unknown                    |
| **Line Colors**      | 7 colors per branch-depth                      | Black only                              | Gray (#777) or light gray (#ccc)             | Color-coded by correctness |
| **Trunk Line**       | Always black, y=0                              | Same as branches                        | Same as branches (thicker when current)      | Unknown                    |

### 5.2 Puzzle Support Comparison

| Feature            | Goban (OGS)                                   | BesoGo                        | Sabaki                                | yengo-source               |
| ------------------ | --------------------------------------------- | ----------------------------- | ------------------------------------- | ------------------------ |
| **Correct Answer** | `correct_answer` → green ring (#33ff33)       | None                          | `TE` prop → green (#59A80F) fill      | `C[RIGHT]` → green path  |
| **Wrong Answer**   | `wrong_answer` → red ring (#ff3333)           | None                          | `BM` prop → red (#F02311) fill        | `C[NOTTHIS]` → red path  |
| **Comment**        | `text` → blue ring (#3333ff)                  | None                          | Comment props → orange (#FFAE3D) fill | `commentCompressedPaths` |
| **Active Path**    | Blue rect (#6BAADA) + 40% opacity on off-path | Turquoise rect (full opacity) | Brighter fill + thicker stroke        | Auto-scroll to current   |
| **Custom Moves**   | Yes (trunk/branch model)                      | Yes (full editor)             | Yes (variation support)               | Yes (exploratory)        |

### 5.3 Performance and Scalability

| Feature              | Goban (OGS)                                   | BesoGo                                      | Sabaki                          |
| -------------------- | --------------------------------------------- | ------------------------------------------- | ------------------------------- |
| **Virtual Scroll**   | Yes — canvas repositions to viewport          | No — full SVG rebuild                       | Yes — viewport culling          |
| **Viewport Culling** | Yes — skip off-screen nodes                   | No — all nodes always in DOM                | Yes — only render visible nodes |
| **Update Strategy**  | Full redraw on any change                     | 3-tier: rebuild / move marker / update icon | Component-level updates         |
| **Tree Rebuild**     | Layout recomputation + full canvas redraw     | Create new SVG, replace old                 | Matrix-dict recomputation       |
| **Large Trees**      | Handles well (O(n) layout + culled rendering) | Degrades (all SVG elements in DOM)          | Handles well (culled rendering) |
| **Memory**           | Single canvas (low)                           | Full SVG DOM (moderate)                     | Virtual DOM diff (moderate)     |

### 5.4 Integration Considerations

| Feature          | Goban (OGS)                        | BesoGo                          | Sabaki                          |
| ---------------- | ---------------------------------- | ------------------------------- | ------------------------------- |
| **Framework**    | Vanilla DOM                        | Vanilla DOM                     | Preact (compatible with Yen-Go) |
| **Dependencies** | GoEngine, themes, callbacks        | besogo.js (editor core)         | @sabaki/immutable-gametree      |
| **Extractable**  | Difficult (coupled to GobanCanvas) | Moderate (self-contained panel) | Moderate (separate component)   |
| **TypeScript**   | Yes                                | No                              | No (but clean JS)               |
| **License**      | Apache 2.0                         | MIT                             | MIT                             |

---

## 6. Recommendations for Yen-Go

### 6.1 Best Approach for Yen-Go's Solution Tree

Given Yen-Go's constraints (Preact, TypeScript, static-first, already using goban):

**Option A: Use yengo-source move tree directly** (Lowest effort)

- Yen-Go already has goban integrated
- The move tree renderer is accessible via `Goban.move_tree_container` and `Goban.move_tree_redraw()`
- Supports correct/wrong rings, active path highlighting, click navigation
- Drawbacks: Canvas 2D (not Preact-idiomatic), horizontal layout only, coupled to GobanCanvas

**Option B: Custom Preact tree component** (Best fit)

- Build a Preact SVG component inspired by Sabaki's approach
- Uses Yen-Go's existing SGF tree data from `parseSgfToTree`
- Full control over puzzle-specific styling (correct/wrong/hint paths)
- Can be designed as a standalone component, independent of goban
- Vertical OR horizontal layout based on screen orientation

**Option C: Port BesoGo's treePanel** (Middle ground)

- Clean, simple SVG rendering logic (~200 lines)
- Easy to understand and modify
- Would need: TypeScript conversion, Preact wrapper, puzzle annotations
- Drawbacks: No viewport culling, full rebuild pattern

### 6.2 Recommended Architecture for Custom Tree

If building a custom tree (Option B), the recommended architecture combines the best patterns:

| Aspect            | Source Inspiration                        | Rationale                                           |
| ----------------- | ----------------------------------------- | --------------------------------------------------- |
| **Rendering**     | SVG (Sabaki-style)                        | Preact-idiomatic, scalable, accessible              |
| **Layout**        | yengo-source column-allocation                     | Better for puzzles (trunk at top, variations below) |
| **Node shapes**   | Sabaki semantic shapes                    | Circles for moves, diamonds for setup               |
| **Correct/Wrong** | yengo-source ring pattern                          | Green/red rings are standard in Go puzzle UIs       |
| **Active path**   | yengo-source opacity (0.4 off-path) + Sabaki color | Clear visual hierarchy                              |
| **Line style**    | yengo-source Bezier curves                         | More visually appealing than straight lines         |
| **Colors**        | yengo-source branch colors (7 distinct)            | Better for complex puzzles with many variations     |
| **Viewport**      | Sabaki virtual rendering                  | Performance for large trees                         |
| **Click**         | Sabaki grid-coordinate calculation        | Standard pattern                                    |

### 6.3 Key Design Decisions

| Decision                     | Recommendation                                  | Reasoning                                                                 |
| ---------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------- |
| **Layout direction**         | Horizontal (L→R)                                | Matches yengo-source convention, better for wide screens typical in puzzle solving |
| **Node representation**      | SVG circles filled with stone color             | Visual consistency with the board                                         |
| **Move labels**              | Move number inside stone                        | Essential for puzzle navigation                                           |
| **Correct/wrong indicators** | Colored ring (green/red) around stone           | Clear, non-obstructive, established pattern                               |
| **Branch line style**        | Quadratic Bezier curves with branch colors      | Visually distinguishable branches                                         |
| **Active path**              | Blue background highlight + off-path fade       | Matches yengo-source, clear navigation                                             |
| **Scroll**                   | CSS overflow: auto on container                 | Simple, native scrollbar                                                  |
| **Click behavior**           | Click node → jump to that position on board     | Standard pattern across all implementations                               |
| **Solution gating**          | Tree hidden until wrong move or explicit review | Yen-Go Holy Law: no spoilers                                              |

---

_This document is research reference for solution tree visualization. It does not modify any code in the repository._
