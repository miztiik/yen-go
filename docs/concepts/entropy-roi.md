# Entropy-Based Region of Interest (ROI) Detection

**Last Updated**: 2026-03-14

## Overview

Entropy ROI identifies the contested region of a tsumego puzzle by computing per-intersection entropy from KataGo ownership values. High-entropy intersections indicate positions where ownership is uncertain — where the puzzle's action is.

## Formula

$$H(p) = -p \cdot \log_2(p) - (1-p) \cdot \log_2(1-p)$$

where $p = \frac{\text{ownership} + 1}{2}$ maps KataGo ownership $[-1, 1]$ to $[0, 1]$.

## How It Works

1. KataGo returns per-intersection ownership values after analysis
2. Each value is mapped to a probability and its binary entropy computed
3. Intersections with entropy above a threshold (default 0.5) are "contested"
4. The bounding box of contested intersections defines the ROI
5. ROI coordinates are used as `allowMoves` for focused queries

## Fallback Chain

1. **Frame + ROI** — primary: tsumego frame applied, ROI restricts queries
2. **ROI only** — if frame fails, use ROI from ownership analysis
3. **Bounding box** — if no ownership data, use `Position.get_puzzle_region_moves()`

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `frame.entropy_quality_check.enabled` | `true` | Enable ownership-based frame validation |
| `frame.entropy_quality_check.variance_threshold` | `0.15` | Max acceptable ownership variance |

> **See also**:
>
> - [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — Pipeline stage changes
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — Full config reference
