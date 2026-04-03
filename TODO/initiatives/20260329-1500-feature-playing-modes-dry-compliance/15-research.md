# Research — Playing Modes DRY Compliance

**Initiative**: `20260329-1500-feature-playing-modes-dry-compliance`
**Last Updated**: 2026-03-29

See full research at: `TODO/initiatives/20260329-research-playing-mode-dry-audit/15-research.md`

## Key Findings Summary

1. **8 playing modes** found; 6 compliant, 2 non-compliant (Rush, Random)
2. **Daily Challenge is fully compliant** — thin wrapper around PuzzleSetPlayer
3. **Rush** hardcodes `max-w-[600px]`, uses InlineSolver instead of SolverView
4. **Random** uses InlineSolver via App.tsx render-prop injection
5. **5 dead code files** confirmed unreferenced
6. **InlineSolver duplicates ~60%** of SolverView's goban setup logic
7. **chess.com/Lichess** validate "shared board + mode overlay" pattern

## Planning Confidence

- Pre-research: 68
- Post-research: 88
- Post-options: 92
- Risk level: medium → triggered mandatory research

## Research Invocation Rationale

Score dropped below 70 due to:
- `-20`: architecture seams unclear (how PSP handles streaming)
- `-15`: external precedent needed (chess.com/Lichess patterns)
- `-10`: test strategy unclear (22 test files affected)
