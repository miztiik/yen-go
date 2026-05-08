# Kishimoto-Mueller Search Optimizations (2026-03-04)

> ⚠️ **ARCHIVED** — This document preserves the historical implementation plan and task ledger for the KataGo enrichment lab's Kishimoto-Mueller search-optimization rollout.
> Current canonical documentation: [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md), [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md), [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md)
> Archived: 2026-05-08

**Last Updated**: 2026-05-08

## Scope

This digest replaces the former TODO plan and task tracker for the search-budget optimizations adapted from Kishimoto and Muller (2005) and Thomsen (2000).

The retired bundle combined:

- a design plan with review-panel rationale
- a 7-phase execution sequence
- a detailed task ledger with gate approvals
- benchmark and documentation completion tracking

## Historical Summary

### 1. Problem Statement

The original plan targeted one concrete bottleneck in the enrichment lab: solution-tree building consumed too much `QueryBudget` on opponent branching, transpositions, and trivially forced continuations.

The key thesis was that search-structure improvements could reduce query cost without changing classification outcomes.

### 2. Implemented Optimization Set

The bundle tracked rollout of five linked techniques:

- sibling-branch simulation (KM-01)
- transposition caching (KM-02)
- forced-move fast-path (KM-03)
- proof-depth difficulty signal (KM-04)
- depth-dependent policy thresholding inspired by lambda search (DD-L3)

These are now documented as implemented behavior in the canonical enrichment docs.

### 3. Delivery Model

The historical plan enforced a gated rollout:

1. config and schema extension
2. transposition caching
3. sibling simulation
4. forced-move fast-path
5. proof-depth scoring integration
6. benchmark and documentation closeout

The companion task ledger recorded each phase as complete and marked all review gates approved by 2026-03-24.

## What Became Canonical Elsewhere

### 1. Architecture Decisions

The durable design decisions now live in [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md), including the KM optimization section and the final architecture notes for simulation, transpositions, forced moves, proof-depth weighting, and depth-aware policy pruning.

### 2. Operator-Facing Configuration

The runtime knobs and their intended use are now covered by:

- [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md)
- [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md)

### 3. Remaining Work Tracking

Any still-open enrichment work should be tracked through the docs-native backlog and canonical architecture docs, not through this historical task ledger.

## Historical Decisions Worth Preserving

### 1. Search Over Knowledge Was the Explicit Strategy

The plan deliberately chose to adapt search-control ideas instead of adding more handcrafted tsumego heuristics. That framing is historically important because it shaped the final implementation and benchmark expectations.

### 2. Review-Panel Consultation Was Part of the Design Record

The plan preserved specific review guidance from Go-domain and engineering perspectives. The final canonical docs retain the resulting decisions, but this archive explains why those choices were evaluated together.

### 3. The Task Ledger Was a Governance Artifact, Not the Long-Term Memory

The former tasks file served as execution bookkeeping. Its checklist, gate rows, and baseline counts were useful during rollout but are not the repository's durable knowledge now that the behavior is documented elsewhere.

## What Stayed Historical Instead of Becoming Canonical

The following content remains historical project record rather than current documentation contract:

- the per-phase task numbering and checklist ledger
- benchmark target thresholds and gate-by-gate sign-off language
- the exact execution ordering constraints between user stories
- detailed completion bookkeeping for config, tests, and review gates
- references to the temporary TODO execution bundle itself

## Retirement Note

The original TODO plan and task files were deleted after this digest was created. Use the canonical enrichment docs for current behavior and configuration; use this archive only for historical rollout context.
