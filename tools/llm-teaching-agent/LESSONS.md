# oshie — Lessons Learned

Hard-won insights from building the Go teaching comment & hint generator. Each lesson comes from a design decision, mistake, or course correction.

> **Name origin**: 教え (oshie) — Japanese for "teaching/lesson". This tool generates teaching prose and progressive hints for tsumego puzzles using LLM inference on KataGo signals.

---

## 0. KataGo Excels at Signals, Not Prose (2026-04-12)

**What happened**: The enrichment lab's KataGo pipeline produces excellent numerical signals — score deltas, win rates, policy scores, principal variations, refutation sequences. But its "teaching comments" are mechanical: "Black plays D7. Score: +44.6. Win rate: 95%." No pedagogy, no intuition, no progressive disclosure.

**Why it matters**: The frontend needs three things KataGo cannot provide: (1) a human-readable explanation of WHY a move works, (2) a description of what goes WRONG with each incorrect first move, and (3) progressive hints that guide without spoiling.

**Lesson**: Separate signal extraction (KataGo's strength) from prose generation (LLM's strength). The `teaching_signals v2` payload is the versioned contract between them. Don't try to make KataGo write prose; don't try to make the LLM compute scores.

**Applied**: Two-phase architecture — enrichment lab produces `enrichment.json` with KataGo signals, oshie consumes those signals and generates teaching prose via LLM API.

---

## 1. Voice Constraints Must Be Explicit for LLMs (2026-04-12)

**What happened**: Early prompt iterations produced teaching comments that were patronizing ("Great try, but..."), verbose ("As we can see from the board position..."), or inconsistent (switching between formal and casual within one puzzle).

**Lesson**: LLMs need explicit voice constraints (VP-1 through VP-5) baked into the system prompt. "Board speaks first" (describe consequence, not student error), "action → consequence with em-dash", "max 15 words for wrong-move summaries", "warmth only for near-misses". Without these, every model produces a different voice.

**Applied**: Five voice principles in `prompts/system_prompt.md`. These are non-negotiable across all personas.

---

## 2. Coordinate Tokens Are the Frontend's Job, Not the LLM's (2026-04-12)

**What happened**: Tier-3 hints include `{!xy}` SGF coordinate tokens (e.g., `{!dg}` for D7). The LLM must use this exact format because the frontend renders them as interactive board highlights.

**Why it's fragile**: Small models hallucinate coordinates. The LLM doesn't have the board position encoded spatially — it's working from a text description. Asking it to emit precise SGF coordinates is asking for memorization, not reasoning.

**Lesson**: This is the same insight as yen-sei Lesson 16 — don't ask the model to generate what can be computed. For tier-3 hints, the correct move coordinate comes from `teaching_signals.correct_move.sgf_coord`. The pipeline should inject `{!xy}` at merge time, not ask the LLM to produce it.

**Status**: Current system asks the LLM to emit `{!xy}` tokens. This may need to change to a computed injection if hallucination rates are high during eval.

---

## 3. Reuse Existing Scanning/Selection Infrastructure (2026-04-19)

**What happened**: When preparing test data for oshie evaluation, the temptation was to write a custom SGF scanner and quality filter. But `tools/core/` and `tools/yen_sei/` already have battle-tested utilities:

- `tools/core/sgf_parser.py` → `parse_sgf()`, `read_sgf_file()` (encoding-safe)
- `tools/core/sgf_analysis.py` → `classify_difficulty()`, `compute_complexity_metrics()`
- `tools/yen_sei/governance/teaching_signal.py` → `extract_signals()` (quality scoring)
- `tools/yen_sei/governance/tier_classifier.py` → `classify()` (gold/silver/bronze)
- `tools/yen_sei/stages/qualify.py` → `run_qualify()` (parallel scanning)

**Lesson**: Before writing new code, check `tools/core/` and `tools/yen_sei/`. The scanning, parsing, scoring, and tiering pipeline already handles 200K+ SGFs reliably. Copy the patterns; import the utilities where module boundaries allow.

**Applied**: Test set generation for oshie will reuse `extract_signals()` + `classify()` for quality scoring, `parse_sgf()` for SGF reading, and the eval_prep stratification pattern for diverse sampling.

---

## 4. External Sources Are Read-Only — Always Copy (2026-04-19)

**What happened**: Established as a project-wide rule, reinforced here. The `external-sources/` directory is shared across multiple tools and agents. It contains crawler output that takes hours to regenerate.

**Lesson**: Never modify, move, or delete files in external-sources. Always copy SGFs to a local working directory (`data/test_inputs/` or similar) for any downstream work. SGF files are the source; enriched outputs are separate artifacts in separate directories.

**Applied**: oshie's test set builder will copy selected SGFs into `tools/llm-teaching-agent/data/test_inputs/`, leaving external-sources untouched.

---

## 5. ASCII-Only Prompts for llama.cpp Endpoints (2026-04-19)

**What happened**: First live test against Gemma 4 26B on llama.cpp server failed with `json.exception.parse_error.101: ill-formed UTF-8 byte`. The system prompt contained an em-dash (`—`) from the VP-2 voice constraint description. llama.cpp's JSON parser rejected the multi-byte UTF-8 character.

**Why it matters**: The oshie system prompt (`prompts/system_prompt.md`) uses em-dashes in VP-2 ("Action → consequence with em-dash"). When this gets JSON-serialized into the chat completions request body, multi-byte UTF-8 characters can break strict JSON parsers in some inference servers.

**Lesson**: Keep all prompt text ASCII-safe when targeting llama.cpp (and likely other local inference servers). Replace em-dashes with `--`, arrows with `->`, and curly quotes with straight quotes. The model understands the instruction equally well in ASCII.

**Applied**: Shortened test prompt used ASCII only and succeeded. Need to audit `prompts/system_prompt.md` and persona files for non-ASCII characters before production use.

---

## 6. Gemma 4 Thinking Mode Consumes 2/3 of Token Budget (2026-04-19)

**What happened**: Gemma 4 26B-A4B-it splits output into `reasoning_content` (chain-of-thought) and `content` (final answer). With `max_tokens: 512`, ALL tokens went to reasoning -- zero visible output. With `max_tokens: 2048`, reasoning consumed ~1500 tokens and the visible answer was truncated. With `max_tokens: 1024` and a shorter prompt, it completed: ~450 tokens reasoning + ~210 tokens content.

**Why it matters**: The thinking budget is implicit and uncontrollable via the standard OpenAI API. oshie's `llm_client.py` must account for this -- if `max_tokens` is too low, the model produces empty content.

**Lesson**: For thinking models on llama.cpp, budget 3-4x the expected output length. A 200-token teaching response needs `max_tokens: 800+`. Also: `llm_client.py` must extract `content` (not `reasoning_content`) and handle markdown code fences in the response.

**Applied**: Successful test used `max_tokens: 1024` for a ~200-token JSON response. The `reasoning_content` field contains genuine Go reading (liberty counting, vital point analysis) -- useful for debugging but not for output.

---

*-- Add lessons here as testing and prompt iteration reveal new insights --*
