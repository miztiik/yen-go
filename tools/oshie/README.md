# oshie (教え) -- Teaching Comment Generator

Generate human-quality teaching comments for Go puzzles using any OpenAI-compatible LLM. Takes KataGo enrichment output (Phase 1) and produces teaching comments, wrong-move explanations, and 3-tier progressive hints (Phase 2).

## Quick Start

```bash
cd tools/oshie

# Preview the prompt without calling the API
python teach.py \
  --input ../puzzle-enrichment-lab/.lab-runtime/outputs/prob0193_result.json \
  --dry-run

# Generate teaching comments (requires API key)
export OPENAI_API_KEY=sk-...
python teach.py \
  --input ../puzzle-enrichment-lab/.lab-runtime/outputs/prob0193_result.json \
  --output prob0193_teaching.json \
  --persona cho_chikun

# Merge LLM output back into enrichment JSON
python merge.py \
  --enrichment ../puzzle-enrichment-lab/.lab-runtime/outputs/prob0193_result.json \
  --teaching prob0193_teaching.json
```

## CLI Reference

```bash
# List available teacher personas
python teach.py --list-personas

# Use a specific persona
python teach.py --input result.json --output teaching.json --persona lee_sedol

# Override model/provider (e.g. local Ollama)
python teach.py --input result.json --output teaching.json \
  --model llama3 --base-url http://localhost:11434/v1

# Merge with schema validation
python merge.py --enrichment result.json --teaching teaching.json --validate
```

## Configuration

Copy `config.example.json` to `config.json` and set your provider:

```json
{
  "provider": {
    "base_url": "https://api.openai.com/v1",
    "api_key_env": "OPENAI_API_KEY",
    "model": "gpt-4o",
    "temperature": 0.3
  },
  "persona": "cho_chikun"
}
```

Swap providers by changing `base_url` + `model` + `api_key_env`. Works with OpenAI, Anthropic (via compatible endpoint), GitHub Copilot, Ollama, LM Studio, vLLM, etc.

## Teacher Personas

| Persona | Style |
|---------|-------|
| `cho_chikun` | Master of life and death. Precise, surgical explanations. |
| `lee_sedol` | Creative fighting spirit. Emphasizes reading and resilience. |
| `generic_teacher` | Neutral professional. Clear, structured explanations. |

Add a new persona by dropping a `.md` file in `prompts/personas/`.

## End-to-End Pipeline

```
SGF → [Enrichment Lab] → enrichment.json → [LLM Agent] → teaching.json → [merge.py] → enriched JSON
         (KataGo)              ↑                (LLM)                          ↑
      Phase 1: signals    teaching_signals v2              Phase 2: prose
```

See [PLAN.md](PLAN.md) for roadmap and architecture details.
