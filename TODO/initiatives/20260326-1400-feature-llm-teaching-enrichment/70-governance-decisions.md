# Governance Decisions: KataGo Teaching Signal Emission

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27

---

## Decision 1: Original Planning Approval (superseded)

- **decision**: approve
- **status_code**: GOV-PLAN-APPROVED
- **rationale**: User explicitly approved ("Execute this approved feature plan package"). Superseded by rescoped plan below.
- **note**: This approval was for the original R-1+R-2 scope which included LLM client code. User subsequently rescoped to signal-emission-only.

---

## Decision 2: Rescoped Plan Governance (current)

- **decision**: approve_with_conditions
- **status_code**: GOV-PLAN-CONDITIONAL
- **rationale**: Plan rescoped per user directive to signal-emission-only. Thorough research with evidence chains. All source code claims verified. 5 minor conditions (RC-1 to RC-5) identified.

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|-------------------|----------|
| GV-1 | Cho Chikun (9p) | Go domain authority | **approve** | Signal payload captures essential Go pedagogical information. 11-condition refutation classifier explains WHY moves fail. Seki exception structurally correct. | Payload schema in 30-plan.md; 11 classifier conditions in 15-research.md §4 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | **approve** | Payload supports multiple wrong-move perspectives. Instructiveness gate filters noise while seki exception preserves creative positions. `refutation_pv` enables reading narrative. | 30-plan.md payload schema; RC-1 seki exception |
| GV-3 | Shin Jinseo (9p) | AI-era professional | **approve** | Zero new KataGo queries (C3) correct. `log_policy_score` formula well-calibrated. `compute_ownership_delta()` reuse is sound. | Formulas in 15-research.md §1; generate_refutations.py:36 |
| GV-4 | PSE-A | Systems architect | **concern** | Backward compat excellent. RC-1: T9 needs `root_ownership` param. RC-2: T14 wiring location ambiguous. RC-3: T9 field type ambiguous. | generate_refutations.py signatures; ownership_consequence:dict mismatches float |
| GV-5 | PSE-B | Pipeline engineer | **concern** | Research gap analysis thorough. RC-4: status.json score=0. RC-5: No 25-options.md. | status.json; directory listing |
| GV-6 | Hana Park (1p) | Player experience | **approve** | Zero player-facing changes. Template system protected by C4. | Charter Non-Goals; C4 constraint |
| GV-8 | Dr. David Wu (KataGo) | MCTS engine | **approve** | Zero new queries correct. `compute_ownership_delta()` handles None guards. `include_ownership=True` already set. | C3; generate_refutations.py:388 |
| GV-9 | Dr. Shin Jinseo (Tsumego) | Difficulty calibration | **approve** | Seki exception mathematically sound (closeness ≈ 1.0 when wr ≈ 0.5). Score_delta complements winrate_delta. 11-condition classifier accurate. | Position_closeness formula; score_delta at generate_refutations.py:453-481 |

### Required Changes (all resolved)

| RC-id | severity | description | resolution | status |
|-------|----------|-------------|-----------|--------|
| RC-1 | minor | T9: Add `root_ownership` parameter to `generate_single_refutation()` | Updated T9 task details with explicit parameter addition + threading from `initial_analysis.ownership` | ✅ resolved |
| RC-2 | minor | T14: Specify exact wiring location | Resolved to `assembly_stage.py` (not result_builders.py). Exact insertion point: after existing field wiring, before `ctx.result = result` | ✅ resolved |
| RC-3 | minor | T9: Use new `ownership_delta: float = 0.0` field, not repurpose `ownership_consequence: dict` | Updated T9 and 30-plan.md to specify new field (correct type) | ✅ resolved |
| RC-4 | minor | Update `status.json.planning_confidence_score` from 0 | Updated to 87 | ✅ resolved |
| RC-5 | minor | Create `25-options.md` artifact | Created with 3 options, tradeoff matrix, 9/9 panel vote | ✅ resolved |

### Support Summary

7 approve / 2 concern (minor task specification gaps, now resolved). Both non-unanimous members (GV-4, GV-5) acknowledged their concerns are minor and fully addressed by RC-1 through RC-5.

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **message**: Plan approved with 5 conditions, all now resolved. Execute T7→T20 in dependency order.
- **required_next_actions**: Execute remaining tasks (T7-T20), run regressions (T18-T19), update AGENTS.md (T20), submit for review mode governance.
- **artifacts_to_update**: 50-execution-log.md, 60-validation-report.md, status.json
- **blocking_items**: none (all RCs resolved)

### Planning Confidence Score: 87 → revised at Decision 3 below

### docs_plan_verification
- present: true
- coverage: complete (AGENTS.md update in T20)

---

## Decision 3: Final Plan Approval (re-review, 2026-03-27)

- **decision**: approve
- **status_code**: GOV-PLAN-APPROVED
- **rationale**: All 5 original RCs resolved. Critical bug discovered (wrong_move_signals always empty due to stage ordering) and addressed via T5b. T8b added for ownership_delta data path. board_size hardcode fix. T16 test coverage expanded. 9/9 unanimous approval.

### Changes Since Decision 2
1. RC-1 through RC-5: All resolved (task specs clarified, options artifact created, confidence score updated)
2. CRITICAL BUG: T5b added — relocate payload build from DifficultyStage to AssemblyStage
3. T8b added — propagate ownership_delta through RefutationEntry
4. T12 updated — accept board_size parameter, accept config for thresholds
5. T16 expanded — populated refutations, seki boundary, config-off, board_size=9

### Member Reviews (re-review)

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Go domain | **approve** | Seki exception structurally correct. Critical bug fix demonstrates thorough due diligence. |
| GV-2 | Lee Sedol (9p) | Fighter | **approve** | Multi-signal approach captures different dimensions of "badness". T5b essential for fighting aspects. |
| GV-3 | Shin Jinseo (9p) | AI-era | **approve** | Zero new queries confirmed. Log_policy formula well-calibrated. Ownership reuse sound. |
| GV-4 | PSE-A | Systems | **approve** | All 5 RCs resolved with source evidence. Task dependency graph well-formed. |
| GV-5 | PSE-B | Pipeline | **approve** | status.json updated. 25-options.md created. Gap analysis exemplary. |
| GV-6 | Hana Park (1p) | Player UX | **approve** | Zero player-facing changes. Template system protected. |
| GV-7 | Mika Chen | DevTools UX | **approve** | Payload schema well-structured. Version field enables evolution. Config-driven thresholds. |
| GV-8 | Dr. David Wu | KataGo | **approve** | Zero engine overhead. Existing ownership infrastructure reused. |
| GV-9 | Dr. Shin Jinseo | Tsumego | **approve** | Seki threshold mathematically justified. Score_delta complements winrate_delta. |

### Support Summary

9/9 unanimous approve. All concerns from Decision 2 resolved. Critical bug discovery and resolution raised confidence from 87→95.

### Planning Confidence Score: 95

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **message**: Plan unanimously approved at confidence 95. Execute T5b first (critical bug fix), then T7/T9/T10/T13 parallel, then T8/T8b/T11 dependent, then T12/T14, then T15-T19 testing, then T20 docs. Submit for review mode governance after T19 passes.
- **required_next_actions**: Execute T5b→T20 in dependency order. Create 50-execution-log.md and 60-validation-report.md. Submit for review governance.
- **artifacts_to_update**: status.json, 50-execution-log.md (create), 60-validation-report.md (create)
- **blocking_items**: none

---

## Decision 4: Implementation Review (2026-03-27)

- **decision**: approve
- **status_code**: GOV-REVIEW-APPROVED
- **rationale**: 9/9 unanimous approve. All 11 acceptance criteria met with source evidence. All 3 governance conditions (RC-1/RC-2/RC-3) verified with test coverage. Zero failures across 38 teaching signal tests + 345 targeted regression + 1580 backend unit tests. Architecture clean, backward compatible, zero new KataGo queries.

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|-------------------|----------|
| GV-1 | Cho Chikun (9p) | Go domain | **approve** | Option B payload captures essential pedagogical dimensions. Seki exception structurally correct. | teaching_signal_payload.py:140-145; 38 tests |
| GV-2 | Lee Sedol (9p) | Fighter | **approve** | Multi-dimensional wrong-move signals support different learning perspectives. T5b fix essential. | CRITICAL-1 fix; test_wrong_moves_populated |
| GV-3 | Shin Jinseo (9p) | AI-era | **approve** | Zero KataGo queries confirmed. compute_ownership_delta() reuse sound. Board size parameterized. | C3 verified; test_board_size_9 |
| GV-4 | PSE-A | Systems | **approve** | All RCs resolved with source evidence. Feature gating clean. Schema v10 additive-only. | CRA-1 through CRA-7 pass; TeachingSignalConfig defaults |
| GV-5 | PSE-B | Pipeline | **approve** | Test evidence chain solid. Gap analysis exemplary. 6-lane execution well-orchestrated. | VAL-25 through VAL-29; 4 gaps closed |
| GV-6 | Hana Park (1p) | Player UX | **approve** | Zero player-facing changes. Template system protected by C4. Feature gate default=False. | TeachingSignalConfig.enabled=False |
| GV-7 | Mika Chen | DevTools UX | **approve** | Payload schema well-structured. round() on floats. Boolean flags for scan-ability. | Payload structure; 5 config knobs |
| GV-8 | Dr. David Wu | KataGo | **approve** | Zero engine overhead. Existing ownership infrastructure reused correctly. | C3; compute_ownership_delta reuse |
| GV-9 | Dr. Shin Jinseo | Tsumego | **approve** | Seki threshold mathematically justified (strict > operator correct). | position_closeness formula; test_seki_exception |

### Support Summary

9/9 unanimous approve. All acceptance criteria verified. Zero required changes.

### Minor Notes (non-blocking)

- CRA-6: try/except import pattern in payload builder — acceptable per enrichment-lab convention
- CRB-6: Pre-existing dead field ownership_consequence: dict — not introduced by this initiative

### Handover

- **from_agent**: Governance-Panel
- **to_agent**: Plan-Executor
- **message**: Implementation approved unanimously. Proceed to closeout audit.
- **required_next_actions**: Run closeout governance audit, update status.json, finalize.
- **artifacts_to_update**: status.json, 70-governance-decisions.md
- **blocking_items**: none

---

## Decision 5: Closeout Audit (2026-03-27)

- **decision**: approve
- **status_code**: GOV-CLOSEOUT-APPROVED
- **rationale**: 9/9 unanimous approve. All 4 gates pass (implementation, tests, documentation, governance). All 20 tasks complete, all 6 lanes merged, all 4 prior governance decisions recorded. AGENTS.md comprehensive. Cross-references verified. Zero player-facing impact. Backward compatibility clean.

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Go domain | **approve** | Payload captures essential pedagogical dimensions. Seki exception mathematically sound. |
| GV-2 | Lee Sedol (9p) | Fighter | **approve** | Multi-dimensional signals support learning perspectives. CRITICAL-1 fix demonstrates debugging culture. |
| GV-3 | Shin Jinseo (9p) | AI-era | **approve** | Zero KataGo overhead. All signals from existing data. Board size parameterized. |
| GV-4 | PSE-A | Systems | **approve** | Backward compat excellent. Feature gating clean. LlmTeachingConfig fully removed. |
| GV-5 | PSE-B | Pipeline | **approve** | Test evidence chain solid. Gap analysis exemplary. 6-lane execution well-orchestrated. |
| GV-6 | Hana Park (1p) | Player UX | **approve** | Zero player-facing changes. Feature gate default=False. |
| GV-7 | Mika Chen | DevTools UX | **approve** | Payload schema well-structured. AGENTS.md discoverability good. |
| GV-8 | Dr. David Wu | KataGo | **approve** | Zero engine overhead. Ownership threading correct. |
| GV-9 | Dr. Shin Jinseo | Tsumego | **approve** | Seki threshold mathematically justified. Score_delta complements winrate_delta. |

### Support Summary

9/9 unanimous approve. Initiative lifecycle fully closed.
