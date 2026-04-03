# Charter: PLNech/gogogo Tactical Pattern Research

**Last Updated**: 2026-03-15
**Initiative ID**: 20260315-research-gogogo-tactics-patterns
**Phase**: Research Review

---

## Goals

1. **Improve test robustness** of enrichment lab detectors by adopting testing methodology patterns from gogogo's test suite (negative tests, multi-orientation, boost stacking, neutral baselines)
2. **Enhance hint generation** by mapping Sensei's 8 Basic Instincts to pedagogical YH hints for intermediate-level puzzles
3. **Evaluate ladder detection** performance to determine if diagonal-scan pre-check adds measurable value

## Non-Goals (Explicitly Out of Scope)

| NG-ID | Finding | Reason |
|-------|---------|--------|
| NG-1 | F-4: Priority/urgency scoring on DetectionResult | Schema evolution — defer to enrichment lab v3 |
| NG-2 | F-6: Static life/death evaluation formula | Requires calibration study against KataGo baselines |
| NG-3 | F-7: Multi-tag evidence layering / feature planes | NN feature planes relevant |
| NG-4 | New tags in config/tags.json | Taxonomy expansion is a Level 5 change — not justified by this research |
| NG-5 | Alpha-beta capture search engine | KataGo already provides tactical analysis; parallel engine adds maintenance burden |

## Constraints

- **Clean-room adaptation only**: No code copied from PLNech/gogogo (no explicit license = All Rights Reserved)
- **Concept-level inspiration**: 8 Basic Instincts from Sensei's Library (public Go knowledge, not copyrightable game rules)
- **Algorithm adaptation**: Detection algorithms must be independently implemented; only the conceptual approach may be referenced
- **Precision-over-recall**: Any new detection logic must maintain the existing "misleading tag is worse than no tag" philosophy
- **Tag taxonomy frozen**: All findings must map to existing 28 canonical tags in config/tags.json v8.3

## Acceptance Criteria

| AC-ID | Criterion | Measurement | Target |
|-------|-----------|-------------|--------|
| AC-1 | Multi-orientation test coverage | Count of detectors with horizontal+vertical variant tests | ≥ 12 of 28 (up from 4) |
| AC-2 | Negative test completeness | Count of detectors with explicit non-detection tests | 28 of 28 (up from 27) |
| AC-3 | Instinct-to-hint mapping table | Documented 1:1 mapping verified by Go professional persona | 8 instincts mapped |
| AC-4 | Ladder benchmark baseline | Timing measurement of current LadderDetector on test corpus | Baseline established (pass/fail) |
| AC-5 | No regression in existing tests | All enrichment lab tests pass after changes | 100% pass |

## Backward Compatibility

- No breaking changes to existing DetectionResult interface
- No changes to config/tags.json
- No changes to YT property format
- Test additions are purely additive

## Clean-Room License Policy

1. **Sensei's Library content** (game patterns, tactics names, Japanese terminology): Public domain Go knowledge documented on senseis.xmp.net — freely usable
2. **Detection algorithms**: Independently implemented based on Go theory, NOT copied from gogogo source
3. **Test patterns**: Testing methodology (positive/negative/orientation) is non-copyrightable engineering practice
4. **No verbatim code**: Zero lines from gogogo may appear in Yen-Go repository
5. **Attribution**: Research brief references gogogo as inspiration source for documentation purposes only
