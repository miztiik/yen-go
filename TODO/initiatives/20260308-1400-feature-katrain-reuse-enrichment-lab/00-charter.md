# Charter: KA Train Reuse Initiative for Puzzle Enrichment Lab

**Initiative ID:** `20260308-1400-feature-katrain-reuse-enrichment-lab`  
**Type:** Feature  
**Last Updated:** 2026-03-08

## Goals

1. Identify 1:1 reusable KA Train non-UI backend functionality and replace equivalent enrichment-lab custom logic.
2. Reduce engineering complexity and maintenance burden by reusing well-established KA Train algorithms where fit is strong.
3. Preserve all required enrichment-lab functional deltas when KA Train coverage is partial.
4. Produce an executor-ready refactor/migration plan with governance-approved task sequencing.

## Non-Goals

1. Importing or depending on KA Train UI/Kivy frontend modules.
2. Migrating whole-game play UX logic into enrichment-lab.
3. Forcing compatibility layers for deprecated enrichment-lab paths.
4. Converting enrichment-lab architecture into a full KA Train clone.

## Constraints

1. `tools/` must remain self-contained and must not import from `backend/puzzle_manager/`.
2. Reuse decisions must respect KA Train MIT license attribution obligations.
3. Replacement is permitted only when functionality match is validated; otherwise preserve delta.
4. Avoid introducing Kivy dependencies into enrichment-lab runtime.
5. Keep solution tsumego-focused even when source logic originates from full-game tooling.

## Acceptance Criteria

1. A reuse matrix exists for all requested areas: frame/border, legal rules validation, strength/ELO leveling relevance, search heuristics, SGF parsing/normalization.
2. Each candidate is classified as exact-match, partial-match, or mismatch with explicit migration recommendation.
3. Selected option includes explicit legacy removal strategy consistent with no-backward-compatibility decision.
4. Task graph includes delta-preservation tasks for partial-match areas before old code deletion.
5. Governance approves selected option and plan with no unresolved blockers.

## Scope Lock

| scope_id | area | in_scope | notes |
|---|---|---|---|
| S1 | KA Train core/ai/engine/rules/utils (non-UI) | Yes | Primary comparison surface |
| S2 | Enrichment lab analyzers/engine/models | Yes | Migration target |
| S3 | KA Train GUI/Kivy components | No | Explicitly excluded by user |
| S4 | Runtime backend integration changes outside `tools/puzzle-enrichment-lab` | No | Out of current initiative |
