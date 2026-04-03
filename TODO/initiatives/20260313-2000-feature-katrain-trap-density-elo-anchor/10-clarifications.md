# Clarifications — KaTrain Trap Density + Elo-Anchor

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? Should existing puzzles retain current difficulty scores? | A: Full re-enrichment OK / B: Backward compat (shadow mode) / C: Other | A | **A** — Full re-enrichment OK. Lab is offline; no published scores affected until new run. | ✅ resolved |
| Q2 | Should old `\|winrate_delta\| × policy` trap density formula be removed or kept alongside? | A: Remove old, replace entirely / B: Keep both configurable / C: Keep old as fallback | A | **A** — Remove. Old formula documented as approximation. New formula strictly better. | ✅ resolved |
| Q3 | `Refutation` model has `winrate_delta` but no `score_delta`. Data available in KataGo response but dropped. Add `score_delta` field? | A: Yes, add to model / B: Compute inline by re-querying / C: Other | A | **A** — Add `score_delta` to `Refutation` model. Stay close to KataGo. ~10 lines across 2 files. | ✅ resolved |
| Q4 | Elo-anchor scope: log-only, soft warning, or hard gate that overrides level? | A: Log-only / B: Soft warning ≥2 levels / C: Hard gate (override level) | B | **C** — Hard gate. "The whole idea of having a level estimation is to estimate puzzles correctly." Must get levels right. | ✅ resolved |
| Q5 | KaTrain covers 18k–5d. For dan levels (and below 18k), no Elo-anchor data. Skip? | A: Skip, log "no data" / B: Extrapolate / C: Other | A | **A** — Skip. Log "no Elo anchor available" for both dan levels AND <18k (novice/beginner). No extrapolation. | ✅ resolved |
| Q6 | Adopt full KaTrain `adj_weight` floor pattern, or just switch numerator? | A: Full pattern (floor + fallback) / B: Just switch numerator / C: Other | B | **Defer to governance** — User wants alignment with KaTrain. Lean toward A (full pattern). Let governance decide. | ✅ resolved (deferred) |

---

## Follow-Up Clarification: Elo Range Coverage

**Issue**: KaTrain's `CALIBRATED_RANK_ELO` covers 18k (≈ -22 Elo) to 5d (≈ 1700 Elo).

Yen-Go's 9 levels map to these Go ranks:

| Yen-Go Level | Rank Range | In KaTrain Elo Range? | Elo-Anchor Available? |
|---|---|---|---|
| Novice | 30k–26k | ❌ Below 18k floor | No — log "no data" |
| Beginner | 25k–21k | ❌ Below 18k floor | No — log "no data" |
| Elementary | 20k–16k | ✅ Partial (18k–16k covered) | Yes — partial coverage |
| Intermediate | 15k–11k | ✅ Full | Yes |
| Upper Intermediate | 10k–6k | ✅ Full | Yes |
| Advanced | 5k–1k | ✅ Full | Yes |
| Low Dan | 1d–3d | ✅ Full (1d–3d covered) | Yes |
| High Dan | 4d–6d | ✅ Partial (4d–5d covered) | Yes — partial coverage |
| Expert | 7d–9d | ❌ Above 5d ceiling | No — log "no data" |

**Effective coverage**: 6 of 9 levels (elementary through high-dan, with partial coverage at edges). Novice, beginner, and expert have no Elo anchor.

**User decision**: Accepted. "Just log as no data available."

---

## Key Decisions Locked

| ID | Decision | Impact |
|----|----------|--------|
| D1 | No backward compatibility | All puzzles will be re-enriched with new formula |
| D2 | Remove legacy trap density formula | Single code path, no configuration branching |
| D3 | Add `score_delta` to `Refutation` model | Thread `score_lead` from KataGo through generate_refutations |
| D4 | Hard gate for Elo-anchor | Level will be overridden when Elo-anchor diverges significantly |
| D5 | Elo-anchor unavailable for novice, beginner, expert | Log "no data" and skip comparison |
| D6 | `adj_weight` pattern: deferred to governance (lean A) | KaTrain alignment vs simplicity tradeoff |
