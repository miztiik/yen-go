# Research — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Research Reference

Full external-sources inventory research was conducted by Feature-Researcher and is stored at:

**[15-research.md](../20260322-research-external-sources-fixture-sourcing/15-research.md)**

## Key Findings Summary

| finding_id | Finding | Impact |
|------------|---------|--------|
| RF-1 | 16 external collections inventoried; 4 graded A/A+ | Sourcing pool is large enough for all 28 technique tags |
| RF-2 | goproblems (51K) + ogs (52K) have pre-applied YT[tag-slug] tags | Grep-based sourcing is trivial for 6/8 technique gaps |
| RF-3 | goproblems_difficulty_based (9K+) has GE[technique]/DI[rank] metadata | Multi-difficulty stratification available for extended-benchmark |
| RF-4 | kisvadim Cho Chikun L&D (2,553 puzzles) — domain-expert curated | Best source for ko/carpenter's-square/living fixtures |
| RF-5 | tasuki/sanderland/eidogo lack solution trees — rejected for calibration | Reduces candidate pool by ~3 collections |
| RF-6 | goproblems flat collection already YV[10] enriched — bias risk | Cross-reference with goproblems_difficulty_based for stratification |

## Sourcing Strategy (Per-Technique)

| technique | primary_source | secondary_source | effort |
|-----------|---------------|-------------------|--------|
| capture-race | goproblems YT[capture-race] | ogs YT[capture-race] | Low |
| snapback | goproblems YT[snapback] | goproblems_difficulty_based tesuji/ | Low |
| throw-in | goproblems YT[throw-in] | kisvadim Tesuji Great Dict | Low-Med |
| net | goproblems YT[net] | goproblems_difficulty_based tesuji/ | Low |
| ko (all variants) | goproblems YT[ko] | kisvadim Cho Chikun L&D | Low-Med |
| living/two-eyes | goproblems YT[living] | goproblems_difficulty_based life_and_death/ | Low |
| squeeze/shibori | goproblems YT[liberty-shortage] | goproblems_difficulty_based tesuji/ | Medium |
| carpenter's-square | goproblems YT[dead-shapes] | kisvadim Cho Chikun L&D | Medium |

## Confidence Update

| Metric | Value |
|--------|-------|
| planning_confidence_score | 75 |
| risk_level | medium |
| research_invoked | true |
| post_research_confidence | 75 |
| open_risk | Test architecture design (resolved by options phase) |
