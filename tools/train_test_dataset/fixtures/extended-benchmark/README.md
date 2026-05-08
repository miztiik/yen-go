# Extended Benchmark Fixtures

Difficulty-stratified puzzle fixtures for technique calibration benchmarking.

## Purpose

These fixtures provide ≥3 difficulty variants per top-5 technique for measuring:
- Difficulty estimation accuracy across the spectrum
- Technique detection consistency at different complexity levels
- Refutation quality variation by puzzle difficulty

## Selection Criteria

1. **Real puzzles** — all sourced from `goproblems` external collection
2. **Pre-tagged** — each has pipeline-assigned YG (difficulty) and YT (technique) properties
3. **Solution trees** — each has at least one correct (RIGHT) and one wrong branch
4. **Difficulty spread** — elementary / intermediate / advanced where available

## Naming Convention

`{technique}_{level}_{source_id}.sgf`

- `technique`: tag slug (e.g., `life-and-death`, `ko`, `nakade`)
- `level`: difficulty tier (`elem`, `int`, `adv`)
- `source_id`: goproblems puzzle ID

## Inventory

| Technique | Elementary | Intermediate | Advanced | Notes |
|-----------|-----------|-------------|----------|-------|
| life-and-death | 1001 | 102 | 1042 | Core objective |
| ko | 1028 | 1022 | 1118 | Ko fight variants |
| snapback | 1134 | 5 | — | No advanced found |
| ladder | 189 | 220 | — | No advanced found |
| nakade | 4774 | 588 | 6421 | Full spread |

## Provenance

All fixtures sourced from `external-sources/goproblems/sgf/` (batch-001 through batch-006).
Pipeline-enriched metadata (YV, YG, YT, YQ) preserved as-is from source.

Last Updated: 2026-03-22
