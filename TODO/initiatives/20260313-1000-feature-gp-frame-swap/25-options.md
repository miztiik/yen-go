# Options: GP Frame Swap — Adapter Wiring Approach

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Context

The charter is approved. The question now is **how** to wire the GP frame into the existing consumer chain (`query_builder.py`, `enrich_single.py`). The charter establishes: shared utility (`frame_utils.py`), GP stays pure, adapter provides compatibility. The options differ in **adapter design** and **wiring strategy**.

---

## Options Comparison

### OPT-1: Thin Adapter Module (`frame_adapter.py`)

**Approach**: Create a new `analyzers/frame_adapter.py` that wraps `apply_gp_frame()` and provides the same call signature as `apply_tsumego_frame()`. Consumers (`query_builder.py`) import from the adapter instead of directly from either frame module.

**Architecture:**
```
frame_utils.py          ← shared: compute_regions(), FrameRegions, FrameConfig (shared subset)
    ↑                       
frame_adapter.py        ← adapter: apply_frame(), remove_frame(), validate_frame()
    ↑                       imports from tsumego_frame_gp.py + frame_utils.py
    ↑
query_builder.py        ← consumer: imports from frame_adapter
enrich_single.py        ← consumer: imports compute_regions from frame_utils
```

**Return type**: Adapter returns a `FrameResult`-compatible object (position + metadata) so consumers don't need to know about `GPFrameResult`.

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | Clean separation. GP stays pure. Consumers have stable import point. Easy to swap back to BFS by changing one adapter. |
| **Drawbacks** | One extra module to maintain. Slight indirection. |
| **Risks** | Low — thin wrapper, minimal code |
| **Complexity** | Low — ~80-100 lines for adapter |
| **Test impact** | New `test_frame_adapter.py` + `test_frame_utils.py` |
| **Rollback** | Change 1 import in adapter to point back to BFS |

### OPT-2: Direct Swap — Rewire Consumers to GP Directly

**Approach**: No adapter module. Consumers import directly from `tsumego_frame_gp.py`. Add `FrameConfig`, `remove_frame()` directly to the GP module. `validate_frame` and `compute_regions` go to `frame_utils.py`.

**Architecture:**
```
frame_utils.py          ← shared: compute_regions(), FrameRegions, validate_frame()
    ↑
tsumego_frame_gp.py     ← GP: apply_gp_frame() + FrameConfig + remove_gp_frame()
    ↑
query_builder.py        ← imports apply_gp_frame from tsumego_frame_gp
enrich_single.py        ← imports compute_regions from frame_utils
```

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | No extra module. Direct call, zero indirection. Fewer files to maintain. |
| **Drawbacks** | Adds `remove_gp_frame()` and `FrameConfig` to GP module (violates C1 partially). Consumers know about GP directly — harder to swap. `query_builder.py` must handle `GPFrameResult` → extracting `.position`. |
| **Risks** | Medium — adding utility code to GP module creeps toward complexity. Rollback requires changing every consumer import. |
| **Complexity** | Lower initial (no adapter file), but higher coupling |
| **Test impact** | Update `test_frames_gp.py` only + `test_frame_utils.py` |
| **Rollback** | Must change imports in every consumer file back to BFS |

### OPT-3: Strategy Pattern — FrameProvider Interface

**Approach**: Define a `FrameProvider` protocol (Python Protocol class) in `frame_utils.py`. Both BFS and GP implement it. Consumers code against the protocol, and a factory function selects the active provider via config.

**Architecture:**
```
frame_utils.py          ← shared: compute_regions(), FrameRegions, FrameProvider protocol, get_frame_provider()
    ↑
tsumego_frame_gp.py     ← implements FrameProvider
tsumego_frame.py        ← implements FrameProvider
    ↑
query_builder.py        ← calls get_frame_provider().apply_frame(...)
enrich_single.py        ← imports compute_regions from frame_utils
```

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | Cleanest abstraction. Config-driven swap. Both implementations always available. |
| **Drawbacks** | Over-engineering — YAGNI. User explicitly said they won't use BFS. Adds protocol class, factory, config plumbing. More complex than needed. |
| **Risks** | Low technical risk, high complexity risk (violates KISS/YAGNI) |
| **Complexity** | Medium-high — protocol + factory + config |
| **Test impact** | Protocol conformance tests + provider tests |
| **Rollback** | Change config value |

---

## Evaluation Matrix

| Criterion | OPT-1 (Adapter) | OPT-2 (Direct) | OPT-3 (Strategy) |
|-----------|-----------------|-----------------|-------------------|
| GP purity (C1) | ✅ GP untouched | ⚠️ Adds remove + FrameConfig to GP | ✅ GP + protocol impl |
| Rollback ease (C5) | ✅ Change 1 file | ❌ Change all consumers | ✅ Change config |
| KISS/YAGNI | ✅ Simple adapter | ✅ Simplest (no extra file) | ❌ Over-engineered |
| Consumer stability (C3) | ✅ Stable import point | ⚠️ Tied to GP directly | ✅ Protocol-stable |
| File count | +2 (adapter, utils) | +1 (utils) | +1 (utils, but bigger) |
| Lines of code | ~80-100 adapter + ~50 utils | ~50 utils + ~15 GP additions | ~120 protocol + factory + ~50 utils |
| Maintenance | Low | Low initially, higher if swap | Medium ongoing |

---

## Recommendation

**OPT-1 (Thin Adapter)** is recommended because:

1. It directly satisfies charter constraint C1 (GP purity) — GP module stays exactly as-is except for the `FrameConfig` dataclass addition
2. It provides the easiest rollback path (C5) — one file change
3. It follows the user's explicit request: "thin adapter layer so that tomorrow we go to BFS also we can use it"
4. It avoids YAGNI (no strategy pattern or protocol for a one-time swap)
5. Consumer stability (C3) — `query_builder.py` imports from adapter, never directly from frame modules

The adapter is intentionally thin (~80-100 lines): `apply_frame()` wraps `apply_gp_frame()`, `remove_frame()` is a one-liner, `validate_frame()` is the existing check.
