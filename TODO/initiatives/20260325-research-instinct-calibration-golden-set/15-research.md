# Research Brief — Instinct Classifier Calibration Golden Set

Last Updated: 2026-03-25

## 1. Research Question and Boundaries

**Question**: What source data, infrastructure, and labeling approach should we use to build a calibration golden set for the instinct classifier (push, hane, cut, descent, extend)?

**Boundaries**:
- Scope: instinct classifier at `tools/puzzle-enrichment-lab/analyzers/instinct_classifier.py` — 5 instinct types only
- Must reuse existing calibration infrastructure patterns (labels.json + fixtures)
- Must NOT require KataGo for golden set construction (instinct classifier is geometry-based, not engine-based)
- Must be held-out from pipeline (follows existing calibration/golden-calibration precedent)

---

## 2. Internal Code Evidence

### R-2.1 Instinct Classifier Architecture

| ID | Finding | File |
|----|---------|------|
| R-2.1a | Classifier detects 5 instincts: `push`, `hane`, `cut`, `descent`, `extend` | `tools/puzzle-enrichment-lab/analyzers/instinct_classifier.py` |
| R-2.1b | Each detection function returns `InstinctResult(instinct, confidence, evidence)` with 3 tiers: HIGH/MEDIUM/LOW | Same file, lines 100-300 |
| R-2.1c | `select_primary()` picks winner using `min_confidence` (0.65), `clarity_threshold` (0.15), `max_before_ambiguous` (4) | Same file, ~line 310 |
| R-2.1d | Confidence ranges: cut (0.45/0.65/0.85), push (0.40/0.60/0.80), hane (0.45/0.65/0.85), descent (0.35/0.55/0.75), extend (0.35/0.50/0.65) | Same file |
| R-2.1e | Input: `Position` (board stones), `AnalysisResponse` (correct move GTP coord), board_size | Same file |
| R-2.1f | L-shape verification added for hane detection to reduce false positives | Same file, ~line 200 |

### R-2.2 Existing Golden Calibration Infrastructure

| ID | Finding | File |
|----|---------|------|
| R-2.2a | `golden-calibration/labels.json` — 95 puzzles total (30 cho-advanced, 30 cho-elementary, 30 cho-intermediate, 5 ko) | `tools/puzzle-enrichment-lab/tests/fixtures/golden-calibration/labels.json` |
| R-2.2b | Label schema has: `sgf_file`, `correct_move_sgf`, `correct_move_gtp`, `human_difficulty`, `labeling_method` ("C"=collection), `source`, `notes` | Same file |
| R-2.2c | **No `instinct_labels` field** in current labels.json — README.md specifies that schema but it's not populated | `golden-calibration/README.md` |
| R-2.2d | `test_instinct_calibration.py` — skeleton test exists, requires ≥50 puzzles, targets ≥70% accuracy (AC-4), both tests currently `pytest.skip` | `tools/puzzle-enrichment-lab/tests/test_instinct_calibration.py` |
| R-2.2e | Golden calibration puzzles sourced from `calibration/cho-advanced/`, `calibration/cho-elementary/`, `calibration/cho-intermediate/`, `calibration/ko/` subdirs | `labels.json` sgf_file paths |

### R-2.3 Existing Benchmark & Calibration Fixtures

| ID | Finding | File |
|----|---------|------|
| R-2.3a | **Benchmark** (49 puzzles): Named `L{level_id}_{seq:03d}_{technique}.sgf`. Sourced from goproblems.com + tsumego-hero.com. Covers all 9 difficulty levels | `tests/fixtures/benchmark/README.md` |
| R-2.3b | **Extended-benchmark** (13 puzzles): Named `{technique}_{level}_{source_id}.sgf`. Sourced from goproblems. 5 techniques × 3 difficulty levels | `tests/fixtures/extended-benchmark/README.md` |
| R-2.3c | **Calibration** (90+ CHO puzzles + 5 ko): Used for KataGo difficulty calibration (P.1.3). Has `cho-elementary/`, `cho-intermediate/`, `cho-advanced/`, `ko/`, `results/` subdirs | `tests/fixtures/calibration/README.md` |
| R-2.3d | `test_calibration.py` uses `run_batch()` CLI, requires KataGo engine, targets difficulty ordering: avg(Elementary) < avg(Intermediate) < avg(Advanced) | `tests/test_calibration.py` |

### R-2.4 CLI Single-Puzzle Enrichment

| ID | Finding | File |
|----|---------|------|
| R-2.4a | `enrich` subcommand: `python cli.py enrich --sgf puzzle.sgf --output result.json --katago /path` | `tools/puzzle-enrichment-lab/cli.py` |
| R-2.4b | `--emit-sgf` flag writes enriched SGF directly | Same, ~line 199 |
| R-2.4c | Output format: `AiAnalysisResult` JSON (includes `puzzle_id`, `validation`, `difficulty`, full enrichment data) | Same |
| R-2.4d | **Important**: Instinct classification does NOT require KataGo — it's a pure geometry check. Only needs Position + correct move coordinate | `instinct_classifier.py` |

---

## 3. External Source Evidence

### R-3.1 Source Directories Analysis

| ID | Source | SGF Count | Technique Info in Filenames | Technique Info in SGF | Difficulty Info | Board Size | Quality |
|----|--------|-----------|---------------------------|----------------------|-----------------|------------|---------|
| R-3.1a | `goproblems/sgf/` | **51,822** across 52 batches | **No** — numeric IDs only (e.g., `189.sgf`) | **Yes** — `YT[tesuji]`, `YG[beginner]`, `YQ[q:3;...]`, `YL[ladder-problems]` in enriched ones; `C[]` comments with RIGHT/WRONG | `YG` property (pipeline-enriched) | 19×19 | **HIGH** — pre-enriched with Yen-Go properties, has solution trees |
| R-3.1b | `goproblems_difficulty_based/` | **9,412** across easy/medium/hard × 7 categories | **Yes** — organized by `tesuji/`, `life_and_death/`, `elementary/`, `endgame/`, `fuseki/`, `joseki/`, `best_move/`; numeric IDs | **Yes** — `GE[tesuji]`, `DI[4k]`, `DP[30]`, `SO[Hans]`, `CO[7]` in raw SGFs | **Yes** — dirs `easy/medium/hard` + `DI` property (e.g., `4k`) | 19×19 | **HIGH** — has difficulty, genre, depth, contributor id; solution trees with RIGHT markers |
| R-3.1c | `kisvadim-goproblems/` | **18,275** across 63 book collections | **Yes** — dirs named by technique (e.g., `SAKATA EIO TESUJI/Hane-s-01.sgf`, `kiri-s-01.sgf`, `Sagari-s-01.sgf`, `Tobi-s-01.sgf`) | **Yes** — `C[]` comments describing techniques (e.g., "When speaking about hane...", "a good kiri is wonderful") | **Partial** — some graded (Kano 239 Graded), most by pro author rep | 13-19 mixed | **GOLD MINE** — Japanese technique names map directly to instinct types |

### R-3.2 Kisvadim Technique-to-Instinct Mapping (CRITICAL)

The `SAKATA EIO TESUJI` collection has files named by Japanese tesuji technique, which map directly to the 5 instincts:

| ID | Kisvadim Filename Prefix | Japanese Term | Maps to Instinct | File Count | Has Solution Tree |
|----|--------------------------|---------------|-------------------|------------|-------------------|
| R-3.2a | `Hane-s-*` | Hane (ハネ) | **hane** | 10 | Yes — with C[] teaching |
| R-3.2b | `kiri-s-*` | Kiri (切り) = Cut | **cut** | 12 | Yes |
| R-3.2c | `Sagari-s-*` | Sagari (下がり) = Descent | **descent** | 12 | Yes |
| R-3.2d | `Tobi-s-*` | Tobi (飛び) = Jump/Extension | **extend** | 10 | Yes |
| R-3.2e | `Tsuke-s-*` | Tsuke (付け) = Attachment | push (close equivalent) | 17 | Yes |
| R-3.2f | `Kosumi-s-*` | Kosumi (コスミ) = Diagonal | (diagonal — not an instinct) | 18 | Yes |
| R-3.2g | `Warikomi-s-*` | Warikomi (割り込み) = Wedge | **cut** variant | 7 | Yes |
| R-3.2h | `Kake-s-*` | Kake (カケ) = Press | **push** variant | 8 | Yes |

**Also valuable**: `MAKING SHAPE TESUJI` collection has `ch13.2.counter-hane.tesuji.*.sgf`, `ch13.3.cross-cut.tesuji.*.sgf`, `ch13.4.driving.tesuji.*.sgf` — filename-embedded technique labels.

**Also valuable**: `LEE CHANGHO TESUJI` has 16 technique chapters organized as subdirs (e.g., `1. FIGHTING AND CAPTURING/`, `2. SNAPBACK AND SHORTAGE OF LIBERTIES/`, `3.1 CONNECTING GROUPS/`, `3.2 SPLITTING GROUPS/`).

### R-3.3 Kano Yoshinori Collection

| ID | Finding |
|----|---------|
| R-3.3a | 239 sequentially numbered SGFs (`001.sgf` to `239.sgf`), board size 13×13 |
| R-3.3b | Rich `C[]` comments with problem descriptions (e.g., "How does Black play to capture a white stone?", "How does Black play to make a living group?") |
| R-3.3c | Correct/Wrong answer labels in comments |
| R-3.3d | Graded by section/problem number (known difficulty progression) |
| R-3.3e | **Caveat**: 13×13 board — instinct classifier assumes 19×19 default, may need board_size adaptation |

### R-3.4 Goproblems Difficulty-Based Collection

| ID | Finding |
|----|---------|
| R-3.4a | Pre-categorized into `easy/medium/hard` × `{tesuji, life_and_death, elementary, endgame, fuseki, joseki, best_move}` |
| R-3.4b | SGF has `GE[tesuji]` (genre), `DI[4k]` (difficulty rank), `DP[30]` (depth), `SO[adum]` (contributor), `CO[7]` (comment count) |
| R-3.4c | `easy/tesuji/` has ~600 SGFs — ample supply for instinct calibration |
| R-3.4d | Numeric puzzle IDs (e.g., `5.sgf, 1029.sgf`) — same puzzles as in `goproblems/sgf/` but reorganized and with metadata headers |
| R-3.4e | **No pipeline-enrichment** — raw SGFs from goproblems.com crawl, unlike `goproblems/sgf/` which has YT/YG properties |

---

## 4. Candidate Adaptations for Yen-Go

### Option A: SAKATA EIO TESUJI Golden Set (Recommended)

**Source**: `kisvadim-goproblems/SAKATA EIO TESUJI/`
- 107 SGFs with technique-labeled filenames mapping to 4 of 5 instincts directly
- Author: Sakata Eio 9-dan (authoritative professional assessment)
- Already in repo, no download needed
- Filename structure `{technique}-s-{num}.sgf` enables automated labeling

**Labeling workflow**:
1. Map Hane→hane, kiri→cut, Sagari→descent, Tobi→extend, Tsuke/Kake→push
2. Parse each SGF to extract correct move coordinate from solution tree
3. Run instinct classifier on each puzzle
4. Human review label accuracy (only mismatches need manual review)

**Gaps**: Push instinct coverage weaker (Tsuke=attachment isn't a perfect push analog)

### Option B: MAKING SHAPE TESUJI + SAKATA Hybrid

**Source**: Combine `SAKATA EIO TESUJI/` + `MAKING SHAPE TESUJI/` + `LEE CHANGHO TESUJI/`
- Additional technique labels from chapter names (counter-hane, cross-cut, driving)
- Broader coverage, more puzzles
- More labeling effort (chapter→instinct mapping is less direct than SAKATA)

### Option C: Goproblems Difficulty-Based Tesuji Subset

**Source**: `goproblems_difficulty_based/easy/tesuji/` + `medium/tesuji/` + `hard/tesuji/`
- ~1800 tesuji SGFs across 3 difficulty levels
- **Pro**: Difficulty stratification built-in; huge sample size
- **Con**: No technique sub-label — every SGF is just "tesuji" → requires manual instinct labeling of each puzzle

### Option D: Extend Existing Golden Calibration Set

**Source**: Add `instinct_labels` field to existing `golden-calibration/labels.json`
- 95 puzzles already have `correct_move_sgf/gtp` + difficulty labels
- Just need to add instinct labels per puzzle
- **Con**: These are life-and-death puzzles (Cho Chikun) — may be biased toward descent/hane, underrepresenting push/cut/extend

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R-5.1 | SAKATA EIO SGFs are 19×19 with teaching comments — instinct classifier ignores comments, only uses stone positions + correct move. Technique labels come from *filename* not from classifier output | Low | Verify each puzzle's correct move is extractable from solution tree, not just described in comments |
| R-5.2 | Some SAKATA puzzles may have ambiguous instinct (e.g., a "hane" puzzle where the correct move is also a cut) — multi-label puzzles | Medium | Allow multi-instinct labels in schema; require agreement with at least one label |
| R-5.3 | Push instinct has weakest source coverage — Tsuke (attachment) and Kake (press) are related but not identical to "push toward edge" as defined in classifier | Medium | Supplement with goproblems puzzles manually identified as push scenarios |
| R-5.4 | 13×13 board puzzles (Kano) need board_size parameter — classifier's `_nearest_edge_distance` function supports any board size but defaults to 19 | Low | Pass explicit `board_size` from SGF `SZ` property |
| R-5.5 | Kisvadim SGFs may have encoding issues (CJK characters in Lee Changho comments: `EV[ƪ 1-60]`) | Low | Classifier doesn't use comments — irrelevant for instinct detection |

**Rejection reasons**:
- Option C (goproblems tesuji) rejected as primary approach: no per-puzzle technique label → too much manual work for initial set
- External web scraping: not needed — existing sources in `external-sources/` are sufficient

---

## 6. Planner Recommendations

1. **Use SAKATA EIO TESUJI as primary golden set source** (Option A). It provides 107 puzzles with professional-grade technique labels mapped directly to 4 of 5 instinct types via filename. Copy selected puzzles to a new `tests/fixtures/instinct-golden/` directory (following held-out convention from `golden-calibration/`).

2. **Extend labels.json schema with `instinct_labels`**. Add to the existing golden-calibration schema pattern: `"instinct_labels": ["hane"]`, `"expected_confidence_tier": "HIGH"`. Allow multi-label for ambiguous puzzles. This aligns with the README.md schema that already specifies `instinct_labels` but was never populated.

3. **Supplement push instinct with manual curation** from `goproblems_difficulty_based/easy/tesuji/` (10-15 puzzles). The push detection pattern (`own behind, opponent ahead, edge proximity`) is distinct enough that a Go-knowledgeable human can identify good candidates from ~600 easy tesuji SGFs in 30-60 minutes.

4. **Target 60-80 puzzles total** (12-16 per instinct × 5 instincts). This exceeds the 50-puzzle minimum required by `test_instinct_calibration.py` and provides enough statistical power for per-instinct accuracy measurement while keeping manual review tractable.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| Post-research confidence | **82/100** |
| Post-research risk level | **low** |
| Key uncertainty | Push instinct source coverage — Tsuke/Kake may not map cleanly; may need 10-15 manually curated push puzzles |
| Strongest signal | SAKATA EIO TESUJI collection is a near-perfect source — professional attribution, technique-labeled filenames, solution trees, all 19×19, already in repo |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should the golden set be a new directory (`instinct-golden/`) or extend existing `golden-calibration/`? | A: New `instinct-golden/` directory / B: Add instinct fields to existing `golden-calibration/labels.json` / C: Both (instinct-golden for instinct-specific + extend golden-calibration for overlap) | A — new directory keeps concerns separate, avoids coupling instinct calibration with difficulty/entropy calibration | | ❌ pending |
| Q2 | Accept 13×13 board puzzles from Kano collection, or restrict to 19×19 only? | A: 19×19 only / B: Include 13×13 with explicit board_size / C: Other | A — avoid board-size edge cases in initial calibration | | ❌ pending |
| Q3 | How to handle multi-instinct puzzles (e.g., a cut that's also pushlike)? | A: Primary instinct only / B: Ordered list of applicable instincts / C: Primary + secondary | B — ordered list, classifier accuracy measured against "matches any label" | | ❌ pending |
| Q4 | Target accuracy threshold for instinct classifier on golden set? | A: ≥70% (match existing AC-4 threshold) / B: ≥80% / C: Per-instinct thresholds | A — match the existing 70% threshold in `test_instinct_calibration.py` | | ❌ pending |
