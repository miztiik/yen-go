# Puzzle Quality Scorer — Research & Implementation

**Created:** 2026-02-27  
**Status:** Research complete — ready for implementation  
**Depends on:** [puzzle-quality-strategy/002-implementation-plan-strategy-d.md](../puzzle-quality-strategy/002-implementation-plan-strategy-d.md)

---

## Purpose

Implement a **Puzzle Quality Scorer** that enriches yen-go's pipeline with
tactical analysis capabilities extracted from two open-source Go repositories.

This extends Strategy D (quality control) with **positional analysis** — the
deferred "Difficulty Classifier Improvement" item from the Strategy D plan.

## Source Repositories

| Repo                                                                          | License | Key Extractions                                                                                                           |
| ----------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| [PLNech/gogogo](https://github.com/PLNech/gogogo)                             | GPL-3.0 | TacticalAnalyzer (ladder, snapback, capture, life/death), 8 Basic Instincts                                               |
| [zhoumeng-creater/gogamev4.0](https://github.com/zhoumeng-creater/gogamev4.0) | MIT     | DeadStoneAnalyzer (eye counting, escape, seki), Territory (influence maps), MistakeDetector (winrate-loss classification) |

> **License note:** GoGoGo is GPL-3.0. We extract _algorithms and patterns_
> (not code verbatim) and reimplement using sgfmill. gogamev4.0 is MIT.

## Directory Structure

```
TODO/puzzle-quality-scorer/
├── README.md                    ← This file
├── implementation-plan.md       ← Combined implementation plan
└── reference/
    ├── gogogo-tactics.md        ← Distilled algorithms from GoGoGo TacticalAnalyzer
    ├── gogogo-instincts.md      ← Distilled algorithms from GoGoGo InstinctAnalyzer
    ├── gogamev4-territory.md    ← Distilled algorithms from gogamev4.0 Territory/DeadStone
    └── gogamev4-analysis.md     ← Distilled algorithms from gogamev4.0 Analysis/Mistake
```

## Relationship to Strategy D

Strategy D (002 plan) covers:

- Position fingerprinting & dedup (Phase 1)
- Content-type classification (Phase 2)
- Frontend quality tabs (Phase 3)

This plan covers the **deferred D2 item** ("Difficulty Classifier Improvement")
plus new capabilities:

- Tactical pattern detection → auto-tag YT
- Life/death verification → validate puzzle objectives
- Group weakness analysis → difficulty scoring input
- Instinct-based hint generation → auto-generate YH

Both plans share the same `core/quality.py` scoring framework.

## See Also

- [../puzzle-quality-strategy/001-research-quality-landscape.md](../puzzle-quality-strategy/001-research-quality-landscape.md) — Data landscape
- [../puzzle-quality-strategy/002-implementation-plan-strategy-d.md](../puzzle-quality-strategy/002-implementation-plan-strategy-d.md) — Strategy D plan
