# Puzzle Sources Catalog

This document describes the schema and metadata format used to catalog puzzle sources in Yen-Go. Specific external source identities are intentionally not enumerated here; consult internal source configuration (`config/sources.json`) for the authoritative list of integrated adapters.

---

## Source Schema

Every source registered in the pipeline is described with the following metadata:

| Field               | Description                                                                  |
| ------------------- | ---------------------------------------------------------------------------- |
| **Source ID**       | Stable slug used by the pipeline (e.g., `yengo-source`)                      |
| **Format**          | Raw input format (SGF, JSON, custom text, etc.)                              |
| **Solutions**       | Whether solutions are embedded and in what shape                             |
| **Estimated Count** | Approximate puzzle count                                                     |
| **License**         | License of the source data (or "Check repository")                           |
| **Adapter**         | Adapter class in `backend/puzzle_manager/adapters/` that ingests this source |

---

## Exemplar Source

The following is a generic example showing all schema fields. Real source identities are not disclosed in documentation.

### `yengo-source`

| Field               | Value                                            |
| ------------------- | ------------------------------------------------ |
| **Source ID**       | `yengo-source`                                   |
| **Repository**      | _(redacted)_                                     |
| **Format**          | SGF / JSON                                       |
| **Solutions**       | ✅ Embedded (variations or `SOL` field)          |
| **Estimated Count** | varies                                           |
| **License**         | Check upstream repository                        |
| **Adapter**         | `YengoSourceAdapter`                             |
| **Ingestion**       | `python -m backend.puzzle_manager run --source yengo-source --stage ingest` |

**Typical JSON payload shape** (when source uses JSON):

```json
{
  "AB": ["eb", "fb", "bc"],
  "AW": ["da", "ab", "bb"],
  "SZ": "19",
  "C": "Black to play",
  "SOL": [["B", "ba", "Correct.", ""]]
}
```

**Typical directory layout** (when source ships SGF files):

```text
collection-name/
├── easy/
├── intermediate/
├── hard/
└── other/
```

---

## User-Uploaded Puzzles

| Field          | Value                      |
| -------------- | -------------------------- |
| **Source ID**  | `user-upload`              |
| **Format**     | SGF (submitted via web UI) |
| **Solutions**  | ✅ Required                |
| **Validation** | Validated via pipeline     |

**Upload Flow**:

1. User submits SGF via upload interface
2. SGF stored in staging area
3. Pipeline validates solution correctness
4. Pipeline classifies difficulty automatically
5. Pipeline assigns technique tags
6. Validated puzzle merged to main collection

**Validation Criteria**:

- SGF must parse successfully
- Solution must be verifiable
- Solution depth ≤ 7 moves
- Single optimal solution (not ambiguous)

---

## Difficulty Mapping

External source difficulty labels are mapped to Yen-Go levels by the classification stage. See [`docs/concepts/quality.md`](../concepts/quality.md) and `config/puzzle-levels.json` for the canonical level taxonomy.

---

## Adding New Sources

When adding a new source:

1. Implement an adapter in `backend/puzzle_manager/adapters/`
2. Register in `config/sources.json`
3. Verify with `python -m backend.puzzle_manager sources`
4. Run import: `python -m backend.puzzle_manager run --source <id> --stage ingest`

See [How-To: Create Adapter](../how-to/backend/create-adapter.md) for the full procedure.

---

## See Also

- [How-To: Create Adapter](../how-to/backend/create-adapter.md) — Add sources guide
- [Architecture: Adapter Design Standards](../architecture/backend/adapter-design-standards.md) — Adapter architecture
- [Concepts: Quality](../concepts/quality.md) — Quality and difficulty taxonomy
