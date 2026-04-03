# Charter: Teaching Comments Quality — V3

**Initiative ID**: `20260311-1800-feature-teaching-comments-quality`
**Last Updated**: 2026-03-11

---

## 1. Problem Statement

The teaching comments system (V2, completed 2026-03-06) uses a two-layer composition architecture: Layer 1 (technique base templates) + Layer 2 (signal overlays). An external expert audit identified the V2 system produces correct but pedagogically suboptimal comments in several dimensions:

- Technique comments explain WHAT the technique is, not WHY this specific move executes it on this board
- Wrong-move default template ("Wrong. The opponent has a strong response.") is uninformative for unclassified refutations
- For multi-move sequences, the teaching comment is placed on Move 1 (setup) rather than the decisive tesuji move
- Wrong-move comments fire regardless of delta magnitude — marginal-loss moves (delta < 5%) get the same "Wrong" as catastrophic blunders
- Available KataGo PV data (move roles, structural info) is unused for richer annotations

## 2. Goals

| ID | Goal | Acceptance Criteria |
|----|------|-------------------|
| G1 | Vital move placement — comment at the decisive moment | For sequences > 3 moves with CERTAIN confidence, comment placed on highest-policy-surprise node, not root |
| G2 | Wrong-move delta gate | Moves with delta < configurable threshold (default 0.05) either suppressed or get distinct "almost correct" template |
| G3 | Refutation technique annotation | Wrong-move comments for classified refutations include the refutation's technique name from config |

## 3. Non-Goals

- LLM-generated contextual comments (violates precision principle)
- Board-specific explanation of WHY a technique works HERE (requires PV-to-prose engine — V4 scope)
- Move role annotation ("Fills the key liberty") from PV node type (requires PV structural parser — V4 scope)
- PV-derived outcome text ("No escape in N moves") on wrong moves (PV truncation risk)

## 4. Stretch Goals (per RC-4)

| ID | Goal | Source |
|----|------|--------|
| S1 | "Almost correct" move template | Ke Jie (GV-4) — moves with delta < 0.05 get "Good move, but there's a slightly better option" instead of binary Wrong/Correct |

## 5. Constraints

- Tools must NOT import from `backend/`
- Config-driven: all comment templates from `config/teaching-comments.json`
- No new external dependencies
- Existing teaching comment tests must continue passing
- One Insight Rule: max one comment per node (vital move placement must suppress root when shifting)

## 6. In-Scope Findings

| ID | Finding | Panel Severity |
|----|---------|---------------|
| F15 | Wrong-move default template uninformative for unclassified refutations | **Medium** |
| F16 | Vital move placement wrong — comment on Move 1 instead of decisive tesuji | **High** |
| F17 | Wrong-move confidence gate missing — marginal-loss moves get "Wrong" | **Medium-High** |
| F23 | No "almost correct" move template (panel-identified) | **Low-Medium** (stretch) |

## 7. Out-of-Scope Findings

| ID | Finding | Reason |
|----|---------|--------|
| F14 | Technique name ≠ mechanism explanation | By-design in V2 Layer 1. Board-specific is a V3+ enhancement requiring PV-to-prose. Medium priority, not addressed here. |
| F18 | Move role annotation unused | Requires PV structural parser. V4 scope. |

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Vital move detection unreliable for complex sequences | Medium | Medium | Guard with CERTAIN confidence + non-truncated PV + policy_surprise threshold |
| Delta threshold causes "silent" wrong moves with no feedback | Low | Medium | "Almost correct" template (S1) fills the gap |
| Suppressing root comment removes useful information | Low | Low | Only suppress when vital node IS different from root AND confidence == CERTAIN |

---

> **See also**:
>
> - [Prior Initiative: Teaching Comments V2](../2026-03-06-feature-teaching-comments-v2/) — Layer architecture (closed out)
> - [Frame Legality Initiative](../20260311-1800-feature-tsumego-frame-legality/) — Parallel initiative
> - [Concepts: Tsumego Frame](../../docs/concepts/tsumego-frame.md) — Frame algorithm
