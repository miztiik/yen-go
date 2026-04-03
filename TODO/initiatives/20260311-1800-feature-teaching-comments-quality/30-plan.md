# Plan: Teaching Comments Quality V3

**Last Updated**: 2026-03-11
**Selected Option**: OPT-1 (Incremental Enhancement)

---

## 1. Architecture & Design

### 1.1 Approach: Extend Existing V2 Layer Architecture

The V2 two-layer composition (technique_phrase + signal_phrase) already has clean extension points. Each finding maps to a specific code location:

| Finding | Code Location | Change Type |
|---------|--------------|-------------|
| F15 | `refutation_classifier.py` + `config/teaching-comments.json` | Add 2-3 new conditions + templates |
| F16 | `teaching_comments.py` + `sgf_enricher.py` | Suppress root comment + vital node placement |
| F17 | `teaching_comments.py` + `config/teaching-comments.json` | Delta gate before wrong-move assembly |
| F23 | `refutation_classifier.py` + `config/teaching-comments.json` | "almost_correct" condition + template |

### 1.2 F15: Expand Wrong-Move Classifier

Add new conditions to `CONDITION_PRIORITY` in `refutation_classifier.py`:

```python
CONDITION_PRIORITY = [
    "immediate_capture",
    "opponent_escapes",
    "opponent_lives",
    "capturing_race_lost",
    "opponent_takes_vital",
    "opponent_reduces_liberties",  # NEW
    "self_atari",                  # NEW
    "shape_death_alias",
    "ko_involved",
    "wrong_direction",             # NEW (lowest priority before default)
    "default",
]
```

New check functions (~20 lines):

```python
def _check_opponent_reduces_liberties(ref: dict) -> bool:
    """Refutation PV shows liberty reduction (but not immediate capture)."""
    return ref.get("liberty_reduction", False) and not ref.get("capture_verified", False)

def _check_self_atari(ref: dict) -> bool:
    """Wrong move puts own stones in atari."""
    return ref.get("self_atari", False)

def _check_wrong_direction(ref: dict) -> bool:
    """Move is far from the vital area."""
    return ref.get("wrong_direction", False)
```

Add corresponding templates to `config/teaching-comments.json`:

```json
{"condition": "opponent_reduces_liberties", "comment": "The opponent reduces your liberties at {!xy}."},
{"condition": "self_atari", "comment": "This stone ends up in atari."},
{"condition": "wrong_direction", "comment": "This move doesn't address the key area."}
```

### 1.3 F16: Vital Move Placement

**In `teaching_comments.py`** — modify `generate_teaching_comments()`:

When `vital_result` is detected AND `vital_result.move_index > 0` (vital move is not the first move):
1. Set `correct_comment = ""` (suppress root comment per Q2: "only vital node gets comment")
2. Add `vital_node_index` and `vital_comment` to return dict

Guard conditions (MH-6):
- `vital_result` is not None
- `vital_result.move_index > 0` (vital move differs from first move)
- `tag_confidence == "CERTAIN"` (high confidence only)

**In `sgf_enricher.py`** — modify `_embed_teaching_comments()`:

Add `vital_comment` and `vital_node_index` parameters. When provided:
1. Walk the correct solution line to `vital_node_index`
2. Place the vital comment on that node's C[] property
3. Skip the correct_comment on root[0] (already empty from suppression)

### 1.4 F17 + F23: Delta Gate + Almost Correct

**Config change** — add to `wrong_move_comments` in `config/teaching-comments.json`:

```json
"almost_correct_threshold": 0.05
```

And add the template:
```json
{"condition": "almost_correct", "comment": "Good move, but there's a slightly better option."}
```

**In `teaching_comments.py`** — before calling `assemble_wrong_comment()` for each refutation:

```python
almost_threshold = tc_config.wrong_move_comments.almost_correct_threshold
for ref in classification.causal + classification.default_moves:
    if abs(ref.delta) < almost_threshold:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition="almost_correct", delta=ref.delta, config=tc_config)
    else:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition=ref.condition, ...)
```

### 1.5 Threshold Hierarchy Documentation

Document the threshold hierarchy in config:
- `almost_correct_threshold` (0.05) < `refutation_gate` (0.08 in katago-enrichment.json) < wrong_move

---

## 2. Data Model Changes

**`generate_teaching_comments()` return dict** — add fields:
```python
{
    "correct_comment": str,
    "vital_comment": str,
    "vital_node_index": int | None,  # NEW: index in solution tree for vital placement
    "wrong_comments": dict[str, str],
    "summary": str,
    "hc_level": int,
}
```

**Config model** — add `almost_correct_threshold: float` to `WrongMoveComments` config class (in `config/__init__.py` or wherever the config Pydantic model lives).

**`_embed_teaching_comments()` signature** — add optional parameters:
```python
def _embed_teaching_comments(
    sgf_text: str,
    correct_comment: str,
    wrong_comments: dict[str, str],
    vital_comment: str = "",        # NEW
    vital_node_index: int | None = None,  # NEW
) -> str:
```

---

## 3. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Vital move detection unreliable for complex sequences | Medium | Medium | Guard with CERTAIN confidence + non-truncated PV + policy threshold |
| Delta threshold too high → too many "almost correct" | Low | Low | Configurable threshold, default 0.05 validated by governance panel |
| New classifier conditions have no data in engine output | Medium | Low | Conditions only fire when engine data fields are present; graceful no-op |
| sgf_enricher vital node traversal fails on short trees | Low | Low | Guard: if tree shorter than vital_node_index, skip vital placement |

---

## 4. Must-Hold Constraints (from Governance)

| MH-ID | Constraint | Implementation |
|-------|-----------|----------------|
| MH-5 | `almost_correct_threshold` configurable in config | Add to `config/teaching-comments.json` under `wrong_move_comments` |
| MH-6 | Vital move suppresses root ONLY when `vital_node_index > 0` AND `confidence == CERTAIN` | Guard conditions in `generate_teaching_comments()` |
| MH-7 | New conditions in `CONDITION_PRIORITY` with corresponding config templates | 3 new conditions + 3 new templates |

---

## 5. Documentation Plan

| doc_action | file | why_updated |
|-----------|------|-------------|
| update | `config/teaching-comments.json` | New templates, almost_correct_threshold, new conditions |
| update | `docs/concepts/teaching-comments.md` | Document delta gate, almost-correct template, vital placement, new classifier conditions (RC-2 from governance) |

---

## 6. Test Strategy

### Unit Tests

| Test | Finding | File |
|------|---------|------|
| `test_almost_correct_template` | F23 — delta < 0.05 produces "Good move" text | `test_comment_assembler.py` or existing teaching test file |
| `test_delta_gate_suppresses_wrong` | F17 — delta < threshold → "almost correct" instead of "Wrong" | `test_teaching_comments.py` |
| `test_delta_gate_passes_above_threshold` | F17 — delta ≥ 0.05 → normal wrong comment | `test_teaching_comments.py` |
| `test_vital_placement_suppresses_root` | F16 — root comment empty when vital node identified | `test_teaching_comments.py` |
| `test_vital_placement_certain_only` | F16/MH-6 — non-CERTAIN confidence keeps root comment | `test_teaching_comments.py` |
| `test_new_classifier_conditions` | F15 — each new condition fires on matching data | `test_refutation_classifier.py` or existing |
| `test_embed_vital_comment_on_node` | F16 — sgf_enricher places comment on vital node | `test_sgf_enricher.py` |
| `test_almost_correct_threshold_config` | MH-5 — threshold read from config | `test_teaching_comments.py` |
