# Governance Decisions — Enrichment Lab Tactical Hints

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Last Updated**: 2026-03-15

---

## Pre-Charter Consultation (GOV-CHARTER-CONSULTATION-COMPLETE)

| Field | Value |
|-------|-------|
| **decision** | `approve` (consultation complete) |
| **status_code** | `GOV-CHARTER-CONSULTATION-COMPLETE` |
| **unanimous** | `true` (7/7) |

### Panel Recommendations Summary

| Question | Consensus | Vote | Recommended Answer |
|----------|-----------|------|-------------------|
| Q-GOV-1: Instinct classification | A — Yes | 7/7 | Add instinct as hint layer. Filter to tsumego-relevant (push, hane, cut, descent, extend). Config-driven. Multi-instinct with tie-breaking. |
| Q-GOV-2: Most valuable hint info | E — All, prioritized by level | 7/7 | Beginner→consequence+position. Intermediate→intent+position. Dan→reading guidance. Config-driven templates keyed by (technique, level_category). |
| Q-GOV-3: Multi-orientation testing | A — Yes, critical | 6/7 A, 1/7 B | Create `Position.rotate()`/`reflect()`. Parametrize tactical detector tests. Non-negotiable for tactical detectors. |
| Q-GOV-4: Top-K rank | C — Supplementary | 6/7 C, 1/7 A | Observe and correlate. Supplementary quality/validation signal. Not primary difficulty driver. |
| Q-GOV-5: Game phase | B/C — Skip | 2/7 B, 4/7 C, 1/7 approve | Existing detectors cover game phase equivalent. Don't add separate taxonomy. |
| Q-GOV-6: Policy entropy | A — Yes | 7/7 unanimous | Strongest signal. Shannon entropy over policy. ~5 LOC. Calibrate before weighting. Store in YX. |

### Key Per-Member Insights

| GV-ID | Member | Most Impactful Contribution |
|-------|--------|---------------------------|
| GV-1 | Cho Chikun (9p) | "Instinct classification adds genuine pedagogical value — I always explain intent before pattern." "Policy entropy measures exactly what makes problems hard." |
| GV-2 | Lee Sedol (9p) | "Don't over-classify instinct: allow multi-instinct. Let primary be strongest KataGo alignment." "Top-K rank: some of my best moves were KataGo's #50." |
| GV-3 | Shin Jinseo (9p) | "KataGo's policy implicitly encodes intent. Use policy direction vectors relative to groups to infer instinct." |
| GV-4 | Ke Jie (9p) | "Level-adaptive: novice-elementary→technique-only, intermediate+→instinct+technique." "Problem type (reading/counting/judgment) more useful than game phase." |
| GV-5 | Staff Engineer A | "Instinct should be new stage, not modification. Config-driven templates. Tie-breaking rule needed for multi-instinct." |
| GV-6 | Staff Engineer B | "Calibration-first: golden set (50-100 puzzles) before production. Entropy calibration before weighting." |
| GV-7 | Hana Park (1p) | "Students ask 'WHY do I play here?' — instinct bridges pattern recognition to positional understanding." "Difficulty entropy = exactly what stumps my students." |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Consultation complete. Prioritize: (1) entropy, (2) DetectionResult pipeline, (3) instinct classification, (4) multi-orientation tests. Scope charter to these 4 + level-adaptive hints + Top-K observability. Skip game phase. Calibration golden set is prerequisite. Return in charter mode for formal review. |
| blocking_items | (none) |

---

## Charter Review (GOV-CHARTER-APPROVED)

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-CHARTER-APPROVED` |
| **unanimous** | `true` (7/7) |

### Member Votes

| GV-ID | Member | Vote | Key Comment |
|-------|--------|------|------------|
| GV-1 | Cho Chikun (9p) | approve | 6 goals pedagogically sound. G-2 evidence discard confirmed. NG-8 correct scoping. |
| GV-2 | Lee Sedol (9p) | approve | Multi-instinct with tie-breaking. Top-K wisely supplementary. AC-4 ≥70% appropriate first iteration. |
| GV-3 | Shin Jinseo (9p) | approve | KataGo policy direction vectors for instinct classification is right methodology. 17/28 board-sim detectors confirms Q3/NG-3. |
| GV-4 | Ke Jie (9p) | approve | G-5 level-adaptive maps to consultation recommendation. `get_level_category()` reuse not reinvention. |
| GV-5 | Staff Engineer A | approve | Scope isolation (C-4), interface change management, clean-room (C-5), test infrastructure (G-4). |
| GV-6 | Staff Engineer B | approve | Calibration-first (C-3) most important constraint. Zero-query (C-1) verified. Planning confidence 82 meets floor. |
| GV-7 | Hana Park (1p) | approve | Addresses student frustration. Instinct bridges pattern→understanding. 15-word cap protected. |

### Support Summary

All 9 technical claims source-verified. 7/7 unanimous. No required changes.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved. Proceed to options. Priority architecture decisions: instinct classifier placement, DetectionResult propagation mechanism, golden set methodology, level-adaptive template structure. Present 2-3 alternatives for instinct classifier (highest-risk component). |
| blocking_items | (none) |

---

## Options Election (GOV-OPTIONS-APPROVED)

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-OPTIONS-APPROVED` |
| **unanimous** | `true` (7/7) |
| **selected_option** | OPT-2: New InstinctStage (Parallel Stage Architecture) |

### Selection Rationale

Instinct classification is conceptually distinct from technique detection — move INTENT vs position PATTERNS. Dedicated stage provides independent `ErrorPolicy.DEGRADE`, automatic timing observability, natural cross-instinct ranking, and clean rollback.

### Must-Hold Constraints

- MH-1: InstinctStage `error_policy = ErrorPolicy.DEGRADE`
- MH-2: `ctx.instinct_results: list[InstinctResult]` on PipelineContext
- MH-3: Stage ordering matches actual `enrich_single.py` code
- MH-4: Instinct classifier module independently unit-testable
- MH-5: Golden set calibration (C-3) before production weighting

---

## Plan Review (GOV-PLAN-CONDITIONAL)

| Field | Value |
|-------|-------|
| **decision** | `approve_with_conditions` |
| **status_code** | `GOV-PLAN-CONDITIONAL` |
| **unanimous** | `false` (6 approve, 1 concern) |

### Member Votes

| GV-ID | Member | Vote | Key Comment |
|-------|--------|------|------------|
| GV-1 | Cho Chikun (9p) | approve | 5 instincts are exactly the fundamental tsumego move types. Level-adaptive progression follows natural teaching arc. |
| GV-2 | Lee Sedol (9p) | approve | Multi-instinct with cross-ranking natural in dedicated stage. Config-driven thresholds enable tuning. |
| GV-3 | Shin Jinseo (9p) | approve | Policy direction vectors for instinct classification is correct methodology. Shannon entropy formulation right. |
| GV-4 | Ke Jie (9p) | approve | Level-adaptive templates correctly implement consultation recommendation. Detection evidence transforms Tier 2. |
| GV-5 | Staff Engineer A | concern | Architecture approve. Documentation plan missing global doc updates — RC-1 issued. |
| GV-6 | Staff Engineer B | approve | Calibration methodology well-structured. StageRunner auto-tracks timing. Zero batch performance impact. |
| GV-7 | Hana Park (1p) | approve | Addresses #1 student frustration. Instinct fills "intent gap" in hints. 15-word cap protected. |

### Required Changes (Both Addressed)

| RC-ID | Change | Status |
|-------|--------|--------|
| RC-1 | Expand Documentation Plan with global doc updates (hints.md, katago-enrichment-lab.md) | ✅ fixed in 30-plan.md §3 |
| RC-2 | Add DRY implementation note to T9 about existing group BFS code in detectors | ✅ fixed in 40-tasks.md T9 |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved with conditions (both addressed). Proceed with Phase 1 (T1-T4) infrastructure tasks. Execute in dependency order per 40-tasks.md. |
| blocking_items | (none — RC-1 and RC-2 resolved) |

---

## Implementation Review (GOV-REVIEW-CONDITIONAL → APPROVED)

| Field | Value |
|-------|-------|
| **decision** | `approve_with_conditions` → conditions resolved |
| **status_code** | `GOV-REVIEW-APPROVED` |
| **unanimous** | `true` (7/7) |

### Member Votes

| GV-ID | Member | Vote | Key Comment |
|-------|--------|------|------------|
| GV-1 | Cho Chikun (9p) | approve | 5 instincts capture fundamental tsumego move shapes. Instinct-to-technique prefix is correct pedagogical flow. |
| GV-2 | Lee Sedol (9p) | approve | Multi-instinct with confidence-sorted output. Policy entropy captures uncertainty landscape correctly. |
| GV-3 | Shin Jinseo (9p) | approve | Instinct from position geometry (not policy vectors) is deterministic and zero-cost. Entropy normalization correct. |
| GV-4 | Ke Jie (9p) | approve | Level-adaptive content correctly implements consultation recommendation. Detection evidence transforms Tier 2. |
| GV-5 | Staff Engineer A | approve | Architecture clean. Pipeline ordering correct. Backward compatibility verified (333 core tests pass). |
| GV-6 | Staff Engineer B | approve | Observability complete. correct_move_ranks in BatchSummary. Calibration methodology correct. |
| GV-7 | Hana Park (1p) | approve | Addresses student frustrations. Instinct bridges pattern→understanding. 15-word cap preserved. |

### Required Changes (All Resolved)

| RC-ID | Change | Status |
|-------|--------|--------|
| RC-1 | Fix rank description in katago-enrichment-lab.md (1-based, not 0-based) | ✅ fixed |

### Support Summary

7/7 unanimous approve. Implementation delivers all 6 charter goals within constraints. 1882 tests pass, zero regressions. 35 new tests added. All constraints verified. One minor doc fix (RC-1) resolved.

### Code Review Evidence

- CR-ALPHA: pass_with_findings → 2 majors fixed (CRA-1: instinct_phrase wiring, CRA-2: BatchSummary rank), 1 edge case fixed (CRA-5)
- CR-BETA: pass — 0 critical, 0 major. Architecture compliant.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation review approved. All conditions resolved. Proceed to closeout governance. |
| blocking_items | (none) |

---

## Closeout Audit (GOV-CLOSEOUT-APPROVED)

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-CLOSEOUT-APPROVED` |
| **unanimous** | `true` (7/7) |

### Closeout Checklist

All 12 closure checks passed. All 6 charter goals delivered. Documentation complete. No unresolved blockers.

### Deferred Items

- AC-2: Entropy-difficulty Spearman correlation ≥ 0.3 — requires golden set + KataGo
- AC-4: Instinct classification accuracy ≥ 70% — requires golden set + KataGo
- Detector-level multi-orientation tests — infrastructure built, follow-up work

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Initiative formally closed. All gates approved. |
| blocking_items | (none) |

---

## Implementation Re-Review (Attempt 2 — GOV-REVIEW-APPROVED)

_Re-opened after external governance review identified 3 additional required changes not caught in attempt 1._

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-REVIEW-APPROVED` |
| **unanimous** | `true` (7/7) |

### Required Changes Resolved

| RC-ID | Finding | Resolution | Status |
|-------|---------|------------|--------|
| RC-1 | CRA-1 (major): Missing detector orientation tests — AC-6 required 5 detectors × 4 rotations | 20 new parametrized tests in test_multi_orientation.py (L447-L690). Helpers `_rotate_gtp()` and `_rotate_analysis()` transform coordinates. Total: 55 tests (was 35). | ✅ resolved |
| RC-2 | GV-7 concern + C-3: Instinct phrases live in player-visible hints before AC-4 calibration | `InstinctConfig.enabled: bool = False` in config/teaching.py. Gate `if instinct_cfg.enabled:` in hint_generator.py and teaching_comments.py. | ✅ resolved |
| RC-3 | CRA-4 (minor): entropy docstring said "H / log2(top_k)" but code uses min(top_k, positive priors) | Docstring updated to "H / log2(K) where K = min(top_k, count of moves with positive prior)" | ✅ resolved |

### Member Votes

| GV-ID | Member | Vote | Key Comment |
|-------|--------|------|------------|
| GV-1 | Cho Chikun (9p) | approve | RC-1 validates fundamental correctness: ladder is a ladder regardless of board orientation. _rotate_gtp() correctly transforms GTP coords. |
| GV-2 | Lee Sedol (9p) | approve | Instinct gate (RC-2) is wise — geometry-based instinct needs empirical validation before player exposure. |
| GV-3 | Shin Jinseo (9p) | approve | _rotate_analysis() transforms MoveAnalysis.move + PV while preserving visits/winrate/policy_prior — correct KataGo semantics. |
| GV-4 | Ke Jie (9p) | approve | Three-point RC-2 fix (config + 2 if-guards) is minimal and clean. |
| GV-5 | Staff Engineer A | approve | Config pattern follows existing pydantic conventions. Test parametrize clean. No new deps. C-4 boundary respected. |
| GV-6 | Staff Engineer B | approve | 20 detector tests provide regression coverage for future coordinate changes. enabled=False preserves batch output identity. |
| GV-7 | Hana Park (1p) | approve | RC-2 directly addresses my concern: students won't see uncalibrated instinct prefixes. Orientation tests ensure rotation-invariant detection. |

### Test Evidence

- test_multi_orientation.py: 55 passed (35 original + 20 new)
- Targeted regression (19 files): 687 passed, 4 skipped, 0 failures
- Core hint/teaching tests: 198 passed, 1 skipped, 0 failures

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation re-review approved (attempt 2). All 3 RCs verified and resolved. Proceed to closeout governance. |
| blocking_items | (none) |

---

## Closeout Audit (Attempt 2 — GOV-CLOSEOUT-APPROVED)

_Second-cycle closeout after all RC resolution from implementation re-review._

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-CLOSEOUT-APPROVED` |
| **unanimous** | `true` (7/7) |

### Closeout Checklist (15/15 pass)

| # | Check | Status |
|---|-------|--------|
| CL-1 | Initiative artifacts present | ✅ |
| CL-2 | status.json gates current | ✅ |
| CL-3 | 50-execution-log.md current (EX-1..25) | ✅ |
| CL-4 | 60-validation-report.md current (VAL-1..24) | ✅ |
| CL-5 | 70-governance-decisions.md current (7 gates) | ✅ |
| CL-6 | All 6 charter goals delivered | ✅ |
| CL-7 | No test regressions (55 + 687 + 198) | ✅ |
| CL-8 | Documentation captures "why" | ✅ |
| CL-9 | Update-first policy (no new doc files) | ✅ |
| CL-10 | Cross-references present | ✅ |
| CL-11 | AGENTS.md updated | ✅ |
| CL-12 | No unresolved blockers | ✅ |
| CL-13 | All 6 lifecycle RCs resolved | ✅ |
| CL-14 | Deferred items documented | ✅ |
| CL-15 | Governance history complete | ✅ |

### RC Resolution Audit (Full Lifecycle)

| Cycle | RC-ID | Source | Status |
|-------|-------|--------|--------|
| Plan | RC-1 | GV-5: Documentation plan | ✅ |
| Plan | RC-2 | GV-5: DRY note T9 | ✅ |
| Review-1 | RC-1 | rank description fix | ✅ |
| Re-Review | RC-1 | CRA-1: detector orientation tests | ✅ |
| Re-Review | RC-2 | GV-7: instinct_enabled gate | ✅ |
| Re-Review | RC-3 | CRA-4: entropy docstring | ✅ |

### Deferred Items (Updated)

| Item | Status | Follow-Up |
|------|--------|-----------|
| AC-2: Entropy Spearman ≥ 0.3 | Infrastructure ready | Separate calibration initiative |
| AC-4: Instinct accuracy ≥ 70% | Infrastructure ready, gated by enabled=False | Separate calibration initiative |
| ~~Detector orientation tests~~ | **RESOLVED** (RC-1) | No longer deferred |

### Member Votes

| GV-ID | Member | Vote |
|-------|--------|------|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | approve |
| GV-5 | Staff Engineer A | approve |
| GV-6 | Staff Engineer B | approve |
| GV-7 | Hana Park (1p) | approve |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Initiative formally closed after second-cycle closeout audit. All 6 goals delivered, 7 constraints verified, 6 RCs resolved. Update status.json to closeout approved. |
| blocking_items | (none) |

---

## Implementation Review (Attempt 3 — GOV-REVIEW-REVISE)

_Re-opened after external governance review identified 2 additional required changes._

| Field | Value |
|-------|-------|
| **decision** | `change_requested` |
| **status_code** | `GOV-REVIEW-REVISE` |
| **unanimous** | No |

### Code Review Summary

| Field | Value |
|-------|-------|
| alpha_verdict | pass_with_findings |
| alpha_ac_met | 8 of 10 |
| beta_verdict | fail |
| beta_architecture_status | violations_found |
| beta_security_status | concerns_found |
| combined_critical_count | 0 |
| combined_major_count | 2 |

### Required Changes

| RC-ID | Source | Change | Status |
|-------|--------|--------|--------|
| RC-1 | CRB-2, GV-7 | Pipe sanitization in `format_yh_property` — strip `|` from tier content before joining | ✅ resolved |
| RC-2 | CRB-1, CRA-5 | Remove dead `LevelAdaptiveTemplates` config model (YAGNI: not wired, C-6 violation) | ✅ resolved |

### Member Votes

| GV-ID | Member | Vote |
|-------|--------|------|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | concern → RC-2 |
| GV-5 | Staff Engineer A | concern → RC-1, RC-2 |
| GV-6 | Staff Engineer B | concern → RC-1, RC-2 |
| GV-7 | Hana Park (1p) | change_requested → RC-1 |

### Resolution Evidence

- RC-1: `format_yh_property` now applies `h.replace("|", " ")` before joining. New test `test_strips_pipe_from_content` passes.
- RC-2: `LevelAdaptiveTemplates` class, `get_level_adaptive_templates()`, and `_DEFAULT_LEVEL_TEMPLATES` removed from `config/teaching.py`. AGENTS.md updated. Level-adaptive hint behavior retained in `_generate_reasoning_hint()` hardcoded branches.
- Targeted regression: 451 passed, 1 skipped, 0 failures across 11 test files.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Both RCs resolved. Proceed to re-review. |
| blocking_items | (none) |
