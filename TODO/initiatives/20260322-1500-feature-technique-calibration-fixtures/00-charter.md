# Charter — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Initiative

| Field | Value |
|-------|-------|
| ID | 20260322-1500-feature-technique-calibration-fixtures |
| Type | Feature |
| Module | tools/puzzle-enrichment-lab |
| Owner | Feature-Planner |

## Problem Statement

The puzzle-enrichment-lab's technique detection pipeline has **35 technique fixtures**, but a 3-expert panel audit found only **34% pass all quality criteria**. Seven fixtures have structural SGF bugs (stones in both AB[] and solution trees), several are mislabeled for technique, and 8 technique categories have no fixture coverage at all. There is no formal definition of what constitutes a "good calibration fixture" and no live KataGo test suite that validates the full pipeline output (correct move, wrong moves, difficulty, technique tags, teaching comments) against ground truth.

### Current State

- 35 technique fixtures in `tests/fixtures/` (12 KEEP, 10 FIX, 7 REMOVE, 2 MERGE, 1 REPLACE, 1 VERIFY, 2 SPLIT per audit)
- 28 technique detectors in `analyzers/detectors/` — many without corresponding calibration fixtures
- Existing test infrastructure:  `test_golden5.py` (5 puzzles, live KataGo), `test_calibration.py` (Cho Chikun difficulty calibration, live KataGo), `test_ai_solve_calibration.py` (structural checks, no live KataGo)
- No test validates technique tag detection accuracy against known-good fixtures
- No formal quality criteria definition

### Target State

- Formally defined quality criteria for calibration fixtures (8 measurable dimensions)
- All 28 technique tags have ≥1 calibration fixture from verified external sources
- Live KataGo test suite validates: correct_move, wrong_moves, difficulty, technique_tags, teaching_comments
- Extended-benchmark directory with multi-difficulty variants for top techniques
- ≥85% fixture pass rate against quality criteria

## Goals

| goal_id | Goal | Measurable Target |
|---------|------|-------------------|
| G-1 | Define calibration quality criteria | 8 formally defined dimensions with measurable thresholds |
| G-2 | Source replacement fixtures from external-sources | Replace 7 REMOVE + 1 REPLACE fixtures; fill 8 technique gaps |
| G-3 | Achieve full technique tag coverage | ≥1 fixture per 28 technique tags |
| G-4 | Create live KataGo calibration test suite | pytest tests covering 5 calibration dimensions (correct_move, wrong_moves, difficulty, technique_tags, teaching_comments) |
| G-5 | Create extended-benchmark directory | ≥3 difficulty variants for top-5 most common techniques |
| G-6 | Improve fixture quality pass rate | From 34% → ≥85% against quality criteria |
| G-7 | Clean up broken fixtures | Delete 7 structurally buggy + 1 mislabeled fixture |

## Non-Goals

| ng_id | Non-Goal | Rationale |
|-------|----------|-----------|
| NG-1 | Fixing structural SGF bugs in existing fixtures | User directive: source replacements, don't fix |
| NG-2 | Mock-based calibration tests | User directive: LIVE KataGo only |
| NG-3 | Modifying benchmark/ existing contents | Benchmark is read-only gold copy |
| NG-4 | Changing the enrichment pipeline itself | Calibration measures existing pipeline, doesn't change it |
| NG-5 | Creating new technique detectors | Out of scope; detectors exist for all 28 tags |
| NG-6 | New external data crawling | Must use existing external-sources |
| NG-7 | Modifying the calibration/ directory (Cho Chikun) | Separate calibration scope — difficulty validation |

## Constraints

| c_id | Constraint | Source |
|------|-----------|--------|
| C-1 | Must use existing external-sources (no new crawling) | User directive |
| C-2 | Benchmark is read-only gold copy — extend only | User directive Q2 |
| C-3 | Domain expert panel arbitrates "best puzzle" selection | User directive |
| C-4 | Tests require KataGo binary + model (skip if missing) | Follows golden5 pattern |
| C-5 | No backward compatibility required for fixture paths | User Q1:B, Q6:B |
| C-6 | Live KataGo execution only — no mocked pipelines | User Q4:B |

## Acceptance Criteria

| ac_id | Criterion | Validation Method |
|-------|-----------|-------------------|
| AC-1 | ≥85% of technique fixtures pass all 8 quality criteria | Quality audit script + manual review |
| AC-2 | All 28 technique tags have ≥1 calibration fixture | Automated coverage check in test |
| AC-3 | Live KataGo tests assert on 5 dimensions: correct_move, wrong_moves, difficulty, technique_tags, teaching_comments | pytest suite passes with live KataGo |
| AC-4 | Extended-benchmark dir has ≥3 difficulty variants for top-5 techniques | Directory listing + fixture audit |
| AC-5 | Zero structural SGF bugs in any fixture | sgfmill parse validation in test |
| AC-6 | Quality criteria formally defined with measurable thresholds | 00-charter.md quality criteria table |
| AC-7 | All 7+1 broken/mislabeled fixtures removed, replaced with sourced alternatives | Diff against current fixture set |

## Correction Level & Phased Execution

**Correction Level: 3** (Multiple files — test files + fixture files + new directory + new test suite)

Per `.claude/rules/01-correction-levels.md`, this requires `Plan Mode → Phased Execution`:

| phase_id | Phase | Scope | Atomicity Rule |
|----------|-------|-------|----------------|
| PH-A | Fixture Sourcing | Grep external-sources, domain expert review, select best-per-technique | No code changes — research & selection only |
| PH-B | Fixture Swap (atomic) | Delete 7+1 broken fixtures, add sourced replacements, update ALL_TAG_FIXTURES in test_fixture_coverage.py and population constants in test_fixture_integrity.py — **same commit** | Single commit: no intermediate broken test state |
| PH-C | Extended Benchmark | Create `extended-benchmark/` directory, populate with multi-difficulty variants | Independent of PH-B — addititive only |
| PH-D | Live KataGo Test Suite | Create new `test_technique_calibration.py` with 5-dimension live assertions | Depends on PH-B (uses new fixtures) |

### Pass-Rate Measurement (AC-1 / G-6)

- **Denominator**: N = final fixture count post-cleanup (expected: ~35 after replacements)
- **Measurement**: A pytest test in `test_fixture_integrity.py` validates each fixture against QC-1 through QC-8, reports pass/fail per fixture, and asserts `pass_count / total >= 0.85`
- **Baseline**: Current 12/35 = 34%. Target: ≥30/35 = 85%+

### Test Migration (Atomic Update Rule)

When fixtures are renamed/deleted (PH-B), the following MUST be updated in the **same commit**:
- `ALL_TAG_FIXTURES` dict in `test_fixture_coverage.py`
- Population constants in `test_fixture_integrity.py`
- Any other test files that import removed fixture paths
- `TECHNIQUE_FIXTURE_AUDIT.md` (mark REMOVE items as completed)

**No intermediate broken state** — `pytest tests/` must pass both before and after the commit.

### Git Safety Acknowledgment

All fixture file operations follow CLAUDE.md git safety rules:
- **Selective staging only**: `git add tests/fixtures/new_fixture.sgf tests/test_fixture_coverage.py` — never `git add .`
- **Pre-commit verification**: `git diff --cached --name-only` to confirm only intended files staged
- **Protected directories**: No operations on `external-sources/` contents (read-only sourcing)

## Calibration Quality Criteria (Proposed)

These 8 dimensions define what makes a "good calibration fixture":

| qc_id | Quality Criterion | Definition | Measurement | Weight |
|-------|------------------|------------|-------------|--------|
| QC-1 | Structural Validity | SGF parses without error; no dual-placement bugs; valid FF[4]/GM[1] | sgfmill parse + custom validator | Critical (gate) |
| QC-2 | Solution Tree Completeness | ≥1 correct branch, ≥1 wrong/refutation branch; no position-only | Branch count from SGF tree walk | Critical (gate) |
| QC-3 | Technique Accuracy | Fixture's labeled technique matches expert consensus (≥2 of 3 experts agree) | Expert panel review | High |
| QC-4 | Technique Purity | Fixture primarily demonstrates ONE technique (not compound) | Expert panel review: secondary technique count ≤1 | Medium |
| QC-5 | Difficulty Calibration | Fixture difficulty appropriate for its labeled level (±1 level tolerance) | KataGo difficulty classifier output vs label | Medium |
| QC-6 | Correct Move Uniqueness | Solution has exactly 1 correct first move (or documented miai) | Solution tree analysis | High |
| QC-7 | Board Clarity | Position is clean enough to isolate technique; not over-cluttered | Expert review; stone count relative to board size | Low |
| QC-8 | KataGo Tractability | KataGo can solve within T2 budget (2000 visits); not pathological | Live KataGo test timing | Medium |

**Gate criteria** (QC-1, QC-2): Fixtures failing these are automatically rejected.

## Calibration Dimensions (Test Assertion Targets)

Per user Q3:D, each fixture's live KataGo test validates:

| cd_id | Dimension | Assertion Type | Example |
|-------|-----------|---------------|---------|
| CD-1 | Correct Move | KataGo's top move matches SGF correct move | `assert result.correct_move == "cc"` |
| CD-2 | Wrong Moves | KataGo refutation analysis identifies ≥1 known wrong move | `assert "cd" in result.refutation_moves` |
| CD-3 | Difficulty Level | Suggested level within ±1 of fixture's labeled level | `assert abs(result.level_id - expected) <= 10` |
| CD-4 | Technique Tags | Primary technique tag appears in result tag set | `assert "snapback" in result.tags` |
| CD-5 | Teaching Comments | At least 1 non-empty teaching comment generated | `assert len(result.teaching_comments) >= 1` |

## Research Summary

External-sources inventory completed (see [15-research.md](../20260322-research-external-sources-fixture-sourcing/15-research.md)):

- **16 collections** inventoried, 4 graded A/A+ (goproblems, goproblems_difficulty_based, ogs, kisvadim)
- **Recommended sourcing strategy**: Grep `goproblems/` + `ogs/` for pre-tagged technique SGFs (covers ~6/8 gaps)
- **Post-research confidence**: 75 (medium risk — sourcing resolved, test architecture remains)

> **See also**:
> - [Clarifications](./10-clarifications.md) — User decisions and directives
> - [Research](../20260322-research-external-sources-fixture-sourcing/15-research.md) — External sources inventory
> - [Audit](../../tools/puzzle-enrichment-lab/tests/fixtures/TECHNIQUE_FIXTURE_AUDIT.md) — 3-expert fixture review
