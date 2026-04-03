# Tsumego Hero Puzzle Downloader

Standalone tool to download Go tsumego puzzles from [Tsumego Hero](https://tsumego.com) and store them as SGF files.

- **Website**: https://tsumego.com
- **Method**: HTML scraping (no formal API)
- **Last Updated**: 2026-02-05
- **Site Statistics**: 49 collections, ~11,745 puzzles, ~17,000 total puzzle IDs, 77 tags, difficulty 15k-9d

## Site Investigation Summary (2026-02-05)

### URL Structure

| Resource         | Pattern                                                           | Example                             |
| ---------------- | ----------------------------------------------------------------- | ----------------------------------- |
| Puzzle page      | `https://tsumego.com/{url_id}`                                    | `https://tsumego.com/5225`          |
| Collection page  | `https://tsumego.com/sets/view/{set_id}`                          | `https://tsumego.com/sets/view/104` |
| Collections list | `https://tsumego.com/sets`                                        | -                                   |
| SGF Editor       | `https://tsumego.com/editor/?setConnectionID={id}&sgfID={sgf_id}` | -                                   |

### ID Systems

Multiple IDs are used:

- **URL ID / setConnectionID**: Used in URLs (1 to ~20,000+)
- **tsumegoID**: Internal puzzle ID (different from URL ID)
- **sgfID**: Links puzzle to SGF content
- **setID**: Collection/set identifier

### Available Collections (49 total)

Sample collections from `/sets`:

| Set ID  | Name                          | Puzzles   | ~Difficulty |
| ------- | ----------------------------- | --------- | ----------- |
| 117     | Easy Capture                  | 200       | 15k         |
| 104     | Easy Life                     | 200       | 15k         |
| 105     | Easy Kill                     | 200       | 15k         |
| 67      | Tsumego Dictionary Volume I   | -         | -           |
| 69      | Tsumego Dictionary Volume II  | -         | -           |
| 81      | Korean Problem Academy 1-4    | -         | -           |
| 191-207 | Life & Death - Intermediate   | ~200 each | ~2-3k       |
| 181-192 | Life & Death - Advanced       | ~200 each | ~1k-1d      |
| 150     | French Go Review              | -         | -           |
| 38      | Kanzufu                       | -         | -           |
| 127     | Gokyo Shumyo I-IV             | -         | -           |
| 231     | Secret Tsumego from Hong Dojo | -         | -           |

Full list at: `https://tsumego.com/sets`

### Difficulty Levels

Available difficulty levels (from `/sets` filter):

- **Kyu**: 15k, 14k, 13k, 12k, 11k, 10k, 9k, 8k, 7k, 6k, 5k, 4k, 3k, 2k, 1k
- **Dan**: 1d, 2d, 3d, 4d, 5d, 6d, 7d, 8d, 9d

### Topics/Categories

**77 tags available** in the dropdown filter at `/sets`:

| Category        | Sample Tags                                                 |
| --------------- | ----------------------------------------------------------- |
| **Tesuji**      | Snapback, Throw-in, Ladder, Geta, Double Atari, Clamp       |
| **Dead Shapes** | L-Group, J-Group, Bulky Five, Carpenter's Square, Bent Four |
| **Objectives**  | Ko, Seki, Semeai (Types 1-6), Attack                        |
| **Game Phase**  | Joseki, Fuseki, Yose, Chuban                                |
| **Shapes**      | Bamboo Joint, Two-Headed Dragon, Crane's Nest               |

Full tag list and mapping in [Tag Mapping](#tag-mapping-77-source-tags--18-yengo-tags) section.

### API / Data Access

**No formal API exists.** Data extraction via HTML scraping:

1. **SGF Content**: Embedded in JavaScript as `options.sgf2 = "..."` (concatenated string)
2. **Metadata**: Embedded in page JavaScript variables:
   - `var tsumegoID = {id};`
   - `var setID = {set_id};`
   - `var author = "{name}";`
   - `tags: [{name: 'tag', id: N, isHint: 0/1, isPopular: 0/1, ...}]`

### Data Available Per Puzzle

| Field             | Source             | Example                                     | Notes                  |
| ----------------- | ------------------ | ------------------------------------------- | ---------------------- |
| SGF               | `options.sgf2`     | `(;GM[1]FF[4]...`                           | Concatenated JS string |
| URL ID            | URL path           | 5225                                        | setConnectionID        |
| tsumegoID         | JavaScript         | 10431                                       | Internal puzzle ID     |
| setID             | JavaScript         | 104                                         | Collection ID          |
| sgfID             | Editor link        | 5348                                        | Links to SGF content   |
| Collection Name   | Page title         | "Easy Life 125/200"                         | Includes position      |
| Description       | `#descriptionText` | "Black to live."                            | Task objective         |
| Tags              | JavaScript `tags:` | `[{name: '1-1 point', id: 167, isHint: 1}]` | With hint flag         |
| Difficulty Rank   | Rating display     | "15k"                                       | Kyu/dan rating         |
| Difficulty Rating | Rating display     | 587.069                                     | Numerical ELO-style    |
| Author            | JavaScript         | "Bradford Malbon"                           | When available         |

**Tag Object Fields**: `name`, `id`, `isHint` (1=solving hint), `isPopular`, `isApproved`, `isMine`, `isAdded`

### Rate Limiting

- **Request delay**: 2.5 seconds (base)
- **Jitter**: ±40%
- **Retries**: 3 with exponential backoff
- No authentication required for public puzzles

### Enumeration Strategy

**Recommended approach: Collection-based enumeration**

1. Fetch collection list from `/sets`
2. For each collection, fetch puzzle list from `/sets/view/{set_id}`
3. Extract puzzle URL IDs from `href="/[0-9]+"` links
4. Download each puzzle page and extract SGF + metadata

**Alternative: Sequential ID enumeration**

- IDs are sequential but with gaps
- Range appears to be 1 to ~20000+ (as of investigation)
- Many IDs may not have puzzles (return 200 but no `options.sgf2`)

## Features

- **Collection-based download**: Enumerate puzzles via collection pages
- **SGF extraction**: Parse embedded JavaScript SGF content (string concatenation format)
- **Rich metadata extraction**:
  - Difficulty rank (15k-9d) and numerical rating (ELO-style)
  - Author attribution
  - Tags with hint indicators (`isHint` flag)
  - Collection name and position
  - Description text
- **Checkpoint/resume**: Track download progress
- **Rate limiting**: Configurable delays with jitter
- **Index file**: Track all downloaded puzzles

## Output Structure

Files are written to `external-sources/t-hero/`:

```
external-sources/t-hero/
├── sgf/
│   ├── batch-001/
│   │   ├── th-5225.sgf
│   │   ├── th-5226.sgf
│   │   └── ... (up to 500 files)
│   ├── batch-002/
│   └── ...
├── logs/
│   └── tsumego-hero-YYYYMMDD_HHMMSS.jsonl
├── sgf-index.txt
├── .checkpoint.json
└── README.md
```

## Usage

```bash
# From project root:
python -m tools.tsumego_hero --help

# List available collections
python -m tools.tsumego_hero --list-collections

# Download a specific collection
python -m tools.tsumego_hero --collection 104 --max-puzzles 50

# Download all collections
python -m tools.tsumego_hero --all --max-puzzles 1000

# Resume interrupted download
python -m tools.tsumego_hero --resume

# Dry run
python -m tools.tsumego_hero --collection 104 --dry-run
```

## Gap Finder Utility

After collection-based download, use the gap finder to discover puzzles that exist outside collections:

```bash
# Find missing IDs in range 1-17500 (default)
python -m tools.tsumego_hero.gap_finder

# Specify ID range
python -m tools.tsumego_hero.gap_finder --min-id 1 --max-id 20000

# Also write sorted list of downloaded IDs
python -m tools.tsumego_hero.gap_finder --sorted-index
```

**Output files:**

- `missing-ids.txt` - IDs not found in downloaded batches (one per line)
- `sorted-index.txt` - Downloaded IDs in numerical order (if `--sorted-index`)

**Gap-fill download:**

```bash
# Download from missing IDs list
python -m tools.tsumego_hero --from-ids missing-ids.txt --max-puzzles 500

# Dry run first
python -m tools.tsumego_hero --from-ids missing-ids.txt --dry-run
```

**Workflow for complete download:**

1. Run collection-based download: `python -m tools.tsumego_hero --max-puzzles 10000`
2. Find gaps: `python -m tools.tsumego_hero.gap_finder --max-id 17500`
3. Fill gaps: `python -m tools.tsumego_hero --from-ids missing-ids.txt --max-puzzles 5000`
4. Repeat 2-3 until no new puzzles found

## SGF Format

Extracted SGF includes:

- `FF[4]GM[1]CA[UTF-8]` - Standard headers
- `SZ[19]` - Board size
- `AW[...]/AB[...]` - Initial stone positions
- Move tree with `C[+]` for correct answers

**YenGo custom properties:**

| Property | Description                                   | Example                  |
| -------- | --------------------------------------------- | ------------------------ |
| `YS`     | Source adapter ID                             | `YS[th]`                 |
| `YG`     | Difficulty level (mapped from kyu/dan)        | `YG[intermediate]`       |
| `YT`     | Tags (comma-separated, mapped from site tags) | `YT[ko,ladder,snapback]` |

## Level Mapping

Maps Tsumego Hero difficulty (15k-9d) to YenGo's 9-level system.

**Reference**: [docs/concepts/levels.md](../../docs/concepts/levels.md)

**Note**: Tsumego Hero's difficulty ratings are calibrated differently than traditional kyu/dan. Their "15k" puzzles are beginner-level problems suited for novice players (30k-26k), not true 15-kyu complexity. The mapping below reflects puzzle complexity, not strict rank equivalence.

| Tsumego Hero | YenGo Level          | Rank Range | Description                   |
| ------------ | -------------------- | ---------- | ----------------------------- |
| 15k-12k      | `novice`             | 30k-26k    | First puzzles, basic captures |
| 11k-9k       | `beginner`           | 25k-21k    | Simple tactics                |
| 8k-6k        | `elementary`         | 20k-16k    | Common patterns               |
| 5k-4k        | `intermediate`       | 15k-11k    | Multi-step sequences          |
| 3k-1k        | `upper-intermediate` | 10k-6k     | Complex reading               |
| 1d-2d        | `advanced`           | 5k-1k      | Deep calculations             |
| 3d-4d        | `low-dan`            | 1d-3d      | Professional patterns         |
| 5d-7d        | `high-dan`           | 4d-6d      | Master techniques             |
| 8d-9d        | `expert`             | 7d-9d      | Professional level            |

## Tag Mapping (77 Source Tags → 18 YenGo Tags)

**Total puzzles available**: ~11,745

**Reference**: [config/tags.json](../../config/tags.json) | [docs/concepts/tags.md](../../docs/concepts/tags.md)

Tsumego Hero has 77 tags. These map to YenGo's 18 canonical tags:

### Tesuji Tags

| Tsumego Hero Tag                   | YenGo Tag          | Notes                                |
| ---------------------------------- | ------------------ | ------------------------------------ |
| Snapback                           | `snapback`         | Direct match - uttegaeshi            |
| Throw-in                           | `throw-in`         | Direct match - horikomi              |
| Sacrifice                          | `throw-in`         | Sacrifice for shape destruction      |
| Tombstone                          | `throw-in`         | Sacrifice-based tesuji               |
| Patting the Raccoon's Belly        | `throw-in`         | Special sacrifice technique          |
| Ladder                             | `ladder`           | Direct match - shicho                |
| Spiral Ladder                      | `ladder`           | Variant of ladder                    |
| Geta                               | `net`              | Direct match - loose capture         |
| Loose ladder                       | `net`              | Same as geta                         |
| Double Atari                       | `double-atari`     | Direct match - ryo-atari             |
| Oiotoshi                           | `connect-and-die`  | Direct match - chase and capture     |
| Under the Stones                   | `under-the-stones` | Direct match - ishi no shita         |
| SendingTwoReturningOne             | `under-the-stones` | Related technique                    |
| Damezumari                         | `liberty-shortage` | Direct match - shortage of liberties |
| Oshi-tsubushi                      | `liberty-shortage` | Push-and-crush (liberty reduction)   |
| Squeeze                            | `liberty-shortage` | Squeezing technique                  |
| Squeeze                            | `liberty-shortage` | (trailing space variant)             |
| Clamp                              | `clamp`            | Direct match - hasami-tsuke          |
| Belly Attachment Tesuji            | `clamp`            | Inside attachment                    |
| Breaking Bamboo Clamp              | `clamp`            | Counter to bamboo joint              |
| Nakade                             | `vital-point`      | Interior killing move                |
| Placement                          | `vital-point`      | Interior placement - oki             |
| Nose Tesuji                        | `vital-point`      | Shape vital point                    |
| 1-1 point                          | `vital-point`      | Corner vital point                   |
| 2-1 point                          | `vital-point`      | Corner vital point                   |
| Hekomi                             | `vital-point`      | Push-in at vital point               |
| Golden Chicken Standing on One Leg | `vital-point`      | Famous vital point pattern           |
| False Eye                          | `eye-shape`        | Eye destruction                      |

### Dead Shape Tags

| Tsumego Hero Tag        | YenGo Tag     | Notes                         |
| ----------------------- | ------------- | ----------------------------- |
| Bent Four in the Corner | `dead-shapes` | Unconditionally dead          |
| L-Group                 | `dead-shapes` | Classic dead shape            |
| L+1 Group               | `dead-shapes` | Variant with extension        |
| L+2 Group               | `dead-shapes` | Variant with 2 extensions     |
| Long L Group            | `dead-shapes` | Extended L shape              |
| J-Group                 | `dead-shapes` | Dead corner shape             |
| J+1 Group               | `dead-shapes` | Variant with extension        |
| Bulky Five              | `dead-shapes` | Guzumi - dead shape           |
| Rabbitty Six            | `dead-shapes` | Killable six-space shape      |
| Carpenter's Square      | `dead-shapes` | Famous killable shape         |
| Weak Carpenter's Square | `dead-shapes` | Variant of carpenter's square |
| Door Group              | `dead-shapes` | Killable corner shape         |
| Comb-Formation          | `dead-shapes` | Killable shape                |
| Crane's Nest            | `dead-shapes` | Famous killable shape         |
| Tripod Group            | `dead-shapes` | Dead corner shape             |

### Objective Tags

| Tsumego Hero Tag     | YenGo Tag        | Notes                       |
| -------------------- | ---------------- | --------------------------- |
| Ko                   | `ko`             | Direct match                |
| Double Ko            | `ko`             | Ko variation                |
| Superko              | `ko`             | Positional superko          |
| Ten Thousand Year Ko | `ko`             | Mannen ko                   |
| Seki                 | `seki`           | Direct match - mutual life  |
| Attack               | `life-and-death` | General killing             |
| Two-Headed Dragon    | `living`         | Living shape                |
| Semeai               | `capture-race`   | Direct match - liberty race |
| Semeai Type 1-6      | `capture-race`   | Semeai classifications      |
| Connect              | `escape`         | Escape by connection        |
| Separate             | `escape`         | Escape by cutting           |
| Sabaki               | `escape`         | Light escape technique      |

### Unmapped Tags (Game Phase / General)

These tags don't map to YenGo's tsumego-focused tags:

| Tsumego Hero Tag | Reason Not Mapped                      |
| ---------------- | -------------------------------------- |
| Joseki           | Opening/corner pattern, not tsumego    |
| Fuseki           | Opening phase                          |
| Yose             | Endgame technique (not life-and-death) |
| Moyo             | Framework strategy                     |
| Chuban           | Middle game phase                      |
| Haengma          | General stone shape                    |
| Sente            | Initiative concept                     |
| Miai             | Dual options concept                   |
| Symmetry         | General pattern                        |
| Bamboo Joint     | Connection shape                       |
| Monkey Jump      | Yose tesuji                            |
| Hane             | General move type                      |
| Crosscut Tesuji  | Fighting technique                     |
| Driving Tesuji   | General tesuji                         |
| Descent          | General move                           |
| Enclosure        | Opening pattern                        |
| tsuke            | Attachment move                        |
| Probe            | General technique                      |

### Mapping Statistics

| Category                      | Count    |
| ----------------------------- | -------- |
| Total Tsumego Hero tags       | 77       |
| Mapped to YenGo tags          | 59       |
| Unmapped (game phase/general) | 18       |
| YenGo tags used               | 18 of 18 |

**All 18 YenGo canonical tags have mappings:**

- **Objectives**: life-and-death, living, ko, seki
- **Techniques**: capture-race, escape, eye-shape, dead-shapes
- **Tesuji**: snapback, throw-in, ladder, net, liberty-shortage, connect-and-die, under-the-stones, double-atari, vital-point, clamp

## Technical Notes

### SGF Extraction

The SGF is embedded as a JavaScript string concatenation:

```javascript
options.sgf2 = "(;GM[1]..." + "\n" + "RU[Japanese]..." + "\n" + "...";
```

Extraction requires:

1. Regex to find `options.sgf2 = "...";`
2. Remove `"+"`
3. Unescape `\n` characters

### Metadata Extraction Patterns

```python
# Puzzle IDs
r'var tsumegoID = (\d+);'
r'var setID = (\d+);'
r'setConnectionID=(\d+)&sgfID=(\d+)'

# Description
r'id="descriptionText">([^<]+)<'

# Tags (multiline, re.DOTALL)
r'tags:\s*\[(.+?)\]'

# Difficulty rank (15k, 1d, etc.)
r'<font size="4">\s*(\d+[kd])'

# Difficulty numerical rating (ELO-style, e.g., 587.069)
r'<font size="4">\s*\d+[kd]\s*<font[^>]*>\((\d+\.\d+)\)'

# Author
r'var author = "([^"]+)";'

# Collection info
r'href="/sets/view/\d+">([^<]+)<'
```

## Known Limitations

1. **No API**: All data must be scraped from HTML
2. **Rate limiting**: Must be conservative to avoid blocking
3. **JavaScript rendering**: Some data might require JS (most is in static HTML)
4. **Authentication**: Some features may require login (tag voting, etc.)
5. **Session-dependent**: Some IDs change between sessions (tsumegoID)

## TODO

- [x] Implement client.py with rate limiting
- [x] Implement collection enumeration
- [x] Implement SGF parser/extractor
- [x] Add level mapping (15k-9d → 9 YenGo levels)
- [x] Add tag mapping (77 tags → 18 YenGo tags)
- [x] Extract author and numerical rating
- [x] Add checkpoint support
- [ ] Test with full collection download
- [ ] Add --all flag for downloading all collections
