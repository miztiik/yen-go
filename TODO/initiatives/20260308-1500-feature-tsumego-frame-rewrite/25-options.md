# Options: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08  
> **Governance charter preflight**: GOV-CHARTER-APPROVED (unanimous)

---

## Options Comparison

| Dimension              | OPT-1: Strict KaTrain Port                                                                                        | OPT-2: Merged KaTrain + ghostban                                                                                                              | OPT-3: Two-Phase (frame now, ko later)                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **ID**                 | OPT-1                                                                                                             | OPT-2                                                                                                                                         | OPT-3                                                                                          |
| **Approach**           | Port KaTrain's `tsumego_frame.py` directly to our codebase. Use their exact algorithms, parameters, and patterns. | Combine KaTrain's attacker inference + normalization + ko threats with ghostban's border logic + `offence_to_win=10` + `defense_area` formula | Same as OPT-2 but split into two PRs: (1) core frame rewrite, (2) ko threats module            |
| **Attacker inference** | KaTrain `guess_black_to_attack()` — edge-proximity heuristic                                                      | Same as OPT-1                                                                                                                                 | Same as OPT-1                                                                                  |
| **Fill algorithm**     | KaTrain count-based half/half with `(i+j)%2==0` checkerboard holes                                                | Same as OPT-1 (shared algorithm)                                                                                                              | Same as OPT-1                                                                                  |
| **Border handling**    | KaTrain: border on ALL 4 sides (attacker-colored wall ring)                                                       | ghostban: border only on non-board-edge sides (more principled — TL corner gets border on right+bottom only)                                  | Same as OPT-2                                                                                  |
| **`offence_to_win`**   | `5` (KaTrain default)                                                                                             | `10` (ghostban, configurable) — proven on goproblems.com with b10 model                                                                       | Same as OPT-2                                                                                  |
| **Territory formula**  | KaTrain: `defense_area = (size² - total_stones) // 2 - 5`                                                         | ghostban: `defense_area = floor((size² - bbox_area) / 2) - komi - offence_to_win` (uses bounding box, not total stones)                       | Same as OPT-2                                                                                  |
| **Normalization**      | KaTrain: `snap()` + `flip_stones()` — normalize to TL corner, frame, denormalize                                  | Same (KaTrain's approach)                                                                                                                     | Phase 1: normalization included                                                                |
| **Ko threats**         | KaTrain: `put_ko_threat()` with 2 fixed ASCII patterns, `for_offense_p` logic                                     | Same (KaTrain's approach), gated on `ko_type` parameter                                                                                       | Phase 2 only (deferred)                                                                        |
| **Density**            | ~65-75% (KaTrain's count-based fill)                                                                              | Same                                                                                                                                          | Same                                                                                           |
| **Portability**        | Medium — single algorithm source, but KaTrain Python has some Go-domain shortcuts                                 | High — clean function decomposition designed for JS/TS portability from day 1. Typed payloads at every boundary.                              | High (same design, split delivery)                                                             |
| **Correctness risk**   | Low — direct port of proven algorithm                                                                             | Low — both sources MIT, well-tested in production                                                                                             | Medium — Phase 1 without ko threats may produce worse results for ko puzzles during gap period |
| **Complexity**         | Low (~200 lines)                                                                                                  | Medium (~300-350 lines) — additional border logic and territory formula                                                                       | Low per phase (~200 + ~100) but two review cycles                                              |
| **Test effort**        | Medium — port KaTrain's test patterns                                                                             | Medium — same tests plus border-specific tests                                                                                                | Higher — test twice, maintain phase boundary                                                   |

---

## Detailed Option Descriptions

### OPT-1: Strict KaTrain Port

Port KaTrain's `tsumego_frame.py` as-is (MIT licensed). This is the simplest path — one well-tested source of truth.

**Benefits:**

- Proven in production (KaTrain is widely used)
- Single reference implementation — no design decisions needed
- Smallest code footprint

**Drawbacks:**

- `offence_to_win=5` is suboptimal for small NN models (goproblems.com found 10 works better)
- Border on all 4 sides wastes stones on board edges (e.g., TL corner has wall on top/left where board edge already blocks)
- Territory formula uses total stones instead of bounding box (less precise)
- Modular decomposition would need to be imposed on top of KaTrain's structure

**Risks:**

- KaTrain's code is optimized for KaTrain's UI flow, not our pipeline
- Some KaTrain-specific patterns (e.g., `analyze` callback) don't fit our architecture

### OPT-2: Merged KaTrain + ghostban (Recommended)

Take the best from each source:

- **From KaTrain**: `guess_black_to_attack()`, `snap()`, `flip_stones()`, `put_ko_threat()`, count-based fill
- **From ghostban**: non-edge border, `offence_to_win=10`, `defense_area` with bbox subtraction
- **Our design**: typed payloads (`FrameConfig`, `FrameResult`), small functions (≤40 lines each), structured interface for each step

**Benefits:**

- Best available algorithm (proven by both KaTrain and goproblems.com)
- `offence_to_win=10` validated on goproblems.com with b10 model (relevant to our small-model use case)
- Non-edge border is more principled (fewer wasted stones)
- Clean modular design from the start — each step is a testable function with a typed input/output
- Directly addresses all 15 V1 bugs

**Drawbacks:**

- Slightly more complex than a direct port (~300-350 lines vs ~200)
- Novel combination — not identical to either source (though both are well-tested individually)

**Risks:**

- Low — both algorithms are MIT-licensed and algorithmically understood
- The merge points are well-defined (border logic, territory formula, `offence_to_win` value)

### OPT-3: Two-Phase Delivery

Identical design to OPT-2 but delivered in two separate PRs:

- **Phase 1**: Core frame rewrite (attacker inference, normalization, fill, border) — no ko threats
- **Phase 2**: Ko threats module added

**Benefits:**

- Smaller incremental PRs
- Phase 1 is independently useful and testable

**Drawbacks:**

- Ko puzzles get worse frame quality during the gap between Phase 1 and Phase 2
- Two review cycles, two test updates
- Extra coordination overhead for what is ultimately a single-file change

**Risks:**

- Phase 2 may be deprioritized, leaving ko support permanently missing
- Integration boundary between phases adds unnecessary complexity for a ~350-line file

---

## Evaluation Matrix

| Criterion                            | Weight | OPT-1                        | OPT-2    | OPT-3                              |
| ------------------------------------ | ------ | ---------------------------- | -------- | ---------------------------------- |
| Correctness (fixes all 15 V1 bugs)   | 25%    | ✅ 14/15 (border suboptimal) | ✅ 15/15 | ✅ 14/15 (ko deferred)             |
| Algorithm quality (territory signal) | 20%    | Good                         | Best     | Good (Phase 1) → Best (Phase 2)    |
| JS/TS portability readiness          | 15%    | Medium                       | High     | High                               |
| Implementation complexity            | 15%    | Low                          | Medium   | Medium (split across 2 deliveries) |
| Test effort                          | 10%    | Medium                       | Medium   | Higher (two rounds)                |
| Delivery risk                        | 10%    | Low                          | Low      | Medium (Phase 2 deprioritization)  |
| Maintenance burden                   | 5%     | Low                          | Low      | Low (once merged)                  |

**Weighted scores** (5-point scale):

| Criterion          | OPT-1   | OPT-2   | OPT-3   |
| ------------------ | ------- | ------- | ------- |
| Correctness        | 4       | 5       | 3.5     |
| Algorithm quality  | 3.5     | 5       | 3.5     |
| Portability        | 3       | 5       | 5       |
| Complexity         | 5       | 4       | 3.5     |
| Test effort        | 4       | 4       | 3       |
| Delivery risk      | 5       | 5       | 3.5     |
| Maintenance        | 5       | 5       | 5       |
| **Weighted total** | **4.0** | **4.8** | **3.6** |

---

## Recommendation

**OPT-2: Merged KaTrain + ghostban** is the recommended option.

**Rationale:**

1. Highest correctness — addresses all 15 V1 bugs including border handling
2. Best algorithm quality — `offence_to_win=10` validated on goproblems.com production
3. Clean modular design from day 1 — typed payloads at every boundary, ≤40 lines per function
4. Single delivery — no Phase 2 deprioritization risk
5. Both source algorithms are MIT-licensed and well-understood

The additional ~100-150 lines of code (vs OPT-1) are justified by better border logic, configurable territory balance, and ko threat support — all delivered in one coherent change.
