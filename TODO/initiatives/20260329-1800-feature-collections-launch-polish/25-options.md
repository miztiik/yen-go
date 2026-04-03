# Options: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Context

Pre-pipeline utility to embed `YL[slug:chapter/position]` into SGF files before ingest. Frontend browse improvements. No pipeline changes.

## Options

### OPT-1: Single-Strategy Embedder (Phrase Match Only)

| Dimension | Detail |
|-----------|--------|
| Approach | Use phrase matching for ALL sources. Walk dirs, match names against `collections.json` aliases. |
| Benefits | Simplest implementation; single strategy to maintain; works for kisvadim, eidogo, tasuki |
| Drawbacks | Misses OGS (manifest-based ordering), gotools (filename-encoded chapter/position); ~47K puzzles lose ordering data |
| Complexity | Low (~200 lines core) |
| Risk | OGS match rate will be poor — directory names are `{numericId}-{slug}` format requiring manifest for ordering |
| Test Impact | Minimal — single code path |

### OPT-2: Multi-Strategy Embedder (Recommended)

| Dimension | Detail |
|-----------|--------|
| Approach | Strategy registry keyed by source: (A) phrase match, (B) manifest lookup, (C) filename pattern. Each source selects strategy via thin wrapper. |
| Benefits | Maximizes coverage (~50K puzzles); each strategy optimized for its source type; extensible via registry |
| Drawbacks | More code (~400 lines core + ~50 lines per wrapper); 3 strategies to maintain |
| Complexity | Medium |
| Risk | Strategy C (filename pattern) requires per-source regex; brittle if naming changes |
| Test Impact | 3 strategy paths × N sources; good test isolation via strategy interface |

### OPT-3: Embedder Per Source (No Shared Core)

| Dimension | Detail |
|-----------|--------|
| Approach | Each source tool builds its own embedder logic. No `tools/core/` shared module. |
| Benefits | Maximum per-source optimization; no abstraction overhead |
| Drawbacks | Violates DRY — 5+ copies of similar logic; no consistency; maintenance burden grows per source |
| Complexity | High (aggregate) |
| Risk | Inconsistent YL formatting across sources; no shared validation |
| Test Impact | Tests duplicated per source |

## Comparison Matrix

| Dimension | OPT-1 | OPT-2 | OPT-3 |
|-----------|-------|-------|-------|
| Coverage (puzzles) | ~8K (phrase-match sources only) | ~50K (all exploitable sources) | ~50K |
| DRY compliance | ✅ | ✅ | ❌ |
| SOLID compliance | ✅ | ✅ (strategy pattern) | ❌ |
| Extensibility | Low | High | Low |
| Implementation effort | ~1 day | ~2-3 days | ~4-5 days |
| Maintenance | Low | Medium | High |
| OGS ordering | ❌ Lost | ✅ Preserved | ✅ Preserved |
| gotools chapters | ❌ Lost | ✅ Preserved | ✅ Preserved |

## Recommendation

**OPT-2** — Multi-strategy embedder with shared core in `tools/core/`. This is the only option that:
1. Covers all 50K+ exploitable puzzles
2. Preserves OGS manifest ordering and gotools chapter/position encoding
3. Follows DRY/SOLID principles with a strategy interface
4. Is extensible for future sources via the registry pattern

Prerequisite: Extract consolidated phrase matcher from `tools/ogs/collections.py` into `tools/core/collection_matcher.py` (DRY consolidation of 4 duplicate implementations).
