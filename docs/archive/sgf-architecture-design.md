# YenGo SGF Architecture Design

> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [docs/architecture/backend/sgf.md](../architecture/backend/sgf.md)
> Archived: 2026-03-24

**Author**: Gordon Player (1P) consulting Principal Systems Architect  
**Date**: January 27, 2026  
**Status**: Normative Design Document  
**Version**: 1.0

---

## Purpose

This document defines the **architectural design rationale** for YenGo's custom SGF properties. It explains WHY each property exists, what problem it solves, and how it fits into the overall system architecture.

For implementation details and industry comparison, see [sgf-format-analysis.md](sgf-format-analysis.md).

---

## Design Philosophy

### Core Principles

1. **Standard-Compliant Extension**: Use SGF FF[4] as foundation, extend only where gaps exist
2. **Private Property Namespace**: `Y*` prefix prevents collision with standard properties
3. **Single Source of Truth**: Config-driven values, never hardcoded
4. **Offline-First**: All data serializable to static files, no runtime computation
5. **Pedagogical Focus**: Properties designed for teaching, not just storage

### Why Custom Properties?

The SGF FF[4] specification provides **no standard properties** for:
- Puzzle difficulty rating
- Technique/tag classification
- Progressive hints
- Quality/complexity metrics
- Board region focus

Every puzzle platform addresses this differently. YenGo's `Y*` namespace follows the recommended practice (similar to KGS's `KGS*` prefix).

---

## Property Catalog

### Version Property

| Property | `YV` - YenGo Version |
|----------|----------------------|
| **Format** | `YV[4]` (integer) |
| **Purpose** | Schema version for backward-compatible parsing |
| **Why It Exists** | As we evolve the SGF schema (adding properties, changing formats), parsers need to know which version they're reading. Without versioning, we couldn't safely migrate existing puzzles. |
| **Design Decision** | Integer versioning (no decimals). Increment by 1 for each major change. Simpler parsing, clearer semantics. |
| **Current Version** | `4` (spec-025 increment from 3) |
| **Source of Truth** | Pipeline configuration |
| **Note** | Version is always an integer. Future versions increment by 1 (5, 6, 7...). No decimal versions like 4.1 or 4.2. |

---

### Difficulty Property

| Property | `YG` - YenGo Grade/Level |
|----------|--------------------------|
| **Format** | `YG[intermediate:2]` → `YG[intermediate]` (spec-025) |
| **Purpose** | Puzzle difficulty classification for filtering/progression |
| **Why It Exists** | The standard SGF has no difficulty concept. Players need to find puzzles at their skill level. The 9-level system maps to Go ranks (30k-9d). |
| **Design Decision** | Use slugs from `config/levels.json`, not numeric IDs, for human-readability. Sub-levels deprecated in spec-025 for simplicity. |
| **9-Level System** | novice → beginner → elementary → intermediate → upper-intermediate → advanced → low-dan → high-dan → expert |
| **Source of Truth** | [config/levels.json](../config/levels.json) |

**Why 9 Levels?** 
- 5 levels (old system) was too coarse - a "beginner" puzzle could span 10 kyu ranks
- 9 levels provide ~5 rank granularity: Novice (30k-26k), Beginner (25k-21k), etc.
- Maps cleanly to DDK/SDK/Dan progression stages

---

### Classification Property

| Property | `YT` - YenGo Tags |
|----------|-------------------|
| **Format** | `YT[snapback,ko,life-and-death]` |
| **Purpose** | Technique classification for drill selection |
| **Why It Exists** | Players want to practice specific techniques (e.g., "I need to work on snapbacks"). Tags enable technique-focused study, not just difficulty-based progression. |
| **Design Decision** | Comma-separated slugs for simplicity. One puzzle can have multiple tags (multi-technique problems). |
| **18 Canonical Tags** | life-and-death, tesuji, capture, connect, escape, kill, ko, ladder, liberty, net, placement, reading, seki, semeai, shape, snapback, squeeze, throw-in |
| **Source of Truth** | [config/tags.json](../config/tags.json) |

**Why These Tags?**
- Derived from Go pedagogy literature (Cho Chikun, Go Seigen)
- Focus on tsumego-relevant techniques (excluded joseki, fuseki)
- 18 tags balances granularity with usability

---

### Hint Properties

| Property | `YH1`, `YH2`, `YH3` - YenGo Hints |
|----------|-----------------------------------|
| **Format** | `YH1[cb]`, `YH2[snapback]`, `YH3[Look for the weakness in white's shape]` |
| **Purpose** | Progressive hint system for learning |
| **Why It Exists** | Standard SGF only has comments (`C[]`). YenGo needs structured, progressive hints that UI can reveal one at a time. Three levels: position → technique → full explanation. |
| **Design Decision** | Three properties (not array) for simplicity. Each hint type has different semantic meaning. |

**Three Hint Levels:**
| Level | Property | Type | Example | Use Case |
|-------|----------|------|---------|----------|
| 1 | `YH1` | Coordinate | `cb` | "Focus here" - narrows search area |
| 2 | `YH2` | Tag slug | `snapback` | "Try this technique" - suggests approach |
| 3 | `YH3` | Free text | `Look for the weakness...` | Full explanation - learning resource |

---

### Refutation Property

| Property | `YR` - YenGo Refutations |
|----------|--------------------------|
| **Format** | `YR[bb,cd]` |
| **Purpose** | Highlight common wrong moves |
| **Why It Exists** | Pedagogically, understanding WHY a move is wrong is as valuable as knowing the right answer. `YR` identifies moves that look good but fail, enabling the UI to provide teaching moments. |
| **Design Decision** | Coordinate list (comma-separated). These are first-moves that have refutation branches in the solution tree. |

**Pedagogical Value:**
- When player makes a `YR` move, show the refutation sequence
- Enables "try again" learning flow instead of immediate "wrong"
- Source data: derived from solution tree refutation branches

---

### Board Region Property

| Property | `YC` - YenGo Corner |
|----------|---------------------|
| **Format** | `YC[TL]`, `YC[center]` |
| **Purpose** | Board region for viewport optimization |
| **Why It Exists** | Most tsumego are local (corner/side). Knowing the region enables the UI to zoom/focus appropriately without computing stone bounding boxes. |
| **Values** | `TL`, `TR`, `BL`, `BR` (corners), `T`, `B`, `L`, `R` (sides), `center` |
| **Design Decision** | Pre-computed at import time. Stored as single value (not computed from stones). |

---

### Ko Context Property

| Property | `YK` - YenGo Ko |
|----------|-----------------|
| **Format** | `YK[direct:B2]`, `YK[none]` |
| **Purpose** | Ko situation context |
| **Why It Exists** | Ko is fundamental to Go. A puzzle might require understanding ko threats, ko fights, or explicitly exclude ko situations. This metadata enables ko-specific filtering and UI treatment. |
| **Values** | `none`, `direct:<coord>`, `approach:<coord>`, `threat` |
| **Design Decision** | Structured format with ko type and coordinate when applicable. |

---

### Move Order Property

| Property | `YO` - YenGo Order |
|----------|-------------------|
| **Format** | `YO[strict]`, `YO[flexible]` |
| **Purpose** | Solution flexibility indicator |
| **Why It Exists** | Some problems have exactly one correct sequence (miai-style problems). Others have multiple valid orders. This affects how the solution validator scores player moves. |
| **Values** | `strict` (exact order required), `flexible` (multiple valid orders) |
| **Status** | ⚠️ Rarely used - considered for deprecation |

---

### Quality Property (spec-024)

| Property | `YQ` - YenGo Quality |
|----------|----------------------|
| **Format** | `YQ[q:2;rc:3;hc:1]` |
| **Purpose** | Data richness indicator (how well documented) |
| **Why It Exists** | Not all puzzles are equal quality. Some have full solution trees, refutations, and comments. Others only have a single correct line. Quality tier enables filtering and weighting in algorithms. |
| **Defined In** | [specs/024-puzzle-quality-system](../specs/024-puzzle-quality-system/spec.md) |

**Quality Metrics:**
| Field | Key | Type | Description |
|-------|-----|------|-------------|
| Quality Tier | `q` | 1-5 | Data completeness (1=Premium, 5=Minimal) |
| Refutation Count | `rc` | int | Number of wrong-move branches |
| Has Comments | `hc` | 0/1 | Whether solution has teaching comments |

**Quality Tiers:**
| Tier | Name | Criteria |
|------|------|----------|
| 1 | Premium | Solution tree + ≥3 refutations + comments |
| 2 | High | Solution tree + ≥2 refutations + comments |
| 3 | Standard | Solution tree + ≥1 refutation |
| 4 | Basic | Solution tree only |
| 5 | Minimal | No solution tree |

---

### Complexity Property (spec-024)

| Property | `YX` - YenGo Complexity |
|----------|-------------------------|
| **Format** | `YX[d:5;r:13;s:24;u:1]` |
| **Purpose** | Puzzle difficulty metrics (how hard to solve) |
| **Why It Exists** | Quality (YQ) measures DATA richness. Complexity (YX) measures PUZZLE difficulty. A simple 3-move problem might have premium quality documentation. A deep 20-move problem might have minimal documentation. These are orthogonal concerns. |
| **Defined In** | [specs/024-puzzle-quality-system](../specs/024-puzzle-quality-system/spec.md) |

**Complexity Metrics:**
| Field | Key | Range | Description |
|-------|-----|-------|-------------|
| Solution Depth | `d` | 1-50 | Moves in main correct line |
| Reading Count | `r` | 1-999 | Total nodes in solution tree |
| Stone Count | `s` | 1-361 | Total stones on board |
| Uniqueness | `u` | 0/1 | Single correct first move? |

**Why Separate from YG (Level)?**
- `YG` is a human classification (editorial judgment)
- `YX` is computed metrics (objective measurement)
- They correlate but aren't identical - a novice puzzle could have deep reading if it's a classic problem

**Computation:** All YX metrics are derived from tree analysis at build time - NO AI/KataGo required.

---

### Move Count Property

| Property | `YM` - YenGo Moves |
|----------|-------------------|
| **Format** | `YM[3]` |
| **Purpose** | Solution length hint |
| **Why It Exists** | Tells player how many moves to find. Useful for filtering ("show me 3-move problems"). |
| **Status** | ⚠️ Redundant with `YX.d` (solution_depth). Consider deprecation. |

---

## Property Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    YenGo SGF Properties                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  METADATA                           PEDAGOGY                     │
│  ─────────                          ────────                     │
│  YV[4] ←── Version (int)           YH1[cb] ←── Position Hint    │
│                                     YH2[snapback] ←── Tech Hint │
│                                     YH3[...] ←── Full Hint      │
│  CLASSIFICATION                     YR[bb,cd] ←── Refutations   │
│  ──────────────                                                  │
│  YG[intermediate] ←── Level        CONTEXT                       │
│  YT[snapback,ko] ←── Tags          ───────                       │
│                                     YC[TL] ←── Region            │
│  METRICS                            YK[direct:B2] ←── Ko         │
│  ───────                            YO[strict] ←── Order         │
│  YQ[q:2;rc:3;hc:1] ←── Quality                                   │
│  YX[d:5;r:13;s:24;u:1] ←── Complexity                           │
│  YM[3] ←── Move Count (redundant)                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Config-Driven Architecture

### Source of Truth Hierarchy

```
config/levels.json ──► YG property values
config/tags.json ──► YT property values
config/quality.json ──► YQ tier thresholds (spec-024)
```

### No Hardcoded Values

Per YenGo constitution and spec-025, all level/tag values MUST come from config files, not hardcoded arrays. This ensures:

1. **Single source of truth** - One place to update levels/tags
2. **Generated types** - TypeScript types derived from config
3. **Validation consistency** - Same validation in pipeline and frontend

---

## SGF Example (Complete)

```sgf
(;FF[4]GM[1]SZ[19]CA[UTF-8]
GN[3ba001edab9a42b0]
PL[B]
AB[eb][fb][bc][cc][dc][be]
AW[da][ab][bb][cb][db]

;; YenGo Custom Properties
YV[4]
YG[intermediate]
YT[life-and-death,tesuji]
YH1[ba]
YH2[tesuji]
YH3[Find the vital point that prevents white's eye formation]
YR[ca,aa]
YC[TL]
YK[none]
YQ[q:2;rc:3;hc:1]
YX[d:5;r:13;s:24;u:1]

;; Solution tree follows...
;B[ba]
  (;W[ca];B[aa])
  (;W[aa];B[ca])
)
```

---

## Related Documents

- [SGF Format Analysis](sgf-format-analysis.md) - Industry comparison
- [config/schemas/sgf-properties.schema.json](../config/schemas/sgf-properties.schema.json) - JSON Schema definition
- [specs/024-puzzle-quality-system](../specs/024-puzzle-quality-system/spec.md) - YQ/YX definitions
- [specs/025-sgf-level-alignment](../specs/025-sgf-level-alignment/spec.md) - Config centralization

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-27 | Gordon Player | Initial design document |
