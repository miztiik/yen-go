# Clarifications

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07

---

| q_id | question                                              | options                                                                                                                                       | recommended     | user_response                                                                                                                       | status   |
| ---- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Q1   | Scope of fix — how many bugs?                         | A: BUG-1 only / B: BUG-1+5 / C: All bugs                                                                                                      | C               | **C: Fix all bugs, not just one.**                                                                                                  | answered |
| Q2   | Non-ASCII/Japanese chars in enrichment-added comments | A: Strip non-ASCII / B: Fix encoding chain / C: Preserve original C[], only add ASCII text                                                    | C               | **C: Preserve original C[] as-is. Do NOT add non-ASCII chars in enrichment text. Leave Japanese cleanup to downstream processors.** | answered |
| Q3   | Diagnostic data in SGF C[] properties                 | A: Remove from C[] / B: Move to property / C: Keep                                                                                            | A               | **A: Only teaching comments in C[]. Diagnostic data goes to logs only.**                                                            | answered |
| Q4   | Golden fixture regression test                        | A: Yes / B: No                                                                                                                                | A               | **A: Yes, encode this puzzle as a golden fixture.**                                                                                 | answered |
| Q5   | Logging — empty log files                             | —                                                                                                                                             | —               | **Fix. Logs not reaching enrichment log files.**                                                                                    | answered |
| Q6   | Log file naming alignment                             | —                                                                                                                                             | —               | **Align enrichment log naming with KataGo naming: `YYYYMMDD-HHMMSS-HASH.log`**                                                      | answered |
| Q7   | `enrich_single.py` decomposition                      | —                                                                                                                                             | —               | **Out of scope for this initiative. Already handled in `2026-03-07-refactor-enrich-single-decomposition` (at closeout).**           | answered |
| Q8   | Documentation updates                                 | —                                                                                                                                             | —               | **Yes: document what changes and why.**                                                                                             | answered |
| Q9   | DRY/SRP violation in three query paths                | A: Patch BUG-1 only (add 1 line) / B: Consolidate tsumego prep into single shared function / C: Merge SyncEngineAdapter into query_builder.py | B (see options) | **User: "This is a serious violation of DRY and SRP. Consider it seriously."**                                                      | answered |
| Q10  | Backward compatibility?                               | A: Required / B: Not required                                                                                                                 | B               | **Not required — broken output has no legitimate consumers.**                                                                       | answered |

> **See also**:
>
> - [00-charter.md](./00-charter.md) — Goals and acceptance criteria
> - [25-options.md](./25-options.md) — DRY refactor options
