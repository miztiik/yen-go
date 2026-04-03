# Analysis: Tsumego Frame Legality & Correctness

**Last Updated**: 2026-03-11

---

## 1. Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 90 |
| Risk Level | low |
| Research Invoked | No |

---

## 2. Consistency Check

| finding_id | check | result | detail |
|-----------|-------|--------|--------|
| F1 | Charter → Options → Plan → Task mapping | ✅ | F1 → `_count_group_liberties()` → T2 → guard in T7 |
| F2 | Charter → Options → Plan → Task mapping | ✅ | F2 → `_would_harm_puzzle_stones()` → T3 → guard in T7 |
| F3 | Charter → Options → Plan → Task mapping | ✅ | F3 → inviolate comment → T11 |
| F7 | Charter → Options → Plan → Task mapping | ✅ | F7 → Low severity, existing warning sufficient → no task needed |
| F8 | Charter → Options → Plan → Task mapping | ✅ | F8 → validate-and-skip approach → T7, T8 |
| F9 | Charter → Options → Plan → Task mapping | ✅ | F9 → player_to_move preserved → T11 (already correct, add comment) |
| F10 | Charter → Options → Plan → Task mapping | ✅ | F10 → `_would_harm_puzzle_stones()` → T3 → guard in T7 |
| F11 | Charter → Options → Plan → Task mapping | ✅ | F11 → `_has_frameable_space()` → T5 → T9 |
| F20 | Charter → Options → Plan → Task mapping | ✅ | F20 → `_is_eye()` → T4 → guard in T7 |
| F25 | Charter → Options → Plan → Task mapping | ✅ | F25 → PL tie-breaker → T10 |

---

## 3. Coverage Map

| area | tasks_covering | gaps |
|------|---------------|------|
| Liberty counting | T2, T13 | None |
| Puzzle protection | T3, T14 | None |
| Eye detection | T4, T15 | None |
| Full-board check | T5, T9, T17 | None |
| FrameResult extension | T6, T18 | None |
| Fill validation | T7, T14, T15 | None |
| Border validation | T8 | Covered by T7 tests (same guards) |
| PL tie-breaker | T10, T16 | None |
| Inviolate rule | T11 | Comment only, no test needed |
| Density metric | T12, T17 | None |
| Data audit | T1, T19 | None |
| Regression | T20 | None |
| Line count (MH-1) | T21 | None |
| Documentation | T22 | None |

---

## 4. Must-Hold Constraint Traceability

| MH-ID | Task(s) | Implementation |
|-------|---------|----------------|
| MH-1 | T21 | Line count check post-implementation |
| MH-2 | T6, T7, T8, T18 | FrameResult fields + guard tracking |
| MH-3 | T10, T16 | logger.info on disagreement |
| MH-4 | T12, T17 | fill_density field + logging |

---

## 5. Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|-----------|--------|
| R1 | downstream | KataGo evaluation quality | Low | Validate-and-skip only improves input quality; never degrades | T7, T19 | ✅ addressed |
| R2 | downstream | Difficulty classification | Low | Better frame → better eval → better classification | T19 | ✅ addressed |
| R3 | lateral | Calibration tests (test_calibration.py) | Medium | Run data audit on calibration fixtures; compare before/after | T19 | ✅ addressed |
| R4 | lateral | FrameResult consumers | Low | New fields are optional (defaults=0); existing consumers unaffected | T6 | ✅ addressed |
| R5 | upstream | Position model | None | No changes to Position model | — | ✅ addressed |
| R6 | lateral | Existing 46 frame tests | Low | All existing tests must pass (T20) | T20 | ✅ addressed |
| R7 | lateral | 271 regression tests | Low | Regression suite validates end-to-end | T20 | ✅ addressed |

---

## 6. Unmapped Tasks

None — all findings, must-hold constraints, and documentation requirements are mapped to tasks.

---

## 7. Findings

| finding_id | severity | description | status |
|-----------|----------|-------------|--------|
| F1 | Risk: Low | Liberty counting BFS is O(board_size²) worst case — negligible for offline tool | ✅ accepted |
| F2 | Risk: Low | Skip-heavy frames could degrade KataGo input — data audit validates on real corpus | ✅ mitigated via T19 |
| F3 | Info | `tsumego_frame.py` grows from ~650 to ~750 lines — within MH-1 threshold | ✅ monitored via T21 |
