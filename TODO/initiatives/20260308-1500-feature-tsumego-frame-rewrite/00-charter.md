# Charter: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Type**: Feature (complete rewrite)  
> **Last Updated**: 2026-03-08

---

## Goals

| ID  | Goal                                                                                                                                      |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | Replace `analyzers/tsumego_frame.py` with a correct, research-backed implementation combining the best of KaTrain and ghostban algorithms |
| G2  | Fix the 15 known bugs/concerns in V1 (attacker inference, 50% density, defense-colored wall, no normalization, no ko threats, etc.)       |
| G3  | Produce a modular, well-typed single-file design with small functions and structured payloads — portable to JS/TS in the future           |
| G4  | Wire the new capabilities into `query_builder.py` so `ko_type` flows into the frame builder                                               |
| G5  | Full test coverage for the rewritten module and updated integration tests                                                                 |

## Non-Goals

| ID  | Non-Goal                                                                    |
| --- | --------------------------------------------------------------------------- |
| NG1 | Actually porting to JS/TS/WASM (future work, not this initiative)           |
| NG2 | Building a GUI for tsumego frame visualization                              |
| NG3 | Backward compatibility with V1's API shape beyond the entry-point signature |
| NG4 | KataGo model selection or engine changes                                    |
| NG5 | Changes to the SGF parser, difficulty estimator, or any other analyzer      |

## Constraints

| ID  | Constraint                                                                                  |
| --- | ------------------------------------------------------------------------------------------- |
| C1  | Single file: `analyzers/tsumego_frame.py` — no new package directory                        |
| C2  | Python snake_case throughout; function decomposition with typed dataclass/Pydantic payloads |
| C3  | Must use existing `models/position.py` types (Position, Stone, Color)                       |
| C4  | Entry point must remain `apply_tsumego_frame(position, ...)` for caller compatibility       |
| C5  | `remove_tsumego_frame()` must remain (even if trivial) — callers depend on it               |
| C6  | Ko threats module is optional (activated when `ko_type` is not `"none"`)                    |
| C7  | `offence_to_win` is configurable with default 10                                            |
| C8  | No backward compatibility — old V1 code is deleted entirely                                 |
| C9  | Tools must NOT import from `backend/` (architecture rule)                                   |
| C10 | No new external dependencies (use stdlib + existing deps only)                              |

## Acceptance Criteria

| ID   | Criterion                                                                            | Verification                                                                |
| ---- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| AC1  | Attacker color correctly inferred using edge-proximity heuristic (`guess_attacker`)  | Unit test: "Black to play, Black near edge → Black defends → White attacks" |
| AC2  | Fill density ~65-75% of frameable area (count-based half/half, not 50% checkerboard) | Unit test: measure density on 19×19 corner, edge, center puzzles            |
| AC3  | Wall is ATTACKER color (not defender)                                                | Unit test: wall stones adjacent to puzzle region are attacker color         |
| AC4  | Border placed only on non-board-edge sides of puzzle region                          | Unit test: TL corner → border on right+bottom only, not top/left            |
| AC5  | Full normalize→frame→denormalize for consistent framing                              | Unit test: TL and BR corner positions produce equivalent frame quality      |
| AC6  | Ko threats placed when `ko_type != "none"`                                           | Unit test: ko puzzle gets 2 extra stone patterns near puzzle                |
| AC7  | `offence_to_win` configurable, default 10                                            | Unit test: different values produce different territory splits              |
| AC8  | `query_builder.py` passes `ko_type` to frame builder                                 | Integration test: ko puzzle query includes ko threats in frame              |
| AC9  | All existing tests updated — no test references V1 internals                         | Test suite passes with 0 failures                                           |
| AC10 | Each function is ≤ ~40 lines, takes/returns typed payload                            | Code review                                                                 |
| AC11 | Documentation updated in `docs/`                                                     | Doc review                                                                  |

## Research Inputs

Prior research from `TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/15-research.md`:

- KaTrain source: MIT, SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed` (verbatim)
- ghostban source: MIT, `https://github.com/goproblems/ghostban` v3.0.0-alpha.155 (verbatim JS)
- Three-way comparison table with 63 research findings (R-1 through R-63)
- Merged algorithm combining best of both sources

> **See also**:
>
> - [Research: goproblems tsumego frame](../2026-03-08-research-goproblems-tsumego-frame/15-research.md) — Verbatim source analysis
> - [Architecture: puzzle-enrichment-lab](../../../docs/architecture/) — Tool isolation rules
