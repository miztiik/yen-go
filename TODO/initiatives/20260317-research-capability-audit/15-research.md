# Research Brief: YenGo Comprehensive Capability Audit

> **Research question**: What does YenGo already do well, what's partially built, what's planned but not started, and what's the single most valuable missing addition?
>
> **Boundaries**: Codebase evidence + config/docs/TODO analysis. No code changes. Focused on user-facing value and strategic direction.
>
> **Last updated**: 2026-03-17

---

## 1. Research Question and Boundaries

**Goal**: Produce a complete inventory of YenGo's capabilities across frontend, backend, tooling, and content — then identify the highest-value gap.

**Scope**:
- Frontend feature inventory (pages, components, hooks, services)
- Backend pipeline maturity (stages, adapters, enrichment)
- Content scale (puzzles, collections, tags, levels)
- TODO/planned work
- Competitive gap analysis for a Go puzzle app

**Out of scope**: Implementation changes, performance benchmarking, external competitor product testing.

---

## 2. Existing Capabilities (What Works Today)

### 2.1 Frontend — User-Facing Features

| R-ID | Feature | Maturity | Key Files |
|------|---------|----------|-----------|
| R-1 | **6-Mode Home Page** — modern tile grid with Daily, Training, Rush, Collections, Technique, Learning modes | Production | `pages/HomePageGrid.tsx` |
| R-2 | **Puzzle Solver** — unified 2-column (desktop) / stacked (mobile) solver with OGS Goban rendering | Production | `components/Solver/SolverView.tsx`, `hooks/useGoban.ts`, `hooks/usePuzzleState.ts` |
| R-3 | **Daily Challenge** — 3-section daily puzzles (standard, timed, by_tag) with calendar strip, blitz timer, daily summary | Production | `pages/DailyChallengePage.tsx`, `pages/DailyBrowsePage.tsx`, `services/dailyChallengeService.ts`, `services/dailyQueryService.ts` |
| R-4 | **Training Mode** — 9-level graded progression (Novice→Expert), tag/content-type filtering, accuracy tracking, level unlock at 70% | Production | `pages/TrainingViewPage.tsx`, `pages/TrainingBrowsePage.tsx`, `components/Training/` |
| R-5 | **Puzzle Rush** — timed speed mode (1-30 min), 3-life system, level/tag filtering, score tracking, dedicated overlay HUD | Production | `pages/PuzzleRushPage.tsx`, `pages/RushBrowsePage.tsx`, `components/Rush/`, `hooks/useRushSession.ts` |
| R-6 | **Collections Browser** — SQLite-backed FTS5 search, curated editorial collections, progress tracking per collection | Production | `pages/CollectionsBrowsePage.tsx`, `pages/CollectionViewPage.tsx`, `services/collectionService.ts` |
| R-7 | **Technique Focus Mode** — browse puzzles by technique tag (28 tags), filter by level, count indicators | Production | `pages/TechniqueBrowsePage.tsx`, `pages/TechniqueViewPage.tsx` |
| R-8 | **Random Challenge** — random puzzle by level with surprise factor | Production | `pages/RandomChallengePage.tsx`, `pages/RandomPage.tsx` |
| R-9 | **Learning Page** — structured curriculum with 3 tiers (Foundations→Building Strength→Advancing to Dan), topic-based lessons | Production | `pages/LearningPage.tsx`, `data/learning-topics.ts` |
| R-10 | **Progressive Hints** — 3-tier system (text→area→exact coordinate with `{!coord}` token resolution), board marking integration | Production | `components/Solver/HintOverlay.tsx`, `hooks/useHints.ts`, `lib/hints/` |
| R-11 | **Solution Reveal** — modal solution tree, gated until wrong move or explicit review request (no spoilers) | Production | `components/Solver/SolutionReveal.tsx` |
| R-12 | **Board Transforms** — 8 transforms (rotate, flip, color swap, zoom, coordinates) that rewrite SGF coordinates | Production | `components/Transforms/`, `hooks/useTransforms.ts` |
| R-13 | **Streak System** — daily streak tracking with milestones, tolerance for missed days, visual display in header | Production | `components/Streak/`, `hooks/useStreak.ts`, `lib/streak/`, `services/streakManager.ts` |
| R-14 | **Progress Tracking** — localStorage-backed per-puzzle completion records, mastery calculation (accuracy-based 6-level system) | Production | `services/progress/`, `services/progressTracker.ts`, `lib/mastery.ts` |
| R-15 | **Achievement System** — 22 achievements across 6 categories (puzzles, streaks, rush, mastery, collection, special), with bronze→platinum tiers | Model defined, partial wiring | `models/achievement.ts`, `tests/unit/achievement.test.ts` |
| R-16 | **Go Tips** — Japanese terminology tips displayed during sessions, level-filtered (90+ tips) | Production | Loaded at boot from `config/go-tips.json`, displayed in solver |
| R-17 | **Keyboard Navigation** — full keyboard support (H=hint, S=solution, R=reset, arrows=navigate) | Production | `components/QuickControls/` |
| R-18 | **PWA / Offline** — service worker, web manifest, works without internet | Production | `sw.ts`, `public/manifest.webmanifest` |
| R-19 | **Dark Mode** — full dark mode with custom board colors per theme | Production | Goban theme system + CSS custom properties |
| R-20 | **Responsive Design** — mobile/tablet/desktop with touch support | Production | Tailwind responsive classes throughout |
| R-21 | **SPA on GitHub Pages** — 404-redirect SPA routing with base path handling | Production | `public/404.html`, `lib/routing/routes.ts` |
| R-22 | **SQLite in Browser** — entire puzzle index loaded via sql.js WASM (~500KB), all queries in-memory | Production | `services/sqliteService.ts`, `services/puzzleQueryService.ts` |
| R-23 | **Auto-Advance** — configurable automatic progression to next puzzle after solve | Production | `hooks/useAutoAdvance.ts` |
| R-24 | **Audio Feedback** — stone placement and correct/wrong/complete sound effects via Goban | Production | `services/audioService.ts` |

### 2.2 Backend — Pipeline Capabilities

| R-ID | Capability | Maturity | Key Files |
|------|-----------|----------|-----------|
| R-25 | **3-Stage Pipeline** (ingest→analyze→publish) with per-stage execution, checkpointing, and resume | Production | `stages/ingest.py`, `stages/analyze.py`, `stages/publish.py`, `pipeline/coordinator.py` |
| R-26 | **5 Adapters** — sanderland (HTTP/JSON), local (filesystem), kisvadim (local), url (HTTP), travisgk (local) | Production | `adapters/` directory |
| R-27 | **Enrichment Engine** — 8-module enrichment: hints, region, ko, move_order, refutation, solution_tagger, quality, complexity | Production | `core/enrichment/` |
| R-28 | **Heuristic Classification** — difficulty classification mapping to 9 levels, confidence-based technique detection for 28 tags | Production | `core/classifier.py`, `core/tagger.py` |
| R-29 | **Content-Hash Identity** — SHA256[:16]-based puzzle identity, GN==filename invariant | Production | `core/naming.py` |
| R-30 | **Dual SQLite DB Architecture** — DB-1 (browser search, ~500KB) + DB-2 (backend content+dedup) with incremental rebuild | Production | `core/db_builder.py`, `core/content_db.py` |
| R-31 | **Daily Challenge Generation** — level/tag-based puzzle selection, rolling window pruning, DB-1 injection | Production | `daily/generator.py`, `daily/db_writer.py` |
| R-32 | **Publish Log & Rollback** — append-only JSONL audit trail, run/puzzle-level rollback with DB-1 rebuild | Production | `publish_log.py`, `rollback.py` |
| R-33 | **13-Command CLI** — run, status, sources, daily, clean, validate, publish-log, rollback, vacuum-db, inventory | Production | `cli.py` |
| R-34 | **SGF Builder & Parser** — KaTrain-derived parser, builder with all YenGo custom properties, round-trip support | Production | `core/sgf_builder.py`, `core/sgf_parser.py`, `core/sgf_publisher.py` |
| R-35 | **Config-Driven Everything** — tags, levels, quality, validation, property policies all from `config/*.json` | Production | `config/loader.py`, 14 config files |

### 2.3 Tools Ecosystem

| R-ID | Tool | Purpose | Maturity |
|------|------|---------|----------|
| R-36 | `puzzle-enrichment-lab` | KataGo-powered AI enrichment — solution tree building, technique detection (28 detectors), difficulty estimation, refutation generation, 3-tier hints, teaching comments | Active development, ~220+ tests |
| R-37 | `puzzle_intent` | Goal inference (attack/defend/connect/capture) from SGF position using keyword + semantic matching | Functional |
| R-38 | `sgf2img` | SGF→PNG/GIF image exporter for documentation/social sharing | Functional |
| R-39 | `core/` (tools/core) | Shared utilities: atomic write, batching, checkpoint, HTTP, SGF analysis, text cleaning, Chinese translation | Production |
| R-40 | Source-specific importers | blacktoplay, gotools, go_problems, ogs, tasuki, t-dragon, weiqi101, plus 8 more | Various maturity |
| R-41 | `sgf-viewer-besogo` | Besogo SGF viewer bundled for potential solution tree replacement | Reference/research |

---

## 3. Partially Built Features

| R-ID | Feature | What Exists | What's Missing |
|------|---------|------------|----------------|
| R-42 | **Achievement System** | Full type definitions (22 achievements, 6 categories, 4 tiers), test file exists | No UI to display achievements, no notification toast, no service to check/unlock achievements, no Settings/Profile page to view them |
| R-43 | **Mastery System** | Accuracy-based 6-level mastery model (`lib/mastery.ts`), concepts doc written | No spaced repetition (listed as TODO in `docs/concepts/mastery.md`), no decay-over-time, no explicit "review failed puzzles" mode |
| R-44 | **Besogo Solution Tree Swap** | Full 7-phase plan written, Besogo source bundled in `tools/sgf-viewer-besogo/` | Not implemented — Goban's shadow DOM tree rendering is still active. Plan identifies shadow DOM as key UX limitation (no CSS customization, no branch coloring) |
| R-45 | **Statistics/Analytics** | `Statistics` and `StatisticsBySkillLevel` types defined in `types/progress.ts`, `UserStatistics` model exists | No dedicated Stats page, no visualization, no export, no performance trends or accuracy-over-time graphs |
| R-46 | **AI-Solve Enrichment** | 220+ tests, 12-phase plan, 5-sprint remediation plan, full code in `tools/puzzle-enrichment-lab/` | 20 identified implementation gaps (remediation sprints partially complete). Not yet integrated into pipeline for production use |
| R-47 | **Hinting Unification** | Transition plan v1 written, both lab and backend systems independently functional | Two separate hinting engines not yet unified. Contract-first integration not started |
| R-48 | **Learning Page Content** | Tier structure + topic framework defined, UI built | Lessons reference external URLs (Sensei's Library). No inline interactive content, no embedded examples |

---

## 4. Planned/TODO Features (Not Started)

| R-ID | Feature | Source Document | Status |
|------|---------|----------------|--------|
| R-49 | **Kishimoto-Mueller Search Optimizations** | `TODO/kishimoto-mueller-search-optimizations.md` | Plan complete, pending Review Panel approval. Adapts df-pn search techniques for 30-50% budget reduction in AI enrichment |
| R-50 | **Backend Trace Search Optimization** | `TODO/backend-trace-search-optimization.md` | Not started. String pre-filter + JSON index for trace search at scale (8-25s→<200ms at 200K entries) |
| R-51 | **Score Estimation WASM** | `TODO/134-score-estimation-wasm/` | Research phase. Browser-side score estimation via WASM (KataGo lite?) |
| R-52 | **Enrichment Lab GUI** | Multiple initiative entries | Web GUI for enrichment lab with SSE streaming, built on FastAPI bridge (`bridge.py` exists) |
| R-53 | **Puzzle Quality Scoring** | `TODO/puzzle-quality-scorer/`, `TODO/puzzle-quality-strategy/` | Research + implementation plan. Multi-dimensional quality classification |
| R-54 | **Lab-Web-KaTrain** | `TODO/lab-web-katrain/` | Full 9-section plan. Browser-based KaGo analysis with Ghostban integration |
| R-55 | **SQLite Index Optimizations** | Multiple initiative entries | Schema improvements, FTS5 tuning, incremental DB feasibility |
| R-56 | **60+ completed initiatives** | `TODO/initiatives/` | 65 initiative folders (research, feature, refactor, fix, UX) documenting completed work |

---

## 5. Content Scale

| Dimension | Count | Source |
|-----------|-------|--------|
| **Published Puzzles** | **2,000** | `db-version.json` (puzzle_count: 2000, as of 2026-03-17) |
| **SGF Batches** | 1 (0001/) | `yengo-puzzle-collections/sgf/` |
| **External Sources** | **16 directories** | `external-sources/`: 101weiqi, ambak-tsumego, blacktoplay, eidogo, goproblems (2 variants), gotools, Kanzufu, kisvadim, manual-imports, ogs, sanderland, t-hero, tasuki, tsumegodragon, Xuan Xuan Qi Jing |
| **Pipeline Adapters** | **5 active** | sanderland, local, kisvadim, url, travisgk |
| **Import Tools** | **12+** | tools/ directory has 12+ source-specific import scripts |
| **Collections** | **159** | `config/collections.json` |
| **Tags (Techniques)** | **28** | `config/tags.json` (objectives, tesuji, technique categories) |
| **Difficulty Levels** | **9** | `config/puzzle-levels.json` (Novice→Expert, 30k→9d) |
| **Go Tips** | **90+** | `config/go-tips.json` |
| **Schema Version** | **v15** | `CLAUDE.md` SGF Custom Properties |

**Content Gap**: 2,000 published puzzles is a good start but low for a comprehensive tsumego app. The 16 external sources suggest potential for **much larger scale** (most sources have 1,000-10,000+ puzzles). The pipeline infrastructure is built for scale (batching, checkpoints, incremental publish), but actual content throughput hasn't been maximized yet.

---

## 6. Technical Maturity Assessment

| Area | Rating | Evidence |
|------|--------|---------|
| **Frontend Architecture** | ★★★★★ Production | 14 pages, ~70 unit tests, TypeScript strict, Vitest+Playwright, Tailwind 4, Preact signals, SQLite WASM |
| **Backend Pipeline** | ★★★★★ Production | ~2,000 tests, 13-command CLI, 3-stage pipeline, dual-DB, rollback/audit trail, config-driven |
| **SGF Processing** | ★★★★★ Production | Custom parser (KaTrain-derived), builder, publisher, all 15+ custom properties, round-trip |
| **Enrichment Lab** | ★★★★☆ Advanced Prototype | 220+ tests, 28 technique detectors, KataGo integration, but 20 known gaps in AI-solve |
| **Content Scale** | ★★☆☆☆ Early | 2,000 puzzles published vs 16 sources with 10,000+ potential. Infrastructure ready, throughput needed |
| **User Engagement Features** | ★★★☆☆ Partial | Streak, mastery model, achievement types exist. No stats page, no spaced repetition, no social |
| **Documentation** | ★★★★★ Excellent | 4-tier doc structure (architecture/how-to/concepts/reference), AGENTS.md per module, extensive TODO/initiative tracking |
| **Testing** | ★★★★★ Comprehensive | ~2,000 backend + ~70 frontend unit + Playwright E2E + visual regression |
| **DevOps/Deploy** | ★★★★☆ Good | GitHub Pages static deploy, PWA, SPA routing, but no CI pipeline visible in workspace |

---

## 7. Unique Strengths (What Makes YenGo Different)

| R-ID | Strength | Why It Matters |
|------|----------|---------------|
| R-57 | **Zero-Backend Architecture** | No server costs, no downtime, works offline. GitHub Pages deployment = free forever. Competitors (OGS, GoProblems) require servers |
| R-58 | **SQLite-in-Browser** | Full relational query capability in the browser via sql.js WASM. Enables complex filtering (level + tags + collection + quality) without API calls |
| R-59 | **KataGo-Powered Enrichment Pipeline** | AI enrichment with 28 technique detectors, difficulty estimation, 3-tier hints, refutation generation. Most competitors use human-only tagging |
| R-60 | **Config-Driven Tag Taxonomy** | 28 standardized tags with 200+ aliases covering Chinese/Japanese/Korean Go terminology. Multi-language source normalization is unique |
| R-61 | **Content-Hash Identity** | SHA256-based puzzle identity ensures deduplication across 16+ sources. No other open-source tsumego app has this |
| R-62 | **Progressive Disclosure Design** | Solution tree gated until wrong answer, 3-tier hints, no spoilers — Apple-inspired minimalism with pedagogical intent |
| R-63 | **Board Transforms** | 8 physical transforms that rewrite SGF coordinates — rotation, flip, color swap. Unique training feature (prevents pattern memorization) |
| R-64 | **Governance-Grade Planning** | Expert panel review (simulated 9p Go professionals + staff engineers), 65+ documented initiatives, formal gate protocols |
| R-65 | **Comprehensive Schema (v15)** | 15 custom SGF properties covering difficulty, techniques, hints, quality, complexity, ko, move order, corner, refutations, collection membership, pipeline metadata |

---

## 8. Critical Gaps — What's Completely Missing

| R-ID | Gap | Impact | Competitors That Have It |
|------|-----|--------|--------------------------|
| R-66 | **No Statistics/Analytics Page** | Users can't see how they're improving over time. No accuracy trends, solve time history, technique strengths/weaknesses, or performance visualization | BlackToPlay, GoProblems, 101Weiqi, chess.com |
| R-67 | **No Spaced Repetition** | Users who get a puzzle wrong never systematically see it again. Mastery concept doc explicitly lists this as TODO. Most impactful learning technique for memorization | BlackToPlay, chess.com, Anki |
| R-68 | **No User Profile/Settings Page** | Achievements exist in model only. No page to view achievements, customize settings (sound, theme, board preferences), or see overall progress summary | Every major puzzle app |
| R-69 | **Content Scale Bottleneck** | 2,000 puzzles with infrastructure for 10,000+. Daily challenge needs diversity; training modes need depth per level. 16 sources untapped | OGS (50K+), GoProblems (40K+), BlackToPlay (10K+) |
| R-70 | **No "Retry Wrong" Mode** | Failed puzzles are recorded but there's no way to filter/replay them. Critical for deliberate practice | BlackToPlay, chess.com tactics trainer |
| R-71 | **No Solution Tree Visualization** | Current Goban tree is shadow-DOM locked (no CSS customization). Besogo swap is planned but not started. Users can't easily explore variations | OGS, KGS, Sabaki |
| R-72 | **No Social/Sharing Features** | No way to share a puzzle, challenge a friend, or compare progress. Entirely single-player | OGS, GoProblems, Lichess |
| R-73 | **No Comments/Discussion** | No way for users to leave notes on puzzles or discuss alternatives | GoProblems, OGS |

---

## 9. Biggest Opportunities — Ranked by Value/Effort

### Recommendation 1: **Statistics & Analytics Page** (HIGH VALUE / MEDIUM EFFORT)

- **Why first**: All the data already exists in localStorage (progress, streaks, mastery scores, technique accuracy). Types are defined (`Statistics`, `StatisticsBySkillLevel`). This is purely a frontend visualization job.
- **User impact**: Transforms YenGo from "puzzle app" to "learning tool." Users need to see improvement over time for motivation and retention.
- **What to build**: Solve history chart, accuracy by level heatmap, technique radar chart, streak calendar, session stats.
- **Effort**: 1 page + 3-5 visualization components. No backend changes. Medium frontend effort.
- **Risk**: Low.

### Recommendation 2: **Content Scale Push — Publish 8,000+ Additional Puzzles** (HIGH VALUE / LOW-MEDIUM EFFORT)

- **Why second**: The pipeline infrastructure is production-ready. 16 external sources exist with 10,000+ raw puzzles. The bottleneck is running the pipeline, not building it. More content improves every mode (daily diversity, training depth, rush variety).
- **What to do**: Build/activate adapters for more sources (currently only 5 adapters for 16 sources). Run pipeline to publish from eidogo, goproblems, ogs, 101weiqi, etc.
- **Effort**: Per-source adapter work (small) + pipeline runs (automated).
- **Risk**: Low (pipeline has rollback + audit trail).

### Recommendation 3: **Spaced Repetition / Retry Wrong Mode** (HIGH VALUE / MEDIUM EFFORT)

- **Why third**: The mastery doc explicitly lists this as the most impactful missing learning feature. Failed puzzle IDs are already tracked in localStorage. Needs a review queue and scheduling algorithm.
- **What to build**: "Review" mode tile on home page. Leitner-style box system or simple "retry failed" queue. Surface count of pending reviews in home tile.
- **Effort**: 1 new page, 1 service (scheduler), localStorage schema extension. Medium effort.
- **Risk**: Low-medium (scheduling algorithm design needed).

### Recommendation 4: **Achievement System UI + Profile Page** (MEDIUM VALUE / MEDIUM EFFORT)

- **Why fourth**: The achievement model is already fully defined (22 achievements, 4 tiers). Needs: achievement check service, notification toast, and a Profile/Settings page. Would also house settings (currently only accessible via header gear icon).
- **What to build**: Achievement checker service, notification component, Profile page with stats summary + achievement grid + settings.
- **Effort**: 1 page + 2 services + 1 notification component. Medium effort.
- **Risk**: Low.

### Recommendation 5: **Solution Tree Visualization (Besogo Swap)** (MEDIUM VALUE / HIGH EFFORT)

- **Why fifth**: Full plan exists (7 phases). Would unlock CSS-styleable branch coloring (correct/wrong/off-tree). Bidirectional sync with Goban required. Improves review mode significantly.
- **What to build**: ESM bundle, Preact wrapper, bidirectional navigation, wire into SolverView, CSS/dark mode.
- **Effort**: High (7-phase plan, ~3 estimated days of focused work).
- **Risk**: Medium (bidirectional sync complexity, echo loop guards).

---

## 10. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| **Post-research confidence** | 92/100 — high confidence in capability assessment. Minor uncertainty around enrichment lab integration timeline and exact external source puzzle counts |
| **Post-research risk level** | **Low** — all top recommendations build on existing infrastructure. No architectural changes needed for top 4 items |

---

## 11. Open Questions for Planner

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Which opportunity should be the first initiative to execute? | A: Statistics page / B: Content scale push / C: Spaced repetition / D: Achievement UI / E: Other | A (Statistics page — all data exists, pure frontend, highest user-visible impact) | | ❌ pending |
| Q2 | What is the target puzzle count for the next content push? | A: 5,000 / B: 10,000 / C: 20,000+ / D: Other | B (10,000 — achievable with 3-4 more adapter activations, meaningful for daily challenge diversity) | | ❌ pending |
| Q3 | Should spaced repetition use Leitner boxes (simple) or SM-2 algorithm (proven but complex)? | A: Leitner / B: SM-2 / C: Custom accuracy-based / D: Research needed | A (Leitner — simple, well-understood, fits localStorage constraints) | | ❌ pending |
| Q4 | Is a combined Profile/Settings/Stats page preferred, or separate pages? | A: Combined / B: Separate pages / C: Stats as page + Settings as modal | C (Stats page + Settings modal — keeps navigation flat, most competitors separate these) | | ❌ pending |
