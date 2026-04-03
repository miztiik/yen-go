# Analysis — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19

## Findings

| f_id | severity | finding | affected_file | impact |
|------|----------|---------|---------------|--------|
| F1 | CRITICAL | "Close" prefix not canonical wrong marker — `infer_correctness_from_comment()` returns None | sgf_enricher.py:345, sgf_correctness.py:78 | Cross-system: downstream tools can't detect wrong branches |
| F2 | HIGH | Tier 3 hint reveals exact first move for tactical puzzles | hint_generator.py:269 | Spoils puzzle answer via hint system |
| F3 | HIGH | `net` tag missing from TAG_PRIORITY (defaults to 99) | technique_classifier.py:54 | Net always loses to capture-race (priority 1) |
| F4 | MEDIUM | Level mismatch `>=` boundary overfires at distance 3 | sgf_enricher.py:462 | Novice overwrite for intermediate puzzles |
| F5 | MEDIUM | No guard against all-almost-correct refutation sets | teaching_comments.py:291, sgf_enricher.py:418 | 9 identical "Close" branches, no contrast |

## Ripple Effects

| impact_id | direction | expected_effect | scope | mitigation |
|-----------|-----------|-----------------|-------|------------|
| R1 | downstream | Frontend correctness detection still works (absence-of-"correct" fallback) | frontend/src/lib/sgf-to-puzzle.ts | No frontend change needed |
| R2 | downstream | Backend pipeline sgf_correctness.py will now recognize "Wrong. Close..." | tools/core/sgf_correctness.py | No change needed — "Wrong" prefix already recognized |
| R3 | lateral | Existing tests for "Close" prefix may need updating | tests/test_teaching_comment_embedding.py | Update test expectations |
| R4 | lateral | TAG_PRIORITY addition may change primary_tag for some puzzles | technique_classifier.py | Test with existing golden puzzles |
| R5 | upstream | Config teaching-comments.json template unchanged | config/teaching-comments.json | Template still outputs "Close..." but enricher now prefixes "Wrong." |
