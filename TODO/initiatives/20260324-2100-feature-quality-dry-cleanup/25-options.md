# 25 — Options

**Initiative**: 20260324-2100-feature-quality-dry-cleanup  
**Last Updated**: 2026-03-24  
**Governance RC-1**: Each option MUST assess parser placement cohesion.

---

## Options Comparison Matrix

| Dimension | OPT-1: Full Merge into `config.ts` + Delete `models/quality.ts` | OPT-2: Full Merge into `config.ts` + Thin Re-export Shim | OPT-3: Split — `config.ts` + `parsers.ts` + Delete `models/quality.ts` |
|-----------|------------------------------------------------------------------|----------------------------------------------------------|------------------------------------------------------------------------|
| **Summary** | Move all unique content from `models/quality.ts` into `config.ts`. Delete `models/quality.ts` entirely. Update 4 consumers to import from `@/lib/quality/config`. | Move all unique content into `config.ts`. Replace `models/quality.ts` body with re-exports from `config.ts`. 0 consumer changes. | Move config-derived types/constants into `config.ts`. Move SGF parsers + defaults into new `lib/quality/parsers.ts`. Delete `models/quality.ts`. Update consumers. |
| **Files modified** | 6 (config.ts, 4 consumers, delete 2 files) | 3 (config.ts, models/quality.ts rewrite, delete 1 file) | 7 (config.ts, new parsers.ts, 4 consumers, delete 2 files) |
| **Files deleted** | `generated-types.ts`, `models/quality.ts` | `generated-types.ts` | `generated-types.ts`, `models/quality.ts` |
| **Files created** | 0 | 0 | 1 (`lib/quality/parsers.ts`) |
| **Consumer changes** | 4 import path updates | 0 | 4+ import path updates |
| **Cohesion (RC-1)** | ⚠️ Medium — SGF parsers (`parseQualityMetrics`, `parseComplexityMetrics`) are pure string→struct transforms unrelated to config derivation. Mixing config-derived constants with wire-format parsers in one file. But file stays < 200 lines total. | ⚠️ Same as OPT-1 internally; models/quality.ts becomes pure re-export shim. | ✅ High — `config.ts` stays config-focused; `parsers.ts` holds SGF wire-format concerns. Clear separation of responsibilities. |
| **DRY** | ✅ Maximum — single file, zero duplication | ⚠️ Acceptable — re-export shim exists but adds no logic | ✅ Maximum — zero duplication, split by concern |
| **Dead code** | ✅ Zero — `models/quality.ts` fully deleted | ⚠️ `models/quality.ts` file persists as shim (9 re-export lines) | ✅ Zero |
| **Complexity** | Low — straightforward move + delete | Low — move + rewrite to re-exports | Medium — requires deciding what goes where, new file |
| **Test impact** | Existing tests continue (import from `config.ts`). Need tests for migrated parsers. | No test changes needed. | Need test file for new `parsers.ts`. |
| **Rollback** | Simple `git revert` | Simple `git revert` | Simple `git revert` |
| **Risk** | Low — known consumer surface | Very low — zero consumer changes | Low — slightly more files |
| **Architecture policy** | ✅ Dead code policy satisfied | ⚠️ Shim file persists (counter to "delete, don't deprecate") | ✅ Maximum cohesion but introduces new file (YAGNI concern for 2 parsers) |

---

## Detailed Option Descriptions

### OPT-1: Full Merge + Delete

**Approach**: Take the unique content from `models/quality.ts` — `PuzzleQualityLevel`, `PuzzleQualityInfo`, `PUZZLE_QUALITY_INFO`, `QualityMetrics`, `ComplexityMetrics`, `parseQualityMetrics()`, `parseComplexityMetrics()`, defaults, `getPuzzleQualityInfo()`, `isValidPuzzleQualityLevel()` — and add them to `config.ts`. Delete `models/quality.ts` and `generated-types.ts`. Update 4 consumers.

**Parser cohesion assessment (RC-1)**: Parsers are string→struct transforms with no config dependency. Placing them in `config.ts` creates a mild cohesion concern. However, `config.ts` is currently ~105 lines and would grow to ~175 lines — still manageable. The parsers are tightly coupled to the quality domain (they produce `QualityMetrics` using `PuzzleQualityLevel`), so co-location is defensible.

**Benefits**: Maximum simplicity. One file for everything quality. Dead code policy fully satisfied.

**Drawbacks**: Slight cohesion concern (parsers ≠ config). 4 consumer files need import updates.

**Recommendation**: ⭐ **Recommended**. Balances simplicity, DRY, and dead code policy. The cohesion concern is minor given the file stays under 200 lines and all types are quality-domain.

---

### OPT-2: Full Merge + Thin Re-export Shim

**Approach**: Same merge into `config.ts`, but instead of deleting `models/quality.ts`, rewrite it as:
```ts
// models/quality.ts — Thin re-export shim for backward compatibility
export { PuzzleQualityLevel, PuzzleQualityInfo, PUZZLE_QUALITY_INFO, ... } from '@/lib/quality/config';
```

**Parser cohesion assessment (RC-1)**: Same as OPT-1 — parsers end up in `config.ts`.

**Benefits**: Zero consumer changes. Minimal blast radius.

**Drawbacks**: Contradicts dead code policy ("delete, don't deprecate"). Shim file persists with no real purpose. Doesn't fully resolve the 3-file problem (becomes 2 files with a redirect).

---

### OPT-3: Split into `config.ts` + `parsers.ts`

**Approach**: Keep config-derived types/constants in `config.ts`. Create new `lib/quality/parsers.ts` for `QualityMetrics`, `ComplexityMetrics`, parser functions, defaults. Delete both `generated-types.ts` and `models/quality.ts`.

**Parser cohesion assessment (RC-1)**: ✅ Maximum cohesion — each file has a single concern.

**Benefits**: Best cohesion. Clean separation.

**Drawbacks**: Introduces a new file for only 2 functions + 2 interfaces + 2 constants (~60 lines). YAGNI concern — these parsers are unlikely to grow. More files to touch during execution.

---

## Recommendation

**OPT-1** is recommended. The cohesion concern (RC-1) is real but minor: `config.ts` stays under 200 lines, all types serve the quality domain, and the parsers produce types defined in the same file. Creating a separate `parsers.ts` (OPT-3) for ~60 lines of 2 functions violates YAGNI. The thin shim (OPT-2) contradicts the project's dead code policy.
