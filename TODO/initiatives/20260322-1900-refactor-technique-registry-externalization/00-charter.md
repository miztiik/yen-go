# Charter — Externalize TECHNIQUE_REGISTRY

Last Updated: 2026-03-22

## Initiative

| Field | Value |
|-------|-------|
| ID | 20260322-1900-refactor-technique-registry-externalization |
| Type | Refactor |
| Module | tools/puzzle-enrichment-lab |
| Owner | Refactor-Planner |
| Parent Initiative | 20260322-1500-feature-technique-calibration-fixtures (OPT-3, closed) |

## Problem Statement

The `TECHNIQUE_REGISTRY` in `test_technique_calibration.py` contains ~250 lines of hardcoded ground-truth calibration data (25 `TechniqueSpec` entries). This data is:

1. **Embedded in test code** — test files should test, not define canonical data
2. **Not independently updateable** — changing a fixture's expected values requires editing Python source
3. **Not regeneratable** — if fixtures or pipeline behavior change, expected values must be manually re-derived
4. **Not versioned as data** — git history mixes data changes with test logic changes

### Current State

- 25 `TechniqueSpec` dict entries hardcoded in `test_technique_calibration.py` (~lines 68–398)
- `TechniqueSpec` TypedDict defines 5 required calibration dimensions + 4 optional edge-case fields
- 3 unit tests cross-check registry against `config/tags.json`
- 5 parametrized integration tests validate each technique across 5 dimensions
- `EXCLUDED_NON_TSUMEGO_TAGS = {"joseki", "fuseki", "endgame"}` (C2 governance decision)

### Target State

- `TECHNIQUE_REGISTRY` data stored externally (format TBD per options)
- `test_technique_calibration.py` loads data at import time
- All 8 existing tests pass unchanged
- Clear regeneration path for when fixtures/pipeline change
- Git history cleanly separates data changes from test logic

## Goals

| goal_id | Goal | Measurable Target |
|---------|------|-------------------|
| G-1 | Externalize calibration ground-truth data | 0 hardcoded TechniqueSpec dicts in test file |
| G-2 | Maintain test compatibility | All 3 unit + 5×25 integration tests pass |
| G-3 | Enable independent data updates | Data file editable without touching test code |
| G-4 | Enable regeneration | Process exists to re-derive expected values from fixtures |
| G-5 | Improve git history clarity | Data changes in dedicated data files |

## Non-Goals

| ng_id | Non-Goal | Rationale |
|-------|----------|-----------|
| NG-1 | Changing the enrichment pipeline | This is data-location only |
| NG-2 | Changing test assertions or calibration dimensions | Tests stay identical |
| NG-3 | Adding new techniques or fixtures | Fixture set is stable from parent initiative |
| NG-4 | Modifying TechniqueSpec TypedDict | Governance-approved design (OPT-3) |
| NG-5 | Centralizing with `test_fixture_coverage.py` data | Separate concern |

## Constraints

| c_id | Constraint | Source |
|------|-----------|--------|
| C-1 | TechniqueSpec TypedDict must remain | Governance decision (OPT-3, parent initiative) |
| C-2 | EXCLUDED_NON_TSUMEGO_TAGS must remain | Governance decision C2 |
| C-3 | No changes to enrichment pipeline | User constraint |
| C-4 | Solution must be simple (YAGNI) | Project principles |
| C-5 | config/tags.json is SSOT for tag definitions | Project architecture |
| C-6 | Enrichment lab must NOT import from backend/ | Architecture rule |
| C-7 | AGENTS.md must be updated for structural changes | Project convention |
| C-8 | 3-tier docs pattern for documentation changes | Project convention |

## In-Scope Files

| file_id | File | Role |
|---------|------|------|
| F-1 | `tools/puzzle-enrichment-lab/tests/test_technique_calibration.py` | Source file: remove hardcoded data, add loader |
| F-2 | TBD data file (per selected option) | New: ground-truth data |
| F-3 | TBD regeneration utility (per selected option) | New: optional regen script |
| F-4 | `tools/puzzle-enrichment-lab/AGENTS.md` | Update: reflect new data file |

## Out-of-Scope Files

- `tools/puzzle-enrichment-lab/tests/test_fixture_coverage.py` — has its own data, separate concern
- `tools/puzzle-enrichment-lab/tests/test_golden5.py` — GOLDEN5_PUZZLES is separate
- `config/tags.json` — read-only source of truth, no changes
- All enrichment pipeline code (`analyzers/`, `models/`, `config/`)
