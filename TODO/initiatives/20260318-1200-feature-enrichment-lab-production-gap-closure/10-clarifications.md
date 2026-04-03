# Clarifications - 2026-03-18

| q_id | question | options | recommended | user_response | status |
|---|---|---|---|---|---|
| Q1 | Is backward compatibility required, and should old code be removed? | A) Keep compatibility + legacy, B) Keep compatibility + deprecate, C) No compatibility + remove old, D) Other | C: clean production-final path, avoids dual-path complexity | C | ✅ resolved |
| Q2 | What is the exact target for this effort? | A) Planning-only gap audit with task package, B) Planning + immediate implementation, C) Audit report only, D) Other | A: governance-approved execution package first | A | ✅ resolved |
| Q3 | Scope priority for deferred NG items? | A) Evaluate NG-1/2/3/5 only, B) Evaluate NG-1..5 but NG-4 low priority, C) Evaluate only NG-1 and NG-5, D) Other | B: include all but keep NG-4 excluded unless extraordinary reason | B | ✅ resolved |
| Q4 | Evidence bar for objective completion? | A) code+tests+config fully wired, B) code-only, C) research rationale only, D) Other | A: strict, non-mock, functional objective closure | Functional objective met vs not met in code + tests + config, fully wired, not mocks | ✅ resolved |
| Q5 | Include initiative corpus as files or content? | A) include all files, B) include content only, C) docs only, D) other | B: use content extraction, avoid file-level noise | include the content, not the files | ✅ resolved |
| Q6 | Agent/model preference for research and coordination? | A) exact custom agent name only, B) available feature researcher, C) try both, D) other | Use GPT-5.3-Codex model path and best available subagent tools | Use GPT-5.3-Codex model for all research/coordination where possible | ✅ resolved |

## Scope Lock Notes

- Planning mode only for this initiative.
- Primary implementation surface: tools/puzzle-enrichment-lab.
- Evaluation corpus includes TODO enrichment plans, initiatives content, docs architecture/how-to/reference/archive where enrichment-specific.
- NG-4 (new tags taxonomy expansion) remains out unless extraordinary evidence emerges.
