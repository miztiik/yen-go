# Options Assessment

**Last Updated**: 2026-03-10

## Options Evaluated

| Option | Title | Decision |
|---|---|---|
| A | Config-Only (migrate TECHNIQUE_HINTS to config) | Not selected — doesn't improve YH2 |
| B | Config + Dynamic YH2 Reasoning | **Selected** (GOV-OPTIONS-CONDITIONAL) |
| C | Full Lab Align (remove atari detection) | Not selected — loses legitimate atari hints |

## Selected: Option B

Migrate `TECHNIQUE_HINTS` `hint_text` to `teaching-comments.json` reads + enhance `generate_reasoning_hint()` with solution depth, refutation count, and secondary tag context.

**Must-hold constraints**: Config is single source of truth for YH1 text. Do No Harm principle. Atari detection kept with R5 gating. `{!xy}` tokens preserved. Backward-compatible.

See governance options review (2026-03-10) for full panel analysis.
