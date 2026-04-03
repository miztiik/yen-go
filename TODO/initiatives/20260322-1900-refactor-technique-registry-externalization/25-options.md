# Options — Externalize TECHNIQUE_REGISTRY

Last Updated: 2026-03-22

## Context

User clarifications resolved (Q1–Q7). Key decisions:
- **Q1:B** No backward compatibility needed
- **Q2:A** Remove hardcoded dict entirely
- **Q3:A** `tests/fixtures/technique-benchmark-reference.json`
- **Q4:A** JSON format
- **Q5:A** Include regeneration script now
- **Q6:A** Store all fields (explicit ground truth)
- **Q7:A** Metadata header (version + last_updated)

## Options Comparison

### OPT-1: JSON Data File + Thin Loader

**Approach**: Create `tests/fixtures/technique-benchmark-reference.json` with all 25 TechniqueSpec entries. Add a `_load_registry()` function in `test_technique_calibration.py` that reads and validates the JSON at module import time. Create `scripts/regenerate_benchmark_reference.py` that enriches each fixture through the pipeline and writes the JSON.

**Data file structure**:
```json
{
  "$schema": "./schemas/technique-benchmark.schema.json",
  "version": "1.0",
  "last_updated": "2026-03-22",
  "description": "Ground-truth calibration data for 25 active tsumego techniques",
  "techniques": {
    "life-and-death": {
      "fixture": "simple_life_death.sgf",
      "correct_move_gtp": "B2",
      "expected_tags": ["life-and-death"],
      "min_level_id": 130,
      "max_level_id": 230,
      "min_refutations": 1,
      "expect_teaching_comments": false,
      "board_size": 19,
      "notes": "Goproblems 1042: advanced L&D..."
    }
  }
}
```

**Loader in test file** (~15 lines):
```python
def _load_registry() -> dict[str, TechniqueSpec]:
    path = FIXTURES / "technique-benchmark-reference.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: TechniqueSpec(**v) for k, v in data["techniques"].items()}

TECHNIQUE_REGISTRY = _load_registry()
```

**Regen script**: `scripts/regenerate_benchmark_reference.py` — runs `enrich_single_puzzle()` on each fixture, extracts actual values, writes JSON. Requires KataGo.

| Dimension | Assessment |
|-----------|------------|
| OPT-1-BEN | **Benefits**: Clean data/logic separation. JSON is human-readable, diff-friendly, and toolable. Matches `config/*.json` conventions. Metadata header enables traceability. Regen script closes the loop. |
| OPT-1-DRW | **Drawbacks**: No native comments in JSON (must use `notes` field). Loader needs explicit TypedDict casting. Schema drift risk if TechniqueSpec changes without JSON update. |
| OPT-1-RSK | **Risks**: LOW — JSON loading is trivial. Only risk is schema mismatch between TypedDict and JSON keys, mitigated by runtime validation in loader. |
| OPT-1-CPX | **Complexity**: LOW — 1 new JSON file, 1 new script, ~20 lines changed in test file |
| OPT-1-MIG | **Migration**: Export current dict → JSON, replace dict with loader, verify tests pass |
| OPT-1-RBK | **Rollback**: Revert 3 files (test, JSON, script). Or: inline JSON back to dict. |
| OPT-1-SLD | **SOLID/DRY/KISS/YAGNI**: KISS ✅ (simple file read). SRP ✅ (test tests, data is data). YAGNI: regen script is requested by user. DRY ✅ (single source of truth for calibration data). |

---

### OPT-2: Python Data Module (`_technique_registry_data.py`)

**Approach**: Create `tests/_technique_registry_data.py` containing the dict literal. `test_technique_calibration.py` imports it. No JSON, no parsing, no schema drift risk. Regen script writes Python source.

**Data module**:
```python
# tests/_technique_registry_data.py
"""Ground-truth calibration data — auto-generated, do not hand-edit."""
REGISTRY_VERSION = "1.0"
REGISTRY_LAST_UPDATED = "2026-03-22"

TECHNIQUE_DATA: dict[str, dict] = {
    "life-and-death": {
        "fixture": "simple_life_death.sgf",
        ...
    }
}
```

**Import in test file** (~3 lines):
```python
from _technique_registry_data import TECHNIQUE_DATA
TECHNIQUE_REGISTRY: dict[str, TechniqueSpec] = TECHNIQUE_DATA  # type: ignore
```

| Dimension | Assessment |
|-----------|------------|
| OPT-2-BEN | **Benefits**: Zero parsing overhead. Native Python comments. IDE autocomplete on keys. No schema drift — it's already Python. Trivial import. |
| OPT-2-DRW | **Drawbacks**: Data is still Python code — not independently toolable by non-Python scripts. Git diffs mix Python syntax with data changes. Not "data as data" (it's "data as code"). TypedDict validation requires `# type: ignore` or explicit casting. |
| OPT-2-RSK | **Risks**: LOW — but doesn't achieve the stated goal of separating data from code. Python module is still code. |
| OPT-2-CPX | **Complexity**: LOWEST — 1 new `.py` file, 3 lines changed in test file |
| OPT-2-MIG | **Migration**: Move dict to new file, add import. Trivial. |
| OPT-2-RBK | **Rollback**: Move dict back inline. |
| OPT-2-SLD | **SOLID/DRY/KISS/YAGNI**: KISS ✅ (just an import). SRP: partial — it's a separate file but still Python. DRY ✅. YAGNI ✅. |

---

### OPT-3: JSON Data File + JSON Schema Validation

**Approach**: Same as OPT-1 but adds a JSON Schema file (`tests/fixtures/schemas/technique-benchmark.schema.json`) that formally defines the TechniqueSpec structure. The loader validates against the schema at import time using `jsonschema` (new dev dependency) or a simple structural check.

| Dimension | Assessment |
|-----------|------------|
| OPT-3-BEN | **Benefits**: All OPT-1 benefits + formal schema enforcement. Prevents silent data corruption. Schema file is self-documenting. |
| OPT-3-DRW | **Drawbacks**: Adds `jsonschema` dependency (or manual validation code). Over-engineering for 25 entries that are already validated by 3 unit tests (the cross-check tests catch any structural issues). Dual schema maintenance (TypedDict + JSON Schema). |
| OPT-3-RSK | **Risks**: LOW technically, but HIGH for YAGNI violation. The 3 existing unit tests already validate: (1) all tags covered, (2) all fixture files exist, (3) no excluded tags. Adding JSON Schema duplicates this validation. |
| OPT-3-CPX | **Complexity**: MEDIUM — 1 JSON + 1 schema + potential new dependency + validation code |
| OPT-3-MIG | **Migration**: Same as OPT-1 + create schema + add validation |
| OPT-3-RBK | **Rollback**: Same as OPT-1 |
| OPT-3-SLD | **SOLID/DRY/KISS/YAGNI**: KISS ❌ (schema is unnecessary given existing unit tests). YAGNI ❌ (formal schema for 25 entries validated by tests). DRY ❌ (TypedDict + Schema = dual definitions). |

---

## Comparison Matrix

| Dimension | OPT-1 (JSON + Loader) | OPT-2 (Python Module) | OPT-3 (JSON + Schema) |
|-----------|----------------------|----------------------|----------------------|
| Data/code separation | ✅ Full | ⚠️ Partial (still Python) | ✅ Full |
| Human editability | ✅ JSON is universal | ⚠️ Requires Python knowledge | ✅ JSON is universal |
| Toolability (non-Python) | ✅ Any JSON tool | ❌ Python only | ✅ Any JSON tool |
| Git diff clarity | ✅ Clean JSON diffs | ⚠️ Python syntax noise | ✅ Clean JSON diffs |
| Type safety | ⚠️ Needs runtime cast | ⚠️ Needs `type: ignore` | ✅ Schema-validated |
| Complexity | LOW | LOWEST | MEDIUM |
| YAGNI compliance | ✅ | ✅ | ❌ |
| New dependencies | None | None | `jsonschema` (optional) |
| Regen script complexity | Medium (write JSON) | Medium (write Python) | Medium (write JSON) |
| Migration effort | ~1 hour | ~30 min | ~2 hours |

## Recommendation

**OPT-1 (JSON Data File + Thin Loader)** is the recommended option:

1. Achieves clean data/code separation (the stated goal)
2. Matches project convention (`config/*.json`, `extended-benchmark/README.md`)
3. KISS/YAGNI compliant — no unnecessary schema machinery
4. Enables non-Python tooling and clean git diffs
5. Regen script writes standard JSON (simple `json.dump`)
6. User already indicated Q4:A (JSON) preference

OPT-2 is simpler but doesn't fully achieve the "data as data" goal. OPT-3 is over-engineered given existing test guards.
