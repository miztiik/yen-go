# Plan — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19
**Selected Option**: OPT-1 (Single bundled fix, all 5 RCs)

## Implementation Plan

### Phase 1: Code fixes (RC-1 through RC-5)

**RC-1**: Remove `if text.startswith("Close"): marked = text` special-casing in `sgf_enricher.py`. All wrong-move comments now get "Wrong." prefix uniformly.

**RC-2**: Add `TIER3_TACTICAL_SUPPRESS_TAGS` set to `hint_generator.py` containing tags where first move IS the answer (net, ladder, snapback, throw-in, oiotoshi). Suppress Tier 3 coordinate for these tags.

**RC-3**: Add `"net": 1` to `TAG_PRIORITY` in `technique_classifier.py`. Net gets same priority as capture-race; when both fire, net is more specific so list it first.

**RC-4**: Change `if distance >= threshold` to `if distance > threshold` in `sgf_enricher.py`. Distance exactly 3 no longer overwrites.

**RC-5**: In `sgf_enricher.py`, before building refutation branches, check if ALL refutations have delta below `almost_correct_threshold`. If so, skip AI refutation branch generation to preserve curated tree.

### Phase 2: Tests

Add targeted tests for each RC. Update existing tests whose expectations change.

### Phase 3: Documentation

Update `tools/puzzle-enrichment-lab/AGENTS.md` with new behavior.

## Documentation Plan

| doc_id | file | action | why_updated |
|--------|------|--------|-------------|
| D1 | tools/puzzle-enrichment-lab/AGENTS.md | Update | Document new TIER3_TACTICAL_SUPPRESS_TAGS, net priority, level threshold change, all-almost-correct guard |

## Backward Compatibility

Required: false. Changes affect future enrichment output only. No existing SGFs modified.
