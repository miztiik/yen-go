# Analysis: Tsumego Frame Flood-Fill Rewrite (OPT-3)

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Last Updated**: 2026-03-12

---

## 1. Planning Context

| Metric | Value |
|--------|-------|
| `planning_confidence_score_pre` | 55 |
| `planning_confidence_score_post` | 88 |
| `risk_level` | low |
| `research_invoked` | true |
| `research_trigger` | Score < 70, two+ viable approaches with unknown tradeoffs |

---

## 2. Consistency Checks

| finding_id | artifact | check | result | notes |
|------------|----------|-------|--------|-------|
| F1 | charter ↔ options | All 6 charter goals mapped to options | ✅ pass | OPT-3 meets G1-G6 |
| F2 | options ↔ plan | Selected option (OPT-3) drives plan | ✅ pass | Plan §1 matches OPT-3 description |
| F3 | plan ↔ tasks | Every plan section has corresponding task(s) | ✅ pass | T1-T13 cover all plan sections |
| F4 | charter AC ↔ tasks | AC1-AC10 mapped to tasks | ✅ pass | See coverage map §3 |
| F5 | governance MH ↔ tasks | MH-1 through MH-6 mapped to tasks | ✅ pass | See coverage map §3 |
| F6 | clarifications ↔ plan | Q1-Q8 decisions reflected in plan | ✅ pass | Q3→score-neutral (T5), Q5→validation (T9-T10), Q6→removal (T5-T6), Q7→delete scan (T8), Q8→both tests (T11) |
| F7 | research ↔ plan | Research recommendations R-20 through R-24 traced to tasks | ✅ pass | R-20→T2, R-21→T7-T8, R-22→T8, R-23→T7, R-24→T8 multi-seed fallback |
| F8 | status.json ↔ artifacts | Phase state matches reality | ✅ pass | `options: approved`, `plan: in_progress` |

---

## 3. Coverage Map

### Acceptance Criteria → Task Traceability

| AC | Description | Task(s) | Status |
|----|-------------|---------|--------|
| AC1 | `fill_territory()` replaced with BFS flood-fill | T7, T8 | ✅ mapped |
| AC2 | Defender fill single connected component | T9, T11 | ✅ mapped |
| AC3 | Attacker fill + border single connected component | T9, T11 | ✅ mapped |
| AC4 | No frame stone isolated | T9, T11 | ✅ mapped |
| AC5 | `offence_to_win` removed | T5, T6, T13 | ✅ mapped |
| AC6 | `_choose_scan_order` deleted, `_choose_flood_seeds` added | T7, T8, T13 | ✅ mapped |
| AC7 | `normalize_to_tl()` includes axis-swap | T2, T4 | ✅ mapped |
| AC8 | Validation failure returns original + warning + dump | T9, T10, T11 | ✅ mapped |
| AC9 | All tests pass + new connectivity tests | T4, T11 | ✅ mapped |
| AC10 | `fill_density` metric preserved | T8 (preserved in fill return) | ✅ mapped |

### Must-Hold Constraints → Task Traceability

| MH | Description | Task(s) | Status |
|----|-------------|---------|--------|
| MH-1 | Round-trip test with swap_xy=True | T4, T11 | ✅ mapped |
| MH-2 | Disconnected = component count > 1 | T9 | ✅ mapped |
| MH-3 | Dead stone = zero same-color ortho neighbors | T9 | ✅ mapped |
| MH-4 | Legality guards preserved unchanged | T7, T8 (reuse, no modify) | ✅ mapped |
| MH-5 | offence_to_win fully deleted | T5, T6, T13 | ✅ mapped |
| MH-6 | Validation failure returns original | T10, T11 | ✅ mapped |

### Goals → Task Traceability

| Goal | Task(s) |
|------|---------|
| G1 (connected fill) | T7, T8, T9, T11 |
| G2 (no dead stones) | T7, T8, T9, T11 |
| G3 (score-neutral) | T5, T6, T11 |
| G4 (post-fill validation) | T9, T10, T11 |
| G5 (correct normalization) | T1, T2, T3, T4 |
| G6 (clean API) | T5, T6, T7, T8, T13 |

---

## 4. Unmapped Tasks

None. All tasks trace to at least one AC, MH, or Goal.

---

## 5. Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | `query_builder.py:prepare_tsumego_query()` calls `apply_tsumego_frame()` | Low — caller doesn't pass `offence_to_win`, no signature change for other params | No code change needed; verify with grep | T13 | ✅ addressed |
| RE-2 | downstream | `query_builder.py:build_query_from_position()` calls `apply_tsumego_frame()` | Low — same as RE-1, doesn't pass removed param | Verify with grep | T13 | ✅ addressed |
| RE-3 | downstream | `enrich_single.py` or other enrichment modules | Very Low — they call `build_query_from_sgf()` which calls `apply_tsumego_frame()` internally; no direct frame API usage | Verify integration test passes | T11 | ✅ addressed |
| RE-4 | lateral | `show_frame.py` diagnostic script | Medium — uses `apply_tsumego_frame()` with `offence_to_win` parameter | Update script to remove `offence_to_win` param | T13 | ❌ needs action |
| RE-5 | lateral | `tests/test_tsumego_frame.py:TestOffenceToWin` | High — tests for `offence_to_win` behavior must be removed/replaced | Replace with score-neutral split tests | T11 | ✅ addressed |
| RE-6 | lateral | `tests/test_tsumego_frame.py:TestLeftRightEdgePuzzles` | Medium — tests `_choose_scan_order()` which is deleted | Remove scan_order test, add seed selection test | T11 | ✅ addressed |
| RE-7 | downstream | `docs/concepts/tsumego-frame.md` | High — algorithm description is outdated after changes | Full section rewrite | T12 | ✅ addressed |
| RE-8 | upstream | `models/position.py:crop_to_tight_board()` | None — no changes to cropping logic | D33 preserved | — | ✅ addressed |
| RE-9 | lateral | `analyzers/liberty.py` | None — legality guards preserved unchanged (MH-4) | No modifications | — | ✅ addressed |
| RE-10 | downstream | KataGo evaluation quality | Low — score-neutral fill changes territory balance | Post-change calibration with golden puzzles | T11 (golden comparison) | ✅ addressed |

### RE-4 Action Required

`show_frame.py` (line 84) passes `offence_to_win` → not currently, but check if the script might break. Reading the script (attached), it does NOT pass `offence_to_win` — it only passes `margin`, `offense_color`, `ko_type`. **No action needed.** Reclassified.

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-4 | lateral | `show_frame.py` diagnostic script | Very Low — does NOT pass `offence_to_win` | Verified from source (attached) | — | ✅ addressed |

---

## 6. Severity-Based Findings

| finding_id | severity | description | resolution |
|------------|----------|-------------|------------|
| F-S1 | **Critical** | ISSUE-1 dead checker stones corrupt KataGo ownership | T7-T8: BFS flood-fill eliminates isolated stones by construction |
| F-S2 | **High** | ISSUE-2 border fragments defender fill | T8: Attacker BFS seeded from border cells → single connected blob |
| F-S3 | **High** | ISSUE-3 row-major scan disconnected islands | T2: normalize axis-swap + T8: BFS (no linear scan) |
| F-S4 | **Medium** | ISSUE-4 no post-fill validation | T9-T10: `validate_frame()` with hard-fail |
| F-S5 | **High** | ISSUE-5 offence_to_win asymmetry | T5-T6: 50/50 score-neutral split |

---

## 7. Test Strategy

| test_type | coverage | tasks |
|-----------|----------|-------|
| Unit — normalize round-trip | swap_xy=True path, all position types | T4 |
| Unit — score-neutral split | defense_area ≈ offense_area (±1) | T11 |
| Unit — BFS connectivity | Single component per color | T11 |
| Unit — dead stone detection | All frame stones have ≥1 same-color neighbor | T11 |
| Unit — validation failure | Forced invalid → original position returned | T11 |
| Unit — density check | fill_density in expected range | T11 |
| Integration — full pipeline | `apply_tsumego_frame()` produces valid frame | T11 |
| Regression — existing tests | All updated tests pass | T11 |
| Verification — grep cleanup | No offence_to_win, no _choose_scan_order | T13 |

---

> **See also**:
>
> - [Plan](./30-plan.md) — Architecture design
> - [Tasks](./40-tasks.md) — Dependency-ordered task list
> - [Charter](./00-charter.md) — Goals and acceptance criteria
> - [Research](../20260312-research-tsumego-frame-flood-fill/15-research.md) — Evidence base
