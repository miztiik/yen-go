# Clarifications — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Backward compatibility: retroactive update or future-only? | A: Future only / B: Retroactive / C: Other | A: Future only | A: Future only | ✅ resolved |
| Q2 | Remove `if text.startswith("Close")` special-casing? | A: Remove / B: Keep / C: Other | A: Remove | A: Remove | ✅ resolved |
| Q3 | RC-1 fix: prefix "Wrong." or add "close" to canonical list? | A: Prefix "Wrong." / B: Add to canonical / C: Both / D: Other | A: Prefix "Wrong." | A: Prefix "Wrong." | ✅ resolved |
| Q4 | RC-2: which tags suppress Tier 3 coordinate hints? | A: Tactical only / B: All first-move-IS-answer / C: Global depth 5+ / D: Directional guidance / E: Other | A: Tactical + depth hybrid | A: Tactical tags | ✅ resolved |
| Q5 | RC-3: net vs capture-race priority? | A: Net always wins / B: Confidence wins / C: Preserve original + net priority / D: Other | C: Preserve + net priority | C: Preserve + net priority | ✅ resolved |
| Q6 | RC-4: threshold fix strategy? | A: `>=` to `>` / B: Raise to 4 / C: Confidence weighting / D: Other | A: `>=` to `>` | A: `>=` to `>` | ✅ resolved |
| Q7 | RC-5: all-almost-correct policy? | A: 1 representative / B: Skip AI, keep curated / C: Widen one / D: Reduce count / E: Other | B: Skip AI, keep curated | B: Skip AI, keep curated | ✅ resolved |
| Q8 | Bundle or separate initiatives? | A: Single / B: Two groups / C: Five separate / D: Other | A: Single | A: Single | ✅ resolved |
