# YenGo SGF Format Analysis: Industry Comparison & Recommendations

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/architecture/backend/sgf.md](../architecture/backend/sgf.md)
> Archived: 2026-03-24

**Author**: Gordon Player (1P) consulting Principal Systems Architect  
**Date**: January 27, 2026  
**Status**: Technical Analysis Document

---

## Executive Summary

This document provides a comprehensive analysis of YenGo's custom SGF properties, comparing them against:
1. The official SGF FF[4] specification
2. Common industry practices from major Go platforms
3. Best practices for tsumego/puzzle applications

**Key Finding**: YenGo's approach is **well-designed** but has some areas requiring standardization and documentation. The custom `Y*` prefix convention is appropriate and follows industry best practices for private properties.

**Related Documents**:
- [SGF Architecture Design](sgf-architecture-design.md) - Design rationale for all Y* properties
- [config/sgf-properties.schema.json](../../config/sgf-properties.schema.json) - JSON Schema definition

---

## 1. Current YenGo SGF Custom Properties

### 1.1 Properties in Use

| Property | Name | Description | Example | Status |
|----------|------|-------------|---------|--------|
| `YV` | Yengo Version | Schema version | `YV[4.0]` | ✅ Good |
| `YG` | Yengo Grade/Level | Difficulty with sub-level | `YG[intermediate:2]` | ✅ Fixed (9-level) |
| `YT` | Yengo Tags | Technique tags | `YT[snapback,ko]` | ✅ Good |
| `YH1` | Yengo Hint 1 | Region/area hint | `YH1[Focus on top-left]` | ✅ Unique value |
| `YH2` | Yengo Hint 2 | Technique hint | `YH2[snapback]` | ✅ Unique value |
| `YH3` | Yengo Hint 3 | Full text hint | `YH3[Look for...]` | ✅ Unique value |
| `YR` | Yengo Refutations | Wrong move hints | `YR[bb,cd]` | ✅ Pedagogical value |
| `YM` | Yengo Moves | Solution length | `YM[3]` | ⚠️ Redundant (see YX.d) |
| `YC` | Yengo Corner | Board region | `YC[TL]` | ✅ Good |
| `YQ` | Yengo Quality | Data richness | `YQ[q:2;rc:3;hc:1]` | ✅ spec-024 |
| `YX` | Yengo Complexity | Puzzle difficulty | `YX[d:5;r:13;s:24;u:1]` | ✅ NEW (spec-024) |
| `YK` | Yengo Ko | Ko context | `YK[direct:B2]` | ✅ Unique value |
| `YO` | Yengo Order | Move flexibility | `YO[strict]` | ⚠️ Rarely used |

### 1.2 Actual Usage in Published SGFs

From `yengo-puzzle-collections/sgf/`:
```sgf
(;FF[4]GM[1]SZ[19]CA[UTF-8]GN[3ba001edab9a42b0]PL[B]
AB[eb][fb][bc][cc][dc][be]AW[da][ab][bb][cb][db]
YV[3]YG[beginner:1]YT[life-and-death]
YH1[Focus on the top-left area]YH2[The first move is at ba]
)
```

**Observation**: Actual files use `YV[3]` not `YV[3.0]` - inconsistency in versioning.

---

## 2. Industry Comparison

### 2.1 Standard SGF FF[4] Properties (Official)

The official FF[4] specification provides NO standard properties for:
- ❌ Puzzle difficulty rating
- ❌ Technique/tag classification
- ❌ Progressive hints
- ❌ Quality metrics
- ❌ Board region focus

**This is a gap in the standard** that every puzzle platform addresses differently.

### 2.2 How Major Platforms Handle This

#### yengo-source
```sgf
; Historical approach - uses comments and implicit conventions
C[Black to play and live.]  ; Problem instruction in comment
GE[life and death]          ; Problem type (non-standard)
DI[7k]                      ; Difficulty level (non-standard)
```

From the Sensei's Library data:
- `GE` - Problem type ("joseki", "life and death", "tesuji", "endgame")
- `DI` - Difficulty (e.g., "7k", "1d")
- `CO`, `DP` - Unknown purpose (internal metadata)

#### SmartGo (Anders Kierulf - SGF inventor)
Uses extensive private properties with no prefix:
- `TY`, `TZ`, `TC` - Territory analysis
- `TU` - Time used to solve problem
- `NN` - Nodes examined during search
- `DE` - Search depth

#### KGS/yengo-source Online Servers
```sgf
KGSDE[...] ; Dead stones
KGSSB[...] ; Black score
KGSSW[...] ; White score
```
- Uses `KGS` prefix for private properties (best practice)

#### GoGoD (Professional Database)
- `OH` - Old Handicap system (accepted into spec)
- `KK` - Key/label for problem collections

#### Dragon Go Server
- `XM` - Next move number indicator

### 2.3 Industry Patterns Summary

| Feature | yengo-source | SmartGo | KGS | GoGoD | YenGo |
|---------|------------|---------|-----|-------|-------|
| Prefix Convention | ❌ None | ❌ None | ✅ `KGS*` | ❌ None | ✅ `Y*` |
| Difficulty | `DI[]` | ❌ | ❌ | ❌ | `YG[]` |
| Problem Type | `GE[]` | ❌ | ❌ | ❌ | `YT[]` |
| Hints | ❌ Comment | ❌ | ❌ | ❌ | `YH1/2/3[]` |
| Quality | ❌ | Various | ❌ | ❌ | `YQ[]` |
| Board Region | ❌ | ❌ | ❌ | ❌ | `YC[]` |

---

## 3. Detailed Property Analysis

### 3.1 `YG` - Difficulty Level

**Current Format**: `YG[intermediate:2]`

**Problem**: 
- The 5-level system in `SgfBuilder` (`beginner, basic, intermediate, advanced, expert`) conflicts with the 9-level system in `config/levels.json` (`novice` through `expert`)
- Sub-level (1-3) adds complexity

**Industry Comparison**:
- yengo-source uses `DI[7k]` - direct rank format
- SmartGo doesn't standardize difficulty

**Recommendation**: 
1. **Use rank-based format**: `YG[15k-11k]` or `YG[intermediate]` (no sub-level)
2. **Or use numeric level**: `YG[4]` mapping to config/levels.json
3. Remove sub-level - it adds complexity without clear value

**Impact Assessment**:
- Frontend parser needs update
- 5 adapters need update (`yengo-source`, `books101`, `yengo-source`, `yengo-source`, `yengo-source`)
- All existing SGFs need migration

### 3.2 `YT` - Tags

**Current Format**: `YT[snapback,ko,life-death]`

**Assessment**: ✅ **Well designed**
- Comma-separated is standard
- Maps to `config/tags.json` (single source of truth)
- 18 canonical tags is reasonable

**Industry Comparison**:
- Similar to yengo-source' `GE[]` but more comprehensive
- Better: supports multiple tags

**Recommendation**: Keep as-is. Consider adding category prefix option:
```
YT[tesuji:snapback,objective:ko]  ; Optional category prefix
```

### 3.3 `YH1/YH2/YH3` - Progressive Hints

**Current Format**: 
- `YH1[cb]` - Coordinate
- `YH2[snapback]` - Technique  
- `YH3[Look for the throw-in]` - Text

**Assessment**: ✅ **Unique value proposition**

No other platform provides structured progressive hints. This is YenGo's competitive advantage.

**Observation**: In actual SGFs, `YH1` contains text, not coordinates:
```
YH1[Focus on the top-left area]
YH2[The first move is at ba]
```

**Problem**: Spec says `YH1` should be coordinates, but implementation uses text.

**Recommendation**:
1. Either fix implementation to match spec
2. Or revise spec to match current behavior
3. Consider: `YH1` = region text, `YH2` = coordinate, `YH3` = technique/solution text

### 3.4 `YQ` - Quality Metrics

**Current Format**: `YQ[d:3;u:1;m:0.8;e:0.9;r:5;f:0.7]`

**Assessment**: ⚠️ **Overly complex for SGF**

| Key | Meaning | Useful? |
|-----|---------|---------|
| `d` | Depth (solution length) | ✅ Yes |
| `u` | Uniqueness (single answer?) | ✅ Yes |
| `m` | Misdirection | ⚠️ Subjective |
| `e` | Elegance | ⚠️ Subjective |
| `r` | Reading depth | ✅ Yes |
| `f` | Forcing ratio | ⚠️ Complex |

**Industry Comparison**: 
- No platform embeds this in SGF
- SmartGo stores separate analysis files
- GoGoD uses database metadata

**Recommendation**:
1. **Move to index file** (JSON), not SGF
2. Keep in SGF only: `YQ[d:3;u:1;r:5]` (objective metrics)
3. Subjective metrics belong in view indexes

### 3.5 `YM` - Move Count

**Current Format**: `YM[3]`

**Assessment**: ⚠️ **Redundant**

- Can be computed from solution tree
- Duplicates `YQ[d:N]`

**Recommendation**: Deprecate. Use `YQ[d:N]` if needed.

### 3.6 `YC` - Board Region

**Current Format**: `YC[TL]`, `YC[TL:3-3]`

**Assessment**: ✅ **Unique value**

No other platform provides this. Enables:
- Region-based filtering
- Focused practice (corners vs sides)
- Adaptive board display

**Recommendation**: Keep as-is. Document well.

### 3.7 `YK` - Ko Context  

**Current Format**: `YK[direct:B2,W1]`

**Assessment**: ✅ **Unique value**

Complex but necessary for proper ko puzzle handling. No other platform addresses this systematically.

**Recommendation**: Keep but ensure frontend can parse all variants.

### 3.8 `YR` - Refutation Moves

**Current Format**: `YR[bb,cd]`

**Assessment**: ✅ **Pedagogical value**

Marks common wrong moves for educational feedback.

**Recommendation**: Keep. Consider making frontend use these for "try again" hints.

### 3.9 `YO` - Move Order

**Current Format**: `YO[strict]`, `YO[1,2:flexible]`

**Assessment**: ⚠️ **Rarely needed**

Most puzzles have strict order. This adds complexity for edge cases.

**Recommendation**: 
- Keep but document as optional
- Default assumption: strict order (no `YO` property = strict)

### 3.10 `YV` - Version

**Current Format**: `YV[3.0]` (spec) vs `YV[3]` (actual)

**Assessment**: ⚠️ **Inconsistent**

**Recommendation**: 
- Standardize on `YV[3]` (simpler)
- Use semantic versioning only for breaking changes
- Document migration path

---

## 4. Comparison with Standard SGF Properties

### 4.1 Standard Properties YenGo Should Use

| Property | Current Usage | Recommendation |
|----------|--------------|----------------|
| `GN` | ✅ Used for puzzle ID | Good |
| `PL` | ✅ Side to move | Good |
| `SZ` | ✅ Board size | Good |
| `AB/AW` | ✅ Stone setup | Good |
| `C` | ⚠️ Underused | Use for source/credit |
| `TE` | ❌ Not used | Consider for first correct move |
| `BM` | ❌ Not used | Consider for refutation moves |
| `VW` | ⚠️ Inconsistent | Use for focused view |

### 4.2 Standard Properties for Move Annotation

The FF[4] spec provides these move annotation properties:
- `TE[1]` - Tesuji (good move) 
- `BM[1]` - Bad move
- `DO` - Doubtful move
- `IT` - Interesting move

**Current YenGo approach**: Uses comment markers like `C[Correct]`

**Recommendation**: Use standard `TE[1]` and `BM[1]` in solution tree:
```sgf
;B[cb]TE[1]C[Correct - threatens snapback]
  (;W[bb]BM[1]C[This fails...]
```

This improves compatibility with standard SGF viewers.

---

## 5. Documentation Recommendations

### 5.1 Where to Document

| Document | Purpose | Location |
|----------|---------|----------|
| SGF Schema Spec | Technical reference for all properties | `config/sgf-schema.md` (new) |
| Property Registry | Quick reference table | `config/README.md` (extend) |
| Levels Definition | Level system | `config/levels.json` ✅ exists |
| Tags Definition | Tag taxonomy | `config/tags.json` ✅ exists |
| Quality Tiers | Quality system | `config/quality.json` (new) |

### 5.2 Proposed `config/sgf-schema.md` Structure

```markdown
# YenGo SGF Schema v3.1

## Overview
YenGo extends SGF FF[4] with custom properties prefixed with `Y`.

## Custom Properties

### YV - Version
- Type: number
- Format: `YV[N]`
- Example: `YV[3]`
- Required: Yes
- Description: Schema version for migration compatibility

### YG - Level
- Type: simpletext
- Format: `YG[level-slug]`
- Example: `YG[intermediate]`
- Required: Yes
- Values: See config/levels.json
- Description: Difficulty classification

[... etc for each property ...]

## Validation Rules
1. YV must be present
2. YG must reference valid level from levels.json
3. YT tags must exist in tags.json
4. YH1/YH2/YH3 are optional but progressive
```

### 5.3 Benefits of Centralized Schema

1. **Frontend consistency** - TypeScript types generated from schema
2. **Backend validation** - Python validators reference same source
3. **Adapter compliance** - All ingestors follow same rules
4. **Tool compatibility** - External tools can validate

---

## 6. Second-Order Impact Analysis

### 6.1 If We Change `YG` Format

**From**: `YG[intermediate:2]`  
**To**: `YG[intermediate]`

| Component | Impact | Effort |
|-----------|--------|--------|
| Frontend `puzzleLoader.ts` | Parse change | 2hr |
| `SgfBuilder` | Remove sub-level | 1hr |
| `yengo-source/converter.py` | Update call | 30min |
| `books101/converter.py` | Update call | 30min |
| `yengo-source/enricher.py` | Update call | 30min |
| Existing SGFs | Migration script | 2hr |
| Tests | Update expectations | 2hr |
| **Total** | | **~8hr** |

**Benefits**:
- Simpler format
- Aligns with config/levels.json
- Easier to explain to users

### 6.2 If We Move `YQ` to Index Files

**From**: Embedded in SGF `YQ[d:3;u:1;...]`  
**To**: JSON index file

| Component | Impact | Effort |
|-----------|--------|--------|
| Publish stage | Add to JSON index | 2hr |
| Frontend | Read from index | 1hr |
| `SgfBuilder` | Remove YQ methods | 1hr |
| Adapters | No change (don't set YQ) | 0hr |
| **Total** | | **~4hr** |

**Benefits**:
- SGFs remain compatible with standard viewers
- Quality can be recalculated without regenerating SGFs
- Separates content (SGF) from metadata (JSON)

### 6.3 If We Fix `YH1/YH2/YH3` Semantics

**Current** (inconsistent):
- Spec: `YH1` = coordinate
- Actual: `YH1` = region text

**Options**:

| Option | Change | Impact |
|--------|--------|--------|
| A: Fix to match spec | `YH1[cb]` coordinate | High - all SGFs wrong |
| B: Update spec | `YH1` = region text | Low - document reality |
| C: Reorder | `YH1`=text, `YH2`=coord, `YH3`=technique | Medium |

**Recommendation**: Option B - accept current behavior, update spec.

---

## 7. Recommendations Summary

### 7.1 Immediate Actions (No Breaking Changes)

1. **Create `config/sgf-schema.md`** - Document all Y* properties
2. **Fix `YV` consistency** - Use `YV[3]` everywhere
3. **Update spec for `YH1/YH2/YH3`** - Match actual behavior
4. **Add `TE[1]`/`BM[1]`** to solution tree - Standard compliance

### 7.2 Short-term Improvements

1. **Simplify `YG`** - Remove sub-level (`:N`)
2. **Move subjective metrics from `YQ`** to index files
3. **Deprecate `YM`** - Redundant with depth in `YQ`

### 7.3 Long-term Considerations

1. **Submit proposal to SGF standards** - `DI` for difficulty is common need
2. **Create JSON Schema** for `config/sgf-schema.json` - Machine validation
3. **TypeScript types** auto-generated from schema

---

## 8. Appendix: Full Property Reference

### A. YenGo Custom Properties

```
YV[version]           ; Schema version (required)
YG[level]             ; Difficulty level (required)
YT[tag1,tag2,...]     ; Technique tags (required)
YH1[hint]             ; Region hint (optional)
YH2[hint]             ; Technique hint (optional)
YH3[hint]             ; Full text hint (optional)
YR[coord1,coord2]     ; Refutation coordinates (optional)
YC[region]            ; Board region (optional)
YQ[d:N;u:B;...]       ; Quality metrics (optional)
YK[ko-type]           ; Ko context (optional)
YO[order]             ; Move order flexibility (optional)
```

### B. Standard Properties Used

```
GM[1]                 ; Game type (Go)
FF[4]                 ; File format version
CA[UTF-8]             ; Character encoding
SZ[19]                ; Board size
GN[puzzle-id]         ; Puzzle identifier
PL[B|W]               ; Side to move
AB[coord][coord]      ; Black stones
AW[coord][coord]      ; White stones
C[text]               ; Comment
VW[coords]            ; View (crop) region
TE[1]                 ; Good move marker
BM[1]                 ; Bad move marker
```

### C. Properties NOT to Use

```
DI[]    ; Non-standard, conflicts with our YG
GE[]    ; Non-standard, use YT instead
KK[]    ; GoGoD-specific
```

---

## 9. Decision Matrix

| Property | Keep? | Change? | Action |
|----------|-------|---------|--------|
| `YV` | ✅ | Format | Standardize to `YV[3]` |
| `YG` | ✅ | Simplify | Remove sub-level |
| `YT` | ✅ | No | Document well |
| `YH1/2/3` | ✅ | Document | Match spec to reality |
| `YR` | ✅ | No | Document well |
| `YC` | ✅ | No | Document well |
| `YQ` | ⚠️ | Move | Keep only objective metrics in SGF |
| `YK` | ✅ | No | Document well |
| `YO` | ⚠️ | Optional | Make truly optional |
| `YM` | ❌ | Remove | Deprecate (redundant) |

---

*Document prepared for architectural review. Recommend scheduling discussion with frontend and pipeline teams before implementing changes.*
