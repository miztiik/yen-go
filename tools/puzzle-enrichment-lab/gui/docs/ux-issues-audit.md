# Enrichment Lab GUI — UX Issues Audit

> Audit date: 2026-03-10
> Reference: GoProblems.com Research(Beta) view
> Status: DRAFT — Awaiting user confirmation before implementation

---

## Critical Issues (Broken / Unusable)

### C1. Board Doesn't Update During SSE Enrichment Events
- **Symptom**: Clicking "Enrich" runs the pipeline (log panel shows progress), but the board position doesn't change to reflect the enriched SGF until the entire pipeline completes.
- **Root cause**: `processSSEEvent()` in `app.js` only calls `sgfText.set(data.sgf)` on the final `enriched_sgf` event with `status === 'complete'`. Intermediate `board_state` events log a message but don't update the board.
- **Impact**: User cannot visually follow the enrichment pipeline in real-time. Defeats the purpose of a "visual pipeline observer."
- **Fix**: On `board_state` events, update the board to show the current position being analyzed. On intermediate events that contain partial SGF or position data, render them.

### C2. Engine Status is Misleading
- **Symptom**: Engine status shows "—" on load, then "not_started" after health check. Clicking "Enrich" shows "Enriching..." but the engine status still says "not_started" until the engine actually starts.
- **Root cause**: `/api/health` returns `"not_started"` when `_engine_manager is None` (i.e., engine hasn't been lazily initialized yet). The engine only starts on first `/api/analyze` or `/api/enrich` call.
- **Impact**: User thinks something is broken. "Engine: not_started" reads as an error, not a "waiting for first use" state.
- **Fix**: Use clearer status labels: "Idle" (not yet initialized), "Starting..." (first request in progress), "Ready" (engine running), "Error" (startup failed). Consider adding a "Loading engine..." indicator when the first enrich/analyze kicks off.

---

## Major Issues (Poor UX, Feature Gaps)

### M1. Board Shrinks Dramatically on Wide Screens
- **Symptom**: On a 1920px+ wide monitor, the Go board occupies maybe 30-40% of the available space. There's huge empty space, but the board is tiny.
- **Root cause**: CSS layout uses `flex: 1` on `.main-area` which lets the board grow/shrink freely. The `#besogo-container` has `flex: 1 1 auto` with no `min-width`. BesoGo calculates board dimensions based on available container size, so when the container is taller than wide (due to the tree panel eating horizontal space), the board shrinks.
- **Impact**: Poor visual hierarchy. The board is the primary content but doesn't dominate.
- **GoProblems reference**: Board has a fixed pixel size that does not shrink. It dominates the viewport.
- **Fix**: Set a `min-width` on the board area (e.g., 500-600px). Consider fixing the board at a specific pixel dimension. Move the tree panel OUT of the besogo-container so it doesn't steal board width.

### M2. Solution Tree Steals Board Width
- **Symptom**: The BesoGo tree panel is rendered inside `#besogo-container` as a `.besogo-panels` div. This creates a horizontal split where the tree competes with the board for width inside the same flex container.
- **Root cause**: `besogo.create()` with `panels: ['tree']` creates the tree panel as a sibling inside the container. With `orient: 'landscape'`, the panels are placed to the right of the board.
- **Impact**: Board width = container width - tree panel width - priors panel width. On a narrow container, board becomes tiny.
- **GoProblems reference**: The solution tree is in a separate panel to the right, not inside the board container.
- **Fix**: Either (a) use `panels: []` in BesoGo and build a custom tree panel outside, or (b) create a right panel layout where `.besogo-panels` is pulled out of the board container via CSS/DOM restructuring.

### M3. No Score/Prior Overlays on Board Intersections or Solution Tree
- **Symptom**: After analysis, scores and priors only appear in the analysis table and the policy panel. The board itself shows no analysis indicators. The solution tree also shows no score annotations.
- **GoProblems reference**: GoProblems shows colored circles with score values and visit counts directly on board intersections for top candidate moves. The hovered candidate's intersection gets an orange/salmon overlay showing score (e.g., "-52.8") and visits (e.g., "1"). Additionally, the solution tree nodes also display score/prior information.
- **Impact**: User must cross-reference GTP coordinates between the table and the board mentally. This is the #1 most-wanted feature for analysis visualization.
- **Fix**: After analysis completes, overlay SVG elements on the BesoGo board at candidate move coordinates. Show: score value + visit count, color-coded by favorability. Also annotate solution tree nodes with score data.

### M4. No PV (Principal Variation) Preview on Hover with Numbered Stones
- **Symptom**: The analysis table shows PV as text (e.g., "D3 E5 F4 G3"). Hovering does nothing.
- **GoProblems reference**: Hovering over a candidate row places **numbered semi-transparent stones** on the board. If the PV is 4 moves long, stones labeled "1", "2", "3", "4" appear at the corresponding intersections showing the full predicted sequence. The hovered candidate's intersection also shows a score overlay (e.g., orange circle with "-52.8" and "1").
- **Impact**: User cannot visualize the continuation without mentally playing it out.
- **Fix**: On `mouseenter` of an analysis table row:
  1. Place numbered semi-transparent stones on the board for each PV move (e.g., 1, 2, 3...)
  2. Highlight the candidate's intersection with its score overlay (colored circle + score text)
  3. On `mouseleave`, remove all preview overlays.

### M5. No Player-to-Move Indicator
- **Symptom**: There's no visible indication of whose turn it is (Black or White).
- **Root cause**: The `status-bar` exists but is empty. `boardState` contains `currentPlayer` but it's not rendered.
- **GoProblems reference**: Clear player indicator (stone icon + "Black to play" / "White to play").
- **Fix**: Add a player indicator in the status bar — a filled circle (black or white) with text label.

### M6. Log Panel is Too Small
- **Symptom**: The log panel has `max-height: 200px` for the container and `max-height: 160px` for content. When enrichment is running, logs quickly fill this space and auto-scroll makes it hard to read.
- **Impact**: Important engine output is hidden. User must manually scroll to find errors.
- **Fix**: Increase default height to 300px. Make it resizable (CSS `resize: vertical` or a drag handle). When collapsed, show just the header. When expanded, show more content.

### M7. Enrich vs Analyze — No Explanation
- **Symptom**: Two buttons "Enrich" and "Analyze" with no tooltip or description. User doesn't know the difference.
- **Fix**: Add `title` tooltips:
  - Enrich: "Run full 10-stage pipeline: validate, refute, difficulty, teach"
  - Analyze: "Quick KataGo analysis of current board position (~1-3s)"
  - Also update the label to show state: "Idle" → "Running..." → "Complete" / "Error"

---

## Minor Issues (Polish)

### m1. Analysis Table Layout Could Be Improved
- **Current**: Table is below the board, taking vertical scroll space.
- **Better**: Move to the right panel, stacked under the solution tree and priors.

### m2. Board Stone Rendering is Flat
- **Current**: Flat SVG fills (`#1a1a1a` black, `#f0f0f0` white).
- **GoProblems**: Subtle radial gradients give depth. Multiple stone themes available.
- **Fix**: Add SVG radial gradient definitions to the board theme CSS/JS.

### m3. Sidebar SGF Textarea is Always Visible
- **Current**: The SGF textarea always shows, taking up sidebar space even after loading.
- **Better**: Collapse SGF input after loading. Show just "loaded: puzzle.sgf" with an expand button.

### m4. Pipeline Bar Pill Labels Could Be Icons
- **Current**: Text labels like "Parse SGF", "Extract Solution" are fine but verbose.
- **Better**: Consider abbreviated labels or icons for compact display.

---

## Priority Order for Implementation

1. **C1** — Board SSE updates (critical, broken feature)
2. **C2** — Engine status labels (critical, user confusion)
3. **M1 + M2** — Board sizing + tree separation (biggest visual impact)
4. **M3** — Score overlays on board (most-wanted analysis feature)
5. **M5** — Player-to-move indicator (quick win)
6. **M6** — Log panel sizing (quick win)
7. **M7** — Button tooltips (quick win)
8. **M4** — PV hover preview (complex, high value)
9. **m1-m4** — Polish items (lower priority)
