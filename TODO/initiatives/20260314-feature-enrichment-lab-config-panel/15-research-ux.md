# Research: UI/UX Patterns for Config Panel & Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Research question**: What visual patterns, widget designs, and layout strategies should the Config Panel & Sidebar Redesign adopt for a dark-themed developer tool GUI?
**Last Updated**: 2026-03-14

---

## 1. Research Question & Boundaries

| q_id | question | status |
|------|----------|--------|
| RQ-1 | What sidebar stepper/progress patterns work for pipeline stages? | ✅ resolved |
| RQ-2 | What accordion/grouping patterns work for 45 config parameters? | ✅ resolved |
| RQ-3 | What slider/input widget patterns work for dark themes? | ✅ resolved |
| RQ-4 | How should constrained weight sliders (sum=100) be implemented? | ✅ resolved |
| RQ-5 | What scroll/space strategy fits a dense sidebar? | ✅ resolved |
| RQ-6 | Should we use Tailwind, hand-written CSS, or a CSS-only framework? | ✅ resolved |

---

## 2. Internal Code Evidence

### 2.1 Current GUI Stack & CSS Variables

| R-ID | Artifact | Finding |
|------|----------|---------|
| I-1 | [gui/css/styles.css](../../tools/puzzle-enrichment-lab/gui/css/styles.css) | 11 CSS custom properties on `:root` (`--bg`, `--bg-panel`, `--bg-input`, `--text`, `--text-dim`, `--border`, `--accent`, `--green`, `--red`, `--yellow`, `--blue-pulse`). Dark navy palette `#1a1a2e`. No build step — plain `.css` served by FastAPI static mount. |
| I-2 | [gui/css/styles.css](../../tools/puzzle-enrichment-lab/gui/css/styles.css) | Layout: 3-column CSS Grid `minmax(180px, 260px) 1fr minmax(280px, 360px)`. Sidebar is `flex-column`, `gap: 10px`, `overflow-y: auto`. |
| I-3 | [gui/src/state.js](../../tools/puzzle-enrichment-lab/gui/src/state.js) | Observable atom pattern: `createState(initial)` → `{get, set, subscribe}`. Simple pub/sub, no framework. Pipeline stages stored as array of `{id, label, status}` objects. |
| I-4 | [gui/src/pipeline-bar.js](../../tools/puzzle-enrichment-lab/gui/src/pipeline-bar.js) | 10 stages rendered as horizontal pills in `#pipeline-bar` header. States: `pending` (gray) → `active` (blue pulse) → `complete` (green) → `error` (red). Labels: Parse SGF, Extract Solution, Tsumego Frame, KataGo Analysis, Validate Move, Refutations, Level ID, Assemble, Hints+Comments, Build SGF. |
| I-5 | [gui/src/sgf-input.js](../../tools/puzzle-enrichment-lab/gui/src/sgf-input.js) | Sidebar contains: textarea (6 rows), Upload/Download buttons, Enrich/Analyze/Cancel buttons. ~60-70% of sidebar height is empty below `#run-info`. |
| I-6 | [gui/src/log-panel.js](../../tools/puzzle-enrichment-lab/gui/src/log-panel.js) | Collapsible panel pattern already exists: toggle via class `collapsed`, drag-resize handle. This same pattern can be reused for accordion sections. |
| I-7 | [frontend/package.json](../../frontend/package.json) | Main app uses Tailwind CSS v4.1.18 with `@tailwindcss/vite` plugin. Build-step dependent. |
| I-8 | [15-research.md](./15-research.md) | 45 config parameters cataloged across 7 groups (Analysis, Refutations, AI-Solve, Validation, Difficulty, Teaching, Ko). MVP subset: 21 params (C-1 to C-5, C-10 to C-15, C-22 to C-28). |

### 2.2 Existing CSS Widget Patterns

| R-ID | Pattern | CSS Selector | Reusable? |
|------|---------|-------------|-----------|
| W-1 | Panel box | `.status-box` | ✅ `background: var(--bg-panel)`, `border: 1px solid var(--border)`, `border-radius: 6px`, `padding: 8px` |
| W-2 | Button variants | `.btn`, `.btn-primary`, `.btn-sm`, `.btn-danger` | ✅ Good base for toggle buttons |
| W-3 | Bar chart row | `.prior-row` + `.prior-bar-track` + `.prior-bar-fill` | ✅ Can be adapted for slider track styling |
| W-4 | Collapse toggle | `.hidden` class + JS toggle | ✅ Used by `#run-info`, log panel |
| W-5 | Pulse animation | `@keyframes pulse` | ✅ For active stage indicator |
| W-6 | Monospace code | `font-family: 'Fira Code', 'Consolas', monospace` | ✅ For numeric displays |

---

## 3. External References

### 3.1 Sidebar Stepper/Progress Patterns (RQ-1)

| R-ID | Reference | Pattern | Applicability |
|------|-----------|---------|---------------|
| E-1 | **VS Code Source Control sidebar** | Vertical list with status icons (modified ●, staged ✓, untracked U). Dense, single-line items. No animation, pure icon+label. | High — the simplest model. Status icon left, label right. Compact single-line per stage. |
| E-2 | **GitHub Actions workflow sidebar** | Vertical stepper with circle icons connected by vertical lines. States: gray circle (pending) → spinner (running) → green check (success) → red X (failure). Timing shown inline. | High — the gold standard for pipeline steppers. Connected dots pattern. |
| E-3 | **GitLab CI pipeline sidebar** | Similar to GitHub Actions. Numbered circles with connecting lines. Expandable per-job details. Duration shown as badge. | Medium — more complex than needed, but the connecting-line pattern is proven. |
| E-4 | **Grafana query editor sidebar** | Collapsible sections with header bars. Each section has a chevron toggle. Dense, functional. No stepper concept. | Medium — relevant for config grouping pattern, not for stage progress. |
| E-5 | **KaTrain sidebar** | Left panel shows move history with colored dots (mistake severity). Analysis settings accessible via modal dialog. Engine status shown as text. | Medium — KaTrain uses modal dialogs for settings, not inline sidebar configuration. The colored-dot pattern for status is useful. |
| E-6 | **LizGoban** | Config via `config.json` file + Preferences dialog. No inline sidebar config. Tsumego frame feature. Electron-based, uses menus rather than sidebar panels. | Low — file-based config, no sidebar config UI to reference. |

**Recommended pattern**: GitHub Actions–style vertical stepper with connected dots.

### 3.2 Config Accordion/Grouping (RQ-2)

| R-ID | Reference | Pattern | Applicability |
|------|-----------|---------|---------------|
| E-7 | **VS Code Settings UI** | Grouped sections with bold header, collapsible. Each setting: label + widget + description below. Search bar at top filters settings across all groups. Maximum 2 levels of nesting. | High — the best model for developer tool settings. |
| E-8 | **Chrome DevTools Elements panel** | Collapsible property groups (Layout, Box Model, etc.). Compact single-line per property. Inline editing on click. | High — extremely dense, good for constrained sidebar width. |
| E-9 | **Grafana panel options** | Collapsible sections with colored left border. Mixed widgets (sliders, dropdowns, toggles, text). Auto-collapse inactive sections. Section header shows current state summary. | High — directly comparable: analysis tool with many tuning parameters. |
| E-10 | **Figma right panel** | Flat sections separated by thin lines. No accordion chrome, just inline expand/collapse. Ultra-compact. | Medium — too minimal for 45 parameters. |

**Recommended pattern**: Grafana-style collapsible sections with left accent border.

### 3.3 Dark Theme Widget Patterns (RQ-3)

| R-ID | Reference | Pattern | Applicability |
|------|-----------|---------|---------------|
| E-11 | **VS Code native range inputs** | Styled with CSS custom properties. Track: thin gray line. Thumb: small circle with border. Value shown to the right. | High — simple, proven in dark themes. |
| E-12 | **Grafana range sliders** | Custom track with filled portion (accent color). Thumb with hover state. Value label inside or beside the thumb. Often paired with number input for direct entry. | High — dual-input pattern (slider + number) is ideal for precision. |
| E-13 | **iOS toggle switch CSS pattern** | Sliding oval with circle thumb. 2 states via `:checked` pseudo-class. Pure CSS, no JS needed. | High — universally recognized, compact. |
| E-14 | **Chrome DevTools color/number inputs** | Inline number with up/down arrows on hover. Drag to scrub value. Focus state shows full input. | Medium — scrub-to-change is nice but complex to implement. |
| E-15 | **Open Props / Pico CSS toggle** | CSS-only checkbox → toggle transformation using `appearance: none` + custom styling. Minimal code. | High — aligns with "no build step" constraint. |

### 3.4 Constrained Weight Sliders (RQ-4)

| R-ID | Reference | Pattern | Description |
|------|-----------|---------|-------------|
| E-16 | **Audio mixing boards (Ableton, FL Studio)** | Vertical faders with dB scales. Moving one fader does NOT auto-adjust others. Independent channels. Sum is not constrained. | Low — not applicable; audio mixing doesn't enforce sum constraint. |
| E-17 | **Portfolio allocation tools (Betterment, Wealthfront)** | Horizontal bars or pie chart with linked sliders. Moving one slider proportionally redistributes remaining to other sliders. Visual feedback via stacked bar or pie. | High — clean proportional redistribution model. |
| E-18 | **Voting/budget allocation UIs (participatory budgeting)** | Distribute N tokens across M categories. Each has a slider. "Remaining" counter shown prominently. Over-allocation blocked or warned. | High — simpler than proportional redistribution. |
| E-19 | **Google Analytics custom channel grouping** | Percentage inputs with validation (sum must equal 100%). Manual entry with warning banner if sum ≠ 100. | Medium — simplest approach but worst UX. |

**Two viable approaches:**

**Approach A: Proportional redistribution** — When dragging slider X from 35→45 (+10), distribute −10 proportionally across the other 4 sliders based on their relative weight. This is what portfolio tools use. Code: ~30-40 lines of JS.

**Approach B: Remainder counter** — Show a "Remaining: N%" counter above the group. Each slider is independent. If sum ≠ 100, show warning (red text). Normalize button redistributes automatically. Code: ~15-20 lines of JS.

### 3.5 Sidebar Scroll/Space Strategy (RQ-5)

| R-ID | Reference | Pattern | Description |
|------|-----------|---------|-------------|
| E-20 | **VS Code Explorer sidebar** | Single scroll container. Sticky section headers. Tree structure with collapse. | Medium — works but loses pinned actions. |
| E-21 | **Grafana sidebar** | Fixed top (search/nav), scrollable middle (content), fixed bottom (actions). Three-zone layout. | High — best for our use case: pinned SGF input top, scrollable config, pinned actions bottom. |
| E-22 | **Chrome DevTools Elements panel** | Full scroll, no fixed zones. But actions are in the tab bar (outside scroll). | Medium — actions are already accessible outside the scrolling area. |
| E-23 | **Figma right panel** | Fully scrollable. Section headers are visually distinct but not sticky. | Low — loses pinned context. |

**Recommended strategy**: Three-zone sidebar (see Section 4).

### 3.6 Tailwind vs Custom CSS (RQ-6)

| R-ID | Option | Pros | Cons | Verdict |
|------|--------|------|------|---------|
| E-24 | **A: Add Tailwind** | Consistency with `frontend/`. Rapid prototyping. Responsive utilities. | Requires build step (Vite/PostCSS). The enrichment lab is served by FastAPI `StaticFiles` — no Vite integration. Adds complexity for a developer tool. Tailwind v4 requires @theme directive setup. | ❌ **Reject** — the build-step requirement conflicts with the static-file serving model. |
| E-25 | **B: Continue hand-written CSS** | Zero build step. Already working. CSS custom properties provide theming. Full control. Simple for future maintainers. | No utility classes. Verbose for layout. Must write all widgets from scratch. | ✅ **Recommend** — extends the existing pattern naturally. |
| E-26 | **C: Open Props** | CSS custom properties (no build step). Design token library. Works with static files. | Adds 14KB+ of CSS variables. Overlaps with existing custom properties. Learning curve for property names. Could conflict. | ❌ **Reject** — overlap with existing `--bg`, `--accent` etc. would create confusion. |
| E-27 | **D: Pico CSS** | Classless CSS framework. Works with static files. Dark mode built-in. | Opinionated reset that would clash with existing styles. Not designed for sidebar-dense layouts. | ❌ **Reject** — too opinionated for integration. |

---

## 4. Candidate Adaptations for Yen-Go

### 4.1 Recommended Sidebar Layout (Wireframe)

```
┌────────────────────────────┐
│ FIXED ZONE (top)           │
│ ┌────────────────────────┐ │
│ │ SGF Input              │ │
│ │ [textarea 4 rows]      │ │
│ │ [Upload] [Download]    │ │
│ │ [Enrich] [Analyze] [X] │ │
│ └────────────────────────┘ │
│ ┌────────────────────────┐ │
│ │ Engine: b18c384 ● ready│ │
│ └────────────────────────┘ │
├────────────────────────────┤
│ SCROLL ZONE (middle)       │
│ ┌────────────────────────┐ │
│ │ Pipeline Progress       │ │
│ │ ○─ Parse SGF     ✓ 12ms│ │
│ │ ○─ Solve Paths   ✓ 1.2s│ │
│ │ ●─ KataGo Anlys  ⟳ ... │ │
│ │ ○─ Validate           │ │
│ │ ○─ Refutations        │ │
│ │ ○─ Difficulty         │ │
│ │ ○─ Assemble           │ │
│ │ ○─ Techniques         │ │
│ │ ○─ Teaching           │ │
│ │ ○─ Build SGF          │ │
│ └────────────────────────┘ │
│ ┌────────────────────────┐ │
│ │ ▸ Analysis    [3 params]│ │
│ │ ▸ Refutations [6 params]│ │
│ │ ▸ AI-Solve   [8 params]│ │
│ │ ▸ Validation  [4 params]│ │
│ │ ▸ Difficulty  [7 params]│ │
│ │ ▸ Teaching    [3 params]│ │
│ │ ▸ Ko Analysis [2 params]│ │
│ └────────────────────────┘ │
│                            │
│ (expanded accordion):      │
│ ┌────────────────────────┐ │
│ │ ▾ Analysis             │ │
│ │ ┊ T1 Visits  ═══●═ 500│ │
│ │ ┊ T2 Visits  ══●══2000│ │
│ │ ┊ Symmetries [●──] 4/8 │ │
│ └────────────────────────┘ │
├────────────────────────────┤
│ FIXED ZONE (bottom)        │
│ ┌────────────────────────┐ │
│ │ run: abc123 trace: def │ │
│ └────────────────────────┘ │
└────────────────────────────┘
```

**Rationale**: Three-zone layout (E-21 Grafana pattern). SGF input + action buttons are always visible (fixed top). Config accordion + pipeline progress scroll together in the middle. Run metadata pinned at bottom.

### 4.2 Pipeline Stage Progress Widget

**Pattern**: Vertical stepper with connected line (E-2 GitHub Actions).

**HTML structure:**

```html
<div class="stage-stepper">
  <div class="stage-item stage-complete">
    <div class="stage-line"></div>
    <div class="stage-dot"></div>
    <div class="stage-content">
      <span class="stage-name">Parse SGF</span>
      <span class="stage-time">12ms</span>
    </div>
  </div>
  <div class="stage-item stage-active">
    <div class="stage-line"></div>
    <div class="stage-dot"></div>
    <div class="stage-content">
      <span class="stage-name">KataGo Analysis</span>
      <span class="stage-time">1.2s</span>
    </div>
  </div>
  <div class="stage-item stage-pending">
    <div class="stage-line"></div>
    <div class="stage-dot"></div>
    <div class="stage-content">
      <span class="stage-name">Validate Move</span>
    </div>
  </div>
</div>
```

**CSS:**

```css
.stage-stepper {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  padding: 3px 0;
  font-size: 12px;
}

/* Connecting vertical line */
.stage-item:not(:last-child) .stage-line {
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: -8px;
  width: 2px;
  background: var(--border);
}
.stage-item.stage-complete:not(:last-child) .stage-line {
  background: var(--green);
}

/* Dot indicator */
.stage-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--border);
  background: var(--bg);
  z-index: 1;
}

.stage-complete .stage-dot {
  background: var(--green);
  border-color: var(--green);
}
.stage-active .stage-dot {
  background: var(--blue-pulse);
  border-color: var(--blue-pulse);
  animation: pulse 1.2s infinite;
}
.stage-error .stage-dot {
  background: var(--red);
  border-color: var(--red);
}

/* Content */
.stage-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stage-name {
  color: var(--text-dim);
}
.stage-complete .stage-name {
  color: var(--text);
}
.stage-active .stage-name {
  color: var(--accent);
  font-weight: 600;
}
.stage-time {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 10px;
  color: var(--text-dim);
}
```

**Total height for 10 stages**: ~220px (22px per item). Compact enough to coexist with config sections.

### 4.3 Config Accordion Widget

**Pattern**: Grafana-style collapsible sections (E-9) with left accent border.

**HTML structure:**

```html
<div class="config-panel">
  <div class="config-group" data-group="analysis">
    <button class="config-group-header" aria-expanded="false">
      <span class="config-chevron">▸</span>
      <span class="config-group-title">Analysis</span>
      <span class="config-group-count">3</span>
    </button>
    <div class="config-group-body hidden">
      <!-- Individual config items go here -->
    </div>
  </div>
</div>
```

**CSS:**

```css
.config-panel {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.config-group {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.config-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 8px;
  background: none;
  border: none;
  border-left: 3px solid var(--accent);
  color: var(--text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
}
.config-group-header:hover {
  background: rgba(255,255,255,0.03);
}
.config-group-header[aria-expanded="true"] .config-chevron {
  transform: rotate(90deg);
}

.config-chevron {
  font-size: 10px;
  transition: transform 0.15s;
  color: var(--text-dim);
}

.config-group-count {
  margin-left: auto;
  background: rgba(255,255,255,0.08);
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
  color: var(--text-dim);
}

.config-group-body {
  padding: 4px 8px 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border);
}

/* Transition for expand/collapse */
.config-group-body:not(.hidden) {
  animation: config-expand 0.15s ease-out;
}
@keyframes config-expand {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 500px; }
}
```

**Nesting depth**: Maximum 1 level (group → items). No sub-groups needed for 7 categories.

### 4.4 Widget Library (Dark Theme)

#### 4.4.1 Range Slider with Value Display

```html
<div class="config-item">
  <div class="config-item-header">
    <label class="config-label">T1 Visits</label>
    <span class="config-value">500</span>
  </div>
  <div class="config-slider-row">
    <input type="range" class="config-slider" min="50" max="5000" step="50" value="500">
  </div>
  <div class="config-range-labels">
    <span>50</span>
    <span class="config-default">default: 500</span>
    <span>5000</span>
  </div>
</div>
```

```css
.config-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.config-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-label {
  font-size: 11px;
  color: var(--text);
}

.config-value {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
  color: var(--accent);
  min-width: 40px;
  text-align: right;
}

.config-slider-row {
  display: flex;
  align-items: center;
}

/* Custom range slider for dark theme */
.config-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  outline: none;
}
.config-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid var(--bg-panel);
  box-shadow: 0 0 0 1px var(--accent);
}
.config-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid var(--bg-panel);
}
.config-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 2px;
}
.config-slider:focus::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.3);
}

.config-range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: var(--text-dim);
}

.config-default {
  font-style: italic;
  opacity: 0.6;
}
```

#### 4.4.2 Compact Number Input

```html
<div class="config-item">
  <div class="config-item-header">
    <label class="config-label">Max Candidates</label>
  </div>
  <input type="number" class="config-number" min="1" max="20" step="1" value="5">
</div>
```

```css
.config-number {
  width: 100%;
  padding: 4px 6px;
  background: var(--bg-input);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 3px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
}
.config-number:focus {
  border-color: var(--accent);
  outline: none;
}
.config-number::-webkit-inner-spin-button {
  opacity: 0.5;
}
.config-number:hover::-webkit-inner-spin-button {
  opacity: 1;
}
```

#### 4.4.3 Toggle Switch

```html
<div class="config-item config-item-row">
  <label class="config-label">Tree Validation</label>
  <label class="config-toggle">
    <input type="checkbox" checked>
    <span class="toggle-track">
      <span class="toggle-thumb"></span>
    </span>
  </label>
</div>
```

```css
.config-item-row {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.config-toggle {
  position: relative;
  cursor: pointer;
}
.config-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}

.toggle-track {
  display: inline-block;
  width: 32px;
  height: 18px;
  background: rgba(255,255,255,0.15);
  border-radius: 9px;
  transition: background 0.2s;
  position: relative;
}

.config-toggle input:checked + .toggle-track {
  background: var(--accent);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.config-toggle input:checked + .toggle-track .toggle-thumb {
  transform: translateX(14px);
}
```

#### 4.4.4 Dropdown (Select)

```html
<div class="config-item">
  <div class="config-item-header">
    <label class="config-label">Ko Rules (none)</label>
  </div>
  <select class="config-select">
    <option value="chinese">Chinese</option>
    <option value="tromp-taylor">Tromp-Taylor</option>
    <option value="japanese">Japanese</option>
  </select>
</div>
```

```css
.config-select {
  width: 100%;
  padding: 4px 6px;
  background: var(--bg-input);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8'%3E%3Cpath d='M0 2l4 4 4-4' fill='none' stroke='%238a8a9a' stroke-width='1.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 6px center;
  padding-right: 20px;
}
.config-select:focus {
  border-color: var(--accent);
  outline: none;
}
.config-select option {
  background: var(--bg-panel);
  color: var(--text);
}
```

### 4.5 Constrained Weight Sliders (sum=100)

**Recommended approach**: **Approach B (Remainder counter)** with normalize button for MVP. Proportional redistribution (Approach A) is better UX but adds complexity.

```html
<div class="config-weights">
  <div class="weights-header">
    <span class="config-label">Structural Weights</span>
    <span class="weights-sum" id="weights-sum">100%</span>
    <button class="btn-sm weights-normalize" id="weights-normalize" disabled>Normalize</button>
  </div>
  <div class="weight-row">
    <label class="weight-label">sol_depth</label>
    <input type="range" class="config-slider weight-slider" min="0" max="100" step="1" value="35">
    <span class="weight-value">35</span>
  </div>
  <!-- ...repeat for branch_count(22), local_candidates(18), refutation_count(15), proof_depth(10) -->
</div>
```

```css
.weights-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.weights-sum {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
  color: var(--green);
  margin-left: auto;
}
.weights-sum.invalid {
  color: var(--red);
}

.weights-normalize {
  opacity: 0.5;
}
.weights-normalize:not(:disabled) {
  opacity: 1;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}

.weight-label {
  font-size: 10px;
  color: var(--text-dim);
  width: 80px;
  flex-shrink: 0;
}

.weight-value {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 10px;
  color: var(--accent);
  width: 24px;
  text-align: right;
}
```

**JS logic sketch (Approach B):**

```javascript
function updateWeightSum() {
  const sliders = document.querySelectorAll('.weight-slider');
  const sum = [...sliders].reduce((s, el) => s + Number(el.value), 0);
  const sumEl = document.getElementById('weights-sum');
  sumEl.textContent = `${sum}%`;
  sumEl.classList.toggle('invalid', sum !== 100);
  document.getElementById('weights-normalize').disabled = (sum === 100);
}

function normalizeWeights() {
  const sliders = [...document.querySelectorAll('.weight-slider')];
  const sum = sliders.reduce((s, el) => s + Number(el.value), 0);
  if (sum === 0) return;
  sliders.forEach(el => {
    el.value = Math.round((Number(el.value) / sum) * 100);
  });
  // Fix rounding: add remainder to largest
  const newSum = sliders.reduce((s, el) => s + Number(el.value), 0);
  if (newSum !== 100) {
    const sorted = sliders.sort((a, b) => Number(b.value) - Number(a.value));
    sorted[0].value = Number(sorted[0].value) + (100 - newSum);
  }
  updateWeightSum();
}
```

### 4.6 Reference Descriptions (Imagined Screenshots)

| R-ID | Tool | Description of Relevant UI |
|------|------|---------------------------|
| REF-1 | **VS Code Settings** | Dark background (#1e1e1e). Left sidebar: flat list of categories. Right: settings with label above, widget below, faint description beneath. Each setting is ~40-50px tall. Search bar at top. Groups separated by bold headers with top margin. |
| REF-2 | **GitHub Actions sidebar** | Dark sidebar on left. Workflow steps shown as vertical list. Each step: circle icon (16px) + stage name + duration. Completed = green circle with check mark. Running = animated spinner circle. Failed = red circle with X. Vertical line (2px, gray) connects circles between items. Active step highlighted with slight background tint. |
| REF-3 | **Grafana panel options sidebar** | Right sidebar ~300px. Dark (#111217). Sections with bold white header + chevron toggle. Left border 3px accent (blue/purple). Inside: mixed controls — sliders with numeric value on right, toggles aligned right, dropdowns full width. Section collapsed shows just header (28px). Expanded sections scroll independently. |
| REF-4 | **KaTrain settings dialog** | Modal overlay. Dark background. Two columns: category list (left, ~120px) + settings (right). Settings use Kivy widgets: sliders with blue track, text inputs for precise values, checkboxes. "Calibrated" options highlighted with lighter background. Rank estimate shown live as settings change. |
| REF-5 | **Chrome DevTools Elements panel (Computed tab)** | Ultra-dense. Single-line items: property name (left-aligned, dim gray) + value (right-aligned, white). Expandable groups collapse to header-only. Filter bar at top. ~16px per row. No whitespace waste. |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| RK-1 | **45 parameters in 180-260px sidebar** may feel cramped | Medium | Use accordion pattern — only 1 group expanded at a time. Collapsed state shows only group headers (~28px × 7 = ~196px). Well within sidebar constraint. |
| RK-2 | **Range slider thumb precision** at low sidebar widths (180px) | Low | Pair slider with editable number input for exact values. Slider for rough, input for fine. At 180px with 8px padding × 2, track is 164px wide — usable. |
| RK-3 | **Browser CSS variance** for `input[type=range]` styling | Low | Use both `-webkit-` and `-moz-` prefixes. Test in Chrome (primary dev browser). Firefox fallback is acceptable for developer tool. |
| RK-4 | **Constrained weight slider rounding** errors (sum ≠ 100 due to integer rounding) | Low | Normalize function adds remainder to largest. Show explicit sum counter so user sees the constraint. |
| RK-5 | **Accordion state persistence** — reopening the page loses expanded/collapsed state | Low | Store accordion state in `localStorage` key `enrichment-lab-config-accordion`. Small effort, nice polish. |
| RK-6 | **No license concerns** — all widget CSS is hand-written, using standard CSS techniques. No copied code. | None | N/A |
| RK-7 | **Performance** — 45 slider `input` events firing during drag | Low | Debounce input events (100ms). Config changes are sent only on `change` event (mouseup), not during drag. |

**Rejected alternatives:**

| R-ID | Alternative | Reason for Rejection |
|------|-------------|---------------------|
| REJ-1 | Tailwind CSS for enrichment lab | Build step required; FastAPI serves static files with no bundler pipeline. Adds maintainability burden for a developer tool. |
| REJ-2 | Config as separate tab/route | Breaks the "unified workflow" requirement. User must mentally map between tabs. Sidebar inline is better for tuning workflow. |
| REJ-3 | Config in right panel | Right panel is already occupied by analysis table + solution tree + policy priors. It's the "results" panel. Config belongs in "inputs" sidebar. |
| REJ-4 | Horizontal pipeline pills (status quo) | Wastes 40px of vertical space. Disconnected from the workflow. User specified removal. |
| REJ-5 | Audio mixing board approach for weights | Over-engineered. Vertical faders need more width than 180-260px sidebar offers. Overkill for 5 values. |
| REJ-6 | Open Props CSS framework | Overlapping custom property names with existing `:root` vars would cause confusion and potential bugs. |

---

## 6. Planner Recommendations

| P-ID | Recommendation | Rationale |
|------|---------------|-----------|
| P-1 | **Use three-zone sidebar layout**: Fixed SGF input + buttons (top), scrollable pipeline stepper + config accordion (middle), fixed run-info (bottom). | Keeps primary actions always visible. Config and progress scroll together naturally. Matches Grafana pattern (E-21). |
| P-2 | **Replace horizontal pill bar with vertical stepper in the scrolling zone.** Use GitHub Actions–style connected dots (E-2). Remove `<header id="pipeline-bar">` entirely. | Saves 40px vertical space. Stage progress lives next to config in the sidebar — a unified "pipeline control" zone. 10 stages ≈ 220px, compact enough. |
| P-3 | **Continue with hand-written CSS + custom properties.** Extend existing `:root` vars (add `--bg-hover`, `--accent-dim`). Do NOT add Tailwind or framework. | Zero build-step change. Consistent with existing codebase. Developer tool doesn't need utility-class rapid iteration. Hand-written gives full control over dark-theme slider/toggle styling. |
| P-4 | **For constrained difficulty weights (sum=100), use Approach B (remainder counter + normalize button)** for MVP, with visual warning when sum ≠ 100. Upgrade to proportional redistribution (Approach A) in a later iteration if users request it. | Approach B is ~15 lines of JS. Approach A is ~40 lines. The normalize button is clearer (user intent explicit) and simpler to implement. |
| P-5 | **Cap accordion nesting at 1 level.** 7 groups is the right granularity. Only 1 expanded at a time (auto-collapse siblings) to prevent scroll explosion. Start all collapsed by default. | 7 collapsed group headers ≈ 196px. One expanded group ≈ 120-250px depending on param count. Total scroll ≈ 416-646px including stepper. Well within a scrollable sidebar. |
| P-6 | **Implement slider+number dual input for all range parameters.** The slider sets the rough value; clicking the value span converts it to an editable `<input type="number">` for precision. | Standard developer tool pattern (E-12 Grafana). Solves the "180px track width isn't precise enough" problem without extra screen space. |

---

## 7. Confidence & Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 90 |
| `post_research_risk_level` | low |

**Justification**: All 6 research questions answered with both internal and external evidence. The recommended patterns are established (GitHub Actions stepper, Grafana accordion, standard CSS slider/toggle styling) and well-suited to the 180-260px dark-theme sidebar constraint. The main uncertainty is whether the three-zone layout needs adjustment once real content is placed — but the existing `overflow-y: auto` on the sidebar handles this gracefully.

---

## Internal References

| R-ID | Artifact | Relevance |
|------|----------|-----------|
| IR-1 | `tools/puzzle-enrichment-lab/gui/css/styles.css` | Current CSS variables, layout grid, existing widget styles (W-1 to W-6) |
| IR-2 | `tools/puzzle-enrichment-lab/gui/src/pipeline-bar.js` | Current 10-stage pill implementation to be replaced |
| IR-3 | `tools/puzzle-enrichment-lab/gui/src/sgf-input.js` | Sidebar content structure (textarea, buttons, state bindings) |
| IR-4 | `tools/puzzle-enrichment-lab/gui/src/state.js` | Observable atom pattern for state management |
| IR-5 | `tools/puzzle-enrichment-lab/gui/src/log-panel.js` | Existing collapsible/drag-resize panel pattern |
| IR-6 | `tools/puzzle-enrichment-lab/gui/index.html` | HTML structure: 3-column grid, besogo library, ES module imports |
| IR-7 | `TODO/initiatives/20260314-feature-enrichment-lab-config-panel/15-research.md` | Config parameter catalog (45 params), stage map, bridge API analysis |
| IR-8 | `frontend/package.json` + `frontend/src/styles/app.css` | Tailwind v4 usage in main app (decision input for RQ-6) |

## External References

| R-ID | Source | Relevance |
|------|--------|-----------|
| ER-1 | VS Code Settings UI (built-in) | Grouped/searchable config panel pattern for developer tools (E-7) |
| ER-2 | GitHub Actions workflow visualization | Vertical stepper with connected dots for pipeline progress (E-2) |
| ER-3 | Grafana panel options sidebar | Collapsible sections with left accent border for config grouping (E-9, E-21) |
| ER-4 | KaTrain (github.com/sanderland/katrain) | Go analysis tool with sidebar config. Uses modal dialogs, not inline config. "Calibrated" highlighting pattern useful (E-5) |
| ER-5 | LizGoban (github.com/kaorahi/lizgoban) | Go analysis tool. Config via JSON file. Tsumego frame feature. No sidebar config UI (E-6) |
| ER-6 | Chrome DevTools Elements/Computed panel | Ultra-dense property display in sidebar, collapsible groups (E-8) |
| ER-7 | Portfolio allocation UIs (Betterment/Wealthfront pattern) | Constrained weight redistribution pattern for sum=100 sliders (E-17) |
| ER-8 | CSS `appearance: none` + `::-webkit-slider-thumb` technique | Standard cross-browser approach for custom range sliders in dark themes (E-11, E-12) |
