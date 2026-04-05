# Kisvadim SGF Enrichment — Agent Handover Prompt

> Use this prompt to parallelize SGF enrichment across kisvadim-goproblems source directories.
> Each agent handles ONE source directory end-to-end.

## Context

The `external-sources/kisvadim-goproblems/` directory contains 63 subdirectories of Go/Weiqi tsumego puzzle files in SGF format, sourced from the kisvadim GitHub collection. Each directory represents one book or collection by a specific author.

**State file**: `tools/kisvadim_goproblems/_enrichment_state.json` — single source of truth for per-directory status (`done`/`pending`), collection slug mapping, chapter mapping, and volume offsets. Check this file before starting work on any directory. Update it when work is complete.

## Enrichment Pipeline (per directory)

Execute these steps IN ORDER for a given `SOURCE_DIR`:

### Step 0: Author Verification (Internet Research)

**MANDATORY before any file changes.** Use a sub-agent (`subagent_type: general-purpose`) with web search to verify:

1. **Author identity**: Search for the author name (from directory name) + "Go" / "Baduk" / "Weiqi" / "professional". Confirm:
   - Full romanized name (given name + family name)
   - Original script (kanji / hangul / Chinese characters)
   - Professional rank and affiliation (Nihon Ki-in, Hanguk Kiwon, etc.)
   - Notable achievements (titles won, career highlights)
2. **Book attribution**: Search for the book title. Confirm:
   - The author listed in the directory name actually wrote this book
   - Alternate titles (original language, translations)
   - Publisher (if available)
   - If attribution is uncertain, flag it — do NOT proceed with a potentially wrong author name in the slug
3. **Name disambiguation**: If the author has a common surname (e.g., Kobayashi, Lee, Kim, Chen), verify which specific professional is meant. Search with kanji/hangul to confirm identity.

**Output**: A brief factual summary with confirmed author name, rank, and book attribution. If attribution cannot be confirmed, escalate to the user before proceeding.

### Step 1: Survey

Gather facts before making any changes:

```
- Count SGF files (total, per subdirectory if chapters exist)
- Check encoding: read first file as bytes, look for CA[] property or try UTF-8/GB2312/GBK
- Check for CJK: scan C[], N[], GN[], EV[] for Chinese/Japanese characters
- Check for non-standard properties: AP[], GN[] (if not YENGO format), EV[]
- Check for existing YL[]: any files already have collection membership?
- List chapter subdirectories (if any)
- Sample 3 files and print their full content
```

Report findings before proceeding.

### Step 2: Identify Author & Collection

1. **Author name**: Use the verified name from Step 0. Cross-check against `config/cn-en-dictionary.json` author_names section. Use FULL romanized name (e.g., "Yamada Kimio" not just "Yamada", "Kobayashi Satoru" not just "Kobayashi").
2. **Collection slug**: Format as `{author-full-name}-{book-short-title}`, e.g., `yamada-kimio-basic-tsumego`, `hashimoto-utaro-1-year-tsumego`.
3. **Check `config/collections.json`**: Does a collection already exist for this book? If yes, use that slug. If no, register a new one with the next available ID.
4. **Slug full-name compliance check**: If an existing slug uses a shortened name (e.g., `kobayashi-basic-tesuji` instead of `kobayashi-satoru-basic-tesuji`), it MUST be renamed to use the full author name. Follow the **Slug Rename Checklist** (Lesson Learned #16) before proceeding with any enrichment.
5. **Cross-source dedup check**: Search for published puzzles already using this collection slug:
   - Grep `yengo-puzzle-collections/sgf/` for the slug in `YL[]` properties — count existing published puzzles
   - Grep `external-sources/` (all subdirectories, not just kisvadim) for the slug — check if other sources already contributed to this collection
   - If puzzles are already published under this slug from another source, record the count and note that this kisvadim source will add to (not replace) the existing collection. Sequence numbers for YL[] embedding must account for the existing puzzle count (use `volume_offset` in `_enrichment_state.json`).
   - If the existing puzzles may overlap with the new source (same author, similar count), investigate dedup before embedding — the pipeline's content-hash dedup will catch identical positions but not near-duplicates.

### Step 3: Normalize file names

Rename all SGF files to 4-digit zero-padded format (`0001.sgf`, `0002.sgf`, ...) using natural sort order. This must happen BEFORE YL embedding since sequence numbers depend on sorted file order.

```python
import re
from pathlib import Path

def natural_sort_key(name: str):
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

source_dir = Path("external-sources/kisvadim-goproblems/SOURCE_DIR")
# For each leaf dir (or source_dir itself if flat):
sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: natural_sort_key(p.name))
# Two-pass rename to avoid collisions
temp_map = []
for i, sgf_path in enumerate(sgf_files, 1):
    new_name = f"{i:04d}.sgf"
    if sgf_path.name != new_name:
        temp_path = sgf_path.parent / f"_tmp_rename_{i:04d}.sgf"
        sgf_path.rename(temp_path)
        temp_map.append((temp_path, new_name))
for temp_path, new_name in temp_map:
    temp_path.rename(temp_path.parent / new_name)
```

Handles: `Problem (N).sgf`, `NNN.sgf`, `NNNN.sgf`, and any non-standard naming.

### Step 4: Prepare (re-encode + clean)

Run the prepare tool:

```bash
python -m tools.kisvadim_goproblems prepare --source-dir "external-sources/kisvadim-goproblems/SOURCE_DIR"
```

This does:
- Detect encoding via CA[] property (GB2312, GBK, UTF-8)
- Re-encode to UTF-8
- Parser/builder round-trip (drops AP[], GN[], and other non-whitelisted properties)
- Preserves root C[] comments and move-level C[] comments

If the tool doesn't cover your needs (e.g., unusual encoding), write an inline script using the same pattern:
```python
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_builder import SGFBuilder

tree = parse_sgf(sgf_text)
builder = SGFBuilder.from_tree(tree)
builder.metadata.pop("AP", None)
builder.metadata.pop("GN", None)
clean_sgf = builder.build()
```

### Step 5: Embed YL[] (collection membership)

**If directory has chapter subdirectories:**

1. Create `embed.json` in the source directory:
```json
{
  "collection_slug": "author-name-book-title",
  "source_dir": "DIRECTORY NAME",
  "chapters": {
    "CHAPTER 1": "1",
    "CHAPTER 2": "2",
    "Some Named Dir": "named-slug"
  }
}
```

2. Run:
```bash
python -m tools.kisvadim_goproblems embed-chapters \
  --source-dir "external-sources/kisvadim-goproblems/SOURCE_DIR" \
  --mapping "external-sources/kisvadim-goproblems/SOURCE_DIR/embed.json"
```

**If directory has NO chapter subdirectories (flat list of SGFs):**

Use the phrase-match strategy or write inline:
```python
# Simple YL embedding for flat directories
import re
from pathlib import Path

source_dir = Path("external-sources/kisvadim-goproblems/SOURCE_DIR")
slug = "collection-slug-here"

for i, sgf_path in enumerate(sorted(source_dir.glob("*.sgf")), 1):
    content = sgf_path.read_text(encoding="utf-8")
    if "YL[" in content:
        continue  # already embedded
    # Insert YL after PL[B] or PL[W], or after the first property
    content = re.sub(
        r'(PL\[[BW]\])',
        rf'\1YL[{slug}:{i}]',
        content,
        count=1,
    )
    sgf_path.write_text(content, encoding="utf-8")
```

### Step 6: Translate CJK comments

Only if Step 1 found CJK characters in C[] or N[] properties.

```bash
python -m tools.kisvadim_goproblems translate --source-dir "external-sources/kisvadim-goproblems/SOURCE_DIR"
```

If fragments remain (exit code 1), the local dictionary is missing entries. **Do NOT guess translations.** Instead:

1. **Extract untranslated fragments**: Run with `--output-fragments` (or manually collect from the error output) to produce a `_cjk_to_translate.json` file listing all missing phrases.
2. **Use a sub-agent for translation**: Launch a sub-agent (`subagent_type: general-purpose`) with web search access, providing the fragment list. The sub-agent should:
   - Search for each phrase's meaning in Go/Weiqi context (not just literal translation)
   - Distinguish between Go terminology, general Chinese/Japanese vocabulary, and proper nouns
   - Return a mapping of `{original: translated}` pairs with confidence levels
   - Flag any phrases that are ambiguous or context-dependent
3. **Add to dictionary**: After human review of the sub-agent's output, add confirmed translations to `config/cn-en-dictionary.json` in the appropriate section (`go_terms`, `common_phrases`, `connectors_and_particles`, or `author_names`).
4. **Re-run translate**: Run the translate command again. Repeat until exit code 0 (zero remaining fragments).

**Important**: The dictionary is a shared resource. All additions must be accurate Go-domain translations, not generic machine translations. When in doubt, preserve the original CJK text rather than insert a bad translation.

### Step 7: Merge N[] into C[]

Run the merge tool:

```bash
python -m tools.kisvadim_goproblems merge-node-names \
  --source-dir "external-sources/kisvadim-goproblems/SOURCE_DIR"
```

This preserves branch labels (correct/wrong/variation) in C[] comments before the pipeline drops N[].

### Step 8: Verify

Final verification scan:

```bash
python -m tools.kisvadim_goproblems verify --source-dir "external-sources/kisvadim-goproblems/SOURCE_DIR"
```

Additionally check:
```python
# Check: YL[] present in all files, no AP/GN/EV, no N[], files are 4-digit named
for sgf_path in source_dir.rglob("*.sgf"):
    content = sgf_path.read_text(encoding="utf-8")
    assert "YL[" in content, f"Missing YL: {sgf_path}"
    assert "AP[" not in content, f"AP not removed: {sgf_path}"
    # Check N[] removed
    assert not re.search(r'N\[', content), f"N[] not merged: {sgf_path}"
```

Report per-directory summary:
- Total files
- YL coverage (should be 100%)
- CJK remaining (should be 0)
- Any errors

### Step 9: Register in collections.json (if new)

If the collection doesn't already exist in `config/collections.json`, add it:

```json
{
  "slug": "author-name-book-title",
  "name": "Author Name: Book Title",
  "description": "Brief description",
  "curator": "Author Name",
  "source": "kisvadim-goproblems",
  "type": "authored",
  "ordering": "sequential",
  "tier": "reference",
  "aliases": [],
  "id": NEXT_AVAILABLE_ID
}
```

## Environment

- Repo root: `c:\Users\kumarsnaveen\Downloads\NawiN\personal\gitrepos\yen-go`
- Platform: Windows 11, bash shell
- Always use `PYTHONIOENCODING=utf-8` for Python commands
- SGF parser: `tools.core.sgf_parser.parse_sgf()`
- SGF builder: `tools.core.sgf_builder.SGFBuilder.from_tree()`
- Translator: `tools.core.chinese_translator.ChineseTranslator`
- Dictionary: `config/cn-en-dictionary.json` (~1566 entries, growing)
- JP Dictionary: `config/jp-en-dictionary.json` (v1.0, ~569 entries — Go terms only, NOT for prose translation)
- Collections: `config/collections.json` (172 entries, check `max(id)+1` for next available ID)

## Important Rules

1. **Never use regex for SGF property manipulation** when the parser/builder round-trip is available
2. **Never use `git stash`, `git reset --hard`, `git clean`** — other work may be in progress
3. **Stage only YOUR files** — `git add` specific paths, never `git add .`
4. **Test before writing** — always `--dry-run` first
5. **Track failures** — if any step fails, report which files and why
6. **Dictionary is shared** — do NOT modify `config/cn-en-dictionary.json` without coordinating. Instead, output `_cjk_to_translate.json` with missing fragments for later batch update
7. **collections.json is shared** — check for slug conflicts before adding. Use next available ID

## Translation Policy

All CJK (Chinese/Japanese/Korean) content must be translated using **full cultural translation**, not literal word-for-word dictionary mapping. This applies to ALL Go Seigen and future enrichment work.

### Principles

1. **Intent preservation**: Translations must capture the Go/Weiqi tactical and strategic meaning, not just literal word equivalents. A phrase like 全军覆灭 should become "total annihilation" (capturing-race context), not "whole army destroyed."

2. **No bilingual preservation**: Do not keep original CJK alongside translations. The translated text replaces the original completely.

3. **No partial translation**: Every CJK string must be fully translated. Do not leave fragments untranslated.

4. **Sub-agent mandatory**: For ALL CJK translation work, launch a sub-agent with Go expert persona (professional-level knowledge). Do NOT rely solely on `cn-en-dictionary.json` or `jp-en-dictionary.json` word-by-word matching. The dictionary is a cache of confirmed translations, not a translation engine.

5. **Cultural context**: Four-character idioms (成語/Chengyu), literary allusions, and Go proverbs must be translated with cultural significance preserved. Example: 寿石不老 = "The Long-Lived Stone Does Not Age" (a metaphor for stones that survive on the board).

6. **Japanese vs Chinese**: Distinguish between Chinese (Simplified/Traditional) and Japanese content. Japanese prose commentary should be translated by a Japanese-language-capable sub-agent, not the Chinese translator. The `jp-en-dictionary.json` is for isolated Go term headers only, not connected prose.

7. **Attribution/watermark stripping**: Digitizer URLs, email addresses, and website watermarks (e.g., flygo.net, zypzyp) are stripped entirely — they are not author content. If digitizer credit is desired, add it to the collection's `description` field in `collections.json`, not in individual SGF comments.

### Workflow

1. Survey CJK content with `translate --dry-run` to get fragment list
2. Launch sub-agent with Go expert persona to translate ALL fragments
3. Review translations for Go domain accuracy
4. Add confirmed translations to appropriate dictionary section
5. Re-run translate to apply
6. Verify 0 remaining CJK fragments

## Directory Status

See `_enrichment_state.json` for the full per-directory state (63 directories, 38 done, 25 pending). That file is the single source of truth — do not duplicate status here.

## Lessons Learned

1. **GB2312 encoding**: All kisvadim files with `CA[gb2312]` are GB2312-encoded. `_prepare.py` handles detection and re-encoding.
2. **Watermark removal**: `飞扬围棋出品` (FeiYang Go product) appears in ~1900 files as a C[] watermark. Added to dictionary as empty string for stripping.
3. **N[] preserved by parser/builder**: Tested April 2026: `parse_sgf()` → `SGFBuilder.from_tree()` → `build()` DOES preserve N[] on non-root nodes. The correct pipeline order is: prepare (re-encode to UTF-8) → merge N[] into C[] (requires UTF-8) → translate → embed. The merge tool (`_merge_n_into_c.py`) reads files as UTF-8 only, so prepare MUST run first.
4. **CJK vocabulary is small**: Hashimoto used only 19 unique phrases. Dictionary needed only 13 new entries. Survey CJK first to estimate scope.
5. **Multi-volume sequence offsets**: Store `volume_offset` per directory in the state file for cross-volume numbering.
6. **Collection naming**: Full author name in slugs. Numbers retained only when part of published title. Consult domain experts for proper romanization.
7. **Chapter IDs**: Use directory names (e.g., `elementary`, `intermediate`, `advanced`) not integers in YL[] chapter slots.
8. **File name normalization**: Always rename to 4-digit zero-padded (`0001.sgf`) BEFORE embedding. Two-pass rename avoids collisions. Natural sort handles `Problem (N).sgf` patterns.
9. **Japanese content requires different handling**: `MAEDA TSUMEGO Tsumego Masterpieces` contains Japanese literary commentary (hiragana/katakana + kanji), NOT Chinese. Do NOT run `ChineseTranslator` on Japanese text — it garbles the output by replacing hiragana particles (の, は, を, に, で, か) with English glosses that destroy sentence structure. Use `config/jp-en-dictionary.json` ONLY for isolated Go term headers (e.g., `黒先白死` → "Black to play, White dies"), not full literary prose. Preserve original Japanese where it has scholarly/historical value.
10. **Dictionary-based JP translation is destructive on prose**: The JP-EN dictionary works for isolated terms but fails catastrophically on connected prose. If a file contains full Japanese sentences, preserve the original text. Only translate structured headers (e.g., `第N図「XXX」` puzzle intent lines). If you accidentally garble text, reverse-translate using the dictionary's inverse mapping, then fix bracket pairing (`「`→`」` alternation).
11. **Slug naming convention**: Use `{author-full-name}-{book-short-title}` pattern. For Japanese level names: SHOKYU=beginner, CHUKYU=intermediate, JOKYU=advanced. When renaming existing slugs, move old slug to `aliases[]` array. Also update `tools/consolidate_collections.py` SLUG_MAP with old→new mappings, and grep for old slug references in published SGFs.
12. **Cross-source dedup**: When a kisvadim directory matches an existing OGS collection (same author, same puzzle count, same level), map to the existing collection slug rather than creating a new one. SHOKYU/CHUKYU matched OGS ids 96/97 by identical puzzle counts (225/210).
13. **Maeda enrichment script**: `tools/kisvadim_goproblems/_enrich_maeda.py` orchestrates all 10 MAEDA directories in one run with `--type A|B|C` filtering. Can be used as a template for future batch enrichment scripts.
14. **General Chinese vocabulary in teaching comments**: Teaching-comment-rich directories (like SHOKYU, Newly Selected Continued) use general Chinese vocabulary beyond Go terminology. The `cn-en-dictionary.json` `connectors_and_particles` section now has ~370 entries covering common characters (复杂, 找, 续, 念, etc.). Survey remaining CJK fragments after first translate pass, batch-add to dictionary, re-translate.
15. **Non-standard SGF properties**: Some sources use MK[] (markers), LB[] (labels with GBK artifacts), ID[] (numeric problem IDs), FF[1] (old format version). The prepare step's parser/builder round-trip handles most, but MK[] and ID[] may need explicit stripping if the parser whitelist doesn't catch them.
16. **Slug rename checklist** (mandatory when renaming any collection slug):
    1. Update `config/collections.json`: change `slug`, move old slug to `aliases[]`
    2. Update `tools/consolidate_collections.py`: add old→new mapping in `SLUG_MAP`
    3. Grep published SGFs (`yengo-puzzle-collections/sgf/`) for old slug references and update them
    4. Grep source SGFs (`external-sources/`) for old slug in `YL[]` properties and update them
    5. Check `_enrichment_state.json` `slug` fields for old references
    If collapsing one collection into another (e.g., ID 20→21), remove the absorbed entry entirely from `collections.json` (gap in IDs is expected and normal — IDs are stable identifiers, never reused).
17. **Fujisawa Shuuko worked example**: The `FUJISAWA SHUUKO - A Collection of Original Tsumego Masterpiece` directory (163 SGFs, 4 chapter subdirs) maps to:
    - Canonical slug: `fujisawa-shuuko-tsumego-masterpiece` (ID 21)
    - Chapters: `elementary` (40), `intermediate` (39), `advanced` (61), `high-dan` (23)
    - YL format: `fujisawa-shuuko-tsumego-masterpiece:elementary/1` through `high-dan/23`
    - Collection ID 20 (`fujisawa-tsumego-graded`) was collapsed into ID 21 — its aliases absorbed, old slug added to aliases and SLUG_MAP.
    - ID 19 (`fujisawa-shuuko-tsumego-classroom`) kept as placeholder for 藤沢秀行詰碁教室 (Yomiuri 1980).
    - ID 126 (`fujisawa-shuuko-fuseki-exercises`) is a separate book (Fuseki-Ubungen, Lehwald 1977), different source (OGS).
    - Two-format source: Elementary files had no CA[] header (gbk-fallback), rest had CA[gb2312]. Elementary had N[] labels, rest used C[] for variation labels. Running prepare→merge→translate→embed-chapters handled both formats correctly.
    - 69 new CN-EN dictionary entries added to cover Fujisawa's commentary vocabulary.
18. **Author verification is mandatory**: Directory names in kisvadim-goproblems are not authoritative for author attribution. Some books may be misattributed (e.g., a Cho Chikun book labeled as Kobayashi Satoru). Always verify authorship via internet research (Step 0) before committing a slug. If attribution cannot be confirmed, flag to the user — do not guess.
19. **Slug full-name normalization**: Existing collection slugs created before the full-name convention was established may use shortened names (e.g., `kobayashi-basic-tesuji` instead of `kobayashi-satoru-basic-tesuji`). When working on a directory, check the existing slug for full-name compliance. If it needs renaming, execute the Slug Rename Checklist (#16) as a prerequisite step before any enrichment work. This includes updating published SGFs that already reference the old slug.
20. **Cross-source published puzzle accounting**: Before embedding YL[], always check how many puzzles are already published under the target collection slug. If 59 puzzles exist from OGS and the kisvadim source has 105 files, some may overlap (content-hash dedup catches identical positions) and sequence numbering must be coordinated. Record existing published count in the survey report.
21. **Sub-agent for CJK translation**: When CJK fragments are not in the local dictionary, do NOT guess translations. Launch a sub-agent with web search to research each phrase in Go/Weiqi context. The sub-agent should distinguish Go terminology from general vocabulary and return confidence-rated translations for human review before dictionary updates.
22. **Kada Katsuji worked example**: 3 directories (Brilliances 216, Class 48, Masterpieces 436 = 700 total puzzles):
    - Author: 加田克司, Kada Katsuji 9p, Nihon Ki-in. "Tsumego no Kamisama" (God of Tsumego). 1931-1996. Kitani dojo.
    - Books: 衆妙詰碁 (Brilliances, 4 vols, 1993-94), 加田詰碁教室 (Class, 1971), 傑作詰碁 (Masterpieces, 8 vols, 1988-91). All published by Seibundo Shinkosha (except Class by Nihon Ki-in).
    - Collection IDs: 171 (brilliances), 172 (class), 173 (masterpieces).
    - Chapters: `vol-1` through `vol-N` for multi-volume sets; flat (no chapters) for single-book Class.
    - CJK content: Brilliances had watermark + `正解图`/`变化图`/`失败图` only (dictionary-covered). Class had rich teaching commentary (22 new dictionary entries needed). Masterpieces had GN[]/EV[] with CJK numbering (stripped by prepare, no C[] CJK content).
    - Masterpieces VOL.1 had 58 files (others 54) — publisher variation, accepted as-is.
    - Pipeline order: rename → prepare → merge N[] → translate → embed YL[] → verify.
    - No cross-source dedup needed (Kada exists only in kisvadim-goproblems).
23. **Flat collection YL[] format**: For single-book collections without chapters, embed as `slug:N` (e.g., `kada-katsuji-tsumego-class:1`). Use inline Python script with regex insertion after `PL[]` or `SZ[]` since the `embed-chapters` command requires chapter subdirectories.
24. **embed-chapters mapping path**: The `--mapping` argument for `embed-chapters` CLI command must be an absolute path, not relative. Relative paths are resolved from the tool module directory, not the repo root.
25. **Dictionary entry workflow**: Run `translate --dry-run` first to get the list of remaining CJK fragments. If <30 fragments, use a sub-agent with Go master persona to translate them contextually. Add entries to the `connectors_and_particles` section of `cn-en-dictionary.json`. Re-run `translate --dry-run` to confirm 0 remaining, then run actual translate. This two-pass approach (dry-run → add entries → real run) is the standard workflow.
26. **Multi-game SGF files**: Some kisvadim sources have multiple `(;GM[1]...)` game trees concatenated in a single file. The `parse_sgf()` parser processes only the first tree. After prepare, each file contains one clean game tree — the additional games are silently dropped. If puzzle count doesn't match expected, check the original files for multi-game concatenation.
27. **Kobayashi Satoru semeai tesuji worked example**: `KOBAYASHI SATORU 105 BASIC TESUJI FOR 1~3 DAN` (105 SGFs, flat directory):
    - Author: 小林覚, Kobayashi Satoru 9p (b. 1959), Nihon Ki-in. Student of Kitani Minoru. Won Kisei + Gosei 1995. Chairman of Nihon Ki-in 2019.
    - Book: 攻め合いの手筋 (Semeai Tesuji), Go Pocket Series #17 (Seibido Shuppan, June 2003). ISBN 4415023894. Difficulty: 1-dan to 3-dan.
    - The directory name says "Basic Tesuji" but the book is specifically about **semeai** (capturing races). Proper title research via Sensei's Library (SemeaiTesuji page) revealed the true scope. Do NOT trust directory names for book titles.
    - Slug renamed: `kobayashi-basic-tesuji` → `kobayashi-satoru-semeai-tesuji` (ID 43). Old slug moved to `aliases[]`. 104 published SGFs updated. SLUG_MAP updated.
    - 4 chapters (flat file, no subdirs — chapter boundaries by problem number):
      - `fundamental` (1–35): 攻め合いの基本手筋３５問
      - `dan-level` (36–70): 攻め合いの有段手筋３５問
      - `high-dan` (71–90): 攻め合いの高段手筋２０問
      - `strength-test` (91–105): 腕だめしの手筋１５問
    - YL format: `kobayashi-satoru-semeai-tesuji:fundamental/1` through `strength-test/15`
    - SGF content: Extremely clean — no CJK, no C[] comments, no N[], no CA[] header. Just `SZ[19]FF[4]` + stone positions + solution branches. Steps 4 (prepare), 6 (translate), 7 (merge) are trivial or skippable.
    - Cross-source: 104 puzzles already published from other sources (OGS/mixed). Content-hash dedup in the pipeline handles identical positions. The kisvadim source adds the authoritative chapter structure + collection membership.
28. **Book title research is mandatory**: Directory names in kisvadim-goproblems often use translated/simplified titles that misrepresent the actual book content. "105 Basic Tesuji" was actually a semeai-specific book. Always verify the actual book title and subject via Sensei's Library, Amazon.co.jp, or ISBN lookup before creating collection slugs. A misleading slug (e.g., `basic-tesuji` for a semeai book) confuses users and damages collection credibility.
29. **Go Seigen batch enrichment** (9 directories + Segoe split = 2092 files across 7 collections):
    - Author: 吴清源, Go Seigen (Wu Qingyuan) 9p (1914-2014). Greatest player of the 20th century. Emigrated Japan→Taiwan.
    - Collections: `go-seigen-evil-moves` (ID 23, 30), `go-seigen-tsumego-dojo` (ID 24, 198 across 2 vols), `segoe-kensaku-tesuji-dictionary` (ID 58, 1002 from split), `go-seigen-jikyou-fusoku` (ID 174, 200), `go-seigen-jushi-furou` (ID 175, 200), `go-seigen-reading-training` (ID 176, 122 across 3 chapters), `go-seigen-tsumego-collection` (ID 177, 340 across shokyuu/jokyuu).
    - Chengyu titles: Striving + Long-Lived Stone use 4-character Chinese idioms (成語) as puzzle titles. 403 unique chengyu translated via Go expert sub-agent → `_chengyu_translations.json`. Applied to GN[]/EV[]/C[] fields.
    - Segoe Dictionary split: 505 dual-puzzle files → 1002 individual puzzles via `_split_segoe.py`. Split files contain mixed Chinese (formulaic labels) + Japanese (52 files with prose commentary). Required 3-pass translation: Chinese regex patterns → Japanese exact-match dictionary → fullwidth/katakana/particle cleanup. Final result: 0 CJK remaining.
    - Shokyuu rich commentary: Files 143-240 contain multi-paragraph Chinese Go commentary. Translated via comprehensive Go terminology dictionary approach (not simple word substitution). Multiple cleanup passes needed.
    - Merged Dojo directory: `GO SEIGEN TSUMEGO DOJO/vol-1/` and `vol-2/` are exact copies of VOL 1/VOL 2. Both sets processed identically — confirmed identical content via diff.
    - YL[] embedding: `_embed_go_seigen.py` handles all 10 source directories (including merged Dojo). Inserts after PL[] or SZ[] as fallback. Dry run verified 2290 total, then applied live. All 16 boundary checks passed.
    - Artifacts kept: `_chengyu_translations.json` (403 translations, reference), `_embed_go_seigen.py` (reusable). Temp scripts removed: `_temp_jp_survey.py`, `_fix_segoe_remaining.py`, `_translate_segoe_jp.py`, `_translate_shokyuu.py`, `_chengyu_list.json`.
