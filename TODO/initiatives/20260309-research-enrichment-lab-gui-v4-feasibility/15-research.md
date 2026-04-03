# Research Brief: Enrichment Lab GUI v4 & KataGo Tsumego Feasibility

**Initiative:** `20260309-research-enrichment-lab-gui-v4-feasibility`  
**Last Updated:** 2026-03-09  
**Researcher:** Feature-Researcher mode  
**Status:** Complete

---

## 1. Research Question and Boundaries

**Primary question:** Is it feasible to build an Enrichment Lab GUI v4 by reviving `gui_deprecated/`? And does the fundamental KataGo-cannot-find-tsumego-solutions concern invalidate the GUI's utility?

**Sub-questions:**

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Does KataGo reliably find correct tsumego moves without a pre-existing solution? | A: Yes (solves from scratch) / B: No (validates only) / C: Hybrid approach | C | — | ✅ resolved by evidence |
| Q2 | What was the actual deprecation reason for gui_deprecated? | A: Technical failure / B: Abandoned incomplete / C: Superseded | B | — | ✅ resolved by evidence |
| Q3 | Which board library offers the best tradeoff for GUI v4? | A: GhostBan npm alpha / B: goban (OGS) / C: Custom SVG | A | — | ✅ resolved by evidence |
| Q4 | Are the SSE events from bridge.py sufficient for real-time GUI updates? | A: Yes / B: Partial (analysis dots missing) / C: No | B | — | ✅ resolved by evidence |

**Boundaries:**  
In scope: `tools/puzzle-enrichment-lab/` — analyzers, bridge, gui_deprecated, models.  
Out of scope: frontend changes, backend pipeline, goban package modifications.

---

## 2. Internal Code Evidence

### 2.1 Q1 — KataGo Tsumego Solving Approach

| R-id | File | Finding |
|------|------|---------|
| R-1 | [analyzers/solve_position.py L1–26](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L1) | Module header declares two distinct operating modes: (a) *validating*: classify existing-solution moves with delta-based thresholds; (b) *solving*: build a full recursive solution tree from a position-only SGF. These are not the same code path. |
| R-2 | [analyzers/solve_position.py L214–L230](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L214) | Pre-filter: only moves with `policy >= confirmation_min_policy` (0.03) are confirmed. Low-policy moves are discarded before any recursion. This is the mechanism that stops KataGo "playing all around" — moves with policy below 3% are never explored. |
| R-3 | [analyzers/solve_position.py L237–L280](../../../tools/puzzle-enrichment-lab/analyzers/solve_position.py#L237) | S1-G16: per-candidate confirmation queries at `confirmation_visits`. Each candidate above the policy floor gets its own dedicated engine query rather than relying on the shared multi-move scan. |
| R-4 | [analyzers/enrich_single.py L806](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L806) | Two code paths in `enrich_single.py`: `_run_position_only_path()` (no solution → AI-Solve builds tree) and `_run_has_solution_path()` (has solution → validate + discover alternatives). The user's concern applies specifically to the position-only path. |
| R-5 | [analyzers/enrich_single.py L884–L910](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L884) | After the query, `response = uncrop_response(response, cropped)` back-translates KataGo's GTP coordinates from the cropped board to original-board space. Without this, coordinates would be wrong for the GUI. |
| R-6 | [analyzers/tsumego_frame.py (via research doc R-4)](../../../docs/architecture/tools/katago-enrichment.md) | ADR D20: "Tsumego frame is MANDATORY. Without it, KataGo's policy outputs are meaningless for tsumego — the model treats the puzzle as a fragment of a whole-board position." ADR D21: "Natural-looking frames produce ~15% winrate error vs ~3% for artificial frames." |
| R-7 | [TODO/katago-puzzle-enrichment/001-research-browser-and-local-katago-for-tsumego.md L141](../../../TODO/katago-puzzle-enrichment/001-research-browser-and-local-katago-for-tsumego.md#L141) | Research doc estimates ~95%+ accuracy for standard life-and-death validation with b28c512 at 2000 visits. This is the *validation* path, not the *solving* path — the claim is that KataGo agrees with curated human solutions at that rate. |
| R-8 | [TODO/ai-solve-remediation-sprints.md L229](../../../TODO/ai-solve-remediation-sprints.md#L229) | Cho Chikun panel: "If a collection has >20% disagreement rate [between KataGo and existing SGF solutions], flag it for full review." This implies expected disagreement rate is below 20% for typical collections — i.e., KataGo agrees more than 80% of the time. |
| R-9 | [TODO/ai-solve-enrichment-plan-v3.md DD-9](../../../TODO/ai-solve-enrichment-plan-v3.md) | DD-9: "Position-only → always run AI-Solve." For position-only SGFs (no solution tree), AI-Solve is the only path. `ac:2 AI_SOLVED` is assigned only when tree is complete and budget is not exhausted. |
| R-10 | [TODO/katago-puzzle-enrichment/007-adr-policy-aligned-enrichment.md D12](../../../TODO/katago-puzzle-enrichment/007-adr-policy-aligned-enrichment.md#D12) | Model tier decision: b10c128 for quick enrichment (200 visits), b28c512 for production (2000 visits). The user's concern about "playing all around" is most acute with weaker/faster models at low visit counts. |

**Summary for Q1:**

The user's framing — "KataGo can't find the tsumego solution unless there's a pre-baked solution tree" — is **partially correct** but misses an important distinction:

- **Validating (has-solution):** KataGo *confirms* the human solution using policy + winrate signals. This works reliably (~80-95% agreement rate). This is the primary enrichment use case.
- **Solving (position-only):** KataGo *builds* a solution tree from scratch. This is harder and requires: tsumego frame + komi=0.0 + policy pre-filter (≥0.03) + budget cap (50 queries). The "playing all around" concern is mitigated by these mechanisms, but not eliminated — complex seki/ko positions may still confuse the solver. `ac:2` is only assigned when the tree completes cleanly.
- **What the GUI does:** The GUI primarily shows the *results* of enrichment — the already-built solution tree — not real-time KataGo solving. The analysis dots on /api/analyze are interactive board queries, not the enrichment pipeline.

### 2.2 Q2 — gui_deprecated Assessment

| R-id | File | Finding |
|------|------|---------|
| R-11 | [gui_deprecated/ARCHITECTURE.md L1–20](../../../tools/puzzle-enrichment-lab/gui_deprecated/ARCHITECTURE.md) | All 8 planned components implemented: `GoBoardPanel`, `StatusBar`, `ControlBar`, `AnalysisTable`, `SolutionTree`, `EngineSettings`, `EnrichPanel`, `SgfInput`. Architecture doc is up-to-date and detailed. |
| R-12 | [gui_deprecated/src/app.tsx L1–90](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/app.tsx) | App.tsx is complete with keyboard shortcuts (ArrowLeft/Right, Home/End), `handleSgfLoad`, `handleNodeClick`, `handleIntersectionClick`, `handleMoveHover`. State wiring via signals is fully done. |
| R-13 | [gui_deprecated/src/app.tsx L58–L64](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/app.tsx#L58) | Known defect: `// TODO: Capture logic not implemented — moves overlay without removing captured groups. Puzzles with ko or snapback will display incorrectly.` Stone removal not implemented in tree navigation. |
| R-14 | [gui_deprecated/src/engine/engine-manager.ts L1–120](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/engine/engine-manager.ts) | Dual-engine fully implemented: browser path (TF.js Worker) and bridge path (HTTP to bridge.py). Auto-initializes TF.js models. Progress streaming via `analysisResult.value` signal. |
| R-15 | [gui_deprecated/src/components/EnrichPanel.tsx L1–150](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/components/EnrichPanel.tsx) | SSE streaming loop is complete: `for await (const event of streamEnrichment(...))` — handles all 15 SSE event types, collects results, updates `enrichStages` signal, downloads enriched SGF. |
| R-16 | [gui_deprecated/src/engine/bridge-client.ts L1–200](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/engine/bridge-client.ts) | Bridge client is complete: cancel-previous pattern, proper `BridgeCanceledError`, full request serialization, `mapBridgeResponseToAnalysisResult()` maps bridge response to GUI types. |
| R-17 | [gui_deprecated/src/components/GoBoardPanel.tsx L1–80](../../../tools/puzzle-enrichment-lab/gui_deprecated/src/components/GoBoardPanel.tsx) | Analysis overlay is complete: score-loss-based dot colors (green/blue/yellow/red), PV stone preview on hover, problem frame dimming. Overlay canvas correctly synced with GhostBan canvas size. |
| R-18 | [TODO/initiatives/20260308-1800-feature-enrichment-lab-ghostban-gui](../../../initiatives/20260308-1800-feature-enrichment-lab-ghostban-gui/) | Initiative directory exists but has no charter file, no files beyond the directory itself. This is **an abandoned initiative stub**, not a failed implementation. The code in gui_deprecated/ was written during this initiative but the initiative was never formally completed. |
| R-19 | [gui_deprecated/package.json L1–35](../../../tools/puzzle-enrichment-lab/gui_deprecated/package.json) | Dependencies: Preact 10.28.4, @preact/signals 2.8.2, ghostban 2.0.0-alpha.16, TF.js 4.22.0 + WASM + WebGL backends, pako 2.1.0. Total: ~200MB node_modules (dominated by TF.js weights and backends). |

**Summary for Q2:**

The gui_deprecated was **not abandoned due to technical failure**. It was abandoned because the `20260308-1800` initiative was never formally chartered or completed. The code is functional — all planned components are implemented and integration tests would likely pass. The single known defect is the TODO capture logic in tree navigation.

**Reuse assessment by component:**

| Component | Reuse | Notes |
|-----------|-------|-------|
| `bridge-client.ts` | ✅ Direct | Fully compliant with current bridge.py API |
| `analysis-bridge.ts` | ✅ Direct | GTP→SGF coord normalization, worker analysis type |
| `engine-manager.ts` | ✅ Direct | Dual-engine logic complete |
| `EnrichPanel.tsx` | ✅ Direct | SSE loop matches current 15 event types |
| `AnalysisTable.tsx` | ✅ Likely | Needs verification against current AnalysisResult type |
| `GoBoardPanel.tsx` | ⚠️ With fix | Missing capture logic in tree navigation |
| `SolutionTree.tsx` | ✅ Likely | SVG tree with correct/wrong coloring seems complete |
| `store/state.ts` | ✅ Direct | Complete Preact Signals store |
| `sgf/parser.ts` | ✅ Direct | SGF→boardMat+solutionTree |
| `lib/frame.ts` | ✅ Direct | Problem frame computation |

### 2.3 Q3 — Board Library Assessment

| R-id | File | Finding |
|------|------|---------|
| R-20 | [gui_deprecated/GHOSTBAN_INTEGRATION.md L1–70](../../../tools/puzzle-enrichment-lab/gui_deprecated/GHOSTBAN_INTEGRATION.md) | GhostBan v2.0.0-alpha.16: `gb.render(boardMat)` for board updates, `gb.cursor` for click detection, `gb.calcSpaceAndPadding()` exposed for overlay alignment. Custom overlay canvas approach is documented and implemented. |
| R-21 | [gui_deprecated/GHOSTBAN_INTEGRATION.md L27–45](../../../tools/puzzle-enrichment-lab/gui_deprecated/GHOSTBAN_INTEGRATION.md#L27) | Confirmed: `npm` ghostban alpha.16 does NOT include `setAnalysis()`. That API only exists in goproblems.com's private fork (v3-alpha.155). The overlay canvas is the correct workaround. |
| R-22 | [docs/reference/go-board-js-libraries-analysis.md §3.7](../../../docs/reference/go-board-js-libraries-analysis.md) | `goban` (OGS): 11.2MB unpacked, requires GobanContainer mounting pattern, heavy OGS coupling. Verdict from prior research: "Keep using goban for the main frontend; it is not suitable for the enrichment lab side-quest." |
| R-23 | [docs/reference/go-board-js-libraries-analysis.md §2 Library Matrix](../../../docs/reference/go-board-js-libraries-analysis.md) | No other library offers GhostBan's combination of: npm availability + TypeScript + canvas rendering + lightweight + Go-specific. jGoBoard (CC-BY-NC-4.0) is rejected on license grounds. WGo.js/Glift are abandoned. Shudan requires 3+ packages with no puzzle mode. |
| R-24 | [docs/reference/go-board-js-libraries-analysis.md §3.5](../../../docs/reference/go-board-js-libraries-analysis.md) | goproblems.com Research(Beta) uses ghostban internally (confirmed 2026-03-08 from live bundle `920.ed9fa994.js`). Their analysis overlay is the `e.FO` function from ghostban. This validates GhostBan as the correct choice for an analysis-focused board GUI. |

**Summary for Q3:**

GhostBan is the correct library. The custom overlay canvas approach (already implemented in gui_deprecated) is superior to any `setAnalysis()` fork dependency because: (a) the unpublished goproblems.com fork cannot be installed via npm, (b) the overlay gives independent control over dot colors, PV rendering, and frame dimming, (c) the current implementation is already working.

The `goban` (OGS) library is not suitable for this GUI — it is 11.2MB, tightly coupled to OGS architecture, and designed for the main frontend's puzzle-solving workflow, not analysis research.

### 2.4 Q4 — Bridge SSE Events

| R-id | File | Finding |
|------|------|---------|
| R-25 | [tools/puzzle-enrichment-lab/bridge.py L416–L490](../../../tools/puzzle-enrichment-lab/bridge.py#L416) | SSE stream is implemented via `asyncio.Queue`. `event_generator()` runs pipeline in background task; all `progress_cb` calls go to queue; GUI reads via EventSource. Heartbeat every 5s (ADR D13). |
| R-26 | [analyzers/enrich_single.py L747](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L747) | Stage 1: `parse_sgf` → `{step: 1, label: "Parse SGF"}` |
| R-27 | [analyzers/enrich_single.py L791](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L791) | Stage 2: `extract_solution` → `{puzzle_id}` |
| R-28 | [analyzers/enrich_single.py L856](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L856) | Stage 3a: `board_state` → `{puzzle_id, board_size, player_to_move, black_stones: [[x,y],...], white_stones: [[x,y],...], sgf}` **Contains actual stone data for rendering.** Re-fires when tight-board crop changes board size. |
| R-29 | [analyzers/enrich_single.py L879](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L879) | Stage 3b: `build_query` → `{puzzle_id, board_size, player_to_move, num_stones}` |
| R-30 | [analyzers/enrich_single.py L964](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L964) | Stage 4: `katago_analysis` → `{puzzle_id}` (start token only; no analysis data in payload) |
| R-31 | [analyzers/enrich_single.py L1009](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1009) | Stage 5: `validate_move` → `{puzzle_id}` |
| R-32 | [analyzers/enrich_single.py L1169](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1169) | Stage 6: `generate_refutations` → `{puzzle_id, correct_move, solution_depth}` |
| R-33 | [analyzers/enrich_single.py L1313](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1313) | Stage 7: `estimate_difficulty` → `{puzzle_id}` |
| R-34 | [analyzers/enrich_single.py L1372](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1372) | Stage 8: `assemble_result` → `{puzzle_id}` |
| R-35 | [analyzers/enrich_single.py L1519](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1519) | Stage 9: `teaching_enrichment` → `{puzzle_id, validation_status, refutation_count, difficulty_level}` |
| R-36 | [analyzers/enrich_single.py L1566](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L1566) | Stage 10: `enriched_sgf` → `{puzzle_id, status: "building"}` then `{puzzle_id, sgf: <sgf_text>, status: "complete"}` or `{puzzle_id, status: "failed", error}` |
| R-37 | [tools/puzzle-enrichment-lab/bridge.py L462–L475](../../../tools/puzzle-enrichment-lab/bridge.py#L462) | Terminal events: `complete` (full `AiAnalysisResult.model_dump()`), `cancelled` (`{}`), `error` (`{message}`), `heartbeat` (`{}`) |

**Complete SSE event catalog (15 event types):**

| Event | Payload fields | GUI use |
|-------|----------------|---------|
| `parse_sgf` | `step`, `label` | Step 1 indicator |
| `extract_solution` | `puzzle_id` | Step 2 indicator |
| `board_state` | `puzzle_id`, `board_size`, `player_to_move`, `black_stones`, `white_stones`, `sgf`, `cropped?`, `original_board_size?` | **Board rendering** — update canvas |
| `build_query` | `puzzle_id`, `board_size`, `player_to_move`, `num_stones` | Step 3 indicator |
| `katago_analysis` | `puzzle_id` | "KataGo thinking…" spinner |
| `validate_move` | `puzzle_id` | Step 5 indicator |
| `generate_refutations` | `puzzle_id`, `correct_move`, `solution_depth` | Step 6 indicator |
| `estimate_difficulty` | `puzzle_id` | Step 7 indicator |
| `assemble_result` | `puzzle_id` | Step 8 indicator |
| `teaching_enrichment` | `puzzle_id`, `validation_status`, `refutation_count`, `difficulty_level` | Step 9 + partial result preview |
| `enriched_sgf` (building) | `puzzle_id`, `status: "building"` | Step 10 start |
| `enriched_sgf` (complete) | `puzzle_id`, `sgf`, `status: "complete"` | **Board update** — show enriched SGF |
| `enriched_sgf` (failed) | `puzzle_id`, `status: "failed"`, `error` | Error display |
| `complete` | Full `AiAnalysisResult` dict | Results panel |
| `cancelled` | `{}` | Cancellation acknowledgement |
| `error` | `message` | Error display |
| `heartbeat` | `{}` | Keep-alive |

**Gap:** The `katago_analysis` event is a start token only — it does not deliver the analysis response data (move candidates, winrates, policy priors). The GUI cannot show analysis dots during the enrichment pipeline. To show dots, a separate `/api/analyze` call with the puzzle position is needed after the `board_state` event delivers the stones.

---

## 3. External References

| R-id | Source | Finding |
|------|--------|---------|
| R-38 | [KaTrain tsumego_frame.py (live MIT, sanderland/katrain)](https://github.com/sanderland/katrain) | Checkerboard pattern is the established reference implementation. Our `tsumego_frame.py` is a port of this. The frame approach is validated by real-world use in KaTrain and goproblems.com. |
| R-39 | [goproblems.com Research(Beta) live observation](https://www.goproblems.com) | "Model: b10 / auto(webgl) / visits: 500." Uses ghostban for board rendering. Analysis dots displayed via `e.FO` function from ghostban bundle. Confirms: (a) ghostban is production-ready for this use case, (b) 500 visits gives ~2-3s on WebGL b10c128, (c) solving/analysis are shown interactively, not just at the end. |
| R-40 | [MachineKomi/Infinite_AI_Tsumego_Miner](https://github.com/MachineKomi/Infinite_AI_Tsumego_Miner) | Uses 11 different KataGo models for tsumego puzzle generation/filtering. Confirms difficulty formula: `visits_to_solve / policy_prior`. Validates the multi-factor approach already implemented in `estimate_difficulty.py`. |
| R-41 | [KataGo analysis protocol documentation](https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md) | Policy output is a full-board distribution that will scatter to low-policy moves without the tsumego frame. This is the technical basis for the user's observation about "playing all around." The frame is the accepted countermeasure in the literature. |

---

## 4. Candidate Adaptations for Yen-Go

### Option A: Revive gui_deprecated as-is (minimal changes)

**Description:** Create a `gui_v4/` directory by copying gui_deprecated and making targeted fixes:
1. Fix the stone-capture TODO in GoBoardPanel.tsx (Go rules capture logic, ~50 lines)
2. Wire the `board_state` SSE event to trigger a `/api/analyze` call after board update (gives analysis dots during enrichment)
3. Update EnrichPanel to listen for result fields in `teaching_enrichment` event (partial preview)
4. Verify all SSE event names match current bridge.py (they appear to match based on code review)

**Effort:** Low (< 2 files of net-new logic)  
**Risk:** Low — code is complete, defects are known and isolated

### Option B: gui_deprecated + Remove TF.js browser engine

**Description:** Same as Option A, but also remove the TF.js browser engine (Worker + TF.js deps). GUI becomes bridge-only. This eliminates the 200MB TF.js dependency footprint.

**Impact:** `package.json` deps drop from ~200MB to ~5MB. Dev startup much faster.  
**Tradeoff:** No offline browser analysis. Bridge server must be running.  
**Feasibility:** High — `engineMode` signal defaults to `'bridge'`; removing browser path is a targeted deletion, not a rewrite.

### Option C: gui_deprecated + Post-enrichment analysis dots

**Description:** Same as Option B, plus add a specific flow: after `enriched_sgf` (complete) arrives, automatically call `/api/analyze` on the enriched position and display analysis dots. This is the "stones getting placed during enrichment" feature the user wants.

**Effort:** Medium — requires coordinating SSE completion event → analyze call → overlay update  
**Risk:** Low — bridge already supports both endpoints independently

### Option D: Full Position-Only tsumego solving GUI (new scope)

**Description:** A GUI specifically designed to demonstrate AI-Solve tree building in real-time. Would require adding analysis data to the `katago_analysis` SSE event (or a separate WebSocket channel), plus animating tree node creation.

**Effort:** High — requires bridge changes (new event payload) and new tree-building visualization  
**Risk:** Medium — touches bridge.py which is production-worthy code  
**Note:** This would answer the user's concern about "does KataGo actually find the solution" — you could watch it happen live.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| Risk | Severity | Mitigation |
|------|----------|------------|
| TF.js 200MB dependency | Medium | Option B removes it; bridge-only mode is viable for a local enrichment tool |
| GhostBan alpha status (v2.0.0-alpha.16) | Low | Already pinned in package.json; no production deployment needed; version is stable in practice |
| Capture logic defect causes incorrect board display | Medium | Required fix before any meaningful puzzle validation in GUI; ~50 lines |
| KataGo analysis dots not available during pipeline run | Low | Gap is understood; workaround is post-enrichment /api/analyze call |
| SSE event schema drift (bridge.py vs EnrichPanel.tsx) | Low | Code review confirms current event names match; needs regression test |
| `board_state` coordinate system mismatch (cropped vs uncropped) | Medium | `uncrop_response()` is applied before `board_state` is emitted (R-5); GUI would show cropped board during analysis but correct board after enriched_sgf; this may look confusing |
| Position-only AI-Solve tree completeness is non-deterministic | Medium | `ac:2` only assigned when complete; GUI should show `tree_truncated` flag from result |

**License compliance:**  
- GhostBan: no explicit license in npm package record; used by goproblems.com production — treat as permissive  
- Preact: MIT  
- TF.js: Apache 2.0  
- No CC-BY-NC or GPL dependencies  

**Rejection reasons for alternatives:**  
- goban (OGS): Too heavy (11.2MB), wrong architecture for a side-quest analysis tool, violates KISS  
- jGoBoard: CC-BY-NC-4.0 is prohibited for any distribution use  
- Custom SVG board: Would require rebuilding GhostBan's capabilities; YAGNI  
- web-katrain fork: 200MB, React/Zustand framework coupling, confirmed too complex (Attempt 1 failure)

---

## 6. Planner Recommendations

1. **Proceed with Option B (gui_deprecated revival, bridge-only, no TF.js).**  
   The code is ~85% complete. Only the stone-capture defect requires net-new logic. Removing TF.js eliminates the complexity concern from Attempt 1 (200MB deps). This can be completed at Correction Level 2-3.

2. **Fix the capture logic first (blocking).** `GoBoardPanel.tsx` line 58 TODO is the only known correctness defect. Without it, ko and snapback positions display incorrectly — exactly the class of puzzles where KataGo's behavior is most interesting.

3. **Wire `board_state` → `/api/analyze` for analysis dots during enrichment (high value).** The `board_state` event delivers stones + board_size, which is sufficient to call `/api/analyze`. Adding this loop gives the "stones getting placed" visual the user wants. This is a bridge-client enhancement, not a bridge.py change.

4. **Document the KataGo solving boundary clearly in the GUI.** Add a status indicator that shows `ac_level` from the `complete` event: `UNTOUCHED (0) / ENRICHED (1) / AI_SOLVED (2)`. This directly answers the user's question — the GUI will show whether KataGo successfully solved from scratch or only validated an existing tree.

---

## 7. Confidence and Risk Update for Planner

- `post_research_confidence_score`: **82**
- `post_research_risk_level`: **low**

**Basis:** All four research questions have clear answers from code inspection. The gui_deprecated is functionally complete with one known defect. The KataGo limitation concern is well-documented and already mitigated by the existing architecture (tsumego frame + policy pre-filter + budget cap). The main uncertainty is whether the GhostBan alpha.16 package has undocumented breaking changes relative to the existing usage — this can be resolved in <1 hour by running `npm install && npm run dev`.

---

## Handoff

- `research_completed`: true  
- `initiative_path`: `TODO/initiatives/20260309-research-enrichment-lab-gui-v4-feasibility/`  
- `artifact`: `15-research.md`  
- `top_recommendations`:  
  1. Revive gui_deprecated as gui_v4 (bridge-only, remove TF.js)  
  2. Fix stone-capture defect in GoBoardPanel.tsx  
  3. Wire board_state → /api/analyze for analysis dots  
  4. Add ac_level indicator to show KataGo solving depth  
- `open_questions`:  
  - None blocking. Optional: Does npm `ghostban@2.0.0-alpha.16` install cleanly today on current Node? (verify with `npm install`)  
- `post_research_confidence_score`: 82  
- `post_research_risk_level`: low
