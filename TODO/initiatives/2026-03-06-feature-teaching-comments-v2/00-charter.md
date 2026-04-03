# Charter — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Supersedes**: `2026-03-05-feature-teaching-comments-overhaul` (V1 closeout + V2 research)  
**Last Updated**: 2026-03-06

---

## Problem Statement

V1 teaching comments are limited to technique labels on the first correct move only. They tell the student WHAT technique is used ("Snapback — allow capture, then recapture") but not WHY this specific move achieves it or why alternatives fail. The actual tesuji often occurs on move 3 or 5, not move 1 — yet only move 1 gets a comment. Wrong-move feedback is generic ("Wrong. The opponent has a strong response.") regardless of what actually goes wrong.

With KataGo engine access available for all puzzles, teaching comments should:

- Explain the causal logic behind correct and wrong moves
- Annotate the decisive tesuji deeper in the solution tree
- Use position-specific coordinate references
- Convey move quality signals (vital point, forcing, unique solution, non-obvious)

## One-System Principle

**There is no lab vs production distinction for teaching comments.** All puzzles are processed through the lab (which has KataGo). When the lab eventually integrates with the production pipeline, it will be seamless — same code, same config, same output. There is:

- No backward compatibility concern
- No transition period
- No two-tier degradation (Tier 1/Tier 2)
- No conditional code paths based on data availability
- No "backfill" concept

Every puzzle is enriched once, completely. If teaching comments improve, puzzles are re-enriched.

## Goals

1. **Explain WHY moves work/fail** — Causal explanations using engine + tree signals (policy, ownership, winrate delta, PV sequences)
2. **Annotate vital moves** — Comment on the decisive tesuji deeper in the solution tree, not just the first move
3. **Improve wrong-move feedback** — Specific explanations ("The opponent escapes", "This loses the capturing race") based on refutation PV and tree structure
4. **Position-aware comments** — `{!xy}` coordinate tokens for board-specific explanations
5. **Move quality signals** — Vital point, forcing, unique solution, non-obvious — embedded in comment text where engine supports it
6. **Complete coverage** — Every puzzle that passes enrichment gets full teaching comment treatment

## Non-Goals

- Level-specific comment variants (would multiply templates by 9)
- LLM-generated comments at build time (templates only)
- Backward compatibility with V1-only comments
- Partial/phased rollout or transition periods
- Separate lab vs production code paths or configs

## Constraints

| #   | Constraint                                                                             | Source                    |
| --- | -------------------------------------------------------------------------------------- | ------------------------- |
| C1  | One system — KataGo always available, no conditional paths                             | Product owner directive   |
| C2  | Templates with token substitution only, no free-text generation                        | V1 charter                |
| C3  | Config in global `config/teaching-comments.json`                                       | Product owner directive   |
| C4  | 15-word cap per comment                                                                | V1 panel (non-negotiable) |
| C5  | One-insight-rule — one actionable insight per move node                                | V1 panel                  |
| C6  | Precision over emission — suppress when uncertain                                      | V1 panel                  |
| C7  | Confidence gating — HIGH+ for specific techniques, CERTAIN for ambiguous category tags | V1 panel + Section 10 C3  |

## Architecture Principle

```
One system. One generation path. One config.

tools/puzzle-enrichment-lab/
└── phase_b/teaching_comments.py       ← ALL generation logic
    ├── Input: AiAnalysisResult + enriched solution tree + config
    └── Output: teaching_comments field in result JSON

config/teaching-comments.json           ← ALL config (templates, thresholds, policies)

backend/puzzle_manager/
└── core/enrichment/hints.py           ← Reads pre-computed comments from JSON → SGF C[]
```

When the lab integrates with production, the generation logic moves with it. Same code, same config, same output. Seamless.

## Carried-Forward Design Decisions

These decisions from the previous governance rounds remain valid regardless of system architecture:

| ID        | Decision                                                                           | Source           |
| --------- | ---------------------------------------------------------------------------------- | ---------------- |
| GOV-V2-01 | Suppress vital-move annotation when `YO != strict`                                 | Panel Section 10 |
| GOV-V2-02 | General→specific alias progression (parent tag on first move, alias on vital move) | Panel Section 10 |
| GOV-V2-03 | Wrong-move condition priority by immediacy (first-match-wins on ordered array)     | Panel Section 10 |
| GOV-V2-04 | Max 3 causal wrong-move annotations per puzzle, ranked by refutation depth         | Panel Section 10 |
| C4 (old)  | Signal replaces mechanism suffix (`comment_with_signal`), does not append          | Panel Section 10 |

## Acceptance Criteria

1. All 28 canonical tags have technique templates with `{coord}` token support
2. Vital move detection identifies the decisive tesuji in multi-move sequences
3. Wrong-move branches get causal explanations when refutation data provides evidence
4. Comments generated for every enriched puzzle (no partial coverage)
5. 15-word cap respected in all generated comments
6. Config schema validated — all thresholds and policies in `config/teaching-comments.json`
7. Expert review of sample puzzles (≥50) confirms pedagogical quality
8. All tests pass

## Available Data (Every Puzzle)

Since KataGo is always available, every puzzle has:

| Signal                                         | Source            | Available |
| ---------------------------------------------- | ----------------- | --------- |
| Policy prior per move                          | KataGo analysis   | ✅ Always |
| Winrate + winrate delta                        | KataGo analysis   | ✅ Always |
| Principal variation (PV) sequences             | KataGo analysis   | ✅ Always |
| Ownership map                                  | KataGo analysis   | ✅ Always |
| Enriched solution tree (branches, refutations) | AI-Solve pipeline | ✅ Always |
| Tag classification                             | Pipeline tagging  | ✅ Always |
| Complexity metrics (YX)                        | Pipeline analysis | ✅ Always |
| Move order classification (YO)                 | Pipeline analysis | ✅ Always |

No conditional logic needed. All signals available for all puzzles.

> **See also**:
>
> - Previous research: `TODO/initiatives/2026-03-05-feature-teaching-comments-overhaul/15-research.md` (sections 1-6 research findings still valid as factual reference)
> - Phase B.4 scope: `TODO/katago-puzzle-enrichment/006-implementation-plan-final.md` (B.4.1, B.4.2)
> - AI-Solve pipeline: `TODO/ai-solve-enrichment-plan-v3.md` (Step 9: Teaching enrichment)
> - V1 config: `config/teaching-comments.json`
> - V1 concepts doc: `docs/concepts/teaching-comments.md`
