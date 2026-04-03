## Plan: Standardize Config JSON Schemas & Metadata

**Last Updated**: 2026-02-18
**Status**: Not Started

**TL;DR**: Create 4 missing JSON schemas (`tags`, `puzzle-levels`, `go-tips`, `source-quality`), fix/add `$schema` references in all 10 config files, standardize metadata fields (`version`, `description`, `last_updated`, `changelog`) across all configs, and trim `config/README.md` to a summary linking to docs. Total: 4 new schema files, ~10 config file metadata edits, 1 README rewrite.

**Decisions**:
- Metadata convention: **top-level** `version`, `description`, `last_updated`, `changelog` (not underscored)
- JSON Schema version: **draft-07** (matches gold-standard puzzle-quality.schema.json and collections.schema.json)
- Scope: 4 new schemas (tags, puzzle-levels, go-tips, source-quality); also fix 2 existing missing refs (puzzle-objectives, collections)
- Skip: logging.json, jp-en-dictionary.json (low-value utility configs)

---

**Steps**

### Phase 1: Create 4 New Schema Files

1. **Create `config/schemas/tags.schema.json`** — validates `config/tags.json`. Define: root object requires `version`, `description`, `last_updated`, `changelog`, `tags`. Tag entry definition: `slug` (kebab-case pattern), `id` (integer), `name` (string), `category` (enum: `objective`/`tesuji`/`technique`), `description` (string), `aliases` (string array). Use `additionalProperties` on tag entries, `patternProperties` with `^[a-z][a-z0-9-]*$` on `tags` object keys.

2. **Create `config/schemas/puzzle-levels.schema.json`** — validates `config/puzzle-levels.json`. Define: root requires `version`, `description`, `last_updated`, `frozen`, `levels` (array, 9 items). Level entry: `id` (integer), `slug`, `name`, `shortName`, `rankRange` (object with `min`/`max`), `description`. Constrain `id` ranges.

3. **Create `config/schemas/go-tips.schema.json`** — validates `config/go-tips.json`. Define: root requires `version`, `description`, `last_updated`, `tips` (array). Tip entry: `text` (string), `category` (string), `levels` (array of level slug strings).

4. **Create `config/schemas/source-quality.schema.json`** — currently referenced by `config/source-quality.json` but **does not exist** (broken ref). Define: root requires `version`, `description`, `last_updated`, `tiers`. Tier entry: `name`, `stars`, `description`, `criteria`. Keys `"1"`-`"5"` via `patternProperties`.

### Phase 2: Standardize Metadata in Config Files

5. **`config/tags.json`** — change `$schema` from JSON Schema meta-URL to `"./schemas/tags.schema.json"`. Already has `version`, `description`, `last_updated`, `changelog` — no other changes needed.

6. **`config/puzzle-levels.json`** — change `$schema` from JSON Schema meta-URL to `"./schemas/puzzle-levels.schema.json"`. Add `changelog` field (brief history string). Already has `version`, `description`, `last_updated`.

7. **`config/go-tips.json`** — add `$schema: "./schemas/go-tips.schema.json"`, add `description`, `last_updated` (today: 2026-02-18), add `changelog`.

8. **`config/source-quality.json`** — rename `_version` to `version`, rename `_description` to `description`, add `last_updated` (today), add `changelog`. Fix `$schema` path (already points to correct file, which we'll create in step 4).

9. **`config/puzzle-quality.json`** — rename `_version` to `version`, rename `_description` to `description`, add `last_updated`, add `changelog`. Update `config/schemas/puzzle-quality.schema.json` to accept `version`/`description` (not underscored). Keep `$schema` as-is (already correct).

10. **`config/puzzle-objectives.json`** — add `$schema: "./schemas/puzzle-objectives.schema.json"`, rename `schema_version` to `version`, add `description`, add `last_updated`. Update `config/schemas/puzzle-objectives.schema.json` to accept `version` instead of `schema_version`, and add `description`/`last_updated` properties.

11. **`config/collections.json`** — add `$schema: "./schemas/collections.schema.json"`. Add `description`, `last_updated`, `changelog`. Update `config/schemas/collections.schema.json` to accept new metadata fields.

12. **`config/puzzle-validation.json`** — already has `$schema`. Add `description`, `last_updated`, `changelog`, ensure `version` is string format. Update `config/schemas/puzzle-validation.schema.json` for new fields.

### Phase 3: Update Backend Code Reading Changed Fields

13. **Grep for `_version`, `_description`, `schema_version`** in backend Python code that reads puzzle-quality.json, source-quality.json, or puzzle-objectives.json — update field references to `version`/`description`.

### Phase 4: Update README

14. **Trim `config/README.md`** — replace 400-line doc with a concise summary table (file name, purpose, schema ref, version) + link to `docs/reference/` for detailed docs. Keep it under 80 lines.

### Phase 5: Tests & Docs

15. **Run backend unit tests** — `pytest -m unit --ignore=tools` to verify no Python code broke from field renames.
16. **Run frontend tests** — `npx vitest run` to verify no frontend code broke.
17. **Update `CLAUDE.md`** if any config field references changed.

---

**Verification**
- Every config JSON in `config/*.json` has a `$schema` field pointing to `./schemas/{name}.schema.json` (except logging.json and jp-en-dictionary.json)
- Every schema-referenced config has `version` (string), `description` (string), `last_updated` (ISO date string)
- `source-quality.schema.json` exists (fixes broken reference)
- `grep -r "_version\|_description\|schema_version" config/*.json` returns zero matches (except logging/jp-en-dict)
- `pytest -m unit --ignore=tools` passes
- `npx vitest run` passes (pre-existing failures only)
