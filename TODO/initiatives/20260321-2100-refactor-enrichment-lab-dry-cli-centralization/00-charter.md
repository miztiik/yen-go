# Charter — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-21  
> Initiative ID: 20260321-2100-refactor-enrichment-lab-dry-cli-centralization  
> Correction Level: **Level 3 (Multiple Files)** — 10+ files, logging + config + CLI + engine lifecycle

## Problem Statement

The `tools/puzzle-enrichment-lab/` has accumulated significant DRY violations and CLI bypass patterns:

1. **13 in-scope standalone scripts** (2 excluded per C4) with `if __name__ == "__main__"` blocks that bypass the CLI entry point
2. **5 different logging initialization patterns** with inconsistent parameters
3. **20+ calls to `load_enrichment_config()`** scattered across files with 4 different call patterns
4. **8 independent `argparse.ArgumentParser` instances** with duplicated argument definitions
5. **3 KataGo engine lifecycle duplications** (create → start → run → shutdown)
6. **2 regex-based SGF parsers** duplicating `core.tsumego_analysis.parse_sgf()` functionality
7. **`_model_paths.py` executes config loading at import time** (non-lazy, before logging setup)

These violations cause maintenance burden, inconsistent behavior, and risk of config/log drift.

## Goals

| ID | Goal | Measurable Outcome |
|----|------|--------------------|
| G1 | Centralize logging initialization | Single `init_lab()` or bootstrap function used by ALL entry points (cli, bridge, conftest, scripts) |
| G2 | Centralize config loading | Single cached load pattern; remove non-lazy module-level loads |
| G3 | Eliminate KataGo config resolution duplication | `_resolve_katago_config()` exists in ONE location |
| G4 | Provide engine lifecycle context manager | `async with engine_context(config) as engine:` pattern usable by all callers |
| G5 | Remove regex SGF parsers in test utilities | `tests/render_fixtures.py` and `tests/generate_review_report.py` use `core` parser |
| G6 | Absorb key scripts into CLI subcommands | Scripts that use enrichment internals route through CLI |
| G7 | Zero test regressions | All functional/unit tests pass before AND after every phase |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Merge `probe_frame.py` / `probe_frame_gp.py` | User directive: do not touch these files |
| NG2 | Rewrite logging infrastructure (`log_config.py` internals) | KISS — centralize calls, don't restructure the logging engine |
| NG3 | Change config schema or `EnrichmentConfig` model | Out of scope — only change how/where config is loaded |
| NG4 | Add new enrichment features | Pure refactor — behavior must be identical |
| NG5 | Modify calibration/benchmark/golden test infrastructure | Excluded from regression gating |

## Constraints

| ID | Constraint |
|----|------------|
| C1 | Zero regressions — ALL functional/unit tests must pass before AND after each phase |
| C2 | Clean commit before implementation starts |
| C3 | Every phase gated by Governance Panel review |
| C4 | Do NOT modify `probe_frame.py` or `probe_frame_gp.py` |
| C5 | AGENTS.md must be updated in the same commit as structural changes |
| C6 | Documentation updates are part of definition-of-done |
| C7 | No new external dependencies |

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | `setup_logging()` called from exactly ONE bootstrap function across all entry points | grep verification |
| AC2 | `load_enrichment_config()` called through centralized pattern (no module-level eager loads) | grep + code review |
| AC3 | `_resolve_katago_config()` exists in exactly ONE file | grep verification |
| AC4 | Engine lifecycle uses context manager or shared factory | Code review |
| AC5 | Regex SGF parsing deduplicated to single shared module (`tests/_sgf_render_utils.py`); no copy-paste parsers in individual test utilities. Rationale: research Adaptation D confirms regex is appropriate for visualization utilities — dedup is the priority, not technology change. | grep for `parse_sgf_properties` in render_fixtures.py and generate_review_report.py → should import from _sgf_render_utils |
| AC6 | Test suite passes identically before and after | pytest output comparison |
| AC7 | AGENTS.md updated with structural changes | Commit review |

## Affected Files (Estimated)

| File | Change Type |
|------|-------------|
| `cli.py` | Major: extract bootstrap, add engine context manager usage |
| `bridge.py` | Medium: use bootstrap, use engine context manager |
| `conftest.py` | Minor: use bootstrap |
| `log_config.py` | Minor: may add bootstrap wrapper |
| `_model_paths.py` | Medium: make lazy |
| `config/__init__.py` | Minor: ensure caching consistency |
| `scripts/run_calibration.py` | Medium: remove `_resolve_katago_config()` duplicate, use bootstrap |
| `scripts/diagnose_chase_puzzle.py` | Medium: use bootstrap |
| `scripts/download_models.py` | Minor: use bootstrap if applicable |
| `scripts/hydrate_calibration_fixtures.py` | Minor: use bootstrap |
| `tests/render_fixtures.py` | Medium: replace regex SGF parser |
| `tests/generate_review_report.py` | Medium: replace regex SGF parser |
| `AGENTS.md` | Documentation: update structural map |

> **See also:**
> - [Clarifications](./10-clarifications.md) — Resolved decisions
> - [Options](./25-options.md) — Design alternatives (pending)
> - [Analysis](./20-analysis.md) — Coverage and impact analysis (pending)
