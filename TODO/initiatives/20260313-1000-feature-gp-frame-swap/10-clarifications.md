# Clarifications: GP Frame Swap

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should old BFS code be removed? | A) Remove BFS code entirely / B) Keep BFS code, skip tests, GP becomes active / C) Keep both wired with a toggle | B — keep code, skip tests | **B** — Keep BFS code but don't use it; skip its tests. GP becomes the active frame. | ✅ resolved |
| Q2 | Where should `compute_regions` + `FrameRegions` live? | A) Stay in `tsumego_frame.py` / B) New shared `frame_utils.py` utility / C) In `enrich_single.py` | B — small shared utility module | **B** — Extract to a shared utility outside both BFS and GP. Pure bbox geometry. | ✅ resolved |
| Q3 | Should GP have a `FrameConfig` dataclass internally? | A) Yes, structured dataclass / B) No, keep keyword args | A — prevents parameter sprawl, structured | **A** — Add `FrameConfig` dataclass for GP internal use. Structured is better than loose kwargs. | ✅ resolved |
| Q4 | Should `remove_tsumego_frame` be added to GP's interface? | A) Yes, in GP module / B) Yes, in shared utility / C) Not needed | B — shared utility, it's a trivial one-liner | **A/B** — Add it so GP has the same interface. Can be in adapter layer. | ✅ resolved |
| Q5 | Where should `validate_frame` live for GP? | A) Inside GP code / B) Separate utility / C) In adapter layer | B/C — keep GP pure, validation outside | **B** — Keep as separate utility. Do not embed in GP code. Keep GP simple. | ✅ resolved |
| Q6 | How to handle `defense_area` in GP? It's a local variable in GP's `_put_outside()`, and a field in BFS's `FrameRegions`. | A) Expose as field in shared `FrameRegions` / B) Keep internal to GP, no external exposure / C) Expose only if consumers need it | B — no external consumer | **B** — Exclude from shared `FrameRegions`. No external consumer. ISP: minimal interface. GOV-CHARTER-APPROVED. | ✅ resolved |
| Q7 | How should attacker color detection work? GP uses `player_to_move` (player to move = attacker), BFS uses `guess_attacker()` heuristic. | A) Use `player_to_move` directly (simpler) / B) Use BFS's `guess_attacker()` heuristic / C) Make configurable | A — convention-correct | **A** — Use `player_to_move` directly. Convention-correct for tsumego (all 4 Go professionals confirm). Pipeline guarantees PL set. GOV-CHARTER-APPROVED. | ✅ resolved |
| Q8 | Should old BFS test file be `pytest.skip`-decorated or moved? | A) Add `pytestmark = pytest.mark.skip` to whole file / B) Move to `tests/archived/` / C) Delete | A — skip marker, least disruptive | **A** — Add skip marker. Don't delete; keep for reference. | ✅ resolved |
| Q9 | Should the dead `FrameRegions` TYPE_CHECKING import in `liberty.py` be removed? | A) Yes / B) No | A — confirmed dead import | **A** — Remove it. Never used at runtime or in any type annotation. | ✅ resolved |
| Q10 | Should `test_frames_gp.py` broken import (`analyzers.frames_gp`) be fixed? | A) Fix import path / B) Rewrite tests entirely | A — fix import, tests are valid | **A** — Fix the import to point to correct module name. | ✅ resolved |

## Pre-resolved from Conversation

1. **GP code purity**: User explicitly wants GP code (~600 lines) kept simple. All complexity (validation, region computation, frame removal) lives in adapter/utility layers outside GP.
2. **Adapter pattern**: Thin adapter layer wraps GP to provide the same interface as BFS, enabling future rollback if needed.
3. **`query_builder.py`**: Must be rewired from `apply_tsumego_frame` → GP adapter.
4. **`enrich_single.py`**: Must import `compute_regions`/`FrameRegions` from new shared utility instead of `tsumego_frame.py`.

## Resolved by Governance (GOV-CHARTER-APPROVED)

- **Q6**: `defense_area` — **Exclude** from shared `FrameRegions`. No external consumer exists. ISP: minimal interface.
- **Q7**: Attacker detection — **Use `player_to_move` directly**. Convention-correct for tsumego. Pipeline guarantees PL is always set. Confirmed by all 4 Go professional panel members.
