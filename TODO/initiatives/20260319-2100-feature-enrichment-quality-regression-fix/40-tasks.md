# Tasks — Enrichment Quality Regression Fix

**Initiative**: `20260319-2100-feature-enrichment-quality-regression-fix`
**Date**: 2026-03-19

## Task List

| task_id | title | files | depends | parallel | est_lines |
|---------|-------|-------|---------|----------|-----------|
| T1 | RC-1: Remove "Close" special-casing, enforce "Wrong." prefix | sgf_enricher.py | — | [P] | ~5 |
| T2 | RC-2: Add tactical tag Tier 3 suppression | hint_generator.py | — | [P] | ~15 |
| T3 | RC-3: Add `net` to TAG_PRIORITY | technique_classifier.py | — | [P] | ~3 |
| T4 | RC-4: Change `>=` to `>` threshold | sgf_enricher.py | — | [P] | ~2 |
| T5 | RC-5: Guard against all-almost-correct refutations | sgf_enricher.py, teaching_comments.py | — | [P] | ~20 |
| T6 | Tests for RC-1 through RC-5 | tests/ | T1-T5 | — | ~80 |
| T7 | Run regression test suite | — | T6 | — | 0 |
| T8 | Update AGENTS.md | AGENTS.md | T1-T5 | — | ~15 |

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T4 | sgf_enricher.py | none | not_started |
| L2 | T2 | hint_generator.py | none | not_started |
| L3 | T3 | technique_classifier.py | none | not_started |
| L4 | T5 | sgf_enricher.py, teaching_comments.py | L1 (same file) | not_started |
| L5 | T6 | tests/ | L1-L4 | not_started |
| L6 | T7 | — | L5 | not_started |
| L7 | T8 | AGENTS.md | L1-L4 | not_started |

Note: L1 and L4 share sgf_enricher.py — sequential execution required.
