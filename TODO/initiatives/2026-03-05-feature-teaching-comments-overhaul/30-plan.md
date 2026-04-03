# Plan — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Architecture Decisions

### AD-1: Config file structure (`config/teaching-comments.json`)

The config follows the pattern of `config/go-tips.json` but with comment-specific structure:

```json
{
  "$schema": "./schemas/teaching-comments.schema.json",
  "version": "1.0",
  "description": "Teaching comment templates for SGF solution tree embedding.",
  "design_principles": {
    "precision_over_emission": "Never emit a false, vague, or misleading comment. Suppress when uncertain.",
    "technique_grounded": "Every comment must name the specific technique and its key mechanism.",
    "confidence_gated": "Comments are only emitted when tag classification confidence is HIGH or CERTAIN.",
    "one_insight_rule": "Each comment delivers exactly one actionable insight per move.",
    "student_learning": "Comments exist to teach. Include Japanese/Korean terms where standard. Help the student recognize and name the pattern."
  },
  "correct_move_comments": {
    "snapback": {
      "comment": "Snapback (uttegaeshi) — allow the capture, then recapture the larger group.",
      "hint_text": "Snapback (uttegaeshi)",
      "min_confidence": "HIGH"
    },
    "dead-shapes": {
      "comment": "This shape cannot make two eyes — it is already dead.",
      "hint_text": "Dead shapes",
      "min_confidence": "HIGH",
      "alias_comments": {
        "bent-four": "Bent four in the corner — unconditionally dead.",
        "bulky-five": "Bulky five (guzumi) — dead; the vital point prevents two eyes.",
        "rabbity-six": "Rabbity six — dead; no matter who plays first.",
        "l-group": "L-group (eru-gata) — dead; cannot form two independent eyes.",
        "straight-three": "Straight three (choku-san) — dead on the first line."
      }
    },
    "tesuji": {
      "comment": "Tesuji — a sharp tactical move that exploits a weakness.",
      "hint_text": "Tesuji",
      "min_confidence": "HIGH",
      "alias_comments": {
        "hane": "Hane — bend around the opponent's stone at the key point.",
        "crane's nest": "Crane's nest (tsuru no sugomori) — trap the stones within their own shape.",
        "wedge": "Wedge (warikomi) — insert between the opponent's stones to split them.",
        "tiger's mouth": "Tiger's mouth — a shape that threatens to capture if the opponent enters."
      }
    }
  },
  "wrong_move_comments": {
    "templates": [
      {
        "condition": "pv_depth_lte_1_AND_captures_verified",
        "comment": "This stone is captured immediately.",
        "guard": "Only when PV depth is verified ≥ actual (not truncated)."
      },
      {
        "condition": "ko_involved",
        "comment": "This leads to a ko, but the direct solution avoids it."
      },
      {
        "condition": "default",
        "comment": "Wrong. The opponent has a strong response."
      }
    ],
    "delta_annotations": {
      "significant_loss": {
        "threshold": 0.5,
        "template": "Loses approximately {delta_pct}% of the position."
      },
      "moderate_loss": {
        "threshold": 0.2,
        "template": "Results in a significant disadvantage."
      }
    }
  }
}
```

**Rationale**: Separating `correct_move_comments` and `wrong_move_comments` mirrors the two code paths in `teaching_comments.py`. The `min_confidence` field per tag enables fine-grained gating. Delta annotation thresholds align with existing `config/katago-enrichment.json` teaching section but are co-located with the text for auditability.

### AD-2: Teaching comments vs. production hints (separation preserved)

| System                                  | Purpose                                      | Storage                        | Source of Truth                         |
| --------------------------------------- | -------------------------------------------- | ------------------------------ | --------------------------------------- |
| **Teaching comments** (this initiative) | Post-solve explanation embedded in SGF `C[]` | Solution tree move nodes       | `config/teaching-comments.json`         |
| **Hints (YH)**                          | Pre-solve progressive disclosure             | Root property `YH[h1\|h2\|h3]` | Production `hints.py` `TECHNIQUE_HINTS` |
| **Go tips**                             | Session ambient learning                     | Frontend display               | `config/go-tips.json`                   |

These remain three distinct systems. Teaching comments explain _after_ the move is played. Hints guide _before_ the move. Tips are ambient.

### AD-3: SGF embedding strategy — implementation path

Teaching comments are written as `C[]` properties on specific nodes in the SGF solution tree.

**Current architecture (the gap):**

- `enrich_sgf()` in `sgf_enricher.py` handles Phase 1 (refutation branches) and Phase 2 (root properties). It does NOT touch solution-tree move `C[]`.
- `compose_enriched_sgf()` in `sgf_parser.py` already accepts a `comments` parameter (dict) but `_compose_node()` does not use it.
- `AiAnalysisResult.teaching_comments` already stores `{correct_comment, wrong_comments, summary}` — this data is computed but not wired into SGF output.

**New Phase 3 in `enrich_sgf()`:**

```python
# Phase 3: Teaching comment embedding (solution tree C[] properties)
if result.teaching_comments:
    correct_comment = result.teaching_comments.get("correct_comment", "")
    wrong_comments = result.teaching_comments.get("wrong_comments", {})

    # Embed correct_comment on the first correct move node
    # Embed wrong_comments[move] on each refutation branch root
    sgf_text = _embed_teaching_comments(sgf_text, correct_comment, wrong_comments)
```

**Embedding rules:**

1. **Correct first move**: `C[Snapback (uttegaeshi) — allow the capture, then recapture the larger group.]`
2. **Wrong first moves (refutation branches)**: Already have `C[Wrong. ...]` from Phase 1. Teaching wrong-move comments are appended to existing refutation `C[]` text, not replacing it.
3. **Subsequent correct moves**: No comment added. Only the first correct move gets the teaching comment to avoid redundancy in forced sequences.
4. **Preserved existing comments**: If a correct-move node already has a `C[]` from the source SGF, append with `\n\n` separator (respects `preserve_root_comment` policy). Never overwrite.
5. **Confidence gate**: If `teaching_comments` is empty (suppressed by confidence gate), Phase 3 is a no-op.

**Implementation approach**: Use `sgfmill` to parse → walk solution tree → set `C[]` on target nodes → re-serialize. This is the same library already used by `_apply_patches()`.

### AD-3b: `compose_enriched_sgf` comments parameter — REMOVED

> **Governance decision (GOV-PLAN-CONDITIONAL, Condition 1):** AD-3b is removed. The `comments` parameter on `compose_enriched_sgf()` is dead code (accepted but never used). Phase 3 uses the sgfmill-based `_embed_teaching_comments()` approach from AD-3 instead. The dead `comments` parameter should be cleaned up as part of Phase F legacy removal (T-16).

### AD-4: Confidence gating

```
Tag confidence HIGH or CERTAIN → emit correct_move_comment
Tag confidence MEDIUM           → emit coordinate-only (no teaching text)
Tag confidence LOW              → suppress entirely
```

For wrong-move comments, the guard is PV-quality:

- PV depth verified ≥ 2 AND not truncated → emit specific refutation template
- PV truncated OR depth unknown → emit generic "Wrong. The opponent has a strong response."

### AD-5: Comment tightening — before/after examples

| Tag        | Current (verbose)                                                                                                                                                                                                                           | Proposed (tight)                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `snapback` | "This is a snapback — allow the opponent to capture a stone, then immediately recapture a larger group. The key is recognizing that the capture creates a self-atari for the opponent." (30 words)                                          | "Snapback — allow the capture, then recapture the larger group." (10 words)    |
| `ladder`   | "This involves a ladder (shicho) — chase the opponent's stones diagonally toward the edge. Each atari forces a single response, and the stones cannot escape if the ladder works." (30 words)                                               | "Ladder (shicho) — each atari forces one response toward the edge." (10 words) |
| `ko`       | "This position involves a ko fight. The correct approach starts a ko that is advantageous..." (30+ words)                                                                                                                                   | "Ko fight — start the ko that favors your position." (9 words)                 |
| `throw-in` | "The correct move is a throw-in — a sacrifice stone placed inside the opponent's territory to reduce their liberties or create a false eye. The sacrifice forces the opponent to capture, which changes the position favorably." (37 words) | "Throw-in — sacrifice inside to reduce eye space." (8 words)                   |

**Design principle**: Each comment = `{Technique name} — {one key mechanism}`. Max 15 words. Japanese term in parentheses when standard.

---

## Data Model Impact

- **New file**: `config/teaching-comments.json` (new config file — all 28 tags + alias sub-comments)
- **New file**: `config/schemas/teaching-comments.schema.json` (JSON schema)
- **Modified**: `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` (read from config; remove hardcoded `TECHNIQUE_COMMENTS` and `WRONG_MOVE_TEMPLATES`; add alias-aware lookup)
- **Modified**: `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` (read technique hints from config; remove hardcoded `TECHNIQUE_HINTS` and `REASONING_HINTS`)
- **Modified**: `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` (add Phase 3: embed teaching comments as `C[]` on solution tree nodes)
- **Modified**: `tools/puzzle-enrichment-lab/analyzers/sgf_parser.py` (wire `comments` dict into `_compose_node()` so `compose_enriched_sgf` actually uses it)
- **Modified**: `tools/puzzle-enrichment-lab/config.py` (add TeachingComments config loader)
- **No change**: `tools/puzzle-enrichment-lab/models/ai_analysis_result.py` (uses existing `teaching_comments` field)
- **New file**: `docs/concepts/teaching-comments.md` (documentation)

---

## Risks and Mitigations

| Risk                                                     | Likelihood       | Impact | Mitigation                                                                |
| -------------------------------------------------------- | ---------------- | ------ | ------------------------------------------------------------------------- |
| Config file out of sync with tags.json                   | Medium           | High   | Test: validate all tag slugs in teaching-comments.json exist in tags.json |
| PV truncation causes false "captured immediately" claims | High (known bug) | High   | Guard: only emit capture-specific comments when PV depth verified         |
| Teaching comments redundant with YH hints                | Low              | Medium | Clear separation: hints = pre-solve, teaching = post-solve                |
| Existing test suite breaks after dict removal            | Medium           | Medium | Run full test suite before and after migration                            |
| SGF C[] property conflicts with preserved comments       | Medium           | Medium | Append strategy with separator, never overwrite                           |

---

## Rollout/Rollback

- **Rollout**: Feature-gated via config — `teaching-comments.json` can set `"enabled": false` at top level to suppress all comment emission. Default: enabled.
- **Rollback**: Remove the config file and revert the 3 modified Python files. SGFs already enriched with comments remain valid (C[] is standard SGF).
