# Puzzle Quality Strategy

**Created:** 2026-02-25  
**Status:** Planning complete — ready for implementation  
**Chosen Strategy:** D (Hybrid) — Shift-left dedup + Content-type classification + Quality-tier UX

---

## Strategy Decision

Five strategies were evaluated (A through E). **Strategy D (Hybrid)** was selected based on multi-persona consultation (Cho Chikun, Lee Chang-ho, Takemiya Masaki perspectives) and staff-engineer architectural review.

See [001-research-quality-landscape.md](001-research-quality-landscape.md) § 6-7 for the full comparison matrix and recommendation rationale.

## Documents

|  #  | File                                                                           | Purpose                                                                                       | Status   |
| :-: | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | -------- |
| 001 | [001-research-quality-landscape.md](001-research-quality-landscape.md)         | Data sampling (~194K puzzles), pipeline audit, professional consultation, strategy comparison | Complete |
| 002 | [002-implementation-plan-strategy-d.md](002-implementation-plan-strategy-d.md) | 3-phase implementation plan, architectural decisions, schema changes, deferred items          | Complete |

## Scope Summary

### In Plan (3 phases, ~7.5 weeks)

| Phase | What                                                                                                                               |  Duration  |
| :---: | ---------------------------------------------------------------------------------------------------------------------------------- | :--------: |
|   1   | Position fingerprinting, cross-source dedup, trivial capture detection, avg_refutation_depth metric, config-driven quality scoring | ~2.5 weeks |
|   2   | Content-type classification (curated/practice/training), shard routing, manifest expansion                                         |  ~3 weeks  |
|   3   | Frontend quality tabs (Curated/Practice/All), quality stars display                                                                |  ~2 weeks  |

### Deferred (4 items, tracked in plan § Deferred Items)

| ID  | Item                                                    |   Effort   |      Blocked By      |
| :-: | ------------------------------------------------------- | :--------: | :------------------: |
| D1  | Quality-weighted daily challenge selection              |  ~3 days   |       Phase 2        |
| D2  | Difficulty classifier improvement (replace placeholder) | ~2-3 weeks |         None         |
| D3  | Dedup metadata merging (multi-source merge)             | ~1-2 weeks | Phase 1 + usage data |
| D4  | Training Lab as 4th dedicated tab                       |  ~2 days   |       Phase 3        |

### Promoted into Scope (from originally deferred)

These items were initially deferred but added after feasibility analysis showed low effort and high value:

- **avg_refutation_depth** → Phase 1 (§ 1.5, ~2 hours, extends YX with `a` sub-field)
- **Config-driven quality scoring** → Phase 1 (§ 1.6, ~3 hours, makes `quality.py` read from `puzzle-quality.json`)

## Key Decisions Log

| Decision            | Choice                                              |  Where Documented   |
| ------------------- | --------------------------------------------------- | :-----------------: |
| Strategy            | D (Hybrid)                                          |       001 § 7       |
| Dedup normalization | Corner-normalize to TL quadrant                     | 002 § Key Decisions |
| Fingerprint storage | YM JSON only (no shard field)                       | 002 § Key Decisions |
| Content-type values | 3 types: curated(1), practice(2), training(3)       | 002 § Key Decisions |
| Frontend tabs       | 3 tabs: Curated / Practice / All (default=Practice) | 002 § Key Decisions |
| Reprocessing        | Big-bang (no migration)                             | 002 § Key Decisions |
