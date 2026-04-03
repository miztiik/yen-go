# Charter — Enrichment Lab Config Panel + Sidebar Redesign

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Type**: Feature
**Last Updated**: 2026-03-14

---

## Goals

| G-ID | Goal | Acceptance Criteria |
|------|------|-------------------|
| G-1 | **Expose all 45 enrichment config parameters** in the GUI sidebar with intuitive widgets (sliders, toggles, dropdowns, number inputs) | All 45 params from `EnrichmentConfig` visible, grouped by stage, pre-filled with defaults, editable, and sent as overrides to the pipeline |
| G-2 | **Redesign sidebar layout** — Replace horizontal pipeline pill bar with vertical stage stepper integrated into the sidebar | Pipeline pills removed from header, vertical stepper in sidebar showing stage name/status/timing, header space reclaimed |
| G-3 | **Three-zone sidebar** — Fixed SGF controls (top), scrollable stepper + config (middle), fixed run-info (bottom) | SGF input + action buttons always visible; config sections scroll; run metadata pinned at bottom |
| G-4 | **Bridge API: config override support** — `POST /api/enrich` accepts optional config overrides; `GET /api/config` returns current defaults | Override dict sent from GUI → bridge → `enrich_single_puzzle(config=merged)` |
| G-5 | **Analyze button visits dropdown** — Quick-select visits (200/500/1000/2000/5000) next to Analyze button | Dropdown visible, selection sent to `/api/analyze` as `visits` param |
| G-6 | **Config persistence** — Save GUI config tweaks to localStorage, restore on reload | Config state survives page refresh; reset-to-defaults button available |
| G-7 | **Difficulty weight sliders (sum=100)** — 5 linked weight sliders with remainder counter, normalize button, and fallback to defaults if invalid | Sum counter visible, normalize redistributes proportionally, invalid sum → server uses defaults |
| G-8 | **Per-stage re-run foundation** — Serialize PipelineContext so engine-free stages (Difficulty, Technique, Teaching, SgfWriteback) can be re-run independently | Context serialization/deserialization utility; `from_stage` field on enrich request; re-run triggers in GUI stepper |

## Non-Goals

| NG-ID | Exclusion | Rationale |
|-------|-----------|-----------|
| NG-1 | Engine-dependent per-stage re-run (Analyze, Refutations, SolvePath) | Deferred — engine-free re-run gives instant feedback; engine re-run has timeout/restart complexity |
| NG-2 | Config file editing from GUI | Out of scope — GUI overrides are per-request, not persisted to disk config |
| NG-3 | Multi-puzzle batch GUI | This is a single-puzzle tuning tool |
| NG-4 | Adding Tailwind to enrichment lab | FastAPI static serve has no build step; hand-written CSS continues (see research REJ-1) |

## Constraints

| C-ID | Constraint |
|------|-----------|
| C-1 | No build step — GUI is served as static files by FastAPI `StaticFiles`. No Vite, no webpack, no PostCSS. |
| C-2 | Hand-written CSS with CSS custom properties. Must match existing dark theme (`--bg`, `--bg-panel`, `--accent`, etc.). |
| C-3 | All config parameters must come from `EnrichmentConfig` Pydantic model. No hardcoded values in JS. |
| C-4 | Config overrides validated by Pydantic (server-side). Invalid values → 422 error to GUI. |
| C-5 | Breaking changes to `EnrichRequest` API are acceptable (no backward compat required). |
| C-6 | Old code (hardcoded `visits: 200`, pill bar) may be kept or removed — no forced cleanup. |
| C-7 | Must look polished — dark theme developer tool aesthetic (Grafana, VS Code settings, GitHub Actions stepper). |

---

> **See also**:
> - [10-clarifications.md](./10-clarifications.md) — User decisions on all 8 questions
> - [15-research.md](./15-research.md) — 45 config params, stage map, PipelineContext schema
> - [15-research-ux.md](./15-research-ux.md) — Sidebar wireframe, widget CSS, accordion patterns
