# Puzzle Quality Strategy (2026-02-25)

> ⚠️ **ARCHIVED** — This document preserves the historical puzzle-quality planning bundle that originally lived under `TODO/puzzle-quality-strategy/`.
> Current canonical documentation: [Quality Metrics](../concepts/quality.md), [SQLite Index Architecture](../concepts/sqlite-index-architecture.md), [Dedup Hashing](../concepts/dedup-hashing.md), [View Index Schema](../reference/view-index-schema.md), [KataGo Enrichment Architecture](../architecture/tools/katago-enrichment.md)
> Archived: 2026-05-07

**Last Updated**: 2026-05-07

## Scope

This digest replaces the historical TODO planning bundle:

- `README.md`
- `001-research-quality-landscape.md`
- `002-implementation-plan-strategy-d.md`
- `003-d2-classifier-research.md`

The original bundle evaluated how YenGo should handle quality control across a ~194K puzzle corpus, choose a quality-control strategy, and defer deeper classifier work into a separate research lane.

## Historical Summary

### Strategy Choice

The bundle selected **Strategy D (Hybrid)** as the preferred direction for puzzle quality control.

Its three planned phases were:

1. Position fingerprinting, cross-source dedup, trivial-capture detection, and config-driven quality scoring.
2. Content-type classification with `curated`, `practice`, and `training` buckets.
3. Frontend quality-tier UX layered on top of the backend classification model.

### Deferred or Follow-On Work

The bundle explicitly deferred:

- quality-weighted daily challenge selection
- difficulty classifier replacement / recalibration
- dedup metadata merging across duplicate sources
- a dedicated training-only UI tab

The D2 classifier work was then broken out into a separate research note that audited the limitations of `core/classifier.py` and proposed a calibration path based on collection `level_hint` data.

## What Became Canonical Elsewhere

The durable technical decisions from the strategy bundle are no longer TODO-only knowledge.

### 1. Content-Type Model

The historical plan proposed a 3-value content-type model:

- `1 = curated`
- `2 = practice`
- `3 = training`

That model is now reflected in the current docs:

- [SQLite Index Architecture](../concepts/sqlite-index-architecture.md)
- [View Index Schema](../reference/view-index-schema.md)

### 2. Fingerprint and Dedup Design

The original plan tied quality control to position fingerprinting and cross-source dedup. The active documentation for dedup and fingerprint semantics now lives in:

- [Dedup Hashing](../concepts/dedup-hashing.md)
- [Collection Editions](../concepts/collection-editions.md)
- [SQLite Index Architecture](../concepts/sqlite-index-architecture.md)

### 3. Quality Metrics and Enrichment Signals

The planning bundle's quality-scoring concerns now map to:

- [Quality Metrics](../concepts/quality.md)
- [KataGo Enrichment Architecture](../architecture/tools/katago-enrichment.md)

Those current docs supersede the old planning narrative for how quality and complexity signals are represented in published SGF and downstream indexes.

## Historical Findings Worth Preserving

### 1. The Original Problem Statement Was Corpus Quality, Not Just AI Enrichment

The strategy bundle framed quality as a broader corpus-management problem:

- some sources were already pipeline-ready
- some needed enrichment only
- some needed conversion or structural cleanup
- some "puzzles" were actually training material or trivial drills

That framing is still useful historical context for why YenGo ended up with content-type fields, dedup design, and richer quality metadata.

### 2. The Classifier Was Recognized Early as a Placeholder

The D2 research explicitly documented that `core/classifier.py` was heuristic, additive, and bug-prone, including:

- incorrect solution-depth traversal
- unreachable upper difficulty levels from the score mapping
- no technique-aware or liberty-aware features

That note remains useful as historical rationale for later enrichment and calibration work, but it should not be treated as the current design contract.

### 3. The Bundle Was a Planning Artifact, Not a Final Architecture Contract

The quality-strategy documents mixed:

- source-inventory research
- architecture decisions
- implementation sequencing
- deferred work lists

Those functions are now split across current docs and this archive record, which is why the old TODO bundle can be retired safely.

## What Stayed Historical Instead of Becoming Canonical

The following items were planning-specific and remain archived rather than promoted to current docs:

- the original three-phase delivery schedule and effort estimates
- the exact strategy-comparison matrix across candidate strategies A-E
- source-inventory counts captured at the February 2026 snapshot
- the deferred D1-D4 backlog framing as a single quality program

## Retirement Note

The `TODO/puzzle-quality-strategy/` directory was removed after this digest was created. Current engineering guidance should come from the canonical docs linked above, not from the historical strategy plan.
