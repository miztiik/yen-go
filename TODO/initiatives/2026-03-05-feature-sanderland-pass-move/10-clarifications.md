# Clarifications: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Last Updated**: 2026-03-05

## Mandatory Question

**Q: Is backward compatibility required, and should old code be removed?**  
**A**: No backward compatibility required. Clean re-run is acceptable. No old code exists to remove — this is a new detection path.

## Feature-Specific Questions

| #   | Question                    | Answer                                                         |
| --- | --------------------------- | -------------------------------------------------------------- |
| 1   | Pass encoding format?       | SGF standard empty string: `B[]` / `W[]`                       |
| 2   | Pass-only puzzles?          | Import normally with pass move. Not filtered.                  |
| 3   | Comment text?               | "White passes" / "Black passes" (no "here" suffix)             |
| 4   | Mid-sequence passes?        | Keep full solution, convert passes inline                      |
| 5   | Which coordinates are pass? | `"zz"` from Sanderland data (also empty string for robustness) |

## Data Evidence

- Grep across all Sanderland JSON files found exactly **1 occurrence** of `"zz"` in `Suteishi02_17-18.json`
- No occurrences of `"tt"` as pass in Sanderland JSON data
- The sole affected SOL entry: `[["W", "zz", "", ""]]`
