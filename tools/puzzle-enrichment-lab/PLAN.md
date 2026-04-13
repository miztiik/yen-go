# Puzzle Enrichment Lab — Plan

## Status: Stable, Post-Cleanup (2026-04-12)

Core KataGo pipeline (stages 1-7) is stable and well-tested. Heuristic teaching system (stages 8-11) works but is scheduled for eventual replacement by the LLM Teaching Agent (`tools/llm-teaching-agent/`).

## Recent Changes (2026-04-12 Audit)

### Phase A: Dead Code Cleanup
Removed ~4,700 lines of dead code across 11 files:
- 7 dead scripts: `debug_integration.py`, `render_debug.py`, `mini_calibration.py`, `check_conflicts.py`, `expert_review.py`, `analyzers/validate_solution.py`, `result.json`
- 3 dead test files: root `test_allowmoves.py`, `tests/test_tsumego_frame.py` (100% skipped), `tests/test_remediation_sprints.py` (duplicate)
- 1 stale copy: `gui/bridge.py`

### Phase B: Pipeline Stabilization
- Migrated SGF handling from `sgfmill` to native `core/sgf_parser.py` (KaTrain-derived)
- Upgraded `teaching_signals` payload to v2 (added `context` section with technique_tags, difficulty, goal)
- Replaced deprecated `classify_techniques()` fallback with `result.technique_tags = []`
- Deleted ~330 lines of deprecated heuristic classifiers from `technique_classifier.py`
- Fixed pre-existing crash bug in tier-1 error recovery path

## Architecture

### 12-Stage Pipeline
```
Parse → SolvePath → Analyze → Validate → Refutation → Difficulty → Assembly → Technique → Instinct → Teaching → SgfWriteback
```

Stages 1-7 (KataGo signal extraction): **stable, well-tested**
Stages 8-11 (heuristic teaching): **working but slated for LLM replacement**

### Key Components
- **28 TechniqueDetector classes** in `analyzers/technique_detectors/` — typed, tested
- **teaching_signals v2 payload** — bridge to LLM agent (`analyzers/teaching_signal_payload.py`)
- **StageRunner** — orchestrates pipeline stages with error recovery
- **AiAnalysisResult** — Pydantic model (schema v10) for all enrichment output

### Two-Phase Teaching Design
```
Phase 1 (this tool): SGF → KataGo → enrichment.json (includes teaching_signals v2)
Phase 2 (LLM agent): enrichment.json → LLM → teaching output → merge into SGF
```

## Test Status
- 2,287 tests after cleanup (was 2,342 before removing deprecated test classes)
- All passing on `pytest tests/ -m "not integration and not slow and not golden5 and not calibration"`

## Future Deprecation Candidates
Once LLM teaching agent is proven:
- `analyzers/teaching_comments.py`, `comment_assembler.py`, `hint_generator.py`
- `analyzers/vital_move.py`, `refutation_classifier.py`
- `analyzers/stages/teaching_stage.py`
- Related config in `config/teaching.py` (but `TeachingSignalConfig` stays)

Keep heuristic path as fallback for offline/no-API-key scenarios.
