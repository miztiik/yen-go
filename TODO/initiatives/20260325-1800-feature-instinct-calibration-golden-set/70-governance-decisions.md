# Governance Decisions — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

---

## Gate 1: Charter Review

- **Gate**: `charter-review`
- **Decision**: `approve`
- **Status Code**: `GOV-CHARTER-APPROVED`
- **Unanimous**: Yes (9/9)
- **Date**: 2026-03-25

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Five instinct types map cleanly to fundamental tsumego concepts. Sakata Eio collection with filename-level labels is excellent ground truth. Tobi verification (G-7) critical — tobi can include keima which are NOT axis-aligned extensions. Null category appropriate for kosumi/tsuke/oki/kake. Warikomi could be cut in some positions — expert verification correct approach. | Sakata directory verified (110 SGFs); `INSTINCT_TYPES` in instinct_result.py; Tobi risk in charter |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Push is hardest to source — charter correctly identifies Lee Changho Fighting chapter as mitigation. Multi-label schema (`instinct_labels[]` array) allows capturing sequence nuance. 70% threshold pragmatic for geometric classifier. AC-4 (null FP = 0%) is aggressive but appropriate. | Charter source material; `instinct_labels[]` array in G-4; AC-4 threshold |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Calibration set correctly positioned as signal-to-words bridge. KataGo entropy values meaningless without human-verified anchoring. Observation: charter doesn't specify whether KataGo analysis will be run on golden set for cross-validation — could be follow-up. | `instinct_classifier.py` header; Q12 key design decision |
| GV-4 | Staff Engineer A | Systems architect | approve | Architecture isolation well-designed: tools must not import from backend (C-1), read-only external-sources (C-2), separate fixture directory. Test scaffold exists. Naming convention consistent with extended-benchmark. Concern: two permanent tools need clear placement (subdirectory vs top-level) — resolvable in planning. | `tools/__init__.py`; `test_instinct_calibration.py`; `labels.json` schema |
| GV-5 | Staff Engineer B | Data pipeline | approve | Inventory concrete and verifiable. ~120 target with ≥10 per instinct and ≥5 per technique creates well-distributed set. Warikomi ambiguity appropriate for expert resolution. Phased approach (Sakata auto-map → verify → gap fill) is sound. Concern: AC-6 "top 10 technique tags" not enumerated — resolvable in options. | Sakata inventory; Lee Changho directory listing; AC-6 |
| GV-6 | Hana Park (1p) | Player experience | approve | Ground truth for instinct classification that surfaces in teaching comments, technique labels, progressive hints. AC-1 determines whether players see instinct-based content. AC-4 (null FP = 0%) excellent from player trust perspective. | Charter AC-1, AC-4; NG-1 |
| GV-7 | Mika Chen | DevTools UX | approve | Two permanent tools (search, copy-rename) are appropriate developer-facing utilities. ASCII board rendering via existing `render_sgf_ascii()` provides serviceable labeling interface. Tool usability reviewable at plan stage. | G-2, G-3; C-6; `ascii_board.py` |
| GV-8 | Dr. David Wu | KataGo engine | approve | Charter is about human labeling infrastructure, not KataGo configuration changes. No engine parameters modified. Calibration set validates geometric classification, not engine tuning. No KataGo concerns. | Charter non-goals NG-1; instinct_classifier.py is purely geometric |
| GV-9 | Dr. Shin Jinseo | Tsumego correctness | approve | Instinct taxonomy well-grounded in tsumego pedagogy. Null correct catch-all for non-matching first moves. AC thresholds properly tiered. Tobi verification essential. Multi-dimensional labels enable future technique tag calibration. Source material from three professional-grade collections provides strong provenance. | Sakata inventory; `INSTINCT_TYPES`; AC-1/AC-2/AC-3/AC-4; G-7 |

### Support Summary

Unanimous approval. Charter demonstrates exceptional scope clarity: 7 goals with concrete deliverables, 5 non-goals with rationale, 7 constraints anchored to verifiable project rules, and 8 acceptance criteria with quantitative thresholds. Source material verified against actual directory contents. Risk coverage adequate with explicit mitigations.

### Required Changes (Non-Blocking)

| RC-ID | Severity | Description | Owner Artifact | Status |
|-------|----------|-------------|----------------|--------|
| RC-1 | recommendation | Enumerate "top 10 technique tags" for AC-6 and verify source coverage | `25-options.md` | ✅ resolved |
| RC-2 | recommendation | Remove forward-reference links from charter until target artifacts exist | `00-charter.md` | ✅ resolved |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Feature-Planner
- **decision**: approve
- **status_code**: GOV-CHARTER-APPROVED
- **message**: Charter approved unanimously. Proceed to options drafting. Enumerate top 10 technique tags for AC-6 (verify against `config/tags.json`), specify tool placement within `tools/`.
- **required_next_actions**:
  1. Update `status.json`: charter → approved, current_phase → options
  2. Draft `25-options.md` with ≥2 alternative approaches
  3. Enumerate top 10 technique tags for AC-6
  4. Remove forward-reference links from charter (RC-2)
  5. Submit `25-options.md` for governance options review
- **blocking_items**: none

---

## Gate 2: Options Review

- **Gate**: `options-review`
- **Decision**: `approve`
- **Status Code**: `GOV-OPTIONS-APPROVED`
- **Unanimous**: Yes (9/9)
- **Date**: 2026-03-25
- **Selected Option**: OPT-1 (Two Standalone Scripts)

### Selection Rationale

Pattern consistency with existing `tools/` conventions, YAGNI compliance, charter alignment ("two permanent tools"), identical calibration output quality, minimal maintenance burden (2 files vs 7).

### Must-Hold Constraints

| MH-ID | Constraint | Rationale |
|-------|-----------|-----------|
| MH-1 | Both scripts include `--dry-run` flag | UX safety for copy/rename operations |
| MH-2 | Tests placed in consistent location | Either `tools/core/tests/` or adjacent test files |
| MH-3 | `labels.json` must include `instinct_labels[]` array | Multi-label support for ambiguous first moves |
| MH-4 | Scripts must use `tools.core.sgf_parser` for SGF reading | Architecture boundary (C-1) enforcement |
| MH-5 | RC-2 addressed before plan | ✅ Already resolved |

### Member Vote Summary

All 9 members voted `approve` for OPT-1. Key consensus points:
- Pattern consistency: standalone scripts match existing `tools/` convention (GV-4)
- YAGNI: OPT-2's validate/stats subcommands already covered by test harness (GV-1, GV-3, GV-5)
- Identical output: Both options produce same labels.json and fixtures (GV-1, GV-6, GV-9)
- Developer UX: Two `--help`-discoverable scripts cleaner than subcommand navigation (GV-7)

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Feature-Planner
- **decision**: approve
- **status_code**: GOV-OPTIONS-APPROVED
- **message**: OPT-1 unanimously approved. Proceed to plan and tasks. Apply MH-1 through MH-5.
- **blocking_items**: none

---

## Gate 3: Plan Review

- **Gate**: `plan-review`
- **Decision**: `approve`
- **Status Code**: `GOV-PLAN-APPROVED`
- **Unanimous**: Yes (9/9)
- **Date**: 2026-03-25

### Verification Summary

- 16 pre-review checks: all pass
- Planning confidence: 85/100 ≥ 80 threshold ✅
- Codebase verification: 12 claims verified against actual code
- All must-holds (MH-1 through MH-5) confirmed in plan

### Member Vote Summary

All 9 members voted `approve`. Key consensus points:
- Exceptional traceability: 7 goals → 23 tasks → 8 ACs, zero gaps (all members)
- Sakata filename→instinct mapping correct for Japanese Go terminology (GV-1, GV-9)
- Push sourcing via Lee Changho Fighting chapter is pragmatic (GV-2)
- Geometric classifier calibration is fast, deterministic, CI-friendly (GV-3)
- Architecture isolation verified: no `backend/` imports, stable `tools.core` APIs (GV-4)
- Phased ETL methodology with correct parallelization (GV-5)
- Plan gates player-visible instinct features correctly (GV-6)
- Tool CLI design follows project convention (GV-7)
- No KataGo engine changes (GV-8)
- AC threshold tiering (70/60/85/0% FP) structurally sound (GV-9)

### Required Changes

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | cosmetic | DOC-3 action "Update" → "Create" in plan Documentation Plan table | ✅ resolved |

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve
- **status_code**: GOV-PLAN-APPROVED
- **message**: Plan unanimously approved. Execute 23 tasks across 5 phases. Start T1∥T3∥T5 in parallel. TDD for Phase 1 and Phase 4. Run V-1 through V-6 validation checkpoints. Run regression suites after T20.
- **blocking_items**: none

---

## Gate 4: Implementation Review

- **Gate**: `implementation-review`
- **Decision**: `approve_with_conditions`
- **Status Code**: `GOV-REVIEW-CONDITIONAL`
- **Unanimous**: No (8 approve, 2 concern → both mapped to RC-1)
- **Date**: 2026-03-25

### Required Changes

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | required | Rename 6 warikomi-promoted files from `null_intermediate_057-063` to `cut_intermediate_013-018` to satisfy C-3 naming convention | ✅ resolved |
| RC-2 | cosmetic | Fix stale note for `null_intermediate_062.sgf` | ✅ resolved |

### Resolution Evidence

- RC-1: 6 files renamed, labels.json keys updated. Verification: 0 null-named files with cut instinct, 21 cut files match 21 cut labels.
- RC-2: Note updated to "T11: verified as null (true wedge, not splitting cut)".
- Calibration tests re-run post-fix: 2 passed, 2 skipped, 4 xfailed (exit 0). Same accuracy baselines (no regression).

### Support Summary

8 approve, 2 concern. Core deliverables verified: 134 labeled puzzles, 24 tool tests, 4 calibration tests (xfail baselines), 3 documentation artifacts. Architecture isolation maintained. Single finding (CRA-1 naming violation) resolved via RC-1.

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve_with_conditions
- **status_code**: GOV-REVIEW-CONDITIONAL
- **message**: Implementation approved. RC-1 and RC-2 resolved. Proceed to closeout.
- **blocking_items**: none (RCs resolved)

---

## Gate 5: Closeout Audit

- **Gate**: `closeout-audit`
- **Decision**: `approve`
- **Status Code**: `GOV-CLOSEOUT-APPROVED`
- **Unanimous**: Yes (9/9)
- **Date**: 2026-03-26

### Closeout Checklist

| check_id | item | result |
|-----------|------|--------|
| CL-1 | Charter goals met | ✅ |
| CL-2 | All 23 tasks completed | ✅ |
| CL-3 | Validation suite passed (VAL-1 through VAL-6) | ✅ |
| CL-4 | RC-1 and RC-2 resolved | ✅ |
| CL-5 | Documentation complete (DOC-1, DOC-2, DOC-3) | ✅ |
| CL-6 | No regressions (293 enrichment + 1580 backend) | ✅ |
| CL-7 | Architecture isolation maintained (C-1, C-2) | ✅ |
| CL-8 | Naming convention compliant (C-3) | ✅ |
| CL-9 | Labels schema v1.0 verified | ✅ |
| CL-10 | Execution artifacts complete | ✅ |

### Documentation Quality

| dq_id | doc | score |
|-------|-----|-------|
| DQ-1 | AGENTS.md (DOC-1) | ✅ complete |
| DQ-2 | README.md (DOC-2) | ✅ complete |
| DQ-3 | enrichment-calibration.md (DOC-3) | ✅ complete |
| DQ-4 | Cross-references | ✅ verified |
| DQ-5 | labels.json schema docs | ✅ verified |
| DQ-6 | See-also callouts | ✅ present |

### Support Summary

Unanimous approval (9/9). All deliverables verified on disk: 134 labeled SGFs, 2 CLI tools with 24 tests, 4 calibration tests (xfail baselines), 3 documentation artifacts. No required changes identified.

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **decision**: approve
- **status_code**: GOV-CLOSEOUT-APPROVED
- **message**: Closeout approved unanimously. Initiative complete. Update status.json to reflect closeout approval.
- **blocking_items**: none
- **re_review_requested**: false
