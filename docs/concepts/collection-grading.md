# Collection Grading

_Last Updated: 2026-02-14_

> **See also**:
>
> - [Concepts: Collections](./collections.md) -- Collection taxonomy and schema
> - [Concepts: Quality Metrics](./quality.md) -- Per-puzzle YQ/YX metrics
> - [Tool: sort_collections.py](../../tools/source_adapter/sort_collections.py) -- Implementation

When YenGo imports puzzle collections from external community platforms, there are thousands of collections to choose from -- but they vary wildly in quality. Some are carefully curated by professional Go players with hundreds of well-structured problems. Others are a single test puzzle named "aaaaaaaa" with zero solvers.

Collection grading answers two questions:

1. **Which collections should we download next?** (pipeline priority)
2. **Which collections are worth showing to users?** (frontend display)

---

## How the Scoring Works

Every collection gets a **priority score** between 0.0 and 1.0. The score combines three signals, each measuring a different aspect of collection quality.

### The Three Signals

**Rating Quality (30% of the score)**

Users on the source platform rate collections on a 1-to-5 star scale. But raw star ratings are misleading -- a collection with a single 5-star rating is not necessarily better than one with 10,000 ratings averaging 4.5 stars. To fix this, the algorithm uses a **Bayesian average** (explained below) that adjusts for rating confidence.

**Community Engagement (35% of the score)**

This is the heaviest weight because it is the hardest signal to fake. It combines:

- **View count** (60% of engagement): How many people have looked at this collection. Measured on a logarithmic scale because the difference between 100 and 1,000 views matters more than the difference between 1,000,000 and 1,001,000.
- **Solve rate** (40% of engagement): What fraction of attempts result in a solve. This indicates whether the difficulty labeling is accurate and whether the problems are well-constructed. Capped at 1.0 because source platforms often count solves per-puzzle while counting attempts differently, so `solved_count` can sometimes exceed `attempt_count`.

**Content Value (20% of the score)**

How many puzzles the collection contains, measured on a logarithmic scale. A collection with 100 puzzles is much more useful than one with 10, but a collection with 1,000 puzzles is not 10 times more useful than one with 100. Diminishing returns are the reason for the log scale.

### Size Penalty

Very small collections get a penalty multiplier applied to their final score:

| Puzzle Count | Multiplier        | Rationale                         |
| ------------ | ----------------- | --------------------------------- |
| 1-2 puzzles  | 0.3 (70% penalty) | Likely test/throwaway content     |
| 3-4 puzzles  | 0.5 (50% penalty) | Too small to be a real collection |
| 5-9 puzzles  | 0.8 (20% penalty) | Minimal but potentially useful    |
| 10+ puzzles  | 1.0 (no penalty)  | Full-sized collection             |

### The Formula

```
priority_score = (
    bayesian_rating_normalized * 0.30 +
    engagement_score           * 0.35 +
    content_score              * 0.20
) * size_multiplier
```

Each component is normalized to a 0-to-1 range before weighting, so they contribute proportionally regardless of their raw scales.

---

## What Is Bayesian Rating?

In plain English: **a Bayesian rating is a star rating that has been adjusted for how many people actually voted.**

Imagine two restaurants:

- Restaurant A: one review, 5 stars
- Restaurant B: 10,000 reviews, 4.5 stars average

Which is more likely to be good? Restaurant B, obviously. The single 5-star review at Restaurant A could be the owner's friend. But 10,000 people agreeing on 4.5 stars is a strong signal.

A Bayesian rating does this adjustment mathematically. It works by blending each collection's actual rating with the **global average rating** (about 4.39 stars across all imported collections). Collections with few ratings get pulled strongly toward the global average. Collections with many ratings stay close to their actual number.

The formula:

```
bayesian_rating = (actual_rating * rating_count + global_mean * C) / (rating_count + C)
```

Where `C` is the median number of ratings across all collections (about 3 in the current dataset). This means:

- A collection with 1 rating of 5.0 gets a Bayesian rating of about 4.5 (pulled toward the mean)
- A collection with 10,000 ratings of 4.5 gets a Bayesian rating of about 4.5 (barely changed)
- A collection with 0 ratings gets the global mean of 4.39

The result is a rating you can actually compare across collections regardless of how many people voted.

---

## Quality Tiers

After computing scores, collections are divided into four tiers based on their percentile rank:

### Premier (Top 10%)

The best of the best. These are collections that score highly across all three signals -- good ratings, heavy community use, and substantial puzzle counts.

**What you find here:** Cho Chikun's Encyclopedia of Life and Death, Fran's Library, Guan Zi Pu, James Davies' Tesuji, curated beginner courses. Professional-authored works and the most popular community collections.

**Typical stats:** Median 34 puzzles, median 6,285 views, scores 0.52-0.71.

### Curated (Top 10-30%)

Solid collections with clear educational value. Good community engagement and reasonable size, but not in the top tier.

**What you find here:** Specialized technique sets, regional Go school curricula, translated problem books, well-maintained community projects.

**Typical stats:** Median 16 puzzles, median 1,258 views, scores 0.44-0.52.

### Community (Top 30-60%)

Usable collections that have some community validation but may be smaller, less popular, or more niche.

**What you find here:** Personal problem sets with some followers, small technique drills, club homework collections.

**Typical stats:** Median 6 puzzles, median 254 views, scores 0.19-0.44.

### Unvetted (Bottom 40%)

Collections with minimal community engagement. Many are test uploads, single-puzzle experiments, or abandoned projects.

**What you find here:** Collections named "test", "aaaaaaaa", "deneme" (Turkish for "test"), single-puzzle uploads, collections with zero solves.

**Typical stats:** Median 1 puzzle, median 63 views, scores 0.04-0.19.

---

## What `sort_rank` Means

Every collection gets a `sort_rank` from 1 to N (currently 3,230). Rank 1 is the highest-priority collection. The rank is simply the position after sorting all collections by `priority_score` descending. Ties are broken by view count (more views = lower rank number).

The rank is useful for:

- **Pipeline operators**: "Download the top 200 collections first"
- **Frontend**: "Show collections in this order on the browse page"
- **Analysis**: "Compare where a specific collection falls relative to others"

---

## Expert Opinion: Where to Draw the Line

Two perspectives on when external collections stop being worth the effort to import, informed by professional Go player principles on tsumego study.

### Cho Chikun's Perspective (Quality-First)

Cho Chikun, 25th Honinbo and author of the definitive _Encyclopedia of Life and Death_, has consistently advocated that **quality matters more than quantity** in tsumego study. His teaching philosophy: solve well-constructed problems from recognized sources, and solve them repeatedly until the patterns are internalized.

Applying this philosophy to collection selection: **the premier and curated tiers (top 30%, roughly ranks 1-969) represent the collections worth importing.** These have meaningful community validation (median 1,258+ views), sufficient content (median 16+ puzzles), and demonstrated educational value.

Below rank ~970 (the curated/community boundary), collections become progressively more speculative:

- Puzzle counts drop (median 6 in community tier, median 1 in unvetted)
- Community engagement drops sharply (median 254 views in community, 63 in unvetted)
- The ratio of genuine educational content to test/junk uploads deteriorates

**Cho-style cutoff: score >= 0.44 (curated tier and above, ~969 collections)**

This is the conservative, high-quality approach. You get approximately 28,000 puzzles from ~969 well-validated collections.

### Lee Changho's Perspective (Volume with Validation)

Lee Changho, arguably the greatest competitive Go player in history, is famous for solving the same tsumego books hundreds of times. But he also emphasizes **breadth** -- exposure to diverse problem types builds pattern recognition that narrow study cannot replicate.

Applying this philosophy: **extend the cutoff into the community tier, but apply a minimum engagement threshold.** A collection with 5+ puzzles and 100+ views has been seen by real players and is more likely to contain legitimate problems, even if it is not a recognized classic.

The community/unvetted boundary (rank ~1,938, score ~0.19) is where collections degrade sharply -- names become random strings, puzzle counts drop to 1, and view counts suggest nobody has looked at them. But the _upper half_ of the community tier (ranks 970-1,450, scores 0.30-0.44) still contains usable material.

**Lee-style cutoff: score >= 0.30 (upper community tier and above, ~1,450 collections)**

This is the broader approach. You get approximately 35,000 puzzles from ~1,450 collections, accepting some lower-quality material in exchange for more diverse problem exposure.

### Practical Recommendation

| Use Case                               | Cutoff        | Collections                | Estimated Puzzles |
| -------------------------------------- | ------------- | -------------------------- | ----------------- |
| **Conservative** (frontend "Featured") | score >= 0.52 | ~323 (premier only)        | ~14,000           |
| **Standard** (pipeline import)         | score >= 0.44 | ~969 (premier + curated)   | ~28,000           |
| **Broad** (comprehensive import)       | score >= 0.30 | ~1,450 (+ upper community) | ~35,000           |
| **Everything** (research/analysis)     | no cutoff     | 3,230                      | ~45,000           |

Below score 0.19 (the unvetted tier), collections are not worth importing for any purpose other than research. The median collection has 1 puzzle and 63 views.

---

## Output Fields

The sorting utility (`tools/source_adapter/sort_collections.py`) adds these fields to each collection record in the output JSONL:

| Field             | Type          | Description                                                                          |
| ----------------- | ------------- | ------------------------------------------------------------------------------------ |
| `sort_rank`       | int           | Position in the sorted list (1 = highest priority)                                   |
| `priority_score`  | float         | Composite score from 0.0 to 1.0 (6 decimal places)                                   |
| `quality_tier`    | string        | `"premier"`, `"curated"`, `"community"`, or `"unvetted"`                             |
| `bayesian_rating` | float         | Confidence-adjusted star rating (4 decimal places)                                   |
| `solve_rate`      | float or null | Fraction of attempts that resulted in solves (capped at 1.0), or null if no attempts |

All original fields from the input JSONL are preserved unchanged.

---

## Usage

```bash
# Sort collections from the source extraction
python -m tools.source_adapter.sort_collections --input external-sources/source_platform/20260211-203516-collections.jsonl

# Custom output path
python -m tools.source_adapter.sort_collections -i <input.jsonl> -o <output.jsonl>

# Verbose logging
python -m tools.source_adapter.sort_collections -i <input.jsonl> -v
```

Default output: `<input-stem>-sorted.jsonl` in the same directory as the input file.

---

## Design Decisions

- **Log scales for views and puzzle count** -- Prevents outliers (10M-view collections) from dominating. The difference between 100 and 1,000 views is more meaningful than between 1M and 2M.
- **Bayesian over raw rating** -- Raw star ratings are unreliable with few voters. The Bayesian prior pulls uncertain ratings toward the global mean.
- **Solve rate capped at 1.0** -- Platform counting semantics allow `solved_count > attempt_count`. Uncapped solve rates distort the engagement score.
- **Percentile-based tiers** -- Fixed percentiles (10/30/60/100) rather than fixed score thresholds. This means tiers adjust naturally if the overall quality distribution shifts with new data.
- **Size penalty, not size filter** -- Small collections are penalized but not excluded. A 2-puzzle collection with 50,000 views still appears (just ranked lower than a 100-puzzle collection with the same engagement).
- **No source provenance scoring** -- The algorithm does not boost collections based on author name recognition. This is intentional: provenance is already captured in `YL[]` matching and collection taxonomies. The grading algorithm should be objective and data-driven.

---

## Puzzle-to-Collection Overlap Analysis

Analysis of the full source dataset (57,970 unique puzzles across 3,230 collections) reveals that puzzle overlap across collections is negligible.

### Distribution

| Collections per Puzzle | Puzzles | Share |
| ---------------------- | ------- | ----- |
| 1                      | 57,824  | 99.7% |
| 2                      | 146     | 0.3%  |
| 3+                     | 0       | 0.0%  |

**No puzzle appears in more than 2 collections.** The mean and median are both 1.0.

### Per-Tier Overlap

Overlap rates within each quality tier:

| Tier      | Unique Puzzles | In 2 Collections | Overlap Rate |
| --------- | -------------- | ---------------- | ------------ |
| Premier   | 27,943         | 21               | 0.1%         |
| Curated   | 18,699         | 48               | 0.3%         |
| Community | 9,334          | 50               | 0.5%         |
| Unvetted  | 1,994          | 27               | 1.4%         |

Puzzles do not cross tiers -- every puzzle's collections all fall within a single tier. There is no case of a puzzle appearing in both a premier and a curated collection, for example.

### Overlap by Priority Score Threshold

| Threshold          | Collections | Unique Puzzles | Max Overlap |
| ------------------ | ----------- | -------------- | ----------- |
| >= 0.60            | 45          | 12,577         | 1           |
| >= 0.52 (premier)  | 335         | 28,332         | 2           |
| >= 0.44 (standard) | 959         | 46,483         | 2           |
| >= 0.30 (broad)    | 1,614       | 54,613         | 2           |
| >= 0.19            | 1,949       | 56,014         | 2           |

### `YL[]` Assignment Algorithm

Given the negligible overlap, the collection assignment algorithm for the `YL[]` SGF property is straightforward: **assign all qualifying collections**.

```
For each puzzle being ingested:
  1. Look up all collections that contain this puzzle ID
  2. Filter to collections with priority_score >= 0.3
  3. Write ALL remaining collection slugs to YL[] (comma-separated)
```

No selection, ranking, or cap logic is needed. The `YL[]` property will contain:

- **1 value** for 99.7% of puzzles
- **2 values** for 0.3% of puzzles
- **Never more than 2 values**

The 146 dual-collection puzzles are mostly from duplicate collection uploads on the source platform (e.g., the "Number Shape" series appearing twice with identical scores). Keeping both entries is correct -- they represent the same pedagogical lineage and the `YL[]` field handles multiple values natively.

### Implications

- **No "top N" selection needed** -- The anticipated scenario of puzzles belonging to dozens or hundreds of collections does not exist in the dataset. The maximum is 2.
- **Quality filtering happens at the collection level** -- The priority score threshold (>= 0.3) applied during collection selection is sufficient. No per-puzzle filtering is needed.
- **No truncation logic required** -- The `YL[]` field will never exceed 2 comma-separated values, well within any reasonable size limit.
