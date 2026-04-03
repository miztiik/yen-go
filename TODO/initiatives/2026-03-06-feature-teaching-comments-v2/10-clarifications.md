# Clarifications — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Last Updated**: 2026-03-06

---

## Answered

### CQ-1: Is backward compatibility required? Should old code be removed?

**Answer**: No backward compatibility. One system. Old V1-only generation logic is superseded. There is no transition period, no two-tier degradation, no conditional paths. All puzzles go through the lab and get full enrichment.

**Source**: Product owner (2026-03-06), explicit and repeated.

---

### CQ-2: Should the system differentiate between lab and production?

**Answer**: No. Treat as one system. The lab IS the system. When it integrates with production, the transition is seamless — same code, same config, same output. No separate logic for "lab-processed" vs "production-processed" puzzles.

**Source**: Product owner (2026-03-06).

---

### CQ-3: Where should teaching comment config live?

**Answer**: Global config — `config/teaching-comments.json`. Not in the lab config (`config/katago-enrichment.json`). The lab config will eventually merge to global, but for teaching comments, use global now.

**Source**: Product owner (2026-03-06).

---

### CQ-4: Should all puzzles be enriched, or only a subset?

**Answer**: All puzzles. Not weakest-first, not strongest-first. Everything. "We solve it once and iterate upon that."

**Source**: Product owner (2026-03-06).

---

### CQ-5: Is KataGo engine access available for teaching comment generation?

**Answer**: Yes, always. Every puzzle has full engine access (policy, winrate, PV, ownership, enriched solution trees). No conditional logic needed.

**Source**: Product owner (2026-03-06), following from one-system principle.

---

## Answered (continued)

### CQ-6: Should previous GOV-V2 pedagogical decisions carry forward?

**Answer**: Yes, carry forward as design constraints. However, since the scope is expanding (full engine access, no conditional paths), the governance panel must RE-REVIEW them for potential ripple effects. The decisions themselves are assumed valid unless the panel identifies conflicts.

Previous decisions carried forward:

| Decision  | Content                                                                            |
| --------- | ---------------------------------------------------------------------------------- |
| GOV-V2-01 | Suppress vital-move annotation when `YO != strict`                                 |
| GOV-V2-02 | General→specific alias progression (parent tag on first move, alias on vital move) |
| GOV-V2-03 | Wrong-move condition priority by immediacy (first-match-wins)                      |
| GOV-V2-04 | Max 3 causal wrong-move annotations, ranked by refutation depth                    |
| C3        | HIGH confidence for specific techniques, CERTAIN for category tags                 |
| C4        | Signal replaces mechanism suffix (`comment_with_signal` field)                     |

**Source**: Product owner (2026-03-06). "Assume as-is, also review with the panel again because there might be ripple effects."

---

### CQ-7: Relationship to Phase B.4 — is this initiative the complete B.4 specification?

**Answer**: Yes. This initiative defines the complete teaching comment generation requirements. Phase B.4 is the execution vehicle. The scope EXPANDS B.4 with all additional improvements (vital move detection, causal wrong-move, move quality signals) plus governance review of the full package.

**Source**: Product owner (2026-03-06). "We need to expand and all the additional improvements — consult the review panel."

---

## Open Questions

None — all decision-critical ambiguities resolved.

**Assumed**: This initiative defines the complete teaching comment generation requirements. Phase B.4 is the execution vehicle. The initiative tasks will reference B.4's test structure.

---

## Compatibility & Migration

| Question                         | Answer                                                   |
| -------------------------------- | -------------------------------------------------------- |
| Backward compatibility required? | **No**                                                   |
| Remove old code?                 | **Yes** — V1-only generation in production is superseded |
| Transition period?               | **None** — all puzzles re-enriched                       |
| Two-tier degradation?            | **None** — KataGo always available                       |
| Config migration?                | Use global config from the start                         |
