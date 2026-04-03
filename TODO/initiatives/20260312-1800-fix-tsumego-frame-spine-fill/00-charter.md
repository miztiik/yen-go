# Charter: Tsumego Frame Spine Fill (V3.2)

**Last Updated**: 2026-03-12

## Problem
V3.1 BFS flood-fill with checkerboard holes produces:
- 10 White + 7 Black disconnected components (target: 1 per color)
- 65% density (target: 35-50%)
- 55 White eyes (target: 2-10 per color)
- Out-of-distribution for KataGo analysis

## Goal
Replace checkerboard skip pattern with connectivity-preserving spine fill that guarantees 1 connected component per color, 35-50% density, and periodic eye-forming gaps.

## Scope
- `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` — core algorithm
- `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py` — test updates

## Non-Goals
- File cleanup/optimization (deferred)
- Documentation updates (deferred to post-validation)

## Governance
Sumeku panel unanimous `change_requested` — RC-1 through RC-8 items approved.
