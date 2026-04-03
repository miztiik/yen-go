# Governance Decisions — Enrichment Lab Test Audit (Phase 2)

> Last Updated: 2026-03-24

## Charter Review (2026-03-24)

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`
**Unanimous**: No (8 approve, 2 approve_with_conditions)

### Support Summary

The panel **unanimously supports** the core initiative. Phase 1 (duplicate deletion) is zero-risk with verified evidence. The DRY/YAGNI analysis is sound and the consolidation scope is appropriate. GV-5 and GV-6 voted `approve_with_conditions` requiring 4 items resolved before plan approval.

### Member Reviews

| GV-ID | Member | Domain | Vote | Key Comment |
|-------|--------|--------|------|-------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Priority-based naming is correct — maps to detection priority order. Delete frequency-named legacy files. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Delete most config snapshots. **Preserve `TestThresholdConservation`** (C9 invariants: t_good=0.05, t_bad=0.15, t_hotspot=0.30). |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | **Keep perf files separate** for CI tier selection. Don't merge into parametrized suite. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Redistribute sprint tests to module files — S1-G1 means nothing later, but `TestOwnershipConvergence` in `test_solve_position.py` is self-documenting. |
| GV-5 | Principal Staff Engineer A | Systems architect | approve_with_conditions | **RC-1**: File count arithmetic. **RC-2**: Phase 4 redistribution mapping. **RC-4**: Formalized acceptance criteria. |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve_with_conditions | **RC-3**: `.vscode/tasks.json` co-modification in same commit. Test failure localization via class-level organization. |
| GV-7 | Hana Park (1p) | Player experience | approve | No player-facing impact. C9 threshold conservation guards must survive. |
| GV-8 | Mika Chen | DevTools UX | approve | No developer tooling affected. |
| GV-9 | Dr. David Wu (KataGo) | MCTS engine | approve | No engine parameters modified. **Keep perf files separate** — each scale exercises different convergence behaviors. |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve | Priority-named files are canonical (T33-T41 task IDs). Sprint gap tests are correctness regression guards, not throwaway artifacts. |

### Required Changes (Plan-Gate)

| RC-ID | Category | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | Scope clarity | Provide explicit per-phase file mapping (old → new/deleted) | ❌ pending |
| RC-2 | Plan specificity | Phase 4 redistribution targets explicit (per charter, deferred to NG5) | ✅ resolved (deferred) |
| RC-3 | Co-modification | `.vscode/tasks.json` updated in same commit as file changes | ❌ pending |
| RC-4 | Acceptance criteria | Formalized in charter AC1-AC7 | ✅ resolved |

### Panel Answers to Charter Questions

| Q# | Question | Panel Answer |
|----|----------|--------------|
| Q1 | Detector naming — priority-based correct? | **Yes** — canonical. Delete frequency-based legacy. (GV-1, GV-3, GV-10 unanimous) |
| Q2 | Config snapshot tests — preserve or delete? | **Partial delete** — Keep only `TestThresholdConservation` (C9 guards). (GV-2, GV-7) |
| Q3 | Perf suite — merge or keep separate? | **Keep separate** — different convergence regimes, CI tiering value. (GV-3, GV-9 unanimous) |
| Q4 | Remediation sprint tests — redistribute? | **Redistribute** long-term, but deferred to NG5. Keep as-is for this initiative. (GV-4, GV-10) |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| mode | charter |
| decision | approve_with_conditions |
| status_code | GOV-CHARTER-CONDITIONAL |
| message | Charter approved. Proceed to options/plan with RC-1/RC-3 as mandatory plan content. Phase 1 (delete 4 duplicates) may be fast-tracked — independently safe. |
| blocking_items | RC-1 (file mapping), RC-3 (tasks.json co-modification) |

---

## Options Election (2026-03-24)

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-OPTIONS-CONDITIONAL`
**Selected Option**: OPT-1 — Phased Consolidation (Conservative)
**Unanimous**: 8 approve, 2 concern (GV-2, GV-7 → mapped to RC-5)

### Selection Rationale

OPT-1 unanimously preferred. Matches Level 3 correction workflow. Phase 1 is independently safe (zero-risk duplicate deletion). Per-commit rollback enables surgical revert. OPT-2's single-batch approach provides no advantage for test-only initiative where bisectability matters.

### Required Changes

| RC-ID | Category | Description | Blocking? |
|-------|----------|-------------|-----------|
| RC-5 | Due diligence | Before Phase 2 (delete test_feature_activation.py), executor MUST verify and document which existing tests exercise C9 thresholds (t_good=0.05, t_bad=0.15, t_hotspot=0.30) transitively. If none, log gap for user awareness. Per Q2=A, do NOT re-introduce tests. | Phase 2 gate |

### Must-Hold Constraints

| MH-ID | Constraint |
|-------|-----------|
| MH-1 | Phase ordering 1→2→3→4 with pytest --co -q verification after each |
| MH-2 | VS Code tasks updated when phase files change |
| MH-3 | Zero assertion changes — only file merges, imports, deletions |
| MH-4 | All @pytest.mark markers preserved |
| MH-5 | AGENTS.md test section updated |
| MH-6 | RC-5 C9 verification before Phase 2 |

---

## Plan Review (2026-03-24)

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`
**Unanimous**: 8 approve, 2 approve_with_conditions (GV-5, GV-6)

### Summary

Plan approved for execution. 4-phase structure is well-structured, independently verifiable, and correctly scoped. All prior RCs resolved. Three non-blocking documentation hygiene items (RC-6/7/8) resolved at execution start.

### Required Changes (All Non-Blocking)

| RC-ID | Description | Status |
|-------|-------------|--------|
| RC-6 | Fix 40-tasks.md summary narrative to match arithmetic table | ✅ Fixed |
| RC-7 | Update 20-analysis.md RE-4 to "deferred" and RE-6 to "addressed" | ✅ Fixed |
| RC-8 | Update status.json phase_state.analyze to "approved" | ✅ Fixed |

### Handover to Plan-Executor

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve_with_conditions |
| status_code | GOV-PLAN-CONDITIONAL |
| message | Plan approved. Execute phases 1→2→3→4 per MH-1. T2-RC5 MUST complete before T2. Verify pytest --co -q count at each phase boundary. |
| blocking_items | None — all RCs resolved |

---

## Implementation Review (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: Yes (10/10 approve)

### Support Summary

All 10 panel members unanimously approve the implementation. All 7 acceptance criteria (AC1-AC7) verified, all 6 must-hold constraints (MH-1 through MH-6) satisfied. Zero new test failures introduced. RC-5 C9 transitive coverage fully documented (6 test functions). Test collection arithmetic precise: 2798 → 2639. File count reduction: 84 → 73.

### Member Reviews

| GV-ID | Member | Vote | Key Comment |
|-------|--------|------|-------------|
| GV-1 | Cho Chikun (9p) | approve | Clean structural execution. Priority-based naming now canonical. |
| GV-2 | Lee Sedol (9p) | approve | C9 threshold guards survived — RC-5 verification complete. |
| GV-3 | Shin Jinseo (9p) | approve | Perf files correctly untouched per NG1. |
| GV-4 | Ke Jie (9p) | approve | Config split (loading vs values) is meaningful organizational improvement. |
| GV-5 | Principal Staff Engineer A | approve | All prior RCs resolved. Architecture clean. |
| GV-6 | Principal Staff Engineer B | approve | Phase ordering enforced with precise count tracking. |
| GV-7 | Hana Park (1p) | approve | No player-facing impact. C9 guards intact. |
| GV-8 | Mika Chen | approve | No developer tooling affected. |
| GV-9 | Dr. David Wu (KataGo) | approve | No engine parameters modified. |
| GV-10 | Dr. Shin Jinseo | approve | 116 refutation quality tests cover critical correctness chain. |

### Minor Findings (Non-Blocking)

| ID | Description |
|----|-------------|
| CRA-1 | EX-4a documents "12 classes" for test_config_loading.py; actual is 11. Documentation hygiene only. |
| CRB-1 | `.pytest_cache` stale entries — cleared on next `--cache-clear` run. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve |
| status_code | GOV-REVIEW-APPROVED |
| message | Implementation approved unanimously. Proceed to closeout. |
| blocking_items | None |

---

## Closeout Audit (2026-03-24)

**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Unanimous**: Yes (10/10 approve)

### Support Summary

Initiative closed. All 6 charter goals delivered. All 4 governance gates passed (charter → options → plan → review → closeout). Test infrastructure reduced: 84 → 73 files, 2798 → 2639 tests. Zero new test failures. AGENTS.md updated. Three non-blocking residual items documented (CRA-1 class count typo, CRB-1 cache staleness, T6 user-level tasks).

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | User |
| decision | approve |
| status_code | GOV-CLOSEOUT-APPROVED |
| message | Initiative closed. All goals delivered, all gates passed. |
| blocking_items | None |
