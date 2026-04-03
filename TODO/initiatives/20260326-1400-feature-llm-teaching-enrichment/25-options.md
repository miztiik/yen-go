# Options Evaluation: Wrong-Move Signal Richness (Q8)

> **Initiative**: 20260326-1400-feature-llm-teaching-enrichment
> **Date**: 2026-03-27
> **Source**: Governance Panel Expert Consultation (Q8: "Which wrong moves should get signals?")

---

## Options Evaluated

### Option A: Minimal Payload

| Component | Included |
|-----------|----------|
| `log_policy` | ✅ |
| `score_lead_rank` | ✅ |
| `delta` (winrate) | ✅ |
| `score_delta` | ❌ |
| `refutation_depth` | ❌ |
| `refutation_pv` | ❌ |
| `refutation_type` | ❌ |
| `ownership_delta_max` | ❌ |
| Instructiveness gate | ❌ |

**Pros**: Simplest, smallest payload, fastest implementation
**Cons**: Insufficient for meaningful Go teaching — a downstream LLM cannot explain WHY a move fails without refutation PV or classification. No score-loss context for close positions.

### Option B: Rich Payload (SELECTED)

| Component | Included |
|-----------|----------|
| `log_policy` | ✅ |
| `score_lead_rank` | ✅ |
| `delta` (winrate) | ✅ |
| `score_delta` | ✅ |
| `wrong_move_policy` | ✅ |
| `refutation_depth` | ✅ |
| `refutation_pv` | ✅ |
| `refutation_type` | ✅ (11 conditions) |
| `ownership_delta_max` | ✅ (conditional: > 0.3) |
| Instructiveness gate | ✅ (with seki exception) |

**Pros**: Sufficient for effective Go teaching. Downstream LLM can explain technique, consequence, reading depth. Score_delta distinguishes "slightly worse" from "catastrophic". Ownership delta shows territory impact. Instructiveness gate filters noise.
**Cons**: More implementation work; needs 3 pipeline data gaps fixed (score_delta, wrong_move_policy propagation; ownership_delta storage)

### Option C: Full Depth Payload

| Component | Included |
|-----------|----------|
| Everything in Option B | ✅ |
| ASCII board representation | ✅ |
| Full ownership heatmap | ✅ |
| Ladder detection signal | ✅ |
| Per-intersection influence map | ✅ |

**Pros**: Maximum information for the most detailed teaching comments
**Cons**: Significantly more complex. ASCII board is LLM-concern (not our job). Ownership heatmap bloats payload. Ladder detection is a separate feature (out of scope). YAGNI violation.

---

## Tradeoff Matrix

| Dimension | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Implementation effort | Low | Medium | High |
| Payload richness | Insufficient | Sufficient | Overkill |
| Pipeline changes needed | 0 gaps | 3 gaps (all verified) | 3+ gaps + new features |
| Teaching quality potential | Poor | Good | Diminishing returns |
| YAGNI compliance | ✅ | ✅ | ❌ |
| Scope creep risk | None | Low | High |

---

## Panel Vote (9/9 → Option B)

| Panel Member | Vote | Key Rationale |
|-------------|------|---------------|
| Cho Chikun (9p) | B | "11-condition refutation_type classifier captures essential Go concepts" |
| Lee Sedol (9p) | B | "refutation_pv enables narrative teaching about reading" |
| Shin Jinseo (9p) | B | "Zero new KataGo queries, log_policy formula well-calibrated" |
| Principal Staff Engineer A | B | "Backward compat excellent; minor task spec gaps only" |
| Principal Staff Engineer B | B | "Research gap analysis thorough with evidence chains" |
| Hana Park (1p) | B | "Zero player-facing changes, template system protected" |
| Dr. David Wu (KataGo) | B | "Existing ownership_delta reuse is sound engineering" |
| Dr. Shin Jinseo (Tsumego) | B | "Seki exception theoretically sound, score_delta complements winrate" |
| (9th panel member) | B | "Rich enough for effective teaching, not overbuilt" |

**Unanimous selection: Option B with 3 required changes (RC-1, RC-2, RC-3)**

---

## Required Changes Applied to Option B

| RC | Requirement | Status |
|----|-------------|--------|
| RC-1 | Seki exception: bypass instructiveness gate when `position_closeness > 0.9` | ✅ Incorporated in plan/tasks |
| RC-2 | Config-driven thresholds for instructiveness gate | ✅ `TeachingSignalConfig` model |
| RC-3 | Conditional ownership emission: only when `ownership_delta_max > 0.3` | ✅ Incorporated in plan/tasks |
