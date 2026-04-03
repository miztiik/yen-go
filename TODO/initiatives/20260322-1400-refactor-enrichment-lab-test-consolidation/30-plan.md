# Plan — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Execution Order

```
Lane 2 (trivial rename) → Lane 3 (sys.path DRY fix) → Lane 1 (sprint migration) → Lane 4 (perf helpers)
```

**Rationale:** L2 is trivial and unblocked. L3 creates a clean import base before L1 migration. L1 is the core work. L4 is optional polish.

---

## Lane 2: Rename test_remediation_sprints.py (Level 0)

**Single atomic operation:**
- Rename `test_remediation_sprints.py` → `test_ai_solve_remediation.py`
- Update any imports or references to the old filename
- Verify: `pytest --co -q` count unchanged

---

## Lane 3: Fix sys.path DRY Violation (Level 2)

**Phase 3a: Verify pythonpath approach**
1. Add `pythonpath = ["."]` to `tools/puzzle-enrichment-lab/pyproject.toml` under `[tool.pytest.ini_options]`
2. Remove `sys.path.insert` from ONE representative file per pattern:
   - `_LAB_DIR` pattern (45 files) — test one
   - `_LAB` pattern (8 files) — test one
   - `_lab_root` pattern (5 files) — test one
   - `_TOOLS_ROOT` pattern (3 files) — test one
3. Run `pytest tests/ -m "not slow" -q` — confirm green

**Phase 3b: Automated removal**
1. Script to remove the `sys.path.insert` boilerplate block from all test files
2. Pattern to remove (4-line block):
   ```python
   _LAB_DIR = Path(__file__).resolve().parent.parent
   if str(_LAB_DIR) not in sys.path:
       sys.path.insert(0, str(_LAB_DIR))
   ```
3. Also remove unused `import sys` and `from pathlib import Path` where they become orphaned
4. Verify: `pytest --co -q` count unchanged; `pytest tests/ -m "not slow" -q` green

---

## Lane 1: Sprint File Domain Migration (Level 3)

**5 atomic commits, one per sprint file.**

### Migration Mapping Table

#### Commit 1: test_sprint1_fixes.py → 6 target files

| Test Class | Functions | Target File | Rationale |
|-----------|-----------|-------------|-----------|
| TestTreeValidationSortByVisits | 1 | test_ai_analysis_result.py | Tests MoveAnalysis sorting — belongs with analysis models |
| TestThrowInAllEdges | 10 | test_technique_classifier.py | Tests `_detect_throw_in` — dedicated classifier file |
| TestDifficultyWeightsValidation | 4 | test_difficulty.py | Config validation for difficulty model |
| TestYxUFieldSemantics | 5 | test_sgf_enricher.py | Tests `_build_yx` — enricher output |
| TestDifficultyEstimateRename | 1 | test_ai_analysis_result.py | Model import verification |
| TestCompareResultsCorrectMove | 1 | test_single_engine.py | Tests SingleEngineManager |

#### Commit 2: test_sprint2_fixes.py → 3 target files

| Test Class | Functions | Target File | Rationale |
|-----------|-----------|-------------|-----------|
| TestGtpToSgfTokenBoardSize | 14 | test_hint_generator.py | Coordinate conversion is hint generator logic |
| TestGenerateHintsBoardSize | 3 | test_hint_generator.py | Public API of hint generator |
| TestSmallBoardFixtures | 6 | test_sgf_parser.py | SGF parsing fixture validation |
| TestStoneGtpCoordAudit | 4 | test_complexity_metric.py | Stone model coordinates (no dedicated file) |

#### Commit 3: test_sprint3_fixes.py → 3 target files

| Test Class | Functions | Target File | Rationale |
|-----------|-----------|-------------|-----------|
| TestRefutationPvCap | 4 | test_enrichment_config.py | Config loading validation |
| TestDynamicRefutationColors | 3 | test_sgf_enricher.py | Refutation branch coloring in enricher |
| TestEngineModelCheck | 3 | test_engine_client.py | Engine startup preflight |

#### Commit 4: test_sprint4_fixes.py → 1 target file

| Test Class | Functions | Target File | Rationale |
|-----------|-----------|-------------|-----------|
| TestStructuralWeightsFromConfig | 4 | test_difficulty.py | Difficulty weighting formula |

#### Commit 5: test_sprint5_fixes.py → 2 target files

| Test Class | Functions | Target File | Rationale |
|-----------|-----------|-------------|-----------|
| TestPerRunLogFiles | 2 | test_log_config.py | Log configuration tests |
| TestKatagoBatchConfig | 1 | test_engine_health.py | Engine resource constraints |
| TestKatagoLogDirOverride | 1 | test_engine_client.py | Engine config override |

### Migration Rules (Per RC-7, RC-8)

1. **Docstring preservation:** Each test class keeps its original docstring including gap ID (P0.1, G2, etc.)
2. **Zero assertion changes:** Only import paths and file location change
3. **Import adjustment:** Update `from` paths if sys.path boilerplate was the resolution mechanism (will be already fixed by Lane 3)
4. **Append position:** New classes appended at end of target file
5. **Verification per commit:** `pytest --co -q` count matches baseline; target file tests pass

---

## Lane 4: Perf Utility Extraction (Level 2)

**Extract shared utilities from perf test files:**

1. Create `tests/_perf_helpers.py` (or add to conftest.py) with:
   - `_get_referee_model()` — identical across 4 files
   - `_parse_statuses()` — identical across 2 files
2. Keep `_prepare_input()` per-file (signatures differ — see analysis)
3. Update perf test files to import from shared location
4. Verify: `pytest tests/ -m slow --co -q` shows same test count

---

## Verification Protocol

| Step | Command | Expected |
|------|---------|----------|
| Baseline | `pytest tests/ --co -q 2>&1 \| tail -1` | Record test count |
| After each lane | Same command | Count matches baseline |
| Final | `pytest tests/ -m "not slow" -q --no-header --tb=short` | All green |
| sys.path audit | `grep -r "sys.path.insert" tests/ \| grep -v conftest` | Empty |
| Sprint audit | `ls tests/test_sprint*.py` | No results |
