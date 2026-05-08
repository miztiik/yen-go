# March 2026 Initiative Decomposition

> ⚠️ **ARCHIVED** — This digest preserves the March 2026 planning workspace after those initiative directories were decomposed and removed from `TODO/initiatives/`.
> Current canonical documentation: [Katago Enrichment Architecture](../architecture/tools/katago-enrichment.md), [Enrichment Lab GUI Architecture](../architecture/tools/enrichment-lab-gui.md), [Hint Architecture](../architecture/backend/hint-architecture.md), [SQLite Index Architecture](../concepts/sqlite-index-architecture.md), [Tsumego Frame](../concepts/tsumego-frame.md)
> Archived: 2026-05-07

**Last Updated**: 2026-05-08

## Scope

- Retirement decision date: 2026-05-07.
- Retired scope: every March 2026 initiative directory and the March-format outliers that still lived under `TODO/initiatives/`.
- Total retired directories: 90.
- Later retired separately: [Browser-Session Bulk Capture Research](browser-session-bulk-capture-research-2026-04-13.md), which was still active when the March retirement was recorded.

The durable engineering knowledge from these initiatives already lives in the canonical documentation tree. This archive document preserves the planning lineage and theme clustering so the old initiative workspace no longer has to function as long-term repository memory.

Source-specific initiative slugs are normalized in this digest when the original slug embedded an upstream site identity.

## Canonical Landing Zones

- Pipeline, publish, and runtime operations: [Pipeline Architecture](../architecture/backend/pipeline.md), [Inventory Operations](../architecture/backend/inventory-operations.md), [Observability](../concepts/observability.md)
- Enrichment engine and KataGo behavior: [Katago Enrichment Architecture](../architecture/tools/katago-enrichment.md), [Katago Enrichment Lab](../how-to/tools/katago-enrichment-lab.md), [Quality](../concepts/quality.md)
- Teaching comments and hints: [Hint Architecture](../architecture/backend/hint-architecture.md), [Hints](../concepts/hints.md), [Tags](../concepts/tags.md)
- Tsumego frame and board integration: [Tsumego Frame](../concepts/tsumego-frame.md), [Goban Integration Architecture](../architecture/frontend/goban-integration.md), [Goban Integration How-To](../how-to/frontend/goban-integration.md)
- Search, collections, and data layout: [SQLite Index Architecture](../concepts/sqlite-index-architecture.md), [Collections](../concepts/collections.md), [Collection Editions](../concepts/collection-editions.md)
- Frontend progress and study flows: [Progress Page](../how-to/frontend/progress-page.md), [Enrichment Lab GUI Architecture](../architecture/tools/enrichment-lab-gui.md)

## Historical Theme Clusters

### 1. Publish, Pipeline, and Backend Operations

These initiatives drove the early-March publish-stage hardening, runtime safety, traceability, and backend cleanup work that is now captured in the canonical pipeline and inventory docs.

- `20260305-0000-feature-publish-incremental-flush`
- `20260305-0000-feature-publish-snapshot-wiring`
- `20260305-0000-feature-remove-dormant-dedup`
- `20260305-0000-feature-sanderland-pass-move`
- `20260306-0000-feature-publish-stage-cleanup`
- `20260310-1400-feature-inventory-reset-safety`
- `20260315-1400-feature-tactical-analysis-wiring`
- `20260315-1500-feature-daily-db-migration`
- `20260319-1000-feature-trace-search-optimization`
- `20260324-1500-feature-backend-dead-code-cleanup`
- `20260324-2000-feature-backend-test-remediation`
- `20260324-research-backend-failing-tests`

### 2. Enrichment Lab GUI and Operator Tooling

This cluster covers the rapid GUI iteration cycle, query fixes, logging scope, Ghostban explorations, operator-facing reports, and config-panel work that eventually converged into the current enrichment-lab GUI architecture.

- `2026-03-06-fix-enrichment-lab-logging-scope`
- `20260307-0000-feature-enrichment-lab-gui`
- `20260307-0000-feature-enrichment-lab-query-fix`
- `20260308-1800-feature-enrichment-lab-ghostban-gui`
- `2026-03-08-research-ghostban-katago-webgl`
- `20260309-1000-feature-enrichment-lab-gui-v4`
- `20260310-feature-enrichment-lab-gui-ux-overhaul`
- `20260311-feature-enrichment-lab-gui-update`
- `20260314-feature-enrichment-lab-config-panel`
- `20260321-1400-feature-html-report-redesign`
- `20260321-1800-feature-enrichment-log-viewer`

### 3. Tsumego Frame and Board Reasoning

These initiatives represent the frame-rewrite sequence: visualization strategy, legality constraints, flood-fill and spine-fill refinements, and the GP frame swap. Their lasting results belong in the frame and goban docs rather than the old planner workspace.

- `20260308-1500-feature-tsumego-frame-rewrite`
- `20260311-1800-feature-tsumego-frame-legality`
- `20260312-1400-feature-tsumego-frame-flood-fill`
- `20260312-1800-fix-tsumego-frame-spine-fill`
- `20260313-1000-feature-gp-frame-swap`

### 4. Teaching Comments, Hints, and Move-Quality Pedagogy

This cluster covers the evolution from teaching-comments overhaul to tactical hints, hint-system comparison, alternative-move annotation, and later LLM-assisted teaching enrichment.

- `20260305-0000-feature-teaching-comments-overhaul`
- `20260306-0000-feature-teaching-comments-v2`
- `20260310-feature-hint-config-dynamic-yh2`
- `20260311-1800-feature-teaching-comments-quality`
- `20260315-1700-feature-enrichment-lab-tactical-hints`
- `20260315-2000-feature-refutation-quality`
- `20260318-research-hinting-system-comparison`
- `20260320-1400-feature-enrichment-almost-correct-reversal`
- `20260321-1000-feature-mark-sibling-refutations`
- `20260326-1400-feature-llm-teaching-enrichment`

### 5. KataGo, KaTrain, and Enrichment-Engine Evolution

These initiatives contain the bulk of the March engine work: no-solution resilience, perspective fixes, KaTrain comparisons, parser-swap research, production hardening, calibration, and technique-registry externalization.

- `20260306-0000-refactor-phase-b-merge`
- `20260307-0000-refactor-enrich-single-decomposition`
- `20260307-0000-refactor-enrichment-no-solution-resilience`
- `20260308-0000-bugfix-katago-perspective`
- `20260308-1400-feature-katrain-reuse-enrichment-lab`
- `20260311-1600-feature-enrichment-lab-consolidation`
- `20260311-fix-config-fail-fast-dead-code`
- `20260313-1400-refactor-enrich-single-srp`
- `20260313-1600-feature-katrain-sgf-parser-swap`
- `20260313-2000-feature-katrain-trap-density-elo-anchor`
- `20260313-research-katrain-config-comparison`
- `20260313-research-score-trap-density-elo-anchor`
- `20260314-1400-feature-enrichment-lab-v2`
- `20260314-research-lizgoban-katrain-patterns`
- `20260317-research-capability-audit`
- `20260318-1200-feature-enrichment-lab-production-gap-closure`
- `20260318-1400-feature-enrichment-lab-production-readiness`
- `20260319-2100-feature-enrichment-quality-regression-fix`
- `20260319-research-katago-allowmoves-occupied`
- `20260320-1600-feature-katago-enrichment-tuning`
- `20260320-2200-feature-katago-cfg-audit-fix`
- `20260322-1400-refactor-enrichment-lab-test-consolidation`
- `20260322-1500-feature-technique-calibration-fixtures`
- `20260322-1900-refactor-technique-registry-externalization`
- `20260324-2200-feature-enrichment-lab-test-audit`
- `20260325-1800-feature-instinct-calibration-golden-set`
- `20260325-research-instinct-calibration-golden-set`

### 6. SQLite, Search, Collections, and Browse

These initiatives cover the move to SQLite-backed search, browse-filter work, collection taxonomy, edition detection, and the supporting source-architecture/schema research that fed those decisions.

- `20260312-1600-feature-browse-filter-navigation-fix`
- `20260313-2200-feature-sqlite-puzzle-index`
- `20260314-2200-refactor-config-py-decomposition`
- `20260314-2300-feature-advanced-search-filters`
- `20260314-research-external-source-architecture`
- `20260314-research-db1-schema-tag-storage`
- `20260314-research-incremental-db-feasibility`
- `20260314-research-sequence-number-removal`
- `20260324-1900-feature-timed-puzzle-json-to-sql`
- `20260329-1800-feature-collections-launch-polish`
- `20260329-research-collection-assignment-pipeline`
- `20260330-2200-feature-collection-edition-detection`

### 7. Learning, Progress, and Play-Mode UX

This cluster contains the adaptive-learning and progress-page work, the rush-mode follow-through, and the broader playing-mode cleanup that remains historically relevant but no longer belongs under the active initiative workspace.

- `20260317-1400-feature-adaptive-learning-engine`
- `20260317-1400-feature-enrichment-data-liberation`
- `20260317-research-browser-tiny-llm`
- `20260322-1800-feature-rush-mode-fix`
- `20260324-1400-feature-rush-progress-component-tests`
- `20260324-1800-feature-frontend-cleanup-post-recovery`
- `20260324-2100-feature-quality-dry-cleanup`
- `20260329-1500-feature-playing-modes-dry-compliance`

### 8. Governance, Meta-Tracking, and Historical Outliers

These items were important to the March portfolio but are now historical records rather than active planning state. They are preserved here because they explain why the old initiative workspace was retired.

- `20260310-docs-consolidated-backlog`
- `20260315-research-gogogo-tactics-patterns`
- `20260324-research-initiative-audit`
- `20260325-refactor-model-paths-decomposition`

## Complete Retired Directory Index

```text
20260305-0000-feature-publish-incremental-flush
20260305-0000-feature-publish-snapshot-wiring
20260305-0000-feature-remove-dormant-dedup
20260305-0000-feature-sanderland-pass-move
20260305-0000-feature-teaching-comments-overhaul
20260306-0000-feature-publish-stage-cleanup
20260306-0000-feature-teaching-comments-v2
20260306-0000-refactor-phase-b-merge
2026-03-06-fix-enrichment-lab-logging-scope
20260307-0000-feature-enrichment-lab-gui
20260307-0000-feature-enrichment-lab-query-fix
20260307-0000-refactor-enrichment-no-solution-resilience
20260307-0000-refactor-enrich-single-decomposition
20260308-0000-bugfix-katago-perspective
20260308-1400-feature-katrain-reuse-enrichment-lab
20260308-1500-feature-tsumego-frame-rewrite
20260308-1800-feature-enrichment-lab-ghostban-gui
2026-03-08-research-ghostban-katago-webgl
20260309-1000-feature-enrichment-lab-gui-v4
20260310-1400-feature-inventory-reset-safety
20260310-docs-consolidated-backlog
20260310-feature-enrichment-lab-gui-ux-overhaul
20260310-feature-hint-config-dynamic-yh2
20260311-1600-feature-enrichment-lab-consolidation
20260311-1800-feature-teaching-comments-quality
20260311-1800-feature-tsumego-frame-legality
20260311-feature-enrichment-lab-gui-update
20260311-fix-config-fail-fast-dead-code
20260312-1400-feature-tsumego-frame-flood-fill
20260312-1600-feature-browse-filter-navigation-fix
20260312-1800-fix-tsumego-frame-spine-fill
20260313-1000-feature-gp-frame-swap
20260313-1400-refactor-enrich-single-srp
20260313-1600-feature-katrain-sgf-parser-swap
20260313-2000-feature-katrain-trap-density-elo-anchor
20260313-2200-feature-sqlite-puzzle-index
20260313-research-katrain-config-comparison
20260313-research-score-trap-density-elo-anchor
20260314-1400-feature-enrichment-lab-v2
20260314-2200-refactor-config-py-decomposition
20260314-2300-feature-advanced-search-filters
20260314-feature-enrichment-lab-config-panel
20260314-research-external-source-architecture
20260314-research-db1-schema-tag-storage
20260314-research-incremental-db-feasibility
20260314-research-lizgoban-katrain-patterns
20260314-research-sequence-number-removal
20260315-1400-feature-tactical-analysis-wiring
20260315-1500-feature-daily-db-migration
20260315-1700-feature-enrichment-lab-tactical-hints
20260315-2000-feature-refutation-quality
20260315-research-gogogo-tactics-patterns
20260317-1400-feature-adaptive-learning-engine
20260317-1400-feature-enrichment-data-liberation
20260317-research-browser-tiny-llm
20260317-research-capability-audit
20260318-1200-feature-enrichment-lab-production-gap-closure
20260318-1400-feature-enrichment-lab-production-readiness
20260318-research-hinting-system-comparison
20260319-1000-feature-trace-search-optimization
20260319-2100-feature-enrichment-quality-regression-fix
20260319-research-katago-allowmoves-occupied
20260320-1400-feature-enrichment-almost-correct-reversal
20260320-1600-feature-katago-enrichment-tuning
20260320-2200-feature-katago-cfg-audit-fix
20260321-1000-feature-mark-sibling-refutations
20260321-1400-feature-html-report-redesign
20260321-1800-feature-enrichment-log-viewer
20260321-2100-refactor-enrichment-lab-dry-cli-centralization
20260322-1400-refactor-enrichment-lab-test-consolidation
20260322-1500-feature-technique-calibration-fixtures
20260322-1800-feature-rush-mode-fix
20260322-1900-refactor-technique-registry-externalization
20260324-1400-feature-rush-progress-component-tests
20260324-1500-feature-backend-dead-code-cleanup
20260324-1800-feature-frontend-cleanup-post-recovery
20260324-1900-feature-timed-puzzle-json-to-sql
20260324-2000-feature-backend-test-remediation
20260324-2100-feature-quality-dry-cleanup
20260324-2200-feature-enrichment-lab-test-audit
20260324-research-backend-failing-tests
20260324-research-initiative-audit
20260325-1800-feature-instinct-calibration-golden-set
20260325-refactor-model-paths-decomposition
20260325-research-instinct-calibration-golden-set
20260326-1400-feature-llm-teaching-enrichment
20260329-1500-feature-playing-modes-dry-compliance
20260329-1800-feature-collections-launch-polish
20260329-research-collection-assignment-pipeline
20260330-2200-feature-collection-edition-detection
```

## Notes on Retention Strategy

- This digest intentionally replaces the old folder tree with one historical narrative entry point.
- Canonical engineering guidance belongs in the current architecture, concepts, how-to, and reference docs listed above.
- The active initiative workspace now starts after the March retirement boundary; April and later work remains in `TODO/initiatives/` until it is explicitly retired.
