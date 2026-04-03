# YenGo SGF Properties Reference

Technical reference for YenGo custom SGF properties.

> **Single Source of Truth**: `config/schemas/sgf-properties.schema.json`

---

## Schema Version 8

Current schema version: **8** (as of Spec 053)

### Changes in v8

- **YH format**: Compact pipe-delimited (`YH[hint1|hint2|hint3]`). YH1/YH2/YH3 removed.
- **SO property**: Removed (provenance in pipeline state).
- **Root C[] comment**: Removed during enrichment.
- **GN property**: Standardized to `YENGO-{16-hex}` format.
- **YT property**: Alphabetically sorted, deduplicated.
- **No empty lines**: Clean compact output.

---

## Property Ownership Matrix

This matrix defines which component is authoritative for each property (Spec 053, FR-027).

| Property | Adapter Provides | Enricher Action | Final Authority |
|----------|------------------|-----------------|-----------------|
| **GN** | Optional (any format) | Overwrites to `YENGO-{hash}` | Enricher |
| **SO** | Optional (source URL) | **Removes** | N/A (not in output) |
| **YV** | No | Sets to current version | Enricher |
| **YG** | Optional (level hint) | Validates, may override | Enricher |
| **YT** | Optional (initial tags) | Merges, dedupes, sorts | Enricher |
| **YH** | No | Generates from analysis | Enricher |
| **YI** | No | Added at publish stage | Pipeline |
| **YQ** | No | Computes from tree | Enricher |
| **YX** | No | Computes from tree | Enricher |
| **YC** | No | Detects from stones | Enricher |
| **YK** | No | Analyzes ko patterns | Enricher |
| **YO** | No | Detects move order | Enricher |
| **YR** | No | Extracts from tree | Enricher |
| **C[]** (root) | Optional (metadata) | **Removes** | N/A (not in output) |
| **C[]** (moves) | Optional (pedagogy) | **Preserves** | Adapter |

**Key Principles:**
1. Enricher is **final authority** for all YenGo properties (Y*)
2. Adapter data is used as **hints** but enricher validates and may override
3. Provenance (SO) is tracked in pipeline state, not in published SGF
4. Root comments are metadata (removed); move comments are pedagogy (preserved)

---

## Required Properties

These properties MUST be present in all published puzzle SGF files.

### GN - Game Name

Puzzle identifier in standardized format.

| Attribute | Value |
|-----------|-------|
| Format | `YENGO-{16-hex-chars}` |
| Pattern | `^YENGO-[a-f0-9]{16}$` |
| Example | `GN[YENGO-a1b2c3d4e5f67890]` |
| Purpose | Unique puzzle ID matching filename |

### YV - Schema Version

Schema version number. Used for format compatibility.

| Attribute | Value |
|-----------|-------|
| Format | Integer |
| Current | 8 |
| Example | `YV[8]` |
| Source | `config/schemas/sgf-properties.schema.json` |

### YI - Run ID

Pipeline run identifier for rollback tracking.

| Attribute | Value |
|-----------|-------|
| Format | Date-prefixed: YYYYMMDD-xxxxxxxx |
| Pattern | `^[0-9]{8}-[a-f0-9]{8}$` |
| Example | `YI[20260129-abc12345]` |
| Purpose | Enables selective rollback by pipeline run |

**Use Cases**:
- Rollback all puzzles from a specific pipeline run
- Track puzzle lineage and provenance
- Audit trail for compliance
- Instant date identification from run_id (e.g., `20260129-abc12345` → Jan 29, 2026)

### YG - Level (Grade)

Difficulty level using the 9-level system.

| Attribute | Value |
|-----------|-------|
| Format | Slug or `slug:sublevel` |
| Pattern | `^[a-z][a-z-]*(?::\d+)?$` |
| Example | `YG[beginner]` or `YG[intermediate:2]` |

**Valid Slugs**:
| Level | Slug | Rank Range |
|-------|------|------------|
| 1 | `novice` | 30k-26k |
| 2 | `beginner` | 25k-21k |
| 3 | `elementary` | 20k-16k |
| 4 | `intermediate` | 15k-11k |
| 5 | `upper-intermediate` | 10k-6k |
| 6 | `advanced` | 5k-1k |
| 7 | `low-dan` | 1d-3d |
| 8 | `high-dan` | 4d-6d |
| 9 | `expert` | 7d-9d |

### YQ - Quality Metrics

Quality level and metrics for puzzle curation.

| Attribute | Value |
|-----------|-------|
| Format | `q:{level};rc:{count};hc:{flag}` |
| Pattern | `^q:[1-5];rc:\d+;hc:[01]$` |
| Example | `YQ[q:3;rc:2;hc:1]` |

**Fields**:
| Field | Description | Values |
|-------|-------------|--------|
| `q` | Quality level (1=worst, 5=best) | 1-5 |
| `rc` | Refutation count | 0+ |
| `hc` | Has teaching comments | 0 or 1 |

### YX - Complexity Metrics

Complexity metrics measuring puzzle difficulty.

| Attribute | Value |
|-----------|-------|
| Format | `d:{depth};r:{reading};s:{stones};u:{unique}` |
| Pattern | `^d:\d+;r:\d+;s:\d+;u:[01]$` |
| Example | `YX[d:5;r:13;s:24;u:1]` |

**Fields**:
| Field | Description | Values |
|-------|-------------|--------|
| `d` | Solution depth (moves in main line) | 0+ |
| `r` | Reading count (total tree nodes) | 1+ |
| `s` | Stone count | 1+ |
| `u` | Unique first move (1) or miai (0) | 0 or 1 |

---

## Optional Properties

### YT - Tags

Technique tags for categorization (sorted alphabetically, deduplicated).

| Attribute | Value |
|-----------|-------|
| Format | Comma-separated list |
| Example | `YT[ko,ladder,snapback]` |
| Reference | [technique-tags.md](technique-tags.md) |

### YH - Progressive Hints

Hints in compact pipe-delimited format.

| Attribute | Value |
|-----------|-------|
| Format | `hint1\|hint2\|hint3` |
| Example | `YH[Top-left corner\|Look for a sacrifice\|cg]` |

**Hint Order** (by specificity):
1. Region/direction (e.g., "Top-left corner")
2. Technique hint (e.g., "Look for a sacrifice")  
3. Specific coordinate or move hint (e.g., "cg")

See: [Hint Concepts](../concepts/hints.md)

### YK - Ko Context

Ko handling information.

| Value | Description |
|-------|-------------|
| `none` | No ko involved |
| `simple` | Simple ko |
| `superko:positional` | Positional superko |
| `superko:situational` | Situational superko |

### YO - Move Order

Move order flexibility.

| Value | Description |
|-------|-------------|
| `strict` | Exact order required |
| `flexible:A,B` | Moves A and B can be swapped |

### YC - Board Region

Primary puzzle region.

| Code | Region |
|------|--------|
| TL | Top-left corner |
| TR | Top-right corner |
| BL | Bottom-left corner |
| BR | Bottom-right corner |
| TE | Top edge |
| BE | Bottom edge |
| LE | Left edge |
| RE | Right edge |
| C | Center |

### YR - Refutation Moves

Marks wrong move responses with explanations.

```
YR[bd:This allows white to connect]
```

---

## Validation

SGF files are validated before publishing. Validation checks:

1. **Required properties present**: GN, YV, YI, YG, YQ, YX
2. **Format patterns match**: Each property value matches expected pattern
3. **Level slug valid**: YG contains a recognized level slug
4. **GN format**: Must match `YENGO-{16-hex}` pattern

**Emergency bypass**: Use `--skip-validation` flag (logs warning)

---

## Example (Schema v8)

```sgf
(;FF[4]GM[1]SZ[9]CA[UTF-8]
GN[YENGO-a1b2c3d4e5f67890]
PL[B]
YV[8]
YI[20260129-abc12345]
YG[intermediate]
YT[snapback,tesuji]
YQ[q:3;rc:2;hc:1]
YX[d:3;r:5;s:12;u:1]
YH[Look at the corner|Sacrifice pattern|bg]
YK[none]
YO[strict]
YC[BL]
AB[af][bf][ag][cg][ah][bh]
AW[bg][ch][dh]
;B[ai]
(;W[bi];B[ci];W[bj];B[aj])
(;W[ci];B[bi]))
```

**Notes**:
- No SO property (provenance in pipeline state)
- No root C[] comment (removed during enrichment)
- No empty lines in output
- GN uses standardized format
- YT tags alphabetically sorted

---

## Deprecated Properties

### YH1, YH2, YH3 - Progressive Hints (Removed in v8)

Previously used separate properties for hints. Use compact `YH` format instead.

```
# Old (deprecated)
YH1[Look at the corner]
YH2[Sacrifice pattern]
YH3[bg]

# New (use YH)
YH[Look at the corner|Sacrifice pattern|bg]
```

### SO - Source (Removed in v8)

Previously stored source URL. Provenance is now tracked in pipeline state.

### YM - Move Count (Removed in v5)

Previously stored total moves in main line. Use `d` field in YX instead.

---

## See Also

- [SGF Architecture](../architecture/backend/sgf.md)
- [Configuration Reference](configuration.md)
- [Technique Tags](technique-tags.md)
