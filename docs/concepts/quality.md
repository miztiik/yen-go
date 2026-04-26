# Quality Metrics (YQ/YX)

**Last Updated**: 2026-03-24

> **See also**:
>
> - [Concepts: Enrichment Confidence Scores](./enrichment-confidence-scores.md) — All 6 confidence levels
> - [Concepts: SGF Properties](./sgf-properties.md) — Property definitions
> - [Concepts: Mastery](./mastery.md) — User skill progression
> - [Architecture: Enrichment](../architecture/backend/enrichment.md) — Quality computation
> - [Architecture: KataGo Enrichment — Signal Formulas](../architecture/tools/katago-enrichment.md#signal-formulas) — qk algorithm derivation

**Last Updated**: 2026-03-17

YenGo uses two complementary quality metrics: **YQ** (curation quality) and **YX** (puzzle complexity).

---

## YQ - Quality Metrics

Quality level and metadata for puzzle curation.

### Format

Backend pipeline writes:
```sgf
YQ[q:3;rc:2;hc:1;ac:1]
```

Enrichment lab writes (adds `qk` field):
```sgf
YQ[q:3;rc:2;hc:1;ac:1;qk:4]
```

### Fields

| Field | Name             | Description                          | Values                                                       | Writer         | Search DB Column |
| ----- | ---------------- | ------------------------------------ | ------------------------------------------------------------ | -------------- | -------------- |
| `q`   | Quality Level    | Overall quality rating               | 1-5 (5=best)                                                 | Both           | `quality`      |
| `rc`  | Refutation Count | Number of wrong-move branches        | 0+                                                           | Both           | —              |
| `hc`  | Comment Level    | Comment quality level                | 0 (none), 1 (correctness markers only), or 2 (teaching text) | Both           | —              |
| `ac`  | AI Correctness   | AI pipeline processing level         | 0-3 (see below)                                              | Both           | `puzzles.ac`   |
| `qk`  | Quality-Knowledge | Composite puzzle quality score      | 0-5 integer (see [Signal Formulas](../architecture/tools/katago-enrichment.md#signal-formulas)) | Enrichment lab only | **Not indexed** |

> **Design decision**: `qk` is written to SGF by the enrichment lab but intentionally NOT indexed in `yengo-search.db`. The signal is a diagnostic quality score used for enrichment validation and calibration. Frontend filtering uses `quality` (q field) for user-facing quality selection. The `qk` score remains available in the SGF for offline analysis and future indexing if needed.

### AI Correctness (AC) Levels

| Level | Name      | Description                                           | Set By      |
| ----- | --------- | ----------------------------------------------------- | ----------- |
| 0     | UNTOUCHED | AI pipeline has NOT processed this puzzle             | Default     |
| 1     | ENRICHED  | AI enriched metadata but existing solution used as-is | Pipeline    |
| 2     | AI_SOLVED | AI built or extended the solution tree                | Pipeline    |
| 3     | VERIFIED  | Human expert confirmed AI solution                    | Manual only |

**Truncation rule:** If the solution tree is truncated (budget exhaustion before `min_depth`), AC is downgraded from 2 (AI_SOLVED) to 1 (ENRICHED).

### Enrichment Tier ↔ AC Mapping (D64)

The enrichment tier (internal to AI pipeline) and AC level (published in YQ) are related but distinct:

| Enrichment Tier | Valid AC Levels | Meaning                                          |
| --------------- | --------------- | ------------------------------------------------ |
| 1 (Bare)        | 0               | No KataGo data — stone-pattern analysis only     |
| 2 (Structural)  | 0               | KataGo data available but no solution tree built |
| 3 (Full)        | 0, 1, 2, 3      | Complete KataGo analysis with solution tree      |

**Tier-2 dual semantics (D63):** Tier-2 results can originate from two paths:

- **Partial enrichment (FLAGGED):** AI-Solve attempted but found no correct moves → policy-only difficulty + techniques + hints, no solution tree
- **Legacy migration (ACCEPTED):** Pre-existing structural data from v2 migration

Disambiguate via `validation.status`: `FLAGGED` = partial enrichment, `ACCEPTED` = legacy.

> **See also:** [Architecture: KataGo Enrichment D57-D65](../architecture/tools/katago-enrichment.md) — Full design decisions

### Quality Levels

| Level | Name       | Criteria                             |
| ----- | ---------- | ------------------------------------ |
| 5     | Premium    | ≥3 refutations + teaching comments   |
| 4     | High       | ≥2 refutations + teaching comments   |
| 3     | Standard   | ≥1 refutation                        |
| 2     | Basic      | Solution tree present, 0 refutations |
| 1     | Unverified | No solution tree                     |

### How Refutation Count (`rc`) Is Computed

Refutation count uses a **three-layer fallback system** (see `core/correctness.py`):

#### Layer 1: SGF Markers (Gold Standard)

The SGF parser checks for explicit properties on each solution node:

| Marker  | Meaning     | Effect               |
| ------- | ----------- | -------------------- |
| `BM[1]` | Bad Move    | `is_correct = False` |
| `TR[]`  | Triangle    | `is_correct = False` |
| `TE[1]` | Tesuji      | `is_correct = True`  |
| `IT[]`  | Interesting | `is_correct = True`  |

When both wrong and correct markers are present, correct wins (TE/IT override BM/TR).

#### Layer 2: Comment Text Prefix (Silver Standard)

When no SGF markers are present, the parser checks the `C[]` comment text using conservative prefix matching:

| Comment Pattern                          | Inferred | Sources               |
| ---------------------------------------- | -------- | --------------------- |
| Starts with `Wrong` (case-insensitive)   | Wrong    | All sources           |
| Starts with `Incorrect`                  | Wrong    | yengo-source, yengo-source       |
| Starts with `Correct` (case-insensitive) | Correct  | All sources           |
| Starts with `Right`                      | Correct  | yengo-source            |
| Exactly `+`                              | Correct  | yengo-source-tsumego, yengo-source |

**Not matched** (too ambiguous): `bad`, `fail`, `lose`, `dead`, `oops`, `good`, `win`, `live`, non-English text.

This covers ~99% of the 80,000+ SGF files across 9 source adapters.

#### Layer 3: Tree Structure Heuristic (Bronze Fallback)

When no SGF markers AND no comment text provide correctness signals (all children retain the default `is_correct=True`), the quality module estimates refutation count from tree structure:

```text
rc = max(0, total_first_level_children - 1)
```

**Rationale**: In a well-formed tsumego, typically 1 branch is the correct first move and the rest are authored refutations showing why other moves fail.

**Scope**: Layer 3 **only** influences `rc` in YQ. It does NOT affect:

- `u` (uniqueness in YX) — requires definitive correctness
- `d` (depth in YX) — must follow the correct branch
- `YR` (refutation coordinates) — must identify specific wrong moves

### YQ Computation Flow

```text
Parse SGF
  → Layer 1 & 2 set is_correct on each SolutionNode
  → count_refutation_moves() traverses tree
    → If any is_correct=False found → use that count
    → If all is_correct=True (no signal) → Layer 3 structural fallback
  → compute_comment_level() classifies C[] text (0=none, 1=markers, 2=teaching)
  → Quality level = f(rc, hc)
```

---

## YX - Complexity Metrics

Objective complexity measurements for difficulty analysis.

### YX Format

Backend pipeline writes (4 core fields):
```sgf
YX[d:5;r:13;s:24;u:1]
```

Enrichment lab writes (8 fields — 4 core + 4 extended):
```sgf
YX[d:5;r:13;s:24;u:1;w:3;a:2;b:4;t:35]
```

### YX Fields

| Field | Name                 | Description                                 | Values                 | Writer              | Search DB Column    |
| ----- | -------------------- | ------------------------------------------- | ---------------------- | ------------------- | ------------------- |
| `d`   | Depth                | Moves in main correct line                  | 0+                     | Both                | `cx_depth`          |
| `r`   | Reading              | Total nodes in solution tree (all branches) | 1+                     | Both                | `cx_refutations`    |
| `s`   | Stones               | Initial stone count on board                | 1+                     | Both                | `cx_solution_len`   |
| `u`   | Unique               | Single correct first move                   | 0 (miai) or 1 (unique) | Both                | `cx_unique_resp`    |
| `w`   | Wrong-first count    | Distinct wrong first moves identified       | 0+ (optional)          | Enrichment lab only | **Not indexed**     |
| `a`   | Avg refutation depth | Mean depth of wrong-move branches           | 0+ (optional)          | Enrichment lab only | **Not indexed**     |
| `b`   | Branch count         | Total solution tree branches                | 0+ (optional)          | Enrichment lab only | **Not indexed**     |
| `t`   | Trap density %       | Percentage of plausible wrong moves         | 0-100 (optional)       | Enrichment lab only | **Not indexed**     |

> **Design decision**: `yengo-search.db`'s `parse_yx()` in `db_builder.py` only unpacks the first 4 fields (d, r, s, u). The extended fields (w, a, b, t) are enrichment-lab-only additions that provide richer complexity data in the SGF file but are not needed for frontend search/filtering. The core 4 fields are sufficient for the browser's puzzle selection queries. Extended fields remain available in the raw SGF for offline analysis, calibration, and future search DB schema evolution.

### How Each Field Is Computed

| Field | Function                         | Logic                                                                                            |
| ----- | -------------------------------- | ------------------------------------------------------------------------------------------------ |
| `d`   | `compute_solution_depth()`       | Follows first `is_correct=True` child at each level                                              |
| `r`   | `count_total_nodes()`            | Recursive count of ALL nodes (correct + wrong) including root                                    |
| `s`   | `count_stones()`                 | `len(black_stones) + len(white_stones)`                                                          |
| `u`   | `is_unique_first_move()`         | `1` if exactly 1 `is_correct=True` first-level child, else `0`                                   |
| `w`   | `_build_yx()` in sgf_enricher    | Count of distinct wrong first moves from refutation analysis                                     |
| `a`   | `compute_avg_refutation_depth()` | Mean depth of wrong-move branches (0 if no refutations)                                          |
| `b`   | `_build_yx()` in sgf_enricher    | Total branch count in solution tree                                                              |
| `t`   | `_build_yx()` in sgf_enricher    | `round(trap_density * 100)` — trap density as integer percentage from `DifficultySnapshot`       |

### Complexity Interpretation

| Metric  | Low  | Medium | High |
| ------- | ---- | ------ | ---- |
| Depth   | 1-3  | 4-7    | 8+   |
| Reading | 1-10 | 11-30  | 31+  |
| Stones  | 1-15 | 16-40  | 41+  |

### Example Analysis

```sgf
YX[d:5;r:13;s:24;u:1]
```

- **d:5** — 5-move solution (medium difficulty)
- **r:13** — 13 nodes in tree (moderate reading)
- **s:24** — 24 stones (typical corner problem)
- **u:1** — Unique first move (single correct answer)

### Important: `r` (Reading) vs `rc` (Refutation Count)

These measure different things:

| Metric     | What it counts                     | Purpose                                     |
| ---------- | ---------------------------------- | ------------------------------------------- |
| `r` in YX  | **All** nodes in the solution tree | Complexity — how much reading is needed     |
| `rc` in YQ | Only **wrong** move branches       | Quality — how well documented the puzzle is |

Example: A puzzle with 1 correct line of 3 moves + 4 wrong first moves each followed by 1 opponent response:

- `r` = 1 (root) + 3 (correct line) + 8 (4 wrong × 2 nodes) = 12
- `rc` = 4

---

## Relationship to Levels

Quality and complexity inform level assignment:

```text
Level = f(YX.d, YX.r, Source Quality, Source Level Hint)
```

But they serve different purposes:

| Metric              | Purpose                   | Use Case               |
| ------------------- | ------------------------- | ---------------------- |
| **YG** (Level)      | Difficulty classification | Filtering, progression |
| **YQ** (Quality)    | Curation rating           | Content selection      |
| **YX** (Complexity) | Objective measurement     | Analytics, validation  |

---

## Benson Gate

Benson's unconditional life detection identifies positions where the defender's contest group is provably alive — it has at least two vital regions (empty connected regions fully enclosed by the group). When triggered, the solution tree builder skips the KataGo engine query and returns a terminal node (defender wins).

**Quality signal:** A Benson gate activation at the root level indicates the puzzle is trivially solved (the defender is already unconditionally alive). This is a negative quality signal — the puzzle may not be a meaningful challenge.

Ko-dependent groups are inherently NOT unconditionally alive (they fail the vital region test), so Benson correctly falls through to KataGo for these positions. Seki groups are also not classified as alive.

**Important:** Framework/surrounding stones in tsumego ARE expected to be unconditionally alive. The gate only fires when the *contest group* (the group under attack within the `puzzle_region`) is in the alive set. Framework groups being alive is expected and does NOT trigger the gate.

## Interior-Point Exit

The interior-point two-eye death check identifies positions where the defender has ≤ 2 empty interior points within the `puzzle_region`, and no two are orthogonally adjacent. In these positions, the defender cannot form two eyes, meaning the attacker wins.

**Quality signal:** An interior-point exit indicates a clear attacking victory — the puzzle's outcome is deterministic from this board state. This allows the solver to skip engine queries for positions where death is geometrically certain.

The check uses `compute_regions()` from `tsumego_frame.py` to determine the bounded puzzle region, ensuring only cells within the relevant area are considered.

## Source Quality Rating

Source credibility affects overall quality:

### source-quality.json

```json
{
  "sources": {
    "yengo-source": { "trust_level": 4, "verification": "community" },
    "yengo-source": { "trust_level": 3, "verification": "community" },
    "yengo-source": { "trust_level": 5, "verification": "curated" }
  }
}
```

### Trust Levels

| Level | Description            |
| ----- | ---------------------- |
| 5     | Professionally curated |
| 4     | High-quality community |
| 3     | Moderate community     |
| 2     | Unverified             |
| 1     | Unknown                |

---

## Frontend Usage

### Quality Filtering

```typescript
// High quality only
const qualityPuzzles = puzzles.filter((p) => p.yq.q >= 4);

// With any comments (correctness markers or teaching text)
const withComments = puzzles.filter((p) => p.yq.hc >= 1);

// With genuine teaching text only
const withTeaching = puzzles.filter((p) => p.yq.hc === 2);
```

### Complexity Analysis

```typescript
// Easy reading
const easyReading = puzzles.filter((p) => p.yx.r <= 10);

// Deep problems
const deepProblems = puzzles.filter((p) => p.yx.d >= 8);
```

---

## Enricher Computation

### YQ Calculation (`core/quality.py`)

```python
def compute_quality_metrics(game: SGFGame) -> str:
    level = compute_puzzle_quality_level(game)
    # count_refutation_moves uses three-layer fallback (see correctness.py)
    refutation_count = count_refutation_moves(game.solution_tree)
    comment_level = compute_comment_level(game.solution_tree)
    return f"q:{level};rc:{refutation_count};hc:{comment_level}"
```

### YX Calculation (`core/complexity.py`)

```python
def compute_complexity_metrics(game: SGFGame) -> str:
    depth = compute_solution_depth(game.solution_tree)    # follows correct path
    reading_count = count_total_nodes(game.solution_tree)  # all nodes
    stone_count = count_stones(game)                       # AB + AW
    uniqueness = 1 if is_unique_first_move(game) else 0    # single correct first move
    return f"d:{depth};r:{reading_count};s:{stone_count};u:{uniqueness}"
```

---

## Validation

Metrics are validated during enrichment:

- `q` must be 1-5
- `rc` must be non-negative
- `hc` must be 0, 1, or 2
- `d` must be non-negative
- `r` must be positive
- `s` must be positive
- `u` must be 0 or 1

---

> **See also:**
>
> - [Architecture: KataGo Enrichment — Pre-Query Terminal Detection](../architecture/tools/katago-enrichment.md#pre-query-terminal-detection) — design decisions
> - [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md#pre-query-terminal-detection) — usage guide
> - [Reference: KataGo Enrichment Config — Benson Gate](../reference/katago-enrichment-config.md#benson-gate-config) — configuration
