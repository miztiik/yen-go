# Charter: Tsumego Frame Legality & Correctness

**Initiative ID**: `20260311-1800-feature-tsumego-frame-legality`
**Last Updated**: 2026-03-11 (amended: F25 added per GOV-CHARTER-CONDITIONAL)

---

## 1. Problem Statement

The current tsumego frame implementation (`tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`, V2 rewrite completed 2026-03-08) places frame stones around puzzle positions without Go legality enforcement. An external expert audit and Governance Panel review identified residual gaps in the V2 implementation:

- Frame stones are placed as raw `Stone()` objects without liberty counting, capture resolution, or suicide checking
- Frame stones adjacent to puzzle stones could theoretically reduce puzzle stone liberties to zero (mitigated by margin=2 but unverified on full corpus)
- Player-to-move is preserved from input; 50+ frame stones placed without alternating turns creates move parity mismatch for KataGo's policy head
- Fill patterns are fully deterministic with no randomization
- Ko-threat placement uses fixed offsets that may fail on crowded boards
- No eye-space detection — frame stones may be placed inside obvious eyes
- Attacker inference ignores PL (player_to_move) — relies on heuristics only, PL provides strong tie-breaker signal

## 2. Goals

| ID | Goal | Acceptance Criteria |
|----|------|-------------------|
| G1 | Zero illegal positions from framing | After framing, no stone group has zero liberties. Verified on full puzzle corpus. |
| G2 | Zero puzzle stone captures from framing | No frame stone placement reduces any puzzle stone's liberty count to zero. |
| G3 | KataGo receives correct turn/ko context | `player_to_move` is set to a canonical value after framing; move parity is coherent. |
| G4 | Eye-space respected in fill | Frame stones are not placed inside empty points that form obvious single-point eyes of existing groups. |
| G5 | Nearly-full board robustness | Boards with <10% frameable area skip or reduce fill aggressively. |

## 3. Non-Goals

- Full Go rules engine (only minimal liberty counting + capture resolution)
- Stochastic/augmented frame generation (research interest, not production need)
- Synthetic komi fixes (off by default, experimental only)
- Influence-based flood fill (algorithmic improvement, not correctness)
- Soft/gradient borders (aesthetic improvement)
- Ko-threat sliding window search (existing fixed offsets work for most cases)

## 4. Constraints

- Tools must NOT import from `backend/` (project rule)
- All frame code lives in `tools/puzzle-enrichment-lab/analyzers/`
- Existing 46 frame tests + 271 regression tests must continue passing
- No new external dependencies without `pyproject.toml` review

## 5. In-Scope Findings

| ID | Finding | Panel Severity |
|----|---------|---------------|
| F1 | Illegality/capture issues — stones added without resolving captures or suicide | **High** |
| F2 | Unintentional puzzle stone capture — frame may capture puzzle-region stones | **High** (pending data audit RC-1) |
| F3 | Turn/ko semantics mismatch — player_to_move parity wrong after 50+ frame stones | **High** |
| F7 | Ko-threat placement fragility — fixed offsets on crowded boards | **Low** |
| F8 | Need legality-aware stone placement (remediation for F1) | **High** |
| F9 | Need sensible turn/ko state after framing (remediation for F3) | **Medium-High** |
| F10 | Avoid immediate captures of puzzle stones (remediation for F2) | **High** |
| F11 | Nearly-full board robustness — no density check before fill | **Low** |
| F20 | Frame stones placed in obvious eyes of existing groups | **Medium** |
| F25 | PL (player_to_move) not used in attacker inference — `guess_attacker()` ignores PL property, relies on heuristics only; PL provides strong tie-breaker signal | **Medium** |

## 6. Out-of-Scope Findings (removed per RC-2)

| ID | Finding | Reason Excluded |
|----|---------|----------------|
| F5 | Synthetic komi brittleness | Off by default, not a production issue |
| F6 | Position API inconsistency | Not a finding — API is consistent (Pydantic computed properties) |
| F12 | Normalize roundtrip test missing | Not a finding — test already exists (`test_roundtrip_identity`) |

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Building liberty-counting engine is scope creep | Medium | High | Minimal implementation (~100-150 lines). No full rules engine. |
| Legality enforcement changes frame output, breaking calibration | Medium | Medium | Run calibration tests after changes. Golden-file comparison. |
| Data audit (RC-1) reveals 0 illegal positions → F1/F2 downgraded | Medium | Low | If 0 cases, defer legality engine. Still fix F3 (turn parity). |

---

> **See also**:
>
> - [Concepts: Tsumego Frame](../../docs/concepts/tsumego-frame.md) — Algorithm overview
> - [Prior Initiative: Frame Rewrite](../20260308-1500-feature-tsumego-frame-rewrite/) — V2 rewrite (closed out)
> - [Teaching Comments Quality Initiative](../20260311-1800-feature-teaching-comments-quality/) — Parallel initiative
