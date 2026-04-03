# Charter: GP Frame Swap — Replace BFS Frame with GoProblems.com Algorithm

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Type**: Feature
> **Last Updated**: 2026-03-13

---

## Problem Statement

The current BFS-based tsumego frame (`tsumego_frame.py`, ~1130 lines) has grown overly complex through multiple rewrites (V1 → V2 → V3, flood-fill, spine-fill patches). It has accumulated 17 public functions, nested BFS logic, legality guards, and multiple governance-mandated patches. The GoProblems.com-style frame (`tsumego_frame_gp.py`, ~600 lines) is a simpler, proven algorithm ported from KaTrain (MIT, SHA 877684f9) that produces equivalent frame quality with significantly less code complexity.

The user has decided to swap the active frame implementation from BFS to GP, keeping the BFS code archived but inactive, and building a clean adapter/utility layer so the GP module itself stays pure.

## Goals

| ID | Goal | Acceptance Criteria |
|----|------|---------------------|
| G1 | Replace the active frame algorithm with GP | `query_builder.py` calls GP (via adapter) instead of BFS `apply_tsumego_frame` |
| G2 | Extract `compute_regions`/`FrameRegions` into shared utility | New `frame_utils.py` module with pure bbox geometry, importable by any consumer |
| G3 | Add `FrameConfig` dataclass to GP internal config | Structured parameter passing instead of loose keyword args |
| G4 | Build thin adapter layer around GP | Provides `apply_frame()`, `remove_frame()`, `validate_frame()` — same shape as BFS interface |
| G5 | Keep GP code pure (~600 lines) | No validation logic, region computation, or removal logic embedded in GP |
| G6 | Remove dead `FrameRegions` import from `liberty.py` | Clean import, no dead code |
| G7 | Skip BFS tests, add GP adapter tests | `test_tsumego_frame.py` gets `pytest.mark.skip`, new tests cover adapter |
| G8 | Fix `test_frames_gp.py` broken import | `analyzers.frames_gp` → `analyzers.tsumego_frame_gp` |

## Non-Goals

| ID | Non-Goal |
|----|----------|
| NG1 | Deleting the BFS code (`tsumego_frame.py`) — kept for reference |
| NG2 | Modifying the GP algorithm internals (KaTrain port stays faithful) |
| NG3 | Changes to KataGo engine, SGF parser, or other analyzers beyond wiring |
| NG4 | Frontend changes |
| NG5 | Performance benchmarking (GP is known to be simpler, not slower) |

## Constraints

| ID | Constraint |
|----|-----------|
| C1 | GP module purity — no validation/utility logic embedded in GP |
| C2 | `player_to_move` must be preserved through framing (inviolate rule) |
| C3 | Adapter must provide same return shape so `query_builder.py` and `enrich_single.py` work without cascading changes |
| C4 | `compute_regions` output (`puzzle_region: frozenset[tuple[int,int]]`) must remain compatible with `solve_position.py` Benson/interior-point gates |
| C5 | BFS code kept, tests skipped — enables rollback if GP proves insufficient |
| C6 | `tools/` isolation rule — no imports from `backend/` |

## Scope Summary

| Area | Files Affected |
|------|---------------|
| New utility module | `analyzers/frame_utils.py` (new) |
| New adapter module | `analyzers/frame_adapter.py` (new) |
| GP config addition | `analyzers/tsumego_frame_gp.py` (add `FrameConfig` dataclass) |
| Rewire consumers | `analyzers/query_builder.py`, `analyzers/enrich_single.py` |
| Script simplification | `scripts/show_frame.py` |
| Dead import cleanup | `analyzers/liberty.py` |
| Test skip | `tests/test_tsumego_frame.py` |
| Test fix | `tests/test_frames_gp.py` |
| New tests | `tests/test_frame_adapter.py` (new), `tests/test_frame_utils.py` (new) |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GP produces different frame quality than BFS | Low | Medium | GP is proven (KaTrain/ghostban). Adapter layer + validation utility catches issues |
| `guess_attacker` heuristic loss (GP uses `player_to_move` directly) | Low | Low | In tsumego, `player_to_move` IS the attacker by convention. BFS's `guess_attacker` is a fallback for when PL is absent — we verify PL is always set in our pipeline |
| `defense_area` removal breaks something downstream | Low | Low | Confirmed: no external consumer uses `defense_area` from `FrameRegions` |
| Rollback needed after swap | Low | Low | BFS code preserved, tests can be un-skipped |
