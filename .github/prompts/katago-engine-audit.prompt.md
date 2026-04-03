---
mode: agent
agent: KataGo-Engine-Expert
description: Audit KataGo enrichment config from MCTS engine perspective
---

## Prompt

Evaluate the KataGo enrichment configuration for the puzzle-enrichment-lab.

**Config file**: `config/katago-enrichment.json`
**KataGo CFG**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Config models**: `tools/puzzle-enrichment-lab/config/` (Pydantic models)

Evaluate all parameters from an MCTS engine perspective:

1. Read the config files above
2. Assess visit budgets, model selection, noise parameters, escalation policy, search tree behavior, ko/rules configuration
3. Return your structured per-parameter assessment table
4. Flag any parameters that are misconfigured for tsumego enrichment vs general gameplay

Focus areas (if specified by user): {{focus_areas}}
