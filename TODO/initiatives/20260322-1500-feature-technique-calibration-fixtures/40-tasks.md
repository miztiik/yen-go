# Tasks — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Overview

Selected option: **OPT-3 (Python Registry + Parametrized Tests)**
Correction level: **3** (Multiple files — phased execution)
Phases: PH-A (Sourcing) → PH-B (Fixture Swap) → PH-C (Extended Benchmark) → PH-D (Live Test Suite)

---

## Phase A: Fixture Sourcing (Research + Selection)

| task_id | Task | Files | Depends On | Parallel |
|---------|------|-------|------------|----------|
| T1 | **Grep external-sources for pre-tagged technique SGFs** — Run `grep -rl "YT\[snapback\]"` (and similar for each gap technique including **living** per C4) across `external-sources/goproblems/sgf/` and `external-sources/ogs/sgf/`. Collect candidate lists. Gap techniques: living, connection, shape, tesuji, capture-race variants, semeai, squeeze, carpenter's-square. | `external-sources/goproblems/sgf/**`, `external-sources/ogs/sgf/**` | — | [P] with T2 |
| T2 | **Grep goproblems_difficulty_based for technique-specific puzzles** — Search `external-sources/goproblems_difficulty_based/` by technique directory (life_and_death/, tesuji/) for candidates stratified by difficulty. | `external-sources/goproblems_difficulty_based/**` | — | [P] with T1 |
| T3 | **Render candidate SGFs as ASCII for domain expert review** — For each of the 8 gap techniques, render top 3 candidates (by solution tree depth) as ASCII boards. Assess technique accuracy, difficulty, quality. | Temp rendering script | T1, T2 | |
| T4 | **Domain expert panel selects best-per-technique** — For each gap technique, review candidates and select: (a) 1 best for fixtures/, (b) 2-3 difficulty variants for extended-benchmark/. Record selection rationale. | Selection log | T3 | |
| T5 | **Select replacement fixtures for 7 REMOVE'd puzzles** — For connection, endgame, fuseki, joseki, shape, simple_life_death, tesuji: identify if a technique fixture is NEEDED (some tags may be covered by other fixtures). Source replacements where needed. | External sources | T1, T2 | |
| T6 | **Select replacement for cutting.sgf (REPLACE)** — Source a game-realistic cutting-point puzzle from goproblems/ogs to replace the lab-construct #7. | External sources | T1 | |

## Phase B: Fixture Swap (Atomic Commit)

**CRITICAL**: All tasks in Phase B must land in a **single commit**. No intermediate broken state.

| task_id | Task | Files | Depends On | Parallel |
|---------|------|-------|------------|----------|
| T7 | **Delete 5 REMOVE fixtures** — Remove: connection_puzzle.sgf, endgame.sgf, fuseki.sgf, joseki.sgf, shape.sgf. **Keep simple_life_death.sgf and tesuji.sgf on disk** (golden5 depends on them — see C1/C6). Replace their contents in-place with quality sourced replacements in T8.1. | `tests/fixtures/` (5 files deleted) | T5 | [P] with T8, T9 |
| T8 | **Add sourced replacement fixtures** — Copy selected SGFs from external-sources, normalize metadata (FF[4], GM[1], SZ, YT tags). Add to `tests/fixtures/`. | `tests/fixtures/` (~8 new files) | T4, T5, T6 | [P] with T7, T9 |
| T9 | **Add cutting replacement** — Replace cutting.sgf with sourced game-realistic alternative. | `tests/fixtures/cutting.sgf` | T6 | [P] with T7, T8 |
| T8.1 | **Replace-in-place for golden5 fixtures (C1/C6)** — Replace simple_life_death.sgf content with a properly tagged L&D puzzle (preserving filename). Replace tesuji.sgf content with a specific tesuji (e.g., sacrifice variant). Update board_size in GOLDEN5_PUZZLES dict if board size changes. **Same atomic commit as T7-T9.** | `tests/fixtures/simple_life_death.sgf`, `tests/fixtures/tesuji.sgf`, `tests/test_golden5.py` | T4, T5 | [P] with T7, T8, T9 |
| T10 | **Update ALL_TAG_FIXTURES + fix miai→living (C3)** — Remove entries for deleted fixtures, add entries for new fixtures. Fix stale mapping: change ALL_KNOWN_TAG_SLUGS 'miai' to 'living' (ID 14). Fix ALL_TAG_FIXTURES miai entries. Ensure coverage for all 25 tsumego tags. | `tests/test_fixture_coverage.py` | T7, T8, T8.1, T9 | |
| T11 | **Update test_fixture_integrity.py** — Add extended-benchmark to population check if needed. Update any fixture count constants. | `tests/test_fixture_integrity.py` | T8 | [P] with T10 |
| T12 | **Verify pytest tests/ passes** — Run `pytest tests/ -m unit -q --no-header --tb=short` to confirm no broken references. | — | T10, T11 | |
| T13 | **Update TECHNIQUE_FIXTURE_AUDIT.md** — Mark REMOVE items as completed, update REPLACE status. | `tests/fixtures/TECHNIQUE_FIXTURE_AUDIT.md` | T7, T8, T9 | |

## Phase C: Extended Benchmark (Additive)

| task_id | Task | Files | Depends On | Parallel |
|---------|------|-------|------------|----------|
| T14 | **Create extended-benchmark/ directory** — Create `tests/fixtures/extended-benchmark/` with README.md documenting purpose, provenance, selection criteria. | `tests/fixtures/extended-benchmark/README.md` | — | [P] with T15 |
| T15 | **Populate with difficulty variants** — For top-5 techniques (life-and-death, ko, snapback, ladder, nakade), add ≥3 difficulty variants (elem/int/adv) from external-sources. Normalize metadata. | `tests/fixtures/extended-benchmark/*.sgf` (~15 files) | T4 | [P] with T14 |
| T16 | **Add extended-benchmark to fixture integrity tests** — Update test_fixture_integrity.py to include extended-benchmark in population check. | `tests/test_fixture_integrity.py` | T14, T15 | |

## Phase D: Live KataGo Test Suite

| task_id | Task | Files | Depends On | Parallel |
|---------|------|-------|------------|----------|
| T17 | **Create test_technique_calibration.py with TechniqueSpec TypedDict (C2/C3)** — Define the TechniqueSpec type and module-level TECHNIQUE_REGISTRY dict with 25 active entries + EXCLUDED_NON_TSUMEGO_TAGS = {'joseki', 'fuseki', 'endgame'} (C2). Use 'living' (ID 14) not 'miai' for tag slug (C3). Mark audit-pending fixtures as skip per MH-5. | `tests/test_technique_calibration.py` | T10 (need final fixture names) | |
| T18 | **Implement class-scoped engine fixture** — Copy golden5 pattern: class-scoped SingleEngineManager in quick_only mode, _enrich() helper. Add @pytest.mark.slow + @pytest.mark.integration markers (MH-4). | `tests/test_technique_calibration.py` | T17 | |
| T19 | **Implement 5 parametrized calibration tests** — test_correct_move, test_technique_tags, test_difficulty_range, test_refutations, test_teaching_comments. Each parametrized over TECHNIQUE_REGISTRY. | `tests/test_technique_calibration.py` | T18 | |
| T20 | **Implement config/tags.json cross-check test (C2)** — Unit test (MH-3) that loads config/tags.json, subtracts EXCLUDED_NON_TSUMEGO_TAGS, and asserts every remaining tag slug has a TECHNIQUE_REGISTRY entry. Mark as @pytest.mark.unit. | `tests/test_technique_calibration.py` | T17 | [P] with T18, T19 |
| T21 | **Populate registry expected values** — For each of the 28 techniques, determine correct_move_gtp, expected difficulty range, expected refutations from fixture SGF analysis and audit data. | `tests/test_technique_calibration.py` | T19 | |
| T22 | **Run live KataGo validation** — Execute `pytest tests/test_technique_calibration.py -v --tb=short` with live KataGo. Verify ≥85% of non-skipped tests pass. Adjust tolerances as needed. | — | T21 | |

## Phase E: Documentation and Cleanup

| task_id | Task | Files | Depends On | Parallel |
|---------|------|-------|------------|----------|
| T23 | **Update AGENTS.md** — Add test_technique_calibration.py, extended-benchmark/ directory, and TECHNIQUE_REGISTRY pattern description. | `tools/puzzle-enrichment-lab/AGENTS.md` | T19 | [P] with T24 |
| T24 | **Delete _render_all_techniques.py temp script** — Clean up the temporary rendering script created during the audit. | `tools/puzzle-enrichment-lab/_render_all_techniques.py` | — | [P] with T23 |
| T25 | **Final regression test** — Run full enrichment lab test suite: `pytest tests/ -m "not slow" --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -q --no-header --tb=short` | — | T22, T23 | |

---

## Dependency Graph

```
T1 ──┐
T2 ──┼──→ T3 ──→ T4 ──→ T5 ──→ T7 ──┐
     │                   T6 ──→ T9 ──┤
     │                                ├──→ T10 ──→ T12 ──→ T17 ──→ T18 ──→ T19 ──→ T21 ──→ T22 ──→ T25
     │                                ├──→ T11 ──┘        T20 [P]──┘
     │                                ├──→ T8 ──┘
     │                                └──→ T13
     │
     └──→ T4 ──→ T15 ──→ T16
               T14 [P]──┘

T23 [P] with T24 ──→ T25
```

## Task Summary

| Phase | Tasks | Parallel-safe | Key files changed |
|-------|------:|:---:|---|
| PH-A (Sourcing) | T1–T6 | T1∥T2 | External sources (read-only) |
| PH-B (Swap) | T7–T13 | T7∥T8∥T9 | tests/fixtures/*.sgf, test_fixture_coverage.py, test_fixture_integrity.py |
| PH-C (Extended BM) | T14–T16 | T14∥T15 | tests/fixtures/extended-benchmark/ |
| PH-D (Test Suite) | T17–T22 | T20∥T18∥T19 | tests/test_technique_calibration.py |
| PH-E (Docs/Cleanup) | T23–T25 | T23∥T24 | AGENTS.md, temp script |
| **Total** | **25** | | |

> **See also**:
> - [Plan](./30-plan.md) — Architecture decisions and registry structure
> - [Charter](./00-charter.md) — Acceptance criteria mapping
> - [Analysis](./20-analysis.md) — Task coverage verification
