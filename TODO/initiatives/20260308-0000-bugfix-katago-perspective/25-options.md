# Options — KataGo Winrate Perspective Fix + Enrichment Reconciliation

Last Updated: 2026-03-08

## Context

The enrichment lab has a systemic winrate perspective mismatch (KataGo config `BLACK` vs code assuming `SIDETOMOVE`), zero decision logging in 4/8 analyzer modules, ko detection false positives, difficulty estimation collinearity, and accumulated dead code. See [15-research.md](./15-research.md) for approach comparison.

## Option Comparison

| Dimension                      | OPT-1: Config-First Fix                                                                                                                                                                                         | OPT-2: Boundary Normalization                                                                                                                             |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ID**                         | OPT-1                                                                                                                                                                                                           | OPT-2                                                                                                                                                     |
| **Title**                      | Fix config to SIDETOMOVE + targeted code fixes                                                                                                                                                                  | Normalize at parse boundary + targeted code fixes                                                                                                         |
| **Approach**                   | Change 1 config line (`reportAnalysisWinratesAs = SIDETOMOVE`). Fix `generate_refutations.py` L214 independently (broken under any mode). All other code becomes correct because it was written for SIDETOMOVE. | Add perspective normalization in `from_katago_json()` to convert BLACK→puzzle-player. Requires knowing puzzle_player at parse time. Keep config as BLACK. |
| **KISS**                       | ✅ **Best** — zero code changes for perspective itself                                                                                                                                                          | ❌ Adds coupling — parser needs puzzle_player context                                                                                                     |
| **DRY**                        | ✅ **Best** — no new normalization layer                                                                                                                                                                        | ❌ Adds transformation layer that duplicates `normalize_winrate()` responsibility                                                                         |
| **SOLID**                      | ✅ SRP maintained — parser stays a parser                                                                                                                                                                       | ❌ SRP violation — parser takes on perspective responsibility                                                                                             |
| **Code changes**               | 1 config line + 1 bug fix (L214)                                                                                                                                                                                | ~5 files (parser + all callers need updating)                                                                                                             |
| **Test changes**               | Fix MockConfirmationEngine + add White-puzzle tests                                                                                                                                                             | Same + add boundary tests                                                                                                                                 |
| **Risk**                       | Low — code already works for SIDETOMOVE                                                                                                                                                                         | Medium — new transformation could introduce bugs                                                                                                          |
| **Rollback**                   | Trivial — revert 1 config line                                                                                                                                                                                  | Complex — revert normalization layer across files                                                                                                         |
| **SIDETOMOVE doc'd by KataGo** | Yes — P2.4 in consolidated review recommended it                                                                                                                                                                | N/A                                                                                                                                                       |
| **Blast radius**               | Minimal                                                                                                                                                                                                         | Moderate                                                                                                                                                  |

### Shared work (both options)

Both options require the same work for the non-perspective scope items:

- Comprehensive decision logging across 8 modules
- Ko detection capture verification fix
- Difficulty collinearity weight rebalancing
- Dead code removal (`difficulty_result.py`, `ai_solve.enabled`, abandoned initiative)
- Log naming fix (run_id for `enrich` CLI, conftest alignment)
- White-to-play test fixtures
- Re-run session evidence puzzle

## Recommendation

**OPT-1** is unambiguously superior on every KISS/DRY/SOLID dimension. The code was written for SIDETOMOVE. The config is the sole error. P2.4 from the consolidated review already recommended this exact change but it was never implemented.

OPT-2 would add complexity to solve a problem that OPT-1 solves with a single config line change.

> **See also**:
>
> - [Charter](./00-charter.md) — Goals G1-G11
> - [Research](./15-research.md) — KataGo perspective documentation, flow traces
> - [Clarifications](./10-clarifications.md) — User decisions Q3:A confirmed
