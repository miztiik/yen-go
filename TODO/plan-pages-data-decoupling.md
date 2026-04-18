# Plan: Decouple GitHub Pages Artifact from Puzzle Data Hosting

Last Updated: 2026-04-18
Status: Ready for execution by next agent
Correction Level: 4 (Large Scale)
Downtime Policy: Downtime accepted (single cutover is allowed)

## 1. Executive Summary

The current deployment works, but the architecture is wrong for scale.

The fix is to separate app hosting from data fetching:

1. Keep GitHub Pages for frontend app assets only.
2. Keep puzzle data files in the repo as-is (no external host needed).
3. Frontend fetches puzzle data from raw.githubusercontent.com at runtime.
4. Stop bundling puzzle data into the Pages artifact.
5. Stop redeploying the frontend app for daily data updates.

Data stays in the repo. The only change is where the frontend fetches it from: same-origin Pages artifact becomes cross-origin raw GitHub URL.

## 2. Problem Statement

Today, frontend deployment bundles the full data tree into the Pages artifact. This is operationally expensive and not necessary.

Even if it is fine at low volume, it will become fragile as puzzle count and SGF file count increase.

GitHub Pages limits are documented here:
https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

## 3. Evidence (Verified in Repository)

### 3.1 Deploy workflow currently bundles full puzzle collections

1. Bundle step copies entire collection into dist:
   [copy collections into dist](../.github/workflows/_deploy-pages.yml#L55)
2. Config folder copy also happens in same step block:
   [copy config into dist](../.github/workflows/_deploy-pages.yml#L56)
3. Only backend-only files are removed afterward, not SGF payloads:
   [remove yengo-content.db](../.github/workflows/_deploy-pages.yml#L58)
   [remove puzzle inventory state](../.github/workflows/_deploy-pages.yml#L59)
   [remove batch state](../.github/workflows/_deploy-pages.yml#L60)
4. Dist is uploaded as Pages artifact:
   [upload pages artifact](../.github/workflows/_deploy-pages.yml#L66)

### 3.2 Frontend runtime is hard-coupled to same-origin data path

1. CDN base is derived from BASE_URL and fixed to yengo-puzzle-collections path:
   [frontend constants cdnBase](../frontend/src/config/constants.ts#L67)
2. SQLite service paths are same-origin hardcoded (duplicates its own BASE derivation):
   [sqlite DB path](../frontend/src/services/sqliteService.ts#L4)
   [sqlite db-version path](../frontend/src/services/sqliteService.ts#L5)
3. SGF fetch uses centralized base path, which currently resolves same-origin:
   [fetch SGF content](../frontend/src/services/puzzleLoader.ts#L63)
4. Puzzle loader has its own hardcoded base URL for JSON data:
   [puzzle loader baseUrl](../frontend/src/lib/puzzle/loader.ts#L41)
5. Daily challenge entries reconstruct SGF path under same tree:
   [daily SGF path reconstruction](../frontend/src/services/dailyChallengeService.ts#L147)

### 3.3 Service worker currently rejects cross-origin fetch handling

1. Same-origin gate:
   [same-origin gate comment](../frontend/src/sw.ts#L122)
   [same-origin gate condition](../frontend/src/sw.ts#L123)
2. Cache patterns assume local yengo-puzzle-collections path:
   [puzzle json cache pattern](../frontend/src/sw.ts#L48)
   [sgf cache pattern](../frontend/src/sw.ts#L50)

### 3.4 Daily workflow still couples data update to app deploy

1. Daily workflow stages DB files in repo:
   [add search db](../.github/workflows/daily-generation.yml#L70)
   [add db version file](../.github/workflows/daily-generation.yml#L71)
2. Daily workflow calls shared deploy workflow:
   [daily workflow deploy call](../.github/workflows/daily-generation.yml#L86)

### 3.5 Current dataset is small now, but this is not future-proof

1. Current puzzle_count in this workspace:
   [current puzzle_count](../yengo-puzzle-collections/db-version.json#L3)

## 4. Root Cause

Deployment boundary is incorrect.

The application and content are shipped together, which causes:

1. Unnecessary artifact growth.
2. Unnecessary repeated transfer of static SGF payloads on app-only changes.
3. Data release cadence coupled to app release cadence.
4. Higher chance of hitting Pages size and deployment-time constraints in the future.

## 5. Target Architecture (Fix)

### 5.1 Data hosting strategy

No external host needed. Puzzle data files stay in the repo at `yengo-puzzle-collections/`.

The frontend fetches data at runtime from raw.githubusercontent.com, which:

- Serves any file from the repo (including binary `.db` files).
- Sets `Access-Control-Allow-Origin: *` (no CORS issues).
- Is backed by Fastly CDN.
- Requires zero infrastructure provisioning.

### 5.2 Runtime topology

1. App host:
   GitHub Pages (frontend app bundle only).
2. Data source:
   Same repo, same branch - fetched via raw.githubusercontent.com.
3. Data fetched at runtime:
   - db-version.json
   - yengo-search.db
   - sgf batch files

### 5.3 Build-time configuration

Frontend receives a new environment variable:

1. VITE_DATA_BASE_URL

Behavior:

1. If VITE_DATA_BASE_URL is set, frontend fetches all puzzle data from that URL.
   Production value: `https://raw.githubusercontent.com/{owner}/{repo}/main/yengo-puzzle-collections`
2. If absent, frontend uses current local fallback path (`${BASE}/yengo-puzzle-collections`) for dev compatibility.

### 5.4 Workflow topology

1. App deploy workflow:
   Builds frontend with VITE_DATA_BASE_URL and deploys app assets only. No collection bundling.
2. Daily generation workflow:
   Commits updated DB files to repo. Does NOT trigger frontend app redeploy.

## 6. Migration Plan (Phased)

### Phase 1: Frontend Runtime Decoupling

Edit files:

1. [constants.ts](../frontend/src/config/constants.ts)
2. [sqliteService.ts](../frontend/src/services/sqliteService.ts)
3. [lib/puzzle/loader.ts](../frontend/src/lib/puzzle/loader.ts)
4. [vite-env.d.ts](../frontend/src/vite-env.d.ts)

Changes:

1. Add `VITE_DATA_BASE_URL` to typed env interface in vite-env.d.ts.
2. In constants.ts: derive `cdnBase` from `VITE_DATA_BASE_URL` when present, fall back to current `${BASE}/yengo-puzzle-collections` for dev.
3. In sqliteService.ts: remove duplicated `BASE` derivation, consume `APP_CONSTANTS.paths.cdnBase` for DB and db-version paths.
4. In lib/puzzle/loader.ts: consume `APP_CONSTANTS.paths.cdnBase` instead of hardcoded `${BASE}/yengo-puzzle-collections/data`.

Deliverable:
Frontend can run against cross-origin data URL. Local dev unchanged.

### Phase 2: Service Worker Cross-Origin Support

Edit file:

1. [sw.ts](../frontend/src/sw.ts)

Changes:

1. Replace strict same-origin gate with an allowlist model:
   - App origin (location.origin).
   - Data origin (parsed from a build-time injected constant, or raw.githubusercontent.com).
2. Keep rejecting all unknown origins.
3. Ensure puzzle data requests from raw.githubusercontent.com use intended cache strategies (stale-while-revalidate for DB/SGF).
4. Bump cache version names to avoid stale cache conflicts after cutover.

Note: Service worker cannot access `import.meta.env`. The data origin must be injected at build time via Vite's `define` config or a generated constant.

Deliverable:
PWA caching works correctly for cross-origin data fetches.

### Phase 3: Deploy Workflow Decoupling

Edit files:

1. [shared deploy workflow](../.github/workflows/_deploy-pages.yml)
2. [deploy entry workflow](../.github/workflows/deploy.yml)

Changes:

1. Remove the "Bundle puzzle collections into build output" step from the shared deploy workflow (lines 53-60).
2. Keep config folder copy (tags.json, puzzle-levels.json are needed by Vite build-time imports, NOT fetched at runtime).
3. Inject `VITE_DATA_BASE_URL` as environment variable in the frontend build step.
4. Add preflight step: verify raw.githubusercontent.com data URL is reachable before deploying.

Deliverable:
Pages artifact no longer contains yengo-puzzle-collections. App bundle is small.

### Phase 4: Daily Workflow Decoupling

Edit file:

1. [daily generation workflow](../.github/workflows/daily-generation.yml)

Changes:

1. Keep daily DB generation and repo commit as-is.
2. Remove the `deploy` job that calls `_deploy-pages.yml`. Daily data commits should NOT trigger a full frontend redeploy.
3. Keep the `notify` job for failure alerting (adjust its `needs` dependency).

Note: The `deploy.yml` workflow triggers on push to main. To prevent daily data commits from triggering unnecessary app rebuilds, add a path filter to `deploy.yml`:

```yaml
on:
  push:
    branches: [main]
    paths-ignore:
      - 'yengo-puzzle-collections/**'
```

Deliverable:
Daily data updates commit to repo without triggering frontend redeploy.

### Phase 5: Cutover

1. Deploy frontend with VITE_DATA_BASE_URL pointing to raw.githubusercontent.com.
2. Validate production: browse, solve, daily challenge, collection views.
3. Verify service worker caches cross-origin requests correctly.
4. Verify daily workflow no longer triggers app deploy.

Deliverable:
Production running on decoupled architecture.

## 7. Exact Change Surface (for Next Agent)

### Primary files to edit (code):

1. [frontend constants](../frontend/src/config/constants.ts) - cdnBase derivation from env var
2. [frontend sqlite service](../frontend/src/services/sqliteService.ts) - use APP_CONSTANTS instead of duplicated BASE
3. [frontend puzzle loader](../frontend/src/lib/puzzle/loader.ts) - use APP_CONSTANTS instead of hardcoded base
4. [frontend service worker](../frontend/src/sw.ts) - cross-origin allowlist
5. [frontend vite env types](../frontend/src/vite-env.d.ts) - VITE_DATA_BASE_URL type
6. [vite config](../frontend/vite.config.ts) - inject data origin constant for service worker

### Primary files to edit (workflows):

7. [shared pages deploy workflow](../.github/workflows/_deploy-pages.yml) - remove collection bundling, add env var
8. [daily generation workflow](../.github/workflows/daily-generation.yml) - remove deploy job
9. [deploy entry workflow](../.github/workflows/deploy.yml) - add paths-ignore filter

### Primary files to edit (docs):

10. [database deployment topology ADR](../docs/architecture/backend/database-deployment-topology.md) - update decision from repo-static to raw-github-static
11. [frontend build deploy docs](../docs/how-to/frontend/build-deploy.md) - document new data URL config
12. [frontend architecture index](../docs/architecture/frontend/README.md) - note decoupled data fetch
13. [frontend how-to index](../docs/how-to/frontend/README.md) - link to updated guide

### Secondary validation references:

14. [frontend README architecture notes](../frontend/README.md)
15. [frontend CLAUDE.md](../frontend/CLAUDE.md) - update "Base Path & SPA Routing" section

### Cleanup:

16. [frontend config/cdn.ts](../frontend/src/config/cdn.ts) - dead code, delete

## 8. Acceptance Criteria

All must pass:

1. Pages deploy artifact does not include yengo-puzzle-collections.
2. Production app fetches yengo-search.db from raw.githubusercontent.com.
3. Production app fetches SGF files from raw.githubusercontent.com.
4. Daily challenge still works end-to-end.
5. Service worker caches cross-origin data requests correctly.
6. Daily data commit no longer triggers frontend app redeploy.
7. Frontend typecheck, tests, and build pass.
8. Local dev mode (`npm run dev`) still works with local files (no env var set).
9. Docs and ADR reflect new architecture.

## 9. Risk Register and Mitigations

1. Risk: raw.githubusercontent.com changes CORS policy or URL structure.
   Mitigation: VITE_DATA_BASE_URL is configurable - can point to any static host if GitHub changes behavior. Migration to R2/S3 is a one-line env var change.

2. Risk: Service worker stale cache behavior after origin change.
   Mitigation: Cache version bump forces fresh caches on first load after cutover.

3. Risk: Daily commit to main triggers unwanted Pages deploy.
   Mitigation: paths-ignore filter on deploy.yml prevents yengo-puzzle-collections changes from triggering deploy.

4. Risk: raw.githubusercontent.com rate limiting under heavy traffic.
   Mitigation: Service worker caching reduces repeat fetches. At current scale (~9K puzzles, ~500KB DB) this is not a concern. If it becomes one, switch VITE_DATA_BASE_URL to a CDN.

## 10. Rollback Plan

1. Restore collection bundling step in [deploy workflow](../.github/workflows/_deploy-pages.yml#L55).
2. Remove or unset VITE_DATA_BASE_URL from deploy environment.
3. Restore deploy job in [daily workflow](../.github/workflows/daily-generation.yml).
4. Remove paths-ignore from [deploy.yml](../.github/workflows/deploy.yml).
5. Redeploy app.

Rollback success criteria:

1. App loads DB and SGF from same-origin bundled path.
2. Users can continue solving puzzles.

## 11. Handover Memo

Debug Handover - 2026-04-18

### Target
Decouple GitHub Pages artifact from puzzle data hosting.

### Status
Expected:
App artifact contains only app assets; data fetched from raw.githubusercontent.com.

Actual:
Deploy workflow currently copies full puzzle collection into dist before Pages upload.

### Repro Steps

1. Check collection copy in deploy workflow at [copy step](../.github/workflows/_deploy-pages.yml#L55).
2. Check hardcoded same-origin data base in [frontend constants](../frontend/src/config/constants.ts#L67).
3. Check sqlite paths in [sqlite service](../frontend/src/services/sqliteService.ts#L4).
4. Check same-origin service worker gate in [service worker](../frontend/src/sw.ts#L123).
5. Check puzzle loader hardcoded base in [puzzle loader](../frontend/src/lib/puzzle/loader.ts#L41).

### Primary Candidate
Workflow and frontend runtime path coupling.

### Secondary Candidate
Service worker origin assumptions.

### Level and Flow
Level 4.
Phased execution with one cutover window.

### Fix Attempted in This Artifact
No runtime code changed in this plan artifact.

### Next Steps
Execute phases 1 to 5 in order.

## 12. Implementation Artifact (Execution Board)

Lane A: Frontend runtime decoupling

1. Add VITE_DATA_BASE_URL typed env support.
2. Wire constants.ts cdnBase through env var.
3. Consolidate sqliteService.ts to use APP_CONSTANTS (remove duplicated BASE).
4. Wire lib/puzzle/loader.ts to use APP_CONSTANTS.
5. Add environment typing.

Lane B: Service worker compatibility

1. Inject data origin constant via Vite define config.
2. Implement cross-origin allowlist in sw.ts.
3. Bump cache version names.
4. Validate cache behavior for cross-origin DB and SGF assets.

Lane C: CI and workflows

1. Remove collection bundling from app deploy workflow.
2. Inject VITE_DATA_BASE_URL in deploy build step.
3. Add preflight check for data URL reachability.
4. Remove deploy job from daily workflow.
5. Add paths-ignore filter to deploy.yml.

Lane D: Docs and operational handoff

1. Update database deployment topology ADR.
2. Update build and deploy how-to.
3. Update frontend architecture index and how-to index.
4. Update frontend CLAUDE.md base path section.

## 13. PR Checklist (for Next Agent)

Scope and governance:

- [ ] Correction level declared as Level 4 in PR description.
- [ ] Target architecture and non-goals stated in PR summary.

Code changes:

- [ ] Added VITE_DATA_BASE_URL env var support in [constants](../frontend/src/config/constants.ts).
- [ ] Consolidated [sqlite service](../frontend/src/services/sqliteService.ts) to use APP_CONSTANTS.paths.cdnBase.
- [ ] Consolidated [puzzle loader](../frontend/src/lib/puzzle/loader.ts) to use APP_CONSTANTS.paths.cdnBase.
- [ ] Updated [service worker](../frontend/src/sw.ts) for cross-origin allowlist.
- [ ] Added typed env declaration in [vite env definitions](../frontend/src/vite-env.d.ts).
- [ ] Injected data origin constant in [vite config](../frontend/vite.config.ts).
- [ ] Deleted dead code [config/cdn.ts](../frontend/src/config/cdn.ts).

Workflow changes:

- [ ] Removed collection copy from [shared deploy workflow](../.github/workflows/_deploy-pages.yml).
- [ ] Injected VITE_DATA_BASE_URL in deploy build step.
- [ ] Added preflight data URL check in deploy workflow.
- [ ] Removed deploy job from [daily workflow](../.github/workflows/daily-generation.yml).
- [ ] Added paths-ignore to [deploy entry workflow](../.github/workflows/deploy.yml).

Validation:

- [ ] Frontend typecheck passes.
- [ ] Frontend tests pass.
- [ ] Frontend build passes.
- [ ] Local dev mode works without VITE_DATA_BASE_URL set.
- [ ] Production smoke test passes for browse, solve, and daily.
- [ ] Artifact size delta recorded in PR notes.

Documentation:

- [ ] Updated [database deployment topology ADR](../docs/architecture/backend/database-deployment-topology.md).
- [ ] Updated [build and deploy guide](../docs/how-to/frontend/build-deploy.md).
- [ ] Updated [frontend architecture index](../docs/architecture/frontend/README.md).
- [ ] Updated [frontend how-to index](../docs/how-to/frontend/README.md).
- [ ] Updated [frontend CLAUDE.md](../frontend/CLAUDE.md).

Rollback readiness:

- [ ] Rollback procedure included in PR description.

## 14. Boundaries (Now vs Later)

Do now:

1. Decouple deployment topology.
2. Keep runtime behavior unchanged from user perspective.
3. Keep data schema unchanged.
4. Keep data files in the repo.

Do later:

1. Optional migration to dedicated CDN (R2/S3) if raw.githubusercontent.com becomes insufficient. This is a one-line env var change.
2. Optional service worker advanced cache controls per data type.
3. Optional path filter refinement for deploy triggers.

## 15. Final Recommendation

Proceed with the decoupling migration now.

The fix is simple: frontend artifact should not carry the SGF corpus. Data stays in the repo. Frontend fetches from raw.githubusercontent.com via a configurable env var. Daily data commits no longer trigger app redeployment.

No external infrastructure needed. No release mechanism. One env var, a few path consolidations, and workflow cleanup.
