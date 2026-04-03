# Options: Tsumego Frame Flood-Fill Rewrite

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Last Updated**: 2026-03-12

---

## Option Comparison

| Criterion | OPT-1: Normalize-Swap Only (KaTrain Parity) | OPT-2: Normalize-Swap + BFS Flood-Fill (Full Rewrite) | OPT-3: Full Rewrite + Validation Hardening |
|-----------|---------------------------------------------|--------------------------------------------------------|---------------------------------------------|
| **Summary** | Fix `normalize_to_tl()` axis-swap only. Linear scan stays, but now always operates on corner-normalized puzzles = connected zones by construction. Remove `offence_to_win`. | Fix normalize + replace `fill_territory()` with BFS flood-fill. Connected zones guaranteed by algorithm. Remove `offence_to_win`. Delete `_choose_scan_order`. | OPT-2 + comprehensive post-fill validation assertions + diagnostic dump of failed frames + multi-seed BFS fallback for unreachable cells. |

---

## OPT-1: Normalize-Swap Only (KaTrain Parity)

### Approach
Fix the root cause identified by research: `normalize_to_tl()` lacks axis-swap. KaTrain uses `if imin < jmin → swap(i,j)` to reliably put puzzles in a corner. Our implementation only flips, leaving edge puzzles as edge puzzles.

**Changes:**
1. Add `swap_xy: bool` to `NormalizedPosition` dataclass
2. Update `normalize_to_tl()` to detect when puzzle is on an edge (not corner) and swap axes
3. Update `denormalize()` to reverse the swap
4. Remove `offence_to_win` from `FrameConfig`, `compute_regions()`, `apply_tsumego_frame()`
5. Update `compute_regions()` to use 50/50 territory split (score-neutral)
6. Keep `fill_territory()` linear scan unchanged (it works correctly on corner-normalized positions)
7. Keep `_choose_scan_order()` (returns row-major for corner positions, which is correct)
8. Update test assertions for changed normalization behavior

**Does NOT change:**
- Fill algorithm (linear scan preserved)
- Border wall placement logic
- Ko threat placement

### Benefits
| ID | Benefit |
|----|---------|
| B1 | Smallest code change (~30 lines modified) |
| B2 | Directly addresses root cause (R-6, R-13, R-14) |
| B3 | Linear scan is proven to work on corner puzzles (KaTrain uses it) |
| B4 | Lowest calibration risk — fill pattern stays similar |
| B5 | Fastest to implement and validate |

### Drawbacks
| ID | Drawback |
|----|----------|
| D1 | Checker stones in far-from-seam regions still exist (ISSUE-1 partially unresolved) |
| D2 | No connectivity guarantee — relies on corner-normalization correctness |
| D3 | No post-fill validation — silent failures still possible (ISSUE-4 unresolved) |
| D4 | Border wall can still fragment fill in edge cases |
| D5 | Does not address user's reference to GoProblems.com clean fill quality |

### Risk Assessment
| Risk | Likelihood | Impact |
|------|-----------|--------|
| Axis-swap introduces subtle coordinate bugs in denormalize | Medium | High |
| Checker stones remain in sparse regions (weaker fill) | High | Medium |
| No validation catches future regressions | Medium | Medium |

### Architecture/Policy Compliance
- ✅ C1-C7 constraints met
- ✅ Legality guards preserved
- ⚠️ G1 (connected fill) NOT guaranteed — relies on normalization correctness
- ⚠️ G2 (no dead stones) NOT addressed — checker stones remain
- ✅ G3 (score-neutral) addressed
- ❌ G4 (post-fill validation) NOT addressed
- ✅ G5 (correct normalization) addressed
- ⚠️ G6 (clean API) partially — `_choose_scan_order()` retained

---

## OPT-2: Normalize-Swap + BFS Flood-Fill (Full Rewrite)

### Approach
Fix normalize (like OPT-1) AND replace the fill algorithm. BFS flood-fill from seed points guarantees connected zones by construction.

**Changes:**
1. All OPT-1 changes (normalize-swap, offence_to_win removal, score-neutral split)
2. Replace `fill_territory()` linear scan with BFS flood-fill:
   - Compute frameable cells = total board − puzzle_region − occupied
   - Defender BFS from seed at farthest corner from puzzle (e.g., `(bs-1, 0)` after normalize)
   - Attacker BFS from border wall cells + farthest opposite corner
   - Quota: defender fills `frameable // 2` cells, attacker fills remainder
   - Each BFS placement applies existing legality guards (eye, suicide, puzzle-protect)
3. Delete `_choose_scan_order()`, add `_choose_flood_seeds()`
4. Modify `build_frame()` to pass border stone coords as attacker BFS seeds
5. Update `NormalizedPosition` with `swap_xy` field
6. Update all affected tests + add connectivity tests
7. Update docs

### Benefits
| ID | Benefit |
|----|---------|
| B1 | Connected zones guaranteed by construction (BFS grows from seed = single component) |
| B2 | No dead checker stones — every stone is part of a connected group |
| B3 | Addresses all 5 issues (ISSUE-1 through ISSUE-5) |
| B4 | BFS primitive already exists in codebase (`liberty.py:count_group_liberties`) |
| B5 | Cleaner API — `_choose_scan_order()` deleted, replaced with geometry-aware seeds |
| B6 | Fill quality matches GoProblems.com reference (solid blocks, clean seams) |
| B7 | Attacker BFS seeded from border cells = border + attacker fill form single connected blob (ISSUE-2 fixed) |

### Drawbacks
| ID | Drawback |
|----|----------|
| D1 | ~80 lines changed vs ~30 for OPT-1 |
| D2 | All calibration tests need threshold updates |
| D3 | BFS may not reach all frameable cells if puzzle region creates isolated pockets (requires fallback) |
| D4 | No validation — still relies on algorithm correctness (ISSUE-4) |

### Risk Assessment
| Risk | Likelihood | Impact |
|------|-----------|--------|
| BFS leaves unreachable cells (puzzle as barrier) | Medium | Medium |
| Calibration tests all need updating | High | Low |
| Fill density changes affect downstream analysis quality | Low | Medium |

### Architecture/Policy Compliance
- ✅ C1-C7 constraints met
- ✅ Legality guards preserved
- ✅ G1 (connected fill) guaranteed by BFS construction
- ✅ G2 (no dead stones) guaranteed — BFS only places connected stones
- ✅ G3 (score-neutral) addressed
- ❌ G4 (post-fill validation) NOT addressed
- ✅ G5 (correct normalization) addressed
- ✅ G6 (clean API) fully addressed

---

## OPT-3: Full Rewrite + Validation Hardening (Recommended)

### Approach
OPT-2 changes PLUS comprehensive post-fill validation and diagnostic tooling.

**Changes:**
1. All OPT-2 changes (normalize-swap, BFS flood-fill, offence_to_win removal, score-neutral)
2. Add `validate_frame()` function in `tsumego_frame.py`:
   - BFS connectivity check: both defender and attacker fill must be single connected components
   - Dead stone check: no frame stone with zero same-color orthogonal neighbors (except board edges)
   - Zone integrity check: no defender stone inside attacker zone's convex hull
   - Returns `(is_valid, diagnostics_dict)` tuple
3. In `build_frame()`: call `validate_frame()` after assembly. If validation fails:
   - Log `WARNING` with full diagnostics (position, seed locations, skip counts)
   - Log the failed frame position as SGF for troubleshooting (`position.to_sgf()`)
   - Return `FrameResult` with original position (frame skipped), `frame_stones_added=0`
4. Multi-seed BFS fallback: after primary BFS, scan frameable cells not reached; if >5% unreached, add secondary seeds and extend BFS
5. Fill density metric preserved in `FrameResult`
6. Update all tests: existing density checks + new connectivity assertions

### Benefits
| ID | Benefit |
|----|---------|
| B1 | All OPT-2 benefits (B1-B7) |
| B2 | No silent failures — validation catches and reports any frame quality issues |
| B3 | Diagnostic dump enables analysis of failed frames (user request Q5) |
| B4 | Multi-seed fallback handles unreachable cell edge cases |
| B5 | Defense-in-depth: algorithm correctness (BFS) + validation (assertions) |
| B6 | Addresses ALL 5 issues + ALL 6 goals (G1-G6) |
| B7 | Future-proof: validation catches regressions from any future frame changes |

### Drawbacks
| ID | Drawback |
|----|----------|
| D1 | Largest code change (~120 lines total) |
| D2 | All calibration tests need threshold updates (same as OPT-2) |
| D3 | Validation adds ~10ms per frame (BFS traversal) — negligible vs KataGo analysis time |
| D4 | Most complex option to review and test |

### Risk Assessment
| Risk | Likelihood | Impact |
|------|-----------|--------|
| Validation is too strict, rejects valid frames | Low | Medium (fallback = original position) |
| Multi-seed fallback adds complexity | Low | Low |
| Added BFS for validation negligible perf impact | Very Low | Very Low |

### Architecture/Policy Compliance
- ✅ C1-C7 constraints met
- ✅ Legality guards preserved
- ✅ G1 (connected fill) guaranteed by BFS construction + validated
- ✅ G2 (no dead stones) guaranteed + validated
- ✅ G3 (score-neutral) addressed
- ✅ G4 (post-fill validation) fully addressed
- ✅ G5 (correct normalization) addressed
- ✅ G6 (clean API) fully addressed

---

## Tradeoff Matrix

| Criterion | OPT-1 | OPT-2 | OPT-3 |
|-----------|-------|-------|-------|
| **Correctness (ISSUE-1: Dead stones)** | ⚠️ Partially — checker pattern remains | ✅ Fully — BFS connected | ✅ Fully — BFS + validated |
| **Correctness (ISSUE-2: Border fragments)** | ⚠️ Partially | ✅ Fully — attacker seeded from border | ✅ Fully + validated |
| **Correctness (ISSUE-3: Disconnected islands)** | ✅ Fixed by normalize-swap | ✅ Fixed by normalize + BFS | ✅ Fixed + validated |
| **Correctness (ISSUE-4: No validation)** | ❌ Not addressed | ❌ Not addressed | ✅ Fully addressed |
| **Correctness (ISSUE-5: offence_to_win)** | ✅ Removed | ✅ Removed | ✅ Removed |
| **Goals met** | 3/6 (G3, G5, partial G6) | 5/6 (G1-G3, G5-G6) | 6/6 (G1-G6) |
| **Code complexity** | ~30 lines changed | ~80 lines changed | ~120 lines changed |
| **Test impact** | Low — normalize tests update | Medium — fill output changes | Medium-High — fill + new tests |
| **Calibration effort** | Low | Medium | Medium |
| **Future regression risk** | High — no validation | Medium — algorithm correct but unchecked | Low — validated |
| **Fill quality** | ⚠️ Checker pattern far from seam | ✅ Solid connected blocks | ✅ Solid + verified |
| **User reference match** | ❌ Does not match GoProblems.com | ✅ Matches GoProblems.com style | ✅ Matches + guaranteed |
| **Risk level** | Medium | Low-Medium | Low |
| **KISS/YAGNI** | ✅ Simplest | ✅ Right complexity for problem | ⚠️ Validation may be over-engineering |

---

## Recommendation

**OPT-3 (Full Rewrite + Validation Hardening)** is recommended for the following reasons:

1. **All 6 goals met** — OPT-1 misses 3 goals, OPT-2 misses 1
2. **User explicitly requested hard-fail validation** (Q5:A) — OPT-1 and OPT-2 cannot deliver this
3. **"No wall is better than bad wall"** — only OPT-3 guarantees detection and fallback when the wall/fill is bad
4. **Defense-in-depth** — BFS guarantees correctness by construction; validation catches any edge cases the algorithm misses
5. **Diagnostic dump for troubleshooting** — user requirement (Q5) for frame analysis
6. **Incremental effort** — OPT-3 is 40 lines more than OPT-2, most of which is a single `validate_frame()` function
7. **Future-proof** — validation catches regressions from any future frame changes

The YAGNI concern (D4) is mitigated by the user's explicit requirement for validation (Q5:A) and the project's existing pattern of post-operation validation (e.g., `has_frameable_space()` check for F11).

---

> **See also**:
>
> - [Charter](./00-charter.md) — Goals G1-G6 and constraints C1-C7
> - [Clarifications](./10-clarifications.md) — User decisions Q1-Q8
> - [Research: Flood-Fill Strategy](../20260312-research-tsumego-frame-flood-fill/15-research.md) — R-20 through R-25
> - [Governance: Charter Decision](./70-governance-decisions.md) — RC-1 and RC-2
