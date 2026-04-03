# Options: KA Train Reuse for Enrichment Lab

**Last Updated:** 2026-03-08

## Option Comparison

| option_id | title | approach_summary | benefits | drawbacks | risks | complexity | test_impact | rollback_implications | architecture_and_policy_compliance | recommendation_candidate |
|---|---|---|---|---|---|---|---|---|---|---|
| OPT-1 | Targeted Algorithm Port (Frame+Utilities) | Port only KA Train pure algorithmic units with clear 1:1 value (`tsumego_frame` parity incl. flip+ko-threat, `var_to_grid`, optional interpolation helpers). Keep current engine/rules/SGF architecture. | Fastest value with lowest blast radius; no Kivy coupling; directly addresses confirmed gaps; aligns with replacement-first and no-compat policy. | Does not unify full search/rules stack; some custom lab logic remains. | Coordinate-axis mapping mistakes during frame port; small risk of behavior drift on tiny boards. | Low-Medium | Add focused unit/regression tests for frame parity and coordinate transforms. | Simple rollback by reverting limited files. | Fully compliant: stays inside `tools/`, avoids UI dependencies, preserves delta explicitly. | Yes |
| OPT-2 | Broad Selective Vendoring | Vendor larger KA Train non-UI chunks: expanded SGF parser capabilities (NGF/GIB), more utils, and deeper AI helper functions in one initiative. | Maximum immediate reuse; reduces custom code footprint more aggressively. | Higher integration cost; bigger behavior surface; may import concepts irrelevant to tsumego-only workflows. | Hidden coupling to whole-game assumptions; higher regression risk in SGF and solve path. | Medium-High | Requires broad test expansion across parsers, solver, and enrichment pipeline. | Harder rollback due multi-module changes. | Conditional compliance: still non-UI, but higher risk of architectural overreach. | No |
| OPT-3 | De-Kivy Core Extraction | Attempt to extract KA Train engine/game/ai modules by removing Kivy coupling and creating adapters for enrichment-lab. | Theoretically maximizes upstream alignment and future shared evolution. | Large refactor, likely brittle, and drags whole-game abstractions into tsumego tooling. | High risk, high effort, uncertain benefit; violates KISS/YAGNI for current goals. | High | Extensive integration and performance/regression coverage required. | Difficult rollback due structural change set. | Weak compliance with simplicity constraints; high chance of dependency creep. | No |

## Evaluation Criteria

| criteria_id | criterion | weighting | OPT-1 | OPT-2 | OPT-3 |
|---|---|---:|---:|---:|---:|
| E1 | 1:1 functional match realization | 30 | 9 | 7 | 5 |
| E2 | Delta preservation safety | 25 | 9 | 6 | 4 |
| E3 | Architectural compliance | 20 | 9 | 7 | 4 |
| E4 | Delivery/rollback risk | 15 | 8 | 5 | 2 |
| E5 | Long-term maintainability | 10 | 8 | 7 | 3 |
| E-TOTAL | Weighted score (/10) | 100 | 8.7 | 6.5 | 3.9 |

## Recommendation (Pre-Election)

OPT-1 is the leading candidate because it gives direct, evidence-backed reuse without importing whole-game complexity, and it cleanly implements your rule: replace exact matches, preserve required deltas, then remove old code.
