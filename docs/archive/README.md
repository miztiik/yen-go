# Archived Documentation

> **See also**:
>
> - [Architecture Overview](../architecture/README.md) — Current system design
> - [How-To Guides](../how-to/) — Current procedures

**Last Updated**: 2026-03-10

Documents in this directory are deprecated and kept for historical reference only.

---

## Deprecation Policy

Documents are moved here when:

- Technology is no longer used
- Approach has been superseded
- Information is outdated but historically relevant

All archived documents include a deprecation banner at the top.

---

## Archived Documents

| Document                                           | Superseded By                             | Deprecated |
| -------------------------------------------------- | ----------------------------------------- | ---------- |
| [katago-integration.md](katago-integration.md)     | Curated sources (no AI validation)        | 2026-01    |
| [pipeline-v3-design.md](pipeline-v3-design.md)     | 3-stage pipeline (ingest/analyze/publish) | 2026-02    |
| [ai-puzzle-validation.md](ai-puzzle-validation.md) | Source quality ratings + PuzzleValidator  | 2026-02    |
| [di-test-isolation.md](di-test-isolation.md)       | `YENGO_RUNTIME_DIR` env var + `paths.py`  | 2026-02    |
| [ai-solve-enrichment-plan-v1.md](ai-solve-enrichment-plan-v1.md) | AI-solve v3 unified plan + ADR-008 | 2026-03 |
| [ai-solve-enrichment-plan-v2.1.md](ai-solve-enrichment-plan-v2.1.md) | AI-solve v3 unified plan + ADR-008 | 2026-03 |
| [enrichment-lab-code-review-2026-03-02.md](enrichment-lab-code-review-2026-03-02.md) | Audit synthesis + remediation sprints | 2026-03 |
| [katago-enrichment-code-review-2026-03-02.md](katago-enrichment-code-review-2026-03-02.md) | Audit synthesis + remediation sprints | 2026-03 |
| [katago-enrichment-audit-synthesis-2026-03-02.md](katago-enrichment-audit-synthesis-2026-03-02.md) | AI-solve remediation and initiative tracking | 2026-03 |
| [xuanxuango-solver-research-2026-03-04.md](xuanxuango-solver-research-2026-03-04.md) | External solver research notes and benchmark ideas | 2026-03 |
| [sgf-architecture-design.md](sgf-architecture-design.md) | SGF property design rationale — superseded by [architecture/backend/sgf.md](../architecture/backend/sgf.md) | 2026-03 |
| [sgf-format-analysis.md](sgf-format-analysis.md) | SGF format industry comparison — superseded by [architecture/backend/sgf.md](../architecture/backend/sgf.md) | 2026-03 |
| [guides-observability.md](guides-observability.md) | Observability guide — superseded by [how-to/backend/monitor.md](../how-to/backend/monitor.md) | 2026-03 |
| [guides-pipeline-operations.md](guides-pipeline-operations.md) | Pipeline ops guide — superseded by [how-to/backend/run-pipeline.md](../how-to/backend/run-pipeline.md) | 2026-03 |
| [guides-puzzle-manager-usage.md](guides-puzzle-manager-usage.md) | CLI usage guide — superseded by [how-to/backend/cli-reference.md](../how-to/backend/cli-reference.md) | 2026-03 |
| [guides-rollback.md](guides-rollback.md) | Rollback guide — superseded by [how-to/backend/rollback.md](../how-to/backend/rollback.md) | 2026-03 |
| [guides-troubleshoot.md](guides-troubleshoot.md) | Troubleshoot guide — superseded by [how-to/backend/troubleshoot.md](../how-to/backend/troubleshoot.md) | 2026-03 |

---

## Using Archived Documents

⚠️ **Do not use information from archived documents for current development.**

If you need similar functionality:

1. Check current documentation in `docs/`
2. Ask for guidance
