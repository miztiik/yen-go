# Research — Enrichment Lab GUI v4

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-09

---

Full research brief is at: `TODO/initiatives/20260309-research-enrichment-lab-gui-v4-feasibility/15-research.md`

## Summary

**Planning Confidence Score:** 82 (post-research)  
**Risk Level:** low

### Key Findings

1. **KataGo tsumego solving (Q1):** Two distinct paths — *validation* (~80-95% accuracy with existing solution tree) and *position-only solving* (builds tree from scratch via AI-Solve with policy pre-filter + budget cap, less reliable). The user's concern about "playing all around" is mitigated by tsumego frame + komi=0.0 + policy ≥0.03 filter. The GUI should surface the `ac_level` to show which path was taken.

2. **gui_deprecated status (Q2):** Abandoned mid-initiative, not due to technical failure — but user confirmed real deprecation reasons: (a) hybrid browser+bridge architecture mismatch, (b) coordinate/signal bugs between Preact Signals and GhostBan, (c) scope creep into browser-side analysis. Fresh build is correct approach.

3. **Board library (Q3):** GhostBan is validated (goproblems.com uses it). BesoGo (tools/sgf-viewer-besogo/) is an additional candidate, especially for the tree panel. goban (OGS) is too heavy.

4. **Bridge SSE events (Q4):** 15 event types cover all stages. Gap: `katago_analysis` event is start-token only (no move data). To show analysis dots during enrichment, a separate `/api/analyze` call must be triggered after `board_state` event delivers stone data.

### gui_deprecated Deprecation Root Cause (User-Confirmed)

| Cause | Detail |
|-------|--------|
| Hybrid architecture | Tried to be both browser TF.js engine AND Python bridge — constant confusion about which engine was active |
| Coordinate bugs | Preact Signals stored mat[row][col] but GhostBan expects mat[col][row]. Transposition was fragile and caused persistent display bugs |
| Scope creep | GUI recreated analysis capabilities that belong in Python, not browser |
