# Database Deployment Topology (ADR)

**Last Updated**: 2026-03-14

## Status

**DECIDED** — 2026-02-21 (updated 2026-03-14 for SQLite migration)

## Context

The SQLite-based query architecture requires one canonical deployment topology for database files, daily views, and SGF artifacts. Mixed runtime fetch modes are disallowed because they create contract drift, cache inconsistency, and mixed-state rollout risk.

## Decision

Chosen option: **Repo-static mode**

The frontend fetches the SQLite database and SGF files from repository-hosted static paths via `CDN_BASE_PATH`. This is treated as canonical for production and CI/CD packaging.

## Architecture

The selected topology preserves these locked URL and resolver contracts:

- Canonical routes are `/contexts` and `/search` only (no standalone `/puzzles/{id}` canonical route).
- Compact filter query keys are `l`, `t`, `c`, `q`.
- Navigation term is `offset` (not `cursor`).
- `id` query param represents the currently rendered puzzle identity for troubleshooting/replay.
- Public `id` must be a stable identifier and must not expose raw storage hashes in URL contracts.
- DB version + `offset` + optional `id` enable deterministic replay across evolving datasets.
- Quality dimension `q` is in-scope.

## Options

1. **Bundled-static mode**
   - Database and artifacts packaged with the deployed frontend artifact.
   - Runtime fetch base is artifact-local.
2. **Repo-static mode**
   - Frontend fetches database and artifacts from repository-hosted static paths.
   - Runtime fetch base is repository/CDN path.

## Decision Drivers

- Single canonical fetch base in production.
- Deterministic deployment and rollback behavior.
- Cache invalidation clarity using `db-version.json`.
- Operational simplicity for CI/CD and release verification.

## Decision Rationale

**Why Repo-static:**

- Matches the existing `CDN_BASE_PATH` pattern already used by the frontend.
- No Vite rebuild required when the pipeline publishes new puzzles — only `yengo-search.db` and `db-version.json` change.
- SGF files and database are served from the same fetch base, avoiding cross-origin complexity.
- Cache invalidation is straightforward: `db-version.json` version field differentiates releases; SGF files are content-addressed and immutable (infinitely cacheable).

**Why NOT Bundled-static:**

- Would require a frontend rebuild on every pipeline publish, coupling the pipeline to the frontend CI.
- Self-contained artifacts grow linearly with puzzle count (240 MB SGF at 500K scale).
- No operational benefit — GitHub Pages already serves static files with CDN caching.

## Consequences

- Runtime fetch base is `APP_CONSTANTS.paths.cdnBase` (unchanged from current system).
- CI/CD pipeline writes database files and SGF to `yengo-puzzle-collections/` and pushes to the repo.
- Frontend bootstrap: fetch `yengo-search.db` → initialize sql.js WASM → load DB into memory → query via SQL.
- SGF fetch path: `sgf/{batch}/{hash}.sgf` (content-addressed, append-only).
- Topology changes require this ADR to be updated and re-reviewed.
- Route/query contract drift must be treated as deployment contract breakage.

## Validation Checklist

- [x] One topology mode selected (no dual-path fallback) — **Repo-static**.
- [x] Database, daily views, and SGF served from the same mode — all via `CDN_BASE_PATH`.
- [x] Cache invalidation strategy documented for selected mode — `db-version.json` + content-addressed SGF.
- [ ] CI/CD packaging rules updated and verified.
- [ ] Route and loader contracts validated end-to-end.
- [ ] Canonical URL behavior verified for `/contexts` routes.
- [ ] `offset` and `id` replay semantics validated.
- [ ] Public `id` contract checked to avoid raw storage-hash exposure.

> **See also**:
>
> - [Concepts: SQLite Index Architecture](../concepts/sqlite-index-architecture.md) — Terminology and schema
> - [Architecture docs index](./README.md)
> - [System Overview](./system-overview.md)
