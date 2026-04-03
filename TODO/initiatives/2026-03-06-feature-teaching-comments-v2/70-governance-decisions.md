# Governance Decisions — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Last Updated**: 2026-03-06

---

## Decision 1: Options Election (2026-03-06)

**Gate**: options-review  
**Decision**: `approve`  
**Status Code**: `GOV-OPTIONS-APPROVED`  
**Unanimous**: Yes (6/6)

### Selected Option

| Field               | Value                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Option ID           | OPT-3                                                                                                                                                                                                                                                                                                                                                                                               |
| Title               | Layered Composition — Technique Base + Signal Overlay                                                                                                                                                                                                                                                                                                                                               |
| Selection Rationale | Fewest templates (34 vs 168), strongest fallback safety (V1 output when no signal), backward-compatible config extension, independently testable layers, most natural implementation of GOV-C4. Satisfies all charter constraints, respects SOLID/DRY/KISS/YAGNI, aligns with B.4 template engine design. One-system principle means Layer 2 uses engine data directly — no tree-heuristic proxies. |

### Must-Hold Constraints

1. 15-word cap enforced by assembly, not author counting
2. V1 fallback: no signal detected → emit V1 `comment` field verbatim
3. `technique_phrase` and `signal_phrase` independently authored and tested
4. `overflow_strategy: "signal_replaces_mechanism"` is the default and only strategy
5. Assembly edge cases (empty signal, empty technique, exact word cap) must have explicit test coverage
6. All 6 carried-forward decisions retained per verdicts below

### Support Table

| ID   | Member           | Domain              | Vote  | Key Rationale                                                                                                                         |
| ---- | ---------------- | ------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1 | Cho Chikun (9p)  | Classical tsumego   | OPT-3 | Clean separation mirrors professional annotation practice. Assembly-enforced word cap. V1 fallback preserves precision-over-emission. |
| GV-2 | Lee Sedol (9p)   | Intuitive fighter   | OPT-3 | Tag-agnostic signal phrases avoid forced pairings. Independent iteration. 34 vs 168 templates.                                        |
| GV-3 | Shin Jinseo (9p) | AI-era professional | OPT-3 | Engine signals feed Layer 2 directly. Signal misclassification safe (fallback to V1). Eliminates V2a/V2b split.                       |
| GV-4 | Ke Jie (9p)      | Strategic thinker   | OPT-3 | Best maintenance/iteration speed. One signal edit propagates to all 28 tags.                                                          |
| GV-5 | Staff Engineer A | Systems architect   | OPT-3 | DRY (34 vs 168). Independently testable layers. Additive config. Trivial rollback.                                                    |
| GV-6 | Staff Engineer B | Data pipeline       | OPT-3 | Microsecond overhead. Ideal observability point. Minimal config footprint.                                                            |

### Carried-Forward Decision Verdicts

| ID               | Decision                                | Verdict      | Clarification                                               |
| ---------------- | --------------------------------------- | ------------ | ----------------------------------------------------------- |
| CF-1 (GOV-V2-01) | Suppress vital-move when `YO != strict` | **RETAINED** | Pedagogical argument holds regardless of engine capability  |
| CF-2 (GOV-V2-02) | General→specific alias progression      | **RETAINED** | Alias feeds Layer 1 at vital move; signal layer independent |
| CF-3 (GOV-V2-03) | Wrong-move priority by immediacy        | **RETAINED** | Engine enhances condition detection, not ordering           |
| CF-4 (GOV-V2-04) | Max 3 causal wrong-move annotations     | **RETAINED** | Reflects cognitive science, not data scarcity               |
| CF-5 (GOV-C3)    | Confidence gate: HIGH/CERTAIN           | **RETAINED** | Engine improves tagger confidence upstream of gate          |
| CF-6 (GOV-C4)    | Signal replaces mechanism suffix        | **RETAINED** | OPT-3 `overflow_strategy` is canonical implementation       |

---

## Decision 2: Plan Review (2026-03-06)

**Gate**: plan-review  
**Decision**: `approve_with_conditions`  
**Status Code**: `GOV-PLAN-CONDITIONAL`  
**Unanimous**: Yes (6/6 `approve_with_conditions`)

### Required Changes Applied

| ID   | Severity        | Description                                                                                                    | Status                         |
| ---- | --------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| RC-1 | HIGH (blocking) | V1 removal: add subtask to T7 for deleting `analyzers/teaching_comments.py`, migrating imports, updating tests | ✅ Applied                     |
| RC-2 | MEDIUM          | T7 file list: include `enrich_single.py` as modified file                                                      | ✅ Applied                     |
| RC-3 | LOW             | Clarify `delta_annotations` preserved unchanged in V2 config                                                   | ✅ Applied (note in plan + T1) |
| RC-4 | LOW             | Codify parenthetical-as-one-word counting rule in `assembly_rules`                                             | ✅ Applied (plan + T3)         |

### Support Table

| ID   | Member           | Domain                 | Vote                    | Key Rationale                                                                                                                                                             |
| ---- | ---------------- | ---------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1 | Cho Chikun (9p)  | Classical tsumego      | approve_with_conditions | Two-layer model mirrors professional annotation. Alias progression essential. Thresholds reasonable. Expert review should be 75+ (accepted 50 as minimum). RC-1 blocking. |
| GV-2 | Lee Sedol (9p)   | Intuitive fighter      | approve_with_conditions | Wrong-move classifier is strongest improvement. T8 should include multi-technique overlap puzzles. RC-1 blocking.                                                         |
| GV-3 | Shin Jinseo (9p) | AI-era professional    | approve_with_conditions | Signal detection well-calibrated for KataGo. Edge case: `opponent_takes_vital` coincidental coordinate match — guard with ownership check. RC-1 blocking.                 |
| GV-4 | Ke Jie (9p)      | Strategic thinker      | approve_with_conditions | High information density (4 learning dimensions per comment). Parenthetical counting is natural. RC-1 blocking.                                                           |
| GV-5 | Staff Engineer A | Systems architect      | approve_with_conditions | Architecture clean. Schema `additionalProperties: false` requires T1 schema update first. V1 coexistence is a plan defect (RC-1). T7 must list orchestrator file (RC-2).  |
| GV-6 | Staff Engineer B | Data pipeline engineer | approve_with_conditions | Config-driven thresholds correct for observability. Delta annotations need disposition clarity (RC-3). Add signal detection rate logging in T7.                           |

### Panel Answers to Open Questions

| Question                         | Consensus                                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------------------------ |
| Q1: Signal threshold defaults    | Reasonable starting points. Configurable is the right pattern.                                   |
| Q2: Technique phrase cap         | 4 words with parenthetical-as-one-token. Codify in `assembly_rules`.                             |
| Q3: `opponent_takes_vital` value | Clear pedagogical value. Guard with ownership check for edge cases.                              |
| Q4: Expert review 50 puzzles     | Acceptable minimum. Stratify by tag + source. Include multi-technique and KataGo-hard positions. |

### Handover

| Field                 | Value                                                                                                                                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent            | Governance-Panel                                                                                                                                                                                                              |
| to_agent              | Feature-Planner                                                                                                                                                                                                               |
| message               | Plan approved pending RC-1 correction. RC-1 applied: T7 now includes V1 deletion subtask, orchestrator file modification, and test migration. RC-2/RC-3/RC-4 also applied. All blocking items resolved. Proceed to execution. |
| required_next_actions | 1. Update status.json to mark plan approved. 2. Package for Plan-Executor.                                                                                                                                                    |
| artifacts_to_update   | status.json, 70-governance-decisions.md                                                                                                                                                                                       |
| blocking_items        | None (RC-1 resolved)                                                                                                                                                                                                          |

---

## Decision 3: Implementation Review (2026-03-06)

**Gate**: implementation-review  
**Decision**: `approve`  
**Status Code**: `GOV-REVIEW-APPROVED`  
**Unanimous**: Yes (6/6)

### Verification Summary

All 4 RCs verified against code, all 4 GOV-V2 decisions honored, 131/131 tests pass, 4 docs + CHANGELOG updated. Architecture clean — no dependency violations, config-driven, SOLID/DRY/KISS/YAGNI compliant.

### Observations

| ID    | Severity | Description                                                                                        | Action              |
| ----- | -------- | -------------------------------------------------------------------------------------------------- | ------------------- |
| OBS-1 | INFO     | `test_teaching_comment_embedding.py` unmodified (imports from sgf_enricher, not teaching_comments) | No action required  |
| OBS-2 | INFO     | `docs/architecture/tools/katago-enrichment.md` references deleted V1 module                        | Future housekeeping |
| OBS-3 | INFO     | T8 (Expert Review) deferred — requires human expert                                                | Track separately    |

### Support Table

| GV-ID | Member           | Domain              | Vote    | Key Evidence                                                                                                                                       |
| ----- | ---------------- | ------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1  | Cho Chikun (9p)  | Classical tsumego   | approve | Two-layer model mirrors professional annotation. 8 wrong-move conditions cover primary tsumego failure modes. GOV-V2-01 vital suppression correct. |
| GV-2  | Lee Sedol (9p)   | Intuitive fighter   | approve | Signal layer explains WHY moves work. V1 fallback = right safety net. Wrong-move top-3 with refutation-depth ranking. Overflow strategy elegant.   |
| GV-3  | Shin Jinseo (9p) | AI-era professional | approve | Signal detection leverages KataGo strengths. Confidence gating prevents false teaching. sacrifice_setup uses tag presence (pragmatic).             |
| GV-4  | Ke Jie (9p)      | Strategic thinker   | approve | 4 learning dimensions in 15-word cap. Parenthetical counting (RC-4) critical. hc:2→3 enables data-driven threshold tuning.                         |
| GV-5  | Staff Engineer A | Systems architect   | approve | 4 modules with clear boundaries. Config injection, Pydantic validation. Schema additive. V1 deletion clean (0 live import refs).                   |
| GV-6  | Staff Engineer B | Data pipeline       | approve | Observability via hc_level. Config-driven thresholds. O(n log n) classification. Cached config loading. No new I/O deps.                           |

### Handover

| Field                 | Value                                                                                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent            | Governance-Panel                                                                                                                                                                         |
| to_agent              | Plan-Executor                                                                                                                                                                            |
| message               | Implementation approved unanimously. All RCs satisfied, all GOV-V2 decisions honored, 131/131 tests pass, docs updated. Proceed to closeout. T8 deferred, OBS-2 for future housekeeping. |
| required_next_actions | 1. Update status.json (governance_review: approved, closeout). 2. Complete initiative closeout. 3. Track T8 separately.                                                                  |
| artifacts_to_update   | status.json, 70-governance-decisions.md                                                                                                                                                  |
| blocking_items        | None                                                                                                                                                                                     |
