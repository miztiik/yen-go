# yen-sei Lessons Learned

Hard-won insights from building the yen-sei SFT pipeline. Each lesson came from a mistake or course correction during development.

---

## 0. Three Things That Quietly Poisoned Training Data (2026-04-18)

**What happened**: After producing what looked like a clean v2.2 SFT corpus
(671 gold + 1,881 silver + 11,381 bronze) and rebuilding the Colab notebooks
to be one-click runnable, the user pointed out three independent issues that
would have wasted ~6 hours of T4 training time:

1. The data directory was a graveyard of `qualification_v2*.jsonl`,
   `qualification_v2.1_baseline.jsonl`, `qualification_v2_STALE_pre_walkbug_fix.jsonl`,
   `qualification_kano_239*`, `qualify_*.log`, `qualify_smoke*` etc. No
   timestamp convention, no auto-cleanup, no obvious "current" pointer.
2. Test prompts included `Context: {root_comment}` — i.e. the SGF root comment
   that often paraphrases the answer. We were leaking the label into the
   input and inflating val/test scores.
3. The pipeline had **zero awareness** of the `YQ.ac` SGF property. KataGo-
   enriched and GPT-4o-enriched puzzles were silently flowing into training
   as "gold" examples — meaning we'd be SFT-ing on the previous generation
   of our own AI's output.

**Why each mattered**:
1. Stale qualification files → ingest could trivially read the wrong vintage
   (it did, twice). No way to know which file was "current" without `dir /OD`.
2. Eval prompt-leak → val/test scores would look great even if the model
   learned nothing. We'd ship a "trained" model that fails on real puzzles
   because real puzzles don't come with their own root comment in the prompt.
3. AI-contamination → defeats the entire reason yen-sei exists, which is to
   learn HUMAN teaching prose, not to recursively distil our own LLM outputs.

**Lesson**: Run a structural sanity audit BEFORE training, not after.
Specifically:
- Every persisted artefact path → POSIX, repo-root-relative, timestamped.
- Every gate that drops puzzles → cheap regex check BEFORE expensive parse.
- Every eval prompt → diff it against the assistant target. If any token
  appears verbatim in both prompt and target, it's a leak.

**Applied**:
- New `tools/yen_sei/data_paths.py` enforces `{kind}_{YYYYMMDDTHHMM}.{ext}` +
  `{kind}_latest.{ext}` pointer + `cleanup_old(keep=3)`. All stages use it.
- New `governance/teaching_signal.py` gates: `ai_enriched` (parses `YQ[ac:N]`,
  drops if N>0) and `ai_signature_prose` (6 templated-LLM-prose regexes,
  drops if >=2 hits). Both run before sgfmill parse.
- New `eval/{scorers,judges,runner}.py` module with three layers (Structural /
  Grounded / Judge). Headline metric is `useful_answer_pct` not raw JSON%.
- `_build_user_prompt` in `stages/refine.py` no longer emits the `Context:` line.

**Cost of NOT doing this**: 6 GPU-hours per training run × however many runs
until somebody noticed the model could only "answer" puzzles that arrived
with their own answer attached. Probably 2-3 runs = ~18 GPU-hours = 1-2
weeks of Colab Free quota. The fix took one afternoon.

---

## 1. Never Copy Data Blindly

**What happened**: First ingest attempt blindly copied ~70,000 SGFs from 3 sources into `data/sources/` based on nothing more than "these directories have SGF files." No quality assessment, no filtering, no understanding of what was actually in the files.

**Why it was wrong**: The 70K included ~23K pure drill files (gotools) with zero teaching content — just "Correct"/"Wrong" markers. Copying them wasted time and would have polluted the training pipeline with noise. For SFT training, data quality matters exponentially more than quantity. 3,000 excellent examples beats 70,000 mediocre ones.

**Lesson**: Always audit data before copying. Build a discovery/scanning tool first. Understand what you're working with. For ML training data, design selection criteria before touching files.

**Applied**: Built `selector.py` with expert-informed scoring criteria. Scanned all 191,794 SGFs, scored each one, selected only 20,154 Tier A puzzles (score >= 0.5).

---

## 2. Consult Domain Experts Before Designing Heuristics

**What happened**: Initial filtering was based on simple heuristics — comment character count > 80, exclude marker words. This misses the point of what makes a Go teaching comment valuable.

**Why it was wrong**: A 100-character comment saying "Black plays here. White responds. Black captures." has length but no teaching value. Meanwhile a 60-character comment explaining "This creates a shortage of liberties (damezumari)" is gold for SFT training.

**Lesson**: For domain-specific data selection, involve domain experts. We consulted Go professional personas (Cho Chikun for pedagogical structure, Lee Sedol for intuitive pattern recognition) to design multi-dimensional scoring: comment quality (40%), technique identification (25%), stone density (15%), reading depth (10%), metadata (10%).

**Applied**: The scoring system now weights technique identification and explanation quality, not just raw character count.

---

## 3. Scan ALL Sources, Not Just the Obvious Ones

**What happened**: Initially planned to use only 3 sources (OGS, GoProblems, GoGameGuru) based on familiarity. Total estimate was ~3,400 usable examples.

**Why it was wrong**: The project has 14 external-source directories with 191K+ SGFs. By scanning ALL sources, we found teaching content in places we wouldn't have looked: classic-books has 734 rich-teaching puzzles, dragon-archive has 2,134 Tier A puzzles, curated-ogs (previously estimated at ~178 usable) actually has 3,692 Tier A puzzles hidden across named collections.

**Lesson**: Don't assume you know where the good data is. Scan everything, let the scoring function find it.

**Applied**: Discovery scan covers all 14 sources. Tier A count went from estimated 3,400 to actual 20,154 — a 6x improvement.

---

## 4. Separate Discovery/Selection From Copying

**What happened**: The original ingest stage had one job: copy files. It didn't know or care about quality.

**Why it was wrong**: This couples "what to copy" with "how to copy" and makes it impossible to audit the selection before committing to it. The user rightly wanted to see a qualification report BEFORE any files were copied.

**Lesson**: Build a two-phase process: (1) scan + score + report, (2) copy. The report is a checkpoint where humans review the selection criteria and results before any data moves.

**Applied**: `selector.py` handles scanning and scoring (produces `qualification_report.txt` and `qualification_scores.json`). `ingest.py` handles copying, using selector scores as its filter. The report is always generated first.

---

## 5. Flat is Better Than Nested (for ML Data)

**What happened**: Initial design maintained per-source subdirectories in `data/sources/` (ogs/, goproblems/, gogameguru/).

**Why it was wrong**: 11 source directories means 11 paths to configure, 11 directory trees to walk, 11 special cases in downstream code. The harvest stage doesn't care where a file came from — it reads SGF content and extracts teaching pairs. Source provenance is metadata, not file system structure.

**Lesson**: For ML training data, use a flat directory with provenance in filenames (`{source}_{name}.sgf`). Downstream stages become trivially simple: glob `*.sgf`, read, process.

**Applied**: Single flat `data/sources/` directory. Source tracked in filename prefix and in the `RawExtract.source` field.

---

## 6. Python Module Names Must Use Underscores

**What happened**: Initial directory was named `tools/yen-sei/` (with a hyphen). Running `python -m tools.yen-sei` failed because Python module names cannot contain hyphens.

**Lesson**: Always use underscores for Python package/module directory names. Check with `python -m` before proceeding.

**Applied**: Renamed to `tools/yen_sei/`.

---

## 7. Absolute Paths in Scripts Are Fragile

**What happened**: The discovery script hardcoded `Path(r"C:\Users\abc\...")` as the external-sources root.

**Why it was wrong**: Breaks on any other machine, any other checkout location. Also violates the "config-driven" principle from CLAUDE.md.

**Lesson**: Always derive paths from `__file__` or a config module. The `config.py` pattern of `TOOL_ROOT = Path(__file__).parent` is correct.

**Applied**: `selector.py` imports `PROJECT_ROOT` from config, doesn't hardcode any absolute paths.

---

## 8. SFT Data Volume: Quality Over Quantity

**What happened**: The temptation was to copy everything that "might" be useful — 70K+ files.

**Why it was wrong**: For LoRA SFT on a 2.3B parameter model, the sweet spot is 3K-10K high-quality examples. More data with thin comments dilutes the training signal. The model learns to generate shallow "Correct. This captures the stone." responses instead of rich teaching explanations.

**Lesson**: For fine-tuning, curate aggressively. It's better to have 3,000 examples where every one demonstrates excellent teaching than 70,000 where most are just "Correct"/"Wrong" markers with a coordinate.

**Applied**: Selected only Tier A (20,154 puzzles, score >= 0.5). After harvest+refine filtering, expect 3,000-5,000 usable SFT examples. Tier B stays in external-sources for synthetic augmentation later.

---

## 9. The Data Isolation Policy Was Right From The Start

**What happened**: We established early that yen-sei should NEVER read from `external-sources/` directly during training stages — only during ingest.

**Why it held up**: This turned out to be crucial. Multiple agents work on external-sources concurrently (crawlers, enrichment tools). If harvest/refine read directly from external-sources, they'd see inconsistent state as other tools modify files. The ingest stage creates a frozen snapshot in `data/sources/`.

**Lesson**: Data isolation policies feel overly cautious until they save you. Keep them.

---

## 10. Filtration Without Tiering Is Useless (the v2 rebuild)

**What happened**: After Lesson 1-9, we *thought* we had quality data. Audit revealed the v1 `sft.jsonl` was **47% garbage**: 44.7% of rows had `correct_comment` ≤ 20 chars (just "Right!" / "Correct!" / "+"), 59.2% had no `wrong_comments` at all. Score-based selection had treated all puzzles equally above the threshold — a problem-with-no-teaching scored the same as a Cho Chikun encyclopedia entry.

**Why it was wrong**: A single binary "qualified / not qualified" decision throws away the teaching-quality signal that the scoring computes. Worse, downstream stages (`harvest`, `refine`) had no way to recover that signal — they treated every file in `data/sources/` as equivalent.

**Lesson**: When ML data quality varies by 10x within your "qualified" set, you need **tiers**, not a threshold. Tiers must be carried in the data itself (not only in metadata) so every downstream stage can reason about them.

**Applied** (yen-sei v2):
1. **Single config-driven source of truth**: `tools/yen_sei/curation_config.json` defines hard gates, tier rules (gold/silver/bronze), per-source caps, weights. No hardcoded thresholds anywhere in `stages/*.py`.
2. **Tier-prefixed filenames**: `gold_goproblems_3300.sgf`, `silver_kisvadim-goproblems_0025.sgf`. Harvest reads tier from filename without parsing SGF — no SGF content pollution.
3. **Weighted upsampling**: Refine emits gold examples 3× into the train split. Val/test stay 1× for clean evaluation.
4. **Tier-aware dedup**: On position-hash collision, keep the **highest-tier** copy (gold > silver > bronze).
5. **Stratified splits**: Splits are stratified per tier so val/test always contain proportional gold/silver/bronze.
6. **Result**: 47% garbage → **0.2%**. Median `correct_comment` length jumped to 100 chars. Final dataset: 8,753 rows from 13,116 ingested (525 unique gold + 1,279 silver + 6,109 bronze).

---

## 11. Per-Tree Signals ≠ Per-Response Signals

**What happened**: After v2 tier system was in place, we still saw 18.8% of rows with thin `correct_comment` (≤20 chars). Investigation: the qualify stage measured teaching-quality signals across the **entire SGF solution tree** (e.g., "tree has 100+ chars of correct explanation"), but the refine stage's `_build_assistant_response` was emitting only the **first** correct node's comment — which could be a marker like "Right!" while the rich explanation lived on a deeper node.

**Lesson**: When you score data at one granularity and serve it at another, you have a leak. Either your serving function must reconstruct everything you scored, or you must add a serving-side gate that re-checks the same property.

**Applied**:
1. `_build_assistant_response` now picks the **longest** correct-path comment (not the first).
2. Added a final response-quality gate in refine: drop any example where the assembled `correct_comment < 40 chars` AND no `wrong_comment ≥ 40 chars`.
3. Result: thin correct_comment dropped to **0.2%**, worst-case garbage to **0%**.

---

## 12. Pre-Parse Gates Save Worker Pools From Going Stuck

**What happened**: First parallel scan of all 209K SGFs got stuck at 75K because a few enormous game-record SGFs (>100KB, thousands of branches) caused `sgfmill.parse` to hang for minutes. With `pool.map(chunksize=100)`, the slow worker blocked the whole chunk.

**Lesson**: For multiprocessing pools over heterogeneous file collections, add cheap pre-parse gates BEFORE invoking expensive parsers. File-size and structural-shape checks (`(` count) catch outliers without spinning up the parser.

**Applied** in `qualify.py`:
- File-size gate: `> 256 KB` → skip without parsing (real tsumego are < 50KB).
- Branch-count gate: `(` count `> 500` → tagged `looks_like_full_game`, drop.
- After these gates, 209K files scan in ~15 min at 228 files/sec on 11 workers (`pool.map(chunksize=50)`).


---

## 13. Structural Proxies Hide Behind Hard Gates  Make Them Soft When Content Can Speak

**What happened**: `min_variations: 2` was a hard gate intended to mean *"this puzzle teaches both right AND wrong moves."* But that's a **structural proxy** for a **content goal**. Classic-book sources (Xuan Xuan Qi Jing, Harada, etc.) put wrong-move analysis in PROSE inside a single big `C[]` comment instead of in tree branches. With the structural gate firing first, 93.4% of one rich enriched folder was dropped despite avg 151 char correct comments + book citations.

**Why per-source overrides are an anti-pattern**: When you're planning to enrich dozens of future directories, source-name-based `hard_gate_overrides` don't scale. Each new source becomes a config edit + a re-test cycle. Worse, future agents won't know the override exists.

**Lesson**: When a hard gate is a *proxy* for what you actually want, replace it with a content-shape OR. Add a **prose_fallback** that looks at the same content the rest of the pipeline already counts (correct chars + a refutation-language vocabulary). Both branches are content-driven, neither names a source.

**Applied** in `curation_config.json` + `teaching_signal.py`:
- New `HardGates.prose_fallback` block (enabled by default, 27 refutation phrases, min 150 correct chars + 2 phrase hits).
- `teachable_content` gate fires when `variation_count >= 2` OR (`correct_chars >= 150` AND `refutation_phrase_count >= 2`).
- Result on full 209K scan: **+320 bronze, 0 change in gold/silver, -387 `no_variations` failures**. No regressions on existing sources, no per-source rules introduced. Xuan Xuan folder went 23 -> 49 promoted.

**Heuristic**: If a hard gate's failure rate looks suspicious in one folder, ask whether the gate is structural-by-shape but the underlying intent is content-by-meaning. If yes, OR-in a content-shape escape.


---

## 14. Tier Rules Have the Same Structural-Proxy Problem as Hard Gates

**What happened**: After fixing the `min_variations` hard gate (Lesson #13), Xuan Xuan Qi Jing puzzles passed the gate as bronze but **none reached gold or silver**. The gold tier required `min_wrong_explanation_chars: 50` (chars on incorrect SGF tree branches) and `min_explanation_node_count: 2` (number of distinct commented tree nodes). A Xuan Xuan puzzle like `0261.sgf` with **6,094 chars of brilliant English commentary citing Go Seigen and Takagi Shoichi** scored `wrong_chars=0, node_count=1` because everything was in one root C[].

**Why this matters**: Same structural-proxy problem at a different layer. The tier ceiling silently re-imposed the constraint we just removed at the gate. Without fixing both, prose-rich gold-quality puzzles get demoted to bronze (×1 weight) instead of gold (×3 weight) — losing the very content the model would learn most from.

**Lesson**: When you replace a structural proxy with a content-shape OR at the gate level, audit ALL downstream rules that count the same structural proxy. Any rule that says "must have N tree branches" or "must have wrong-branch chars" needs a parallel content-shape OR.

**Applied** in `curation_config.json` + `tier_classifier.py`:
- New optional `prose_path` block per tier rule (gold + silver, not bronze).
- New `_passes_prose()` function: tier passes if structural OR prose path satisfied.
- Gold prose threshold: `correct_chars>=400` AND `refutation_phrase_count>=5` AND `causal_phrases>=5` AND `technique_mentions>=3`.
- Silver prose threshold: `correct_chars>=200` AND `refutation_phrase_count>=3` AND `causal_phrases>=2` AND `technique_mentions>=1`.
- Result on full 209K: **gold 546 -> 620 (+74), silver 1462 -> 1838 (+376), bronze 11429 -> 10979 (-450), drop unchanged at 200359**. Authors gold went 0 -> 8.

**Heuristic**: When introducing an alternative content path at one layer, grep the codebase for the structural property name (e.g. `wrong_explanation_chars`, `explanation_node_count`) and check every downstream consumer. Each one is a candidate for the same OR-in pattern.


---

## 15. Untracked Code Hides Silent Regressions ` Commit Early

**What happened**: After running the v2.1 full-corpus qualify scan and producing `qualification_v2.jsonl` with tier counts (546 gold, 11K bronze, etc.), I built v2.2 (added prose_path to tier rules) and re-classified the JSONL in-place using `classify()` on the existing signals. When the user asked "how many gold puzzles?", I reported 620. Then they asked about adding new directories, so I built `qualify --path <dir>` and tested it on the Xuan Xuan folder. The single-folder preview reported **16 gold** for Xuan Xuan but the main jsonl said **8 gold** for the entire authors source. Investigation showed `extract_signals()` produced DIFFERENT signal values now than what was in the main jsonl (e.g. cor=1463/nodes=7 vs cor=741/nodes=2 for the same file). Root cause: somewhere between the v2.1 scan and the v2.2 work, `_walk()` recursion in teaching_signal.py changed (most likely an early-return on incorrect branches was removed). The whole baseline was therefore stale.

**Why I couldn't tell when/why it changed**: `tools/yen_sei/` was never committed to git. No history, no diff baseline, no review trail. The bug was real but invisible.

**Lesson**: Untracked code in a long-running multi-session project is a silent-regression factory. Rules that look stable today silently mutate tomorrow. The 47%-garbage v1 we burned at the start of this work is the same kind of failure: signals that were "right" at one point become "wrong" because no one notices when behavior changes. Commit code (NOT the .jsonl/.sgf data files) early so that:
- ``git diff`` shows what changed in the rule engine.
- A re-scan that produces unexpectedly different numbers immediately points to a known commit.
- New session contributors know "this is the active rule" vs "this is in-progress experiment".

**Applied**:
- Added .gitignore entries for `tools/yen_sei/data/*.jsonl` and `tools/yen_sei/data/*.txt` (data, not code).
- Committed `tools/yen_sei/**.py`, `tools/yen_sei/**.json`, `tools/yen_sei/**.md` (code + config + docs).
- Re-ran full qualify on 213K corpus with current code; preserved the stale jsonl as `qualification_v2_STALE_pre_walkbug_fix.jsonl` for forensic comparison.

**Heuristic**: If a tool ships a "config-driven rule engine" — commit it. The whole point of config-driven is that you can audit/revert/diff changes. Without git, you've recreated the problem you set out to solve.

