# Options — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Last Updated**: 2026-03-06

---

## Planning Confidence Assessment

| Metric                    | Value                                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Planning Confidence Score | 78/100                                                                                                       |
| Risk Level                | medium                                                                                                       |
| Research invocation       | Not needed — previous research (15-research.md §1-6) provides factual evidence; new framing simplifies scope |

Deductions: -10 (template design choices have multiple viable approaches), -12 (interaction between move quality signals, vital move detection, and 15-word cap needs panel judgment)

---

## Context

### What we're designing

A teaching comment generation system that runs during puzzle enrichment with FULL KataGo engine access. Every puzzle gets a complete set of teaching comments — correct-move explanations, vital-move annotations, and causal wrong-move feedback. One system, one pass, one config.

### Available signals (always present for every puzzle)

| Signal                   | Source   | What it tells us                                                          |
| ------------------------ | -------- | ------------------------------------------------------------------------- |
| Policy prior per move    | KataGo   | How "obvious" a move is to the neural network (proxy for human intuition) |
| Winrate delta            | KataGo   | How much each move changes the evaluation                                 |
| Principal Variation (PV) | KataGo   | The engine's expected sequence after each move                            |
| Ownership map            | KataGo   | Which stones are alive/dead/contested                                     |
| Enriched solution tree   | AI-Solve | Full correct + wrong branches with refutations                            |
| Tag classification       | Pipeline | Technique labels (28 canonical tags + aliases)                            |
| Complexity metrics (YX)  | Pipeline | Depth, refutations, solution length, unique responses                     |
| Move order (YO)          | Pipeline | strict / flexible / miai                                                  |

### Carried-forward constraints (from V1 panel + GOV-V2)

| ID        | Constraint                                                               | Status                         |
| --------- | ------------------------------------------------------------------------ | ------------------------------ |
| V1-P1     | 15-word cap per comment                                                  | Non-negotiable                 |
| V1-P2     | One-insight-rule (one actionable insight per node)                       | Non-negotiable                 |
| V1-P3     | Precision-over-emission (suppress when uncertain)                        | Non-negotiable                 |
| V1-P4     | Confidence gate: HIGH for specific techniques, CERTAIN for category tags | Carry forward, panel re-review |
| GOV-V2-01 | Suppress vital-move annotation when `YO != strict`                       | Carry forward, panel re-review |
| GOV-V2-02 | General→specific alias progression (parent→alias)                        | Carry forward, panel re-review |
| GOV-V2-03 | Wrong-move priority by immediacy (first-match-wins ordered array)        | Carry forward, panel re-review |
| GOV-V2-04 | Max 3 causal wrong-move annotations, ranked by refutation depth          | Carry forward, panel re-review |
| GOV-C4    | Signal replaces mechanism suffix (`comment_with_signal`)                 | Carry forward, panel re-review |

---

## Option Comparison

### OPT-1: Template-First with Engine Signal Enrichment

**Approach**: Start from the existing 28 technique templates. Add `{coord}` token support, `comment_with_signal` variants, and a signal detection layer that classifies each move's quality (vital point, forcing, unique, non-obvious) from engine data. Templates are the primary generation unit; engine signals select which template variant to emit.

**Generation flow**:

```
1. Tag classification → select primary technique template
2. Engine signal detection → classify move quality (vital/forcing/unique/non-obvious)
3. Template selection:
   - If signal detected AND comment_with_signal exists → use signal-enriched template
   - Else → use base technique template
4. Token substitution → replace {coord}, {alias}, {opponent_move} tokens
5. Placement → first correct move + vital move (if YO=strict) + wrong moves
```

**Template schema extension (per tag)**:

```json
{
  "snapback": {
    "comment": "Snapback (uttegaeshi) — allow the capture, then recapture the larger group.",
    "comment_with_signal": {
      "vital_point": "Snapback (uttegaeshi) — this is the vital point that triggers recapture.",
      "forcing": "Snapback (uttegaeshi) — the only response, forcing the recapture.",
      "non_obvious": "Snapback (uttegaeshi) — the key move that sets up the recapture."
    },
    "vital_move_comment": "Now recapture — the snapback (uttegaeshi) is complete.",
    "hint_text": "Snapback (uttegaeshi)",
    "min_confidence": "HIGH"
  }
}
```

| Criterion                   | Assessment                                                                                                                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Benefits**                | Builds on existing 28-tag config. Predictable output. Each template is individually reviewable. Signal enrichment is additive — template works even if signal detection is uncertain.                   |
| **Drawbacks**               | Template proliferation: 28 tags × 4 signal variants × vital_move = up to ~168 template strings. Maintenance burden. Some combinations may feel forced ("Endgame — this is the vital point" is awkward). |
| **Complexity**              | Medium — config extension + signal classifier + template selector                                                                                                                                       |
| **Test impact**             | One test per tag × signal variant. ~100+ unit tests for template correctness.                                                                                                                           |
| **Rollback**                | Safe — remove `comment_with_signal` fields, revert to base `comment`. Config-only rollback.                                                                                                             |
| **Architecture compliance** | Config-driven, extends existing pattern. No new abstraction layer.                                                                                                                                      |
| **Risk**                    | Template quality varies across signal×tag combinations. Some will be natural ("Snapback — vital point"), others forced ("Joseki — vital point").                                                        |

---

### OPT-2: Signal-Driven Comment Assembly

**Approach**: Instead of starting from technique templates and adding signals, start from the ENGINE SIGNAL as the primary classifier. What does the engine tell us about this move? Map that signal to a comment structure. The technique name is embedded as context, not as the frame.

**Generation flow**:

```
1. Engine signal detection → primary signal (vital_point / forcing / non_obvious / sacrifice / captures)
2. Technique lookup → get tag name and Japanese term
3. Comment assembly → signal-specific template with technique context
   Example: "The vital point at {coord} — {technique_name} decides the group's fate."
4. Token substitution → coordinates, technique names, alias names
5. Placement → first correct move + vital move (if rules allow) + wrong moves
```

**Template schema (signal-oriented)**:

```json
{
  "move_quality_templates": {
    "vital_point": {
      "comment": "The vital point at {coord} — {technique} decides the outcome.",
      "min_policy_threshold": 0.01,
      "requires": "ownership_change > 0.3"
    },
    "forcing_only_move": {
      "comment": "The only move — all alternatives lose immediately.",
      "requires": "correct_alternatives == 0"
    },
    "non_obvious": {
      "comment": "A surprising {technique} at {coord} — low intuitive probability but decisive.",
      "requires": "policy_prior < 0.05"
    },
    "sacrifice_setup": {
      "comment": "{technique} ({japanese}) — sacrifice first, then exploit the response.",
      "requires": "move_is_capture == false AND next_move_is_capture == true"
    }
  },
  "technique_fallback": {
    "description": "When no strong engine signal matches, fall back to technique template",
    "uses": "correct_move_comments from existing V1 config"
  }
}
```

| Criterion                   | Assessment                                                                                                                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Benefits**                | Signal is the primary frame — comments directly answer "why is this move good?" not just "what technique is this?" More natural language. Fewer templates (signal count × 1 template, not tag count × signal count). Technique name is a parameter, not the frame. |
| **Drawbacks**               | Breaks from existing V1 template-per-tag model. More reliance on engine signal correctness. If signal detection is wrong, the comment is misleading (vs OPT-1 where fallback is always safe). V1 config structure changes significantly.                           |
| **Complexity**              | Medium-high — new signal taxonomy, new template structure, technique name as parameter                                                                                                                                                                             |
| **Test impact**             | Tests per signal type × edge cases. Signal detection needs calibration tests against reference puzzles.                                                                                                                                                            |
| **Rollback**                | Harder — config schema change. Would need V1 fallback path.                                                                                                                                                                                                        |
| **Architecture compliance** | New template schema. More powerful but larger migration from V1.                                                                                                                                                                                                   |
| **Risk**                    | Signal misclassification produces worse comments than V1 (technique-only is always safe; "vital point" on a non-vital move is misleading). Needs strong confidence gates.                                                                                          |

---

### OPT-3: Layered Composition (Technique Base + Signal Overlay)

**Approach**: Decompose comment generation into two independent layers that compose at assembly time. Layer 1 is the technique comment (what technique). Layer 2 is the signal overlay (why this move). Each layer is independently generated, tested, and configured. The assembly step composes them under the 15-word cap.

**Generation flow**:

```
1. Layer 1: Technique layer
   - Tag → technique template (existing V1 model, enhanced with aliases)
   - Output: technique phrase ("Snapback (uttegaeshi)")

2. Layer 2: Signal layer
   - Engine signals → signal phrase ("this is the vital point at {coord}")
   - Independent of technique — purely about move quality

3. Assembly:
   - Compose: "{technique_phrase} — {signal_phrase}" if combined ≤ 15 words
   - If over 15 words: signal_phrase replaces mechanism suffix (GOV-C4)
   - If no signal: use full V1 technique template as-is

4. Vital move: Layer 1 uses vital_move_comment or alias. Layer 2 carries over.
5. Wrong moves: Separate wrong-move layer with refutation signal templates.
```

**Config schema (additive, backward-compatible)**:

```json
{
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
    "vital_point": "this is the vital point at {coord}",
    "forcing": "the only move — all alternatives fail",
    "non_obvious": "an unexpected but decisive move at {coord}",
    "unique_solution": "the only path to success"
  },
  "assembly_rules": {
    "composition": "{technique_phrase} — {signal_phrase}.",
    "max_words": 15,
    "overflow_strategy": "signal_replaces_mechanism"
  },
  "wrong_move_comments": { "...": "..." }
}
```

| Criterion                   | Assessment                                                                                                                                                                                                                                                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Benefits**                | Clean separation of concerns — technique and signal are independently testable. Backward-compatible config extension. V1 comments are preserved as fallback (no signal = V1 output). Signal templates are tag-agnostic (4-6 templates, not 28×4). Assembly rules are explicit and configurable. |
| **Drawbacks**               | Composition can produce awkward phrasing when technique + signal don't mesh naturally. The assembly step itself needs testing. Two layers = more moving parts than OPT-1's single lookup.                                                                                                       |
| **Complexity**              | Medium — two independent layers + assembly step                                                                                                                                                                                                                                                 |
| **Test impact**             | Layer 1 tests (tag→phrase). Layer 2 tests (signal→phrase). Assembly tests (compose + word cap + overflow). More focused tests, fewer combinatorial explosions than OPT-1.                                                                                                                       |
| **Rollback**                | Trivial — remove signal_templates section, assembly falls back to V1 `comment` field.                                                                                                                                                                                                           |
| **Architecture compliance** | Extends existing config, no new abstraction layer, composable.                                                                                                                                                                                                                                  |
| **Risk**                    | 15-word cap constraint may force aggressive truncation. Some technique+signal combinations may read awkwardly. Need Go expert review of composed output.                                                                                                                                        |

---

## Tradeoff Matrix

| Criterion               | OPT-1 Template-First                             | OPT-2 Signal-Driven                         | OPT-3 Layered Composition                 |
| ----------------------- | ------------------------------------------------ | ------------------------------------------- | ----------------------------------------- |
| **Template count**      | ~168 (28 tags × 6 variants)                      | ~6-10 signal templates                      | ~28 technique phrases + ~6 signal phrases |
| **Maintenance burden**  | High                                             | Low                                         | Medium                                    |
| **Fallback safety**     | ✅ Strong (base template always safe)            | ⚠️ Weak (signal-first, misleading if wrong) | ✅ Strong (no signal = V1 output)         |
| **Comment naturalness** | Good for common combos, forced for rare ones     | Natural (signal-framed)                     | Depends on assembly quality               |
| **Config migration**    | Additive                                         | Breaking change                             | Additive                                  |
| **15-word cap**         | Per-template (author controls)                   | Per-template (author controls)              | Assembly enforces (may truncate)          |
| **Test complexity**     | High (combinatorial)                             | Medium (signal tests)                       | Medium (layer + assembly)                 |
| **Rollback ease**       | Config field removal                             | Schema revert                               | Config field removal                      |
| **B.4 alignment**       | Closest to B.4 design (28 templates + generator) | Diverges from B.4                           | Compatible with B.4                       |

---

## Recommendation

**OPT-3 (Layered Composition)** strikes the best balance:

- Fewest templates to maintain (34 total vs 168 for OPT-1)
- Safe fallback to V1 output when no signal is available or uncertain
- Backward-compatible config extension
- Each layer independently testable by Go experts
- Clean separation answers both "what technique?" and "why this move?"
- Assembly rules are configurable without code changes
- Aligns with GOV-C4 (signal replaces mechanism suffix) naturally

OPT-1 is the most conservative choice if template proliferation is acceptable. OPT-2 is the most ambitious but has the highest risk from signal misclassification.

**Recommendation candidate**: OPT-3, with OPT-1 as safety fallback if composition quality issues surface during expert review.
