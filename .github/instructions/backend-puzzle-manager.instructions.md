---
applyTo: "backend/puzzle_manager/**"
---

## backend/puzzle_manager Module Context

Before working in this module, read [`backend/puzzle_manager/AGENTS.md`](../../backend/puzzle_manager/AGENTS.md). It contains the full architecture map: file inventory, core entities, key methods, 3-stage pipeline flow, adapter contract, and gotchas.

### Update Rule

After any structural change in this module, update `AGENTS.md` in the **same commit**:
- New file added → add row to Section 1
- New public function/class → add row to Section 3
- New adapter → add row to adapters section
- Changed pipeline flow → update Section 4
- New SGF property → add row to Section 7
- Update footer: `_Last updated: {YYYY-MM-DD} | Trigger: {what changed}_`

To regenerate from scratch after large changes, use the prompt at `.github/prompts/regen-agents-map.prompt.md`.

### Key Facts (Quick Reference)

- Entry point: `python -m backend.puzzle_manager run --source {name}` (from repo root)
- 3 stages: `ingest` → `analyze` → `publish` (can run separately with `--stage`)
- GN property rule: Adapters MUST NOT set `GN[YENGO-...]` — `PublishStage` computes and sets it
- `content_hash` = `SHA256(sgf_content)[:16]` = `GN` suffix = filename (all three must match)
- Config authority: `config/tags.json` (tags), `config/puzzle-levels.json` (levels) — never hardcode
- Tests: `pytest -m "not (cli or slow)"` (~30s) from repo root; `pytest -m unit` (~20s) for fastest
