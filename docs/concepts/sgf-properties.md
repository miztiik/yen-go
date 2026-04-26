# SGF Properties

> **See also**:
>
> - [Architecture: Enrichment](../architecture/backend/enrichment.md) — Pipeline logic and property ownership
> - [Concepts: Hints](./hints.md) — Hint system details
> - [Concepts: Tags](./tags.md) — Tag taxonomy
> - [Concepts: Levels](./levels.md) — 9-level difficulty system

**Last Updated**: 2026-04-03

**Single Source of Truth**: [`config/schemas/sgf-properties.schema.json`](../../config/schemas/sgf-properties.schema.json)

This is the canonical reference for YenGo SGF properties. All YenGo custom properties start with `Y`.

---

All published YenGo SGFs carry a `YV` schema marker so readers can validate the file against the active schema definition.

---

## Property Summary

| Property | Required | Description                                    | Example                                      |
| -------- | -------- | ---------------------------------------------- | -------------------------------------------- |
| `GN`     | Yes      | Puzzle ID                                      | `GN[YENGO-a1b2c3d4e5f67890]`                 |
| `YV`     | Yes      | Schema version                                 | `YV[15]`                                     |
| `YG`     | Yes      | Difficulty level                               | `YG[intermediate]`                           |
| `YL`     | No       | Collection membership                          | `YL[cho-chikun-elementary,tesuji]`           |
| `YQ`     | Yes      | Quality metrics                                | `YQ[q:3;rc:2;hc:1;ac:0]`                     |
| `YX`     | Yes      | Complexity metrics                             | `YX[d:5;r:13;s:24;u:1]`                      |
| `YT`     | No       | Tags                                           | `YT[ko,ladder,snapback]`                     |
| `YH`     | No       | Progressive hints                              | `YH[hint1\|hint2\|hint3]`                    |
| `YK`     | No       | Ko context                                     | `YK[direct]`                                 |
| `YO`     | No       | Move order                                     | `YO[strict]`                                 |
| `YC`     | No       | Corner position                                | `YC[TL]`                                     |
| `YR`     | No       | Refutation moves (wrong first-move SGF coords) | `YR[cd,de,ef]`                               |
| `YM`     | No       | Pipeline metadata JSON                         | `YM[{"t":"abc...","i":"20260220-abc12345"}]` |

**Note**: Source tracking and run correlation are carried through `YM` plus pipeline records rather than separate SGF properties.

---

## Required Properties

### GN - Game Name (Puzzle ID)

Unique puzzle identifier matching filename.

| Attribute | Value                        |
| --------- | ---------------------------- |
| Format    | `YENGO-{16-hex-chars}`       |
| Pattern   | `^YENGO-[a-f0-9]{16}$`       |
| Example   | `GN[YENGO-a1b2c3d4e5f67890]` |

### YV - Schema Version

Schema version number for format compatibility.

| Attribute | Value    |
| --------- | -------- |
| Format    | Integer  |
| Current   | `15`     |
| Example   | `YV[15]` |

### YG - Level (Grade)

Difficulty level using the 9-level system.

| Attribute | Value                                  |
| --------- | -------------------------------------- |
| Format    | Slug or `slug:sublevel`                |
| Pattern   | `^[a-z][a-z-]*(?::\d+)?$`              |
| Example   | `YG[beginner]` or `YG[intermediate:2]` |

**Valid Level Slugs**:

| Level | Slug                 | Rank Range |
| ----- | -------------------- | ---------- |
| 1     | `novice`             | 30k-26k    |
| 2     | `beginner`           | 25k-21k    |
| 3     | `elementary`         | 20k-16k    |
| 4     | `intermediate`       | 15k-11k    |
| 5     | `upper-intermediate` | 10k-6k     |
| 6     | `advanced`           | 5k-1k      |
| 7     | `low-dan`            | 1d-3d      |
| 8     | `high-dan`           | 4d-6d      |
| 9     | `expert`             | 7d-9d      |

See [Concepts: Levels](./levels.md) for full details.

### YQ - Quality Metrics

Quality level and metrics for puzzle curation.

| Attribute | Value                                                        |
| --------- | ------------------------------------------------------------ |
| Format    | `q:{level};rc:{count};hc:{comment_level};ac:{analysis_completeness}[;qk:{quality_knowledge}]` |
| Example (backend)   | `YQ[q:3;rc:2;hc:1;ac:0]`                                     |
| Example (enrichment lab) | `YQ[q:3;rc:2;hc:1;ac:1;qk:4]`                          |

| Field | Description              | Values                                 | Writer              |
| ----- | ------------------------ | -------------------------------------- | ------------------- |
| `q`   | Quality level            | 1-5 (5=best)                           | Both                |
| `rc`  | Refutation count         | 0+                                     | Both                |
| `hc`  | Comment level            | 0 (none), 1 (markers), or 2 (teaching) | Both                |
| `ac`  | Analysis completeness    | 0 (untouched), 1 (enriched), 2 (ai_solved), 3 (verified) | Both |
| `qk`  | Quality-knowledge score  | 0-5 integer (optional, enrichment lab only) | Enrichment lab only |

### YX - Complexity Metrics

Complexity metrics measuring puzzle difficulty.

| Attribute | Value                                         |
| --------- | --------------------------------------------- |
| Format (backend) | `d:{depth};r:{reading};s:{stones};u:{unique}` |
| Format (enrichment lab) | `d:{depth};r:{reading};s:{stones};u:{unique};w:{wrong};a:{avg_depth};b:{branches};t:{trap_pct}` |
| Example (backend)  | `YX[d:5;r:13;s:24;u:1]`                       |
| Example (enrichment lab) | `YX[d:5;r:13;s:24;u:1;w:3;a:2;b:4;t:35]` |

| Field | Description          | Values                 | Writer              | Search DB Column |
| ----- | -------------------- | ---------------------- | ------------------- | ---------------- |
| `d`   | Solution depth       | 0+ moves               | Both                | `cx_depth`       |
| `r`   | Reading count        | 1+ nodes               | Both                | `cx_refutations` |
| `s`   | Stone count          | 1+                     | Both                | `cx_solution_len`|
| `u`   | Unique first move    | 0 (miai) or 1 (unique) | Both                | `cx_unique_resp` |
| `w`   | Wrong-first count    | 0+ (optional)          | Enrichment lab only | Not indexed      |
| `a`   | Avg refutation depth | 0+ (optional)          | Enrichment lab only | Not indexed      |
| `b`   | Branch count         | 0+ (optional)          | Enrichment lab only | Not indexed      |
| `t`   | Trap density %       | 0-100 (optional)       | Enrichment lab only | Not indexed      |

See [Concepts: Quality](./quality.md#yx---complexity-metrics) for detailed field computation.

---

## Optional Properties

### YT - Tags

Technique tags for categorization.

| Attribute | Value                                                |
| --------- | ---------------------------------------------------- |
| Format    | Comma-separated, sorted alphabetically, deduplicated |
| Example   | `YT[ko,ladder,snapback]`                             |

See [Concepts: Tags](./tags.md) for full tag taxonomy.

### YL - Collection Membership

Membership in curated puzzle collections.

| Attribute | Value                                                |
| --------- | ---------------------------------------------------- |
| Format    | Comma-separated, sorted alphabetically, deduplicated |
| Example   | `YL[cho-chikun-elementary,tesuji-speed-match]`       |

Assigned automatically during analysis based on source metadata (folder paths) matching collection aliases defined in `config/collections.json`.

### YH - Progressive Hints

Hints in compact pipe-delimited format (max 3).

| Attribute | Value                                                                     |
| --------- | ------------------------------------------------------------------------- |
| Format    | `hint1\|hint2\|hint3`                                                     |
| Example   | `YH[Focus on the corner\|Look for a ladder\|The first move is at {!cg}.]` |

**Hint order** (by specificity):

1. Region/direction (transform-invariant text)
2. Technique hint (transform-invariant)
3. Specific coordinate (uses `{!xy}` token format)

**Coordinate tokens**: YH3 embeds coordinates as `{!xy}` tokens (SGF coordinate format) instead of human-readable notation. Consumers can resolve these tokens after board transforms so the hint text stays orientation-safe.

**Color references**: Liberty analysis in YH1 uses role-based labels ("Your group", "the opponent") instead of color names ("Black", "White") so hints remain correct when colors are swapped.

See [Concepts: Hints](./hints.md) for full details.

### YK - Ko Context

| Value      | Description                               |
| ---------- | ----------------------------------------- |
| `none`     | No ko involved                            |
| `direct`   | Direct ko (immediate recapture situation) |
| `approach` | Approach ko (needs extra move before ko)  |

### YO - Move Order

| Value      | Description                  |
| ---------- | ---------------------------- |
| `strict`   | Moves must be in order       |
| `flexible` | Order doesn't matter         |
| `miai`     | Multiple correct first moves |

### YC - Corner Position

Detected by `detect_region()` in the enrichment stage. The algorithm uses **proportional thresholds** (calibrated on 19×19) that scale to any board size from 4×4 to 25×25. Internally 10 fine-grained regions are detected (TL, TR, BL, BR, T, B, L, R, C, FULL) and mapped to the 6 canonical output values below.

| Value | Description                                     |
| ----- | ----------------------------------------------- |
| `TL`  | Top-left corner                                 |
| `TR`  | Top-right corner                                |
| `BL`  | Bottom-left corner                              |
| `BR`  | Bottom-right corner                             |
| `C`   | Center (or full-board — no zoom)                |
| `E`   | Edge (top/bottom/left/right — no quadrant zoom) |

### YR - Refutation Moves

Wrong first-move SGF coordinates, comma-separated.

| Attribute | Value                           |
| --------- | ------------------------------- |
| Format    | Comma-separated SGF coordinates |
| Example   | `YR[cd,de,ef]`                  |
| Max       | 5 coordinates                   |

Set by the enrichment stage using `extract_refutations()`. Only lists wrong **first-move** coordinates (direct children of root where `is_correct=False` and `move` is not None).

**Not to be confused with `rc` in YQ**: `YR` lists specific wrong-move coordinates; `rc` is the count of all wrong branches at any depth (including Layer 3 structural fallback). See [Concepts: Quality](./quality.md) for the three-layer refutation counting system.

### YM - Pipeline Metadata

Pipeline metadata JSON embedded directly in SGF for cross-stage correlation.

| Attribute | Value                                                  |
| --------- | ------------------------------------------------------ |
| Format    | JSON object                                            |
| Example   | `YM[{"t":"a1b2c3d4e5f67890","i":"20260220-abc12345"}]` |

| Field | Description                                     | Required | Publish behavior        |
| ----- | ----------------------------------------------- | -------- | ----------------------- |
| `t`   | Trace ID (16-char hex) — unique per puzzle file | Yes      | Kept                    |
| `i`   | Pipeline run ID (`YYYYMMDD-xxxxxxxx`)           | No       | Kept                    |
| `f`   | Original filename from source adapter           | No       | **Stripped at publish** |

**Note on `f` (original filename)**: The `f` field may be present earlier in the pipeline for cross-stage tracking, but published SGFs should keep only the metadata needed for durable correlation.

**Note on source tracking**: Source adapter ID is tracked via the CLI `--source` flag and publish records rather than being embedded as a standalone SGF property.

Set at ingest, preserved through analyze. At publish, `f` is extracted and recorded in the publish log, then stripped from the SGF. Enables end-to-end tracing of each puzzle through the pipeline via `trace_id`.

---

## Property Ordering

The `SGFBuilder` emits root node properties in a deterministic order. All Y\* properties are grouped together between standard SGF headers and stone placements:

```text
SZ → FF → GM → PL → GN → YV → YG → YT → YQ → YX → YL → YH → YC → YK → YO → YR → YM → AB → AW → [moves]
```

This ordering is enforced by builder round-tripping during the publish stage.

---

## Property Ownership Matrix

Property handling is **config-driven** via [`config/sgf-property-policies.json`](../../config/sgf-property-policies.json). Each property has a declarative policy that controls its lifecycle.

| Property                    | Policy              | Adapter Provides | Enricher Action                                                                 | Final Authority   |
| --------------------------- | ------------------- | ---------------- | ------------------------------------------------------------------------------- | ----------------- |
| **FF**                      | `hardcode`          | No               | Forces to `4`                                                                   | Enricher          |
| **GM**                      | `hardcode`          | No               | Forces to `1`                                                                   | Enricher          |
| **GN**                      | `override`          | Optional         | Overwrites to `YENGO-{hash}`                                                    | Publisher         |
| **YV**                      | `override`          | No               | Sets to current version                                                         | Enricher          |
| **SZ**                      | `enrich_if_absent`  | Yes              | Defaults to `19` when absent                                                    | Source / Enricher |
| **AN**                      | `preserve`          | Yes              | Preserved as-is                                                                 | Source            |
| **PL**                      | `preserve`          | Yes              | Preserved as-is                                                                 | Source            |
| **GC**                      | `preserve`          | Yes              | Preserved as-is                                                                 | Source            |
| **PB**                      | `preserve`          | Optional         | Preserved as-is                                                                 | Source            |
| **PW**                      | `preserve`          | Optional         | Preserved as-is                                                                 | Source            |
| **YG**                      | `enrich_if_absent`  | Optional         | Preserved if present; computed when missing                                     | Source / Enricher |
| **YT**                      | `enrich_if_absent`  | Optional         | Preserved if present; computed when missing                                     | Source / Enricher |
| **YL**                      | `enrich_if_absent`  | Optional         | Preserved if present; assigned when missing                                     | Source / Enricher |
| **YQ**                      | `enrich_if_partial` | No               | Re-computed if invalid/partial                                                  | Enricher          |
| **YX**                      | `enrich_if_partial` | No               | Re-computed if invalid/partial                                                  | Enricher          |
| **YH**                      | `enrich_if_absent`  | Optional         | Preserved if present; generated when missing                                    | Source / Enricher |
| **YC**                      | `enrich_if_absent`  | Optional         | Preserved if present; detected when missing                                     | Source / Enricher |
| **YK**                      | `enrich_if_absent`  | Optional         | Preserved if present; detected when missing                                     | Source / Enricher |
| **YO**                      | `enrich_if_absent`  | Optional         | Preserved if present; detected when missing                                     | Source / Enricher |
| **YR**                      | `enrich_if_absent`  | Optional         | Preserved if present; counted when missing                                      | Source / Enricher |
| **YM**                      | `override`          | No               | Pipeline metadata JSON                                                          | Pipeline          |
| **SO**                      | `remove`            | Optional         | Parsed then **removed**                                                         | N/A               |
| **C[]** (root)              | `configurable`      | Optional         | Cleaned (HTML/CJK stripped), **preserved by default** (`preserve_root_comment`) | Configurable      |
| **C[]** (moves)             | —                   | Optional         | **Standardized** (Correct/Wrong prefix, CJK stripped)                           | Enricher          |
| **DT, CA, RE, AP, KM, ...** | `blocked`           | N/A              | **Dropped at parse time**                                                       | N/A               |

> **See also**: [`config/sgf-property-policies.json`](../../config/sgf-property-policies.json) — the single source of truth for property policies.

### Pre-Pipeline SGF Enrichment: N[] (Node Name)

The standard SGF `N[]` property labels nodes in the game tree (e.g., `N[正解]` = correct solution, `N[失敗]` = failure). Many third-party puzzle sources use `N[]` to mark branch types in tsumego files.

**Problem**: `N[]` is not in the pipeline's metadata whitelist and is **dropped at parse time**. This loses valuable branch-label information that aids puzzle comprehension.

**Solution**: Before pipeline ingestion, merge `N[]` values into `C[]` comments as a pre-pipeline enrichment step:

| Node State            | Action                                    | Example                                      |
| --------------------- | ----------------------------------------- | -------------------------------------------- |
| `N[text]` + `C[comment]` | Merge: `C[text. comment]`, remove `N[]` | `N[correct];C[White dies]` → `C[correct. White dies]` |
| `N[text]` only        | Convert: `C[text]`, remove `N[]`          | `N[variation]` → `C[variation]`              |
| No `N[]`              | No change                                 | —                                            |

**Tool**: `python -m tools.yengo-source merge-node-names --source-dir <dir>`

This is a general-purpose operation applicable to any source collection that uses `N[]` for branch labeling. The merged text is then preserved through the pipeline via the standard `C[]` property handling (root comments preserved by default, move comments standardized).

**Key Principles**:

1. Property handling is **declarative and config-driven** — add/modify policies without code changes
2. `enrich_if_absent`: source values are **preserved**; pipeline computes only when missing
3. `enrich_if_partial`: values are re-computed only when they fail validation (YQ, YX)
4. `override`: always overwritten regardless of source value (GN, YV, YM)
5. `blocked`: dropped at parse time — never enters the pipeline (DT, CA, RE, AP, etc.)
6. Provenance (SO) is tracked in pipeline state, not in published SGF
7. Root comments are cleaned (HTML/CJK stripped) and preserved by default (`configurable` policy)
8. Move comments are standardized with Correct/Wrong prefix and CJK stripped
9. `enable_*` flags in `EnrichmentConfig` are **orthogonal** — they toggle computation, not property policy

---

## Example SGF

```sgf
(;SZ[19]FF[4]GM[1]PL[B]GN[YENGO-a1b2c3d4e5f67890]YV[15]YG[intermediate]YT[ladder,life-and-death]YQ[q:4;rc:2;hc:1;ac:1;qk:4]YX[d:5;r:13;s:24;u:1;w:3;a:2;b:4;t:35]YL[classic-problems]YH[Focus on the corner|Watch the ladder|The first move is at {!cg}.]YC[TL]YK[none]YO[strict]YM[{"t":"fedcba9876543210","i":"20260220-abc12345"}]AB[aa][ba][ca]AW[ab][bb];B[da]
(;W[ea];B[db];W[eb];B[dc]C[Correct!])
(;W[db];B[ea]C[Also wins])
)
```

---

## Validation

Validate SGF properties against schema:

```bash
python -m backend.puzzle_manager validate
```

For schema details, see [`config/schemas/sgf-properties.schema.json`](../../config/schemas/sgf-properties.schema.json).
