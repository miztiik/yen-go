# Analysis: GP Frame Swap

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Planning Metadata

| Field | Value |
|-------|-------|
| Planning Confidence Score | 80 |
| Risk Level | Low |
| Research Invoked | No (score ≥ 70, risk low, no external evidence gaps) |

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| R-1 | downstream | `query_builder.py` → `apply_frame()` return type change | Low | Adapter returns `FrameResult` with `.position`; call site extracts it. Same data, different container. | T12 | ✅ addressed |
| R-2 | downstream | `enrich_single.py` → `compute_regions()` new signature | Low | Signature changes from `(position, FrameConfig)` → `(position, *, margin, board_size)`. Simpler. 2 callsites. | T13 | ✅ addressed |
| R-3 | downstream | `solve_position.py` → `puzzle_region` type contract | Low | `FrameRegions.puzzle_region` stays `frozenset[tuple[int,int]]`. Type assertion in T4. No code change in `solve_position.py`. | T4 (RC-2) | ✅ addressed |
| R-4 | lateral | `liberty.py` → dead import removal | None | Pure cleanup. No runtime impact. | T14 | ✅ addressed |
| R-5 | lateral | `test_tsumego_frame.py` → skip marker | None | Tests still exist. No deletion. un-skip for rollback. | T15 | ✅ addressed |
| R-6 | lateral | `test_frames_gp.py` → import fix | None | Fixes existing broken import. Enables tests that were already broken. | T16 | ✅ addressed |
| R-7 | upstream | `ko_type` str → `ko` bool conversion | Low | GP doesn't distinguish direct/approach. Both produce ko material. Conversion is lossy but semantically correct for frame fill. Log original `ko_type` for observability. | T12 | ✅ addressed |
| R-8 | upstream | `guess_attacker()` heuristic removed from active path | Low | `player_to_move` is convention-correct (Q7, governance-resolved). Pipeline guarantees PL is set. Function still exists in archived BFS code. | T8 | ✅ addressed |
| R-9 | downstream | `docs/concepts/tsumego-frame.md` → stale documentation | Low | T17 updates doc to reflect GP as active. | T17 | ✅ addressed |
| R-10 | lateral | `scripts/show_frame.py` → imports BFS directly, has `--ko`/`--color` flags | Low | T19 rewires to adapter, drops `--ko` and `--color` CLI flags. `probe_frame.py` left as-is (covered by `probe_frame_gp.py`). | T19 | ✅ addressed |

---

## Consistency Checks

| finding_id | severity | finding | resolution |
|------------|----------|---------|------------|
| F1 | Info | Charter G3 (FrameConfig dataclass for GP) mapped to T5-T6. RC-1 resolved: GP uses `GPFrameConfig` (distinct name). `compute_regions` takes plain args. | ✅ pass |
| F2 | Info | Charter G4 (thin adapter) mapped to T7-T10. Adapter contains `apply_frame`, `remove_frame`, `validate_frame`. | ✅ pass |
| F3 | Info | RC-2 (`puzzle_region` type preservation) mapped to T4 (test assertion) and T1 (type definition). | ✅ pass |
| F4 | Info | Charter C2 (`player_to_move` preservation) → GP already preserves PL at `tsumego_frame_gp.py` line 157. Adapter passes through. T11 tests this. | ✅ pass |
| F5 | Warning | `validate_frame` is ported from BFS (~80 lines). Could have BFS-specific assumptions. | Mitigated: dead stone check and connectivity check are generic geometry. No BFS-specific logic in the validation function body. |
| F6 | Info | `ko_type` str→bool is a lossy conversion (R-7). GP frame fill doesn't distinguish direct/approach — both place ko material. | ✅ acceptable — frame fill doesn't need the distinction; only KataGo rules config uses it, and that's separate from frame fill. |

---

## Coverage Map

| Charter Goal | Plan Section | Tasks | Test Coverage |
|-------------|-------------|-------|---------------|
| G1 (Replace active frame) | §3d query_builder rewire | T12 | T11, T18 |
| G2 (Extract compute_regions) | §3a frame_utils.py | T1-T3 | T4 |
| G3 (FrameConfig for GP) | §3c tsumego_frame_gp.py | T5-T6 | T16 (existing GP tests) |
| G4 (Thin adapter) | §3b frame_adapter.py | T7-T10 | T11 |
| G5 (GP purity) | C1 constraint | — | Visual inspection: no new logic in GP |
| G6 (Dead import cleanup) | §3f liberty.py | T14 | T18 (import check) |
| G7 (Skip BFS tests, add GP tests) | §3g, §3i, §3j | T15, T4, T11 | T18 |
| G8 (Fix test import) | §3h test_frames_gp.py | T16 | T18 |
| — (show_frame.py script) | §3h show_frame.py | T19 | T18 |

---

## Unmapped Tasks

None — all 19 tasks trace to charter goals or script maintenance.

---

## Constraint Verification Matrix

| Constraint | Verification Method | Tasks |
|-----------|-------------------|-------|
| C1 (GP purity) | Diff `tsumego_frame_gp.py` — only `GPFrameConfig` added | T5, T6 |
| C2 (`player_to_move`) | T11 test: `result.position.player_to_move == original.player_to_move` | T11 |
| C3 (Same return shape) | `FrameResult` type in adapter matches consumer expectations | T7, T8 |
| C4 (`puzzle_region` type) | T4 assertion: `isinstance(fr.puzzle_region, frozenset)` | T4 |
| C5 (BFS kept, tests skipped) | T15: `pytest.mark.skip`. `tsumego_frame.py` untouched. | T15 |
| C6 (tools/ isolation) | No new imports from `backend/` | All new files |
