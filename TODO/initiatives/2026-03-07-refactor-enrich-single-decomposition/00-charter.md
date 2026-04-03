# Charter: Decompose enrich_single.py into smaller modules

**Last Updated:** 2026-03-07  
**Initiative ID:** 2026-03-07-refactor-enrich-single-decomposition  
**Type:** Refactor  
**Correction Level:** Level 3 (Multiple Files — 2-3+ files, logic restructuring)

## Problem Statement

`tools/puzzle-enrichment-lab/analyzers/enrich_single.py` is ~1,593 lines containing:

- Config resolution helpers (metadata extraction, tag/level lookup caching)
- Result assembly helpers (error results, partial results, difficulty snapshots, refutation entries)
- Coordinate back-translation
- The main 500+ line `enrich_single_puzzle()` orchestrator with 3 major code paths:
  - Position-only path (AI-Solve from scratch)
  - Has-solution + AI-Solve validation path
  - Standard path (no AI-Solve)

This monolith file makes independent iteration difficult — changes to metadata parsing, result assembly, or AI-Solve integration require touching and re-testing the same large file.

## Goals

1. Enable independent iteration on distinct functional areas
2. Improve testability — unit tests for helpers can target specific modules
3. Reduce cognitive load when modifying one concern
4. Preserve all existing behavior (zero functional changes)

## In-Scope Files

| ID  | File                                                      | Role                                    |
| --- | --------------------------------------------------------- | --------------------------------------- |
| F1  | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`  | Primary target (1,593 lines)            |
| F2  | `tools/puzzle-enrichment-lab/tests/test_enrich_single.py` | Tests importing private symbols         |
| F3  | `tools/puzzle-enrichment-lab/cli.py`                      | Caller (imports `enrich_single_puzzle`) |
| F4  | `tools/puzzle-enrichment-lab/gui/bridge.py`               | Caller (imports `enrich_single_puzzle`) |
| F5  | `tools/puzzle-enrichment-lab/scripts/run_calibration.py`  | Caller (imports `enrich_single_puzzle`) |

## Out-of-Scope

- Functional changes to enrichment behavior
- Changes to pipeline backend (`backend/puzzle_manager/`)
- Changes to models (`tools/puzzle-enrichment-lab/models/`)
- Performance optimization
- New features

## Functional Groups Identified in enrich_single.py

| Group    | Lines    | Functions                                                                                                                                                                     | Description                             |
| -------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| G-META   | 118–295  | `_extract_metadata`, `_parse_tag_ids`, `_load_tag_slug_map`, `_load_tag_id_to_name`, `_load_level_id_map`, `_resolve_tag_names`, `_resolve_level_info`, `_extract_level_slug` | Config/metadata resolution with caching |
| G-RESULT | 300–429  | `_build_refutation_entries`, `_build_difficulty_snapshot`, `_compute_config_hash`, `_make_error_result`, `_build_partial_result`                                              | Result assembly/factory helpers         |
| G-COORD  | 437–492  | `_uncrop_response`                                                                                                                                                            | Coordinate back-translation             |
| G-ORCH   | 505–1593 | `enrich_single_puzzle()`                                                                                                                                                      | Main orchestrator (9-step pipeline)     |

## Callers of Public API

| Caller                       | Import                                                     |
| ---------------------------- | ---------------------------------------------------------- |
| `cli.py`                     | `from analyzers.enrich_single import enrich_single_puzzle` |
| `gui/bridge.py`              | `from analyzers.enrich_single import enrich_single_puzzle` |
| `scripts/run_calibration.py` | `from analyzers.enrich_single import enrich_single_puzzle` |

## Test Imports (Private Symbols)

```python
from analyzers.enrich_single import enrich_single_puzzle, _parse_tag_ids, _load_tag_slug_map, _TAG_SLUG_TO_ID, _extract_metadata
import analyzers.enrich_single as _enrich_mod  # resets _TAG_SLUG_TO_ID cache
```

## Constraints

1. `tools/` must NOT import from `backend/` (architecture rule)
2. Existing dual try/except import pattern must be preserved for module-level imports
3. All existing tests must pass without behavioral changes
4. No new external dependencies

> **See also:**
>
> - [Architecture: enrichment-lab](../../docs/architecture/) — System context
> - [Concepts: numeric-id-scheme](../../docs/concepts/numeric-id-scheme.md) — ID resolution
