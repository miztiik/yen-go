# Governance Decisions — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Plan Review Decision

- **Decision**: `approve_with_conditions`
- **Status Code**: `GOV-PLAN-CONDITIONAL`
- **Unanimous**: No (5 approve, 1 concern — both concerns non-blocking)

---

## Panel Member Reviews

| Member           | Domain                      | Vote    | Supporting Comment                                                                                                                                                                                                                              |
| ---------------- | --------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cho Chikun (9p)  | Classical tsumego authority | concern | `{Technique} ({jp_term}) — {mechanism}` format is pedagogically sound. First-move-only embedding is a real limitation for multi-move forcing sequences — accept as V1 but document. joseki/fuseki should use CERTAIN (stricter than HIGH) gate. |
| Lee Sedol (9p)   | Intuitive fighter           | approve | 15-word max acceptable. Alias sub-comments for dead-shapes/tesuji valuable — students seeing bent-four should get specific comment. PV truncation fix (T-09) critical.                                                                          |
| Shin Jinseo (9p) | AI-era professional         | approve | KataGo PV truncation guard is correct mitigation. Confidence gating at HIGH+ well-calibrated. Delta annotation thresholds align with existing katago-enrichment.json.                                                                           |
| Ke Jie (9p)      | Strategic thinker           | approve | Practical learning value high. 28-tag full coverage with alias awareness addresses current gaps. dead-shapes alias set (bent-four, bulky-five, rabbity-six, l-group, straight-three) is correct.                                                |
| Staff Engineer A | Systems architect           | concern | Plan well-structured at Level 4. AD-3/AD-3b propose conflicting paths — consolidate on AD-3 (sgfmill-based). T-11 conflates teaching text with hint text — must use hint_text field, not full comment.                                          |
| Staff Engineer B | Data pipeline engineer      | approve | Config cached after first load. sgfmill approach efficient. T-20 cross-validation prevents drift. Test plan comprehensive (6 tasks).                                                                                                            |

---

## Required Conditions (3)

### Condition 1: Resolve AD-3/AD-3b implementation inconsistency

- **Issue**: AD-3 and AD-3b describe two conflicting SGF embedding approaches
- **Resolution**: Keep AD-3 (`_embed_teaching_comments()` using sgfmill). Remove AD-3b (`_compose_node` wiring). Repurpose T-14 to clean up dead `comments` parameter.
- **Status**: **RESOLVED** — 30-plan.md updated: AD-3b marked REMOVED; 40-tasks.md updated: T-14 repurposed to cleanup

### Condition 2: Clarify T-11 hint/teaching text boundary

- **Issue**: T-11 loads from teaching-comments.json but full comment text includes mechanism suffix that is spoilery for pre-solve YH hints
- **Resolution**: Added `hint_text` field per entry in config schema. `hint_text` = technique name + Japanese term only (e.g., "Snapback (uttegaeshi)"), NOT the full teaching comment. T-11 loads `hint_text` for YH Tier 1, not `comment`. T-05 schema updated.
- **Status**: **RESOLVED** — 30-plan.md AD-1 config updated with `hint_text` field; 40-tasks.md T-01/T-05/T-11 updated

### Condition 3: Document V1 first-move-only limitation

- **Issue**: First-move-only C[] embedding may miss actual tesuji in multi-move forcing sequences. joseki/fuseki need stricter gating.
- **Resolution**: T-18 updated to include "Known Limitations (V1)" section in docs. T-01 updated: joseki/fuseki entries use `"min_confidence": "CERTAIN"`.
- **Status**: **RESOLVED** — 40-tasks.md T-01 and T-18 updated

---

## Handover (consumed from Governance-Panel)

```yaml
handover:
  from_agent: Governance-Panel
  to_agent: Feature-Planner
  mode: plan
  decision: approve_with_conditions
  status_code: GOV-PLAN-CONDITIONAL
  message: >
    Plan is approved with 3 conditions that require artifact updates before
    execution begins. Resolve the AD-3/AD-3b implementation path conflict
    (pick sgfmill-based approach, drop _compose_node wiring). Clarify the
    T-11 hint text boundary so teaching comment mechanism text doesn't leak
    into pre-solve YH hints. Document the first-move-only V1 limitation in
    the docs task. Once these edits are made, update status.json to
    governance_review: "conditional_approved" and proceed to execution.
  required_next_actions:
    - "Update 30-plan.md: Remove AD-3b, consolidate on AD-3 approach"
    - "Update 40-tasks.md T-14: Repurpose or remove"
    - "Update 40-tasks.md T-11: Specify hint_text extraction strategy"
    - "Update 40-tasks.md T-05: If adding hint_text field, update schema task"
    - "Update 40-tasks.md T-18: Add Known Limitations section requirement"
    - "Update 40-tasks.md T-01: Set joseki/fuseki min_confidence to CERTAIN"
    - "Update status.json: governance_review → conditional_approved"
  artifacts_to_update:
    - "30-plan.md"
    - "40-tasks.md"
    - "status.json"
  blocking_items:
    - "AD-3/AD-3b conflict unresolved"
    - "T-11 hint/teaching text boundary unspecified"
```

### Resolution Status

All 3 conditions resolved. All blocking items cleared. Artifacts updated:

- [30-plan.md](30-plan.md) — AD-3b removed, `hint_text` field added to AD-1 config
- [40-tasks.md](40-tasks.md) — T-01 (CERTAIN for joseki/fuseki, hint_text field), T-05 (hint_text in schema), T-11 (hint_text extraction), T-14 (repurposed to cleanup), T-18 (V1 limitations)
- [status.json](status.json) — governance_review updated

---

## Tiny Status JSON (Plan Review)

```json
{
  "gate": "plan-review",
  "decision": "approve_with_conditions",
  "status_code": "GOV-PLAN-CONDITIONAL",
  "conditions_resolved": 3,
  "conditions_pending": 0,
  "unanimous": false,
  "has_supporting_comments": true,
  "next_agent": "Plan-Executor"
}
```

---

## Implementation Review Decision

- **Decision**: `approve`
- **Status Code**: `GOV-REVIEW-APPROVED`
- **Unanimous**: Yes (6/6)
- **Date**: 2026-03-06

### Panel Member Reviews

| Member           | Domain                      | Vote    | Supporting Comment                                                                                                                                        |
| ---------------- | --------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cho Chikun (9p)  | Classical tsumego authority | approve | Comment format pedagogically sharp. Dead-shape aliases Go-accurate. V1 limitation honestly documented. joseki/fuseki correctly gated at CERTAIN.          |
| Lee Sedol (9p)   | Intuitive fighter           | approve | Alias sub-comments are the key win — bent-four students get specific teaching. PV truncation guard correctly prevents false capture claims.               |
| Shin Jinseo (9p) | AI-era professional         | approve | KataGo PV quality is the right signal. Capture-verified template guard correctly conservative. Delta annotations align with katago-enrichment.json.       |
| Ke Jie (9p)      | Strategic thinker           | approve | Three-system separation maintained. hint_text isolation keeps hints spoiler-free. 28/28 coverage. Cross-validation test prevents drift.                   |
| Staff Engineer A | Systems architect           | approve | AD-3/AD-3b conflict resolved — single sgfmill code path. Dead comments param cleaned. Pydantic validation enforces confidence enum. Config well-factored. |
| Staff Engineer B | Data pipeline engineer      | approve | Config cached matching existing pattern. UTF-8 deviation correct. Phase 3 no-op path clean. 163 tests strong for Level 4. Early return fix clean.         |

### Condition Verification

| Condition              | Requirement                         | Verdict                                                                          |
| ---------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| 1: AD-3/AD-3b conflict | Consolidate on sgfmill AD-3         | PASS — `_embed_teaching_comments()` uses sgfmill. Dead `comments` param removed. |
| 2: hint_text boundary  | T-11 uses `hint_text` not `comment` | PASS — `_resolve_hint_text()` reads `entry.hint_text`.                           |
| 3: V1 limitation docs  | Known Limitations section           | PASS — docs/concepts/teaching-comments.md has V1 limitations section.            |

### Handover

```yaml
handover:
  from_agent: Governance-Panel
  to_agent: Plan-Executor
  mode: review
  decision: approve
  status_code: GOV-REVIEW-APPROVED
  message: >
    Implementation review APPROVED unanimously (6/6). All 20 tasks executed,
    all 3 plan-approval conditions verified in code, 163 tests passing with
    0 failures, documentation complete. Ready for closeout.
  required_next_actions:
    - "Update status.json: governance_review → approved, current_phase → closeout"
    - "Stage and commit all modified/created files to feature branch"
  artifacts_to_update:
    - "status.json"
  blocking_items: []
```

### Tiny Status JSON (Implementation Review)

```json
{
  "gate": "implementation-review",
  "decision": "approve",
  "status_code": "GOV-REVIEW-APPROVED",
  "unanimous": true,
  "has_supporting_comments": true,
  "next_agent": "Plan-Executor"
}
```
