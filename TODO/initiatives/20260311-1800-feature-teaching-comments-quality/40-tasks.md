# Tasks: Teaching Comments Quality V3

**Last Updated**: 2026-03-12
**Selected Option**: OPT-1 (Incremental Enhancement)

---

## Task Graph

| Task | Title | File(s) | Depends On | [P]arallel | Status |
|------|-------|---------|------------|------------|--------|
| T1 | Add `almost_correct_threshold` to config model | `config.py` | — | [P] with T2 | ✅ completed |
| T2 | Add `almost_correct` template + 3 new condition templates to config JSON | `config/teaching-comments.json` | — | [P] with T1 | ✅ completed |
| T3 | Add 3 new classifier conditions + check functions | `analyzers/refutation_classifier.py` | T2 | | ✅ completed |
| T4 | Add delta gate logic in `generate_teaching_comments()` | `analyzers/teaching_comments.py` | T1, T3 | | ✅ completed |
| T5 | Add vital-move root suppression in `generate_teaching_comments()` | `analyzers/teaching_comments.py` | — | [P] with T3 | ✅ completed |
| T6 | Add `vital_node_index` to return dict | `analyzers/teaching_comments.py` | T5 | | ✅ completed |
| T7 | Update `_embed_teaching_comments()` for vital node placement | `analyzers/sgf_enricher.py` | T6 | | ✅ completed |
| T8 | Update `enrich_sgf()` to pass vital params to embedder | `analyzers/sgf_enricher.py` | T7 | | ✅ completed |
| T9-T14 | Unit tests (original plan) | tests | T3-T8 | [P] | see remediation below |
| T15 | Regression: run existing teaching comment tests | — | T4, T5, T7 | | ✅ completed |
| T16 | Update `docs/concepts/teaching-comments.md` | `docs/concepts/teaching-comments.md` | T15 | | ✅ completed |

---

## Test Remediation Tasks (added 2026-03-12, post-implementation review)

Gov review identified 10 planned tests not implemented across three test files.

| Task | Title | File(s) | Finding | [P]arallel | Status |
|------|-------|---------|---------|------------|--------|
| T9a | Test `_check_opponent_reduces_liberties` fires + doesn't fire | `tests/test_refutation_classifier.py` | F15 | [P] | ✅ completed |
| T9b | Test `_check_self_atari` fires + doesn't fire | `tests/test_refutation_classifier.py` | F15 | [P] | ✅ completed |
| T9c | Test `_check_wrong_direction` fires + doesn't fire | `tests/test_refutation_classifier.py` | F15 | [P] | ✅ completed |
| T10a | Test delta gate: abs(delta) < 0.05 → almost_correct | `tests/test_teaching_comments.py` | F17 | [P] | ✅ completed |
| T10b | Test delta gate: abs(delta) >= 0.05 → normal condition | `tests/test_teaching_comments.py` | F17 | [P] | ✅ completed |
| T11a | Test vital root suppression: CERTAIN + move_index > 0 | `tests/test_teaching_comments.py` | F16/MH-6 | [P] | ✅ completed |
| T11b | Test vital guard: non-CERTAIN preserves root comment | `tests/test_teaching_comments.py` | F16/MH-6 | [P] | ✅ completed |
| T12a | Test `_embed_teaching_comments()` vital node in SGF | `tests/test_sgf_enricher.py` | F16 | | ✅ completed |
| T13a | Test `assemble_wrong_comment(condition="almost_correct")` | `tests/test_comment_assembler.py` | F23 | [P] | ✅ completed |
| T14a | Test `almost_correct_threshold` read from config | `tests/test_teaching_comments_config.py` | MH-5 | [P] | ✅ completed |

---

## Task Details

### T1: Config Model Update
Add `almost_correct_threshold: float = 0.05` to the wrong_move_comments config model/dataclass.

Location: Find the config class that models `wrong_move_comments` — likely in `tools/puzzle-enrichment-lab/config/__init__.py` or a Pydantic model.

### T2: Config JSON Update
In `config/teaching-comments.json`, add:

Under `wrong_move_comments`:
```json
"almost_correct_threshold": 0.05
```

Add to `templates` array (in priority order):
```json
{"condition": "opponent_reduces_liberties", "comment": "The opponent reduces your liberties at {!xy}."},
{"condition": "self_atari", "comment": "This stone ends up in atari."},
{"condition": "wrong_direction", "comment": "This move doesn't address the key area."},
{"condition": "almost_correct", "comment": "Good move, but there's a slightly better option."}
```

### T3: Classifier Expansion
In `refutation_classifier.py`:

1. Add `"opponent_reduces_liberties"`, `"self_atari"`, `"wrong_direction"` to `CONDITION_PRIORITY` (before `default`)
2. Add check functions:
   - `_check_opponent_reduces_liberties(ref)` → `ref.get("liberty_reduction", False) and not ref.get("capture_verified", False)`
   - `_check_self_atari(ref)` → `ref.get("self_atari", False)`
   - `_check_wrong_direction(ref)` → `ref.get("wrong_direction", False)`
3. Wire into `classify_refutation()` function's condition cascade

### T4: Delta Gate
In `generate_teaching_comments()`, modify the wrong_comments assembly loop:

```python
almost_threshold = tc_config.wrong_move_comments.almost_correct_threshold

for ref in classification.causal:
    if abs(ref.delta) < almost_threshold:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition="almost_correct", delta=ref.delta, config=tc_config)
    else:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition=ref.condition, coord=ref.refutation_coord,
            alias=ref.alias, delta=ref.delta, config=tc_config)

for ref in classification.default_moves:
    if abs(ref.delta) < almost_threshold:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition="almost_correct", delta=ref.delta, config=tc_config)
    else:
        wrong_comments[ref.wrong_move] = assemble_wrong_comment(
            condition="default", delta=ref.delta, config=tc_config)
```

### T5: Vital Move Root Suppression
In `generate_teaching_comments()`, after vital_result detection:

```python
vital_node_index = None
if vital_result and vital_result.move_index > 0 and tag_confidence == "CERTAIN":
    correct_comment = ""  # Suppress root — vital node gets the comment
    vital_node_index = vital_result.move_index
```

### T6: Return Dict Extension
Add `vital_node_index` to return dict:
```python
return {
    "correct_comment": correct_comment,
    "vital_comment": vital_comment,
    "vital_node_index": vital_node_index,
    "wrong_comments": wrong_comments,
    "summary": summary,
    "hc_level": hc_level,
}
```

### T7: SGF Enricher Vital Embedding
Update `_embed_teaching_comments()` signature and implementation:
- Add `vital_comment: str = ""` and `vital_node_index: int | None = None` parameters
- When both are provided, walk the correct solution line (main line from root[0]) to `vital_node_index` and place the vital comment there
- Guard: if tree is shorter than `vital_node_index`, skip vital placement

### T8: Wire in enrich_sgf
In `enrich_sgf()` Phase 3, extract `vital_comment` and `vital_node_index` from `tc` dict and pass to `_embed_teaching_comments()`.

### T15: Regression
Run all existing teaching comment tests to verify no behavior change on non-affected code paths.

---

## Test Remediation Details

### T9a: Test `_check_opponent_reduces_liberties` (F15)
**File:** `tests/test_refutation_classifier.py`
**Class:** `TestClassifyRefutation`

The `_ref()` helper needs 2 new kwargs: `liberty_reduction` and `self_atari`. Add them with `False` defaults to stay backward-compatible.

```python
# Positive test:
def test_opponent_reduces_liberties_classified(self):
    ref = _ref(liberty_reduction=True)
    result = classify_refutation(ref, "cc", ["life-and-death"])
    assert result.condition == "opponent_reduces_liberties"

# Negative test (field absent → default):
def test_opponent_reduces_liberties_not_without_data(self):
    ref = _ref()  # liberty_reduction defaults to False
    result = classify_refutation(ref, "xx", ["life-and-death"])  # no other conditions fire either
    assert result.condition == "default"

# Guard: capture_verified=True overrides (higher priority):
def test_liberty_reduction_with_capture_uses_capture(self):
    ref = _ref(liberty_reduction=True, capture_verified=True, refutation_depth=1)
    result = classify_refutation(ref, "cc", ["life-and-death"])
    assert result.condition == "immediate_capture"  # higher priority
```

### T9b: Test `_check_self_atari` (F15)
**File:** `tests/test_refutation_classifier.py`

```python
def test_self_atari_classified(self):
    ref = _ref(self_atari=True)
    result = classify_refutation(ref, "cc", ["life-and-death"])
    assert result.condition == "self_atari"

def test_self_atari_not_without_data(self):
    ref = _ref()  # self_atari defaults to False
    result = classify_refutation(ref, "xx", ["life-and-death"])
    assert result.condition == "default"
```

### T9c: Test `_check_wrong_direction` (F15)
**File:** `tests/test_refutation_classifier.py`

```python
def test_wrong_direction_classified(self):
    ref = _ref(wrong_direction=True)
    result = classify_refutation(ref, "cc", ["life-and-death"])
    assert result.condition == "wrong_direction"

def test_wrong_direction_not_without_data(self):
    ref = _ref()  # wrong_direction defaults to False
    result = classify_refutation(ref, "xx", ["life-and-death"])
    assert result.condition == "default"
```

**Important:** The `_ref()` helper must be updated to accept and pass through `liberty_reduction=False`, `self_atari=False`, `wrong_direction=False`.

### T10a: Test Delta Gate Below Threshold (F17)
**File:** `tests/test_teaching_comments.py`
**Class:** New `TestDeltaGate` class

```python
def test_delta_below_threshold_produces_almost_correct(self):
    """F17: abs(delta) < 0.05 → almost_correct template."""
    analysis = _make_analysis(
        refutations=[{
            "wrong_move": "D4", "delta": 0.03,
            "refutation_depth": 3, "refutation_type": "unclassified",
        }]
    )
    result = generate_teaching_comments(analysis, ["life-and-death"])
    assert "Good move" in result["wrong_comments"]["D4"]
    assert "Wrong" not in result["wrong_comments"]["D4"]
```

### T10b: Test Delta Gate Above Threshold (F17)
```python
def test_delta_above_threshold_passes_through(self):
    """F17: abs(delta) >= 0.05 → normal wrong-move comment."""
    analysis = _make_analysis(
        refutations=[{
            "wrong_move": "D4", "delta": 0.06,
            "refutation_depth": 3, "refutation_type": "unclassified",
        }]
    )
    result = generate_teaching_comments(analysis, ["life-and-death"])
    assert "Good move" not in result["wrong_comments"]["D4"]
```

### T11a: Test Vital Root Suppression with CERTAIN (F16/MH-6)
**File:** `tests/test_teaching_comments.py`
**Class:** New `TestVitalMovePlacement` class

Requires a mock/fixture where `detect_vital_move()` returns a result with `move_index > 0`. The simplest approach: provide `analysis["solution_tree"]` with a multi-move sequence so vital detection fires.

```python
def test_vital_suppresses_root_when_certain(self):
    """F16/MH-6: root comment empty, vital_node_index set."""
    analysis = _make_analysis()
    analysis["solution_tree"] = [
        {"move": "cc", "correct": True},
        {"move": "dd", "correct": True, "vital": True},
    ]
    result = generate_teaching_comments(
        analysis, ["snapback"], tag_confidence="CERTAIN"
    )
    # When vital detected at index > 0 with CERTAIN:
    assert result["correct_comment"] == ""
    assert result["vital_node_index"] is not None
    assert result["vital_node_index"] > 0
```

Note: If `detect_vital_move()` doesn't fire on this fixture shape, patch it via `unittest.mock.patch`.

### T11b: Test Vital Guard: Non-CERTAIN Preserves Root (F16/MH-6)
```python
def test_vital_non_certain_preserves_root(self):
    """MH-6: non-CERTAIN confidence keeps root comment."""
    analysis = _make_analysis()
    analysis["solution_tree"] = [
        {"move": "cc", "correct": True},
        {"move": "dd", "correct": True, "vital": True},
    ]
    result = generate_teaching_comments(
        analysis, ["snapback"], tag_confidence="HIGH"  # NOT CERTAIN
    )
    assert result["correct_comment"] != ""
    # vital_node_index should be None or not set
    assert result.get("vital_node_index") is None
```

### T12a: Test Embed Vital Comment on SGF Node (F16)
**File:** `tests/test_sgf_enricher.py` or `tests/test_teaching_comment_embedding.py`

Build a minimal SGF with a 3-move correct line. Call `_embed_teaching_comments()` with `vital_comment="Decisive tesuji"` and `vital_node_index=2`. Parse the result back and verify:
- Root's first child (correct line) does NOT have the vital comment
- Node at depth 2 in the main line has `C[]` containing `"Decisive tesuji"`

```python
def test_embed_vital_comment_on_deeper_node(self):
    sgf = "(;GM[1]SZ[19]PL[B];B[cc];W[dd];B[ee])"  # 3-move correct line
    result = _embed_teaching_comments(
        sgf, correct_comment="",
        wrong_comments={},
        vital_comment="Decisive tesuji",
        vital_node_index=2,
    )
    # Parse result and verify comment placement
    game = sgfmill_sgf.Sgf_game.from_bytes(result.encode())
    root = game.get_root()
    # Node at index 2 = root[0][0] (main line, 2nd child)
    node = root[0]  # move 1
    node = node[0]  # move 2 (vital_node_index=2)
    assert "Decisive tesuji" in node.get_raw("C").decode()
```

### T13a: Test Almost-Correct Template Assembly (F23)
**File:** `tests/test_comment_assembler.py`
**Class:** `TestAssembleWrongComment`

Add `almost_correct` template to the `_make_config()` fixture, then test:

```python
def test_almost_correct_template(self):
    cfg = _make_config()  # must include almost_correct template
    result = assemble_wrong_comment(condition="almost_correct", config=cfg)
    assert "Good move" in result
    assert "slightly better" in result
```

**Important:** The `_make_config()` helper's `templates` list must include:
```python
WrongMoveTemplate(condition="almost_correct", comment="Good move, but there's a slightly better option."),
```

### T14a: Test Almost-Correct Threshold From Config (MH-5)
**File:** `tests/test_teaching_comments_config.py`
**Class:** `TestTeachingCommentsConfigLoader`

```python
def test_almost_correct_threshold_from_config(self):
    """MH-5: almost_correct_threshold is read from config."""
    cfg = load_teaching_comments_config()
    assert hasattr(cfg.wrong_move_comments, "almost_correct_threshold")
    assert cfg.wrong_move_comments.almost_correct_threshold == 0.05
```
