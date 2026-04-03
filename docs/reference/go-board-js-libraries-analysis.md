# Go Board JavaScript Libraries — Comprehensive Analysis

> **Last Updated**: 2026-01-28  
> **Purpose**: Research analysis of how goproblems.com renders Go boards and solution trees, plus a comparison of major Go board JS libraries.

> **See also**:
>
> - [Architecture: Frontend](../architecture/frontend/) — Yen-Go frontend design decisions
> - [Concepts: SGF Properties](../concepts/sgf-properties.md) — Custom SGF property definitions
> - [How-To: Frontend](../how-to/frontend/) — Frontend development guides

---

## Table of Contents

1. [goproblems.com Deep Dive](#1-goproblemcom-deep-dive)
2. [Library Comparison Matrix](#2-library-comparison-matrix)
3. [Individual Library Profiles](#3-individual-library-profiles)
4. [Relevance to Yen-Go](#4-relevance-to-yen-go)

---

## 1. goproblems.com Deep Dive

### 1.1 Technology Stack

| Layer                | Technology                                    |
| -------------------- | --------------------------------------------- |
| **Framework**        | React (SPA, `<div id="root">`)                |
| **Bundler**          | Webpack (chunked builds, code-splitting)      |
| **Board Rendering**  | **Custom Canvas 2D** (no external Go library) |
| **UI Framework**     | Bootstrap (Offcanvas panels)                  |
| **Animations**       | Framer Motion (`oc.P.div`), Lottie            |
| **Charts**           | Chart.js (statistics pages)                   |
| **AI Analysis**      | KataGo (model: `kata1-b6c96`, GTP protocol)   |
| **State Management** | Redux-like (actions/dispatch pattern)         |
| **i18n**             | Full translation JSON embedded in HTML        |
| **Analytics**        | Google Analytics (G-QV80T4WCY8)               |

### 1.2 JavaScript Bundle Structure

The site loads 8 JavaScript bundles from `/build/`:

| Bundle                | Size    | Purpose                       |
| --------------------- | ------- | ----------------------------- |
| `runtime.f743a3dd.js` | ~2 KB   | Webpack runtime, chunk loader |
| `83.c2af3394.js`      | ~35 KB  | Shared dependencies           |
| `920.ed9fa994.js`     | ~199 KB | **Go board Canvas 2D engine** |
| `915.3e67b715.js`     | ~214 KB | Chart.js (statistics)         |
| `535.3654d95f.js`     | ~1.3 MB | General application code      |
| `914.70966ff3.js`     | ~482 KB | Lottie animation library      |
| `148.518c57f7.js`     | ~706 KB | Configuration, themes, KataGo |
| `react.82c35494.js`   | ~804 KB | Main React application        |

**Key finding**: All known Go board libraries (WGo.js, Glift, EidoGo, BesoGo, Sabaki/Shudan, jGoBoard) were searched for across every bundle — **none were found**. goproblems.com uses a completely **custom, proprietary implementation**.

### 1.3 Board Rendering Architecture

The board engine lives in chunk `920.ed9fa994.js` and uses **HTML5 Canvas 2D** with a **multi-layer canvas architecture**:

| Canvas Layer      | Purpose                                           |
| ----------------- | ------------------------------------------------- |
| `board`           | Board background, grid lines, star points, stones |
| `cursorCanvas`    | Mouse hover / touch cursor indicator              |
| `markupCanvas`    | Letters, numbers, triangles, circles, squares     |
| `effectCanvas`    | Move animations (ban effect, placement)           |
| `analysisCanvas`  | KataGo AI analysis overlays                       |
| `ownershipCanvas` | Territory ownership display                       |

**Key rendering details:**

- **28 `getContext("2d")` calls** in the board chunk alone
- Star points drawn at coordinates `[3, 9, 15]`
- `DOMMatrix` transforms for zoom/pan
- `calcSpaceAndPadding()` for responsive sizing
- `stoneRatio` parameter for stone-to-cell proportion
- Stone rendering uses PNG textures (not pure Canvas drawing)

### 1.4 Board Configuration

```javascript
// Minified config object structure
{
  boardLineWidth: 1.2,
  boardEdgeLineWidth: 2,
  dynamicPadding: true,
  interactive: true,
  zoom: false,
  extent: /* visible area */,
  themeResources: /* PNG texture map */
}
```

### 1.5 Theme System

11 board themes are available, each using PNG textures:

| Theme             | Description                    |
| ----------------- | ------------------------------ |
| `BlackAndWhite`   | High contrast, no textures     |
| `Subdued`         | Muted colors                   |
| `ShellStone`      | Shell-textured stones          |
| `SlateAndShell`   | Traditional Japanese materials |
| `Walnut`          | Walnut wood board              |
| `Photorealistic`  | Photo-quality textures         |
| `Flat`            | Modern flat design             |
| `Warm`            | Warm color palette             |
| `Dark`            | Dark mode                      |
| `HighContrast`    | Accessibility-focused          |
| `YunziMonkeyDark` | Yunzi stones on dark board     |

Theme images are served as PNGs from `/build/images/theme/` with variants for board, black stone, and white stone.

### 1.6 Core Go Module (`Ct`)

The main Go logic module exposes these minified identifiers:

| Identifier                              | Purpose                         |
| --------------------------------------- | ------------------------------- |
| `Ct.Ki.Black` / `Ct.Ki.White`           | Stone colors                    |
| `Ct.bs.BlackStone` / `Ct.bs.WhiteStone` | Cursor types                    |
| `Ct.T2`                                 | SGF class (`.toSgf()`, `.root`) |
| `Ct.r8(node, prop)`                     | Read SGF property from node     |
| `Ct.kX(prop, value)`                    | Construct node annotation       |
| `Ct.KC.Problem` / `Ct.KC.Default`       | Analysis point themes           |
| `Ct.Zn`                                 | Coordinate converter            |

### 1.7 Solution Tree & Path Encoding

**Solution correctness** is stored as SGF node annotations:

```javascript
// RIGHT/WRONG detection from SGF Comment (C) property
/(RIGHT|FORCE|NOTTHIS|CHOICE)/g;

// Annotating a correct path:
new Ct.kX("C", "RIGHT");

// Building SGF from tree:
new Ct.T2(rootNode).toSgf();
```

**Path compression**: The site uses a "compressed path" representation for tree navigation. The function `v.FU()` compresses move sequences into string tokens.

**Problem component** (`dc`) receives these compressed path sets:

| Prop                      | Purpose                         |
| ------------------------- | ------------------------------- |
| `rightCompressedPaths`    | Correct solution paths          |
| `wrongCompressedPaths`    | Incorrect paths (refutations)   |
| `questionCompressedPaths` | Intermediate/question paths     |
| `commentCompressedPaths`  | Paths with pedagogical comments |

**Tree visualization component** (`p.bY`) is **lazy-loaded** via webpack code splitting — the actual rendering code is not in the initial page bundles. It receives `baseSgf` and all compressed path sets, plus `autoScrollToCurrentNode` and `options: { minHeight }`.

### 1.8 Board Component API

```javascript
// Board component p.bW props (minified)
{
  (boardRef, // React ref to board element
    mat, // 2D array of stone positions
    visibleAreaMat, // Visible area mask (for zoom)
    markup, // Letters, numbers, shapes
    cursor, // Current cursor style
    turn, // Whose turn (Black/White)
    boardOptions, // Config object (see 1.4)
    onClick); // Move handler
}
```

### 1.9 Key Takeaways for goproblems.com

1. **Fully custom implementation** — No external Go board library dependency
2. **Canvas 2D, not SVG** — Performance-oriented choice with layered canvases
3. **PNG textures for stones** — Not procedurally drawn
4. **KataGo integration** — Server-side AI analysis displayed as Canvas overlay
5. **Compressed path encoding** — Compact representation of solution trees
6. **Lazy-loaded tree visualization** — Tree component loaded on-demand
7. **SGF C property** — Uses `RIGHT/FORCE/NOTTHIS/CHOICE` annotations in SGF `C[]` (Comment) property to mark solution correctness

---

## 2. Library Comparison Matrix

| Feature            | goproblems.com         | WGo.js          | Glift        | BesoGo            | Shudan               | EidoGo       | jGoBoard          | goban (OGS)        |
| ------------------ | ---------------------- | --------------- | ------------ | ----------------- | -------------------- | ------------ | ----------------- | ------------------ |
| **Rendering**      | Canvas 2D (layered)    | Canvas 2D       | SVG          | SVG + CSS         | CSS (React)          | DOM/CSS      | Canvas 2D         | Canvas 2D + SVG    |
| **SGF Parse**      | Custom                 | Yes             | Yes          | Yes (editor)      | No (use @sabaki/sgf) | Yes          | Yes               | Yes                |
| **SGF Edit**       | Yes                    | No              | No           | Yes (full editor) | No                   | Yes          | Yes               | Yes                |
| **Puzzle/Problem** | Yes (core feature)     | Yes (extension) | Yes          | No                | No                   | Yes          | No                | Yes (core feature) |
| **Solution Tree**  | Yes (visual tree)      | No              | No           | Yes (tree panel)  | No                   | No           | No                | Yes                |
| **Game Review**    | Yes (KataGo AI)        | No              | No           | No                | No                   | No           | No                | Yes                |
| **Themes**         | 11 PNG-based           | Canvas textures | Configurable | CSS themes        | CSS                  | CSS          | PNG textures      | Canvas textures    |
| **Board Sizes**    | Any                    | Any             | Any          | Any               | Any                  | 9, 13, 19    | Any               | Any                |
| **Coordinates**    | Yes                    | Yes             | Yes          | Yes               | Yes                  | Yes          | Yes               | Yes                |
| **Markup**         | Full (letters, shapes) | Yes             | Yes          | Full              | Partial              | Yes          | Yes               | Full               |
| **TypeScript**     | N/A (compiled)         | No              | No           | No                | Yes (Preact)         | No           | Yes (v5)          | Yes                |
| **Framework**      | React                  | Vanilla         | Vanilla      | Vanilla           | Preact/React         | Vanilla      | Vanilla           | Vanilla (DOM)      |
| **License**        | Proprietary            | MIT (implied)   | Apache 2.0   | MIT               | MIT                  | AGPL         | CC-BY-NC-4.0      | Apache 2.0         |
| **Stars**          | N/A                    | 334             | 120          | 131               | 103                  | 190          | —                 | —                  |
| **Last Activity**  | Active (2025+)         | 5 years ago     | 7 years ago  | ~8 months ago     | 3 years ago          | 13 years ago | Active (days ago) | 5 months ago       |
| **npm**            | N/A                    | No              | No           | No                | `@pichichi/shudan`   | No           | `jgoboard`        | `goban`            |

---

## 3. Individual Library Profiles

### 3.1 WGo.js

**Repository**: [github.com/waltheri/wgo.js](https://github.com/waltheri/wgo.js)  
**Website**: [wgo.waltheri.net](http://wgo.waltheri.net/)  
**License**: MIT (implied, no explicit LICENSE file)  
**Stars**: 334 | **Forks**: 123 | **Contributors**: 21  
**Last Commit**: ~5 years ago

**Architecture**: Two main modules — `Board` (Canvas 2D rendering) and `Game` (game logic/rules). Comes with a full SGF game viewer ("WGo.js Player") that can be embedded in websites.

**Rendering**: HTML5 Canvas 2D. Supports custom board objects, cut-outs, and stone textures.

**SGF Support**: Built-in SGF player with full game navigation (forward, backward, variations).

**Puzzle Support**: Has a `extensions/tsumego` directory with dedicated puzzle mode configuration.

**Strengths**:

- Most-starred Go board library (334 stars)
- Canvas-based rendering (fast)
- Complete SGF player included
- Tsumego extension built-in
- Extensive customization API

**Weaknesses**:

- No TypeScript types
- No npm package
- Last meaningful update ~5 years ago
- No active maintainer response

### 3.2 Glift

**Repository**: [github.com/Kashomon/glern](https://github.com/niclas-carlsson/glern) / originally Kashomon/glern  
**Website**: [gliftgo.com](https://www.gliftgo.com/)  
**License**: Apache 2.0  
**Stars**: ~120 | **Last Release**: v1.1.2 (October 2016) | **Last Commit**: ~7 years ago

**Architecture**: SVG-based board rendering with a modular widget system. Supports embedding multiple boards on a page.

**Rendering**: SVG elements for board, stones, and markup. Clean scalable graphics.

**SGF Support**: Full SGF parsing with variation navigation.

**Puzzle Support**: **Yes** — dedicated problem-solving mode with RIGHT/WRONG path detection. Uses SGF `GB` and `GW` properties plus `C[]` comment annotations (similar to goproblems.com).

**Strengths**:

- SVG rendering scales cleanly
- Built-in problem-solving support
- Widget-based architecture for embedding
- Apache 2.0 license

**Weaknesses**:

- Abandoned (7 years, no activity)
- No TypeScript
- No npm package
- Documentation gaps

### 3.3 BesoGo

**Repository**: [github.com/yewang/besogo](https://github.com/yewang/besogo)  
**License**: MIT  
**Stars**: 131 | **Last Commit**: ~8 months ago

**Architecture**: SVG-based rendering with CSS theme support. Full SGF editor with navigation, annotation, and editing tools.

**Rendering**: SVG for the board with CSS-based theming. Clean, lightweight approach.

**SGF Support**: **Comprehensive** — full SGF editor with:

- Load/save/export SGF
- Node-by-node editing
- Comment editing
- Markup tools (labels, shapes)
- Multi-game support

**Puzzle Support**: No dedicated puzzle mode, but the tree navigation panel shows the full game/variation tree visually.

**Tree Panel**: **Yes** — BesoGo has a visual tree navigator showing the variation tree structure. This is the most relevant feature for understanding solution tree visualization.

**Strengths**:

- Full SGF editor (richest feature set for editing)
- Visual tree panel navigation
- Most recently active among "classic" libraries
- MIT license
- Lightweight, no dependencies

**Weaknesses**:

- No TypeScript
- No npm package
- No puzzle-solving mode
- Single maintainer

### 3.4 Shudan (@pichichi/shudan)

**Repository**: [github.com/SabakiHQ/Shudan](https://github.com/SabakiHQ/Shudan)  
**License**: MIT  
**Stars**: 103 | **Last Release**: v1.7.1 (August 2022)

**Architecture**: **Preact/React component** — pure CSS board rendering (no Canvas, no SVG). Part of the Sabaki ecosystem.

**Rendering**: CSS Grid/Flexbox with CSS transforms for stones. Stones are CSS-drawn circles with gradients, not images. Board lines are CSS borders.

**SGF Support**: **None built-in** — Shudan is purely a board rendering component. Use `@sabaki/sgf` (MIT, 55 stars) for SGF parsing and `@sabaki/immutable-gametree` for game tree management.

**Puzzle Support**: None — board display only.

**Strengths**:

- Modern Preact/React component architecture
- TypeScript-ready
- Simplest API (just pass board state as props)
- MIT license
- Part of well-designed Sabaki ecosystem

**Weaknesses**:

- Board display ONLY — no game logic, no SGF, no navigation
- Requires additional @sabaki/\* packages for any real functionality
- CSS-only rendering has limitations vs Canvas/SVG
- Sabaki ecosystem is dormant (last SGF parser release: 2019)

**Sabaki SGF Ecosystem**:
| Package | Purpose | Stars | Last Release |
|---------|---------|-------|-------------|
| `@sabaki/sgf` | SGF parser/serializer | 55 | v3.4.0 (Jun 2019) |
| `@sabaki/immutable-gametree` | Tree data structure | — | — |
| `@sabaki/go-board` | Game rules/logic | — | — |
| `@pichichi/shudan` | Board component | 103 | v1.7.1 (Aug 2022) |

### 3.5 EidoGo

**Repository**: [github.com/jcppkkk/eidogo](https://github.com/jcppkkk/eidogo) (community fork of original)  
**Website**: [eidogo.com](https://eidogo.com/)  
**License**: AGPL (mentioned in site footer)  
**Stars**: 190 | **Last Commit**: ~13 years ago

**Architecture**: DOM/CSS-based board rendering. One of the earliest web-based Go board implementations.

**Rendering**: HTML table + positioned `<div>` elements with CSS backgrounds. No Canvas, no SVG.

**SGF Support**: Full SGF parsing with multi-game support, variation navigation.

**Puzzle Support**: **Yes** — dedicated problem mode. Was one of the pioneering web-based Go puzzle platforms.

**Strengths**:

- Pioneering implementation (historical significance)
- Problem-solving mode
- Full SGF editor
- Large community recognition

**Weaknesses**:

- **Completely abandoned** (13 years without updates)
- AGPL license (viral copyleft, incompatible with many projects)
- DOM-based rendering (slowest approach)
- No TypeScript, no npm, no modern tooling
- IE6-era code quality

### 3.6 jGoBoard

**Repository**: [github.com/jokkebk/jgoboard](https://github.com/jokkebk/jgoboard)  
**Website**: [jgoboard.com](http://jgoboard.com/)  
**npm**: `jgoboard` (v5.0.4, published days ago)  
**License**: **CC-BY-NC-4.0** (Creative Commons NonCommercial)  
**Weekly Downloads**: 477

**Architecture**: Modular toolkit with separate entry points for board, game logic, SGF, renderer, and player. **v5 is a complete rewrite** with modern ESM/CJS/UMD exports, TypeScript declarations, and Vite-based dev tooling.

**Rendering**: Canvas 2D with PNG textures for themed boards (`kaya-*`, `walnut-*`, `bw-*`).

**Module Structure**:

```javascript
import { createBoard, createGameTree, createCursor } from "jgoboard";
import { createRenderer } from "jgoboard/renderer";
import { parseSgf, gameTreeFromSgf, sgfFromGameTree } from "jgoboard/sgf";
import { createPlayer } from "jgoboard/player";
```

**SGF Support**: Full parse/serialize with bidirectional conversion between SGF and internal game tree format.

**Puzzle Support**: No dedicated puzzle mode.

**Tree Support**: Has `createGameTree`, `createCursor` for tree navigation; has a `demoV5Tree.html` demo.

**Strengths**:

- **Most actively maintained** (published days ago)
- Modern TypeScript + Vite tooling
- Modular architecture (import only what you need)
- Framework integration docs (React, Vue, Svelte)
- CDN-ready (ESM and UMD builds)
- Comprehensive docs

**Weaknesses**:

- **CC-BY-NC-4.0 license** — NonCommercial restriction makes it **unusable for many projects**
- Relatively young v5 rewrite
- Small user base (477 weekly npm downloads)

### 3.7 goban (OGS)

**Repository**: [github.com/online-go/goban](https://github.com/online-go/goban)  
**npm**: `goban` (v8.3.147)  
**License**: Apache 2.0  
**Weekly Downloads**: 570

**Architecture**: The board rendering engine extracted from [online-go.com](https://online-go.com/). Creates its own DOM element internally. TypeScript throughout.

**Rendering**: Canvas 2D with SVG fallback. Full theme system with stone textures.

**SGF Support**: Full — part of the complete OGS game engine.

**Puzzle Support**: **Yes** — Core feature. OGS has a full puzzle system with `PuzzleObject` format, `initial_state` + `move_tree` architecture.

**Tree Support**: Full game tree with variation navigation, move tree visualization.

**Strengths**:

- **Production-proven** at scale (online-go.com)
- Apache 2.0 license
- TypeScript
- Active development (252 npm versions)
- Complete game engine (rules, scoring, timing)
- Puzzle mode built-in

**Weaknesses**:

- Heavy (11.2 MB unpacked)
- Tightly coupled to OGS architecture
- Creates its own DOM element (not a React/Preact component)
- API documentation is sparse
- Required `GobanContainer` pattern for mounting

---

## 4. Relevance to Yen-Go

### 4.1 Current Architecture

Yen-Go already uses the **goban** (OGS) library with the `GobanContainer` mounting pattern. The frontend uses `sgfToPuzzle()` to convert SGF to OGS-native `PuzzleObject` format, with `parseSgfToTree` for metadata extraction.

### 4.2 What goproblems.com Does Differently

| Aspect                  | goproblems.com                      | Yen-Go                                           |
| ----------------------- | ----------------------------------- | ------------------------------------------------ |
| **Board Library**       | Custom Canvas 2D                    | goban (OGS)                                      |
| **Solution Encoding**   | Compressed paths (string tokens)    | SGF move tree (OGS native)                       |
| **Correctness Markers** | `C[RIGHT]` / `C[WRONG]` in SGF      | Pre-computed solution trees                      |
| **Tree Visualization**  | Visual tree component (lazy-loaded) | Solution tree gating (hidden until wrong/review) |
| **Themes**              | 11 PNG-based themes                 | OGS theme system                                 |

### 4.3 Lessons from goproblems.com

1. **Multi-layer Canvas** — Separating board, cursor, markup, and effects into distinct canvas layers improves rendering performance and enables independent updates
2. **Compressed path encoding** — Efficient representation of solution paths as string tokens rather than full tree objects could reduce payload size
3. **Lazy-loaded tree** — The solution tree visualization is code-split and only loaded when the user navigates to the tree view
4. **RIGHT/WRONG annotations** — Using SGF Comment property for solution correctness is a well-established pattern (also used by Glift)

### 4.4 Library Recommendations for Yen-Go

**Keep using goban (OGS)** — It is the best fit for Yen-Go's requirements:

1. **Apache 2.0 license** — permissive, compatible with open source
2. **Puzzle mode built-in** — core OGS feature, battle-tested
3. **Active maintenance** — 252 npm releases
4. **TypeScript** — matches Yen-Go's strict TypeScript requirement
5. **Already integrated** — switching would be a massive refactor with zero benefit

**Avoid**:

- **jGoBoard** — CC-BY-NC-4.0 license is incompatible with open source distribution
- **EidoGo** — AGPL license + completely abandoned
- **WGo.js / Glift** — Abandoned, no TypeScript, no npm
- **Shudan** — Board display only; would need 3+ packages to match goban's functionality
- **BesoGo** — No npm, no TypeScript, no puzzle mode

---

_This document is a reference analysis. It does not propose any architectural changes to Yen-Go._
