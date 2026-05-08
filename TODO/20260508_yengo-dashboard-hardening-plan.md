# Yen-Go Dashboard — Hardening & UX Plan

**Date:** 2026-05-08
**Status:** Active
**Correction Level:** 4 (cross-cutting; bundled per wave)
**Owner:** Mystique
**Scope:** `tools/yengo_dashboard/` cockpit — bug fixes, UX redesigns, doc/help drift

> Tracking doc for the post-Phase-4 hardening pass. The cockpit is functionally
> useful but not yet trustworthy in the boring ways: clean paths, doc/help
> parity, destructive-action honesty, green tests, theming, and surface
> overload. This plan documents and tracks the fixes through four waves.

---

## Locked decisions (defaults — callable mid-flight)

| # | Question | Default |
|---|----------|---------|
| 1 | Taxonomy edit-mode | Explicit toggle **+** 5-min auto-off |
| 2 | Reset-ingest semantics | File delete (sqlite handle is per-run only) |
| 3 | Charts library | Pure CSS bars first; revisit lib in W4 |
| 4 | Universal search scope | Slug + content_hash prefix; FTS later |
| 5 | Wave packaging | One bundled commit per wave |
| 6 | Adapters location | Stays inside Library as a sub-tab |

---

## W1 — Bugs + safety (low risk, ship first)

| Item | File(s) | Status |
|------|---------|--------|
| W1.1 Add `/daily` to SPA route allowlist | `server/app.py:110` | ✅ shipped (`3d74662d5`) |
| W1.2 Reject invalid adapter ID with 400 | `server/routes_maintenance.py` (adapter_config_add) | ✅ shipped (`3d74662d5`) |
| W1.3 Relabel `--fresh` checkbox to honest destruction wording | `web/app.js` | ✅ shipped (`3d74662d5`) |
| W1.4 Hide taxonomy rename/merge behind "Edit taxonomy" toggle (auto-off 5 min) + amber border | `web/app.js`, `web/styles.css` | ✅ shipped (`3d74662d5`) |
| W1.5 Consolidate status indicators — keep bottom strip; demote top chip to dot+version | `web/app.js` (`paintSystemChip`), styles | ✅ shipped (`3d74662d5`) |
| W1.6 Severity color tokens `--sev-{ok,warn,error,info}` themed for both modes | `web/styles.css` | ✅ shipped (`3d74662d5`) |
| W1.7 Dashboard test suite green | `tests/` | ✅ 228 passed |

## W2 — Adapter clarity (medium)

- W2.1 ✅ Relabel: "Import existing folder" + "Create new adapter from template" with subtitles (`b1d157c6d`).
- W2.2 ✅ Adapter list filter input + sort caption (`b1d157c6d`).
- W2.3 ✅ Per-row "Reset DB" calls existing `source-ingest-state --reset` modal — no new CLI needed (`b1d157c6d`).
- W2.4 ✅ Validate panel describes what is checked (`b1d157c6d`).

## W3 — Help registry + docs (medium)

- W3.1 ✅ `web/help-strings.json` + inline `?` chips + popover (`e831b6b37`).
- W3.2 ✅ CI guard — `tests/test_help_strings.py` asserts every `data-help-id` resolves and every help-drawer doc reference exists.
- W3.3 ✅ ⌘K / Ctrl-K / `/` universal command palette replaces orphaned header search (`e831b6b37`).
- W3.4 ✅ Doc rewrite — `run-yengo-dashboard.md` + `tools/yengo_dashboard/README.md` updated (`e831b6b37`).

## W4 — Structural (larger)

- W4.1 ⏸ Adapter row: Edit (pencil) + Clone (prefills scaffold) overflow actions; backend `PATCH /sources/:slug` route. **Deferred** — needs new mutation route + Pydantic schema; queued for W5.
- W4.2 ✅ Run safety — typed-verb `confirmDialog` now gates per-row Run / Ingest, naming the source + stage. The full Live Run pane already has explicit `--dry-run` / `Start`.
- W4.3 ✅ Charts: inline CSS bar sparklines for tag/level usage in the taxonomy table (relative to per-column max). Grouped-category stacked bar deferred to W5.
- W4.4 ⏸ Library decomposition — split filters / results / detail; URL-state-driven so refresh + deep links survive. **Deferred** — multi-day refactor, queued for W5.
- W4.5 ✅ Idle-page session panel — Library now shows `Recent activity` (last 3 runs from `/api/runs`) plus a "since your last visit" stamp from `localStorage`.

## Out of scope (for now)

- Multi-user / auth / remote access (per existing PLAN §2 non-goals).
- FTS5 in-browser puzzle search — defer behind W3.3 prefix search.
- Replacing BesoGo or any goban changes (frontend, separate concern).

---

## Definition of done per wave

- All listed items shipped.
- Dashboard test suite green.
- Lint clean (ruff backend, no JS lint configured today).
- For W3+: docs in `docs/` updated in the same commit as code.
- AGENTS.md (`tools/yengo_dashboard/AGENTS.md`) updated whenever surfaces shift.

## Rollback strategy

Each wave is one commit on `feature/study-mode-puzzles`. Revert is `git revert <sha>`. Theme tokens (W1.6) and help-strings.json (W3.1) are additive — independent rollback safe.
