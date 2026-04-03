---
mode: agent
agent: KataGo-Tsumego-Expert
description: Audit KataGo enrichment config from tsumego domain perspective
---

## Prompt

Evaluate the KataGo enrichment configuration for puzzle correctness and quality.

**Config file**: `config/katago-enrichment.json`
**KataGo CFG**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Config models**: `tools/puzzle-enrichment-lab/config/` (Pydantic models)

Evaluate all parameters from a professional tsumego perspective:

1. Read the config files above
2. Assess move classification accuracy, solution tree completeness, seki/ko detection, difficulty calibration, technique detection, refutation quality
3. Return your structured per-parameter assessment table
4. Flag any parameters that could cause incorrect puzzle classification or incomplete solution trees

Focus areas (if specified by user): {{focus_areas}}
