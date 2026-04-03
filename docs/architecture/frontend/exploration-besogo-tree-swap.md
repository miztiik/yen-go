# Exploration: Swapping Goban's Solution Tree with Besogo-Based Independent Component

**Last Updated:** 2026-02-17 (v2 — corrected after review)  
**Type:** Architectural Exploration (Read-Only — No Code Changes)  
**Author:** AI Assistant (research for decision-making)

---

## 1. Executive Summary

**Question:** What does it mean to replace Goban's built-in Canvas solution tree renderer with a Besogo-based independent tree component — and is it worth doing?

**Two approaches are evaluated:**

| Approach                                     | Complexity        | New code to write               | Independence                    |
| -------------------------------------------- | ----------------- | ------------------------------- | ------------------------------- |
| **A: Use Besogo library directly**           | Low (1–2 days)    | ~50 lines (thin Preact wrapper) | Full — Besogo is self-contained |
| **B: Port Besogo's algorithm to TypeScript** | Medium (4–5 days) | ~400–500 lines                  | Full — zero runtime dependency  |

**Key findings:**

1. **Besogo was never used as a runtime library in the frontend.** Despite appearances, all previous "Besogo" work (Specs 056, 123) was manual algorithm porting — the library itself was never loaded. The standalone copy at `tools/sgf-viewer-besogo/` was always a reference viewer only.

2. **The Besogo library CAN be used directly** as a standalone tree panel. `besogo.makeTreePanel(container, editor)` requires only a `<div>` and an editor instance — no board rendering required. The editor is 100% DOM-free and can be created from SGF without any visual component.

3. **Goban safely no-ops** when `move_tree_container` is omitted from config, so the swap requires zero patching of goban.

4. **The entire Besogo library is ~137 KB** (15 JS source files). The minimum subset for tree-only usage is **7 files, ~55 KB unminified** (~1,850 lines). For comparison, the goban npm package is orders of magnitude larger.

| Dimension             | Approach A (Library)               | Approach B (Port)                   |
| --------------------- | ---------------------------------- | ----------------------------------- |
| **Complexity**        | Low (1–2 days)                     | Medium (4–5 days)                   |
| **Risk**              | Low                                | Low-Medium                          |
| **Reversibility**     | High (< 30 min)                    | High (< 30 min)                     |
| **New code**          | ~50 lines wrapper                  | ~400–500 lines                      |
| **Maintenance**       | Library unchanged, wrapper trivial | Own layout algorithm to maintain    |
| **ESM compatibility** | Needs shim (global script)         | Native ESM                          |
| **Goban coupling**    | None — uses raw SGF                | None or optional (MoveTree adapter) |

---

## 2. Correction: Besogo Was Never Used as a Library

A key misconception must be corrected. Investigation of the full codebase, all specs, and the frontend history reveals:

**Besogo was never loaded as a runtime dependency.** Here's the evidence:

- Never appeared in `frontend/package.json`
- No `import` or `require` of besogo in `frontend/src/`
- No `<script>` tag in `frontend/index.html`
- No besogo assets in `frontend/public/`
- No Vite/webpack config references

What actually happened across three spec attempts:

| Attempt      | Spec                     | What was done                                                                                    | Outcome                                       |
| ------------ | ------------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| **Spec 056** | First tree visualization | **Manually ported** Besogo's algorithm to TypeScript/Preact. Used CSS pseudo-elements for lines. | "Failed port" — 2,400+ lines, wrong algorithm |
| **Spec 123** | Planned rewrite          | Planned **faithful port** of the 229-line algorithm as TSX+SVG.                                  | Superseded by Spec 125                        |
| **Spec 125** | Goban migration          | Deleted all custom code (~27,587 lines). Used goban's built-in Canvas tree.                      | Current state                                 |

The library at `tools/sgf-viewer-besogo/` has always been a standalone debugging viewer, not a frontend dependency.

**This means:** The option to use Besogo directly as a library — rather than re-porting its algorithm — has never actually been tried. This is the "already done work" that hasn't been leveraged.

---

## 3. Current State: How Goban's Solution Tree Works Today

### Architecture

```
                          GobanConfig
                              │
                              ▼
         ┌──────────────────────────────────────┐
         │            Goban Instance             │
         │  ┌─────────────┐  ┌───────────────┐  │
         │  │ Board Canvas │  │ Tree Canvas   │  │
         │  │ (rendering)  │  │ (internal)    │  │
         │  └──────┬───────┘  └───────┬───────┘  │
         │         │                  │           │
         │    board_div          move_tree_       │
         │    (external)         container        │
         │                       (external)       │
         └──────────────────────────────────────┘
                    │                  │
                    ▼                  ▼
         GobanContainer div     treeRef div
         (SolverView)           (SolverView sidebar)
```

### What goban does internally

1. Receives `move_tree_container` (a `<div>`) in `GobanConfig`
2. Creates a `<canvas>` element inside that container
3. Calls `move_tree_redraw()` on every board state change
4. Handles click-to-navigate on the tree canvas via internal event binding
5. Draws nodes (stones with move numbers), connecting paths (Bezier curves), correctness rings (green/red), and active path highlighting (40% opacity fade on off-path)
6. Auto-navigates the board when tree nodes are clicked (calls `engine.jumpTo()` internally)

### What YenGo controls

- A `<div ref={treeRef}>` in `SolverView.tsx` with CSS visibility gating (`hidden` during solving, visible in review mode)
- Passing `treeRef.current` as `moveTreeContainer` in `buildPuzzleConfig()`
- One-time global color overrides: `MoveTree.line_colors` (uniform gray) and `MoveTree.isobranch_colors`
- CSS rule: `[data-testid="solution-tree-container"] canvas { width: 100%; cursor: pointer; }`
- MutationObserver for auto-scrolling to active node
- Keyboard shortcuts (Left/Right/Up/Down) calling `goban.showPrevious/showNext/prevSibling/nextSibling`

---

## 4. Critical Discovery: Goban's No-Op Behavior

```javascript
// Inside goban's CanvasRenderer.move_tree_redraw():
if (!this.move_tree_container) {
  return; // ← Safe no-op. No canvas, no DOM mutation, no error.
}
```

If we omit `moveTreeContainer` from the config, goban will:

- ✅ Still render the board normally
- ✅ Still run the puzzle engine (correct/wrong move detection)
- ✅ Still maintain the `MoveTree` data structure in `engine.move_tree`
- ✅ Still fire all puzzle events
- ❌ NOT create any tree canvas — cleanly disabled

This is the key enabler for both approaches.

---

## 5. The Besogo Library: What We Already Have

### Library inventory at `tools/sgf-viewer-besogo/`

| Category             | Files                                                                                                                                                                                                    | Size            |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| JS source (15 files) | besogo.js, editor.js, gameRoot.js, treePanel.js, parseSgf.js, loadSgf.js, svgUtil.js, boardDisplay.js, coord.js, controlPanel.js, commentPanel.js, toolPanel.js, filePanel.js, namesPanel.js, saveSgf.js | **~137 KB**     |
| CSS (11 files)       | besogo.css + 10 theme variants                                                                                                                                                                           | ~7 KB           |
| Images (21 files)    | Stone PNGs + board textures                                                                                                                                                                              | ~2.2 MB         |
| besogo-all-min.js    | **BROKEN** — contains a GitHub Pages 404 HTML page, not actual JS                                                                                                                                        | 9 KB (unusable) |

### Minimum subset for tree-only usage: 7 files, ~55 KB

| File              | Lines | Required for tree?       | Purpose                                            |
| ----------------- | ----- | ------------------------ | -------------------------------------------------- |
| `besogo.js`       | 426   | Partial (namespace only) | Entry point, `window.besogo` namespace             |
| `editor.js`       | 545   | **YES**                  | Observer pattern, navigation API, tool state       |
| `gameRoot.js`     | 329   | **YES**                  | Game tree nodes with prototypal board inheritance  |
| `svgUtil.js`      | ~150  | **YES**                  | `svgEl()`, `svgStone()`, `svgLabel()`, `svgPlus()` |
| `parseSgf.js`     | ~170  | **YES**                  | SGF string parser (pure, no DOM)                   |
| `loadSgf.js`      | ~200  | **YES**                  | SGF parse tree → game tree loader                  |
| `treePanel.js`    | 229   | **YES**                  | SVG tree visualization                             |
| `boardDisplay.js` | 600+  | **NO**                   | Board rendering — not needed                       |
| `coord.js`        | ~100  | **NO**                   | Coordinate display — optional                      |
| `controlPanel.js` | ~200  | **NO**                   | Control buttons                                    |
| `commentPanel.js` | ~200  | **NO**                   | Comment display                                    |
| `toolPanel.js`    | ~180  | **NO**                   | Tool selector                                      |
| `filePanel.js`    | ~180  | **NO**                   | File import/export                                 |
| `namesPanel.js`   | ~70   | **NO**                   | Player names                                       |
| `saveSgf.js`      | ~160  | **NO**                   | SGF serialization                                  |

### Key architectural facts about Besogo's internals

1. **Editor is 100% DOM-free.** `besogo.makeEditor(19, 19)` creates a pure data model — no `document`, no DOM, no rendering. It's a model+controller with observer pattern.

2. **`makeTreePanel(container, editor)` is fully standalone.** Needs only a `<div>` and an editor. Does NOT depend on board display, control panel, or any other panel. Zero cross-panel coupling.

3. **SGF loading is two calls:**

   ```javascript
   var parsed = besogo.parseSgf(sgfString); // Pure string→object (no DOM)
   besogo.loadSgf(parsed, editor); // Object→game tree
   ```

4. **`besogo.create()` is NOT needed.** The main entry point unconditionally creates a board display. For tree-only usage, bypass it entirely and construct editor + tree panel directly.

5. **The tree panel manages its own SVG subtree** inside the container div. Preact won't conflict as long as it doesn't reconcile the container's children (standard `ref` pattern).

---

## 6. Approach A: Use Besogo Library Directly

### Architecture

```
                          GobanConfig (no move_tree_container)
                              │
                              ▼
         ┌─────────────────────────────────┐
         │        Goban Instance           │
         │  ┌─────────────┐               │
         │  │ Board Canvas │  (no tree)   │
         │  └──────┬───────┘               │
         └─────────┼───────────────────────┘
                   │
                   ▼
         GobanContainer div              Besogo (self-contained)
         (board rendering)               ┌──────────────────────┐
                                         │  besogo.editor       │
              Raw SGF ──────────────────▶│  besogo.parseSgf()   │
                                         │  besogo.loadSgf()    │
                                         │  besogo.makeTreePanel │
                                         │       ↓               │
                                         │  SVG tree in <div>   │
                                         └──────────────────────┘
         Bidirectional sync via callbacks:
           Goban cur_move event → editor.setCurrent(mapped node)
           Besogo navChange    → goban.engine.jumpTo(mapped node)
```

### How it works

1. **Disable goban's tree**: omit `moveTreeContainer` from config
2. **Load Besogo files**: either as concatenated global script or ESM-wrapped module
3. **Create Besogo editor from same SGF**: `besogo.parseSgf(sgf)` → `besogo.loadSgf(parsed, editor)`
4. **Create tree panel**: `besogo.makeTreePanel(containerDiv, editor)`
5. **Bidirectional sync** (the hard part — see below)

### The Besogo wrapper component (~50 lines)

```tsx
// Conceptual — not production code
function BesogoTree({ sgf, visible }: { sgf: string; visible: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<any>(null);

  useEffect(() => {
    const besogo = (window as any).besogo;
    const editor = besogo.makeEditor(19, 19);
    const parsed = besogo.parseSgf(sgf);
    besogo.loadSgf(parsed, editor);
    besogo.makeTreePanel(containerRef.current!, editor);
    editorRef.current = editor;
    return () => {
      containerRef.current!.innerHTML = "";
    };
  }, [sgf]);

  return <div ref={containerRef} className={visible ? "" : "hidden"} />;
}
```

### The bidirectional sync challenge

This is where Approach A gets interesting. Besogo has its own game tree (`gameRoot` nodes with prototypal board inheritance), while goban has its `MoveTree`. They are **completely different data structures** from different parsers.

Both parse the same SGF, so their trees are structurally isomorphic — but node identity is different. Syncing navigation requires mapping between them.

**Options for sync:**

| Strategy                                                                                                                        | Complexity      | Reliability                      |
| ------------------------------------------------------------------------------------------------------------------------------- | --------------- | -------------------------------- |
| **Move-path based** — track navigation as a path (e.g., `[0, 0, 1, 0]` = main line then branch) and replay it on the other tree | Low (~30 lines) | High for tsumego (shallow trees) |
| **Coordinate matching** — find node by `(x, y, moveNumber)`                                                                     | Low             | Medium (ambiguous in rare cases) |
| **No sync** — Besogo tree is display-only, no click navigation                                                                  | Trivial         | Loses interactivity              |
| **SGF-position sync** — on goban nav change, serialize position and find corresponding Besogo node                              | High            | Overkill                         |

**Recommendation:** Move-path sync. Walk from root to `engine.cur_move` in goban's tree, recording child indices. Replay that path on Besogo's tree via `editor.setCurrent()`. Reverse for click-to-navigate.

### ESM compatibility

Besogo is a pre-ESM global-script library (`window.besogo = ...`). Three options for Vite:

| Option                                     | Effort  | Cleanliness                                                         |
| ------------------------------------------ | ------- | ------------------------------------------------------------------- |
| **Concatenate 7 files, add ESM wrapper**   | ~1 hour | Good — single `besogo-tree.js` file, `export default window.besogo` |
| **Load via `<script>` tag in index.html**  | ~5 min  | Quick but global-polluting                                          |
| **Copy to `public/`, dynamic script load** | ~15 min | Works but async loading adds complexity                             |

**Recommendation:** Concatenate the 7 required files into a single `lib/besogo-tree-bundle.js`, wrap with `export default`, import as ESM. One-time 1-hour task.

### Effort estimate

| Task                                      | Effort          |
| ----------------------------------------- | --------------- |
| Bundle 7 Besogo files into ESM module     | 0.5 day         |
| Preact wrapper component                  | 0.5 day         |
| Bidirectional nav sync (move-path mapper) | 0.5 day         |
| Wire into SolverView + visibility gating  | 0.25 day        |
| CSS theming (dark mode for Besogo SVG)    | 0.25 day        |
| Testing                                   | 0.5 day         |
| **Total**                                 | **~2–2.5 days** |

### Pros / Cons

| Pro                                                        | Con                                                      |
| ---------------------------------------------------------- | -------------------------------------------------------- |
| Besogo's tree already works — no algorithm to implement    | Bidirectional sync adds a mapping layer                  |
| ~50 lines of new code vs ~400–500 for a port               | Besogo is unmaintained upstream (last commit years ago)  |
| Zero algorithm bugs — using proven code as-is              | Global-script library needs ESM wrapping                 |
| Besogo has its own SGF parser — fully independent of goban | Two SGF parsers in the bundle (goban's + Besogo's)       |
| If goban is removed later, Besogo can stand alone          | ~55 KB of library code for a 229-line algorithm's output |

---

## 7. Approach B: Port Besogo's Algorithm to TypeScript

(Preserved from v1 of this document)

### Architecture

```
         Goban Instance
         (no move_tree_container)
              │
              ├── engine.move_tree ──▶ SolutionTreePanel (Preact)
              ├── engine.cur_move  ──▶   (reads MoveTree data)
              └── events: cur_move ──▶   (subscribes for changes)
                                            │
                                            ▼
                                      Pure SVG tree
                                      (own layout algorithm)
```

### What gets ported

The core is `treePanel.js` (229 lines): `recursiveTreeBuild()`, `extendPath()`, `nextOpen[]`, `finishPath()`, `makeNodeIcon()`, `addSelectionMarker()`. Plus `svgUtil.js` helpers (~6 functions) replaced with inline TSX.

### Effort estimate

| Task                                         | Effort        |
| -------------------------------------------- | ------------- |
| Port layout algorithm to TypeScript          | 1 day         |
| Build Preact SVG component                   | 1 day         |
| Add correctness indicators (green/red rings) | 0.5 day       |
| Wire into SolverView + event subscription    | 0.5 day       |
| Dark mode + CSS theming                      | 0.5 day       |
| Testing                                      | 1 day         |
| **Total**                                    | **~4–5 days** |

### Pros / Cons

| Pro                                         | Con                                                  |
| ------------------------------------------- | ---------------------------------------------------- |
| Clean ESM — no global scripts, no wrapping  | More code to write and maintain (~400 lines)         |
| Direct access to goban's MoveTree (no sync) | Risk of porting bugs (happened twice before)         |
| No duplicate SGF parser in bundle           | Need to add correctness indicators that Besogo lacks |
| Full TypeScript type safety                 | Algorithm must be correctly understood               |
| Smaller runtime footprint                   | Third attempt at this specific port                  |

---

## 8. Approach Comparison

### The key question: Port vs. Use

| Dimension                | A: Use Library                                       | B: Port Algorithm                           |
| ------------------------ | ---------------------------------------------------- | ------------------------------------------- |
| **Code to write**        | ~50 lines                                            | ~400–500 lines                              |
| **Code to maintain**     | Besogo library (stable, unchanged) + 50-line wrapper | 400+ lines of own tree code                 |
| **Time to implement**    | 2–2.5 days                                           | 4–5 days                                    |
| **Historical success**   | Never tried before                                   | Failed twice (Specs 056, 123)               |
| **GobanTree coupling**   | Zero — uses raw SGF independently                    | Medium — reads MoveTree data                |
| **Navigation sync**      | Needs move-path mapper (~30 lines)                   | Direct — reads cur_move                     |
| **ESM cleanliness**      | Needs wrapping (1 hour)                              | Native                                      |
| **Bundle size impact**   | +55 KB (7 files)                                     | +5–10 KB (own code only)                    |
| **Risk of layout bugs**  | Zero — using proven rendering code                   | Medium — algorithm must be ported correctly |
| **Future goban removal** | Easier — Besogo can parse SGF independently          | Harder — need to replace MoveTree source    |
| **Dark mode**            | CSS override on Besogo SVG elements                  | Built into component from day one           |
| **Correctness rings**    | Would need to add (Besogo doesn't have them)         | Built into component from day one           |

### Performance: Both approaches identical

Tsumego puzzles have 5–30 nodes. At this scale, SVG (both approaches use SVG) performance is identical and negligible. No performance reason to port vs. use the library.

---

## 9. Syncing Two Trees: The Bidirectional Navigation Problem (Approach A Detail)

When using Besogo as a separate library, two separate game trees exist:

```
Goban engine:  MoveTree (from sgfToPuzzle → move_tree)
Besogo editor: gameRoot (from parseSgf → loadSgf)
```

Both are parsed from the same SGF, so they're structurally identical. Navigation sync:

### Goban → Besogo (board move changes → update tree highlight)

```
1. goban fires 'cur_move' event
2. Walk from engine.move_tree (root) to engine.cur_move
   recording child index at each step → path = [0, 0, 1, 0]
3. Walk Besogo's tree from root following same indices
4. editor.setCurrent(besogoNode) → tree panel updates marker
```

### Besogo → Goban (tree click → update board)

```
1. Besogo editor fires navChange
2. Walk from editor.getRoot() to editor.getCurrent()
   recording child index at each step → path = [0, 0, 1, 0]
3. Walk goban's engine.move_tree following same indices
4. engine.jumpTo(gobanNode) → board updates
```

**The mapper function is ~30 lines** and handles the entire sync. For tsumego trees (5–30 nodes), the walk is microseconds.

---

## 10. Reversibility (Both Approaches)

Switching back to goban's built-in tree is identical for both approaches:

1. Pass `moveTreeContainer: treeRef.current` back to `buildPuzzleConfig()` → goban tree reactivates
2. Remove the Besogo/custom component from SolverView JSX
3. Restore the canvas CSS rule

**Estimated revert time: < 30 minutes** for either approach.

---

## 11. Coupling Analysis

### What's already decoupled

| Concern            | Status                                                 |
| ------------------ | ------------------------------------------------------ |
| Board rendering    | `board_div` is completely separate from tree container |
| Puzzle engine      | `engine.move_tree` is data, not renderer               |
| Puzzle events      | Standard EventEmitter3 — subscribe from anywhere       |
| CSS styling        | Tree container is its own `<div>`                      |
| Keyboard shortcuts | Already external `KBShortcut` components               |

### What's coupled per approach

| Coupling                | Approach A (Library)                       | Approach B (Port)                    |
| ----------------------- | ------------------------------------------ | ------------------------------------ |
| Goban's `MoveTree` type | **None** — Besogo parses SGF independently | **Medium** — reads MoveTree directly |
| Navigation              | Via move-path sync (~30 lines)             | Via `engine.jumpTo()` + callback     |
| SGF format              | Both read SGF — format is the interchange  |
| Goban events            | Subscribes to `cur_move`                   | Subscribes to `cur_move`             |

**Approach A is more independent.** If goban is removed entirely, Approach A's tree keeps working (it has its own SGF parser + editor + renderer). Approach B would need a new data source.

---

## 12. What Does NOT Change (Both Approaches)

- `sgf-to-puzzle.ts` — still used by goban for board rendering
- `usePuzzleState.ts` — still manages puzzle state via goban engine
- `GobanContainer.tsx` — board rendering untouched
- `useTransforms.ts` — SGF transforms independent of tree
- All puzzle pages — they pass SGF to SolverView
- Goban's puzzle validation — `puzzle-correct-answer` / `puzzle-wrong-answer` events still fire

---

## 13. Historical Context

| Spec     | Approach                          | Lines        | Outcome                  | Lesson                                                    |
| -------- | --------------------------------- | ------------ | ------------------------ | --------------------------------------------------------- |
| 056      | Manual port (CSS pseudo-elements) | 2,400+       | Failed — wrong algorithm | Don't reinvent the rendering                              |
| 123      | Manual port (faithful SVG)        | ~300 planned | Superseded               | Good plan, but goban migration won the race               |
| 125      | Delete everything, use goban      | 0 custom     | Shipped                  | Solved the problem but increased goban coupling           |
| **This** | Use library directly OR port      | 50 or 400    | ?                        | First time the "use library directly" option is evaluated |

**The key insight:** The two previous failures (Specs 056, 123) both tried to **port the algorithm** — manually translating Besogo's JavaScript into TypeScript/Preact. The simpler option of just **using Besogo's proven code as-is** was never attempted.

---

## 14. Decision Framework

| If your goal is...                                  | Recommended approach                                              |
| --------------------------------------------------- | ----------------------------------------------------------------- |
| **Maximum independence from goban, minimum effort** | Approach A (use library) — 2 days, ~50 lines, zero algorithm risk |
| **Clean ESM codebase, no legacy globals**           | Approach B (port) — 4-5 days, native TypeScript                   |
| **Fastest path to working tree swap**               | Approach A                                                        |
| **Smallest bundle size**                            | Approach B (saves ~45 KB)                                         |
| **Eventual full goban removal**                     | Approach A (Besogo stands alone) or B with adapter                |
| **Adding correctness rings (green/red)**            | Either — Approach A needs SVG overlay, Approach B builds it in    |
| **Not worth the effort right now**                  | Keep goban's tree. Revisit when goban coupling becomes painful.   |

---

## 15. Recommendation

**Start with Approach A (use Besogo library directly)** for three reasons:

1. **It's the simplest thing that could work.** ~50 lines of Preact wrapper + ~30 lines of nav sync vs ~400+ lines of ported algorithm code.

2. **It avoids the "third failed port" anti-pattern.** Previous attempts to port Besogo's algorithm failed (056) or were superseded (123). Using the library directly eliminates algorithm-porting risk entirely.

3. **It maximizes independence.** Besogo parses SGF, manages its own game tree, and renders its own SVG. It doesn't know or care about goban. If goban is removed later, the tree component continues working with zero changes.

4. **It's fully reversible.** Re-enable goban's tree in < 30 minutes.

After Approach A is working, Approach B can be evaluated as an optimization if the ~55 KB bundle size or ESM cleanliness matters enough. But the working tree component exists first, and YAGNI applies to the port.

---

> **See also:**
>
> - [Architecture: Goban Integration](./goban-integration.md) — Current goban architecture
> - [Reference: Solution Tree Visualization Analysis](../../reference/solution-tree-visualization-analysis.md) — 4-implementation comparison
> - [Besogo Source](../../../tools/sgf-viewer-besogo/) — Complete library (~137 KB JS)
