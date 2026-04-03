# Technique Detection Architecture

**Last Updated**: 2026-03-14

## Overview

The enrichment pipeline classifies each puzzle with technique tags using a hybrid approach: board-state pattern detectors combined with KataGo analysis confirmation.

## Architecture

```
AnalyzeStage → TechniqueStage → Detector Registry → Individual Detectors
                                                   ↓
                                          DetectionResult per detector
                                                   ↓
                                          Merged tag list (sorted, deduped)
```

## Detection Flow

1. **TechniqueStage** calls `run_detectors()` via `get_all_detectors()`
2. All 28 `TechniqueDetector` instances receive typed `Position`, `AnalysisResponse`, and `SolutionNode` objects
3. Each detector independently analyzes the puzzle
4. Positive results (detected=True) are collected
5. Tag slugs are deduplicated, sorted by TAG_PRIORITY, and set on the result

## Confidence Levels

| Range | Meaning |
|-------|---------|
| 0.9-1.0 | Strong board-state evidence + KataGo confirmation |
| 0.7-0.9 | Board-state pattern detected |
| 0.5-0.7 | Analysis signals suggest technique |
| 0.3-0.5 | Heuristic only (joseki, fuseki) |
| 0.0-0.3 | Weak signal, not used for tagging |

## Notable Detector Behaviors

- **Ladder detector**: Simulates stone captures during liberty-chase via `_remove_captured_stones()`, preventing false negatives from phantom liberties.
- **Snapback detector**: Uses PV (principal variation) recapture pattern verification. PV-confirmed snapbacks receive confidence 0.85+; unconfirmed heuristic-only detections receive 0.45. Requires `min_pv_length=3`.

## Design Decisions

1. **One detector per tag** — SRP, independently testable
2. **No cross-detector dependencies** — prevents cascade failures
3. **Config-driven thresholds** — all parameters in `katago-enrichment.json`
4. **Graceful degradation** — DEGRADE error policy, missing data → skip (not fail)

> **See also**:
>
> - [Concepts: Enrichment Confidence Scores](./enrichment-confidence-scores.md) — All 6 confidence levels
> - [Concepts: Detector Interface](detector-interface.md) — Protocol and how to add detectors
> - [Concepts: Entropy ROI](entropy-roi.md) — Board region analysis
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — All thresholds
