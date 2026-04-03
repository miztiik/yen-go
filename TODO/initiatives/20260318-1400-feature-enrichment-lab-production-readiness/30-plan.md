# Technical Plan — OPT-1 Phased Activation

> Initiative: `20260318-1400-feature-enrichment-lab-production-readiness`
> Last Updated: 2026-03-20
> Selected Option: OPT-1 (Phased Activation with Conservative Thresholds)
> Addendum: Work Stream K (Log-Report Generation) added 2026-03-20 per GOV-PLAN-REVISE

---

## Selected Option

| plan_id | selected_option | source_gate | status |
|---------|----------------|-------------|--------|
| PL-1 | OPT-1 Phased Activation with Conservative Thresholds | GOV-OPTIONS-APPROVED (Gate 4, unanimous 7/7) | ✅ selected |

---

## Architecture Plan

### Work Stream A: Signal Wiring + Quality Algorithm (G2, G3)

**Current state**: `_build_yx()` writes `d,r,s,u,w`. `_build_yq()` writes `q,rc,hc,ac`. Signals `policy_entropy`, `correct_move_rank`, `trap_density`, `avg_refutation_depth`, `branch_count` are computed but discarded before SGF output.

**Planned changes**:

1. **Extend `_build_yx()`** in `analyzers/sgf_enricher.py`:
   - Add `a:` (avg refutation depth) — computed from `result.refutations` mean depth
   - Add `b:` (branch count) — from `result.difficulty.branch_count`
   - Add `t:` (trap density × 100) — from `result.difficulty.trap_density`

2. **Add `_compute_qk()`** in `analyzers/sgf_enricher.py` or as a dedicated module:
   - Implements panel-validated formula: `0.40*trap + 0.30*norm(avg_depth,0,10) + 0.20*norm(clamp(rank,1,8),1,8) + 0.10*entropy`
   - Visit-count gate: multiply by 0.7 when `total_visits < rank_min_visits`
   - Weights loaded from `config/katago-enrichment.json` `quality_weights` section
   - Returns integer 0-5

3. **Extend `_build_yq()`** to include `qk:{value}` field

4. **Add `quality_weights` section** to `config/katago-enrichment.json`:
   ```json
   "quality_weights": {
     "trap_density": 0.40,
     "avg_refutation_depth": 0.30,
     "correct_move_rank": 0.20,
     "policy_entropy": 0.10,
     "rank_min_visits": 500,
     "rank_clamp_max": 8,
     "avg_depth_max": 10,
     "low_visit_multiplier": 0.7
   }
   ```

### Work Stream B: Observability Propagation (G5, OPP-1)

**Current state**: `policy_entropy` and `correct_move_rank` computed in `estimate_difficulty.py` but stored only on `PipelineContext` — never persisted to `AiAnalysisResult` or `BatchSummary`.

**Planned changes**:

1. Add `policy_entropy: float` and `correct_move_rank: int` fields to `DifficultySnapshot` model
2. Wire stage context → `AiAnalysisResult.difficulty` during assembly stage
3. Extend `BatchSummaryAccumulator.record_puzzle()` with `policy_entropy` and `correct_move_rank` params
4. Extend `BatchSummary` model with aggregate entropy and rank distributions

### Work Stream C: Hinting Consolidation (G4)

**Current state**: Two independent hint systems. Backend `hints.py` (~900 LOC) has safety features (atari gating, structured logging, solution-aware fallback). Lab `hint_generator.py` (~260 LOC) has KataGo signals (detection evidence, level-adaptive, instinct phrases).

**Planned changes**:

1. **Copy (not import)** backend safety features into lab:
   - Atari relevance gating — reimplemented using KataGo position data (lab has stone positions from SGF + engine analysis, doesn't need backend's `Board` class)
   - Depth-gated Tier 3 coordinate hints
   - Solution-aware fallback (`InferenceConfidence` enum + `infer_technique_from_solution()`)
   - `HintOperationLog` structured logging per tier
   - Liberty analysis for capture-race/ko hints

2. **Preserve lab innovations**:
   - KataGo `DetectionResult` evidence for Tier 2
   - Level-adaptive wording (entry/core/strong)
   - Instinct phrase prefix (T15, gated behind `instinct_enabled`)
   - Pipe sanitization in `format_yh_property()`

3. **Result**: Unified `hint_generator.py` with best of both systems. Mark backend hints as superseded in documentation.

### Work Stream D: Feature Activation (G1)

**No code changes required for Phase 0-1a**: these features are activated by config changes.

1. **Phase 0**: Instantiate `ai_solve=AiSolveConfig()` (currently `None`), populate `elo_anchor.calibrated_rank_elo` from KaTrain MIT data
2. **Phase 1a**: Set `PI-1`, `PI-3`, `PI-12` flags to `True` — independent scoring signals
3. **Phase 1b**: Set `noise_scaling`, `forced_min_visits_formula`, `suboptimal_branches.enabled`
4. **Phase 1c**: Set `PI-10`, `PI-11` flags
5. **Phase 2**: Set `PI-2`, `PI-7`, `PI-8`, `PI-9` — requires budget monitoring infrastructure first
6. **Phase 3**: Set `instinct_enabled`, `elo_anchor` activation, `PI-4` — requires golden set calibration

### Work Stream E: Per-Puzzle Diagnostics (G10)

**Current state**: `BatchSummaryAccumulator` tracks aggregate counts. `DisagreementSink` writes JSONL disagreements. No per-puzzle structured diagnostic.

**Planned changes**:

1. **Create `PuzzleDiagnostic` Pydantic model**:
   ```python
   class PuzzleDiagnostic(BaseModel):
       puzzle_id: str
       source_file: str
       timestamp: str
       stages_run: list[str]           # ["parse", "analyze", "validate", ...]
       stages_skipped: list[str]
       signals_computed: dict[str, Any]  # {"policy_entropy": 0.72, "qk": 4, ...}
       goal_stated: str                 # from root comment/puzzle_intent
       goal_inferred: str               # from technique detectors
       goal_agreement: str              # "match" | "mismatch" | "unknown"
       disagreements: list[str]         # types of disagreements found
       errors: list[str]               # errors encountered
       warnings: list[str]             # warnings (non-fatal)
       phase_timings: dict[str, float]  # per-stage wall-clock seconds
       qk_score: int                   # 0-5
       ac_level: int                   # 0-3
       enrichment_tier: int            # 1-3
   ```

2. **Extend `enrich_single()` pipeline** to build diagnostic during enrichment
3. **Write per-puzzle diagnostic** to `.lab-runtime/diagnostics/{run_id}/{puzzle_id}.json`
4. **Extend `BatchSummaryAccumulator`** to aggregate diagnostic summaries
5. **Add `goal_agreement` to `DisagreementSink`** — log mismatches between stated and inferred goals

### Work Stream F: Test Coverage Expansion (G6, OPP-2)

**Planned changes**:
1. Identify which of 28 detector families currently have rotation tests
2. Add multi-orientation test cases for ≥12 additional families using existing `Position.rotate()` + `Position.reflect()` harness
3. Each test: canonical position + 3 rotations + 1 reflection = 5 orientations minimum

### Work Stream G: Debug Artifact Export (G7, OPP-3)

**Planned changes**:
1. Add `--debug-export` CLI flag to `enrich` command
2. When enabled, export per-puzzle: top-5 trap moves with policy/winrate, detector activation matrix (28 detectors × confidence), technique tag priority ordering
3. Output: JSON file in `.lab-runtime/debug/{run_id}/{puzzle_id}.debug.json`
4. Bridge endpoint: `/debug/{puzzle_id}` returning same data

### Work Stream H: Calibration Baseline (G8)

**Planned changes**:
1. Populate `golden-calibration/labels.json` with Cho Chikun answer keys (Method C — published answers)
2. Run calibration script on 95 fixtures × 3 visit counts [500, 1000, 2000]
3. Compute `qk` distribution, instinct accuracy, threshold sensitivity
4. Human spot-check of top/bottom 10% `qk` scores
5. Adjust weights if calibration shows misalignment (config change only)

### Work Stream I: Comprehensive Documentation (G9)

**Strategy**: Distribute content across existing three-tier structure (≤3 levels). Expand `docs/architecture/tools/katago-enrichment.md` as the primary one-stop-shop. Update existing concept/reference docs — don't create duplicates.

**Expand** `docs/architecture/tools/katago-enrichment.md` with these sections:
- Pipeline stages (12 stages: what each does, inputs/outputs)
- Signal formulas (every formula in English + mathematical notation: difficulty composite, qk quality, trap density, policy entropy, correct move rank)
- Refutation analysis (4 phases A-D, 12 PI items, KM optimizations)
- Decisions log (why we made certain decisions, what we dropped, NG items)
- Future work (all deferred items preserved for future pickup)

**Update** existing concept docs (don't duplicate):
- `docs/concepts/quality.md` — add qk definition, panel algorithm, calibration
- `docs/concepts/hints.md` — consolidated 3-tier hint system with lab architecture
- `docs/concepts/teaching-comments.md` — enrichment teaching comment assembly

**Consolidate** config references:
- Merge `docs/reference/enrichment-config.md` INTO `docs/reference/katago-enrichment-config.md` (single canonical config reference)
- Add quality_weights section to merged file

**Update** how-to + meta docs:
- `docs/how-to/tools/katago-enrichment-lab.md` — new CLI flags, diagnostics, debug export
- `docs/architecture/backend/hint-architecture.md` — add supersession note pointing to lab hint docs
- `tools/puzzle-enrichment-lab/AGENTS.md` — updated in same commit as code changes

### Work Stream J: TODO Cleanup + Archive (G11)

**Planned changes**:
1. Identify all enrichment-lab-related initiatives in `TODO/initiatives/` (≥15 initiatives)
2. For each: extract future work items → consolidate into `future-work.md`
3. Move completed/superseded initiative directories to `docs/archive/initiatives/enrichment-lab/`
4. Update `TODO/` to have clean slate for enrichment-lab scope

---

## Data Model and Contract Impact

| dm_id | contract | impact | compatibility |
|-------|----------|--------|---------------|
| DM-1 | YX property format | Additive: new optional fields `a:`, `b:`, `t:` | Backward-compatible — old parsers ignore unknown fields |
| DM-2 | YQ property format | Additive: new `qk:` field | Backward-compatible |
| DM-3 | `DifficultySnapshot` model | Additive: `policy_entropy`, `correct_move_rank` fields | Schema version bump |
| DM-4 | `BatchSummary` model | Additive: entropy/rank aggregates, goal_agreement | Backward-compatible |
| DM-5 | `config/katago-enrichment.json` | Additive: `quality_weights` section | Existing consumers unaffected |
| DM-6 | `hint_generator.py` | Modified: expanded with backend safety features | Module-internal, no external API change |
| DM-7 | `PuzzleDiagnostic` model | New model | No existing consumers |
| DM-8 | `config/katago-enrichment.json` | Additive: `report_generation` section with `enabled`, `execution_profile` | Existing consumers unaffected |
| DM-9 | `cli.py` CLI contract | Additive: 5 new `--log-report*` flags | No existing CLI args affected |
| DM-10 | Log-report output file | New: `enrichment-report-{token}.md` | No existing files affected |

---

## Risks and Mitigations

| risk_id | risk | level | mitigation | owner_goal |
|---------|------|-------|------------|------------|
| R-1 | Hinting consolidation introduces regression in existing hint output | medium | Port backend test scenarios into lab first (TDD). Test against golden-5 fixtures. | G4 |
| R-2 | `qk` formula produces counterintuitive scores | medium | Calibration baseline (G8). Player validation (AC-11). Config-driven weights allow adjustment. | G3, G8 |
| R-3 | Phase 2 budget explosion | medium | Budget ceiling C7 (≤4x). Monitor via BatchSummary.max_queries_per_puzzle. Kill switch: revert config. | G1 |
| R-4 | Per-puzzle diagnostics slow down enrichment | low | Diagnostic write is async/buffered. JSON serialization is negligible vs KataGo query time. | G10 |
| R-5 | Documentation goes stale after creation | low | Each doc page has "Last Updated" date. Cross-ref to source files. AGENTS.md updated in same commit. | G9 |
| R-6 | TODO cleanup loses valuable research | low | Future work items extracted to `future-work.md` before archiving. Git history preserves originals. | G11 |

---

## Rollout Strategy

| rollout_id | step | success_signal |
|------------|------|----------------|
| RO-1 | Work Streams A+B+E first (signals, observability, diagnostics) | Tests pass; enriched SGF has all YX/YQ fields; diagnostics written |
| RO-2 | Work Stream C (hinting consolidation) | Backend hint test scenarios pass in lab; golden-5 hints unchanged or improved |
| RO-3 | Work Stream D Phase 0-1a (safe feature activation) | Tests pass; no behavior regression; budget unchanged |
| RO-4 | Work Streams F+G (tests, debug artifacts) | ≥12 detector families with rotation tests; debug CLI works |
| RO-5 | Work Stream D Phase 1b-1c (engine + text features) | Tests pass; budget delta < 20% |
| RO-6 | Work Stream H (calibration) | Results in .lab-runtime/calibration-results; qk distribution reasonable |
| RO-7 | Work Stream D Phase 2 (budget-sensitive features) | Budget ≤4x verified; tests pass |
| RO-8 | Work Stream D Phase 3 (calibration-gated) | Instinct accuracy ≥ 70%; macro-F1 ≥ 0.85 |
| RO-9 | Work Stream I (comprehensive documentation) | Directory exists; all pages written; formulas explained |
| RO-10 | Work Stream J (cleanup) | TODO initiatives archived; future work preserved |
| RO-11 | AC-11 player validation | 20+ puzzles per qk tier reviewed; quality perception confirmed |

---

## Rollback Strategy

| rollback_id | trigger | action |
|-------------|---------|--------|
| RB-1 | Feature activation causes regression | Revert config JSON to previous values. No code rollback needed. |
| RB-2 | `qk` scores are counterintuitive | Adjust weights in `quality_weights` config. Re-run calibration. |
| RB-3 | Hint consolidation breaks existing hints | Revert `hint_generator.py` to pre-consolidation state from git. |
| RB-4 | Budget explosion in Phase 2 | Disable PI-2/7/8/9 via config. Revert to Phase 1c state. |

---

## Player-Impact Validation

| pv_id | criterion | timing | owner |
|-------|-----------|--------|-------|
| PV-1 | Phase 1c opponent-response phrases are pedagogically coherent | After Phase 1c | G1 |
| PV-2 | `qk` scores match player perception of puzzle quality | Parallel with Phase 3 (AC-11) | G8 |
| PV-3 | Instinct phrases enhance (not confuse) hint experience | After Phase 3 | G4 |

---

## Documentation Plan (Amended — Three-Tier Compliant)

### Files to expand

| doc_id | path | content to add |
|--------|------|----------------|
| D-1 | `docs/architecture/tools/katago-enrichment.md` | Pipeline stages, signal formulas (English + math), refutation analysis, decisions log, future work |

### Files to update

| doc_id | path | why |
|--------|------|-----|
| D-2 | `docs/concepts/quality.md` | Add qk definition, panel algorithm |
| D-3 | `docs/concepts/hints.md` | Consolidated hint architecture |
| D-4 | `docs/concepts/teaching-comments.md` | Enrichment teaching comment assembly |
| D-5 | `docs/reference/katago-enrichment-config.md` | Merge enrichment-config.md content + quality_weights section |
| D-6 | `docs/how-to/tools/katago-enrichment-lab.md` | New CLI flags, diagnostics, debug export |
| D-7 | `docs/architecture/backend/hint-architecture.md` | Add supersession note |
| D-8 | `tools/puzzle-enrichment-lab/AGENTS.md` | Updated in same commit as code changes |
| D-10 | `docs/how-to/tools/katago-enrichment-lab.md` | Add log-report CLI flags, defaults, operator usage |
| D-11 | `docs/architecture/tools/katago-enrichment.md` | Add log-report architecture section (toggle, precedence, non-blocking) |

### Files to remove (after merge)

| doc_id | path | reason |
|--------|------|--------|
| D-9 | `docs/reference/enrichment-config.md` | Content merged into D-5 (single canonical config ref) |

### Cross-references

| xref_id | from | to | purpose |
|---------|------|----|---------|
| X-1 | katago-enrichment.md signal section | katago-enrichment-config.md | Weight keys |
| X-2 | hints.md | hint-architecture.md (backend) | Supersession note |
| X-3 | quality.md | puzzle-quality.json | Config link |
| X-4 | katago-enrichment.md decisions section | 70-governance-decisions.md | Panel rationale |

## Phase Execution Governance

Each phase boundary has a **Phase Gate Review (PGR)**. See `40-tasks.md` for full PGR protocol.

| PGR | Approval Type | Gate Condition |
|-----|---------------|----------------|
| PGR-0 | Executor self-approve | Config + models ready |
| PGR-1 | Executor self-approve | Signals + observability wired |
| PGR-2 | Executor self-approve | Diagnostics wired |
| PGR-3 | Executor self-approve | Hinting consolidated |
| PGR-4a | **Governance-Panel** | Phase 1a-1c activation verified |
| PGR-4b | **Governance-Panel** | Phase 2 budget verified |
| PGR-5 | Executor self-approve | Tests + debug done |
| PGR-6 | **Governance-Panel** | Calibration + Phase 3 verified |
| PGR-7 | Executor self-approve | All docs written |
| PGR-8 | **Governance-Panel (closeout)** | All tasks complete |
| PGR-LR-0 | **Governance-Panel** | Log-report addendum approved, Q17/Q18 resolved |
| PGR-LR-1 | Executor self-approve | Global toggle + precedence contract tested |
| PGR-LR-2 | Executor self-approve | Auto-trigger wired, non-blocking verified |
| PGR-LR-3 | Executor self-approve | Markdown report engine + token coupling validated |
| PGR-LR-4 | Executor self-approve | Production boundary integration contract tested |
| PGR-LR-5 | **Governance-Panel** | Change-magnitude glossary text approved |
| PGR-LR-6 | Executor self-approve | Full tests + docs + validation complete |

---

## Addendum: Work Stream K — Log-Report Generation (Added 2026-03-20)

> Source: GOV-PLAN-REVISE handover. Scope extension to add automated enrichment log report generation.
> Blocking decisions resolved: Q17:A (backend hard-forces OFF), Q18:C (magnitude blocked until governance glossary).

### K.1 Scope & Rationale

The enrichment lab produces structured JSON logs during enrichment runs. Operators currently must manually parse these logs to understand enrichment outcomes. This work stream adds automated markdown report generation that:
- Correlates KataGo request/response pairs from enrichment logs
- Produces a single markdown report per enrichment run
- Auto-triggers at end of enrich and batch commands
- Defaults to ON in lab, OFF in production

### K.2 Architecture

**Global Feature Toggle**:
- New config key: `report_generation.enabled` in `config/katago-enrichment.json`
- New config key: `report_generation.execution_profile` (`lab` | `production`)

**Precedence Resolution** (highest to lowest):
1. CLI explicit `--log-report on|off`
2. Environment variable `YENGO_LOG_REPORT_ENABLED=true|false|auto`
3. Profile policy: `lab` → ON, `production` → OFF
4. Config default: `report_generation.enabled` (safety fallback: OFF)

`auto` resolves to profile-based behavior. Production profile resolves to OFF unless explicit CLI `on`.

**Non-Blocking Reporter**:
- Report generation runs after enrichment pipeline completes
- Reporter failure produces warning + diagnostic info but does NOT fail the enrichment run
- Try/except boundary wraps the entire report generation call

**Filename Token Coupling**:
- Report filename reuses the exact timestamp token from the enrichment log filename
- Pattern: `enrichment-{token}.jsonl` → `enrichment-report-{token}.md`
- Token extraction is deterministic and test-gated

### K.3 Markdown Report Schema (10 Sections)

Single markdown file sections (in order):

| section_id | section | description |
|------------|---------|-------------|
| S1 | Title and run metadata | generated_timestamp, run_id count, trace_id count, source log path(s), report mode (on/off/auto resolved) |
| S2 | Log linkage and paths | Source log file path(s), relative path from workspace root |
| S3 | Summary metrics | Total puzzles, accepted/flagged/error counts, duration, avg KataGo queries per puzzle |
| S4 | Correlated request/response table | Per-puzzle request→response pairs from enrichment log events |
| S5 | Stable glossary and field definitions | Versioned definitions of all report fields and metrics |
| S6 | Policy definitions | Active policy rules for accept/flag/error classification |
| S7 | Win rate interpretation | How to read win rate deltas and threshold meanings |
| S8 | Category terms | Go/tsumego domain terminology used in analysis |
| S9 | Data quality diagnostics | Unmatched requests, unmatched responses, parse warnings, correlation completeness |
| S10 | Change magnitude levels | **GOVERNANCE-BLOCKED** — placeholder until glossary text approved (Q18:C) |

### K.4 CLI Contract

| arg | values | description |
|-----|--------|-------------|
| `--log-report` | `on\|off\|auto` | Enable/disable/auto report generation |
| `--log-report-output` | `<path>` | Override report output directory |
| `--log-report-filter-status` | `accepted,flagged,error` | Filter report rows by enrichment status |
| `--log-report-min-requests` | `N` | Minimum KataGo request count to include puzzle in report |
| `--log-report-include-glossary` | `true\|false` | Include/exclude glossary section in report |

No CSV options. No ASCII table rendering. Markdown-only.

### K.5 Production Boundary Integration Contract

- Backend invokes enrichment lab with `--log-report off` by default (D14, Q17:A)
- Backend MUST hard-force OFF regardless of lab config default
- Boundary enforcement: explicit flag at CLI invocation level, not config inheritance
- No backend-to-lab architecture violation — communication through CLI flags only
- Operator can override with explicit `--log-report on` for debugging

### K.6 Risks and Mitigations (Log-Report Specific)

| risk_id | risk | level | mitigation |
|---------|------|-------|------------|
| R-LR-1 | Accidental production overhead from report generation | medium | Hard production default OFF at boundary (Q17:A) |
| R-LR-2 | Filename token mismatch between log and report | medium | Deterministic token extraction + reuse tests |
| R-LR-3 | Report generation failure causing enrichment failure | high | Non-blocking reporter with try/except + warning (D17) |
| R-LR-4 | Glossary drift causing inconsistent interpretation | medium | Versioned glossary section in report; changes require governance review |
| R-LR-5 | Partially correlated request/response sets causing misleading conclusions | medium | Explicit data-quality section (S9): unmatched requests/responses, parse warnings |

### K.7 Rollback Strategy (Log-Report Specific)

| trigger | action |
|---------|--------|
| Report generation causes any enrichment regression | Set `report_generation.enabled: false` in config |
| Emergency suppression needed | CLI `--log-report off` overrides all defaults |
| Token coupling error | Fix token extraction; report path independent of enrichment path |

### K.8 Phase Gate Sequence (Log-Report)

| PGR | Phase | Gate Condition | Exit Criteria |
|-----|-------|----------------|---------------|
| PGR-LR-0 | Governance Addendum | Q17/Q18 resolved, addendum in artifacts | Governance approve or approve_with_conditions |
| PGR-LR-1 | Global Toggle + Precedence | Toggle works in single+batch paths | Deterministic precedence tests pass |
| PGR-LR-2 | Auto-Trigger Wiring | End-of-run trigger for enrich and batch | Both run types generate report when enabled; none when disabled; reporter failure non-blocking |
| PGR-LR-3 | Markdown Report Engine | Single markdown file with S1-S9 sections | Markdown output validated; ASCII path removed |
| PGR-LR-4 | Production Boundary | Backend-to-lab contract with default OFF | Integration contract documented and tested |
| PGR-LR-5 | Magnitude Section | Governance glossary approved | Approved glossary embedded in markdown report |
| PGR-LR-6 | Validation + Docs | Full tests + docs + operator examples | Review and closeout pass |

---

## Constraints (Inherited from Charter)

| C-ID | Constraint |
|------|-----------|
| C1 | All code inside `tools/puzzle-enrichment-lab/` |
| C2 | No backward compatibility required |
| C3 | Config-driven qk weights |
| C4 | Visit-count gate at 500 |
| C5 | Non-circular calibration (C+A hybrid) |
| C6 | Phased activation sequence |
| C7 | Budget ceiling ≤4x for Phase 2 |
| C8 | Player-visible impact per phase |
| C9 | Threshold conservation |
| C10 | Goal comparison not storage |
| C11 | Definition of done: code + tests + config |

> **See also**:
>
> - [Charter](./00-charter.md) — Goals, constraints, acceptance criteria
> - [Options](./25-options.md) — OPT-1 selected
> - [Tasks](./40-tasks.md) — Dependency-ordered task checklist
> - [Governance](./70-governance-decisions.md) — Gate 4 approved
