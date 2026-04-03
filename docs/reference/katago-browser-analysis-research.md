# Browser Analysis Research: KataGo/Estimator Feasibility

Last Updated: 2026-02-17

## Scope

This research summarizes what is feasible for live Go puzzle analysis in browser-only mode, based on:

- External signals from KataGo training network distribution and GoProblems runtime behavior.
- Existing Yen-Go architecture constraints.
- Review of Feature 134 draft artifacts in `TODO/134-score-estimation-wasm/`.

## Executive Summary

- Browsers can run Go analysis engines or estimators, but this is workload- and device-dependent.
- A full GoProblems-like, deep, responsive analysis experience for all devices is not reliable in pure client mode.


## Findings From Feature 134 Files

### `TODO/134-score-estimation-wasm/analyze_wasm.py`

- Useful as a local binary introspection script (exports, sections).
- Not integrated into frontend contract validation (no expected export list/version checks).
- Hardcoded filename (`OGSScoreEstimator.wasm`) can drift from versioned asset naming used elsewhere.

### `TODO/134-score-estimation-wasm/plan.md`

- Proposes browser Monte Carlo ownership/score estimation with optional worker offloading.
- Assumes paths/components that appear stale relative to current frontend structure.
- Worker marked optional, but runtime-heavy computation without worker risks UI blocking.

### `TODO/134-score-estimation-wasm/spec.md`

- Strong user value proposition (heatmap, score lead, off-path exploration).
- Contains unresolved placeholders and duplicated success criteria blocks.
- FRs and stories imply runtime analysis behavior that conflicts with current architecture rules.

### `TODO/134-score-estimation-wasm/tasks.md`

- Good phased intent, but has structural inconsistencies:
  - Task file references a non-existent location.
  - Uses component paths likely not present in current codebase.
  - Reuses task IDs (`T013`/`T014`/`T015`) across phases.

## Feasibility: What Is Possible / Not Possible / Limitations

## Possible

- Add analysis UI shell state (toggle, panel, placeholders) with no runtime AI compute.
- Display precomputed static guidance (ownership-like hints, lead snapshots) generated in pipeline.
- Support deterministic review/autoplay from solution trees and precomputed branches.

## Not Possible (Under Current Constraints)

- Runtime Monte Carlo/KataGo-like inference in browser for live arbitrary positions.
- Deep off-path exploratory engine analysis entirely in client at GoProblems-like parity.
- Guaranteeing equal latency and depth across low/mid/high-end devices.

## Limitations (Even If Browser Compute Is Allowed)

- Hardware variability: CPU/GPU, thermal throttling, memory pressure.
- Browser variability: WebAssembly threads/SIMD/WebGPU availability.
- Startup cost: downloading engine + network artifacts and warming runtime.
- UX tradeoff: deeper analysis increases wait time and battery drain.

## Can Browsers Really “Play”

- Yes, technically: browsers can execute compiled WASM engines/estimators and produce move/ownership outputs.
- No, not universally at target depth/performance: practical experience varies substantially by device/browser.
- For production puzzle UX, browser-only live analysis usually requires aggressive fallback policies and quality-tiering.

## Fit Against Yen-Go Constraints

Current constraints in `CLAUDE.md`, `.github/copilot-instructions.md`, and `frontend/CLAUDE.md` prioritize:

- Zero runtime backend
- Local-first persistence

Given those rules, the compliant direction is precomputed/static analysis data, not runtime engine inference.

## Recommended Decision Gates

1. Decide if user goal is pedagogical guidance (static/precomputed) or free-form engine exploration.
2. Set explicit performance budget targets by device class.
3. Define fallback policy for unsupported/slow environments.

## See Also

> **See also**:
>
> - [Architecture: System Overview](../architecture/system-overview.md) — Core runtime constraints and platform boundaries
> - [Reference: Go Board JS Libraries Analysis](./go-board-js-libraries-analysis.md) — Existing library research baseline
> - [How-To: Backend CLI Reference](../how-to/backend/cli-reference.md) — Pipeline entrypoints for precompute workflows
