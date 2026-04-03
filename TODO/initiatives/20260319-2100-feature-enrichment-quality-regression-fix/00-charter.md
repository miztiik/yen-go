# Charter — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Type**: Feature (quality fix bundle)
**Date**: 2026-03-19
**Level**: Level 3 (Multiple Files: 5+ files, enrichment pipeline + config + tests)

## Objective

Fix 5 enrichment output quality regressions identified by Governance Panel review of puzzle `14_net` (goproblems #37934, net-problems collection). The regressions affect correctness markers, hint spoilers, technique classification, level calibration, and refutation pedagogy.

## Success Criteria

1. **RC-1**: All AI-generated refutation branches have canonical "Wrong." prefix recognizable by `infer_correctness_from_comment()`
2. **RC-2**: Tier 3 coordinate hints suppressed for tactical tags (net, ladder, snapback, throw-in, oiotoshi) where first move IS the answer
3. **RC-3**: `net` tag added to `TAG_PRIORITY` with priority 1; net takes precedence over capture-race when both detect
4. **RC-4**: Level mismatch threshold uses `>` instead of `>=` (distance 3 no longer triggers overwrite)
5. **RC-5**: When 100% of refutations are "almost_correct", AI refutation branches are skipped and curated tree preserved
6. All existing tests pass; new tests cover each RC

## Scope

### In Scope
- `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` (RC-1, RC-4, RC-5)
- `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` (RC-2)
- `tools/puzzle-enrichment-lab/analyzers/technique_classifier.py` (RC-3)
- `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` (RC-5)
- Tests for all 5 RCs
- `tools/puzzle-enrichment-lab/AGENTS.md` update

### Out of Scope
- Retroactive re-enrichment of existing SGFs
- Frontend changes
- Config file changes (teaching-comments.json, katago-enrichment.json)
- Technique detector code changes (net_detector.py, capture_race_detector.py)

## Constraints
- Future-only (no retroactive re-enrichment)
- No new dependencies
- Backward compatible with existing enriched SGFs
