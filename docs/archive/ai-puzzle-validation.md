> ⚠️ **ARCHIVED** — This document describes the KataGo/Smargo puzzle validation approach
> which was abandoned in January 2026. Curated sources are pre-validated and don't need
> runtime AI validation. Kept for historical reference only.

---

# AI-Based Puzzle Validation (Abandoned)

## What Was Tried

Spec 005 proposed giving the Smargo solver "teeth" — instead of just logging validation results, it would reject puzzles with incorrect or incomplete solution trees. KataGo was planned as a higher-accuracy alternative for local development validation of unknown sources.

The approach:

1. Run each puzzle's solution tree through KataGo or Smargo
2. Compare the solver's moves against the embedded solution
3. Flag puzzles where solver disagrees with the stated correct answer
4. Optionally enhance solution trees with solver-discovered alternative moves

## Why It Was Abandoned

Yen-Go's puzzle sources are **curated collections** from professional Go players and established repositories:

| Source                    | Why Trusted                                                |
| ------------------------- | ---------------------------------------------------------- |
| Cho Chikun collections    | Published by 9-dan professional; verified by Go publishers |
| Gokyo Shumyo              | Classical tsumego corpus, centuries of validation          |
| OGS puzzle collections    | Community-curated with rating-based difficulty             |
| Sanderland tsumego-solver | Algorithmically generated with provable solutions          |

For these sources, AI validation adds cost (KataGo setup, GPU requirements, runtime overhead) without meaningful quality improvement. The puzzles are correct by provenance.

## What Replaced It

- **Source quality rating** (`config/source-quality.json`) — Each source has a 1–5 quality rating
- **Centralized `PuzzleValidator`** — Validates structural properties (board size, solution tree depth, stone count) without AI
- **`--min-source-quality` CLI flag** — Filter puzzles by source quality at ingest time

## See Also

- [Puzzle Sources Reference](../reference/puzzle-sources.md) — Current source catalog
- [KataGo Integration (archived)](./katago-integration.md) — Related KataGo design that was also removed
