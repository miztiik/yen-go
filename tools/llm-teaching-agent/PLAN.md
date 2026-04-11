# LLM Teaching Agent — Plan

## Status: Skeleton Complete (2026-04-12)

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

1. **End-to-end test with real LLM** — Run against a live API, review quality of generated comments
2. **Prompt iteration** — Tune prompts based on output quality across difficulty levels
3. **Batch processing** — Process multiple puzzles in a single run
4. **SGF writeback** — merge.py currently writes JSON; add SGF regeneration via sgfmill
5. **Cost tracking** — Log token usage per puzzle for cost estimation
6. **Heuristic deprecation** — Once LLM quality is proven, deprecate enrichment lab's heuristic teaching stages (8-11)

## Lessons Learned

- KataGo excels at signal extraction (scores, PVs, refutations) but cannot write human-quality prose
- teaching_signals payload was already designed as "Option B: Rich Payload" for exactly this LLM use case
- Keeping the LLM tool separate from the KataGo pipeline prevents coupling different iteration speeds
- VP-1 through VP-5 voice constraints are critical for consistent, non-patronizing teaching voice
- `{!xy}` coordinate tokens in tier-3 hints are rendered by the frontend — the LLM must use them
