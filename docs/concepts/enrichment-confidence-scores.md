# Enrichment Confidence Scores

> **See also**:
>
> - [Concepts: Quality](./quality.md) — YQ property format and quality levels
> - [Concepts: Technique Detection](./technique-detection.md) — Detector architecture and thresholds
> - [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) — Design decisions
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — All thresholds

**Last Updated**: 2026-03-22

## Overview

The KataGo enrichment pipeline produces confidence scores at **6 different levels**. Each uses a different format suited to its domain. This document is the single reference for all confidence-bearing fields.

## Confidence Taxonomy

| # | Enrichment | Confidence Field | Type | Source Model |
|---|------------|-----------------|------|--------------|
| 1 | Move validation | `ACCEPTED` / `FLAGGED` / `REJECTED` | 3-state enum | `ValidationStatus` |
| 2 | Difficulty estimation | `"high"` / `"medium"` / `"low"` | String | `DifficultyEstimate.confidence` |
| 3 | Technique detection | `0.0`–`1.0` per detector | Float | `DetectionResult.confidence` |
| 4 | Instinct classification | `0.0`–`1.0` per instinct | Float | `InstinctResult.confidence` |
| 5 | Move quality (AI-Solve) | `TE` / `NEUTRAL` / `BM` / `BM_HO` | Enum (delta-based) | `MoveClassification.quality` |
| 6 | Quality score (qk) | `0`–`5` integer | Composite | `PuzzleDiagnostic.qk_score` |

---

## 1. Move Validation (`ValidationStatus`)

KataGo analysis is compared against the SGF's correct first move. The result is a three-state enum.

| Status | Meaning | Pipeline effect |
|--------|---------|-----------------|
| `ACCEPTED` | KataGo agrees the correct move is best | Full enrichment (Tier 3) |
| `FLAGGED` | Uncertain — KataGo disagrees or low confidence | Partial enrichment (Tier 2), no solution tree |
| `REJECTED` | KataGo strongly disagrees | Puzzle skipped or marked for review |

**Defined in:** `tools/puzzle-enrichment-lab/models/validation.py` (`ValidationStatus` enum)

**Downstream impact:** Validation status gates whether AI-Solve builds a solution tree. `FLAGGED` puzzles get policy-only difficulty estimation and techniques but no tree.

---

## 2. Difficulty Estimation Confidence

The difficulty estimator assigns a confidence string based on signal availability and agreement.

| Value | Meaning |
|-------|---------|
| `"high"` | Multiple KataGo signals agree (policy, visits, winrate) |
| `"medium"` | Partial signal agreement or moderate visit budget |
| `"low"` | Few signals available or conflicting indicators |

**Defined in:** `tools/puzzle-enrichment-lab/models/difficulty_estimate.py` (`DifficultyEstimate.confidence`)

**Also on:** `CorrectMoveResult.confidence` (same field, propagated from validation phase)

---

## 3. Technique Detection Confidence

Each of the 28 technique detectors independently outputs a float confidence score.

| Range | Interpretation |
|-------|----------------|
| 0.9–1.0 | Strong board-state evidence + KataGo confirmation |
| 0.7–0.9 | Board-state pattern detected |
| 0.5–0.7 | Analysis signals suggest technique |
| 0.3–0.5 | Heuristic only (joseki, fuseki) |
| 0.0–0.3 | Weak signal — not used for tagging |

**Defined in:** `tools/puzzle-enrichment-lab/models/detection.py` (`DetectionResult.confidence`)

Only detections with `detected=True` contribute tags to the final puzzle. The confidence value is used for ranking and diagnostic logging, not directly for tag inclusion.

---

## 4. Instinct Classification Confidence

Instinct classification identifies the tactical shape of the first move (push, hane, cut, descent, extend).

| Range | Interpretation |
|-------|----------------|
| 0.7–1.0 | High-confidence shape match |
| 0.4–0.7 | Moderate confidence |
| 0.0–0.4 | Low confidence — may not be used |

**Defined in:** `tools/puzzle-enrichment-lab/models/instinct_result.py` (`InstinctResult.confidence`)

**Instinct types:** `push`, `hane`, `cut`, `descent`, `extend` (5 of 8 frozenset from PLNech/gogogo, filtered per NG-8)

---

## 5. Move Quality (AI-Solve Classification)

During AI-Solve, each candidate move is classified by its winrate delta (Δwr) from the root position. This uses **delta-based thresholds only** — no absolute winrate gates (DD-6).

| Classification | Condition | Default Threshold | Meaning |
|---------------|-----------|-------------------|---------|
| `TE` (Tesuji) | Δwr < `t_good` | < 0.05 | Correct move — KataGo confirms |
| `NEUTRAL` | `t_good` ≤ Δwr < `t_bad` | 0.05–0.15 | Acceptable but not best |
| `BM` (Bad Move) | `t_bad` ≤ Δwr < `t_hotspot` | 0.15–0.30 | Wrong move — significant loss |
| `BM_HO` (Blunder Hotspot) | Δwr ≥ `t_hotspot` | ≥ 0.30 | Severe blunder |

**Defined in:** `tools/puzzle-enrichment-lab/models/solve_result.py` (`MoveQuality` enum, `MoveClassification` model)

**Thresholds configured in:** `tools/puzzle-enrichment-lab/config/ai_solve.py` (`AiSolveThresholds`)

**Ordering invariant:** `t_good < t_bad < t_hotspot` (enforced by model validator)

---

## 6. Quality Score (qk)

A composite integer score (0–5) summarizing the overall enrichment quality of a puzzle. Computed from refutation count, comment quality, and AI correctness level.

| Score | Name | Criteria |
|-------|------|----------|
| 5 | Premium | ≥3 refutations + teaching comments |
| 4 | High | ≥2 refutations + teaching comments |
| 3 | Standard | ≥1 refutation |
| 2 | Basic | Solution tree present, 0 refutations |
| 1 | Unverified | No solution tree |
| 0 | Not scored | Enrichment not run or failed |

**Defined in:** `tools/puzzle-enrichment-lab/models/diagnostic.py` (`PuzzleDiagnostic.qk_score`)

**Published as:** `q` field in `YQ[q:3;rc:2;hc:1;ac:1]` SGF property

---

## Three Confidence Formats

The pipeline uses three distinct confidence representations:

| Format | Used by | Rationale |
|--------|---------|-----------|
| **Categorical enum** | Move validation, Move quality | Discrete decision boundaries (accept/reject, correct/wrong) |
| **Ternary string** | Difficulty estimation | Coarse signal reliability indicator |
| **Float 0.0–1.0** | Technique detection, Instinct classification | Continuous per-detector/per-instinct scoring |

The quality score (qk) is a **composite** that synthesizes multiple signals into a single ordinal value for the published SGF.
