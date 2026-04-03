# Analysis — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Last Updated**: 2026-03-06

---

## Planning Confidence

| Metric                    | Value                                                   |
| ------------------------- | ------------------------------------------------------- |
| Planning Confidence Score | 78/100                                                  |
| Risk Level                | medium                                                  |
| Research invoked          | No — previous research (15-research.md §1-6) sufficient |

Deductions: -10 (template design choices), -12 (signal×technique interaction under 15-word cap)

---

## Cross-Artifact Consistency

| Check | Status                                 | Notes                                                 |
| ----- | -------------------------------------- | ----------------------------------------------------- |
| F1    | Charter goals ↔ option scope           | ✅ All 6 goals addressed by OPT-3 layers              |
| F2    | Charter constraints ↔ option design    | ✅ All 7 constraints (C1-C7) satisfied                |
| F3    | Clarification answers ↔ charter        | ✅ One-system principle reflected throughout          |
| F4    | Carried-forward decisions ↔ plan       | ✅ All 6 CF decisions retained, panel re-reviewed     |
| F5    | Option selected ↔ governance decision  | ✅ OPT-3, unanimous (6/6)                             |
| F6    | Phase B.4 alignment ↔ initiative scope | ✅ This initiative IS the B.4 specification, expanded |

---

## Coverage Map

### Charter Goals → Implementation Components

| Goal                            | Component                                                 | Covered in Plan |
| ------------------------------- | --------------------------------------------------------- | --------------- |
| G1: Explain WHY moves work/fail | Layer 2 signal phrases + assembly                         | ✅              |
| G2: Annotate vital moves        | Vital move detector + Layer 1 alias progression           | ✅              |
| G3: Improve wrong-move feedback | Wrong-move refutation classifier + expanded templates     | ✅              |
| G4: Position-aware comments     | `{coord}` token substitution in both layers               | ✅              |
| G5: Move quality signals        | Signal detector (vital/forcing/unique/non-obvious)        | ✅              |
| G6: Complete coverage           | One system, KataGo always available, no conditional paths | ✅              |

### Acceptance Criteria → Tasks

| AC                                    | Task Coverage                            |
| ------------------------------------- | ---------------------------------------- |
| AC1: 28 tags have `{coord}` templates | T2 (technique phrases)                   |
| AC2: Vital move detection             | T4 (vital move detector)                 |
| AC3: Wrong-move causal explanations   | T5 (wrong-move classifier + templates)   |
| AC4: Complete coverage                | T7 (integration), T9 (full suite)        |
| AC5: 15-word cap                      | T3 (assembly rules), T6 (assembly tests) |
| AC6: Config schema validated          | T1 (config extension), T3 (schema)       |
| AC7: Expert review ≥50 puzzles        | T8 (expert review)                       |
| AC8: All tests pass                   | T9 (full test suite)                     |

---

## Risk Analysis

| ID  | Risk                                                                      | Severity | Mitigation                                                                                                             |
| --- | ------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
| R1  | Assembly produces awkward phrasing for some technique+signal combinations | MEDIUM   | Expert review of all 28×6 compositions. Signal phrases designed for brevity. Assembly tests for naturalness.           |
| R2  | 15-word cap forces aggressive truncation on some tag+signal combinations  | MEDIUM   | `technique_phrase` kept to 2-4 words. Signal phrases kept to ≤10 words. Assembly overflow strategy replaces mechanism. |
| R3  | Signal misclassification (engine misjudges seki/complex ko)               | LOW      | Precision-over-emission: signal suppressed when uncertain. V1 fallback is safe. Confidence gates apply.                |
| R4  | Wrong-move refutation trees too shallow for causal classification         | LOW      | Guard: only emit causal explanation when refutation evidence exceeds threshold. Default template fallback.             |
| R5  | Config schema change breaks existing tooling                              | LOW      | Additive extension only. No existing field removed or renamed. Schema version bump.                                    |

---

## Unmapped Tasks

None identified. All charter goals, acceptance criteria, and governance constraints have task assignments.

---

## Findings

| ID  | Severity | Finding                                                                                                                                                                                                  |
| --- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | INFO     | OPT-3's assembly step is a new code unit with no existing equivalent. Needs dedicated edge-case tests (empty inputs, exact word cap, multi-word Japanese terms).                                         |
| F2  | INFO     | The 6 signal types (vital_point, forcing, non_obvious, unique_solution, sacrifice_setup, opponent_takes_vital) are a starting set. Config is extensible — new signals can be added without code changes. |
| F3  | INFO     | Alias progression (CF-2/GOV-V2-02) interacts with Layer 1 only. At the vital move, `technique_phrase` is the alias phrase, not the parent. Signal layer is independent.                                  |
| F4  | WARN     | The `hc` quality metric needs updating: `hc:2` for V1 technique-only, `hc:3` for technique+signal (OPT-3 output). This is a pipeline metadata change.                                                    |
| F5  | INFO     | Old V1 initiative (`2026-03-05-feature-teaching-comments-overhaul`) research sections 1-6 remain valid factual references. Sections 7-11 are superseded by this initiative.                              |
