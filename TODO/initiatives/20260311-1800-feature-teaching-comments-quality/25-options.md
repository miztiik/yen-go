# Options: Teaching Comments Quality V3

**Last Updated**: 2026-03-11

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 95 |
| Risk Level | low |
| Research Invoked | No (score ≥ 70, risk low) |

---

## Option Comparison

| Dimension | OPT-1: Incremental Enhancement | OPT-2: Comment Pipeline Refactor |
|-----------|-------------------------------|----------------------------------|
| **Summary** | Add delta gate, almost-correct template, vital-move placement logic, and expanded classifier conditions to the existing V2 architecture. Minimal structural change. | Refactor `generate_teaching_comments()` into a pipeline pattern (detect → gate → classify → assemble) with explicit stage interfaces. |
| **F15 (default template)** | ✅ Expand `refutation_classifier.py` with new conditions; add corresponding templates to `config/teaching-comments.json` | ✅ Same conditions but inside pipeline stages |
| **F16 (vital placement)** | ✅ Modify `generate_teaching_comments()` to suppress root comment when vital move is detected; add `vital_node_index` to return dict | ✅ Same logic, cleaner stage separation |
| **F17 (delta gate)** | ✅ Add `almost_correct_threshold` to config; check delta before `assemble_wrong_comment()`. Below threshold → "almost correct" template | ✅ Same, but delta gate is an explicit pipeline stage |
| **F23 (almost correct)** | ✅ New template condition `almost_correct` in wrong_move_comments config + classifier | ✅ Same |
| **Files modified** | 3 files: `comment_assembler.py`, `teaching_comments.py`, `config/teaching-comments.json` + 1 file: `refutation_classifier.py` | Same 4 files + new `comment_pipeline.py` |
| **Lines changed** | ~60-80 lines across 4 files | ~150-200 lines (new file + refactor) |
| **Test impact** | Add tests to existing test files | Need new pipeline stage tests |
| **YAGNI compliance** | ✅ Minimal change, no new abstractions | ❌ Pipeline abstraction adds complexity for 4 findings |
| **Regression risk** | Low — each finding is independently testable | Medium — refactor touches working code paths |
| **Backward compat** | N/A (user confirmed: no backward compat) | N/A |

---

## Detailed Option Descriptions

### OPT-1: Incremental Enhancement (Recommended)

**Approach**: Add each finding's fix to the existing V2 two-layer architecture. The current code already has clean separation (classifier → assembler → generator); the fixes slot into existing extension points.

**F15: Expand Classifier** (~20 lines in `refutation_classifier.py`):

Add 2-3 new conditions to `CONDITION_PRIORITY` list:
- `opponent_reduces_liberties`: Refutation PV shows liberty reduction without immediate capture
- `self_atari`: Wrong move puts own stones in atari
- `wrong_direction`: Move is on wrong side of the position (e.g., away from vital point)

Add corresponding templates to `config/teaching-comments.json`:
```json
{
  "condition": "opponent_reduces_liberties",
  "comment": "The opponent reduces your liberties at {!xy}."
},
{
  "condition": "self_atari",
  "comment": "This stone ends up in atari."
},
{
  "condition": "wrong_direction",
  "comment": "This move doesn't address the key area."
}
```

**F16: Vital Move Placement** (~15 lines in `teaching_comments.py`):

Modify `generate_teaching_comments()` to:
1. When `vital_result` is detected AND vital move index > 0 (not already the first move):
   - Set `correct_comment = ""` (suppress root comment)
   - Return `vital_node_index` in the result dict so `sgf_enricher.py` knows where to place the comment

**F17 + F23: Delta Gate + Almost Correct** (~25 lines across assembler + config):

1. Add `almost_correct_threshold: 0.05` to `config/teaching-comments.json` under `wrong_move_comments`
2. In `generate_teaching_comments()`, before calling `assemble_wrong_comment()`:
   ```python
   if ref.delta < config.wrong_move_comments.almost_correct_threshold:
       wrong_comments[ref.wrong_move] = assemble_wrong_comment(
           condition="almost_correct", delta=ref.delta, config=tc_config)
   ```
3. Add `almost_correct` template to config:
   ```json
   {"condition": "almost_correct", "comment": "Good move, but there's a slightly better option."}
   ```

**Benefits**: Minimal change, clean extension of existing architecture, independently testable.
**Drawbacks**: `teaching_comments.py` grows slightly. No structural improvement opportunity.

### OPT-2: Comment Pipeline Refactor

**Approach**: Refactor the `generate_teaching_comments()` function into explicit pipeline stages:
1. **Detect** — signal detection + vital move detection
2. **Gate** — confidence gating + delta gating
3. **Classify** — refutation classification
4. **Assemble** — comment assembly for each node

**Benefits**: Cleaner stage separation, easier to add future stages.
**Drawbacks**: 
- YAGNI — the current architecture already has good separation
- Refactoring increases risk (proven code paths change)
- More lines of code, more test surface

---

## Recommendation

**OPT-1 (Incremental Enhancement)** is recommended:

1. **Architecture is already good**: V2 two-layer composition was designed for exactly this kind of extension
2. **Each finding maps to a clear code location**: F15→classifier, F16→generator, F17/F23→assembler+config
3. **KISS/YAGNI**: 4 findings, ~60-80 lines of change. No new abstractions needed.
4. **Independently testable**: Each fix can be unit-tested without coupling
5. **Config-driven**: New conditions and templates go in `config/teaching-comments.json`
