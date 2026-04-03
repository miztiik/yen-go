# Options — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Context

The initiative needs a live KataGo test architecture that validates technique fixtures across 5 calibration dimensions (correct_move, wrong_moves, difficulty, technique_tags, teaching_comments). Three design patterns exist in the codebase already:

1. **Golden-5 pattern** (`test_golden5.py`): Hand-coded per-puzzle test methods, class-scoped engine
2. **Parametrized structural** (`test_fixture_coverage.py`): `ALL_TAG_FIXTURES` registry + `@pytest.mark.parametrize`
3. **Batch calibration** (`test_calibration.py`): Batch CLI runner, statistical thresholds over collection

The options below cover the **test architecture** for the new technique calibration suite. Fixture sourcing strategy is already decided (grep external-sources for pre-tagged SGFs — see [15-research.md](../20260322-research-external-sources-fixture-sourcing/15-research.md)).

---

## Upstream/Downstream Impact Scan (Pre-Options)

| impact_id | direction | area | risk | mitigation |
|-----------|-----------|------|------|------------|
| I-1 | upstream | config/tags.json (28 tags) | Tag list drift → missing fixtures | Test loads tags.json dynamically as authority |
| I-2 | upstream | analyzers/detectors/ (28 detectors) | Detector behavior change → test flake | Pin expected values to current detector behavior, use tolerances |
| I-3 | upstream | analyzers/enrich_single.py | Pipeline API change → test breakage | Import directly; same module boundary as golden5 |
| I-4 | downstream | test_fixture_coverage.py ALL_TAG_FIXTURES | Fixture renames break existing tests | Atomic update in Phase B (same commit) |
| I-5 | downstream | test_fixture_integrity.py population checks | New extended-benchmark dir needs population rule | Add extended-benchmark to population check |
| I-6 | lateral | benchmark/expert-review.md | Benchmark extensions need review doc update | Add section for extended-benchmark entries |
| I-7 | lateral | AGENTS.md (enrichment lab) | New test file + directory | Update in same commit per CLAUDE.md rule |

---

## Option Comparison

### OPT-1: Golden-5 Extension — Hand-Coded Per-Technique Tests

**Approach**: Extend the `test_golden5.py` pattern. New `test_technique_calibration.py` with a class-scoped `SingleEngineManager`, individual hand-coded test methods per technique group (28 methods). Each method calls `enrich_single_puzzle()` and asserts on all 5 calibration dimensions with technique-specific expected values hardcoded inline.

```python
class TestTechniqueCalibration:
    @pytest.fixture(autouse=True, scope="class")
    def _engine(self): ...  # Same as golden5

    def test_snapback(self):
        result = self._enrich("snapback_puzzle.sgf")
        assert result.validation.correct_move_gtp == "B1"
        assert "snapback" in result.tags
        assert abs(result.difficulty.suggested_level_id - 130) <= 20
        assert len(result.refutations) >= 1
        assert len(result.teaching_comments) >= 1

    def test_throw_in(self): ...
    def test_ladder(self): ...
    # ... 28 total
```

| Criterion | Assessment |
|-----------|------------|
| **Benefits** | Proven pattern in codebase. Per-technique custom assertions (e.g., ko tests can assert YK property). Easy to understand. Full control over edge cases. |
| **Drawbacks** | 28 hand-coded methods = ~700 LOC. Adding/removing fixtures requires code changes. Expected values scattered across methods (hard to audit). |
| **Risks** | Test maintenance burden when expected values change. Large monolithic test file. |
| **Complexity** | Medium — mostly copy-paste from golden5 pattern |
| **Test impact** | 28 slow tests (~2-3 min each × 28 = ~60-90 min total) — needs parallelization or smart engine reuse |
| **Rollback** | Delete one file + revert fixture changes |
| **Architecture compliance** | ✅ Same pattern as golden5, no new abstractions |

---

### OPT-2: Data-Driven Manifest with Parametrized Tests

**Approach**: Each technique fixture has a companion `{name}.expected.json` file containing ground-truth expected values. A single parametrized test class reads all `.expected.json` files and runs assertions generically. Adding/removing techniques = add/remove a JSON file.

```python
# tests/fixtures/snapback_puzzle.expected.json
{
  "correct_move_gtp": "B1",
  "expected_tags": ["snapback"],
  "expected_level_id": 130,
  "level_tolerance": 20,
  "min_refutations": 1,
  "min_teaching_comments": 1
}

# test_technique_calibration.py
@pytest.mark.parametrize("fixture", discover_fixtures())
class TestTechniqueCalibration:
    def test_correct_move(self, fixture):
        assert result.correct_move_gtp == fixture.expected["correct_move_gtp"]
    def test_technique_tags(self, fixture):
        for tag in fixture.expected["expected_tags"]:
            assert tag in result.tags
    # ... 5 dimension tests
```

| Criterion | Assessment |
|-----------|------------|
| **Benefits** | Ground truth is data (JSON), not code. Easy to audit expected values across all fixtures in one grep. Adding fixtures = add SGF + JSON, no code changes. Clean separation of concerns. |
| **Drawbacks** | ~35 extra `.expected.json` files in fixtures/. JSON schema needs definition. Less flexibility for technique-specific assertions (e.g., ko's YK property). |
| **Risks** | JSON schema drift. IDE tooling may not validate JSON expected files. Discovery function could miss files silently. |
| **Complexity** | Medium — new pattern, but simple |
| **Test impact** | Same runtime as OPT-1 (~60-90 min) but parametrize gives individual test IDs for filtering |
| **Rollback** | Delete test file + all .expected.json files |
| **Architecture compliance** | ✅ Data-driven pattern is common in calibration suites. Slight departure from golden5 hand-coded style. |

---

### OPT-3: Python Registry with Parametrized Tests (Recommended)

**Approach**: A single Python dict registry (like `ALL_TAG_FIXTURES` but richer) defines expected values per fixture. Parametrized tests iterate over the registry. All ground truth in one place (the registry), all assertions in one place (the test class). No extra files.

```python
# test_technique_calibration.py
TECHNIQUE_REGISTRY: dict[str, dict] = {
    "snapback": {
        "fixture": "snapback_puzzle.sgf",
        "correct_move_gtp": "B1",
        "expected_tags": ["snapback"],
        "expected_level_id": 130,
        "level_tolerance": 20,
        "min_refutations": 1,
        "min_teaching_comments": 1,
    },
    "throw_in": { ... },
    # ... 28 entries
}

@pytest.mark.parametrize("technique,spec", TECHNIQUE_REGISTRY.items())
class TestTechniqueCalibration:
    @pytest.fixture(autouse=True, scope="class")
    def _engine(self): ...

    def test_correct_move(self, technique, spec):
        result = self._enrich(spec["fixture"])
        assert result.correct_move_gtp == spec["correct_move_gtp"]

    def test_technique_tags(self, technique, spec):
        for tag in spec["expected_tags"]:
            assert tag in result.tags
```

| Criterion | Assessment |
|-----------|------------|
| **Benefits** | All expected values in one auditable registry. Follows `ALL_TAG_FIXTURES` pattern already in codebase. No extra files. Parametrize gives individual test IDs (`test_correct_move[snapback]`). Easy to add/remove by editing registry. Registry can be cross-referenced with config/tags.json dynamically. |
| **Drawbacks** | Large Python dict (~150 LOC for 28 entries). Slightly harder to read than JSON for non-developers. Registry + test logic in same file. |
| **Risks** | Registry staleness — but can be tested against config/tags.json coverage automatically. Parametrize over class may require careful fixture scoping. |
| **Complexity** | Low — combines two existing patterns (ALL_TAG_FIXTURES + golden5 engine) |
| **Test impact** | Same runtime as OPT-1/2. Parametrized IDs allow `pytest -k snapback` for single-technique runs. |
| **Rollback** | Delete one file |
| **Architecture compliance** | ✅ Directly extends existing ALL_TAG_FIXTURES and golden5 patterns. Minimal new abstraction. KISS. |

---

## Comparison Matrix

| criterion_id | Criterion | OPT-1 (Golden-5 Extension) | OPT-2 (Data-Driven JSON) | OPT-3 (Python Registry) |
|---------|-----------|---------------------------|--------------------------|------------------------|
| CMP-1 | Maintenance effort | High (28 methods) | Medium (JSON + code) | Low (1 registry + generic tests) |
| CMP-2 | Auditable ground truth | Poor (scattered in code) | Good (JSON files) | Good (one dict) |
| CMP-3 | Fixture add/remove effort | Code change required | Add/remove JSON file | Edit registry dict |
| CMP-4 | Flexibility for edge cases | Excellent (hand-coded) | Limited (generic only) | Good (registry can have extra fields) |
| CMP-5 | File count impact | 1 file | 1 file + ~35 JSON | 1 file |
| CMP-6 | Pattern familiarity | Matches golden5 | New pattern | Extends ALL_TAG_FIXTURES |
| CMP-7 | Single-technique test run | By method name | By parametrize ID | By parametrize ID |
| CMP-8 | Cross-ref with config/tags.json | Manual | Manual | Automatic (registry key == tag slug) |
| CMP-9 | YAGNI compliance | ✅ | ⚠️ JSON schema overhead | ✅ |
| CMP-10 | KISS compliance | ⚠️ repetitive | ⚠️ two representations | ✅ one source of truth |

## Recommendation

**OPT-3 (Python Registry)** is recommended because:

1. **Follows existing patterns** — combines `ALL_TAG_FIXTURES` registry + `golden5` engine fixture. Zero new abstractions.
2. **Single source of truth** — one dict for expected values, one test class for assertions. DRY.
3. **Minimal file count** — one new file only. YAGNI.
4. **Automatic coverage check** — registry keys can be validated against `config/tags.json` slugs.
5. **Selective execution** — `pytest -k snapback` runs only that technique's 5 assertions.
6. **Easy maintenance** — adding a technique = add one dict entry + one SGF file.

Edge cases (ko YK property, miai move_order) can be handled via optional registry fields that trigger extra assertions when present.

> **See also**:
> - [Charter](./00-charter.md) — Goals and acceptance criteria
> - [Research](../20260322-research-external-sources-fixture-sourcing/15-research.md) — Sourcing strategy
