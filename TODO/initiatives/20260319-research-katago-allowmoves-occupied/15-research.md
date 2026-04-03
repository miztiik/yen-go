# Research Brief: KataGo allowMoves Behavior with Occupied Coordinates

**Last Updated**: 2026-03-19
**Initiative**: 20260319-research-katago-allowmoves-occupied
**Status**: COMPLETED

---

## 1. Research Question and Boundaries

**Question**: When our enrichment pipeline sends KataGo an `allowMoves` list containing coordinates already occupied by stones, does KataGo:

1. Silently ignore occupied coords (our assumption)?
2. Return an error?
3. Have undefined behavior?
4. Waste computation time checking them?

**Scope**: KataGo Analysis Engine JSON protocol, specifically the `allowMoves` field. We are NOT investigating `moves` (game history) or `initialStones` — those have documented error behavior for illegal positions.

**Success criteria**: Authoritative evidence from KataGo source code and/or documentation confirming the exact behavior, plus a risk assessment for the 500K+ puzzle scale.

---

## 2. Internal Code Evidence

### E-1: Two code paths produce allowMoves lists — only one filters occupied coords

| ID | Code Path | Location | Filters Occupied? | Used When |
|----|-----------|----------|-------------------|-----------|
| E-1a | `Position.get_puzzle_region_moves()` | [models/position.py L92-131](../../../tools/puzzle-enrichment-lab/models/position.py#L92-L131) | **YES** — `if (x, y) not in occupied:` at L128 | Fallback (no entropy ROI) |
| E-1b | `get_roi_allow_moves()` | [analyzers/entropy_roi.py L135-166](../../../tools/puzzle-enrichment-lab/analyzers/entropy_roi.py#L135-L166) | **NO** — generates all coords in expanded bounding box | Primary path (entropy ROI available) |
| E-1c | `get_allow_moves_with_fallback()` | [analyzers/frame_adapter.py L207-222](../../../tools/puzzle-enrichment-lab/analyzers/frame_adapter.py#L207-L222) | Inherits from E-1a or E-1b | Routing layer |

The primary code path (E-1b, entropy ROI) does NOT filter occupied coordinates before sending to KataGo.

### E-2: Log evidence proves occupied coords are sent and silently accepted

From [.lab-runtime/outputs/perf-33-b10-run-stderr.log L23](../../../tools/puzzle-enrichment-lab/.lab-runtime/outputs/perf-33-b10-run-stderr.log#L23):

```
board=9x9, stones=47, visits=500, initialPlayer=B, allowMoves_count=35
```

**Mathematical proof**: 9×9 = 81 total intersections. 81 − 47 stones = **34 empty positions**. But `allowMoves_count=35`. Therefore **at least 1 occupied coordinate** is in the allowMoves list. KataGo returned a valid response (no error logged).

### E-3: AnalysisRequest serialization — no occupancy filtering at JSON level

[models/analysis_request.py L109-126](../../../tools/puzzle-enrichment-lab/models/analysis_request.py#L109-L126): The `to_katago_json()` method passes `self.allowed_moves` directly to KataGo without any occupancy validation:

```python
payload["allowMoves"] = [
    {"player": player, "moves": list(self.allowed_moves), "untilDepth": 1}
]
```

### E-4: Engine error handling — errors caught but never triggered by occupied allowMoves

[engine/local_subprocess.py L229-234](../../../tools/puzzle-enrichment-lab/engine/local_subprocess.py#L229-L234):

```python
if "error" in data:
    raise RuntimeError(f"KataGo error: {data['error']}")
```

The `{"error":"Illegal move 2: S17"}` observed in prior logs is from the `moves` field (game history), NOT from `allowMoves`. No such error has ever been observed for `allowMoves` with occupied coords.

### E-5: No existing tests verify allowMoves with occupied coordinates

Searched `tools/puzzle-enrichment-lab/tests/test_entropy_roi.py` — the `TestGetRoiAllowMoves` class tests bounding box expansion and margin logic but never tests behavior when occupied coords are included. No test file in the test suite mentions "occupied" in the context of allowMoves.

---

## 3. External Evidence (KataGo Source Code)

### X-1: KataGo Analysis Engine documentation — allowMoves spec

From [KataGo docs/Analysis_Engine.md L97-103](https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md#L97-L103):

> `allowMoves (list of dicts)`: Optional. Same as `avoidMoves` except prohibits all moves EXCEPT the moves specified. Currently, the list of dicts must also be length 1.

The documentation says nothing about requiring moves to be on empty intersections. No mention of occupancy validation.

### X-2: KataGo coordinate parsing — no occupancy check

[analysis.cpp L729-756](https://github.com/lightvector/KataGo/blob/main/cpp/command/analysis.cpp#L729-L756) — `parseBoardLocs` function:

```cpp
Loc loc;
if(!Location::tryOfString(s, boardXSize, boardYSize, loc) ||
   (!allowPass && loc == Board::PASS_LOC) ||
   (loc == Board::NULL_LOC)) {
    reportErrorForId(rbase.id, field, "Could not parse board location: " + s);
    return false;
}
buf.push_back(loc);
```

This only validates that the coordinate is a parseable GTP board location. **No board state is consulted. No occupancy check exists.**

### X-3: allowMoves → avoidMoveUntilByLoc conversion — occupied coords are harmlessly set

[analysis.cpp L1104-1117](https://github.com/lightvector/KataGo/blob/main/cpp/command/analysis.cpp#L1104-L1117):

```cpp
if(hasAllowMoves) {
    std::fill(avoidMoveUntilByLoc.begin(), avoidMoveUntilByLoc.end(), (int)untilDepth);
    for(Loc loc: parsedLocs) {
        avoidMoveUntilByLoc[loc] = 0;  // "don't avoid this location"
    }
}
```

`allowMoves` is implemented as the inverse of `avoidMoves`: ALL locations are marked "avoid until depth N", then each allowed location is set to 0 ("don't avoid"). Setting `avoidMoveUntilByLoc[occupied_loc] = 0` is a no-op for search because occupied locations are already rejected by legality checks.

### X-4: Search rejects occupied moves BEFORE checking avoidMoveUntilByLoc

[searchresults.cpp L244-250](https://github.com/lightvector/KataGo/blob/main/cpp/search/searchresults.cpp#L244-L250):

```cpp
if(!rootHistory.isLegal(rootBoard, moveLoc, rootPla) || policyProb < 0 || ...)
    return false;
const std::vector<int>& avoidMoveUntilByLoc = ...;
if(avoidMoveUntilByLoc.size() > 0) {
    // ... check only reached if move already passed legality
```

**Two independent rejection gates exist before avoidMoveUntilByLoc is consulted:**

1. `rootHistory.isLegal()` — occupied intersections are always illegal in Go
2. `policyProb < 0` — the neural net outputs `-1` policy for illegal moves (occupied positions)

Both conditions independently reject occupied positions. The `avoidMoveUntilByLoc` array entry for an occupied position is **never read**.

### X-5: Policy output for illegal moves

From [Analysis_Engine.md L280](https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md#L280):

> `policy` - ... with positive values summing to 1 indicating the neural network's prediction of the best move before any search, and **`-1` indicating illegal moves**.

Occupied positions always get policy = `-1`.

### X-6: KataGo's POLICY_ILLEGAL_SELECTION_VALUE

[search.h L392](https://github.com/lightvector/KataGo/blob/main/cpp/search/search.h#L392):

```cpp
static constexpr double POLICY_ILLEGAL_SELECTION_VALUE = -1e50;
```

This ensures illegal moves (occupied positions) are never selected for MCTS expansion, regardless of avoidMoveUntilByLoc settings.

---

## 4. Candidate Adaptations for Yen-Go

### Option A: Do nothing (current behavior)

- **Rationale**: Occupied coords in `allowMoves` are proven harmless. KataGo silently ignores them at multiple independent levels.
- **Effort**: Zero.
- **Risk**: None for correctness or performance. Log readability slightly degraded (allowMoves_count is inflated).

### Option B: Filter occupied coords in `get_roi_allow_moves()`

- **Rationale**: Cleaner data, more accurate `allowMoves_count` in logs, follows defensive programming principle.
- **Effort**: ~5 lines — pass `Position` (or occupied set) into `get_roi_allow_moves()` and add a filter.
- **Risk**: Minimal. Requires passing stone positions to a function that currently only takes the ROI struct and board_size.

### Option C: Filter at the `AnalysisRequest.to_katago_json()` layer

- **Rationale**: Single filtering point catches all callers.
- **Effort**: ~10 lines — requires access to position stones at serialization time.
- **Risk**: Couples the request model to position state, which it currently doesn't depend on.

---

## 5. Risks, License/Compliance, and Rejection Reasons

| ID | Risk | Severity | Assessment |
|----|------|----------|------------|
| R-1 | KataGo errors on occupied allowMoves | **None** | DISPROVEN. `parseBoardLocs` only validates GTP syntax, not board state |
| R-2 | Computation wasted on occupied coords | **None** | DISPROVEN. Search rejects occupied positions before checking avoidMoveUntilByLoc |
| R-3 | Wrong analysis results from edge cases | **None** | DISPROVEN. Two independent layers (legality + policy) reject occupied moves |
| R-4 | Future KataGo version adds validation | **Negligible** | No indication in codebase. Would be a breaking protocol change |
| R-5 | Log readability / debugging overhead | **Low** | `allowMoves_count` includes occupied coords, slightly inflated vs true candidate count |
| R-6 | Silent puzzle pipeline failures | **None** | DISPROVEN by log evidence — occupied coords sent, valid responses received |

**License**: N/A — no external code adopted.
**Rejection of Option C**: Coupling `AnalysisRequest` to `Position` breaks the current clean model/position separation.

---

## 6. Planner Recommendations

1. **Status quo is safe at 500K+ scale.** The assumption "KataGo silently ignores occupied allowMoves" is **PROVEN** by KataGo source code: three independent mechanisms (GTP parse-only validation, `isLegal()` check, `policyProb < 0` gate) all confirm occupied coords are harmlessly ignored with zero computation waste.

2. **Optional: Implement Option B (Level 1 fix, ~5 lines) for log hygiene.** Filter occupied coords in `get_roi_allow_moves()` so `allowMoves_count` in logs accurately reflects candidate empty intersections. This is purely cosmetic / diagnostic — not required for correctness or performance.

3. **Do NOT implement Option C.** It breaks model-position separation in `AnalysisRequest` for no functional benefit.

4. **No test gap to close.** Testing allowMoves with occupied coords would test KataGo's behavior, not our pipeline's. Our pipeline already works correctly regardless.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260319-research-katago-allowmoves-occupied/` |
| `artifact` | `15-research.md` |
| `post_research_confidence_score` | **95** |
| `post_research_risk_level` | **low** |

**Top recommendations** (ordered):

1. No action required — current behavior is proven safe at scale
2. Optional Level 1 fix: filter occupied coords in `get_roi_allow_moves()` for log clarity
3. Do not add occupied-coord tests (they'd test KataGo, not our code)
4. Do not couple AnalysisRequest to Position state

**Open questions**: None. All research questions resolved with source-level evidence.
