# Target Reference Architecture — GoProblems.com Research(Beta)

> Reference design for the Enrichment Lab GUI. Based on screenshots captured 2026-03-10.

---

## Screenshot 1: GoProblems.com Research(Beta) View

**Source:** goproblems.com Research(Beta) panel for a 19x19 tsumego position.

### Layout (Left-to-Right)

```
+------------------+-----------------------------+--------------------------+
|  GO BOARD        |  ANALYSIS TABLE             |  (no right sidebar)      |
|  (fixed-size,    |  (below or beside board)    |                          |
|  dominates the   |  Order | Move | Prior |     |                          |
|  viewport)       |  Winrate | Score | Visits | |                          |
|                  |  PV | Preview               |                          |
|                  +-----------------------------+                          |
|                  |  Research controls          |                          |
+------------------+-----------------------------+--------------------------+
```

### Key Visual Characteristics

1. **Board Size**: Large, fixed-dimension board occupying roughly 50-60% of viewport width. Does NOT shrink with remaining content. Board size remains stable regardless of screen width.

2. **Board Rendering Style**:
   - Warm wood texture (kaya-like) background
   - Black stones: deep black with subtle 3D gradient/highlight
   - White stones: bright white with shell-like shading and subtle radial gradient
   - Grid lines: thin, dark brown
   - Coordinate labels: A-T (columns), 1-19 (rows) in small, readable font on edges
   - Star points (hoshi): small filled circles

3. **Score/Prior Overlays on Board**:
   - Top candidate moves shown directly ON the board intersections as colored circles/indicators
   - Each candidate shows the **score value** as text on the marker (e.g., "-52.8") and **visit count** below it (e.g., "1")
   - Color coding: orange/salmon for hovered candidate, possibly green for best move
   - The #1 move (E5 in screenshot, 98.9% prior, 392 visits) is highlighted distinctly
   - Hovering a row in the analysis table highlights that move's intersection on the board with score overlay

4. **Analysis Table** (right panel, below solution tree):
   - Columns: **Order | Move | Prior | Score | Visits | PV**
   - Screenshot example rows:
     - `1 | E5 | 98.9% | -0.0 | 392 | E5 F2 E2 E1 D...`
     - `2 | D5 | 0.5% | -91.2 | 1 | D5`
     - `3 | D2 | 0.3% | -52.8 | 1 | D2`
     - `4 | F2 | 0.1% | -68.3 | 1 | F2`
   - PV column shows the principal variation as a sequence of GTP moves
   - **Hover-to-preview**: Hovering over a row places **numbered semi-transparent stones** on the board showing the PV sequence (e.g., stones labeled 1, 2, 3, 4... for each move in the variation). Also highlights the candidate intersection with its score overlay.
   - Rows are sorted by visits (descending)
   - Score is signed: `-0.0` for neutral, `-91.2` for very bad

5. **Player-to-Move Indicator**:
   - Clear indicator: "Current Player: B" with a filled black stone icon
   - Shown in the right panel above the analysis table
   - Also shows aggregate stats: "Visits: 396, Score: -"

6. **Right Panel Layout** (from screenshot, top to bottom):
   - **Header**: "Research(Beta)" label
   - **Engine info**: Model name (e.g., "b10"), backend (e.g., "auto(webgl)"), visits target (e.g., "500")
   - **Action buttons**: "Stop Analysis", "Clear Analysis", "Show Problem Frame"
   - **Mini solution tree**: Compact colored-dot tree showing the solution graph. Nodes may also show **score overlays** on the tree branches.
   - **Player / Stats bar**: "Current Player: B | Visits: 396 | Score: -"
   - **Analysis table**: Order | Move | Prior | Score | Visits | PV

7. **Solution Tree with Score Overlays**:
   - The solution tree (mini tree view) also displays **score/prior information** on its nodes
   - Colored nodes indicate correct (green) vs wrong (red) moves
   - Hovering over a tree node may preview the board position at that node

8. **No Cluttered Sidebar**: The board and right panel take priority. No cramped SGF textarea competing for space.

### Color Palette (Dark Theme)

```
Background:       #1a1a2e (deep navy-black)
Panel/Card:       #16213e (darker blue-gray)
Text primary:     #e0e0e0 (light gray)
Text secondary:   #8a8a9a (muted gray)
Accent/links:     #4fc3f7 (light blue)
Green (correct):  #22c55e
Red (wrong):      #ef4444
Border:           #2a2a4a
```

### Fonts

- UI text: System sans-serif stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto)
- Monospace (for moves, PV, code): 'Fira Code', 'Consolas', monospace
- Font sizes: 11-13px for data, 14-16px for headers

---

## Screenshot 2: Yen-Go Enrichment Lab (Current State)

**Source:** Yen-Go Puzzle Enrichment Lab running at localhost:8999

### Current Layout

```
+---------+-------------------------------------------+
| SIDEBAR | BOARD (besogo)        | TREE  | PRIORS   |
| SGF     |                       | panel | panel    |
| input   |                       |       |          |
| Upload  +-----------------------+-------+----------+
| Enrich  | Status bar                                |
| Analyze | Analysis table                            |
| Cancel  +-------------------------------------------+
| Engine  | LOG PANEL (collapsed by default)           |
+---------+-------------------------------------------+
```

### Current Problems (Visible in Screenshot)

1. **Board shrinks dramatically** — On a wide screen, the board occupies a tiny fraction of the viewport. The `flex: 1` CSS on `.main-area` and `max-height: calc(100vh - 200px)` cause the board to be squeezed.

2. **Tree panel eats board space** — The BesoGo `panels: ['tree']` creates a side panel INSIDE the besogo-container that competes with the board for width.

3. **Policy priors panel** is appended inside the besogo panels column — competes for vertical space with the tree.

4. **Engine status shows "—" or "not_started"** — Confusing when user hasn't started analysis yet. Should show "Loaded / Unloaded / Starting..." instead.

5. **Log panel is tiny** — `max-height: 200px` with `max-height: 160px` for content. Too small for meaningful log reading.

6. **No score overlay on board** — GoProblems shows move scores/priors directly on board intersections. Our board is just raw stones.

7. **No PV preview on hover** — GoProblems animates the principal variation on the board when hovering over a candidate row. We don't have this.

8. **No player-to-move indicator** — Not immediately visible who is to play.

9. **Analysis table is below the board** — Takes up vertical space, pushing content down. Should be in a side panel.

10. **Enrich vs Analyze confusion** — Buttons exist but no explanation of what each does. Engine status says "not_started" after clicking Enrich.

11. **Board doesn't update for SSE events** — The board position doesn't reflect enrichment progress in real-time.

---

## Target Design (What We Want)

### Layout Goal

```
+------------------+-------------------------------+
| PIPELINE BAR (compact, top)                       |
+----------+-------+-------------------------------+
| SIDEBAR  | BOARD (fixed size,    | RIGHT PANEL    |
| SGF in   | dominant)            | - Solution Tree |
| Upload   |                      | - Policy Priors |
| Actions  |                      | - Analysis Table|
| Engine   |                      |   (scrollable)  |
| Status   |                      |                 |
+----------+----------------------+-----------------+
| LOG PANEL (taller, collapsible, monospace)        |
+---------------------------------------------------+
```

### Key Differences from Current

| Feature | Current | Target |
|---------|---------|--------|
| Board sizing | Flex, shrinks | Fixed min-width (e.g., 500px), dominates viewport |
| Solution tree | Inside besogo-container, steals board width | Right panel, separate from board |
| Analysis table | Below board | Right panel, below tree |
| Policy priors | Inside besogo panels | Right panel, below tree |
| Score on board | None | Overlay scores/priors on intersections |
| PV hover | None | Animate PV stones on board on hover |
| Player indicator | Hidden | Visible stone icon + text |
| Engine status | "not_started" / "—" | "Idle" / "Loaded" / "Running..." |
| Log panel height | 200px max | 300px min, resizable |
| Board SSE updates | Broken | Real-time position updates |

### Stone Rendering Target

Current BesoGo stones are flat SVG fills. Target:
- Black: `#1a1a1a` fill with subtle radial gradient highlight
- White: `#f0f0f0` fill with subtle radial gradient for depth
- Stroke: match fill color, 4px width (current is fine)
- Consider: Adding a subtle drop shadow for depth

---

## GoProblems Feature Parity Checklist

- [x] Fixed board size (doesn't shrink on wide screens)
- [x] Score/prior values overlaid on board intersections (score text + visit count)
- [x] Score/prior overlays on solution tree nodes
- [x] PV preview on hover with **numbered stones** (1, 2, 3... for each move in sequence)
- [x] Hovered candidate shows orange/salmon score overlay on its board intersection
- [x] Player-to-move indicator (stone icon + "Current Player: B/W" + aggregate visits/score)
- [x] Analysis table with Order, Move, Prior, Score, Visits, PV columns
- [x] Right panel layout: engine info, action buttons, mini tree, player stats, analysis table
- [x] Solution tree in right panel (not competing with board)
- [x] Policy priors bar chart in right panel
- [x] Clear engine status: Idle / Loaded / Starting / Running / Error
- [x] Larger log panel with better readability
- [x] Board updates in real-time during enrichment SSE events
- [x] Enrich vs Analyze tooltips explaining what each does
