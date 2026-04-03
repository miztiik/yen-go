# Clarifications: Inventory Reset Transaction Safety

**Last Updated**: 2026-03-10

## Clarification Rounds

### Round 1 (from forensic investigation, 2026-03-09/10)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? | A: Yes / B: No | B: No — internal pipeline fix, no public API | B: No | ✅ resolved |
| Q2 | Should old code be removed? | A: Yes / B: No | A: Yes — replace unsafe pattern | A: Yes | ✅ resolved |
| Q3 | Is the existing `--dry-run false` guard sufficient, or do we need an additional confirmation flag? | A: Sufficient / B: Add `--confirm-reset-inventory` | A: Sufficient — user confirmed `--dry-run false` already provides adequate protection | A: Sufficient | ✅ resolved |
| Q4 | Should we add provenance metadata (actor, host, pid, etc.) to inventory mutations? | A: Yes (in this initiative) / B: Separate initiative | B: Separate initiative — keep this change focused | B: Separate | ✅ resolved |
| Q5 | Should we add auto-heal / startup reconciliation? | A: Yes (in this initiative) / B: Separate initiative | B: Separate — different concern | B: Separate | ✅ resolved |
| Q6 | Correction level assessment? | Lv1 / Lv2 | Lv1-2: Single file ~30-50 lines | Lv1-2 | ✅ resolved |

## Key Decisions

- **Option A (transaction safety)** is the user's preferred direction — simple, structural, addresses root cause directly
- **Option B (extra CLI guardrails)** deemed unnecessary — `--dry-run false` already exists
- **Option C (auto-heal)** and **Option D (provenance)** deferred to separate initiatives
- User suspects a test may be calling the reset path — to be verified during implementation
