# yen-sei — Go Teaching Model SFT Pipeline

## Goal

Fine-tune a small language model to generate teaching hints for Go (Baduk/Weiqi) tsumego puzzles. The model replaces GPT-4o API calls in `tools/llm-teaching-agent/` and can also run in the browser via WASM for on-demand hints.

## How to train (1-page quickstart)

The data pipeline (qualify → ingest → harvest → refine) produces `train.jsonl`, `val.jsonl`, `test.jsonl` in `tools/yen_sei/data/refined/`. Training itself runs on Google Colab Free (T4 GPU). Both notebooks are self-contained: open in Colab, click **Run all**, drop the JSONL files when prompted.

| Step | Notebook | Time | What you do |
|---|---|---|---|
| 0 | (already done) `qualify` → `ingest` → `harvest` → `refine` CLI | ~25 min on laptop | `python -m tools.yen_sei qualify && ... ingest && ... harvest && ... refine` |
| 1 | [`notebooks/02a_model_evaluation.ipynb`](./notebooks/02a_model_evaluation.ipynb) | ~30-45 min | Open in Colab → Runtime: T4 → **Run all** → upload `train.jsonl` + `val.jsonl` when prompted. Outputs `winner.json`. |
| 2 | [`notebooks/02_train_tier1.ipynb`](./notebooks/02_train_tier1.ipynb) | ~3-6 hr | Set `MODEL_NAME` in CONFIG cell to the winner from step 1 → **Run all** → upload `train.jsonl` + `val.jsonl` + `test.jsonl`. Outputs LoRA adapter + (optional) merged fp16 weights, zipped for download. |
| 3 | [`notebooks/06_eval_quality.ipynb`](./notebooks/06_eval_quality.ipynb) | ~15 min | (To be implemented) End-to-end quality eval. |
| 4 | [`notebooks/03_generate_synthetic.ipynb`](./notebooks/03_generate_synthetic.ipynb) | ~2-3 hr | (To be implemented) Use the trained Tier 1 teacher to synthesise additional training data for Tier 2. |
| 5 | [`notebooks/04_distill_tier2_qwen3.ipynb`](./notebooks/04_distill_tier2_qwen3.ipynb) | ~2-3 hr | (To be implemented) QLoRA-distil Qwen3-0.6B on synthetic data. |
| 6 | [`notebooks/05_quantize_gguf.ipynb`](./notebooks/05_quantize_gguf.ipynb) | ~10 min | (To be implemented) Q4 GGUF for browser WASM. |

There is **no copy-pasting of code**. The notebooks include all install steps, data loading, training, evaluation, and download/zip packaging.

## Model Candidates (Under Evaluation)

We evaluate two candidates for the Tier 1 (server) teacher model before committing:

| Model | Params | License | Pros | Cons |
|-------|--------|---------|------|------|
| **Gemma 4 E2B** | 2.3B | Apache 2.0 | Smallest, newest arch (Apr 2026), 140+ langs | Not on Azure AI Foundry |
| **Phi-4-mini-instruct** | 3.8B | MIT | Azure Foundry serverless SFT, strong structured output | 65% larger, slightly more VRAM |

Tier 2 (browser WASM) model: **Qwen3-0.6B** (0.6B, Apache 2.0, ~350MB Q4, 8-15 tok/s in browser). Unchanged — distilled from whichever Tier 1 wins.

### Evaluation Protocol (Phase 0)

Run notebook `02a_model_evaluation.ipynb` on Colab Free (T4):
1. QLoRA SFT each candidate on 100 examples for 1 epoch
2. Inference on 20 held-out test puzzles
3. Compare: JSON schema compliance %, hint quality, output length, VRAM usage
4. Pick the winner based on quality-per-parameter ratio

## Fine-Tuning Technique: QLoRA SFT

### Why QLoRA SFT (and not other techniques)

| Technique | Decision | Rationale |
|-----------|----------|-----------|
| **QLoRA SFT** | **YES (primary)** | Structured JSON output task. 5K examples is the sweet spot for LoRA on 2-3B models. NF4 quantization fits Colab Free T4 (15GB). |
| LoRA SFT | Fallback | Same quality, ~2x VRAM. Use if QLoRA causes quality issues. |
| Full fine-tuning | NO | 3-4x VRAM, no quality gain over LoRA for format-conformance tasks. |
| DPO | NO (v1) | Requires preference pairs we don't have. Format task doesn't benefit. Revisit in v2 if hint *quality* (not format) is poor. |
| RLHF | NO | Needs reward model (another 2-3B model), PPO training (unstable), 10K+ comparisons, 3-4x cost. Overkill for constrained output. |
| RLVR / RFT | NO | Reward functions require verifiable ground truth (math/code). "Warm, pedagogical, Cho-Chikun-like" is not rewardable programmatically. |

### Why RFT (DPO / RLHF / RLVR) Does Not Fit This Task

Our task is to produce **structured JSON hints in a warm, teacher-like voice**. RFT techniques require either a verifiable reward signal or labeled preference pairs — neither of which we have:

1. **No reward signal.** RFT works for math (check the answer) and code (run the tests). For Go teaching comments, there is no programmatic reward function that can score "is this hint warm, concise, and pedagogically correct?"
2. **Tone and style are not rewardable.** "Warm, friendly, Cho-Chikun-like" requires human judgment. Building a reward model to capture that means labeling 10K+ preference pairs and training another 2–3B model — cost and complexity that dwarfs the SFT approach.
3. **JSON format compliance is solved by SFT.** Structured output (`correct_comment`, `wrong_comments`, `hints[]`) is a format-imitation task. SFT learns this from demonstrations. RLHF/PPO is unstable on small models and degrades JSON schema compliance before improving content quality.
4. **DPO needs preference pairs.** Building them requires: (a) generating two outputs per prompt from SFT v1, (b) ranking them. That is a labeling project — fine as a v2 polish, not a foundation.

**Decision confirmed (2026-04-17): SFT is the primary technique. RFT is a v2 option only.**

### DPO as Optional v2 Polish

After SFT v1 ships, if specific defects appear (verbosity, vague technique names), DPO is the right refinement:

1. Generate outputs for 500–1,000 held-out puzzles using the SFT LoRA
2. For each, write a `preferred` (concise, technique-correct, Cho-Chikun voice) and `non_preferred` (verbose, vague) variant
3. Run DPO for 1 epoch on top of the SFT LoRA weights (do NOT restart from base model)
4. Azure format: `preferred_output` / `non_preferred_output` (not `chosen`/`rejected`)

### Teaching Voice Target (Cho Chikun / Lee Sedol Style)

The voice is set by **training data curation, not algorithm choice**:

1. **200 gold examples** — hand-select or rewrite ~200 examples in the target voice from `professional-authors`, `pro-commentary`, and `classic-books` tiers (already ranked highest by selector). Apply 3–5× sampling weight during training (or upsample in JSONL).
2. **Length budget enforced in refine + system prompt** — cap: ≤ 25 words per hint, ≤ 60 words per `correct_comment`/`wrong_comment`. Drop training examples that exceed the budget. The model learns the budget from data AND the system prompt constraint.
3. **Noun-heavy, not verb-heavy** — Teaching comments should name the shape/technique ("short knight's move captures the ladder-breaker", not "play here because it is good"). Filter during refine: skip examples with comment-to-noun-phrase ratio below threshold.

### Hyperparameters

| Parameter | Tier 1 (2-4B) | Tier 2 (0.6B) |
|-----------|---------------|----------------|
| LoRA rank (r) | 32 | 16 |
| LoRA alpha | 64 | 32 |
| Target modules | all linear layers | all linear layers |
| Learning rate | 2e-4 | 3e-4 |
| Epochs | 3-5 | 5-8 |
| Effective batch size | 16 (batch 4 x grad_accum 4) | 16 |
| Max seq length | 1024-2048 | 1024 |
| Quantization | NF4 (bitsandbytes) | NF4 |
| Double quantization | true | true |
| Compute dtype | bfloat16 | bfloat16 |
| LR scheduler | cosine | cosine |
| Warmup | 10% of total steps | 10% |
| Weight decay | 0.01 | 0.01 |

### Knowledge Distillation (Tier 1 → Tier 2)

Use SFT-on-synthetic, not logit-based distillation:
1. Fine-tune Tier 1 teacher with real 5K examples
2. Run teacher inference on full puzzle corpus (Tier A + B, ~78K puzzles)
3. Filter outputs: schema validation, dedup, quality heuristics
4. Target 15-20K clean synthetic examples
5. QLoRA SFT Qwen3-0.6B on synthetic data

Why not logit distillation: Gemma/Phi and Qwen have different tokenizers, making probability-distribution matching impractical. SFT on teacher outputs is architecture-agnostic and works well for peaked output distributions (structured JSON).

## Compute Options

| Platform | GPU | Cost | Suitable? |
|----------|-----|------|-----------|
| **Google Colab Free** | T4 (15GB) | **$0** | YES — QLoRA on 2-4B fits. 12-hr session limit. |
| **Kaggle Notebooks** | T4x2 (30GB) | **$0** (30 hrs/week) | YES — generous free quota. |
| Google Colab Pro | T4/A100 | $10/mo | YES — longer sessions, A100 option. |
| RunPod | A10G-A100 | $0.44-1.25/hr | YES — pay-per-use, best for long jobs. |
| Azure AI Foundry | Serverless | ~$1.70/M tokens | PARTIAL — only Phi-4-mini, no Gemma/Qwen. SFT only, no LoRA control. |
| Azure ML Custom Jobs | NC/ND VMs | $1-5/hr | YES — full control, any HuggingFace model. |

**Primary target: Colab Free (T4).** Our notebooks are designed to run there. Upgrade path to Colab Pro or RunPod if session limits are hit.

### Azure AI Foundry Limitations (Researched 2026-04-17)

Azure AI Foundry does NOT support:
- Gemma models (any version) for fine-tuning
- Qwen3-0.6B (only Qwen-32B in Global Standard preview)
- LoRA/QLoRA as user-configurable options (abstracted away)
- DPO on open-source models (GPT-only)
- RLHF as a technique

Available for SFT: Phi-4-mini-instruct (3.8B), Ministral-3B, Llama 3.1 8B, GPT-4.1-nano.

If we choose Phi-4-mini as Tier 1 winner, Azure Foundry serverless becomes viable for training (but Tier 2 Qwen3-0.6B still needs external compute).

## Data Format (Universal JSONL)

### SFT Chat Completion Format

Every training/validation example is one JSON object per line:

```jsonl
{"messages": [{"role": "system", "content": "You are a professional Go teacher..."}, {"role": "user", "content": "Board: 19x19\nBlack to play\n..."}, {"role": "assistant", "content": "{\"teaching_comments\": {...}, \"hints\": [...]}"}]}
```

**No extra fields at top level.** No `metadata`, no `id`, no `split`. This format is universal across:
- Azure AI Foundry
- HuggingFace TRL / Unsloth / Axolotl
- OpenAI fine-tuning API
- Together AI, Fireworks, Anyscale

### Encoding

Files must be **UTF-8 with BOM** (`utf-8-sig` in Python) for Azure compatibility. The BOM is harmless on other platforms.

### Metadata Sidecar

Training metadata (source, file_path, quality_score) is written to a separate `sft_metadata.jsonl` file, keyed by a content hash. This preserves provenance without polluting the training data.

### DPO Format (Future v2, if needed)

```jsonl
{"input": {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]}, "preferred_output": [{"role": "assistant", "content": "..."}], "non_preferred_output": [{"role": "assistant", "content": "..."}]}
```

Note: Azure uses `preferred_output`/`non_preferred_output`, NOT `chosen`/`rejected` (HuggingFace convention).

## Data Sources

**Scanned 191,794 SGFs across 14 external-source directories** (2026-04-16).

Selection uses expert-informed criteria (see `selector.py` and `SOURCES.md`):
- Hard gates: variations, comments beyond markers, valid board size, min stones
- Weighted scoring: comment quality (40%), technique identification (25%), stone density (15%), reading depth (10%), metadata (10%)

### Tier A (score >= 0.5) — selected for ingest: 20,154 puzzles

| Source | Tier A | Key strength |
|--------|--------|-------------|
| community-problems | 7,790 | Crowd-sourced technique explanations |
| curated-ogs | 3,692 | Named collections with real teaching |
| difficulty-graded | 3,008 | Difficulty grading + teaching |
| dragon-archive | 2,134 | Deep variation trees |
| classic-books | 1,357 | Professional problem book commentary |
| hero-sets | 1,136 | Curated level progression |
| professional-authors | 500 | Pro-level commentary (Harada) |
| pro-commentary | 194 | Professional-grade explanations |
| pattern-play | 149 | Shape + tesuji identification |
| chinese-problems | 142 | Multi-language content |
| competition-drills | 52 | Life-and-death teaching |

After harvest+refine filtering (min 80 chars, dedup, quality scoring), we expect ~3,000-5,000 usable SFT examples.

### Tier B (score 0.3-0.5): 58,637 puzzles
Stays in external-sources. Will be used for synthetic data generation after Tier 1 model is trained.

### Excluded: drill-collection (23K), misc, shape-basics
Zero teaching content — pure drills with markers only.

## Pipeline Stages (v2 — config-driven, tier-aware)

All thresholds live in `tools/yen_sei/curation_config.json`. Change a number → re-run → see different tier sizes. No hardcoded thresholds in `stages/*.py`.

```
0.  qualify   — Scan ALL external-sources, classify each SGF as gold/silver/bronze/drop
                per curation_config.json. Writes data/qualification_{TS}.jsonl +
                qualification_latest.jsonl pointer (TS = YYYYMMDDTHHMM). Keeps
                last 3 timestamped runs; older ones are auto-deleted.
                Also enforces two AI-contamination gates BEFORE classification:
                  • ai_enriched         — drop if SGF YQ.ac > 0
                  • ai_signature_prose  — drop if >=2 templated-LLM-prose hits
                NO files copied. (Python, local, multiprocessing)
1.  sample    — Print N random puzzles from a tier for human spot-check.
2.  ingest    — Read qualification_latest.jsonl, copy selected tiers into data/sources/
                with tier-prefixed filenames: {tier}_{source}_{stem}.sgf.
                Writes data/sources/_manifest.jsonl with provenance. (Python, local)
3.  harvest   — Extract (position, comment) pairs from data/sources/. Tier is parsed
                from the filename prefix and propagated into RawExtract.tier.
                (Python, local)
4.  refine    — Build training examples with tier-aware processing:
                  • Pick LONGEST correct comment (not first) per puzzle
                  • Final response gate: drop thin assembled responses
                  • Tier-aware dedup (highest tier wins on collision)
                  • Stratified splits per tier (val/test contain proportional gold/silver/bronze)
                  • Weighted upsampling on train (gold ×3, silver ×1, bronze ×1)
                Writes sft.jsonl + sft_metadata.jsonl + train/val/test splits.
                (Python, local)
5.  validate  — Check schema compliance of refined data (Python, local)
6.  train     — QLoRA SFT Tier 1 model (Jupyter, Colab Free T4)
7.  generate  — Use trained model to produce synthetic data (Jupyter, Colab/RunPod)
8.  distill   — QLoRA SFT Qwen3-0.6B on combined data (Jupyter, Colab Free T4)
9.  quantize  — Convert to GGUF Q4 for browser (Jupyter, Colab)
10. eval      — Score output quality (Jupyter, Colab)
```

### v2 Curation Knobs (`tools/yen_sei/curation_config.json`)

| Section | Purpose | Tighten effect |
|---|---|---|
| `hard_gates` | Skip non-tsumego (game records, sparse boards, no variations) | Fewer total candidates |
| `language` | English-content threshold (heuristic stopword count or wordfreq) | Drops more non-English noise |
| `tier_rules.gold/silver/bronze` | Per-tier minimums (correct chars, wrong chars, causal phrases, technique mentions) | Shrinks each tier |
| `source_overrides[*].tier_cap` | Cap a source's max tier (`gold`/`silver`/`bronze`/`drop`) | Excludes whole sources or caps quality |
| `training_weights[tier]` | Upsample multiplier per tier (e.g. gold:3.0) | Reweights training distribution |
| `split_ratios` | train/val/test fractions | — |

### v2 Quality Outcome (vs v1)

| Metric | v1 (score-threshold) | v2 (tier-aware) |
|---|---|---|
| Thin correct_comment (≤20 chars) | **44.7%** | **0.2%** |
| No wrong_comments | 59.2% | 56.2% (intrinsic SGF limit) |
| Worst-case garbage | unknown | **0.0%** |
| Median correct_comment length | unknown | 100 chars |
| Final dataset | unknown | 8,753 rows (525 gold + 1,279 silver + 6,109 bronze, gold ×3 upsampled in train) |

### Data Isolation Policy

**yen-sei NEVER reads from or writes to `external-sources/` directly** (except `qualify`).

- `qualify` scans external-sources/ read-only to score puzzles and produce qualification_{TS}.jsonl + qualification_latest.jsonl pointer.
- `ingest` reads qualification_latest.jsonl (NOT external-sources) and copies selected SGFs into `data/sources/` with tier-prefixed names. All persisted paths are POSIX, repo-root-relative (see `tools/yen_sei/data_paths.py`).
- All downstream stages read only from `data/`.
- Original external-sources files are never modified, moved, or deleted.

### What runs on THIS machine (no GPU)

- **qualify**: Scan all 209K external-source SGFs, classify into tiers (~15 min on 11 workers)
- **sample**: Print N puzzles from a tier for spot-check
- **ingest**: Copy qualified SGFs into flat data/sources/ with tier prefixes
- **harvest**: Parse data/sources/ SGFs, extract raw data to data/raw/
- **refine**: Normalize, gate, weight, format into data/refined/
- **validate**: Check refined JSONL against schema
- **Tests**: All unit tests for qualify + ingest + harvest + refine + validate

### What runs on GPU (Colab Free / RunPod)

- **evaluate / train / generate / distill / quantize / eval**: Jupyter notebooks designed to run on Colab Free T4. Self-contained — upload data, run cells, download results.

## Directory Structure

```
tools/yen_sei/
├── PLAN.md                      # This file
├── SOURCES.md                   # Data landscape documentation
├── LESSONS.md                   # Lessons learned
├── __init__.py
├── __main__.py                  # CLI: select, ingest, harvest, refine, validate, serve
├── config.py                    # Paths, constants
├── selector.py                  # Expert-informed puzzle scoring
│
├── stages/
│   ├── __init__.py
│   ├── ingest.py                # Scored flat-copy into data/sources/
│   ├── harvest.py               # data/sources/ SGFs → data/raw/
│   ├── refine.py                # Filter + normalize → data/refined/
│   └── validate.py              # Schema compliance checks
│
├── models/                      # Pydantic data contracts
│   ├── __init__.py
│   ├── raw_extract.py           # harvest output schema
│   ├── training_example.py      # refine output schema (ChatML)
│   └── pipeline_event.py        # Telemetry event schema
│
├── telemetry/
│   ├── __init__.py
│   ├── logger.py                # Structured JSON logging
│   └── events.py                # Event emitter
│
├── gui/                         # Lightweight monitoring (FastAPI + vanilla JS)
│
├── server.py                    # FastAPI bridge for GUI
│
├── notebooks/
│   ├── 01_audit_data_quality.ipynb       # Sample and assess raw data
│   ├── 02a_model_evaluation.ipynb        # Compare Gemma vs Phi-4-mini (Colab T4)   ← NEW
│   ├── 02_train_tier1.ipynb              # QLoRA SFT winner model (Colab T4)
│   ├── 03_generate_synthetic.ipynb       # Mass-produce data via Tier 1 (Colab/RunPod)
│   ├── 04_distill_tier2_qwen3.ipynb      # QLoRA SFT Qwen3-0.6B (Colab T4)
│   ├── 05_quantize_gguf.ipynb            # Convert to GGUF Q4 (Colab)
│   └── 06_eval_quality.ipynb             # Evaluate both tiers (Colab)
│
├── tests/
│
└── data/                        # Pipeline artifacts (gitignored)
    ├── sources/                 # Flat: {source}_{name}.sgf (ingest output)
    ├── raw/raw.jsonl            # harvest output
    ├── refined/                 # refine output
    │   ├── sft.jsonl            # All examples (messages only, no metadata)
    │   ├── sft_metadata.jsonl   # Sidecar: source, quality_score, etc.
    │   ├── train.jsonl
    │   ├── val.jsonl
    │   └── test.jsonl
    ├── synthetic/               # generate output
    └── models/                  # trained model artifacts
```

## Current Status (2026-04-17)

- **select**: Complete — 191,794 SGFs scanned, 20,154 Tier A identified
- **ingest**: Complete — 20,780 Tier A puzzles copied to flat data/sources/
- **harvest + refine + validate**: Hardened — shared schema from `tools.core.teaching_schema`, programmatic hint generation, validation stage added
- **audit notebook**: Ready — runs on data/sources/ after ingest
- **GPU notebooks (02-06)**: Stubs, awaiting GPU environment
- **Training strategy research**: Complete (2026-04-17) — QLoRA SFT chosen, model evaluation phase added
- **Data format**: Fixed — universal JSONL (messages only), utf-8-sig encoding

### Shared Components (consolidated 2026-04-17)

- `tools.core.teaching_schema` — canonical `TeachingOutput` / `TeachingComments` Pydantic models
- `tools.core.go_teaching_constants` — `GO_TECHNIQUES`, `MARKER_ONLY_PATTERNS`, `GO_TECHNIQUE_PATTERN`, `EXPLANATION_KEYWORDS`
- Both `yen_sei` and `llm-teaching-agent` import from these shared modules

### Next Steps

1. Run harvest → refine → validate to produce actual training data
2. Run `notebooks/01_audit_data_quality.ipynb` to visualize data
3. Upload 100 examples to Colab, run `02a_model_evaluation.ipynb`
4. Pick Tier 1 model winner, proceed with full training

```bash
python -m tools.yen_sei harvest                    # Extract teaching pairs
python -m tools.yen_sei refine --stats             # Produce SFT JSONL with hints
python -m tools.yen_sei validate                   # Check schema compliance
```

## Target Output Format

The refine stage produces ChatML JSONL matching the `TeachingOutput` schema from `tools/llm-teaching-agent/agent/response_parser.py`:

```json
{
  "teaching_comments": {
    "correct_comment": "Explanation of why the correct move works",
    "wrong_comments": {"cd": "Why this move fails"},
    "summary": "One-line puzzle summary"
  },
  "hints": ["Technique name", "Reasoning hint", "Coordinate hint with {!xy}"]
}
```

The challenge: raw SGF comments are freeform text, not structured JSON. The normalization step maps freeform comments -> structured fields. The audit notebook will reveal how feasible this mapping is and what heuristics we need.

## Integration Point

The trained model slots into `tools/llm-teaching-agent/` by changing one config:

```python
# Before (GPT-4o API, paid):
LLMConfig(base_url="https://api.openai.com/v1", model="gpt-4o")

# After (local model, free):
LLMConfig(base_url="http://localhost:8080/v1", model="yen-sei-tier1")
```

Served via llama.cpp server, vLLM, or Ollama (all expose OpenAI-compatible endpoints).

## Data-Path & Naming Policy (added 2026-04-18)

Helpers live in `tools/yen_sei/data_paths.py`. Every stage that writes a primary
artefact MUST use them, and every stage that reads one MUST go through the
`_latest` pointer.

- **Filename format**: `{kind}_{YYYYMMDDTHHMM}.{ext}` (e.g. `qualification_20260418T2146.jsonl`).
- **Pointer**: `{kind}_latest.{ext}` is a byte-copy of the most recent timestamped file (not a symlink — Windows-portable).
- **Retention**: `cleanup_old(keep=3)` after each successful run keeps the 3 most recent timestamps and deletes older ones.
- **POSIX paths only**: all `file_path` / `source_path` fields persisted to JSONL go through `to_posix_rel(p)` (forward slashes, repo-root-relative). Readers use `from_posix_rel(rel)` to materialize an absolute `Path`.

This kills the `qualification_v2 / v2.1 / STALE / kano_239 / smoke` proliferation we accumulated in v2.

## AI-Contamination Filter (added 2026-04-18)

Lives in `governance/teaching_signal.py`, runs inside `qualify`. Two cheap checks
before sgfmill parses anything:

1. **`ai_enriched`** — regex-extract the SGF root property `YQ[...]`, parse `ac:N`, drop if `N > 0` (the puzzle has been touched by enrichment / AI-solve / verification).
2. **`ai_signature_prose`** — count hits across 6 patterns of templated LLM prose ("the correct move is", "as an AI", coordinate dumps `(B 3-4) → (W 5-2)`, etc.). Drop if `>= 2`.

Both append to `gate_failures`, which `tier_classifier` already routes to `drop`.
Manifest written by `ingest` carries `yq_ac` and `ai_signature_hits` for forensics.

Why this matters: without these gates the pipeline would happily ingest
KataGo-enriched and GPT-4o-enriched puzzles as "gold" training data and we
would be SFT-ing on our own AI's previous output. The whole point of yen-sei is
to LEARN HUMAN TEACHING, so AI-touched puzzles must be excluded from training.

## Eval Methodology — Layer A / B / C (added 2026-04-18)

Replaces the old "JSON-compliance %" metric, which was structural-only and
silently passed prose like "I cannot help".

- **Layer A — Structural** (`eval/scorers.py::score_structural`)
  - Free, deterministic. Does the output parse as JSON? Does it have non-empty `teaching_comments.correct_comment`, a `wrong_comments` block, and `hints`?

- **Layer B — Grounded** (`eval/scorers.py::score_grounded`)
  - Free, deterministic, position-anchored. Does the output **mention the actual correct move** (extracted from the reference's `{!cg}` token)? Does it mention **at least one technique that actually applies to this puzzle's tags** (matched against `GO_TECHNIQUE_PATTERN`)? Does it avoid hallucinating off-board SGF coordinates? Is the text plausibly English?

- **Layer C — Judge** (`eval/judges.py`)
  - Pluggable `Judge` Protocol with `grade(prompt, generated, reference, metadata) -> JudgeResult(score 0..5, rubric, rationale, backend)`.
  - Default backend `ManualJudge` returns sentinel `score=-1` immediately and writes a random sample of 20 items to `judge_queue.jsonl` for human grading. The human edits the file in-place: stamp `score` (0..5) and `rationale`, save.
  - **Future plug-in backends** (interface unchanged):
    - `OpenAIJudge` — calls GPT-4o as judge with a fixed rubric prompt
    - `LocalJudge` — calls Ollama / vLLM with a stronger local model (Llama-70B, Qwen-72B)
    - `SubagentJudge` — Copilot subagent invocation via `runSubagent` for batched grading
  - Reference text is included in the queue, but it is **not** used by Layer A/B (which deliberately don't do reference-string matching, since teaching prose is freeform).

**Headline metric**: `useful_answer_pct = (parses) AND (has correct comment) AND (mentions correct coord OR known technique) AND (looks English)`. This is what the notebooks print and what we track across runs.

### Eval prompt-leak fix (`stages/refine.py`)

`_build_user_prompt` no longer includes a `Context: {root_comment}` line. The
SGF root comment frequently paraphrases the answer, and including it in the
test prompt was leaking the label into the input — making val/test scores
misleadingly high.

The user prompt now contains only: board size, side to move, level, stones,
tags. The reference assistant turn is the supervised target during training and
the held-out gold during eval — never repeated back to the model in the prompt.

## v2.3 — Bronze Criteria, No Upsampling, Marker-Only Test Sets (added 2026-04-19)

### Why

Two flaws found after the first end-to-end v2.2 run:

1. **Gold ×3 upsampling**. `training_weights` defaulted to `{gold: 3.0, silver: 1.0, bronze: 1.0}`, and refine's writer multiplied each gold row 3 times into `train.jsonl`. This artificially inflated the apparent dataset size and over-weighted the optimizer's gradient on duplicated rows without adding any new information. Hides true sample counts. Increases overfit risk.

2. **Bronze dominated training**. Default ingest blindly admitted every bronze row that passed the loose tier rules (`cor>=40, wrong>=0`). Bronze ended up at 73% of the training set (8,300+ of 11,400 rows). Bronze is the long tail by definition; if it dominates the distribution, the model learns the long tail's voice rather than gold-and-silver's.

### Fix

- **Upsampling removed**. `training_weights` now `{gold: 1.0, silver: 1.0, bronze: 1.0}` (always). `refine` writes each unique example exactly once. Setting a tier weight to `0.0` still excludes that tier entirely (used to disable a tier without re-running ingest).
- **Bronze admitted by criteria + cap**. New `bronze_selection` block in `curation_config.json`:

  ```json
  {
    "criteria": {"min_wrong_explanation_chars": 30, "min_technique_mentions": 1, "min_quality_score": 0.4},
    "cap_policy": "max_of_gold_silver",
    "sort_formula": { "wrong_chars_weight": 2.0, "techniques_weight": 50.0, ... }
  }
  ```

  Applied at INGEST time. Rows below criteria drop. Survivors are quality-ranked
  via `sort_formula` and capped at `len(gold) + len(silver)` so bronze
  cannot dominate. Result on the same input corpus:
  `bronze 11,535 → 948 kept` (cap was 2,552 — well below).

### Marker-only test pool

Test sets used to be drawn from the same training pool (`split_ratios.test = 0.1`).
That meant test puzzles had teaching prose, so the user prompt risked leaking
the answer (root comment paraphrase) and the reference assistant message was
the very thing we were grading the model on. Now:

- `split_ratios.test = 0.0` — test split inside the training pool is empty.
- New "marker-only" pool: ~45,700 puzzles that **fail the prose / english gates** but are **structurally valid** — `correct_first_move` non-empty, `>=1` wrong_first_move, `variation_count >= 2`, hard gates pass, no AI contamination. They have zero English teaching prose, so nothing leaks.
- New `test_sets[]` config block defines named sets:

  ```json
  [
    {"id": "marker_only_mixed",         "source": "marker_only",   "size": 200},
    {"id": "marker_only_life_death_19", "source": "marker_only",   "size": 150,
       "selectors": {"board_sizes": [19], "techniques_any": ["life","death","kill","live"]}},
    {"id": "marker_only_tactical",      "source": "marker_only",   "size": 100,
       "selectors": {"techniques_any": ["ladder","snapback","net","throw","sacrifice"]}},
    {"id": "heldout_gold_silver",       "source": "training_pool", "size": 100,
       "tiers": ["gold","silver"]}
  ]
  ```

- New CLI stage `python -m tools.yen_sei eval-prep` reads
  `qualification_latest.jsonl + test_sets[]` and writes per-set:
  - `data/refined/test_{id}.jsonl` — chat row with `[system, user]` only (no
    assistant), so the prompt-leak surface is zero.
  - `data/refined/test_{id}_metadata.jsonl` — sidecar with `correct_first_move`,
    `wrong_first_moves`, `tags`, `board_size`, `side_to_move`, `source`,
    `has_reference_prose`, `puzzle_hash`.

### Eval runner: multi-set comparison

`tools.yen_sei.eval.runner` adds:

- `evaluate(rows, sidecars=...)` — reads `correct_first_move` from sidecar
  when there is no reference assistant message (Layer B falls back from
  parsing `{!cg}` in the reference to reading `sidecar.correct_first_move`).
- `evaluate_test_sets(test_sets, ...)` — orchestrator that runs `evaluate`
  on each named set, writes per-set artefacts to
  `out_dir/{test_set_id}/test_summary.json + test_results.json`, and prints
  a comparison table at the top of `out_dir/comparison.json`.
- `load_test_set_bundle(refined_dir, test_set_id)` — convenience loader
  for notebook callers.

### Pre-training dryrun

New `python -m tools.yen_sei eval-dryrun`. Heuristic-only — no GPU. Prints
per-set `n`, board-size / side / source distributions, top tags,
`%has_correct_first_move`, `%with_known_technique_tag`, `%has_reference_prose`,
plus a comparison table. Catches degenerate test sets (single source, all one
side, no tags, etc.) before you spend GPU minutes on them. Writes
`data/refined/test_sets_dryrun.json`.

### Notebook updates

- `02_train_tier1.ipynb` — Cell 3 discovers `test_*.jsonl` automatically.
  Cell 5 replaces the inline 200-line scorer with one call to
  `evaluate_test_sets(model, tokenizer, TEST_SETS, OUT_DIR/eval)`. Cell 6 zips
  the per-set `eval/` subtree into the artifact bundle.
- `02a_model_evaluation.ipynb` (bake-off) — same multi-set runner.
  Verdict cell now picks the winner by **mean `useful_answer_pct` across the
  marker-only sets only** (the prose-leak-free pools); `heldout_gold_silver`
  is reported but excluded from the decision because it shares distribution
  with the training pool.

### v2.3 numbers (same input corpus, same qualifier)

| metric                | v2.2     | v2.3    |
| --------------------- | -------- | ------- |
| qualified gold        | 672      | 672     |
| qualified silver      | 1,879    | 1,880   |
| qualified bronze      | 11,416   | 11,535  |
| **bronze ingested**   | 11,416   | **948** |
| unique training rows  | 8,522    | 3,173   |
| **rows in train.jsonl** | **7,850** (gold ×3 + silver + bronze) | **2,855** (no upsampling) |
| val rows              | 851      | 316     |
| test rows (in pool)   | 855      | 2 (vestigial) |
| marker-only test pool | n/a      | 45,692  |
| named test sets       | n/a      | 4 (200+150+100+100) |

