# Plan — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Selected Option**: OPT-3 — Layered Composition (Technique Base + Signal Overlay)  
**Last Updated**: 2026-03-06

---

## Architecture

### Two-Layer Comment Generation

```
┌──────────────────────────────────────────────────────────┐
│                   Comment Generator                       │
│                                                          │
│  Input: AiAnalysisResult + enriched solution tree + config│
│                                                          │
│  ┌─────────────────┐     ┌─────────────────────┐        │
│  │   Layer 1        │     │   Layer 2            │        │
│  │   Technique      │     │   Signal             │        │
│  │                  │     │                      │        │
│  │ tag → technique_ │     │ engine signals →     │        │
│  │ phrase            │     │ signal_phrase        │        │
│  │                  │     │                      │        │
│  │ "Snapback        │     │ "this is the vital   │        │
│  │  (uttegaeshi)"   │     │  point at {coord}"   │        │
│  └────────┬─────────┘     └──────────┬───────────┘        │
│           │                          │                    │
│           └──────────┬───────────────┘                    │
│                      ▼                                    │
│           ┌─────────────────────┐                         │
│           │  Assembly            │                         │
│           │                     │                         │
│           │ "{technique} —      │                         │
│           │  {signal}."         │                         │
│           │                     │                         │
│           │ If > 15 words:      │                         │
│           │  signal replaces    │                         │
│           │  mechanism suffix   │                         │
│           │                     │                         │
│           │ If no signal:       │                         │
│           │  emit V1 comment    │                         │
│           └─────────────────────┘                         │
│                                                          │
│  Output: teaching_comments per node → AiAnalysisResult   │
└──────────────────────────────────────────────────────────┘
```

### Implementation Method

All comment generation is **pure Python template substitution**. There is no LLM, no external text generation, no AI writing English prose. Each comment is a short template string with zero or more tokens that Python replaces at enrichment time:

| Token     | Replaces with                                         | Example                                            |
| --------- | ----------------------------------------------------- | -------------------------------------------------- |
| `{!xy}`   | Transform-safe board coordinate (SGF 2-letter format) | `{!cg}` → resolved by frontend after rotation/flip |
| `{alias}` | Specific alias name (e.g. "Bent Four")                | For dead-shapes alias comments                     |

`{!xy}` follows the same convention as the hint system (`YH`) — coordinates are **never hardcoded** as board positions (e.g. "C3") because the frontend rotates and flips the board for display. The frontend resolves `{!xy}` tokens after applying any transform.

---

### Comment Placement

| Node type              | What gets placed           | Layer 1 source                       | Layer 2 source               | Rules                                                |
| ---------------------- | -------------------------- | ------------------------------------ | ---------------------------- | ---------------------------------------------------- |
| First correct move     | Technique + signal comment | Parent tag phrase                    | Signal from engine analysis  | Always (if confidence gate passes)                   |
| Vital move             | Alias + signal comment     | Alias phrase (or parent if no alias) | Signal from engine analysis  | Only when `YO == strict` (GOV-V2-01)                 |
| Wrong move (top 3)     | Causal refutation comment  | —                                    | Refutation classifier output | Max 3 (GOV-V2-04), ranked by refutation depth        |
| Wrong move (remaining) | Default template           | —                                    | —                            | Generic "Wrong. The opponent has a strong response." |
| Forced intermediate    | Nothing                    | —                                    | —                            | Silent (no annotation)                               |

### Signal Detection

| Signal                 | Detection method                                           | Engine data used           | Threshold (configurable)          |
| ---------------------- | ---------------------------------------------------------- | -------------------------- | --------------------------------- |
| `vital_point`          | Ownership map change at move coordinate                    | ownership delta            | `> 0.3`                           |
| `forcing`              | All alternatives classified as wrong                       | correct_alternatives count | `== 0`                            |
| `non_obvious`          | Low policy prior for the correct move                      | policy_prior               | `< 0.05`                          |
| `unique_solution`      | No branching in solution tree                              | alternative_correct_moves  | `== 0`                            |
| `sacrifice_setup`      | Move is not a capture, but next move triggers capture      | move analysis + PV         | PV[0] not capture, PV[1] captures |
| `opponent_takes_vital` | Wrong-move refutation PV move 1 == correct move coordinate | refutation PV              | coordinate match                  |

### Wrong-Move Refutation Classification

Priority order (first-match-wins, GOV-V2-03):

| Priority | Condition              | Template                                                  | Evidence required                            |
| -------- | ---------------------- | --------------------------------------------------------- | -------------------------------------------- |
| 1        | `immediate_capture`    | "This stone is captured immediately."                     | PV depth ≤ 1 + capture verified              |
| 2        | `opponent_escapes`     | "Opponent escapes at {!xy}."                              | Refutation PV shows escape sequence          |
| 3        | `opponent_lives`       | "The opponent makes two eyes and lives."                  | Ownership: dead→alive in refutation          |
| 4        | `capturing_race_lost`  | "Loses the capturing race — opponent has more liberties." | Liberty comparison in refutation             |
| 5        | `opponent_takes_vital` | "Opponent takes vital point {!xy} first."                 | Refutation PV[0] == correct first move coord |
| 6        | `shape_death_alias`    | "This creates a {alias} — unconditionally dead."          | Tag = dead-shapes + alias match              |
| 7        | `ko_involved`          | "This leads to a ko, but the direct solution avoids it."  | Ko detected in PV                            |
| 8        | `default`              | "Wrong. The opponent has a strong response."              | Always matches                               |

### Config Schema (target state)

```json
{
  "$schema": "./schemas/teaching-comments.schema.json",
  "version": "2.0",
  "design_principles": { "..." },
  "correct_move_comments": {
    "snapback": {
      "comment": "Snapback (uttegaeshi) — allow the capture, then recapture the larger group.",
      "technique_phrase": "Snapback (uttegaeshi)",
      "vital_move_comment": "Now recapture — the snapback completes.",
      "hint_text": "Snapback (uttegaeshi)",
      "min_confidence": "HIGH"
    }
  },
  "signal_templates": {
    "vital_point": "vital point {!xy}",
    "forcing": "only move — all alternatives fail",
    "non_obvious": "non-obvious — decisive at {!xy}",
    "unique_solution": "only path to success",
    "sacrifice_setup": "sacrifice now, exploit the response",
    "opponent_takes_vital": "opponent takes vital point {!xy}"
  },
  "assembly_rules": {
    "composition": "{technique_phrase} — {signal_phrase}.",
    "max_words": 15,
    "overflow_strategy": "signal_replaces_mechanism",
    "parenthetical_counting": "Parenthetical Japanese terms count as 1 word (e.g. '(uttegaeshi)' = 1 word)",
    "coord_token": "{!xy} format (SGF 2-letter coordinate, transform-safe — never hardcode board positions)"
  },
  "annotation_policy": {
    "max_correct_node_annotations": 2,
    "vital_move_annotation_scope": "strict_only",
    "alias_placement": "vital_move_preferred",
    "max_causal_wrong_moves": 3,
    "causal_wrong_move_ranking": "refutation_depth_desc"
  },
  "wrong_move_comments": {
    "templates": [
      { "condition": "immediate_capture", "comment": "This stone is captured immediately." },
      { "condition": "opponent_escapes", "comment": "Opponent escapes at {!xy}." },
      { "condition": "opponent_lives", "comment": "The opponent makes two eyes and lives." },
      { "condition": "capturing_race_lost", "comment": "Loses the capturing race — opponent has more liberties." },
      { "condition": "opponent_takes_vital", "comment": "Opponent takes vital point {!xy} first." },
      { "condition": "shape_death_alias", "comment": "This creates a {alias} — unconditionally dead." },
      { "condition": "ko_involved", "comment": "This leads to a ko, but the direct solution avoids it." },
      { "condition": "default", "comment": "Wrong. The opponent has a strong response." }
    ],
    "delta_annotations": {
      "significant_loss": { "threshold": 0.5, "template": "Loses approximately {delta_pct}% of the position." },
      "moderate_loss": { "threshold": 0.2, "template": "Results in a significant disadvantage." }
    }
  }
}
```

**Note (RC-3)**: `delta_annotations` are carried forward unchanged from V1. They complement the causal wrong-move conditions — a wrong move can have BOTH a causal template (from the classifier) AND a delta annotation (from winrate change). No task modifies delta_annotations; they are preserved as-is in the V2 schema.

### Data Model Impact

| Change                                            | Type     | Breaking                |
| ------------------------------------------------- | -------- | ----------------------- |
| `technique_phrase` field per tag entry            | Additive | No                      |
| `vital_move_comment` field per tag entry          | Additive | No                      |
| `signal_templates` new section                    | Additive | No                      |
| `assembly_rules` new section                      | Additive | No                      |
| `annotation_policy` new section                   | Additive | No                      |
| New wrong-move conditions (5 new)                 | Additive | No                      |
| Config version `1.0` → `2.0`                      | Bump     | No (forward-compatible) |
| `hc:3` quality level for signal-enriched comments | Additive | No                      |

### Quality Metric Extension

| hc value | Meaning                  | When                                        |
| -------- | ------------------------ | ------------------------------------------- |
| `hc:0`   | No teaching comment      | Comment suppressed (confidence too low)     |
| `hc:1`   | Correctness markers only | "Correct!" / "Wrong." (V0)                  |
| `hc:2`   | Technique-only comment   | V1 `comment` field, technique label only    |
| `hc:3`   | Signal-enriched comment  | OPT-3 output: technique + signal composited |

---

## Risks and Mitigations

| Risk                               | Severity | Mitigation                                                                                    |
| ---------------------------------- | -------- | --------------------------------------------------------------------------------------------- |
| Assembly produces awkward phrasing | MEDIUM   | Expert review all 28 technique phrases × 6 signal phrases. Iteration based on puzzle output.  |
| 15-word cap truncation             | MEDIUM   | Technique phrases ≤ 4 words. Signal phrases ≤ 10 words. Assembly overflow replaces mechanism. |
| Signal misclassification           | LOW      | Confidence gate + precision-over-emission. V1 fallback when uncertain.                        |
| Shallow refutation trees           | LOW      | Guard: causal wrong-move only when evidence exceeds threshold. Default template fallback.     |

---

## Constraints and Dependencies

| Dependency                          | Status                 | Impact                         |
| ----------------------------------- | ---------------------- | ------------------------------ |
| Phase A (KataGo engine integration) | ✅ Complete            | AiAnalysisResult available     |
| Phase P (benchmarking)              | ✅ Complete            | Accuracy baselines established |
| Phase B.4 test structure            | Defined in 006         | Tests align with B.4.1/B.4.2   |
| `config/teaching-comments.json` V1  | ✅ Complete            | Extend, not replace            |
| 28 canonical tags                   | ✅ In config/tags.json | Template coverage target       |
