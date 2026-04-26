# oshie -- Memory

Hard-won insights from building the Go teaching comment & hint generator. Each entry comes from a design decision, mistake, or course correction.

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

**Applied**: oshie's test set builder will copy selected SGFs into `tools/oshie/data/test_inputs/`, leaving external-sources untouched.

---

## 5. ASCII-Only Prompts for llama.cpp Endpoints (2026-04-19)

**What happened**: First live test against Gemma 4 26B on llama.cpp server failed with `json.exception.parse_error.101: ill-formed UTF-8 byte`. The system prompt contained an em-dash (`—`) from the VP-2 voice constraint description. llama.cpp's JSON parser rejected the multi-byte UTF-8 character.

**Why it matters**: The oshie system prompt (`prompts/system_prompt.md`) uses em-dashes in VP-2 ("Action → consequence with em-dash"). When this gets JSON-serialized into the chat completions request body, multi-byte UTF-8 characters can break strict JSON parsers in some inference servers.

**Lesson**: Keep all prompt text ASCII-safe when targeting llama.cpp (and likely other local inference servers). Replace em-dashes with `--`, arrows with `->`, and curly quotes with straight quotes. The model understands the instruction equally well in ASCII.

**Applied**: Shortened test prompt used ASCII only and succeeded. Need to audit `prompts/system_prompt.md` and persona files for non-ASCII characters before production use.

---

## 6. Thinking Models Need 8K+ Token Budget -- 4K Is Not Safe (2026-04-19)

**What happened**: Gemma 4 26B-A4B-it splits output into `reasoning_content` (chain-of-thought) and `content` (final answer). Thorough testing across 3 difficulty levels revealed:

| Puzzle | Difficulty | Thinking tokens | Content tokens | max_tokens | Result |
|--------|-----------|----------------|----------------|------------|--------|
| Ladder | Beginner | 3,056 | 129 | 4,096 | OK |
| Nakade | Intermediate | 4,093 | 0 | 4,096 | EMPTY -- all budget consumed by thinking |
| Ko | Advanced | 3,396 | 144 | 4,096 | OK |
| Nakade (retry) | Intermediate | 3,314 | 149 | 8,192 | OK |

The thinking budget is implicit and uncontrollable via the standard OpenAI API. Life-and-death problems trigger deeper reading (more liberty counting, more variation checking) which consumes more thinking tokens.

**Lesson**: Use `max_tokens: 8192` minimum for oshie. 4096 is unsafe -- one complex puzzle silently returns empty content with `finish_reason: stop` (not `length`!). The model "finishes" its thinking and has no budget left for the answer. `llm_client.py` MUST check for empty `content` and retry with higher budget or flag the failure.

**Applied**: All subsequent tests use 8192+. Added empty-content detection as a requirement for the eval harness (Layer A structural check).

---

## 7. Streaming Reveals What Batch Hides (2026-04-19)

**What happened**: Non-streaming requests to the llama.cpp server return one big JSON blob after 2-3 minutes of silence. With `stream: true`, SSE chunks arrive token-by-token showing:
- Phase transitions: `reasoning_content` tokens first, then `content` tokens
- Real-time progress: ~23 tok/s on AMD EPYC 9V74 (32 cores)
- Hang detection: if tokens stop flowing, something is wrong

The streaming format is fully OpenAI-compatible: `data: {json}\n\n` per token, `data: [DONE]` at end.

**Lesson**: Always use streaming for debugging and progress monitoring. For batch processing, non-streaming is simpler to parse but streaming + empty-content detection is safer. The `reasoning_content` field streams separately from `content` -- oshie's client must handle both.

**Applied**: Test harness uses streaming with 10s progress reporting. Production `llm_client.py` should support both modes.

---

## 8. Model Output Is Structurally Good But Pedagogically Thin (2026-04-19)

**What happened**: Qualitative assessment of 3 test responses by a Go expert sub-agent:

**Structural strengths** (what works):
- Valid JSON every time (when content is non-empty)
- Correct SGF coordinate keys (fd, fe, dc, da, db, ra, pd, sa)
- Voice constraints mostly followed (concise, board-speaks-first, under 15 words)
- All required fields present
- `{!xy}` coordinate tokens in tier-3 hints

**Pedagogical weaknesses** (what needs improvement):
- Comments restate WHAT happens but not WHY or HOW to see it
- No concrete board reasoning (liberty counts, sequence visualization)
- Tier-2 hints are generic platitudes that apply to any problem of the same type
- No transferable skill taught -- student learns the answer, not the method

**Examples of thin vs rich**:
- Thin: "Follow ladder pattern to keep White's liberties low."
- Rich (desired): "Each zigzag move removes one liberty. After F4-F5-G5, White has 2 liberties vs Black's chase giving 3 -- the race is won."
- Thin tier-2: "Maintain zigzag pattern to reduce liberties"
- Rich tier-2: "Count: which direction keeps White's escape route blocked on both sides?"

**Lesson**: The model produces correct scaffolding but the teaching content is surface-level. This is likely because: (1) no KataGo signals are feeding in (no score deltas, liberty counts, PV sequences to cite), and (2) the prompt doesn't explicitly demand concrete board reasoning. Both are addressable.

**Next steps**:
- Test with actual teaching_signals v2 data (KataGo enrichment) to see if concrete numbers improve depth
- Add explicit prompt instructions: "cite specific liberty counts", "describe the punishment sequence move by move"
- Re-evaluate whether tier-2 hints need a stronger specificity requirement in the prompt

---

*-- Add entries here as testing and prompt iteration reveal new insights --*
