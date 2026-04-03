# Clarifications — SQLite Puzzle Index

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2200-feature-sqlite-puzzle-index`

---

## Clarification Rounds

### Round 1 (User-initiated, resolved in conversation)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should old shard code be removed? | A: Keep shards + add SQLite / B: Clean break, delete shards | B | "No backward compatibility. Shards are removed entirely. Published files can be republished." | ✅ resolved |
| Q2 | Should the backend produce dual output (shards + DB)? | A: Dual output during transition / B: DB only from day one | B | "No dual output. DB is the replacement — not a parallel system." | ✅ resolved |
| Q3 | Two databases — what scope for each? | A: Search metadata / B: SGF content + dedup | Both A+B | "Two databases: one for searching metadata, another for storing files (SGF content + dedup)" | ✅ resolved |
| Q4 | Should IDs be numeric or text slugs? | A: Text slugs / B: Numeric IDs | B | "Use numbers for levels, techniques, collections — makes database smaller" | ✅ resolved |
| Q5 | Should DB files be git-tracked? | A: Git-tracked / B: .gitignore (build artifact) | B | ".gitignore — it's just a metadata artifact. Will decide later to add or not." | ✅ resolved |
| Q6 | Should rotation normalization be included? | A: Include (8 symmetries) / B: Skip | B | "No rotational normalization, it just complicates things" | ✅ resolved |
| Q7 | Should sorted AB/AW be used for canonical board hash? | A: Yes / B: No | A | "Yes, but consult Cho Chikun." Validated by Go prof as correct. | ✅ resolved |
| Q8 | FTS5 for collection search? | A: Yes / B: No | A | "Full text search should be supported. Collections will grow to ~5000." | ✅ resolved |
| Q9 | Collection references in metadata — text or numeric? | A: Text name / B: Numeric ID with separate collections table | B | "Collection number in metadata, table for collections with that numeral as reference" | ✅ resolved |
| Q10 |  Browser AI Constraint Removed | A: No / B: No | B | "We should update — browser now runs SQL via WASM.  | ✅ resolved |
| Q11 | Documentation updates required? | A: Incremental / B: Full overhaul | B | "Remove all old documentation, old references" | ✅ resolved |

### Round 2 (Research questions, resolved)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q12 | DB-2: Full SGF content or position hash only? | A: Full SGF / B: Hash only / C: Skip DB-2 | A | Q1-A (full SGF in DB-2) | ✅ resolved |
| Q13 | DB-1 compression? | A: Raw (CDN gzip) / B: Custom compression | A | "Does gzip cause issues with GitHub Pages?" — No, CDN auto-gzips. Confirmed A. | ✅ resolved |
| Q14 | db-version.json location? | A: yengo-puzzle-collections/ / B: Root | A | Q3-A | ✅ resolved |
| Q15 | FTS5 include aliases? | A: name+slug only / B: name+slug+aliases | B | Q4 — yes, with FTS5 (confirmed FTS5 is latest/best) | ✅ resolved |
| Q16 | WASM library choice? | A: sql.js / B: wa-sqlite / C: Official SQLite WASM | A | Q5 — sql.js (wasm) | ✅ resolved |

### Planner-Generated (no user ambiguity detected)

| q_id | question | resolution | status |
|------|----------|------------|--------|
| Q17 | Planning confidence score | 90/100 — architecture clear, tech proven, all decisions made | ✅ resolved |
| Q18 | Risk level | Low — localized change, mature library, clean break | ✅ resolved |
| Q19 | Research needed? | Completed: `20260313-research-sqlite-puzzle-index/15-research.md` | ✅ resolved |

---

## Decision Summary

All planning-blocking ambiguities resolved. No pending questions.
