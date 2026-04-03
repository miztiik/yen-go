# Governance Decisions: Remove Dormant Dedup Infrastructure

**Last Updated:** 2026-03-05

## Panel Review History

### Review 1 — Initial Assessment (2026-03-05)

**Verdict:** concern  
**Context:** Initial evaluation of whether hash-based dedup is valuable.  
**Outcome:** Panel identified that fingerprint code is dormant. Recommended removing fingerprint infra, retaining content-hash.

### Review 2 — Content-Hash Effectiveness (2026-03-05)

**Verdict:** concern  
**Context:** User pointed out that content-hash hashes the ENTIRE SGF (including YM with run_id, comments, metadata), making it near-useless for cross-run or cross-source dedup.  
**Outcome:** Panel agreed content-hash is a naming scheme, not dedup. Recommended phased approach.

### Review 3 — Final Verdict (2026-03-05)

**Verdict:** approve (unanimous 6/6)  
**Context:** User resolved all open questions: backward compatibility not required, duplicates are OK, republish = reset.  
**Outcome:** Panel unanimously approved Option A (remove all dormant dedup infrastructure).

## Final Panel Votes

| Member           | Domain            | Verdict     | Rationale                                                                                                 |
| ---------------- | ----------------- | ----------- | --------------------------------------------------------------------------------------------------------- |
| Cho Chikun (9p)  | Classical tsumego | approve (A) | Duplicate positions with different comments serve different pedagogical purposes; filtering UX handles it |
| Lee Sedol (9p)   | Intuitive fighter | approve (A) | Different annotations on same position add value; removing dormant code is correct                        |
| Shin Jinseo (9p) | AI-era pro        | approve (A) | If needed at 500K+ scale, it can be rebuilt from git history; dormant code creates false confidence       |
| Ke Jie (9p)      | Strategic thinker | approve (A) | Cognitive overhead for contributors wondering why it exists is the real cost                              |
| Staff Engineer A | Systems architect | approve (A) | Project constitution says "Delete, don't deprecate. Git history preserves everything."                    |
| Staff Engineer B | Pipeline engineer | approve (A) | JSON registry wouldn't scale to 500K+ anyway; clean removal eliminates orphaned references                |

## Conditions

1. Git history is the archive — no need to copy code elsewhere before deletion
2. Run `pytest -m "not (cli or slow)"` after removal to confirm no hidden imports break
3. Grep for `dedup_registry` and `position_fingerprint` post-removal to catch stale references
4. Do NOT remove `generate_content_hash()` — that is active production code
