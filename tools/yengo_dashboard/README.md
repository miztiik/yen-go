# yengo_dashboard

Localhost browser cockpit over `backend/puzzle_manager`. One browser tab to
run, observe, and maintain the ~200K-puzzle pipeline across many adapters
without typing CLI flags.

> **Operator tool, not a service.** Loopback only, single user, no auth.
> Every action corresponds 1:1 to a `puzzle_manager` CLI command — the
> CLI remains canonical.

---

## Quick start

```bash
# from the repo root
python -m tools.yengo_dashboard
# → http://127.0.0.1:8201
```

Flags: `--port 8201` (default), `--host 127.0.0.1`, `--config DIR`
(forwards `--config` to every CLI subprocess), `--runtime-dir DIR`
(overrides `.pm-runtime`).

OpenAPI / Swagger UI: `http://127.0.0.1:8201/docs` (FastAPI built-in).

---

## What you can do

| Tab             | Wraps                                                                                  |
| --------------- | -------------------------------------------------------------------------------------- |
| **Overview**    | Published-corpus headline (`yengo-search.db` row counts, by level, by content_type)    |
| **Adapters**    | `source-status` per adapter; one-click Run / Ingest / Enable                           |
| **Live Run**    | Live SSE stream of a `run` / `clean` / `rollback` / `vacuum-db` subprocess + Cancel    |
| **Maintenance** | Forms for `clean`, `rollback`, `vacuum-db`, plus `publish-log search`                  |
| **History**     | Past runs from `.pm-runtime/state/runs/*.json`                                         |

The header lock-status badge wraps `config-lock {status,release}` — click
to release a stuck lock (with `--force` confirm fallback).

---

## Where the docs live (Diataxis)

| Tier             | Path                                              |
| ---------------- | ------------------------------------------------- |
| **Architecture** | `docs/architecture/tools/yengo_dashboard.md` — the *why* |
| **How-to**       | `docs/how-to/tools/run-yengo-dashboard.md` — daily ops   |
| **Reference**    | `docs/reference/yengo-dashboard-api.md` — endpoint catalog |
| **Plan**         | `tools/yengo_dashboard/PLAN.md` — phases + decisions     |
| **Module map**   | `tools/yengo_dashboard/AGENTS.md` — agent-facing layout  |
| **Palette**      | `tools/yengo_dashboard/colors.md` — semantic color rules |

---

## Non-negotiable boundary

`tools/yengo_dashboard/` is a **pure presentation layer** over
`backend/puzzle_manager/`. It may spawn CLI subprocesses, read SQLite/JSON
state files raw, tail logs, render HTML. It may **not** parse SGF, classify
puzzles, decide what status enums mean, or hold any other domain knowledge.

If a UI need surfaces that requires interpretation, the rule is *"add a CLI
subcommand or `--json` flag to `puzzle_manager` first, then the cockpit
calls it"* — never reach across the boundary in JavaScript or Python.

See `docs/architecture/tools/yengo_dashboard.md` for the full rationale (Principle #6).

---

## Tests

```bash
pytest tools/yengo_dashboard/tests/ -q
```

55 tests as of Phase 3. **Real fixtures only** — no mocks, no stubs. The
HTTP/SSE tests drive real subprocesses against tmp `backend/puzzle_manager`
shims; the SQLite tests build real databases with the publisher's schema;
one slow smoke test runs the actual `python -m backend.puzzle_manager
validate`.
