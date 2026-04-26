# oshie (教え) — Plan

> **Pending rename**: `tools/llm-teaching-agent/` → `tools/oshie/` (approved, not yet executed)

## Status: Skeleton Complete → Preparing for First Live Test (2026-04-19)

Phase 1 (KataGo signal extraction) is stable. This tool implements Phase 2: LLM-generated teaching comments.

## Architecture

```
enrichment.json (KataGo output) → teach.py → LLM API → teaching.json → merge.py → enriched SGF
```

- **Separate tool** from the enrichment lab. Different runtime (network API vs local GPU), different iteration cadence (prompt engineering changes daily).
- **OpenAI-compatible API** as universal interface. Swap models by changing `base_url` + `model` + `api_key_env`.
- **Teacher personas** as markdown files in `prompts/personas/`. Add personas by dropping a `.md` file.
- **teaching_signals v2** is the versioned contract between KataGo pipeline and this tool.

## What Works

- `teach.py` CLI: `--input`, `--output`, `--persona`, `--model`, `--base-url`, `--dry-run`, `--list-personas`
- `merge.py`: merges LLM output back into enrichment JSON
- Prompt builder: combines persona + system prompt + teaching_signals data
- Response parser: Pydantic validation of LLM JSON output
- 3 personas: Cho Chikun, Lee Sedol, generic teacher
- 31 tests passing

## What's Next

### Phase 3: Test Set Generation (current)

Build a diverse test set from existing pipeline data. **External-sources is read-only — copy, never modify.**

**Approach** — reuse existing libraries, don't reinvent:

| Step | Tool / Module | What it does |
|------|---------------|--------------|
| 1. Scan | `yen_sei/stages/qualify.py` → `run_qualify()` | Parallel scan of external-sources SGFs |
| 2. Parse | `tools/core/sgf_parser.py` → `parse_sgf()` | Read SGF with encoding fallback |
| 3. Score | `yen_sei/governance/teaching_signal.py` → `extract_signals()` | Quality scoring (correct chars, techniques, english ratio) |
| 4. Tier | `yen_sei/governance/tier_classifier.py` → `classify()` | gold/silver/bronze classification |
| 5. Select | Stratified sampling (inspired by `yen_sei/stages/eval_prep.py`) | Diverse across difficulty + technique |
| 6. Copy | Copy selected SGFs → `data/test_inputs/` | Local snapshot, external-sources untouched |
| 7. Enrich | Run through enrichment lab (KataGo) → `enrichment.json` per puzzle | Generate teaching_signals v2 payloads |

**Target test set**: 30-50 puzzles, stratified:
- Difficulty: ~10 beginner, ~15 intermediate, ~15 advanced, ~10 dan
- Techniques: life-and-death, ladder, net, ko, snapback, capturing race
- Board sizes: mostly 19x19, some 9x9/13x13
- Quality tiers: mix of gold (rich existing comments) and marker-only (no comments)

**Output**: `data/test_inputs/*.sgf` + `data/test_enrichments/*.json` (one enrichment.json per puzzle)

### Phase 4: Evaluation Harness

Inspired by yen-sei's 3-layer eval framework (`tools/yen_sei/eval/`):

| Layer | What it checks | Cost |
|-------|---------------|------|
| **A: Structural** | Valid JSON? Has `correct_comment`? Has `wrong_comments` for each wrong move? 1-3 hints? Character counts? | Free (deterministic) |
| **B: Grounded** | Mentions correct move coord? References ≥1 technique tag? No hallucinated coords? Hints progressive (tier1 < tier2 < tier3 specificity)? Voice constraints met (word count, no patronizing)? | Free (regex/heuristic) |
| **C: Judge** | Prose quality, pedagogical clarity, Go correctness. Pluggable: manual, LLM-as-judge, or Claude subagent | Variable |

**Headline metric**: `Useful Teaching %` = parses OK AND has correct comment AND (mentions correct move OR mentions technique) AND hints are progressive.

**Additional metrics**:
- `voice_compliance_pct` — VP-1..VP-5 constraint adherence
- `avg_hint_progression` — tier 1 is vague, tier 2 is directional, tier 3 has coordinate
- `wrong_move_coverage_pct` — % of wrong moves with explanations
- `avg_correct_comment_chars` — prose length (too short = thin, too long = verbose)

### Phase 5: Live LLM Testing

1. Run `teach.py` against test set with a real LLM endpoint
2. Collect `teaching.json` outputs
3. Score with eval harness (Layers A+B automated, Layer C manual sample)
4. Iterate prompts based on failure modes
5. Compare personas (Cho Chikun vs Lee Sedol vs generic) on same puzzles

### Phase 6: Batch Processing & Integration

1. Batch mode for `teach.py` (multiple puzzles per run)
2. Cost tracking (token usage per puzzle)
3. SGF writeback via `tools/core/sgf_parser.py`
4. Pipeline integration with enrichment lab

### Phase 7: Heuristic Deprecation

Once LLM quality is proven (Useful Teaching % > 80%), deprecate enrichment lab's heuristic teaching stages (8-11).

## Lessons Learned

Moved to `LESSONS.md` — maintained as a living document with hard-won insights.
