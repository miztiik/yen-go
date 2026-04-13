# Shared Configuration

Configuration files shared between the frontend and backend pipeline. **Single source of truth** - do not duplicate elsewhere.

## Standard Metadata

Every config file follows a consistent metadata pattern:

|Field|Type|Description|
|---|---|---|
|`$schema`|string|Relative path to validation schema (e.g. `"./schemas/tags.schema.json"`)|
|`schema_version`|string|Config format version — **always `MAJOR.MINOR`** (e.g. `"2.4"`, never `"2.4.0"`)|
|`description`|string|Human-readable purpose description|
|`last_updated`|string|ISO date of last modification (`YYYY-MM-DD`)|
|`changelog`|array|Version history — array of `{ version, date, author, changes }` objects, newest first|

### Versioning Convention (Non-Negotiable)

All config files use **`MAJOR.MINOR`** (2-segment) versioning:

- **MAJOR** — Increment on breaking structural changes (field removals, renames, format changes that break parsers)
- **MINOR** — Increment on all non-breaking changes (new entries, data corrections, additive fields)

```json
{
  "schema_version": "2.4",
  "changelog": [
    { "version": "2.4", "date": "2026-03-24", "author": "developer", "changes": "Added new tag entries." }
  ]
}
```

**Rules:**
- Always a **string**, never an integer or number
- Always exactly **two segments** separated by a dot (e.g. `"8.3"`, `"1.28"`)
- Never use 3-segment semver (`"1.0.0"` ❌) or bare integers (`"1"` ❌)
- The `changelog[].version` field must match the same 2-segment format
- Schema validators in `config/schemas/` enforce the pattern `^\d+\.\d+$`

**Exception:** `config/schemas/sgf-properties.schema.json` uses an **integer** version (e.g. `15`). This is a data format version embedded in SGF files via `YV[15]` — it is NOT a config structure version and is explicitly exempt from this convention.

## Config Files

|File|Purpose|Schema|Version|
|---|---|---|---|
|`tags.json`|28 canonical puzzle tags with aliases|`schemas/tags.schema.json`|8.3|
|`puzzle-levels.json`|9-level difficulty system (novice → expert)|`schemas/puzzle-levels.schema.json`|2.0|
|`collections.json`|Curated puzzle collection catalog (159+)|`schemas/collections.schema.json`|5.0|
|`puzzle-objectives.json`|23 puzzle objectives for intent extraction|`schemas/puzzle-objectives.schema.json`|2.4|
|`teaching-comments.json`|Teaching comment templates for SGF embedding|`schemas/teaching-comments.schema.json`|2.1|
|`katago-enrichment.json`|KataGo enrichment pipeline configuration|—|1.28|
|`puzzle-quality.json`|5-level puzzle data completeness rating|`schemas/puzzle-quality.schema.json`|2.0|
|`source-quality.json`|5-tier source adapter quality rating|`schemas/source-quality.schema.json`|1.0|
|`puzzle-validation.json`|Board size, solution, and stone count rules|`schemas/puzzle-validation.schema.json`|2.0|
|`go-tips.json`|Japanese Go terminology tips for UI|`schemas/go-tips.schema.json`|1.1|
|`content-types.json`|Content-type classification (curated/practice/training)|`schemas/content-types.schema.json`|1.0|
|`depth-presets.json`|Solution depth preset filters|`schemas/depth-presets.schema.json`|1.0|
|`quality.json`|Quality tier definitions with display colors|`schemas/quality.schema.json`|1.0|
|`logging.json`|Centralized logging configuration|—|1.0|
|`levels.json`|Level configuration (internal)|—|1.0|
|`sgf-property-policies.json`|SGF property handling policies for pipeline|—|1.0|
|`jp-en-dictionary.json`|Japanese→English Go term translations|`schemas/dictionary.schema.json`|1.0|
|`cn-en-dictionary.json`|Chinese→English Go term translations (525+ terms)|`schemas/dictionary.schema.json`|1.1|
|`japanese-go-terms.json`|Japanese Go terminology reference|`schemas/dictionary.schema.json`|1.0|

## Schema Files (`schemas/`)

|Schema|Validates|
|---|---|
|`tags.schema.json`|`tags.json`|
|`puzzle-levels.schema.json`|`puzzle-levels.json`|
|`collections.schema.json`|`collections.json`|
|`puzzle-objectives.schema.json`|`puzzle-objectives.json`|
|`puzzle-quality.schema.json`|`puzzle-quality.json`|
|`source-quality.schema.json`|`source-quality.json`|
|`puzzle-validation.schema.json`|`puzzle-validation.json`|
|`go-tips.schema.json`|`go-tips.json`|
|`db-search.schema.json`|`yengo-search.db` — frontend SQLite search index table definitions|
|`db-content.schema.json`|`yengo-content.db` — backend-only content/dedup store table definitions|
|`sgf-properties.schema.json`|YenGo custom SGF properties (authoritative)|
|`sgf-naming.schema.json`|SGF filename conventions|
|`puzzle-collection-inventory-schema.json`|`.puzzle-inventory-state/` runtime data|
|`dictionary.schema.json`|`jp-en-dictionary.json`, `cn-en-dictionary.json`|

## Workflow

1. **Edit config here** (single source of truth)
2. **Pipeline copies to output** during publish stage
3. **Frontend fetches/imports** from published location

## Formatting Convention

String arrays (alias lists, tag arrays) are kept **inline** -one array per line, not one item per line:

```json
"aliases": ["killing", "kill", "tsumego", "life and death"]
```

**Do not** let your editor expand these to multi-line. VS Code format-on-save is disabled for JSON in `.vscode/settings.json`. If an editor or tool expands them, run from the project root:

```bash
python tools/reformat_config_arrays.py
```

> **See also**:
>
> - [Concepts: Tags](../docs/concepts/tags.md) — Tag taxonomy
> - [Concepts: Levels](../docs/concepts/levels.md) — Difficulty system
> - [Concepts: Collections](../docs/concepts/collections.md) — Collection system
> - [Concepts: SGF Properties](../docs/concepts/sgf-properties.md) — Custom SGF properties
> - [Reference: View Index Schema](../docs/reference/view-index-schema.md) — View JSON format
