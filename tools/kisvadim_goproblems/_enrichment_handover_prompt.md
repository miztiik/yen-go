# Kisvadim SGF Enrichment — Agent Handover Prompt

> Use this prompt to parallelize SGF enrichment across kisvadim-goproblems source directories.
> Each agent handles ONE source directory end-to-end.

## Context

The `external-sources/kisvadim-goproblems/` directory contains 63 subdirectories of Go/Weiqi tsumego puzzle files in SGF format, sourced from the kisvadim GitHub collection. Each directory represents one book or collection by a specific author.

**State file**: `tools/kisvadim_goproblems/_enrichment_state.json` — single source of truth for per-directory status (`done`/`pending`), collection slug mapping, chapter mapping, and volume offsets. Check this file before starting work on any directory. Update it when work is complete.

## Enrichment Pipeline (per directory)

Execute these steps IN ORDER for a given `SOURCE_DIR`:

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

1. **Author name**: Look up directory name → match to `config/cn-en-dictionary.json` author_names section. Use FULL romanized name (e.g., "Yamada Kimio" not just "Yamada").
2. **Collection slug**: Format as `{author-full-name}-{book-short-title}`, e.g., `yamada-kimio-basic-tsumego`, `hashimoto-utaro-1-year-tsumego`.
3. **Check `config/collections.json`**: Does a collection already exist for this book? If yes, use that slug. If no, register a new one with the next available ID.

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

If fragments remain (exit code 1), add missing entries to `config/cn-en-dictionary.json` and re-run.

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
- Dictionary: `config/cn-en-dictionary.json` (v1.4, ~1290 entries)
- JP Dictionary: `config/jp-en-dictionary.json` (v1.0, ~569 entries — Go terms only, NOT for prose translation)
- Collections: `config/collections.json` (168 entries, next ID: 169)

## Important Rules

1. **Never use regex for SGF property manipulation** when the parser/builder round-trip is available
2. **Never use `git stash`, `git reset --hard`, `git clean`** — other work may be in progress
3. **Stage only YOUR files** — `git add` specific paths, never `git add .`
4. **Test before writing** — always `--dry-run` first
5. **Track failures** — if any step fails, report which files and why
6. **Dictionary is shared** — do NOT modify `config/cn-en-dictionary.json` without coordinating. Instead, output `_cjk_to_translate.json` with missing fragments for later batch update
7. **collections.json is shared** — check for slug conflicts before adding. Use next available ID

## Directory Status

See `_enrichment_state.json` for the full per-directory state (63 directories, 24 done, 39 pending). That file is the single source of truth — do not duplicate status here.

## Lessons Learned

1. **GB2312 encoding**: All kisvadim files with `CA[gb2312]` are GB2312-encoded. `_prepare.py` handles detection and re-encoding.
2. **Watermark removal**: `飞扬围棋出品` (FeiYang Go product) appears in ~1900 files as a C[] watermark. Added to dictionary as empty string for stripping.
3. **N[] intent loss**: Parser/builder round-trip strips N[] from non-root nodes. If N[] contains puzzle intent, extract it BEFORE running prepare.
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
