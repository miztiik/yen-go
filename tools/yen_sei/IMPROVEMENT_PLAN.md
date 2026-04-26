# yen-sei Improvement Plan — post 2026-04-19 qwen3-32b run

> Triggered by the Azure Foundry full-SFT run on `qwen3-32b` (run id
> `0efc645f4ae947fdacf607a749eaa8ed`, 3 epochs, batch 32, LR×1.0,
> ~2.5M training tokens). Final train loss **1.53**, eval loss **1.48**.
> Loss floor was high not because the model is weak, but because the
> training targets were linguistically broken and schema-noisy. This plan
> is the ordered backlog to fix that before the next training run.
>
> Last updated: 2026-04-20

---

## 0. Diagnosis Summary (what the loss curves told us)

- **Train loss**: 3.8 → ~1.7 in ~30 steps, then noisy plateau 1.5–1.7
  for the remaining ~240 steps. Healthy initial fit; no further learning
  signal in the tail.
- **Eval loss**: artefact of low eval cadence — flat 0 until step ~90,
  then two flat segments (~1.65, ~1.48). Effectively only **3 eval
  points**. No overfitting visible (eval ≈ train) but also no real
  generalization curve to read.
- **Floor at ~1.5** is too high for an SFT generation task. Typical
  well-fit SFT lands at 0.5–1.0. The cap is the data, not the model:
  - Machine-translated CN→EN garbage in `correct_comment`
    (e.g. `"enter work to this,not can avoid (adverb marker) shape form ko fight"`).
  - Templated trivial life/death rows dominate (`"Black has formed two
    eyes and is alive"`).
  - System prompt forbids coordinates but ~30% of targets contain
    `Black 1`, `White 2`, `{!cg}`, `A B miai`, etc. → the model is being
    trained against its own instruction.
  - Hint #2 is just a prefix of the answer in many rows → teaches
    copy-the-prefix, not reasoning.

---

## 1. Improvement Backlog (ordered by impact ÷ effort)

Each item is sized so it can be picked up as a discrete task. **Item #
prefix** is the order we should execute in.

### 1.1 Data quality (highest impact)

#### [P0-1] Inner-content normalization of `correct_comment` and `wrong_comments`

> ⚠️ **Not the delimiters** — those are already enforced by
> `format_tagged_text()` in `tools/core/teaching_schema.py`. The noise is
> *inside* each section.

Add a deterministic regex pass in `stages/refine.py` (or a new
`stages/polish.py` — see [P0-3]) that strips, on every comment string
before it reaches `format_tagged_text`:

- Trailing markdown: `**-> ...**`, `## Correct`, `#Correct!`, `#Incorrect!`
- SGF-leakage syntax: `(;Correct)`, `(;Wrong)`, `(;wrong )`, leading `1 diagram (;…)`
- CN-style stray markers: `(completed)`, `(question)`, `(adverb marker)`
- Boilerplate prefixes: `Correct! `, `Correct: `, `Wrong: `, `RIGHT`, `WRONG`
  at start/end of section bodies (the section delimiter already conveys this).
- Collapse whitespace runs to single space; strip leading/trailing `\n` per section.
- Drop a section body entirely if, after normalization, length < 4 chars.

**Acceptance**: a snapshot test in `tests/` over 50 hand-picked rows;
diff vs golden expected output. No regression in
`tests/test_teaching_schema.py`.

#### [P0-2] Resolve the system-prompt vs. target contradiction

System prompt says *"Do not output move coordinates or solution
sequences"* but ~30% of targets contain `Black 1`, `White 2 to Black 5`,
`A B miai`, `{!cg}`. Pick **one**:

- **Option A (preferred)**: strip coordinates and "Black N / White N"
  ordinals from training targets. Replace with descriptive phrases
  (`the vital point`, `the key cut`) where possible, else delete clause.
  Keeps the system prompt honest.
- **Option B**: drop the "no coordinates" rule from the system prompt
  and let the model emit moves. Simpler, but the downstream consumer
  (`tools/oshie/`) was designed expecting prose-only.

Tracking: pick A unless oshie integration says otherwise. Implement in
the same regex pass as [P0-1].

#### [P0-3] New `polish` stage — LLM-assisted English cleanup of broken comments

This is the meaty one. Detailed design in **§3** below. Goal: turn the
machine-translated CN→EN comments into fluent English without
hallucinating new technical claims.

#### [P0-4] Better hint generation

Currently `_extract_hints()` produces:
- Hint 1: technique tag (good — keep)
- Hint 2: first ~50 chars of `correct_comment` (bad — leaks the answer
  prefix to the model as a "hint")

Replace Hint 2 with a *concept* extracted from tags + technique
(`vital point`, `shortage of liberties`, `eye shape`, `reading
sequence`). If no concept available, omit the hint rather than emit a
prefix.

#### [P0-5] Down-weight templated trivial rows

The "`Black has formed two eyes and is alive`" template appears in
hundreds of rows from `goproblems_difficulty_based` / similar sources.
Cap the share of templated-target rows in the refined corpus to ≤15%
(measured by SimHash / first-N-token cluster). Excess goes to the
overflow sink, not the trash.

### 1.2 Training config (medium impact)

#### [P1-1] Lower LR + more epochs (validates user's instinct)

For full SFT (Azure path, qwen3-32b):
- LR multiplier **0.3** (was 1.0). The noisy plateau is the classic
  "LR too high for the convergence phase" signature.
- Epochs **5** (was 3) to compensate for smaller steps.
- Add **early-stopping on eval_loss patience=2** so we don't waste budget
  if it actually does plateau.

For QLoRA (Colab path, 2-3B): defaults are usually fine; revisit only
after [P0-1..4] land. LoRA r=16, α=32, dropout=0.05 baseline.

#### [P1-2] Eval cadence: every N steps, not per-epoch

The eval curve in this run is uninformative because eval ran only ~3
times. Configure eval every 20 steps so we can:
- Detect overfitting before it costs an epoch.
- See a real loss curve to reason about.

For Azure Foundry: set `evaluation_strategy=steps`, `eval_steps=20` in
the job config (notebook needs a follow-up). For Colab/HF Trainer:
already supported.

#### [P1-3] Hold-out behavioural test set (50–100 hand-curated puzzles)

Loss is misleading for free-form generation. Add a small
`tests/yen_sei_eval/holdout.jsonl` of 50–100 hand-written *good* teaching
examples spanning all techniques. Evaluate post-train with:
- Format compliance (already covered by `eval/scorers.py`).
- Hint quality (LLM-judge, optional).
- Negative check: does any output contain forbidden coordinate strings?

### 1.3 Diagnostics (low effort, high signal)

#### [P2-1] Pre-train data audit script

`python -m tools.yen_sei audit-corpus` should print:

- % rows containing CN→EN garbage markers (regex)
- % rows where target contains coordinate tokens
- length distribution of `correct_comment`
- top 20 most-duplicated targets (catch templated dominance)
- token-overlap between user prompt and assistant target (prompt-leak detector,
  reuses the [LESSONS.md §0] insight)

Run this **before every training submission**. Add a hard fail-gate
threshold (e.g. >10% CN→EN markers → refuse to write `train.jsonl`).

#### [P2-2] Loss-floor target

Add an explicit acceptance criterion in `PLAN.md`: the next run's
`final_eval_loss` must be **≤ 1.0** to be considered worth deploying.
If after [P0-*] cleanup it's still ≥ 1.3, the bottleneck is something
else (model capacity, task spec) and we go back to design.

---

## 2. Validation of User's Proposed Items

User asked whether three suggestions make sense. Verdict:

| User's suggestion                              | Verdict                  | Why / Adjustment                                                                                                       |
| ---------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Standardize delimiters (`---CORRECT---` etc.)  | ❌ Already done           | `format_tagged_text()` enforces exact delimiters. Real noise is **inside** sections. Re-aim as [P0-1].                 |
| Lower learning rate (1.0 → 0.5 / 0.2)          | ✅ Yes                    | Train-loss noise pattern matches "LR too high in tail." See [P1-1] — recommend **0.3**.                                |
| More epochs (3 → 4–5) to compensate            | ✅ Yes, with caveat       | Pair with **early-stopping** ([P1-1]) and **eval-every-20-steps** ([P1-2]) so extra epochs don't silently overfit.     |
| LLM cleanup of broken English (separate JSONL) | ✅ Yes — full design in §3 | Comment-only rewrite is the right shape; pure board-context cleanup is too expensive and risks hallucinated technical claims. |

---

## 3. Design: Polish Stage for Broken-English Cleanup [P0-3]

The user described two ends of a spectrum: (a) extract just comments to
a small JSONL and rewrite via LLM in isolation, or (b) feed the entire
ASCII board so the LLM can validate technical claims. Recommended
design picks the cheap-and-safe middle path.

### 3.1 Pipeline location

```
qualify → ingest → harvest → polish (NEW) → refine
```

`polish` operates on `raw_extracts.jsonl` (output of `harvest`) and
emits `raw_extracts_polished.jsonl` consumed by `refine`. Original
record fields are preserved alongside polished ones for audit.

### 3.2 Three-stage filter (cost ascending)

#### Stage A — Deterministic regex normalization (free, ~ms/record)

Same regex pass as [P0-1]. Reduces ~40% of "broken" cases to clean
text. No LLM needed.

#### Stage B — Language-quality scoring (free, ~ms/record)

For each comment, compute:

- `cn_marker_hits`: count of `(completed)`, `(question)`, `(adverb marker)`,
  `won't work`, `not what (completed)`, `obtain more more`, etc.
- `english_word_ratio`: tokens in a 10k-word English dict / total tokens.
  Threshold: < 0.6 → broken.
- `repeated_word_runs`: e.g. `"miai;Black A when,White B can"` patterns.
- Optional: `langdetect` confidence on EN.

A comment is **flagged for polish** if `cn_marker_hits ≥ 2` OR
`english_word_ratio < 0.6`. Rows with all comments clean **skip stage C
entirely**.

Persist scores in the manifest for forensics.

#### Stage C — LLM rewrite of flagged comments only (cost-controlled)

**Input to LLM** — comment + structured metadata (NOT board ASCII):

```json
{
  "puzzle_id": "abc123def456",
  "node_path": "0.1.2",            // root.correct.deeper-correct
  "role": "correct" | "wrong" | "root",
  "tags": ["ko", "life-and-death"],
  "technique": "throw-in",
  "level": "intermediate",
  "original": "<raw broken-English comment>"
}
```

**System prompt** (locked, versioned):

> You rewrite Go teaching comments into fluent English.
> RULES:
> 1. Preserve only what the original asserts. Do not add new technical claims.
> 2. Do not output board coordinates (e.g. `cd`, `D17`, `{!xy}`).
> 3. Do not output ordinal move references (e.g. `Black 1`, `White 2`).
> 4. Maximum 2 short sentences. Concrete, no filler.
> 5. If the original is uninterpretable, return the literal string `__SKIP__`.

**Why no full board?** Three reasons:
1. ~10× token cost for marginal gain (the technical content is already
   asserted in the comment; we're fixing English only).
2. The LLM may "helpfully" invent technical claims it reads off the
   board, which corrupts the teaching signal.
3. Tags + technique already gives enough context to disambiguate
   `"throw in"` (sacrifice) vs `"throw-in"` (atari tesuji) etc.

If we later find specific records where the cleanup is ambiguous
without board context, we add a **stage D** that re-runs *only those*
with board ASCII attached. YAGNI for now.

### 3.3 Safeguards (prevent LLM hallucination from poisoning corpus)

A polished record is **rejected** (falls back to original) if any of:

- Polished length > 3× original (probably hallucinated content).
- Polished length < 4 chars (LLM refused — keep original or drop).
- Polished contains coordinate regex `\b[a-s]{2}\b` or `\b[A-T]\d{1,2}\b`.
- Polished contains `Black [0-9]+` / `White [0-9]+` ordinal patterns.
- Polished returns `__SKIP__` → comment is removed from that node
  (record still usable if other nodes have content).

### 3.4 Output format

`raw_extracts_polished.jsonl` has same schema as `raw_extracts.jsonl`
plus per-node `comment_polished` and `comment_polish_status` fields:

```json
{
  "puzzle_id": "...",
  "root_comment": "...",
  "root_comment_polished": "...",
  "root_comment_polish_status": "rewritten" | "kept_original" | "rejected_too_long" | "skipped",
  "solution_nodes": [
    {"move": "cd", "is_correct": true,
     "comment": "<original>",
     "comment_polished": "<rewritten or null>",
     "comment_polish_status": "..."}
  ]
}
```

`refine` reads `comment_polished or comment` (fallback). Audit trail
preserved in original fields. Add manifest counters: `polished_total`,
`rejected_too_long`, `rejected_coords`, `skipped_uninterpretable`.

### 3.5 Cost & batching

- Estimated flagged comments: ~30–40% of ~13k extracts × ~3 nodes/extract
  with comments = ~12k comments to rewrite.
- gpt-4o-mini at ~$0.15/1M input tokens, ~$0.6/1M output tokens.
  Avg ~150 in / 50 out tokens per comment = ~$0.30 total. Negligible.
- Batch via Azure OpenAI batch API or local `httpx` with `tenacity`
  (already a project dep) and a 16-way `asyncio.Semaphore`.
- Cache by `sha256(original + system_prompt_version)` in
  `data/polish_cache/` so re-runs are free unless prompt changes.

### 3.6 Spot-check loop

Before the polished file is accepted as the new "latest":
- `python -m tools.yen_sei polish --sample 50` opens 50 random
  before/after pairs in a CLI diff view; user accepts or rejects.
- On reject, the prompt is revised and the run repeated (cache ensures
  only changed records re-bill).

---

## 4. Execution Order

1. **Day 1**: [P2-1] audit script + [P0-1] regex normalization +
   [P0-2] coordinate strip. Re-run `refine`. Re-measure with audit.
   This alone should cut the loss floor noticeably.
2. **Day 2**: [P0-4] hints + [P0-5] templated cap. Re-run `refine`.
3. **Day 3-4**: [P0-3] polish stage — Stage A+B first (no LLM cost),
   then Stage C with a 200-record dry run for prompt iteration.
4. **Day 5**: [P0-3] full polish run + spot-check. Commit polished
   `raw_extracts_polished_latest.jsonl`.
5. **Day 6**: [P1-1] [P1-2] [P1-3] — kick off the next training run
   with new data, lower LR, eval-every-20-steps, holdout test set.
6. **Decision gate**: [P2-2] — if eval loss ≤ 1.0, ship it. Otherwise
   re-open this plan.

---

## 4a. Day-1 Results (2026-04-20) — ✅ DONE

[P0-1] [P0-2] [P0-4] [P0-5] [P2-1] all landed in one pass. The audit
script gives us a quantitative before/after on the same `train.jsonl`
(2,942 rows, train split):

| Metric                       | Before  | After   | Threshold | Status |
| ---------------------------- | ------: | ------: | --------: | :----: |
| Broken-English markers (%)   |   8.2 % |   4.0 % |    10.0 % | ✅     |
| **Coordinate leaks (%)**     |  44.7 % |   0.1 % |     5.0 % | ✅     |
| Top-template cluster share   |   1.9 % |   2.1 % |    15.0 % | ✅     |
| Avg prompt↔target overlap    |   0.3 % |   0.2 % |    30.0 % | ✅     |
| Median `correct_comment` len |   114   |   105   |       —   | —      |

**Headline**: coord-leak rate fell ~450×. The single largest source of
prompt/target contradiction is now gone. Normalization also dropped ~30
borderline rows (whose bodies collapsed below 4 chars), shrinking the
corpus from 2,973 → 2,942 — acceptable.

Top duplicated templates surfaced by the audit are still ~60-row
clusters of "Black has formed two eyes and is alive" — tracked under
[P0-3] (LLM rewrite) where they will be rewritten with concrete
context, not just deduplicated. The 15% template cap [P0-5] is in
place but not yet biting (top cluster 2.1% < 15%).

Files added:
- `tools/yen_sei/governance/text_normalizer.py` — pure-function
  normalizer, idempotent, 27 unit tests.
- `tools/yen_sei/stages/audit.py` — `python -m tools.yen_sei
  audit-corpus [--strict]` CLI.
- `tools/yen_sei/tests/test_text_normalizer.py` — 27 tests covering
  every regex pattern + real verbatim corpus samples.

Files changed:
- `tools/yen_sei/stages/refine.py` — calls `normalize_section_body()`
  on every correct/wrong body before `format_tagged_text`; new
  `_TAG_TO_CONCEPT` map replaces the old answer-prefix-copy hint #2;
  new template-cluster cap (≤15%) gate after example assembly.
- `tools/yen_sei/__main__.py` — wires the `audit-corpus` subcommand.

**Next**: [P0-3] polish stage. Stage A + B (no LLM cost) lands first
to filter which comments actually need rewriting.

---

## 4b. Day-2 Results (2026-04-20) — ✅ Polish stage A+B+C scaffold landed

[P0-3] is in. Pipeline now:

```
qualify -> ingest -> harvest -> polish (NEW, optional) -> refine
```

`polish` operates on `raw.jsonl` and emits `raw_polished.jsonl`. `refine`
prefers the polished file when present, falls back transparently.

**Default mode is dry-run** — runs Stage A (regex normalize) + Stage B
(language-quality score) on every comment and prints a histogram. No
LLM call, no file written. To actually rewrite, pass `--llm`.

### Stage B distribution on the live corpus

`python -m tools.yen_sei polish` (81,578 comments across 3,654 records):

| Status                    |     N | Share |
| ------------------------- | ----: | ----: |
| `empty`                   | 50,201 | 61.5% |
| `flagged_needs_llm`       | 11,054 | 13.6% |
| `too_short_for_llm`       |  8,968 | 11.0% |
| `clean_native`            |  4,939 |  6.1% |
| `clean_after_regex`       |  4,212 |  5.2% |
| `skipped_uninterpretable` |  2,204 |  2.7% |

Stage C (LLM rewrite) would be called on ~11k comments. At gpt-4o-mini
prices (~$0.15/1M in, $0.6/1M out, ~150 in / 50 out tokens each):
**~$2.50 total**, fully cached after first run.

### Stage C design (active, opt-in)

- System prompt v1 (versioned via `POLISH_PROMPT_VERSION = "v1"` —
  bumping invalidates the cache).
- Hallucination guards reject LLM output that:
  - returns `__SKIP__`,
  - grows >3× the original length,
  - contains coordinate refs (regex from day-1 normalizer),
  - is shorter than 4 chars.
- Cache: `data/raw/polish_cache/{sha256[:16]}.json`, keyed on
  `(prompt_version, original)`. Re-runs are free.
- `--sample N` prints N flagged before/after pairs to stdout for
  manual prompt iteration.

### Side fix discovered via sample inspection

`--sample 5 --limit 200` surfaced rows like
`"Black cannot d19 placement, otherwise White e19 block."` —
**lowercase Western coordinates** that the day-1 regex missed
(`[A-HJ-T]` was case-sensitive). Fixed:
`tools/yen_sei/governance/text_normalizer.py::_WESTERN_COORD` is now
case-insensitive. Audit thresholds still all green after re-refine
(coord leaks 0.1%, broken-EN 4.1%, top cluster 2.1%, prompt-leak 0.2%).

### Further fixes from `--sample 50` (then refactored to `tools/core/`)

A second sample run surfaced three more classes of Unicode-script
noise that had been silently passing through:

1. **Geometric board markers** (▲ ■ ▼ ◯ ★ — Unicode block U+25A0-25FF)
   used in CJK SGFs to point at stones in inline ASCII diagrams.
2. **Fullwidth ASCII punctuation** (U+FF0C "，", U+FF1A "：" etc.)
   common in Chinese-translated prose.
3. **Vietnamese-translated comments** (≈10 SGFs, U+1E00-1EFF range plus
   đĐơưăâ) leaking in from a mixed-language source. We can't reliably
   round-trip these to English, so they should bypass the LLM entirely.

Per the user's "no ad-hoc, write reusable utilities" principle, the
fixes were added to `tools/core/text_cleaner.py` (where `strip_cjk`,
`strip_html`, `strip_urls`, `sanitize_for_training` already live) as
four new public helpers:

- `strip_geometric_markers(text)` — removes U+25A0-25FF + ★.
- `normalize_fullwidth_punct(text)` — `，` → `,`, `：` → `:`, etc.
- `contains_vietnamese(text)` — bool detector.
- `strip_vietnamese(text)` — replaces Vietnamese chars with spaces.

`sanitize_for_training` was extended to call them so every downstream
SFT pipeline benefits, not just yen-sei. `text_normalizer.normalize_section_body`
now delegates the Unicode work to these helpers and only owns the
yen-sei-specific Go-prose patterns (boilerplate, CN markers, coords,
ordinals). The polish classifier short-circuits Vietnamese rows
straight to `skipped_uninterpretable` before any LLM call.

### Files added

- `tools/yen_sei/stages/polish.py` — full polish pipeline.
- `tools/yen_sei/tests/test_polish.py` — 17 unit tests (Stage A+B
  classification, Stage C guards, end-to-end with a fake LLM client).

### Files changed

- `tools/core/text_cleaner.py` — added `strip_geometric_markers`,
  `normalize_fullwidth_punct`, `contains_vietnamese`, `strip_vietnamese`;
  extended `sanitize_for_training` pipeline.
- `tools/core/tests/test_text_cleaner.py` — 11 new tests for the above.
- `tools/yen_sei/config.py` — `RAW_POLISHED_JSONL`, `POLISH_CACHE_DIR`.
- `tools/yen_sei/stages/refine.py` — prefers `RAW_POLISHED_JSONL`
  when it exists; transparent fallback to `RAW_JSONL`.
- `tools/yen_sei/__main__.py` — `polish` subcommand
  (`--llm | --sample N | --limit N`).
- `tools/yen_sei/governance/text_normalizer.py` — coord regex
  case-insensitive; delegates to `tools.core.text_cleaner` for
  Unicode-script work.
- `tools/yen_sei/stages/polish.py` — Vietnamese short-circuit in `classify()`.
- `tools/yen_sei/tests/test_text_normalizer.py` — added lowercase coord test.

### Stage B distribution after the refactor

`python -m tools.yen_sei polish` (81,578 comments):

| Status                    |     N | Share | Δ vs. first run |
| ------------------------- | ----: | ----: | --------------: |
| `empty`                   | 50,201 | 61.5% |             0   |
| `flagged_needs_llm`       | 10,999 | 13.5% |           -55   |
| `too_short_for_llm`       |  8,968 | 11.0% |             0   |
| `clean_after_regex`       |  4,248 |  5.2% |           +36   |
| `clean_native`            |  4,917 |  6.0% |           -22   |
| `skipped_uninterpretable` |  2,245 |  2.8% |           +41   |

Vietnamese rows now correctly bypass the LLM. Estimated cost stays
~$2.50 at gpt-4o-mini.

### Test status

123/123 passing (49 yen_sei + 74 core/text_cleaner & friends).

### Stage C decoupled from any specific LLM provider

Per "no ad-hoc, only reusable utilities", the polish stage no longer
embeds a particular HTTP client. Two new public CLIs make the rewrite
backend pluggable:

```
polish-dump-batch  --output batch.jsonl  [--limit N]
polish-load-batch  --input  responses.jsonl
```

`dump-batch` writes one JSON line per pending (uncached) flagged
request, each containing `cache_key`, `system` prompt, `user` prompt,
and the regex-cleaned `original`. Any backend — GitHub Copilot
subagents, OpenAI Batch API, local Ollama, manual human review —
processes the batch and returns a JSONL of `{cache_key, rewritten}`.
`load-batch` writes those into `data/raw/polish_cache/`.

After the cache is populated, `polish --llm` becomes 100% cache hits
with zero network calls. The same workflow works identically on
$0/run (subagents) or $2.50/run (gpt-4o-mini).

Smoke run: `polish-dump-batch --output batch_001.jsonl --limit 50`
emitted **154 pending requests** (first 50 records of `raw.jsonl`).
File format verified.

Tests: 4 new (`test_dump_batch_emits_only_flagged`,
`test_dump_batch_skips_cached_by_default`,
`test_load_batch_populates_cache`, `test_dump_then_load_then_polish_no_llm_call`).
21/21 polish tests pass.

### Decision point before Day 3

Running `--llm` is a real (small) cost. Recommended: have a human review
~50 sample rewrites first by running:
```
python -m tools.yen_sei polish --sample 50 --limit 2000
```
…then a small `--llm --limit 100` smoke run with eyeball QA, then full
`--llm`. The cache means each successful row is paid for exactly once.

---

## 5. Lessons (cross-link to LESSONS.md §12)

The cross-cutting lesson from this run is appended to
[LESSONS.md](./LESSONS.md) as **§12 — Loss Floor Is the Data Floor**.
Headline: *if SFT loss plateaus high and noisy with eval ≈ train, the
ceiling is target quality, not hyperparameters.* Covered fully there.
