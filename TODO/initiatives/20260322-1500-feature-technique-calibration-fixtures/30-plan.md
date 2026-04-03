# Plan — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Selected Option

**OPT-3: Python Registry + Parametrized Tests** — approved by Governance Panel with 7 must-hold constraints.

---

## Architecture Decisions

### AD-1: Test File Structure

New file: `tools/puzzle-enrichment-lab/tests/test_technique_calibration.py`

```
tests/
├── test_technique_calibration.py  ← NEW (OPT-3: registry + parametrized tests)
├── test_fixture_coverage.py       ← UPDATE (remove REMOVE'd fixtures from ALL_TAG_FIXTURES)
├── test_fixture_integrity.py      ← UPDATE (add extended-benchmark to population check)
├── test_golden5.py                ← UNCHANGED (different purpose: 5 deep integration tests)
├── test_calibration.py            ← UNCHANGED (Cho Chikun difficulty calibration)
├── fixtures/
│   ├── benchmark/                 ← READ-ONLY (gold copy)
│   ├── extended-benchmark/        ← NEW (multi-difficulty variants)
│   ├── calibration/               ← UNCHANGED (Cho Chikun cho-*)
│   ├── *.sgf                      ← MODIFIED (delete 7 REMOVE, add sourced replacements)
│   └── TECHNIQUE_FIXTURE_AUDIT.md ← UPDATE (mark completed actions)
```

### AD-2: Registry Dict Structure (MH-1, MH-6, MH-7)

Module-level dict keyed by technique slug (matches config/tags.json). All 5 calibration dimensions are required fields. Edge-case fields are optional with defaults.

```python
from typing import TypedDict, NotRequired

class TechniqueSpec(TypedDict):
    """Ground truth for a single technique calibration fixture."""
    # Required (MH-1: all 5 calibration dimensions)
    fixture: str                        # filename in tests/fixtures/
    correct_move_gtp: str               # expected correct first move (GTP format)
    expected_tags: list[str]            # MH-2: list, not single value
    min_level_id: int                   # lower bound of acceptable difficulty
    max_level_id: int                   # upper bound of acceptable difficulty
    min_refutations: int                # minimum wrong-move refutations expected
    expect_teaching_comments: bool      # CD-5: at least 1 teaching comment

    # Optional edge-case fields (MH-6: defaults when absent)
    ko_context: NotRequired[str]        # "none" | "direct" | "approach" — ko fixtures
    move_order: NotRequired[str]        # "strict" | "flexible" | "miai"
    board_size: NotRequired[int]        # default 19
    notes: NotRequired[str]             # human-readable audit notes

TECHNIQUE_REGISTRY: dict[str, TechniqueSpec] = { ... }  # 28 entries at module level (MH-7)
```

### AD-3: Parametrized Test Class

```python
@pytest.mark.slow
@pytest.mark.integration               # MH-4
class TestTechniqueCalibration:
    @pytest.fixture(autouse=True, scope="class")
    def _engine(self): ...              # Same pattern as golden5

    def _enrich(self, fixture_name) -> AiAnalysisResult:
        ...                             # Same pattern as golden5

    @pytest.mark.parametrize("slug,spec", TECHNIQUE_REGISTRY.items())
    def test_correct_move(self, slug, spec):
        result = self._enrich(spec["fixture"])
        assert result.validation.correct_move_gtp == spec["correct_move_gtp"]

    @pytest.mark.parametrize("slug,spec", TECHNIQUE_REGISTRY.items())
    def test_technique_tags(self, slug, spec):
        for tag in spec["expected_tags"]:   # MH-2: subset check
            assert tag in result.tags

    @pytest.mark.parametrize("slug,spec", TECHNIQUE_REGISTRY.items())
    def test_difficulty_range(self, slug, spec):
        level_id = result.difficulty.suggested_level_id
        assert spec["min_level_id"] <= level_id <= spec["max_level_id"]

    @pytest.mark.parametrize("slug,spec", TECHNIQUE_REGISTRY.items())
    def test_refutations(self, slug, spec):
        assert len(result.refutations) >= spec["min_refutations"]

    @pytest.mark.parametrize("slug,spec", TECHNIQUE_REGISTRY.items())
    def test_teaching_comments(self, slug, spec):
        if spec["expect_teaching_comments"]:
            assert len(result.teaching_comments) >= 1
```

### AD-4: Coverage Cross-Check (MH-3)

Separate unit test (fast, no KataGo) validates registry completeness:

```python
@pytest.mark.unit
def test_all_tags_have_registry_entry():
    """Every tag in config/tags.json must have a TECHNIQUE_REGISTRY entry."""
    tags = load_tags_from_config()  # reads config/tags.json
    for tag_slug in tags:
        assert tag_slug in TECHNIQUE_REGISTRY, f"Missing registry entry for tag: {tag_slug}"
```

### AD-5: Audit-Pending Fixture Handling (MH-5)

Fixtures marked REMOVE/REPLACE in the audit are excluded from the registry. During the transition period, skip markers are used:

```python
"connection": pytest.param(
    {"fixture": "connection_puzzle.sgf", ...},
    marks=pytest.mark.skip(reason="AUDIT: REMOVE — trivially obvious, zero calibration value"),
),
```

### AD-6: Extended Benchmark Directory

New directory: `tests/fixtures/extended-benchmark/`

Purpose: Multi-difficulty variants for top techniques (e.g., snapback-elementary, snapback-intermediate, snapback-advanced). Structured as:

```
extended-benchmark/
├── README.md           # Purpose, provenance, selection criteria
├── snapback-elem.sgf
├── snapback-int.sgf
├── snapback-adv.sgf
├── ko-elem.sgf
├── ko-int.sgf
├── ko-adv.sgf
└── ...
```

These are NOT covered by the technique calibration test suite (which is 1-per-tag). They serve as a pool for future statistical calibration and are validated separately by `test_fixture_integrity.py`.

---

## Data Model Impact

| Component | Change | Risk |
|-----------|--------|------|
| `ALL_TAG_FIXTURES` in test_fixture_coverage.py | Remove 7 REMOVE'd entries, update renamed entries | Low — same-commit atomic update |
| tests/fixtures/*.sgf | Delete 7 files, add ~8 sourced replacements | Low — replacements pre-validated |
| tests/fixtures/extended-benchmark/ | New directory with ~15 SGFs | None — additive only |
| tests/test_technique_calibration.py | New file (~300 LOC) | None — new file |
| AGENTS.md | Add test_technique_calibration.py entry | None — doc update |

---

## Risks and Mitigations

| risk_id | Risk | Severity | Probability | Mitigation |
|---------|------|----------|-------------|------------|
| R-1 | Sourced fixtures from external-sources may not have expected technique | Medium | Low | Run through enrichment pipeline first to verify tag detection before adding to registry |
| R-2 | Live KataGo test runtime too long (28 × 2-3 min = ~60-90 min) | Medium | Medium | Class-scoped engine (start once), quick_only mode, small model (b10c128). Can parallelize with pytest-xdist. |
| R-3 | test_fixture_coverage.py breaks between REMOVE and REPLACE | High | High | Atomic commit: delete + add + update ALL_TAG_FIXTURES in same commit (PH-B) |
| R-4 | Registry expected values stale after pipeline changes | Medium | Low | Coverage cross-check (MH-3) catches missing tags. Tolerance ranges absorb minor difficulty drift. |
| R-5 | Extended-benchmark SGFs from different sources have inconsistent metadata | Low | Medium | Normalize all sourced SGFs (FF[4], GM[1], SZ, YT tags) before adding |

---

## Documentation Plan

### Files to Update

| doc_id | File | Why |
|--------|------|-----|
| DOC-1 | `tools/puzzle-enrichment-lab/AGENTS.md` | Add test_technique_calibration.py, extended-benchmark/ directory |
| DOC-2 | `tests/fixtures/TECHNIQUE_FIXTURE_AUDIT.md` | Mark completed remediation actions |
| DOC-3 | `tests/fixtures/extended-benchmark/README.md` | Document purpose, provenance, selection criteria |

### Files to Create

| doc_id | File | Why |
|--------|------|-----|
| DOC-4 | `tests/fixtures/extended-benchmark/README.md` | New directory needs documentation |

### Cross-References

- [Charter](./00-charter.md) — Quality criteria definitions (QC-1 through QC-8)
- [Research](../20260322-research-external-sources-fixture-sourcing/15-research.md) — Sourcing strategy per technique
- [Audit](../../tools/puzzle-enrichment-lab/tests/fixtures/TECHNIQUE_FIXTURE_AUDIT.md) — Expert panel assessment

> **See also**:
> - [Options](./25-options.md) — OPT-3 selection rationale
> - [Tasks](./40-tasks.md) — Implementation task decomposition
> - [Analysis](./20-analysis.md) — Cross-artifact consistency check
