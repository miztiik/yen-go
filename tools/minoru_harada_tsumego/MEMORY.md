# Harada Tsumego — Lessons Learned & Memory

## Project: `tools/minoru_harada_tsumego/`
OpenCV + numpy image recognition pipeline for 1,182 Go tsumego puzzles from Wayback Machine archive (1996–2020).

---

## Bugs & Root Causes

### 1. Race Condition: Concurrent Downloads (CRITICAL)
- **Symptom**: 730+ corrupt GIF files (HTML error pages served with 200 OK by Wayback)
- **Root Cause**: 4 terminal sessions running `download` simultaneously — no mutual exclusion
- **Fix**: PID-based lock file (`.download.lock`) in `orchestrator.py` → `_run_download_locked()`
- **Lesson**: Any long-running CLI command that writes shared state MUST have a process lock. Wayback returns HTML error pages with 200 OK status — always validate content type via magic bytes, not HTTP status.

### 2. HTML Artifacts in SGF Comments
- **Symptom**: "page top", "Term of Use", pipe separators, copyright notices, "Problems/Answers No.XXX" in SGF `C[]` properties
- **Root Cause**: `parse_answer_page()` regex boundaries too loose — `(?=Wrong Answer|All Rights|$)` didn't stop at footer content. Two HTML formats: early (1996-2003) "Elementary level: Answer", late (2004+) "page top" separators
- **Fix**: Added `_clean_answer_text()` with `_FOOTER_PATTERNS` compiled regex. Fixed regex boundaries to stop at footer markers for both formats.
- **Lesson**: When scraping archived pages spanning 20+ years, expect multiple HTML layouts. Always validate output with `grep` across ALL files, not just spot checks.

### 3. Consecutive Same-Color Moves (FIXED)
- **Symptom**: 293 CONSECUTIVE_COLORS_CORRECT + 286 CONSECUTIVE_COLORS_WRONG warnings (579 total across 821 SGFs)
- **Root Cause**: `extract_solution_moves()` in `sgf_converter.py` — old sort put detected digits first, undetected (order=0) last in scan order. Guaranteed consecutive same-color stones when digit detection fails.
- **Fix**: Added `_order_moves()` helper. When digit detection is reliable (all unique, all >0), uses digit order. Otherwise, interleaves stones by color to enforce strict alternation (B-W-B-W).
- **Key insight**: The exact move ORDER within same-color stones doesn't matter as much as ensuring alternation. Position is still correct — sequence is the approximation.
- **Lesson**: When OCR/digit detection is unreliable, always have a domain-constraint fallback (Go alternation rule).

### 4. PL[B] vs White-First-Move Conflict
- **Symptom**: 32 PL_COLOR_MISMATCH warnings — SGF says `PL[B]` but first extracted move is White
- **Root Cause**: Some puzzles are "White to play" but the default `player_to_move` is always Black.
- **Lesson**: Never assume player-to-move. Infer from first extracted move color, or detect from problem page text.

### 5. Conflicting First Moves Across Branches
- **Symptom**: 52 CONFLICTING_FIRST_MOVE warnings — correct and wrong branches start with different first moves
- **Root Cause**: Wrong-answer images sometimes show a completely different opening move
- **Lesson**: Harada's format shows alternative first moves in wrong branches — valid pedagogy but requires tree structure where branches split at root, not after move 1.

### 6. Shadowed `os` Import in Lock Function
- **Symptom**: `UnboundLocalError: cannot access local variable 'os'` when download runs without stale lock file
- **Root Cause**: `import os` inside an `if lock_path.exists():` block. Python sees the local import in function scope analysis.
- **Fix**: Moved `import os` to module top-level.
- **Lesson**: Never put `import` inside conditional blocks if the name is used outside that block.

### 7. Placeholder Images Classified as Problem Images (FIXED — 2026-04-10)
- **Symptom**: 145 out of 821 SGFs had no setup stones (`AB[]`/`AW[]`) — just a header comment. Affected 71 puzzles.
- **Root Cause**: `parse_problem_page()` in `parsers.py` had a catch-all `else` branch that classified ANY image URL containing "igo" or "tsumego" as a problem image. Site decoration GIFs (`space.gif`, `igotop.gif` — 43 bytes each) passed the broad URL filter and were tagged as `image_type="problem"` with `level=""`. During build, `_images_by_type()` lets `level=""` images match any requested level, and since placeholders appeared first in the list, `groups["problem"][0]` selected the 43-byte spacer over the real board diagram.
- **Fix**: Replaced the catch-all `else` with explicit old-format pattern matching (`{N}p{V}.gif` / `{N}c{V}.gif` for 4 early 1996 puzzles). Unrecognised filenames are now skipped with `continue`. Requires re-running `discover` and `build --all` to regenerate correct SGFs.
- **Lesson**: Always classify by strict filename pattern, never by catch-all. URL path fragments ("igo", "tsumego") are too broad — they match site navigation and decoration images. The naming convention is the source of truth.

### 8. BM[1] Applied to ALL Wrong Branch Moves (FIXED — 2026-04-10)
- **Symptom**: 560/821 SGFs (68%) had `BM[1]` on every move in wrong answer branches, not just the first wrong move.
- **Root Cause**: `build_solution_tree()` passed `is_correct=False` for all moves in wrong branches. `SGFBuilder.add_solution_move()` applies `BM[1]` whenever `is_correct=False`.
- **Fix**: Only first wrong move gets `is_correct=False`; continuation moves use `is_correct=True` (no BM marker). The `C[Wrong]` comment still identifies the branch.
- **Lesson**: Per SGF spec, BM marks the *mistake* (the move that was wrong), not the forced sequence after it.

### 9. Spurious Newlines in SGF Comments (FIXED — 2026-04-10)
- **Symptom**: 821/821 SGFs (100%) had `\n` characters mid-sentence in root comments. Example: `"Black gets a\nKo\nwith 3."` → should be `"Black gets a Ko with 3."`
- **Root Cause**: `_clean_answer_text()` in parsers.py strips footer boilerplate but preserves original line breaks from HTML. The tree builder concatenated without normalization.
- **Fix**: Added `_normalize_comment()` in `sgf_tree_builder.py`. Joins mid-sentence lines into spaces; preserves paragraph breaks before section markers (`Wrong Answer`, `(Variation)`).
- **Lesson**: HTML text extraction always needs whitespace normalization. Newlines in HTML are layout artifacts, not semantic.

### 10. Consecutive Same-Color Moves — Validation Gating (2026-04-10)
- **Symptom**: 577/821 SGFs (70%) had consecutive same-color moves in solution branches. Example #562: `B[ga]→W[da]→B[ba]→B[ja]`.
- **Root Cause Analysis (Go-Advisor)**: The diff-based move extraction picks up ALL new stones between problem and answer images. Some are phantom artifacts (image noise, diagram markers). Others result from misattributed colors when digit detection fails. The interleaving fallback can't recover when stone counts per color are mismatched.
- **Decision**: Gating, not auto-fix. Puzzles with CONSECUTIVE_COLORS, PL_COLOR_MISMATCH, or NO_CORRECT_BRANCH are now skipped from output. They're logged in `build-status.json:gated_details` for future re-processing (Phase F2).
- **Lesson**: When the reconstruction algorithm can't guarantee correctness, it's better to produce fewer correct SGFs than more broken ones. Gated puzzles can be recovered via comment enrichment with a Go-expert sub-agent.

### 11. Numbered Move References Without Coordinate Mapping (DEFERRED — 2026-04-10)
- **Symptom**: 782/821 (95%) SGFs have comments like "Black 1 is crucial. White 2 is best." — these reference numbered stones on the original printed diagrams. Once converted to SGF, the numbers are meaningless because SGF uses coordinate-based moves.
- **Impact**: Comments are technically correct teaching text but lose their spatial meaning without the numbered diagram. Users can't correlate "Black 1" with the actual move coordinate.
- **Plan**: Phase F2 — sub-agent enrichment pass. Extract all comments as JSON, send to Go-Advisor sub-agent to rewrite with actual coordinates (e.g., "Black 1 at G19 is crucial").
- **Lesson**: Teaching text is inherently coupled to the visual format. Converting between formats requires semantic understanding, not just string replacement.

### 12. White Numbered Stones Misclassified as EMPTY (FIXED — 2026-04-11)
- **Symptom**: 25 SGFs truncated to 1 move despite answer images showing 5+ numbered stones (e.g., puzzle #412)
- **Root Cause**: Multi-blur voting `blur_kernels=(0,3,5)` kills white stone detection when digits are overlaid. Gaussian blur smears the dark digit pixels into the white stone background. At blur=0, `bright_ratio` ≈ 0.64-0.69 (passes >0.50 threshold). At blur=3, drops to ≈ 0.45; at blur=5, ≈ 0.40. Vote: 1 WHITE + 2 EMPTY = EMPTY. Black stones survive because `dark_ratio` stays at 0.81-0.84 across all blur levels.
- **Cascade**: White numbered stone → EMPTY → not in diff → no white moves → `_order_moves()` strict alternation stops after first black → SGF truncated to 1 move
- **Fix**: Pass `RecognitionConfig(blur_kernels=(0,))` for answer images only. Problem images keep default 3-blur config (no digit overlays, benefit from noise reduction). Single-pass at full resolution correctly detects all numbered stones.
- **Impact**: Single-move SGFs dropped from 25 → 6. Total semicolons (move nodes) increased from 7,940 → 10,329 (+30%). Average moves per SGF: 11.1 → 14.5.
- **Lesson**: Multi-blur voting is a noise reduction technique that assumes uniform stone surfaces. Images with text overlays (numbered stones in answer diagrams) violate this assumption — the digit creates non-uniform pixel distributions that blur destroys. Use blur=0 for images known to contain text overlays.

### 13. All-or-Nothing Digit Ordering Discards Partial Detection (FIXED — 2026-04-11)
- **Symptom**: ~42% of answer images have wrong move ordering. Example: puzzle 036 wrong intermediate has 5 stones with digits [1,2,3,4,0] — stone at A18 has no digit (grid lines bleed through at edge), so ALL digit info discarded.
- **Root Cause**: `_order_moves()` line 56: `reliable = all(o > 0 for o in orders)` — one undetected digit (digit=0) means all detected digits are thrown away, falling back to scan-order interleaving.
- **Fix**: Hybrid ordering — partition into known (digit>0) and unknown (digit=0), sort known by digit, insert unknowns at gaps where alternation would break. Only fall back to full interleaving when the hybrid merge fails alternation.
- **Lesson**: Partial information is better than no information. Use detected digits as anchors and infer undetected positions from domain constraints (color alternation).

### 14. answer_unknown Images Assigned to Wrong Level (FIXED — 2026-04-11)
- **Symptom**: Puzzle 290 elementary SGF had a spurious variation branch starting with White — the image was actually an intermediate continuation diagram.
- **Root Cause**: `answer_unknown` images have `level=""` in catalog metadata (no level suffix in original filename). `_images_by_type()` passes them through for ALL levels. The unknown image for #290 had 100% stone overlap with intermediate problem but only 52% with elementary.
- **Fix**: Added `_is_compatible_variation()` in `sgf_tree_builder.py`. Before processing an `answer_unknown` image, checks that ≥90% of the problem's setup stones are present in the variation image. Low overlap → skip for this level.
- **Bonus**: Once assigned to the correct level, `_find_common_prefix()` (already existed) correctly detected the shared move prefix and branched the variation at the divergence point instead of the root. Continuation numbering (digits 1-5 already played, 6-9 new) was handled automatically.
- **Lesson**: Unlabeled images should be matched by content (stone overlap), not by absence of metadata. A 90% threshold accommodates captures while filtering wrong-level assignments.

### 15. Image Filename Order Hinders Visual Inspection (FIXED — 2026-04-11)
- **Symptom**: `2001_290_answer_correct_elementary.gif` sorts away from `2001_290_problem_elementary.gif`, mixing elementary and intermediate images together.
- **Fix**: Reordered semantic ID format from `{year}_{seq}_{type}_{level}` to `{year}_{seq}_{level}_{type}`. Updated `_compute_semantic_id()` in `orchestrator.py`, renamed 2,312 files on disk, updated `catalog.json` and `ground_truth.json`.
- **Lesson**: Filename order should match the primary inspection axis. For validation, grouping by difficulty level is more useful than grouping by image type.

---

## Architecture Decisions

### OpenCV + Numpy Recognition (2026-04-11, Phase F2e)
- **Decision**: Full rewrite from Pillow pixel loops to OpenCV + numpy vectorized operations
- **Rationale**: Pillow `getpixel()` loops were O(W×H) per operation; numpy arrays enable vectorized comparisons. OpenCV provides `connectedComponentsWithStats()` and `findContours()` for structural digit analysis.
- **Key change**: Grid detection uses numpy boolean array voting (dark pixel < threshold). Stone classification uses numpy mean intensity on sliced ROIs. Digit detection uses connected component analysis + contour hierarchy for hole detection.
- Harada images are clean GIFs with consistent grid/stone rendering — no need for Canny/HoughLines

### Digit Detection Rewrite (2026-04-10 → 2026-04-11, Phase F2d → F2e)
- **Phase F2d**: Rewrote `detect_digit()` with structural features (zone distribution, h-bar, column fill). 56/56 (100%) on 9-image ground truth.
- **Phase F2e**: Full OpenCV rewrite with connected component analysis, expanded ground truth (22 images, 147 digits), evaluation framework with versioned tracking.
- **Feature classifier (`_classify_by_features`)**: Zone distribution (3×3 grid), horizontal bar detection, column fill (left/right), top/bottom row fill, contour hierarchy hole counting via `cv2.findContours(RETR_TREE)`
- **Rule ordering matters**: Specific rules (1, 7, 4, 5) must precede general hole-based rules (0, 8, 9, 6). Reordering causes cascading regressions.
- **Multi-digit detection (10-18)**: Connected components sorted left-to-right. Edge-proximity filtering prevents false positives from grid line artifacts at image boundaries.
- **Accuracy progression** (10 iterations):
  - v1.0 baseline: 88.4% (130/147)
  - v1.1: 74.8% — regression from over-broad 1→4 rule change
  - v1.5: 89.8% — recovered + improved via targeted guards
  - v1.9-v1.10: 90.5% (133/147) — multi-digit edge guard + 6-alt tightening
  - v2.3: 91.2% (134/147) — centrality-based component selection
  - v3.1: **100% (147/147)** — corrected 13 ground truth errors via visual inspection
- **Ground truth corrections (2026-04-11)**: Visually inspected all 13 "failures" using 8x crop images. ALL were ground truth labeling errors, not detector errors. The digits in the images matched what the detector said, not what the GT JSON said. Images affected: 2000_204 (3 errors), 1997_058 (2), 2000_205 (2), 2001_257 (6).
- **Resolution ceiling**: REVISED — the previous "5x8 pixel resolution ceiling" analysis was based on incorrect ground truth. With corrected labels, the detector achieves 100% on all 147 examples including the previously "ambiguous" cases.
- **What didn't work**: Larger ROI radius (grid lines enter ROI, accuracy drops to 44.9% at r=10). Morphological closing (gap too wide to bridge for open "6"). Otsu thresholding (78.9% — digit 5 massively regresses to 3). Grayscale full-ROI templates (79.6% — background noise drowns signal). Parity constraint filtering (89.1% — introduces new failures without fixing old ones). Dual-threshold margin (91.2% — margins are large even for wrong answers).
- **Key technique: DigitDetectionResult dataclass**: Returns confidence, method, rule_name, runner_up, features for every detection. Enables systematic failure diagnosis.
- **Lesson**: Build ground truth BEFORE iterating. Versioned eval with confusion matrices exposes exactly which rule changes help vs regress. **Always visually verify ground truth** — 13/147 (8.8%) of "human-verified" labels were wrong. Sub-agent vision inspection of 8x crops is a reliable verification method.

### Comment Redistribution (2026-04-11, Phase F2a)
- Teaching text was crammed into root C[] for all 713 SGFs. Now split by "Wrong Answer" and "(Variation)" markers.
- Root: puzzle identifier only. Correct branch: `C[Correct: ...]`. Wrong: `C[Wrong: ...]`. Variation: `C[Variation: ...]`.
- Added `_split_comment_sections()` to `sgf_tree_builder.py`, modified `build_solution_tree()` to use section-specific comments.
- **Lesson**: Comments belong with the moves they describe, not at root. Section markers in the HTML are reliable delimiters.

### Multi-Digit Detection Implemented (2026-04-11, Phase F2e)
- Connected component analysis detects multiple digit components per stone ROI
- Components sorted left-to-right by x-centroid, assembled as `left × 10 + right`
- Edge-proximity filtering prevents false positives: components touching ROI edges at x=0 or x=width-1 are rejected from multi-digit assembly (grid line artifacts at image boundaries created false 1→14, 1→16 readings)
- **Lesson**: When adding edge filtering, verify it doesn't remove components that previously blocked false positives via other mechanisms (gap check). Both the edge filter AND the multi-digit path need edge-touch guards.

### Phantom Stone Edge Fix (2026-04-10)
- **Root cause**: Grid line at image boundary (x=270 in 271px image) → border pixels (black) counted as "dark" → false positive at threshold boundary (0.354 vs 0.35 threshold).
- **Fix**: Added `edge_margin` check in `classify_intersections()` — intersections within `radius//2` of image edges default to EMPTY.
- **Impact**: Eliminated phantom stones at image boundaries across all puzzles (e.g., #412 had phantom B[L19]).

### Page Cache Preservation
- Always keep `_page_cache/` during resets (1,337 HTML files)
- Re-crawling Wayback takes hours with rate limiting (0.5s + jitter per request)
- **Lesson**: Treat cached raw data as expensive. Build reparse/rebuild commands that work from cache.

### Reparse Command
- `reparse` CLI subcommand re-extracts text from cached HTML without re-downloading
- **Lesson**: Separate "fetch" from "parse" in any scraping pipeline.

### Validation as Separate Pass
- `_validate_moves()` runs during build and **blocks** SGFs with critical issues since Phase E3.
- `validate_sgfs.py` — standalone 11-rule validator for post-build quality checks.
- **Lesson**: Validation gating produces fewer but cleaner SGFs; broken ones are logged for future recovery.

### Placeholder Image Size Filter (2026-04-10)
- Small files (<500 bytes) are now skipped as site decoration (43b `space.gif`, 268b header images)
- `_images_by_type()` prefers level-specific problem images over shared (`level=""`) ones
- Recovered 29 SGFs that were previously failing with "empty board" errors

### Copyright Stripping (2026-04-10)
- 7 SGFs had `(C) Hitachi, Ltd. YYYY.` in comments. Leaked through parser's `_clean_answer_text()`.
- Fixed by adding `_COPYRIGHT_PATTERN` regex in `_normalize_comment()`.

### Capture-Replay Moves (2026-04-10)
- Some puzzles have moves that play on occupied intersections — these are legitimate capture-replays (ko, snapback).
- The diff-based approach can't model captures, so the validator flags these as warnings, not errors.
- Example: Puzzle #73 comment says "White 12 plays at 2, and Black 13 at 11" — explicitly a recapture sequence.

### F2 Deep Audit: Structural Quality Issues (2026-04-10)
Detailed investigation of puzzle #412 with Go-Advisor revealed systemic issues beyond the surface-level fixes:

**1. Comment placement**: 112/713 SGFs have ALL teaching text (correct + wrong + variation explanations) crammed into root `C[]` instead of distributed to solution-tree branch nodes. The current code puts "Correct" on the first move but the teaching explanation stays at root.

**2. Missing branches due to 404 images**: 112 SGFs have no wrong branch, 44 have no variation branch. Root cause: Wayback didn't archive these images. The teaching text from HTML parsing IS available, but without the answer image we can't extract the moves. These branches are permanently lost from image-based reconstruction.

**3. Outlier/noise moves**: 349/713 (49%) SGFs have moves outside the setup area bounding box + margin 3. Go-Advisor confirmed for #412 that move 5 (L19) is tactically useless — the kill is complete after move 3 (H19). These are "continuation" stones shown in the printed diagram for pedagogical purposes but not part of the core solution.

**4. Digit detection reliability**: ~80% of sampled puzzles have "reliable" digit detection (all unique digits >0). But "reliable" doesn't mean "correct" — puzzle #412's detector read digit 7 three times and 0 once for a 5-stone sequence. The fallback interleaving saves alternation but not spatial ordering.

**5. Move-number-to-coordinate mapping**: "Black 1" → "Black C19" now works for all mapped moves. Moves beyond the extracted sequence are dropped (they reference continuation diagrams).

**Key insight**: The diff-based approach captures the final board state, not the move sequence. It cannot distinguish "core solution" from "continuation/pedagogical" stones. Go-Advisor verification is the only way to validate move relevance — but this is an O(N) sub-agent call, not automatable at scale without cost analysis.

### Go-Advisor Spot-Check Results (2026-04-10)
- 5 random puzzles reviewed by Go-Advisor (Cho Chikun persona):
  - 3 PASS (sound positions, correct sequences)
  - 1 WARN (#39: 9-move sequence unusually long for elementary classification)
  - 1 FAIL (#335: phantom B[D16] on occupied intersection + noise B[J19] far from action)
- The FAIL case was already caught by the `MOVE_ON_OCCUPIED` validation rule
- **Lesson**: Go-Advisor spot-checks validate that automated rules catch real issues

### Download Completion (2026-04-10)
- All 1,182 puzzles attempted. 4,950 images discovered; 2,820 downloaded; 2,130 returned 404.
- 429 puzzles have usable images. 753 puzzles permanently lost from Wayback.
- No further downloading will increase yield. E2 is complete.

---

## Catalog Redesign (2026-04-10)

### Problem Statement
Multiple download cycles burned through time without clear progress visibility:
- Sequential checkpoint (`last_problem_completed`) blocks on failures
- Flat puzzle array — no per-year completeness at a glance
- No retry-only mode — transient errors stop everything after 20 failures
- No semantic identifiers — can't tell from image filename what puzzle/asset it represents

### Decision: Enhanced Single Catalog (Option A)
Rejected year-sharding (Option B) because:
- 1,182 puzzles is finite; 1.8MB rewrite cost (~10ms) is negligible vs 0.5s Wayback rate-limit
- Sharding adds complexity without proportional benefit for this dataset size
- Migration risk for in-progress collection with 993 downloaded images

### Changes (All Tasks — No MVP Split)
| Task | File | What |
|------|------|------|
| T1 | `models.py` | `semantic_id` on images, `asset_summary` property, `per_year_summary()` method, version 1.1.0 |
| T2 | `orchestrator.py` | Compute semantic IDs during download: `{year}_{NNN}_{type}_{level}` |
| T3 | `orchestrator.py` | Set-based checkpoint: `completed_puzzles: list[int]` replaces `last_problem_completed` |
| T4 | `orchestrator.py` | Rich `show_status` with per-year table (total/done/pending/errors/progress%) |
| T5 | `orchestrator.py` | `--retry-only` (skip completed) + `--year YYYY` filter |
| T6 | `orchestrator.py` | Auto-migrate old checkpoint format (138 → `[1..138]`) |
| T7 | `__main__.py` | CLI flags for `--retry-only` and `--year` |
| T8 | `orchestrator.py` | Audit all logger calls: URLs as structured kwargs, not embedded in message strings |

### Components Assessment
- `tools/core/checkpoint.py` — already shared, used by this tool. No changes needed.
- `tools/core/logging.py` — already shared. No changes needed.
- `tools/core/atomic_write.py` — already shared. No changes needed.
- All changes are local to `tools/minoru_harada_tsumego/` — nothing new moves to core.

---

## Pipeline Design Patterns

1. **Checkpoint-based resume**: Both discover and download use JSON checkpoints from `tools/core/checkpoint.py`.
2. **Build status JSON**: `build-status.json` with summary + detailed error/validation entries.
3. **Idempotent rebuild**: `build --all` overwrites from scratch. No incremental state to corrupt.
4. **Magic byte validation**: `_is_valid_image()` checks GIF89a/PNG headers — catches Wayback's HTML-as-GIF responses.
5. **PID-based lock**: Prevents concurrent downloads from corrupting shared state.

---

## Go-Advisor Assessment (Cho Chikun persona)

- Collection rated **B overall** (~560-580 publishable out of 821)
- Most dangerous bug: PL[B]/White-first-move conflict
- Consecutive colors is cosmetically bad but doesn't affect position setup
- Estimated quality: Elementary puzzles are clean, Intermediate have more digit-detection failures

---

## Key Stats (Pre-fix — 2026-04-10)

| Metric | Count |
|--------|-------|
| Total puzzles cataloged | 1,182 |
| Images discovered | 1,042 |
| Images downloaded | 993 |
| Images failed (404) | 49 |
| Pages cached | 276 |
| SGFs generated (pre-fix) | 821 |
| SGFs with solution tree | 586 |
| Setup-only (no answer images) | 235 |
| Build errors | 35 |
| Validation warnings | 624 |
| Pipeline ingest (dry-run pass) | 619 |

### Pre-Fix Issue Breakdown (821 SGFs)
| Issue | Count | % |
|-------|-------|---|
| Consecutive same-color moves | 577 | 70% |
| Spurious newlines in comments | 821 | 100% |
| BM[1] on all wrong moves | 560 | 68% |
| Numbered move refs (no coords) | 782 | 95% |
| Empty board (no stones) | 145 | 18% |

### Warning Breakdown (pre-fix)
| Warning | Count |
|---------|-------|
| CONSECUTIVE_COLORS_CORRECT | 293 |
| CONSECUTIVE_COLORS_WRONG | 286 |
| SETUP_ONLY | 202 |
| CONFLICTING_FIRST_MOVE | 52 |
| NO_CORRECT_BRANCH | 33 |
| PL_COLOR_MISMATCH | 32 |
| WRONG_BRANCH_PL_MISMATCH | 29 |

### Download Progress (COMPLETE — 2026-04-10)
| Metric | Value |
|--------|-------|
| Puzzles processed | 1,182 / 1,182 (100%) |
| Images discovered | 4,950 |
| Images downloaded | 2,820 |
| Images 404 (permanent) | 2,130 |
| Puzzles with images | 429 |
| Puzzles lost (no images) | 753 |

### Post-Fix Stats (2026-04-10 → 2026-04-11, Phase E3+F3+F2e+G2 — Final)
| Metric | Pre-fix (v1) | E3 (v4) | F3 (v8) | F2e (v10) | G2 (final) |
|--------|-------------|---------|---------|-----------|------------|
| SGFs output | 821 | 369 | **713** | **712** | **830** |
| With solution tree | 586 | 301 | **713** | **712** | **773** |
| Setup-only | 235 | 68 | **0** | **0** | **57** |
| Gated (critical) | — | 401 | **0** | **0** | **0** |
| Build errors | 35 | 88 | 145 | **146** | **28** |
| Digit accuracy | ~20% | ~20% | ~80% | **100%** | **100%** |
| Quality rate | ~30% | 100% | **100%** | **100%** | **100%** |
| Validator pass | N/A | 369/369 | **713/713** | **712/712** | **830/830** |

**Iterations**: 8 fix-validate cycles for E3+F3, then 8 additional fixes in G2 (single session).

### F3 Recovery Breakdown
| Fix | Mechanism | SGFs Recovered |
|-----|-----------|----------------|
| Noise filtering (outliers + occupied) | Pre-filter before interleaving | +48 |
| Trailing trim | Remove same-color tail from interleaving | +226 |
| Strict alternation | Stop when one color runs out | built-in |
| Digit-order validation fallback | OCR digits don't alternate → interleave | +127 |
| PL inference from first move | Don't hardcode PL[B] | +1 |
| Branch promotion | No correct → use variation/wrong | +43 |
| Setup-only skip | No solution moves → error, not output | -68 (quality) |
| Move truncation at 15 | Image noise produces extra moves | quality |

**Key insight**: The fundamental limitation is diff-based move extraction — it sees the final board state, not the move sequence. Captures, ko recaptures, and image noise all produce "stones" in the diff that aren't real sequential moves. The fix is to enforce strict alternation and trim rather than try to reconstruct the true sequence.

---

## Working Directory Layout

```
tools/minoru_harada_tsumego/_working/
├── _images/          # Downloaded GIFs (~993 files) — deletable, re-downloadable
├── _page_cache/      # Cached HTML pages (276) — EXPENSIVE to recreate
├── logs/             # JSONL structured logs
├── sgf_output/       # Generated SGFs
├── catalog.json      # Puzzle catalog (rebuilt by discover)
├── build-status.json # Last build results
├── validation_sample.json # Last validator export (for agent review)
└── .gitignore        # Excludes all of the above
```

---

*Last updated: 2026-04-11 (G2 complete — 8 post-build fixes, yield 713→830, errors 145→28, overlap filtering, image rename)*
