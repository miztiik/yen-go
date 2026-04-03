# Clarifications — Daily DB Migration

**Initiative**: `20260315-1500-feature-daily-db-migration`
**Last Updated**: 2026-03-15

## Round 1 — Resolved

| q_id | Question | Options | Recommended | user_response | status |
|---|---|---|---|---|---|
| Q1 | DB storage placement | A) Embed in `yengo-search.db` / B) Separate `yengo-daily.db` / C) Other | A | **A** — embed in existing `yengo-search.db` | ✅ resolved |
| Q2 | Rolling window size | A) Rolling 90 days / B) Current month / C) Full history / D) CLI flag | A | **A** — rolling window, **configurable**, default 90 days | ✅ resolved |
| Q3 | Backward compatibility with JSON files | A) Hard cutover / B) Parallel dual-mode / C) DB-first with fallback | A | **No backward compatibility** — hard cutover | ✅ resolved |
| Q4 | Old code removal | A) Delete all / B) Archive / C) Partial removal | A | **Yes — remove** all legacy JSON daily code | ✅ resolved |
| Q5 | Data model in DB | A) Minimal IDs / B) Denormalized / C) JSON blob | A | **A** — normalized `content_hash` IDs, JOIN to puzzles table | ✅ resolved |
| Q6 | Non-puzzle metadata (technique, timed sets) | A) `daily_metadata` table with `attrs` / B) Inline columns / C) JSON sidecar | A | **A** — separate `daily_metadata` table with `attrs` JSON column | ✅ resolved |
| Q7 | Backward compat required? Remove old code? | A) No compat, remove / B) Compat, keep / C) No compat, archive | A | **A** — no backward compat, remove old code | ✅ resolved |

## Additional Directives (from user)

1. **Docs updates mandatory** — all documentation must be updated as part of this work.
2. **Evolutionary architecture** — design for incremental evolution, not big-bang replacement.
3. **Integrate with publish stage** — daily generation should integrate with the publish pipeline stage via appropriate flags, not be a fully separate workflow.
4. **No rebuild/reconcile** — the daily table does not need full DB rebuild. New puzzle hashes are simply ingested/inserted into the daily tables. User wants governance opinion on whether this simplifies architecture.
5. **LOUD FAILURE** — daily generation must fail loudly and visibly (not silently swallow errors). It is its own process and failures must surface clearly.
