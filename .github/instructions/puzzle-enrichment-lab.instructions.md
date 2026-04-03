---
applyTo: "tools/puzzle-enrichment-lab/**"
---

## Puzzle-Enrichment-Lab Module Context

Before working in this module, read [`tools/puzzle-enrichment-lab/AGENTS.md`](../../tools/puzzle-enrichment-lab/AGENTS.md). It contains the full architecture map: file inventory, core entities, key methods, data flow, coordinate systems, and gotchas.

### Update Rule

After any structural change in this module, update `AGENTS.md` in the **same commit**:
- New file added → add row to Section 1
- New public function/class → add row to Section 3
- New data model → add row to Section 2
- Changed data flow → update Section 4
- New coupling or gotcha → add bullet to Section 6
- Update footer: `_Last updated: {YYYY-MM-DD} | Trigger: {what changed}_`

To regenerate from scratch after large changes, use the prompt at `.github/prompts/regen-agents-map.prompt.md`.

### Key Facts (Quick Reference)

- Entry point: `analyzers/enrich_single.py::enrich_single_puzzle()` (async)
- Stage runner: `analyzers/stages/stage_runner.py::StageRunner.run_pipeline()`
- KataGo is never called directly — always via injected `engine_manager`
- Coordinate boundary: `query_builder.py` converts SGF→GTP; `uncrop_response()` converts GTP→SGF
- Config source: `config/katago-enrichment.json` → `EnrichmentConfig`
- Tests: `python -m pytest tests/ --cache-clear` (from `tools/puzzle-enrichment-lab/`)
