# How-To: weiqi101 Tool (101weiqi.com Puzzle Downloader)

**Last Updated:** 2026-03-15

> **See also**:
>
> - [Tool README](../../../tools/weiqi101/README.md) — Full CLI reference, source modes, state files
> - [Download Strategy](../../../tools/weiqi101/DOWNLOAD-STRATEGY.md) — Which books/categories to prioritise
> - [Research & Architecture](../../../tools/weiqi101/RESEARCH.md) — Data model, level/tag mappings, design rationale

---

## What This Tool Does

`weiqi101` downloads Go/Baduk tsumego puzzles from [101weiqi.com](https://www.101weiqi.com) and
saves them as YenGo-enriched SGF files in `external-sources/101weiqi/`. It handles daily sets,
puzzle-by-ID ranges, and complete books, with batch organisation, dedup indexing, and resume support.

> **Package name note**: The package is named `weiqi101` (not `101weiqi`) because Python packages
> cannot start with a digit. The old standalone prototype lived in `tools/101weiqi/`.

---

## Troubleshooting

### Rate Limiting (HTTP 429 / Access Denied)

Increase the delay and use a respectful request spacing:

```bash
python -m tools.weiqi101 puzzle --start-id 78000 --end-id 79000 --puzzle-delay 8.0
```

If you are blocked repeatedly, wait at least 30 minutes before retrying.

### Connection Timeouts

The tool retries automatically with exponential backoff. If timeouts persist across many puzzles,
the site may be temporarily unreachable. Check your connection and retry later with `--resume`.

### Corrupted / Stale Checkpoint State

If a run is interrupted mid-batch and `--resume` picks up incorrect state, delete the checkpoint
file and start the range fresh:

```bash
# For the shared sgf/ pool
del external-sources\101weiqi\.checkpoint.json

# For a specific book
del external-sources\101weiqi\books\book-197\.checkpoint.json
```

### Unexpected Puzzle Gaps in sgf-index.txt

The `sgf-index.txt` is append-only. If an ID appears in the index but the `.sgf` file is missing
(e.g. partial write), re-run the download with `--force` for that ID range to re-fetch and overwrite.

---

## Legal Notice

This tool is for **personal, educational use only**. Please:

- Respect the website's terms of service
- Use reasonable delays between requests
- Do not redistribute downloaded content commercially
