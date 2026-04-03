# Clarifications

**Last Updated**: 2026-03-30

## Resolved

| q_id | question | answer | status |
|------|----------|--------|--------|
| Q1 | Does the solution work for ALL collection types? | Yes. No type check. 2+ sources → editions. Author, technique, graded, reference — all treated identically. | ✅ |
| Q2 | Is user choice (picking an edition) a must-have? | Yes. Must-have. | ✅ |
| Q3 | Are frontend changes in scope? | Yes. Both frontend and backend. | ✅ |
| Q4 | Where are editions stored? | Not in SGF. Editions are rows in `yengo-search.db` `collections` table with `attrs` JSON. Generated at publish time. SGF is unchanged. | ✅ |
| Q5 | How to avoid per-puzzle runtime checks at publish? | Add `collection_slug` column to `yengo-content.db`. Collision detection is one indexed SQL query per collection at ingest startup. Edition creation at publish is one `GROUP BY` query. | ✅ |
| Q6 | Is backward compatibility required? | No. New column is additive. Existing entries get NULL `collection_slug`. | ✅ |
| Q7 | What about auto-best for technique collections? | Deferred to v2. No calibration data exists. For v1, all multi-source collections get editions. | ✅ |
