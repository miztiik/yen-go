# Charter: Config-Driven YH1 + Dynamic YH2 Reasoning

**Last Updated**: 2026-03-10

## Goals

1. **Config-driven YH1**: Migrate hardcoded `TECHNIQUE_HINTS` text to read from `config/teaching-comments.json` `hint_text` field — single source of truth with Japanese terms.
2. **Dynamic YH2**: Enhance `generate_reasoning_hint()` to incorporate solution depth, refutation count, and secondary tag context for richer pedagogical reasoning.

## Non-Goals

- Removing atari detection (kept with R5 gating)
- Porting KataGo-dependent detections from lab
- Changing hint emission thresholds or confidence model
- Modifying frontend hint display

## Constraints

- Pure heuristics only — no engine signals
- "Do No Harm" principle preserved
- `{!xy}` transform tokens preserved
- Backward-compatible — existing hint format unchanged
- All 28 tags must continue to produce hints

## Acceptance Criteria

- [ ] `TECHNIQUE_HINTS` reads `hint_text` from `teaching-comments.json`
- [ ] YH2 includes solution depth when depth ≥ 2
- [ ] YH2 includes refutation count when refutations > 0
- [ ] YH2 includes secondary tag context when multiple tags exist
- [ ] All existing tests pass
- [ ] New tests cover dynamic reasoning paths
- [ ] Documentation updated

> **See also**:
> - [Concepts: Hints](../../docs/concepts/hints.md)
> - [Architecture: Hint Architecture](../../docs/architecture/backend/hint-architecture.md)
