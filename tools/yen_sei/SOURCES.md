# yen-sei Data Sources

Comprehensive catalog of puzzle collections evaluated for the yen-sei SFT training pipeline. All sources were scanned, scored against expert-informed criteria, and tiered by teaching quality.

## Evaluation Methodology

### Expert Criteria (Cho Chikun + Lee Sedol consultation)

Selection criteria designed with two Go professional personas:
- **Cho Chikun**: pedagogical clarity, correct/wrong contrast, consequence explanations, appropriate complexity
- **Lee Sedol**: reading depth, shape recognition, "almost right" moves, technique identification

### Hard Gates (must pass ALL)
1. Has at least 2 variation paths (correct vs wrong moves)
2. Has comments beyond pure markers ("Correct"/"Wrong")
3. Valid board size (5, 6, 7, 9, 13, or 19)
4. Minimum 4 setup stones

### Scoring Weights
| Criterion | Weight | What it measures |
|-----------|--------|------------------|
| Comment quality | 40% | Teaching depth: rich-teaching > teaching > moderate > brief > intent |
| Technique identification | 25% | Go technique keywords in comments or tags (ko, tesuji, life-and-death, etc.) |
| Stone density | 15% | Sweet spot: 8-60 stones per puzzle |
| Reading depth | 10% | Number of variation paths (more = deeper reading required) |
| Metadata presence | 10% | Has tags, level, or collection info |

### Quality Tiers
| Tier | Score | Purpose |
|------|-------|---------|
| A | >= 0.5 | SFT gold — direct training data |
| B | 0.3-0.5 | Augmentation candidates — use after Tier 1 model generates synthetic comments |
| C | < 0.3 | Skip — too thin for training value |

## Scan Results (191,794 SGFs across 14 sources)

### Summary

| Source | Total SGFs | Passed Gates | Tier A | Tier B | Tier C | Avg Score |
|--------|-----------|-------------|--------|--------|--------|-----------|
| community-problems | 51,822 | 26,848 | 7,790 | 18,888 | 170 | 0.492 |
| curated-ogs | 42,749 | 18,228 | 3,692 | 12,908 | 1,628 | 0.439 |
| difficulty-graded | 9,412 | 7,700 | 3,008 | 3,156 | 1,536 | 0.486 |
| dragon-archive | 12,836 | 10,806 | 2,134 | 6,508 | 2,164 | 0.423 |
| drill-collection | 23,462 | 19,790 | 0 | 0 | 19,790 | 0.231 |
| classic-books | 19,119 | 6,957 | 1,357 | 1,705 | 3,895 | 0.378 |
| hero-sets | 13,345 | 11,998 | 1,136 | 9,915 | 947 | 0.397 |
| professional-authors | 2,271 | 712 | 500 | 191 | 21 | 0.531 |
| pro-commentary | 421 | 418 | 194 | 222 | 2 | 0.540 |
| pattern-play | 3,780 | 3,384 | 149 | 3,087 | 148 | 0.405 |
| chinese-problems | 2,372 | 2,252 | 142 | 2,002 | 108 | 0.441 |
| competition-drills | 10,035 | 232 | 52 | 54 | 126 | 0.362 |
| shape-basics | 128 | 1 | 0 | 1 | 0 | 0.411 |
| miscellaneous | 42 | 0 | 0 | 0 | 0 | — |
| **TOTAL** | **191,794** | **109,326** | **20,154** | **58,637** | **30,535** | |

### Gate Failure Breakdown
| Gate | Failures | Impact |
|------|----------|--------|
| No variations | 45,353 | Single-line solutions with no wrong-path contrast |
| No teaching comments | 44,918 | Only markers ("Correct"/"Wrong") or no comments at all |
| Too few stones | 2,381 | Minimal positions (<4 stones) |
| Invalid board size | 1,303 | Non-standard board sizes |

### Technique Coverage (across Tier A+B)
The 20K+ teaching puzzles cover these Go techniques well:

| Technique | Mentions | Coverage |
|-----------|----------|----------|
| Ko | 15,043 | Excellent — ko fights, ko threats, approach ko |
| Kill/Capture | 13,010 / 4,668 | Excellent — life-and-death fundamentals |
| Tesuji | 8,667 | Excellent — tactical moves |
| Seki | 4,319 | Good — mutual life positions |
| Eye shape | 3,177 | Good — eye-making and false eyes |
| Shape | 2,393 | Good — good/bad shape recognition |
| Connect/Cut | 2,065 / 1,311 | Good — connectivity tactics |
| Ladder | 750 | Moderate — ladder reading |
| Nakade | 832 | Moderate — inside-killing shapes |
| Snapback | 862 | Moderate — recapture tactics |

### Notable Gaps
- **Joseki**: Minimal coverage (tsumego sources, not opening theory)
- **Endgame**: Almost zero (tsumego collections don't cover yose)
- **Invasion/Reduction**: Minimal — these are position-type techniques not well-suited to isolated tsumego

## Source Profiles

### professional-authors (Avg score: 0.531)
Classic problem books by professional Go players. Contains the Harada collection — ~712 problems with paragraph-length explanations of why moves work or fail. The highest average quality of any source. Every serious teaching example references specific techniques (liberty shortage, ko, eye shape). **Core training data.**

### pro-commentary (Avg score: 0.540)
Professional-grade commentary on weekly Go problems. ~418 puzzles with detailed explanations of correct and incorrect moves. Comments frequently reference consequence chains ("if White plays here, Black can atari..."). Small but premium quality. **Core training data.**

### community-problems (Avg score: 0.492)
Largest source by Tier A count (7,790). Crowd-sourced problems with community-written explanations. Quality varies — the 1,259 "rich-teaching" puzzles are excellent, the 20K "intent" puzzles have move-purpose labels but no deep teaching. Good technique diversity (ko, kill, tesuji, capture all well-represented). **Bulk teaching data with noise.**

### curated-ogs (Avg score: 0.439)
Large collection (42K) with named puzzle collections. Teaching content is concentrated in specific collections — random sampling shows mostly intent-level comments, but 3,692 Tier A puzzles have real teaching. The 749 "rich-teaching" puzzles are very high quality. **Hidden gems in a large haystack — the selector finds them.**

### difficulty-graded (Avg score: 0.486)
Problems organized by difficulty with strong teaching comments. 568 "rich-teaching" + 1,388 "teaching" quality puzzles. Good at explaining seki, snapback, and ko situations. **Strong secondary source.**

### classic-books (Avg score: 0.378)
Professional problem book collections. 734 "rich-teaching" puzzles — the highest raw count of any source. Deep commentary on classic positions, often multi-paragraph. However, many puzzles lack variation trees (single-line solutions). **Rich text but structural limitations.**

### Excluded Sources

| Source | Reason |
|--------|--------|
| drill-collection (23,462) | All Tier C — intent-only comments, zero technique identification. Pure drills with no teaching value for SFT. |
| miscellaneous (42) | Zero passed gates — no variations, no comments |
| shape-basics (128) | Only 1 puzzle passed — too small |

## Decision: Copy Tier A Only

**20,154 puzzles** selected for the yen-sei training pipeline.

After harvest + refine filtering (min 80 chars, dedup, ChatML formatting), we expect **~3,000-5,000 usable SFT examples**. This is the sweet spot for LoRA fine-tuning a 2.3B model.

Tier B (58,637 puzzles) remains in external-sources for future synthetic data generation after the Tier 1 model is trained.
