# Implementation Plan

**Last Updated**: 2026-03-10

## Scope

### Part 1: Config-Driven YH1

- Add `_load_teaching_comments()` function in `hints.py` that reads `config/teaching-comments.json`
- `TECHNIQUE_HINTS` dict reads `hint_text` from config for YH1 technique text
- Reasoning text stays hardcoded (reasoning templates are production-specific, not in config)
- Fallback: if config missing, keep existing hardcoded values

### Part 2: Dynamic YH2 Reasoning

- `generate_reasoning_hint()` enhanced to append:
  - Solution depth context: "The solution requires N moves of reading." (depth ≥ 2)
  - Refutation count: "There are N tempting wrong moves." (refutations > 0)
  - Secondary tag: "Also consider: {secondary_tag}." (when 2+ tags, secondary ≠ primary)
- New helper: `_count_refutations(solution_tree)` — counts wrong first-move children
- New helper: `_get_secondary_tag(tags, primary_tag)` — returns next-priority tag

### Files Changed

| File | Change |
|---|---|
| `backend/puzzle_manager/core/enrichment/hints.py` | Config loading, dynamic reasoning |
| `backend/puzzle_manager/tests/unit/test_enrichment.py` | New tests for config + dynamic reasoning |
| `docs/concepts/hints.md` | Document dynamic YH2 |

### Test Plan

- Test config loading (happy path + missing config fallback)
- Test dynamic reasoning with depth context
- Test dynamic reasoning with refutation count
- Test dynamic reasoning with secondary tag
- Test all 28 tags still produce hints (regression)
- Test backward compatibility (old method names)

## Documentation Plan

| Action | File | Why |
|---|---|---|
| Update | `docs/concepts/hints.md` | Document dynamic YH2 reasoning format |

> **See also**:
> - [Charter](./00-charter.md)
> - [Options](./25-options.md)
