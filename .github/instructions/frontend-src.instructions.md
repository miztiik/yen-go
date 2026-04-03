---
applyTo: "frontend/src/**"
---

## frontend/src Module Context

Before working in this module, read [`frontend/src/AGENTS.md`](../../frontend/src/AGENTS.md). It contains the full architecture map: component hierarchy, services layer, SQLite integration, key types, boot sequence, and gotchas.

### Update Rule

After any structural change in this module, update `AGENTS.md` in the **same commit**:
- New component → add row to Section 1
- New service function → add row to Section 3
- New TypeScript type/interface → add row to Section 2
- Changed data flow → update Section 4
- New coupling or gotcha → add bullet to Section 6
- Update footer: `_Last updated: {YYYY-MM-DD} | Trigger: {what changed}_`

To regenerate from scratch after large changes, use the prompt at `.github/prompts/regen-agents-map.prompt.md`.

### Key Facts (Quick Reference)

- Boot: `main.tsx` → `boot.ts` (5-steps: configService → sqliteService → render)
- DB: `sqliteService.initDb()` fetches `yengo-search.db` → sql.js WASM → in-memory SQL
- Puzzle load path: `DecodedEntry` → `puzzleLoader.loadPuzzle()` → `sgfToPuzzle()` → `Goban`
- Goban creates own DOM; `GobanContainer.tsx` mounts it — never pass ref to Goban
- No writes to DB-1 from browser — SQLite is read-only in frontend
- All user data: `localStorage` only (via `services/progress/storageOperations.ts`)
- Tests: `cd frontend && npx vitest run --no-coverage`
