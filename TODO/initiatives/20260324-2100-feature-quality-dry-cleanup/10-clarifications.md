# 10 — Clarifications

**Initiative**: 20260324-2100-feature-quality-dry-cleanup
**Last Updated**: 2026-03-24

---

## Clarification Rounds

### Round 1 (Pre-resolved from handoff brief)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required for removed exports? | A: Yes, keep deprecated re-exports for 1 release / B: No, delete immediately / C: Other | B — 0 consumers of `generated-types.ts`, deprecated aliases unused | B | ✅ resolved |
| Q2 | Should old code (`generated-types.ts`, deprecated aliases) be removed? | A: Keep as deprecated / B: Delete immediately | B — dead code policy says "delete, don't deprecate" | B | ✅ resolved |
| Q3 | Where should merged content live — `lib/quality/config.ts` or new `lib/quality/index.ts` barrel? | A: Directly in `config.ts` / B: Create `index.ts` barrel that re-exports from `config.ts` / C: Other | A — minimal change, single canonical location, no barrel indirection | A | ✅ resolved |
| Q4 | Should `models/quality.ts` become a thin re-export shim or be fully deleted? | A: Thin re-export shim (no consumer changes) / B: Delete and update all 4 consumers | B — brief recommends updating consumers; dead code policy applies | B (resolved by OPT-1 governance election) | ✅ resolved |
| Q5 | Should `PUZZLE_QUALITY_INFO` constant be preserved as-is or derived from `QUALITIES` array? | A: Keep hardcoded Record<1-5, info> / B: Derive from QUALITIES in config.ts / C: Other | B — single computation from config JSON, no duplication | B | ✅ resolved |

### Notes

- Q4 has two viable approaches. **Q4-A** (thin shim) avoids touching 4 component files but leaves a redirect file. **Q4-B** (full delete) is cleaner but touches more files. Both are Level 2.  
- The brief recommends Q4-B or Q4-A. This is deferred to the user to confirm. Default recommendation is **Q4-A** (thin re-export) to keep the change minimal and avoid changing import paths in 4+ files and their tests, OR **Q4-B** for maximum cleanliness.

---

## Pre-resolved Context

- `generated-types.ts`: 0 source imports (confirmed via grep). 1 test file (`quality-generated-types.test.ts`) imports from `config.ts`, not `generated-types.ts`.
- `models/quality.ts` consumers: `QualityFilter.tsx`, `QualityBadge.tsx`, `QualityBreakdown.tsx`, `ComplexityIndicator.tsx` (4 components).
- Deprecated aliases: `QualityTier`, `QualityTierName`, `QualityTierInfo`, `QUALITY_TIER_INFO`, `getTierInfo`, `isValidTier` — zero external imports found via grep.
- SGF parsers (`parseQualityMetrics`, `parseComplexityMetrics`) only defined in `models/quality.ts`, only used by consumers that already import from that file.
