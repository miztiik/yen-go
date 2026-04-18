# Database Deployment Topology (ADR)

**Last Updated**: 2026-04-18

## Status

**DECIDED** - 2026-02-21 (updated 2026-04-18 for data hosting decoupling)

## Context

The SQLite-based query architecture requires one canonical deployment topology for database files, daily views, and SGF artifacts. Mixed runtime fetch modes are disallowed because they create contract drift, cache inconsistency, and mixed-state rollout risk.

## Decision

Chosen option: **Raw-GitHub-static mode**

Data files remain in the repository at `yengo-puzzle-collections/`. The frontend fetches puzzle data at runtime from `raw.githubusercontent.com` via a configurable environment variable (`VITE_DATA_BASE_URL`). The GitHub Pages artifact contains only the frontend app bundle - no puzzle data.

This supersedes the prior repo-static mode where data was bundled into the Pages artifact alongside the app.

## Architecture

The selected topology preserves these locked URL and resolver contracts:

- Canonical routes are `/contexts` and `/search` only (no standalone `/puzzles/{id}` canonical route).
- Compact filter query keys are `l`, `t`, `c`, `q`.
- Navigation term is `offset` (not `cursor`).
- `id` query param represents the currently rendered puzzle identity for troubleshooting/replay.
- Public `id` must be a stable identifier and must not expose raw storage hashes in URL contracts.
- DB version + `offset` + optional `id` enable deterministic replay across evolving datasets.
- Quality dimension `q` is in-scope.

### Data fetch topology

- **App host**: GitHub Pages (frontend bundle only).
- **Data source**: Same repo, fetched via `raw.githubusercontent.com` (CORS: `Access-Control-Allow-Origin: *`).
- **Runtime base URL**: `APP_CONSTANTS.paths.cdnBase`, derived from `VITE_DATA_BASE_URL` when set, falling back to `${BASE}/yengo-puzzle-collections` for local development.
- **Service worker**: Allowlists both app origin and data origin for caching.

### Workflow topology

- App deploy (`deploy.yml`): Builds frontend with `VITE_DATA_BASE_URL`, deploys to Pages. Ignores `yengo-puzzle-collections/` changes.
- Daily generation (`daily-generation.yml`): Commits updated DB files to repo. Does NOT trigger app redeploy.

## Options

1. **Bundled-static mode** (rejected)
   - Database and artifacts packaged with the deployed frontend artifact.
   - Runtime fetch base is artifact-local.
2. **Repo-static mode** (prior decision, superseded)
   - Frontend fetches from same-origin Pages path, but data bundled into Pages artifact.
3. **Raw-GitHub-static mode** (current decision)
   - Data stays in repo. Frontend fetches from raw.githubusercontent.com at runtime.
   - Pages artifact contains only app code.

## Decision Drivers

- Single canonical fetch base in production.
- Deterministic deployment and rollback behavior.
- Cache invalidation clarity using `db-version.json`.
- Operational simplicity for CI/CD and release verification.
- Pages artifact size decoupled from puzzle corpus growth.
- Daily data updates should not require frontend redeployment.

## Decision Rationale

**Why Raw-GitHub-static:**

- No external infrastructure needed. Data stays in the repo as-is.
- `raw.githubusercontent.com` provides CORS headers and Fastly CDN backing.
- Pages artifact is small and fast to deploy (app code only).
- Daily data commits do not trigger app redeployment.
- `VITE_DATA_BASE_URL` is configurable - migration to a dedicated CDN is a one-line env var change.
- SGF files are content-addressed and immutable (infinitely cacheable).

**Why NOT Bundled-static:**

- Would require a frontend rebuild on every pipeline publish, coupling the pipeline to the frontend CI.
- Self-contained artifacts grow linearly with puzzle count.
- No operational benefit.

## Consequences

- Runtime fetch base is `APP_CONSTANTS.paths.cdnBase` (configurable via `VITE_DATA_BASE_URL`).
- CI/CD pipeline writes database files and SGF to `yengo-puzzle-collections/` and pushes to the repo.
- Frontend bootstrap: fetch `yengo-search.db` -> initialize sql.js WASM -> load DB into memory -> query via SQL.
- SGF fetch path: `sgf/{batch}/{hash}.sgf` (content-addressed, append-only).
- Service worker caches cross-origin data requests using stale-while-revalidate.
- Topology changes require this ADR to be updated and re-reviewed.
- Route/query contract drift must be treated as deployment contract breakage.

## Validation Checklist

- [x] One topology mode selected (no dual-path fallback) - **Raw-GitHub-static**.
- [x] Database, daily views, and SGF served from the same mode - all via `CDN_BASE_PATH`.
- [x] Cache invalidation strategy documented for selected mode - `db-version.json` + content-addressed SGF.
- [x] Deploy workflow does not bundle puzzle data into Pages artifact.
- [x] Daily workflow does not trigger frontend redeploy.
- [ ] CI/CD packaging rules updated and verified.
- [ ] Route and loader contracts validated end-to-end.
- [ ] Canonical URL behavior verified for `/contexts` routes.
- [ ] `offset` and `id` replay semantics validated.
- [ ] Public `id` contract checked to avoid raw storage-hash exposure.

> **See also**:
>
> - [Concepts: SQLite Index Architecture](../concepts/sqlite-index-architecture.md) - Terminology and schema
> - [Architecture docs index](./README.md)
> - [System Overview](./system-overview.md)
