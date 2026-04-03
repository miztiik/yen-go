# Clarifications

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Date**: 2026-03-21

## Resolved Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | HTML only or both HTML+markdown? | A: HTML only / B: Both formats | A: HTML only — simpler, no dual maintenance | D1: HTML only | ✅ resolved |
| Q2 | One file per run or per puzzle? | A: Single file per run / B: One per puzzle | A: Single file — batch uses collapsible sections | D2: Single file per run | ✅ resolved |
| Q3 | Navigation approach? | A: Standalone index.html / B: Embedded per-report nav | A: Standalone shell — decoupled, maintainable | D3: Standalone index.html | ✅ resolved |
| Q4 | Before/after comparison scope? | A: SGF property values / B: Full SGF diff | A: SGF properties — targeted, readable | D4: SGF properties (YG, YT, YQ, YX, YH, YK, YO, YR, YC) | ✅ resolved |
| Q5 | Is backward compatibility required? | A: Yes / B: No | B: No — operator tool, replaces markdown | No backward compatibility | ✅ resolved |
| Q6 | Should old markdown code be removed? | A: Yes / B: Keep alongside | A: Yes — D1 confirmed HTML-only | Remove old markdown code | ✅ resolved |
