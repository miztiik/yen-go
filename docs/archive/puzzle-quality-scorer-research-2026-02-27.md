# Puzzle Quality Scorer Research (2026-02-27)

> ⚠️ **ARCHIVED** — This document preserves the historical symbolic quality-scorer research bundle that originally lived under `TODO/puzzle-quality-scorer/`.
> Current canonical documentation: [KataGo Enrichment Architecture](../architecture/tools/katago-enrichment.md), [Quality Metrics](../concepts/quality.md), [Enrichment Confidence Scores](../concepts/enrichment-confidence-scores.md)
> Archived: 2026-05-07

**Last Updated**: 2026-05-07

## Scope

This digest replaces the historical TODO planning bundle:

- `README.md`
- `implementation-plan.md`
- `reference/gogogo-tactics.md`
- `reference/gogogo-instincts.md`
- `reference/gogamev4-territory.md`
- `reference/gogamev4-analysis.md`

It described a proposed **symbolic puzzle quality scorer**: a CPU-only tactical-analysis layer meant to run before or alongside KataGo enrichment.

## Historical Summary

### Proposal

The bundle proposed a new `core/tactical_analyzer.py` module that would provide pure board-state analysis for:

- ladder detection
- snapback detection
- capture verification
- life/death evaluation
- eye counting and group-status assessment
- weak-group and seki detection
- instinct-pattern recognition
- tactical-complexity scoring

The intended uses were:

- auto-tagging techniques
- validating that a puzzle objective matches the position
- feeding better signals into difficulty classification
- generating richer hints when no AI engine is available

### Source Research Basis

The bundle extracted algorithm ideas from two external projects under clean-room constraints:

- `PLNech/gogogo` for symbolic tactics and instinct-pattern detection
- `zhoumeng-creater/gogamev4.0` for eye counting, weak-group analysis, territory, and mistake-threshold reasoning

The historical notes correctly distinguished between extracting algorithms/patterns and copying code verbatim, especially because one of the upstream sources was GPL-3.0.

## What Became Canonical Elsewhere

### 1. The Architecture Decision to Run Symbolic Scoring Before KataGo

The most durable part of the bundle is already represented in current docs.

In [KataGo Enrichment Architecture](../architecture/tools/katago-enrichment.md), D11 records the historical relationship:

- the symbolic Quality Scorer runs first
- KataGo enrichment runs second
- KataGo wins when the two disagree

That decision is the canonical architectural descendant of this research bundle.

### 2. Instinct Vocabulary and Signal Evolution

The scorer research pulled instinct-pattern ideas from GoGoGo. The current docs already carry the surviving vocabulary and signal framing in:

- [Enrichment Confidence Scores](../concepts/enrichment-confidence-scores.md)
- [KataGo Enrichment Architecture](../architecture/tools/katago-enrichment.md)

### 3. Quality and Complexity Outputs

The bundle's intended downstream outputs now map to the active metric docs:

- [Quality Metrics](../concepts/quality.md)

The current docs, however, describe the published YQ/YX contract and enrichment-lab fields, not the original symbolic-only implementation proposal.

## Historical Findings Worth Preserving

### 1. Symbolic Tactics Were Treated as a Fast First Pass

The proposal explicitly positioned symbolic analysis as a low-latency structural layer that could handle many puzzles cheaply and act as fallback protection when KataGo was unavailable.

That is important historical context for D11 in the current architecture doc.

### 2. The Bundle Identified Concrete Algorithm Families

The research did more than say "use tactics" in the abstract. It preserved clean-room summaries for:

- ladder tracing
- snapback recognition
- eye validation and real-eye detection
- weak-group classification by liberties and escape potential
- instinct-pattern matching
- mistake severity thresholds from evaluation deltas

Those ideas remain useful historical references, but the current repo should treat them as archived research, not as live implementation guarantees.

### 3. The Bundle Also Framed Puzzle Validation as a Quality Problem

One important historical insight was that puzzle quality was not just about refutation count or comments. The scorer proposal argued that some puzzles should be downgraded or flagged when the board state contradicted the supposed objective.

That concept is still valuable context even though the original `core/tactical_analyzer.py` module was not preserved as a canonical current contract.

## What Stayed Historical Instead of Becoming Canonical

The following parts remained archived rather than promoted as current docs:

- the exact `core/tactical_analyzer.py` module proposal and phase plan
- the proposed `TacticalAnalysis` dataclass shape
- the full symbolic position-validation flow
- the direct roadmap to replace the difficulty classifier using tactical signals
- the detailed per-source algorithm extraction notes as standalone docs

Those materials are historical research input, not the current implementation contract.

## Retirement Note

The `TODO/puzzle-quality-scorer/` directory was removed after this digest was created. Current engineering guidance should come from the canonical docs linked above, with this file retained only for historical traceability.
