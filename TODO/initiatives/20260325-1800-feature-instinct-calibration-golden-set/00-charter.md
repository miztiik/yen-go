# Charter — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

## Summary

Build a multi-dimensional calibration golden set (~120 puzzles) with human-verified labels for instinct, technique, and objective. Create two permanent tools for puzzle discovery and curation. Run calibration to validate the instinct classifier (AC-4 gate: ≥70% accuracy) and establish ground truth for the entire enrichment pipeline.

## Goals

| ID | Goal | Description |
|----|------|-------------|
| G-1 | Instinct calibration set | ~120 labeled puzzles in new `tests/fixtures/instinct-calibration/` directory with instinct, technique tag, and objective labels |
| G-2 | Puzzle search tool | Permanent tool in `tools/` to search `external-sources/` by technique, objective, tag, or instinct text in SGF comments/filenames |
| G-3 | Puzzle copy-and-rename tool | Permanent tool in `tools/` to copy SGFs from external-sources to fixture directories with standardized naming |
| G-4 | Labels schema | `labels.json` with per-puzzle: `instinct_primary`, `instinct_labels[]`, `technique_tag`, `objective`, `human_difficulty`, provenance |
| G-5 | Instinct labeling | Expert-labeled instinct types (cut/push/hane/descent/extend/null) for all ~120 puzzles using ASCII board rendering |
| G-6 | Calibration validation | Implement `test_instinct_accuracy_threshold` in test_instinct_calibration.py against the new golden set |
| G-7 | Tobi verification | Verify all 10 Sakata Tobi files — axis-aligned = extend, knight's-move = null |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG-1 | Enable instinct flag | AC-4 gate flip (`enabled=True`) is a separate 1-line change after calibration passes |
| NG-2 | Full technique tag calibration | We label top technique tag per puzzle, but full 28-tag calibration is a follow-up initiative |
| NG-3 | Modify existing golden-calibration/ | Q9:A — existing set stays untouched |
| NG-4 | Add new instinct types | Placement, throw-in, attachment are identified gaps but out of scope |
| NG-5 | 9x9 board size support | Calibrate on 19x19 only. 9x9 is follow-up |

## Constraints

| ID | Constraint |
|----|-----------|
| C-1 | **Tools isolation**: Tools in `tools/` must NOT import from `backend/` (architecture rule) |
| C-2 | **No external-sources modification**: Only read from `external-sources/`. Never write to it |
| C-3 | **Naming convention**: `{instinct}_{level}_{serial:03d}.sgf` per Q5:A |
| C-4 | **Minimum counts**: ≥10 puzzles per instinct category (6 categories × ≥10 = ≥60 floor) |
| C-5 | **Multi-dimensional labels**: Each puzzle labeled with instinct + top technique tag + objective (Q11:C) |
| C-6 | **Expert labeling via ASCII render**: Use `render_sgf_ascii()` for domain experts to read positions |
| C-7 | **19x19 only**: All calibration puzzles must be 19×19 board size |

## Acceptance Criteria

| ID | Criterion | Threshold |
|----|-----------|-----------|
| AC-1 | Macro instinct accuracy | ≥70% (classifier primary ∈ human instinct_labels) |
| AC-2 | Per-instinct accuracy | Each of 5 instinct types individually ≥60% |
| AC-3 | HIGH-tier precision | ≥85% of HIGH-tier classifier outputs are correct |
| AC-4 | Null false-positive rate | 0% — if human labels `instinct_labels: []`, classifier must return empty |
| AC-5 | Minimum puzzle count | ≥120 puzzles with complete labels in instinct-calibration/ |
| AC-6 | Technique coverage | ≥5 puzzles for each of the top 10 technique tags |
| AC-7 | Search tool functional | Can search by text across external-sources/ and return matching SGF paths |
| AC-8 | Copy tool functional | Can copy + rename SGFs to target fixture directory with standardized names |

## Source Material

| Source | Path | Strength | Primary Use |
|--------|------|----------|-------------|
| Sakata Eio Tesuji | `external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/` | Filename-level technique labels (kiri, Hane, Sagari, Tobi, Kosumi, Tsuke, oki, Kake, Warikomi) | cut, hane, descent, extend, null — ~107 puzzles |
| Lee Changho Tesuji | `external-sources/kisvadim-goproblems/LEE CHANGHO TESUJI/` | Chapter-level technique organization (16 chapters: Fighting, Snapback, Splitting, Capturing Race, etc.) | push, capture-race, liberty-shortage, escape |
| Cho Chikun L&D | `external-sources/kisvadim-goproblems/CHO CHIKUN Encyclopedia Life And Death - {Elementary,Intermediate,Advanced}/` | Professional difficulty grading, rich solution trees | Difficulty anchoring, life-and-death techniques |
| goproblems | `external-sources/goproblems/sgf/` | Difficulty-tiered (KYU/DAN/HIGH DAN/PRO) | Supplemental diversity |

## Inventory: Sakata Eio Tesuji Files

| Technique | Files | Instinct Mapping | Count |
|-----------|-------|-----------------|-------|
| kiri-s-* | kiri-s-01 → kiri-s-12 | **cut** | 12 |
| Hane-s-* | Hane-s-01 → Hane-s-10 (+01A,04A,06A) | **hane** | 13 |
| Sagari-s-* | Sagari-s-01 → Sagari-s-12 | **descent** | 12 |
| Tobi-s-* | Tobi-s-01 → Tobi-s-10 | **extend** (verify axis-aligned) | 10 |
| Kosumi-s-* | Kosumi-s-01 → Kosumi-s-18 (+01a) | **null** | 19 |
| Tsuke-s-* | Tsuke-s-01 → Tsuke-s-17 | **null** | 17 |
| oki-s-* | oki-s-01 → oki-s-12 | **null** | 12 |
| Kake-s-* | Kake-s-01 → Kake-s-08 | **null** | 8 |
| Warikomi-s-* | Warikomi-s-01 → Warikomi-s-07 | **null** (or cut — verify) | 7 |

> **See also**:
> - [10-clarifications.md](./10-clarifications.md) — All resolved clarification questions
> - [70-governance-decisions.md](./70-governance-decisions.md) — Governance review decisions
