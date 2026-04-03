# Clarifications — Externalize TECHNIQUE_REGISTRY

Last Updated: 2026-03-22

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 75 |
| Risk Level | low |
| Research Invoked | No |
| Rationale | Score >= 70, risk low, clear ownership, no external patterns needed |

## Clarification Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required for TECHNIQUE_REGISTRY? (Does anything outside test_technique_calibration.py import it?) | A: Yes, keep importable / B: No, can fully replace / C: Unsure, need to check | B: No backward compat needed | Q1:B — Can fully replace. Only consumed inside this one test file. | ✅ resolved |
| Q2 | Should old code be removed? (Delete the hardcoded dict after externalization, or keep both?) | A: Remove hardcoded dict entirely / B: Keep as fallback / C: Keep commented out | A: Remove entirely | Q2:A — Remove entirely. Clean separation. | ✅ resolved |
| Q3 | Where should the external data file live? | A: `tests/fixtures/technique-benchmark-reference.json` / B: `tests/calibration-data/` / C: `tests/technique-registry.json` / D: Other | A: Alongside fixtures | Q3:A — `tests/fixtures/technique-benchmark-reference.json` | ✅ resolved |
| Q4 | What data format? | A: JSON / B: TOML / C: Python data module / D: Other | A or C | Q4:A — JSON | ✅ resolved |
| Q5 | Should a regeneration script be included in this refactor, or deferred? | A: Include regen script now / B: Defer to follow-up / C: Manual regen is fine | B: Defer (YAGNI) | Q5:A — Include regen script now (user override of recommendation) | ✅ resolved |
| Q6 | Should computed fields (like `correct_move_gtp`) be stored in the data file or derived at test time? | A: Store all fields / B: Derive at test time | A: Store all fields | Q6:A — Store all fields (explicit ground truth) | ✅ resolved |
| Q7 | Should the JSON include versioning metadata? | A: Yes, metadata header / B: No, minimal / C: Just version | A: Yes, metadata header | Q7:A — Version + last_updated + notes | ✅ resolved |

## Dependencies on Clarification

- Q1 + Q2 → Determines whether backward-compat shim is needed (affects task scope)
- Q3 + Q4 → Determines file location and format (core architectural decision for options)
- Q5 → Determines whether regen script is in-scope or deferred
- Q6 → Determines data file content scope
- Q7 → Determines metadata header structure
