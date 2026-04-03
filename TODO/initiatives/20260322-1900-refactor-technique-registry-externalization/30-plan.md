# Refactor Plan — Externalize TECHNIQUE_REGISTRY (OPT-1)

Last Updated: 2026-03-22

## Selected Option

**OPT-1: JSON Data File + Thin Loader** — approved unanimously by governance panel (GOV-OPTIONS-APPROVED).

## Architecture Decisions

| ad_id | Decision | Rationale |
|-------|----------|-----------|
| AD-1 | JSON file at `tests/fixtures/technique-benchmark-reference.json` | Q3:A — alongside existing fixtures. Consistent with `extended-benchmark/README.md` and fixture audit. |
| AD-2 | All TechniqueSpec fields stored in JSON | Q6:A — explicit ground truth. No derived fields at test time. |
| AD-3 | Metadata header: `version`, `last_updated`, `description` | Q7:A — matches `config/*.json` convention. |
| AD-4 | Loader validates via `TechniqueSpec(**entry)` | Must-hold #2 — fail fast on malformed JSON. TypedDict construction catches missing/extra keys at runtime. |
| AD-5 | Regen script at `scripts/regenerate_benchmark_reference.py` | Q5:A — user requested now. Uses `enrich_single_puzzle()` (must-hold #3). |
| AD-6 | TechniqueSpec TypedDict stays in `test_technique_calibration.py` | C-1 governance constraint. TypedDict is a test concern, not data. |
| AD-7 | EXCLUDED_NON_TSUMEGO_TAGS stays in `test_technique_calibration.py` | C-2 governance constraint. Test-level policy. |

## File Transformations

### F-1: `tests/test_technique_calibration.py`

**Remove** (~250 lines):
- Lines 68–398: entire `TECHNIQUE_REGISTRY` dict literal (25 entries, `# fmt: off` / `# fmt: on` block)

**Add** (~20 lines):
- `_load_registry()` function that:
  1. Reads `FIXTURES / "technique-benchmark-reference.json"`
  2. Parses JSON
  3. Extracts `data["techniques"]`
  4. Returns `{slug: TechniqueSpec(**entry) for slug, entry in techniques.items()}`
- `TECHNIQUE_REGISTRY: dict[str, TechniqueSpec] = _load_registry()` at module level

**Keep unchanged**:
- `TechniqueSpec` TypedDict (AD-6)
- `EXCLUDED_NON_TSUMEGO_TAGS` (AD-7)
- All test functions (3 unit + 5 parametrized)
- `_HERE`, `_LAB`, `FIXTURES`, `CONFIG_DIR` path constants
- All imports
- KataGo model resolution and `_best_model()`
- `TestTechniqueCalibration` class and `_enrich()` helper

### F-2: `tests/fixtures/technique-benchmark-reference.json` (NEW)

**Create** with:
- Top-level metadata: `version`, `last_updated`, `description`
- `"techniques"` object: 25 entries keyed by tag slug
- Each entry contains all TechniqueSpec fields (required + optional)
- Values transcribed exactly from current `TECHNIQUE_REGISTRY` dict
- `notes` field preserved per entry for provenance

### F-3: `scripts/regenerate_benchmark_reference.py` (NEW)

**Create** with:
- Async script that:
  1. Reads `config/tags.json` to get active tsumego tag list
  2. Reads current `technique-benchmark-reference.json` for fixture mappings
  3. For each technique, runs `enrich_single_puzzle()` on the fixture
  4. Extracts actual values: correct_move_gtp, technique_tags, difficulty level_id, refutation count, teaching_comments presence
  5. Compares with current expected values and reports diffs
  6. Writes updated JSON with new `last_updated` timestamp
- `--dry-run` mode: show diffs without writing (GV-8 recommendation)
- Requires KataGo binary + model (like integration tests)
- Uses `SingleEngineManager` in `quick_only` mode (matches test suite)

### F-4: `AGENTS.md`

**Update** the `tests/` section to mention:
- `tests/fixtures/technique-benchmark-reference.json` — externalized calibration data
- `scripts/regenerate_benchmark_reference.py` — regen utility

## Invariants

| inv_id | Invariant | Verification |
|--------|-----------|-------------|
| INV-1 | All 25 TechniqueSpec entries present after migration | `test_all_tags_have_registry_entry()` passes |
| INV-2 | All fixture files referenced exist | `test_registry_entries_reference_existing_fixtures()` passes |
| INV-3 | No excluded tags in registry | `test_no_excluded_tags_in_registry()` passes |
| INV-4 | 5 calibration dimensions validated per technique | 5 parametrized `test_*` methods unchanged |
| INV-5 | JSON loads without error | Loader fails fast on malformed JSON (AD-4) |
| INV-6 | Data values identical to current hardcoded values | Diff current output vs JSON content |

## Risks and Mitigations

| risk_id | Risk | Probability | Impact | Mitigation |
|---------|------|-------------|--------|------------|
| R-1 | JSON transcription error (typo in value) | Low | Medium — test failure on specific technique | Automated export from current dict to JSON (T2). Cross-check with `json.dumps()` of current dict. |
| R-2 | TypedDict(**dict) fails on JSON null/missing keys | Low | Low — caught at import time | Loader wraps in try/except with clear error message. Unit test validates loading. |
| R-3 | Regen script produces different values than current | Medium | Low — expected, values are model-dependent | `--dry-run` shows diffs. Document that model version affects results. |
| R-4 | JSON file accidentally modified (format/whitespace) | Low | None — `json.load()` is whitespace-insensitive | Add `.editorconfig` rule for JSON if not exists. |

## Rollback Strategy

1. **Git revert**: Single commit contains all 4 file changes → `git revert <sha>` restores previous state
2. **Manual**: Copy `TECHNIQUE_REGISTRY` dict from git history back into test file, delete JSON + script

## SOLID/DRY/KISS/YAGNI Mapping

| Principle | Application |
|-----------|-------------|
| **SRP** | Test file tests (behavior). JSON file holds data (ground truth). Script regenerates (tooling). Three concerns, three files. |
| **OCP** | Adding a new technique = add JSON entry + fixture file. Test file unchanged. |
| **KISS** | Loader is ~15 lines. JSON is standard. No custom parsing, no schema validation library. |
| **YAGNI** | Regen script included per user request (Q5:A). No JSON Schema (OPT-3 rejected). No TOML. No Python data module. |
| **DRY** | Single source of calibration truth (JSON). TypedDict defines structure once (in test file). |

## Documentation Plan

| doc_id | files_to_update | why_updated | cross_references |
|--------|----------------|-------------|------------------|
| DOC-1 | `tools/puzzle-enrichment-lab/AGENTS.md` | New data file and regen script in directory structure | `tests/test_technique_calibration.py` entry |
| DOC-2 | `tests/fixtures/technique-benchmark-reference.json` (self-documenting) | `description` field explains purpose; `notes` per entry for provenance | Links to parent initiative OPT-3 |

No user-facing docs changes needed — this is internal test infrastructure.
