# Analysis — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 85/100 |
| Risk Level | low |
| Research Invoked | No |
| Deductions | -10 (tool design alternatives), -5 (technique tag coverage verification) |

---

## Cross-Artifact Consistency

| check_id | check | charter | options | plan | tasks | result |
|-----------|-------|---------|---------|------|-------|--------|
| CC-1 | Goals → Tasks traceability | G-1 through G-7 | OPT-1 | D-1 through D-6 | T1-T23 | ✅ All goals mapped |
| CC-2 | AC → Test tasks traceability | AC-1 through AC-8 | — | D-4 | T16-T20 | ✅ All ACs have test tasks |
| CC-3 | Constraints → Plan satisfaction | C-1 through C-7 | — | Constraints table | — | ✅ All constraints addressed |
| CC-4 | Must-hold → Plan satisfaction | MH-1 through MH-5 | — | Must-hold table | — | ✅ All must-holds addressed |
| CC-5 | RC-1 (technique tags) → Tasks | — | Resolved in 25-options | — | T14 validates | ✅ Resolved |
| CC-6 | RC-2 (forward refs) → Charter | — | — | — | — | ✅ Already resolved |
| CC-7 | Option OPT-1 → Plan consistency | — | Two standalone scripts | D-1, architecture diagram | T1-T4 | ✅ Plan implements OPT-1 |
| CC-8 | labels.json schema → Multi-dim (C-5) | C-5 | OPT-1 schema | D-2 | T9-T13 | ✅ instinct + technique + objective |

### Goal → Task Traceability

| goal_id | description | task_ids |
|---------|-------------|----------|
| G-1 | Instinct calibration set (~120 puzzles) | T5, T6, T7, T8, T14 |
| G-2 | Puzzle search tool | T1, T2 |
| G-3 | Puzzle copy-and-rename tool | T3, T4 |
| G-4 | Labels schema | T5, T9 |
| G-5 | Instinct labeling | T9, T10, T11, T12, T13 |
| G-6 | Calibration validation | T15, T16, T17, T18, T19, T20 |
| G-7 | Tobi verification | T10 |

### AC → Test Traceability

| ac_id | criterion | test_task | threshold |
|-------|-----------|-----------|-----------|
| AC-1 | Macro instinct accuracy | T16 | ≥70% |
| AC-2 | Per-instinct accuracy | T17 | ≥60% each |
| AC-3 | HIGH-tier precision | T18 | ≥85% |
| AC-4 | Null false-positive | T19 | 0% |
| AC-5 | Minimum puzzle count | T14 | ≥120 |
| AC-6 | Technique coverage | T14 | ≥5 per top 10 tag |
| AC-7 | Search tool functional | T2 | Tests pass |
| AC-8 | Copy tool functional | T4 | Tests pass |

---

## Coverage Map

### Unmapped Tasks

None. All 23 tasks trace to at least one goal or acceptance criterion.

### Unmapped Goals

None. All 7 goals have at least one implementing task.

### Unmapped Acceptance Criteria

None. All 8 ACs have at least one validating task.

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RI-1 | upstream | `tools.core.sgf_parser` — both search/copy tools depend on it | Low — stable, tested module | Use existing parse_sgf() API unchanged | T1, T3 | ✅ addressed |
| RI-2 | upstream | `tools.core.paths` — path resolution | Low — stable utility | Use existing get_project_root() API unchanged | T1, T3 | ✅ addressed |
| RI-3 | upstream | `analyzers/instinct_classifier.py` — calibration tests import classify_instinct() | Low — Phase 1 changes already committed and tested | Import and call existing API | T16-T19 | ✅ addressed |
| RI-4 | upstream | `analyzers/ascii_board.py` — expert labeling uses render_sgf_ascii() | Low — stable, tested | Read-only usage for visual review | T10-T13 | ✅ addressed |
| RI-5 | downstream | `test_instinct_calibration.py` — existing test file modified | Low — currently has skip markers, no active assertions | Extend, don't replace; existing golden_labels fixture untouched | T15 | ✅ addressed |
| RI-6 | downstream | `InstinctConfig.enabled` gate — if calibration passes, someone flips flag | Low — out of scope (NG-1) | Charter explicitly marks as separate 1-line change | — | ✅ addressed (out of scope) |
| RI-7 | lateral | `tests/fixtures/golden-calibration/` — existing fixture | None — Q9:A explicitly keeps it untouched | New directory `instinct-calibration/` is separate | T5 | ✅ addressed |
| RI-8 | lateral | `tests/fixtures/benchmark/` — existing benchmark fixtures | None — completely independent | No shared naming or structure | — | ✅ addressed |
| RI-9 | lateral | `external-sources/` — puzzle source directories | None — read-only access (C-2) | Tools only read, copies go to fixture dir | T6-T8 | ✅ addressed |
| RI-10 | lateral | `config/tags.json` — technique tag definitions | None — read-only reference for AC-6 tag list | Tags verified in RC-1, no modifications | T14 | ✅ addressed |

---

## Findings

| finding_id | severity | description | recommendation | related_tasks |
|------------|----------|-------------|----------------|---------------|
| F-1 | info | Existing `test_instinct_calibration.py` points at `golden-calibration/` which has no instinct labels. New tests point at `instinct-calibration/`. Both coexist. | Keep parallel — golden-calibration may get instinct labels in future | T15 |
| F-2 | info | Sakata Eio directory has 110 SGF files (not 107 as initially estimated). Three files have variant suffixes (01A, 04A, 06A in Hane set). | Include all variants — minor count adjustment | T6 |
| F-3 | low | Lee Changho "FIGHTING AND CAPTURING" chapter filenames are not technique-labeled. Expert must examine each puzzle individually. | Expected — manual labeling is the charter design (C-6) | T13 |
| F-4 | low | `tools/core/tests/` directory currently exists but needs verification for test runner discovery. | Ensure `conftest.py` or pytest path configuration picks up new test files | T2, T4 |
| F-5 | info | Classifier may score below 70% (R-4). This is a calibration measurement, not a failure. Initiative succeeds by producing the golden set regardless of classifier accuracy. | Document results objectively; classifier improvements are a follow-up | T20 |
| F-6 | info | The `--dry-run` flag on `puzzle_search.py` is functionally identical to normal mode since search is read-only. Including it per MH-1 for interface consistency is still correct. | Add `--dry-run` flag that prints a note and runs normally | T1 |

---

## Quality Strategy

### TDD Approach

| phase | test-first? | rationale |
|-------|-------------|-----------|
| Phase 1 (Tools) | Yes | Write test_puzzle_search and test_puzzle_copy_rename first, then implement |
| Phase 2 (Fixtures) | No | File copy operations — verified by file existence checks |
| Phase 3 (Labeling) | No | Manual expert labeling — validated by T14 coverage check |
| Phase 4 (Calibration) | Yes | Write AC test stubs in T15, then implement assertion logic in T16-T19 |

### Validation Matrix

| validation_id | what | how | when |
|---------------|------|-----|------|
| V-1 | Tool tests pass | `pytest tools/core/tests/test_puzzle_search.py test_puzzle_copy_rename.py` | After T2, T4 |
| V-2 | Fixture files exist | `ls tests/fixtures/instinct-calibration/*.sgf | wc -l` ≥ 120 | After T8 |
| V-3 | Labels complete | `jq '.puzzles | length' labels.json` ≥ 120 | After T14 |
| V-4 | Calibration tests executable | `pytest test_instinct_calibration.py -k instinct` (may fail on accuracy, but runs) | After T19 |
| V-5 | Enrichment regression | `pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" --ignore=...` green | After T20 |
| V-6 | Backend unit regression | `pytest backend/ -m unit -q` green | After T20 |

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope and acceptance criteria
> - [30-plan.md](./30-plan.md) — Architecture decisions
> - [40-tasks.md](./40-tasks.md) — Task breakdown
