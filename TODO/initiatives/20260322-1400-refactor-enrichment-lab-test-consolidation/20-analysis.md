# Analysis — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Test Suite Inventory Summary

| Category | File Count | Test Count (approx) | Status |
|----------|-----------|---------------------|--------|
| Data Models & Serialization | 6 | 94 | Well-organized |
| Engine & Analysis Pipeline | 10 | 112 | Well-organized |
| Difficulty & Quality Estimation | 8 | 129 | Well-organized |
| Technique Detection | 6 | 102 | Well-organized |
| Refutation & Solution Tree | 9 | 155 | Well-organized (phases A-D distinct) |
| SGF Processing | 5 | 79 | Well-organized |
| Teaching & Hints | 5 | 84 | Well-organized (4-layer: unit/integration/embedding/config) |
| Configuration & Validation | 9 | 130 | Well-organized |
| Geometry & Framing | 5 | 79 | Well-organized |
| Integration & Performance | 11 | 75 | Minor cleanup needed (Lane 4) |
| **Sprint Fixes** | **5** | **72** | **ACTION: Migrate to domain files (Lane 1)** |
| Infrastructure (conftest, utils) | 3 | — | Lane 3 target |
| **Total** | **~79 files** | **~600+ tests** | |

## Ripple-Effect Analysis

### Lane 1: Sprint File Migration

| Impact Area | Risk | Mitigation |
|-------------|------|------------|
| 13 target files receive new test classes | Low — append-only operation | Each migration is a single class append with imports |
| 5 sprint files deleted | Low — after verification | `pytest --co -q` count check before/after |
| Gap ID provenance | Medium — could be lost | Mandate docstring preservation (RC-7) |
| Test discovery order | None — pytest collects by function, not file order | No action needed |

### Lane 2: Rename test_remediation_sprints.py

| Impact Area | Risk | Mitigation |
|-------------|------|------------|
| conftest.py | None — no file-specific references | Verified: conftest.py uses fixtures, not file imports |
| pytest markers | None — markers are on functions, not files | No action needed |
| CI configuration | Low — check if any CI scripts reference the exact filename | Grep for "remediation_sprints" in CI configs |

### Lane 3: sys.path DRY Fix

| Impact Area | Risk | Mitigation |
|-------------|------|------------|
| 61 test files modified | Medium — wide blast radius | Automated script approach (RC-9) |
| Import resolution | Medium — must verify pythonpath resolves identically | Test with representative file per pattern (RC-6) |
| conftest.py already does sys.path | Low — conftest.py insert remains for non-pytest invocation | Keep conftest.py sys.path as fallback |

### Lane 4: Perf Utility Extraction

| Impact Area | Risk | Mitigation |
|-------------|------|------------|
| _prepare_input signature differences | Medium — can't naively merge | Extract only common helpers; keep divergent signatures |
| conftest.py growth | Low — additions are small | Alternatively use a `_perf_helpers.py` shared module |

### DRY Initiative Interaction

| DRY Artifact | Interaction | Action |
|-------------|-------------|--------|
| conftest.py (modified by DRY) | Lane 3 keeps conftest.py sys.path intact | No conflict |
| `_sgf_render_utils.py` (created by DRY) | Not touched by any lane | No conflict |
| CLI centralization (DRY scope) | Unrelated to test organization | No conflict |

**Conclusion: Zero conflicts with DRY initiative.**

## sys.path Pattern Analysis

| Pattern Variable | File Count | Path Value |
|-----------------|-----------|------------|
| `_LAB_DIR` | 45 | `Path(__file__).resolve().parent.parent` |
| `_LAB` | 8 | `Path(__file__).resolve().parent.parent` |
| `_lab_root` | 5 | `Path(__file__).resolve().parent.parent` |
| `_TOOLS_ROOT` | 3 | `Path(__file__).resolve().parent.parent.parent` (goes up to tools/) |

**All resolve to the same effective path** — the puzzle-enrichment-lab root. The `_TOOLS_ROOT` variant goes one level higher but is used for cross-tool imports (not applicable after DRY initiative centralized those).

## _prepare_input Signature Comparison (Lane 4)

| File | Signature | Differences |
|------|-----------|-------------|
| test_perf_smoke.py | `_prepare_input(source_dir, dest_dir)` | 2-arg: copies all fixtures |
| test_perf_100.py | `_prepare_input(source_dir, dest_dir, count)` | 3-arg: copies `count` fixtures |
| test_perf_1k.py | `_prepare_input(source_dir, dest_dir)` | 2-arg: same as smoke |
| test_perf_10k.py | `_prepare_input(dest_dir, target)` | 2-arg: different semantics (generates synthetic) |

**Recommendation:** Extract `_get_referee_model()` and `_parse_statuses()` (identical signatures). Keep `_prepare_input` per-file due to semantic differences.
