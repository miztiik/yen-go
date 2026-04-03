# Implementation Plan: Strategy D — Puzzle Quality Control

**Created:** 2026-02-25  
**Status:** Draft — approved in principle, ready for implementation  
**Based on:** [001-research-quality-landscape.md](001-research-quality-landscape.md)  
**Strategy:** D (Hybrid) — Shift-left dedup + Content-type classification + Quality-tier UX

---

## Scope Coverage vs Strategy D Full Recommendation

### Covered in This Plan

| Component                                                                | Phase | Status       |
| ------------------------------------------------------------------------ | :---: | ------------ |
| Board-position fingerprinting (corner-normalized)                        |   1   | **In scope** |
| Cross-source dedup with quality-based winner selection                   |   1   | **In scope** |
| Trivial capture detection                                                |   1   | **In scope** |
| `avg_refutation_depth` enrichment metric (YX extension)                  |   1   | **In scope** |
| Config-driven quality scoring (`quality.py` reads `puzzle-quality.json`) |   1   | **In scope** |
| Content-type classification (curated/practice/training)                  |   2   | **In scope** |
| YM metadata expansion (fp + ct fields)                                   |  1–2  | **In scope** |
| ShardEntry expansion (ct field)                                          |   2   | **In scope** |
| Content-type shard dimension + routing                                   |   2   | **In scope** |
| Frontend: 3 quality-tier tabs (Curated / Practice / All)                 |   3   | **In scope** |
| Frontend: Quality stars display                                          |   3   | **In scope** |

### Deferred (Not in This Plan)

| Component                                  | Why Deferred                                                                                                                                                           | Dependency                       |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| Quality-weighted daily challenge selection | Daily challenge generator already exists. Weighting by q≥4 + ct=curated is a config change once content-type is live.                                                  | Phase 2 complete                 |
| Difficulty classifier improvement          | Research flagged classifier as "placeholder". Requires separate investigation (positional features, liberty analysis, reading depth). Orthogonal to quality strategy.  | None — standalone project        |
| Dedup metadata merging                     | Plan picks highest-quality duplicate as winner. Merging best comments from one copy + best tags from another is complex and risk-prone. Revisit after dedup is proven. | Phase 1 complete + usage data    |
| "Training Lab" as 4th dedicated tab        | User chose 3 tabs. Training content is accessible via "All" tab. A dedicated training mode can be added if user demand warrants it.                                    | Phase 3 complete + user feedback |

---

## Key Decisions (Locked)

| Decision             | Choice                                                                      | Rationale                                                                            |
| -------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Dedup approach       | Corner-normalize to TL quadrant, then fingerprint sorted stones + size + PL | Catches cross-source dupes including rotated positions; simpler than full 8-symmetry |
| Fingerprint storage  | `YM` JSON only (`fp` field). No shard field                                 | Only needed at publish-time dedup, not query-time. Saves ~6MB at scale               |
| Content-type storage | `YM` JSON (`ct` field) + shard numeric `ct` field                           | YM for SGF persistence; shard field for query-time tab filtering                     |
| Content-type values  | 3 types: curated (1), practice (2), training (3)                            | Maps 1:1 to frontend tabs. Simpler than 4-5 types                                    |
| Dedup winner         | Keep highest quality score; on tie keep richest comments (hc)               | Preserves most valuable version. No metadata merging (deferred)                      |
| Trivial capture      | Opponent group at 1 liberty + correct first move captures it                | Reuses existing atari detection from `hints.py`                                      |
| Quality UX           | Three tabs: Curated / Practice / All                                        | Progressive inclusion: Curated ⊂ Practice ⊂ All                                      |
| Tab default          | Practice                                                                    | Broadest useful set without training noise                                           |
| Reprocessing         | Big-bang — discard existing collections, re-ingest all sources              | No migration concern. Clean slate for new schema                                     |

---

## Phase 1: Position Fingerprinting, Dedup & Quality Foundations (~2.5 weeks)

### 1.1 New module: `core/position_fingerprint.py`

Pure function: `compute_position_fingerprint(board_size, black_stones, white_stones, player_to_move) → str` (16-char hex)

**Algorithm:**

1. Compute bounding box of all stones (reuse logic from `core/enrichment/region.py` `_compute_bounding_box()`)
2. Determine which corner the action occupies (reuse `_classify_region()`)
3. Apply rotation/reflection to map stones to canonical **top-left** form
   - 8 candidate transforms (identity, 3 rotations, 4 reflections)
   - Select the transform that moves the bounding-box centroid closest to (0, 0)
   - For ties: lexicographic ordering of the resulting stone list
4. Build canonical string: `"{board_size}:{player_to_move}:{sorted_black_tuples}:{sorted_white_tuples}"`
5. SHA256 → first 16 hex characters

**Dependencies:** Only stdlib `hashlib` + existing `Point`/`Color` types from `core/board.py`. No new libraries.

**Edge cases:**

- Center positions (`YC=C`): No rotation preference — use lexicographic tiebreak
- Edge positions (`YC=E`): Normalize to top edge
- Non-square boards: Use actual width×height in canonical string
- Missing PL: Infer from solution tree (first move color) before fingerprinting

**Tests:**

- 8 rotations/reflections of same position → identical fingerprint
- Different positions → different fingerprints
- Same position, different comments/enrichment → same fingerprint
- Center position stability
- Puzzle with and without PL but inferrable from moves → same fingerprint

### 1.2 Dedup registry: `.pm-runtime/state/dedup-registry.json`

Persistent JSON mapping: `fingerprint → {puzzle_id, quality, source, path, hc}`

**Lifecycle:**

- **Built during publish:** After fingerprinting each puzzle, check registry
- **Conflict resolution order:**
  1. Higher quality score (`q` from YQ) wins
  2. On tie: higher comment level (`hc` from YQ) wins
  3. On tie: existing entry wins (first-in stable)
- **Big-bang mode:** Registry cleared and rebuilt from scratch
- **Incremental mode:** Registry loaded at publish start, updated as puzzles are processed, saved at end
- **Independent of publish log** — survives its 90-day retention

**Size estimate:** 175K entries × ~120 bytes ≈ 21MB JSON. Acceptable at this scale.

**Future consideration:** Migrate to SQLite if registry exceeds 500K entries or lookup latency becomes noticeable.

### 1.3 Expand YM schema with fingerprint

Current YM: `YM[{"t":"trace_id","i":"run_id"}]`  
New YM: `YM[{"t":"trace_id","i":"run_id","fp":"16char_hex"}]`

**Files to modify:**

- `core/sgf_parser.py` — `YenGoProperties`: parse `fp` from YM JSON
- `core/sgf_publisher.py` / `SGFBuilder`: serialize `fp` into YM JSON
- Property policy: YM is already `override` — no policy change needed

### 1.4 Integrate dedup into publish stage

Modify `stages/publish.py` `PublishStage._publish_puzzle()`:

1. After enrichment, before writing to disk → compute position fingerprint
2. Store fingerprint in `game.yengo.pipeline_meta['fp']`
3. Check dedup registry:
   - **No match** → add to registry, proceed normally
   - **Match, new is better** → replace registry entry, write new file, record old puzzle_id as superseded
   - **Match, existing is better** → skip this puzzle, log as `dedup:superseded`
4. Dedup stats logged at end of publish run: total checked, duplicates found, superseded count

**Logging:** Each dedup event logged with both puzzle_ids + fingerprint + quality comparison for auditability.

### 1.5 `avg_refutation_depth` Enrichment Metric

Add average refutation depth to `core/complexity.py` `compute_complexity()` as a new sub-field in YX.

**Algorithm:**

1. Walk the solution tree (`SolutionNode`) — already parsed by `correctness.py`
2. For each wrong-move branch (node where `is_correct == False` or a leaf without children on a player-to-move node):
   - Measure depth from root of that wrong subtree to its deepest leaf
3. Compute mean across all wrong-move branches
4. Round to nearest integer

**YX format extension:**

```
Before: YX[d:5;r:13;s:24;u:1]
After:  YX[d:5;r:13;s:24;u:1;a:3]
```

Where `a` = avg refutation depth (mean depth of wrong-move subtrees).

**Files to modify:**

- `core/complexity.py` — add `avg_refutation_depth` to `ComplexityMetrics` dataclass and `compute_complexity()`
- `core/sgf_parser.py` — parse `a` from YX string
- `core/sgf_publisher.py` — serialize `a` into YX string

**Caveat:** Layer 3 correctness inference (`correctness.py`) doesn't always set `is_correct=False` on wrong nodes explicitly — it infers from tree structure. ~30-40% of puzzles may show `a:0` if the tree lacks explicit wrong branches. This is acceptable data — it correctly reflects that those puzzles have no refutation paths.

**Effort:** ~2 hours, ~20 lines new code. Fully parallelizable with other Phase 1 work.

**Tests:**

- Puzzle with 3 wrong branches of depth 2, 4, 6 → `a:4`
- Puzzle with no wrong branches → `a:0`
- Puzzle with single wrong branch of depth 1 → `a:1`
- Round-trip: serialize → parse → same value

### 1.6 Config-Driven Quality Scoring

Make `core/quality.py` `compute_puzzle_quality_level()` read thresholds from `config/puzzle-quality.json` instead of hardcoding them.

**Current state:** `quality.py` hardcodes conditions like `if refutation_count >= 3 and has_comments: return 5`. The file `config/puzzle-quality.json` exists and documents the same thresholds, but the code never reads it.

**Change:**

1. Load `config/puzzle-quality.json` at module init (or lazily on first call)
2. Replace hardcoded conditions with config lookups:

   ```python
   # Before (hardcoded)
   if refutation_count >= 3 and has_comments:
       return 5

   # After (config-driven)
   for level in sorted(config['levels'], reverse=True):
       if all(check(metric) for check in level['conditions']):
           return level['quality']
   ```

3. Keep the existing thresholds as defaults in case config is missing (defensive)
4. Update `config/puzzle-quality.json` to be the authoritative source

**Files to modify:**

- `core/quality.py` — load config, replace hardcoded thresholds
- `config/puzzle-quality.json` — ensure schema supports engine use (may need minor restructuring)

**Effort:** ~3 hours. No new dependencies. No public API change.

**Tests:**

- Default config → same quality scores as current hardcoded logic (golden master)
- Modified config → different scores (config actually drives behavior)
- Missing config file → graceful fallback to defaults

### 1.7 Trivial capture detection

Add to `core/content_classifier.py` (created in Phase 2, but this function is needed in Phase 1 for early flagging):

`is_trivial_capture(game: SGFGame) → bool`

_(Section numbering note: was 1.5 before D1/D4 were moved into scope.)_

**Algorithm:**

1. Build `Board` from initial position (pattern from `core/enrichment/hints.py` `_build_board()`)
2. Analyze liberties (reuse `_analyze_liberties()` from hints.py `LibertyAnalysis`)
3. Find opponent groups at exactly 1 liberty
4. Get first correct move from solution tree
5. Check if that move captures the atari group (reuse `move_captures_stones()` from `core/enrichment/solution_tagger.py`)
6. If yes → trivial capture

**This is composition of existing functions — minimal new code.**

**Where used in Phase 1:** Flag in YM as `"tc":true` (trivial capture). Used by content-type classifier in Phase 2.

---

## Phase 2: Content-Type Classification (~3 weeks)

### 2.1 New module: `core/content_classifier.py`

Function: `classify_content_type(game: SGFGame) → int`

Returns: `1` (curated), `2` (practice), `3` (training)

**Decision tree (evaluated in order):**

```
1. Is trivial capture? (from 1.5)           → training (3)
2. Has no solution tree?                     → training (3)
3. Root comment matches teaching patterns?   → training (3)
   (regex: demonstrates|explains|shows|concept|lesson|example|tutorial)
4. Solution depth ≤ 1 AND hc:2?             → training (3)
   (single-move with teaching explanation = tutorial)
5. Unique first move (u:1) AND
   refutations ≥ 2 AND
   quality ≥ 3?                              → curated (1)
6. Everything else                           → practice (2)
```

**Policy:** `ENRICH_IF_ABSENT` — if source (or prior run) set content-type, preserve it.

**Config-driven patterns:** Teaching-pattern regexes loaded from `config/content-types.json` (new file), not hardcoded.

### 2.2 New config: `config/content-types.json`

```json
{
  "version": "1.0.0",
  "types": {
    "1": { "name": "curated", "display_label": "Curated" },
    "2": { "name": "practice", "display_label": "Practice" },
    "3": { "name": "training", "display_label": "Training" }
  },
  "teaching_patterns": [
    "\\bdemonstrates?\\b",
    "\\bexplains?\\b",
    "\\bshows?\\b",
    "\\bconcepts?\\b",
    "\\blessons?\\b",
    "\\bexamples?\\b",
    "\\btutorials?\\b",
    "\\billustrates?\\b"
  ],
  "curated_thresholds": {
    "min_quality": 3,
    "min_refutations": 2,
    "require_unique_first_move": true
  }
}
```

### 2.3 Expand YM schema with content-type

New YM: `YM[{"t":"trace_id","i":"run_id","fp":"fingerprint","ct":1}]`

Optionally also `"tc":true` for trivial capture flag (Phase 1).

### 2.4 Add `ct` field to ShardEntry

Modify `core/shard_models.py` `ShardEntry`:

- Add `ct: int` field (1/2/3), default `2` (practice) for backward compat

### 2.5 Update ShardWriter routing for content-type dimension

Modify `core/shard_writer.py` `compute_shard_keys()`:

- New 1D shards: `ct1/`, `ct2/`, `ct3/`
- New 2D intersections: `l{level}-ct{type}/` (level × content-type — needed for level-filtered tab views)
- Optionally: `ct{type}-t{tag}/` if tag-within-tab filtering is needed (defer if not immediately needed)

Update shard schema arrays and context elision for the new dimension.

### 2.6 Update snapshot manifest

Modify `core/snapshot_builder.py`:

- Add `"content_type"` to `dimensions` array in manifest
- Add `null_buckets.content_type`
- Shard entries in `meta.json` get `labels.content_type`

### 2.7 Integrate into analyze stage

Modify `stages/analyze.py`:

- After enrichment (classify, tag, enrich) → call `classify_content_type(game)`
- Store result in `game.yengo.pipeline_meta['ct']`
- Also flow into the `ShardEntry` construction during publish

### 2.8 Update property policy documentation

Update `config/sgf-property-policies.json` to document the YM sub-field expansion (`fp`, `ct`, `tc`).

---

## Phase 3: Frontend Quality Tabs (~2 weeks)

### 3.1 Update configService.ts

Add `contentTypeIdToSlug()` mapping in `frontend/src/services/configService.ts`:

- `{1: 'curated', 2: 'practice', 3: 'training'}`
- Load content-type display labels from config or hardcode (only 3 values)

### 3.2 Update entryDecoder.ts

Modify `frontend/src/services/entryDecoder.ts`:

- Decode `ct` field from shard array-of-arrays entries
- Add `ct` (or `contentType`) to `DecodedEntry` type

### 3.3 Update snapshotService.ts

Modify `frontend/src/services/snapshotService.ts`:

- Recognize `content_type` dimension in manifest
- Support shard key resolution for `ct*` shards and `l{X}-ct{Y}` 2D shards

### 3.4 Browse UI: Three tabs

Add tab component to puzzle browse/list view:

| Tab          | Shard Query                                     | Description                                            |
| ------------ | ----------------------------------------------- | ------------------------------------------------------ |
| **Curated**  | `ct1` or `l{X}-ct1`                             | Best puzzles: unique first move, deep refutations, q≥3 |
| **Practice** | `ct1` + `ct2` (union) or no ct filter with ct≤2 | All proper puzzles without training noise              |
| **All**      | No content-type filter (existing shards)        | Everything including training material                 |

**Default tab:** Practice

**Tab counts:** Display total puzzle count per tab from manifest shard metadata (already available in `meta.json` `count` fields).

### 3.5 Quality stars display

The `q` field already exists in shard entries. Render 1–5 stars on puzzle cards and detail view using colors from `config/puzzle-quality.json`:

- Filled star: `#FFD700` (gold)
- Empty star: `#CCCCCC` (gray)
- Level colors: 1=red, 2=orange, 3=gray, 4=blue, 5=green

---

## Schema Changes Summary

### SGF file (YM property)

```
Before: YM[{"t":"a1b2c3d4","i":"20260225-abc12345"}]
After:  YM[{"t":"a1b2c3d4","i":"20260225-abc12345","fp":"9f3a2b1c8e7d6f50","ct":1}]
```

No new top-level SGF properties. Two new fields (`fp`, `ct`) in existing YM JSON. Optional `tc` boolean for trivial capture.

### SGF file (YX property)

```
Before: YX[d:5;r:13;s:24;u:1]
After:  YX[d:5;r:13;s:24;u:1;a:3]
```

New `a` sub-field = avg refutation depth (integer). Added by Phase 1 complexity enrichment.

### Shard entries

```
Before: ["0001/fc38f029", [10], [6, 47], [1, 2, 11, 1], 3]
         schema: ["p", "t", "c", "x", "q"]

After:  ["0001/fc38f029", [10], [6, 47], [1, 2, 11, 1], 3, 1]
         schema: ["p", "t", "c", "x", "q", "ct"]
```

One new integer field per entry (~1 byte overhead).

### New files

| File                                                  | Purpose                                                                             |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `backend/puzzle_manager/core/position_fingerprint.py` | Corner-normalized position fingerprinting                                           |
| `backend/puzzle_manager/core/content_classifier.py`   | Content-type classification (curated/practice/training) + trivial capture detection |
| `config/content-types.json`                           | Content-type definitions + teaching-pattern regexes + curated thresholds            |
| `.pm-runtime/state/dedup-registry.json`               | Runtime: fingerprint → puzzle_id mapping                                            |

### Modified files (backend)

| File                                | Change                                                                       |
| ----------------------------------- | ---------------------------------------------------------------------------- |
| `core/sgf_parser.py`                | Parse `fp`, `ct` from YM JSON; parse `a` from YX string                      |
| `core/sgf_publisher.py`             | Serialize `fp`, `ct` into YM JSON; serialize `a` into YX string              |
| `core/complexity.py`                | Add `avg_refutation_depth` to `ComplexityMetrics` and `compute_complexity()` |
| `core/quality.py`                   | Load thresholds from `config/puzzle-quality.json` instead of hardcoding      |
| `core/shard_models.py`              | Add `ct` field to `ShardEntry`                                               |
| `core/shard_writer.py`              | Route to `ct*` shards, context elision, schema update                        |
| `core/snapshot_builder.py`          | Handle `content_type` dimension in manifest                                  |
| `stages/analyze.py`                 | Call `classify_content_type()` after enrichment                              |
| `stages/publish.py`                 | Compute fingerprint, check dedup registry, write `fp` to YM                  |
| `config/sgf-property-policies.json` | Document YM sub-field expansion                                              |

### Modified files (frontend)

| File                              | Change                                     |
| --------------------------------- | ------------------------------------------ |
| `src/services/configService.ts`   | `contentTypeIdToSlug()` mapping            |
| `src/services/entryDecoder.ts`    | Decode `ct` field from shard entries       |
| `src/services/snapshotService.ts` | Content-type dimension in shard resolution |
| Browse/puzzle-list component      | Three-tab UI component                     |
| Puzzle card component             | Quality stars rendering                    |

---

## Verification

| Phase          | How to verify                                                                                                                                                                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Phase 1**    | **Unit:** 8 rotations of same position → same fingerprint. Different positions → different fingerprints. **Integration:** Publish 2 identical puzzles from different sources → only highest-quality one in output. Dedup registry populated with correct winner. Dedup stats in publish log. |
| **Phase 2**    | **Unit:** Classify known tsumego → 1, drill → 2, teaching material → 3, trivial atari → 3. **Integration:** Full pipeline run → YM contains `ct` and `fp`. Shard directories include `ct1/`, `ct2/`, `ct3/`. Manifest lists `content_type` dimension.                                        |
| **Phase 3**    | **Visual:** Three tabs visible in browse view. Click "Curated" → only ct=1 puzzles shown. Click "All" → all entries. Tab counts reflect manifest data. Quality stars render with correct colors.                                                                                             |
| **End-to-end** | Big-bang reprocess all sources. Verify: dedup eliminates expected ~15K duplicates. Content-type distribution is reasonable (~15% curated, ~60% practice, ~25% training — rough estimate). Snapshot validates. Frontend loads all three tabs correctly.                                       |

**Commands:**

```bash
# Backend unit tests
cd backend/puzzle_manager && pytest -m unit

# Backend quick validation
cd backend/puzzle_manager && pytest -m "not (cli or slow)"

# Frontend tests
cd frontend && npm test

# Full pipeline (big-bang)
python -m backend.puzzle_manager run --source <all-sources> --stage ingest --stage analyze --stage publish
```

---

## Deferred Items (Future Enhancements)

These items were identified in Strategy D research but are **not part of this plan**. Each can be implemented independently after this plan is complete.

### D1. Quality-Weighted Daily Challenge Selection

**What:** Daily challenge generator weights puzzle selection by q≥4 + ct=curated.  
**Why deferred:** Requires content-type (Phase 2) to be live. A config change to the daily generator once data exists.  
**Where it fits:** `stages/daily.py` or daily challenge generator — add `min_quality` and `content_type` filters.  
**Effort:** ~2-3 days.

### D2. Difficulty Classifier Improvement

**What:** Replace placeholder additive scorer with positional analysis (stone density, liberty counts, reading depth estimation).  
**Why deferred:** Orthogonal to quality strategy. Significant R&D effort. Needs Go professional review.  
**Where it fits:** `core/classifier.py` — complete rewrite of scoring logic.  
**Effort:** ~2-3 weeks with calibration.

### D3. Dedup Metadata Merging

**What:** When duplicates are detected, merge best metadata from all copies (e.g., comments from OGS + tags from goproblems + refutations from tsumegodragon).  
**Why deferred:** Complex merge logic with edge cases (conflicting tags, different comment styles). Winner-takes-all is safer for v1.  
**Where it fits:** `stages/publish.py` dedup handler.  
**Effort:** ~1-2 weeks with extensive testing.

### D4. Training Lab as Dedicated Tab

**What:** Add a 4th "Training Lab" tab that shows only ct=3 (teaching) content as a learning mode.  
**Why deferred:** User chose 3 tabs. Training content accessible via "All" tab. Add if user demand warrants it.  
**Where it fits:** Frontend browse component — add tab backed by `ct3` shards.  
**Effort:** ~2 days (backend already supports it once Phase 2 is live).

---

_This plan implements the core of Strategy D plus two originally-deferred enhancements (avg_refutation_depth and config-driven quality scoring) that were promoted into scope after detailed feasibility analysis. The remaining 4 deferred items represent ~3 additional weeks of work that can be scheduled independently based on priority and user feedback._
