# Charter — Enrichment Lab Visual Pipeline Observer

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Last Updated:** 2026-03-07

---

## Vision

An interactive GUI for the KataGo puzzle enrichment lab (`tools/puzzle-enrichment-lab/`) built by cloning upstream `Sir-Teo/web-katrain` and replacing the in-browser TF.js engine with a Python bridge to the enrichment lab's KataGo subprocess. Lets the developer **visually observe and interact with** each step of the enrichment pipeline — seeing the Go board with web-katrain-quality visuals, the solution/refutation tree being built, and KataGo analysis outputs in real time.

## Goals

| ID  | Goal                                                                                                                                      |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | Visualize the 9-step enrichment pipeline progression in real time with a rich stage bar at the top of the UI                              |
| G2  | Show the Go board with interactive play, ownership heatmap, eval dots, PV overlay, and candidate move visualization (web-katrain quality) |
| G3  | Provide clickable, navigatable solution/refutation tree showing tree construction in progress                                             |
| G4  | Support SGF input via CLI flag AND browser paste/upload                                                                                   |
| G5  | Serve as a debug/observation mode — the enrichment engine must work identically without the GUI                                           |
| G6  | Reuse proven components (yen-go-sensei / web-katrain port) to avoid refactoring later                                                     |

## Non-Goals

| ID  | Non-Goal                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------- |
| NG1 | Full web-katrain feature parity in AI-vs-player mode (AI play, selfplay — these exist as dormant UI but are not the focus) |
| NG2 | Production/public deployment — this is a developer tool                                                                    |
| NG3 | Integration with `backend/puzzle_manager/` — stays isolated in `tools/`                                                    |
| NG4 | Batch queue UI — single-puzzle observation (if it works for 1, works for N)                                                |
| NG5 | Replacing or modifying the existing CLI interface                                                                          |

## Constraints

| ID  | Constraint                                                                               |
| --- | ---------------------------------------------------------------------------------------- |
| C1  | Must NOT import from `backend/puzzle_manager/`                                           |
| C2  | Must live inside `tools/puzzle-enrichment-lab/` in a subdirectory                        |
| C3  | Enrichment pipeline must function identically with GUI disabled (toggle/feature pattern) |
| C4  | No changes to existing CLI arguments (additive only)                                     |
| C5  | Must not require refactoring later — interactive play + full visuals from day one        |
| C6  | Single-user developer tool — no concurrent session handling required                     |
| C7  | Must NOT modify the yen-go-sensei source at `tools/yen-go-sensei/` — GUI is a fork/copy  |

## Acceptance Criteria

| ID  | Criterion                                                                                           |
| --- | --------------------------------------------------------------------------------------------------- |
| AC1 | User can run `python cli.py enrich --sgf puzzle.sgf --gui` and see the enrichment pipeline visually |
| AC2 | Pipeline stage progression is shown in a rich horizontal bar at the top                             |
| AC3 | Go board updates at key pipeline moments (parse, post-frame, post-refutation, final)                |
| AC4 | Ownership heatmap is rendered on the board                                                          |
| AC5 | Solution/refutation tree is clickable and navigatable                                               |
| AC6 | User can paste/upload SGF in the browser for ad-hoc analysis                                        |
| AC7 | Running `python cli.py enrich --sgf puzzle.sgf` (without `--gui`) works exactly as before           |
| AC8 | All existing tests continue to pass without modification                                            |

## Key Design Decisions

All design decisions are documented in the **Architecture Decision Record**:

| ADR Decision | Summary                                                                          |
| ------------ | -------------------------------------------------------------------------------- |
| D1           | Source: clone from upstream Sir-Teo/web-katrain (not from yen-go-sensei)         |
| D2           | CLI/GUI complete isolation — `rm -rf gui/` has zero impact on CLI                |
| D3           | Engine swap: replace TF.js Web Worker with Python bridge-client                  |
| D4           | Dual-purpose bridge: `/api/analyze` (interactive) + `/api/enrich` (pipeline SSE) |
| D5           | Pipeline hook: async callback `progress_cb` (default None = zero overhead)       |
| D6           | SSE via manual StreamingResponse (zero new Python deps)                          |
| D7           | Unused web-katrain features stay dormant (not stripped)                          |
| D8           | PipelineStageBar.tsx — new enrichment-specific component                         |
| D9           | MoveTree correctness coloring (green/red/orange)                                 |
| D10          | Vite dev server with FastAPI proxy                                               |

> **See also:**
>
> - [ADR](./50-adr-gui-design-decisions.md) — Full decision record with rationale
> - [Clarifications](./10-clarifications.md) — User Q&A
> - [Plan](./31-plan-revised.md) — Architecture and implementation
> - [Tasks](./41-tasks-revised.md) — Task breakdown
> - [Governance](./70-governance-decisions.md) — Panel decisions
