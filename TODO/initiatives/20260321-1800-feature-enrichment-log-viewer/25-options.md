# Options: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Last Updated: 2026-03-21

## Context

Decisions locked by user and clarification round:
- Standalone HTML+JS viewer at `tools/puzzle-enrichment-lab/log-viewer/`
- Chart.js for charting (~60KB CDN)
- Separate files: `index.html` + `app.js` + `styles.css`
- Horizontal swim-lane for pipeline journey
- System-preference dark mode via CSS media query
- Graceful degradation with CTA for missing data
- Sample JSONL included
- Performance target: ~1,000 puzzles

The options below vary on **internal architecture** — how the JS code is organized, how data flows from JSONL parse to rendering, and how sections are composed.

---

## Option OPT-1: Module-Per-Section Architecture

### Approach
Single `app.js` file with clearly namespaced section-rendering functions. Each dashboard section (S1-Metadata, S2-Summary, S3-Timing, S4-Pipeline Journey, S5-Puzzle Details, S6-Search, S7-Reference) is a function that receives parsed data and returns DOM elements.

**Data flow**: `JSONL → parse() → EventStore → renderAll(store) → DOM`

```
log-viewer/
├── index.html          # Shell: drop zone, section containers, CDN links
├── app.js              # All logic: parser, EventStore, section renderers, search
├── styles.css          # All styles including dark mode media query
├── sample.jsonl        # Demo data
└── README.md           # Usage instructions
```

### Benefits
| ID | Benefit |
|----|---------|
| B1.1 | Simplest to understand — single JS file, <800 LOC total |
| B1.2 | Easiest to maintain for occasional contributors |
| B1.3 | No module system needed (plain `<script>` tag) |
| B1.4 | Zero friction deployment — copy 4 files, done |

### Drawbacks
| ID | Drawback |
|----|----------|
| D1.1 | Single JS file may grow large (600-800 LOC) as features accumulate |
| D1.2 | No code reuse across sections (e.g., badge rendering duplicated) |
| D1.3 | Testing requires loading entire app.js (no unit-testable modules) |

### Risks
| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R1.1 | File grows too large over time | Low | Split into modules later if needed |
| R1.2 | Chart.js CDN unavailable offline | Low | Add vendored fallback option in README |

### Complexity: **Low** (~3-4 person-days)
### Test Impact: Manual browser testing only. No automated test infrastructure needed.
### Rollback: Delete the `log-viewer/` directory.

---

## Option OPT-2: ES Module Architecture

### Approach
Split JS into ES modules using native `import`/`export` (no bundler). Each section is its own module. A shared `utils.js` provides common functions (badge rendering, formatting, escaping).

**Data flow**: `JSONL → parser.js → EventStore → main.js orchestrates → section modules render → DOM`

```
log-viewer/
├── index.html          # Shell with <script type="module" src="main.js">
├── main.js             # Orchestrator: drop zone, parse, delegate to sections
├── parser.js           # JSONL parser + EventStore class
├── sections/
│   ├── metadata.js     # S1: Run metadata
│   ├── summary.js      # S2: Aggregate statistics + charts
│   ├── timing.js       # S3: Phase timing charts (Chart.js stacked bar)
│   ├── pipeline.js     # S4: Pipeline journey swim-lane (SVG/Canvas)
│   ├── puzzles.js      # S5: Puzzle details (collapsible, lazy-rendered)
│   ├── search.js       # S6: Full-text search
│   └── reference.js    # S7: Glossary with hyperlinks
├── utils.js            # Shared: badge(), escapeHtml(), formatDuration(), tierDescription()
├── styles.css          # Styles + dark mode
├── sample.jsonl        # Demo data
└── README.md           # Usage
```

### Benefits
| ID | Benefit |
|----|---------|
| B2.1 | Clean separation of concerns — each section independently maintainable |
| B2.2 | Shared utilities prevent duplication (badge, escape, format) |
| B2.3 | Individual modules are unit-testable with a JS test runner |
| B2.4 | Native ES modules — no bundler, but tree-shaking possible if bundled later |
| B2.5 | New sections can be added without touching existing code |

### Drawbacks
| ID | Drawback |
|----|----------|
| D2.1 | More files to manage (~12 vs 4) |
| D2.2 | ES modules require `http://` or local server — `file://` protocol may block (CORS) |
| D2.3 | Slightly higher complexity for first-time contributors |

### Risks
| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R2.1 | `file://` CORS blocks ES module imports | Medium | README: use `python -m http.server` or `npx serve`. Alternatively, add a build script that bundles into single file |
| R2.2 | Module resolution edge cases on Windows | Low | Use relative paths consistently |

### Complexity: **Medium** (~4-5 person-days)
### Test Impact: Modules are individually unit-testable. Can add a simple test HTML page.
### Rollback: Delete the `log-viewer/` directory.

---

## Option OPT-3: Single HTML + Inline Modules (Hybrid)

### Approach
Single `index.html` with all CSS and JS inline (like the current Python `generator.py` output), but internally organized as IIFE (Immediately Invoked Function Expression) modules within `<script>` tags. Chart.js loaded via CDN `<script>` tag.

**Data flow**: `JSONL → LogParser IIFE → EventStore → Dashboard IIFE renders sections → DOM`

```
log-viewer/
├── index.html          # Everything: CSS <style>, JS <script> blocks, HTML structure
├── sample.jsonl        # Demo data
└── README.md           # Usage
```

### Benefits
| ID | Benefit |
|----|---------|
| B3.1 | True single-file distribution — works with `file://` protocol, no CORS issues |
| B3.2 | No module system, no bundler, no server needed |
| B3.3 | Easy to email/share a single HTML file |
| B3.4 | Consistent with how the Python report generator works |

### Drawbacks
| ID | Drawback |
|----|----------|
| D3.1 | Single file becomes very large (1500+ LOC) — hard to navigate |
| D3.2 | No code reuse — utility functions scattered across IIFEs |
| D3.3 | Harder to maintain: CSS + JS + HTML in one file |
| D3.4 | No testability — everything is tightly coupled |
| D3.5 | Editing requires finding the right `<script>` block |

### Risks
| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R3.1 | Maintenance burden grows quickly as features are added | Medium | Can refactor to OPT-1 or OPT-2 later |
| R3.2 | Contributors confused by monolithic file | Low | Good internal comments and section markers |

### Complexity: **Low-Medium** (~3-4 person-days)
### Test Impact: Manual testing only. No unit test capability.
### Rollback: Delete the `log-viewer/` directory.

---

## Comparison Matrix

| Criterion | OPT-1 (Module-Per-Section) | OPT-2 (ES Modules) | OPT-3 (Single HTML) |
|-----------|---------------------------|--------------------|--------------------|
| File count | 4 files | ~12 files | 2 files |
| `file://` works | ✅ Yes | ❌ Needs local server | ✅ Yes |
| Maintainability | Medium | High | Low |
| Testability | Low | High | None |
| Contributor friction | Low | Medium | Low (but hard to navigate) |
| Bundle size | ~60KB (CDN) | ~60KB (CDN) | ~60KB (CDN) + inline code |
| Future extensibility | Medium | High | Low |
| YAGNI compliance | ✅ Best | Moderate | ✅ Good |

## Recommendation

**OPT-1 (Module-Per-Section)** is recommended as the best balance of:
- **Simplicity** (KISS/YAGNI — 4 files, single JS file, no module system)
- **`file://` compatibility** (critical for zero-friction dev experience)
- **Adequate maintainability** (600-800 LOC in `app.js` is manageable with good section comments)
- **Upgrade path** (can be refactored to OPT-2 if it outgrows single-file)

OPT-2 is better architecturally but the `file://` CORS restriction is a real friction point that contradicts the "just open index.html" requirement. OPT-3 is too monolithic for the feature scope.

> **Governance**: This recommendation requires election by the Governance Panel.
