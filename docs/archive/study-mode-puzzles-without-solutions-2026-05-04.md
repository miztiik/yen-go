# Study Mode for Puzzles Without Solutions (2026-05-04)

> ⚠️ **ARCHIVED** — This document preserves the historical implementation plan for admitting and rendering puzzles that ship without recorded solution trees.
> Current canonical documentation: [Study Puzzles](../concepts/study-puzzles.md), [Puzzle Solving Architecture](../architecture/frontend/puzzle-solving.md), [SolverView Usage](../how-to/frontend/solver-view.md), [Source Ingest Database](../architecture/backend/source-ingest-db.md)
> Archived: 2026-05-08

**Last Updated**: 2026-05-08

## Scope

This archive replaces the former TODO planning note for "study mode for puzzles without solutions".

The original plan addressed a concrete product gap: some SGF collections contain real pedagogical positions with setup stones but no answer tree. Rejecting them at ingest loses useful material, while rendering them as ordinary solve puzzles causes every click to register as wrong.

## Historical Summary

### 1. Problem Framing

The plan established that the backend was already structurally capable of accepting these positions once the validator gate allowed `min_solution_depth = 0`.

The real UX problem lived in the frontend: the normal solving path assumes a non-empty move tree and funnels user moves through solution verification.

### 2. Selected Design

The plan chose a schema-free frontend discriminator instead of adding a new SGF property.

The selected direction was:

- detect study positions from move-tree shape after parsing
- attach a frontend `mode: 'solve' | 'study'` field
- export one canonical `isStudyMode(puzzle)` predicate
- keep the verifier contract pure and dispatch study behavior at the call site
- reuse `SolverView` rather than creating a dedicated page or route

### 3. Intended User Experience

The planned study-mode experience was:

- board interaction remains enabled
- clicks place stones for free exploration instead of wrong-answer feedback
- no success/failure transitions, red/green overlays, or solve completion card
- the UI clearly signals that the position has no recorded solution
- study interaction should remain distinct from ordinary solve statistics

### 4. Explicit Non-Goals

The planning note explicitly rejected several scope expansions:

- no new route or separate study page
- no AI-generated solutions in this change
- no annotation system for study positions
- no change to the meaning of completion for ordinary solvable puzzles

## What Became Canonical Elsewhere

### 1. Cross-Cutting Product Concept

The current source of truth for what a study puzzle is, how it enters the pipeline, and how the frontend recognises it is [Study Puzzles](../concepts/study-puzzles.md).

### 2. Frontend Behavior

The broader move-validation architecture belongs in [Puzzle Solving Architecture](../architecture/frontend/puzzle-solving.md), with component-level usage details in [SolverView Usage](../how-to/frontend/solver-view.md).

### 3. Backend Ingest Context

The ingest-state and skip-reason history that motivated part of the original analysis remains covered by [Source Ingest Database](../architecture/backend/source-ingest-db.md).

## Historical Decisions Worth Preserving

### 1. Runtime Detection Beat Schema Expansion

One of the plan's most durable design choices was to avoid a new SGF property and instead treat "no solution tree" as a structural frontend fact. That kept the implementation lightweight and avoided a schema bump.

### 2. Verifier Purity Was Treated as a Hard Boundary

The plan explicitly preserved the solution verifier as a solve-path service rather than overloading it with a neutral study-mode return path. That boundary is useful historical rationale for future maintenance.

### 3. Study Was Deliberately Kept Separate from Solve Metrics

The plan treated study engagement as conceptually distinct from solving. Even where later implementation details evolve, that product distinction remains useful context.

## What Stayed Historical Instead of Becoming Canonical

The following parts remain archived planning context rather than current documentation contract:

- the task-by-task execution checklist and validation commands
- the correction-level discussion and governance-panel RC references
- the exact implementation sequencing for frontend tasks
- the alternative design table comparing SGF-property tagging versus runtime detection
- open questions about later AI hints or richer study analytics

## Retirement Note

The original TODO planning file was deleted after this archive digest was created. Durable behavior should now be understood through the canonical docs linked above, not through the historical plan.
