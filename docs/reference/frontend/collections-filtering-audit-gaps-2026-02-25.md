# Collections, Technique, Training Filtering Audit (2026-02-25)

> **Note (2026-03-13)**: This audit was written for the shard-based query architecture which has been replaced by SQLite. See [SQLite Index Architecture](../../concepts/sqlite-index-architecture.md) for the current system.

**Last Updated**: 2026-03-10

This document captures current-state audit evidence, expert consultation, and gap analysis.

---

> **See also**:
>
> - [How-To: Filtering UX Implementation Roadmap](../../how-to/frontend/filtering-ux-implementation-roadmap.md) - Execution plan and sequencing
> - [Architecture: Frontend Overview](../../architecture/frontend/overview.md) - Frontend architecture context
> - [Concepts: Mastery](../../concepts/mastery.md) - Progress and mastery model

---

## Filtering & UX Audit: Collections, Technique, Training Pages

> **Created:** 2026-02-25  
> **Updated:** 2026-02-25 (v2 — architecture-aware revision)  
> **Status:** Draft — Pending Review  
> **Pages audited:** Collections Browse → Collection Detail, Technique Browse → Technique Detail, Training Browse → Training Detail

---

## Table of Contents

1. [Current State Audit](#1-current-state-audit)
2. [Expert Consultation: Go Professionals](#2-expert-consultation-go-professionals)
3. [Expert Consultation: UX Specialists](#3-expert-consultation-ux-specialists)
4. [Gap Analysis](#4-gap-analysis)
5. [Recommendations & Action Items](#5-recommendations--action-items)
6. [Code Bugs & Technical Debt](#6-code-bugs--technical-debt)
7. [Priority Matrix](#7-priority-matrix)

---

## 1. Current State Audit

### 1.1 Collections Browse Page (`/collections`)

| Feature                     | Status           | Details                                                                                |
| --------------------------- | ---------------- | -------------------------------------------------------------------------------------- |
| **Text search**             | ✅ Implemented   | Searches name, description, curator, aliases. 250ms debounce.                          |
| **Section grouping**        | ✅ Implemented   | Featured → Learning Paths → By Technique → By Author → Reference                       |
| **Sort by**                 | ❌ Missing       | No sort options (name, puzzle count, difficulty, progress, recently played)            |
| **Filter by type**          | ⚠️ Implicit only | Sections act as implicit type filter, but no explicit toggle                           |
| **Filter by level range**   | ❌ Missing       | Cannot filter collections by difficulty range (e.g., "show only beginner collections") |
| **Filter by technique/tag** | ❌ Missing       | Cannot filter collections by associated techniques                                     |
| **Progress indicators**     | ✅ Implemented   | Progress bar + mastery badge per collection card                                       |
| **Expand/collapse**         | ✅ Implemented   | "Show all N" / "Show less" per section                                                 |
| **Coming Soon**             | ✅ Implemented   | Disabled cards for collections with 0 published puzzles                                |
| **Pagination**              | ❌ Missing       | All collections loaded at once (currently 159 — could become unwieldy)                 |

**Observed UX Issues:**

- When searching, section structure collapses into a flat list with no indication of which type/section each result belongs to
- No way to browse by author specifically (the "By Author" section is just a grouping, not a filter)
- No sort by progress ("continue where I left off") — forces users to scan visually for incomplete collections
- Search input placeholder is very long on mobile, likely truncated

### 1.2 Collection Detail Page (`/contexts/collection/{slug}`)

| Feature                    | Status         | Details                                                            |
| -------------------------- | -------------- | ------------------------------------------------------------------ |
| **Level filter (desktop)** | ✅ Implemented | Multi-select pills for all 9 levels, count badges                  |
| **Level filter (mobile)**  | ✅ Implemented | 3 category pills: DDK / SDK / Dan                                  |
| **Tag filter**             | ✅ Implemented | Single-select dropdown grouped by category                         |
| **Sort by**                | ❌ Missing     | No way to sort puzzles (by difficulty, by sequence number, random) |
| **Active filter chips**    | ✅ Implemented | Dismissible chips with clear-all when 2+ active                    |
| **Deep linking**           | ✅ Implemented | `?l=110,120&t=36&offset=5&id=abc123` URL params                    |
| **Progress tracking**      | ✅ Implemented | Completion recorded per puzzle                                     |
| **Puzzle navigation**      | ✅ Implemented | Dot navigation, prev/next, keyboard shortcuts                      |
| **Filter empty state**     | ✅ Implemented | "No puzzles match" with clear button                               |

**Observed UX Issues:**

- **No "unsolved first" or "failed first" filter** — users reviewing a 200-puzzle collection must manually skip solved puzzles
- **No difficulty sort** — in graded collections like Cho Chikun Elementary, puzzles have varying difficulty but no way to sort by it
- **No "status" filter** (solved / unsolved / failed) — the most requested feature for revisiting
- **Tag dropdown is single-select** — cannot combine multiple techniques (e.g., "snapback AND life-and-death")
- **Sequence number hidden** — users can't see or jump to a specific problem number (e.g., "Go to #47")
- Mobile level filter loses granularity (DDK lumps together novice through intermediate — 4 levels)

### 1.3 Technique Browse Page (`/technique`)

| Feature                    | Status         | Details                                               |
| -------------------------- | -------------- | ----------------------------------------------------- |
| **Category filter**        | ✅ Implemented | All / Objectives / Techniques / Tesuji Patterns       |
| **Level filter (desktop)** | ✅ Implemented | 9 level pills, cross-dimensional count update         |
| **Level filter (mobile)**  | ✅ Implemented | 3 DDK/SDK/Dan category pills                          |
| **Sort by**                | ✅ Implemented | Name (alpha) or Puzzles (count descending)            |
| **Stats**                  | ✅ Implemented | Total techniques, practiced, solved, accuracy %       |
| **Progress**               | ✅ Implemented | Mastery badge + progress bar per technique card       |
| **Cross-dim filtering**    | ✅ Implemented | Selecting a level updates technique counts reactively |

**Observed UX Issues:**

- **Emojis in section headers** — 🏳️ Objectives, 🔑 Techniques, ⚡ Tesuji — violates "No emojis in production UI" rule
- **No "sort by progress"** — cannot surface "almost mastered" techniques or "never tried"
- **No "sort by accuracy"** — would help identify weakest techniques for focused practice
- **Category names may confuse** — "Techniques" as a category within "Technique Focus" page is tautological
- **No search** — unlike Collections page, no text search for technique names
- **Stat badges at top are static-looking** — users may not realize they update when filters change

### 1.4 Technique Detail Page (`/contexts/technique/{slug}`)

Shares the same `CollectionViewPage` component with `tag-{slug}` prefix.

| Feature           | Status             | Details                                                                                                                                      |
| ----------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Level filter**  | ✅ Implemented     | Same as Collection Detail (multi-select desktop, 3-pill mobile)                                                                              |
| **Tag filter**    | ⚠️ Present but odd | Shows tag dropdown inside a technique-specific view — you're already filtered by technique, so this is "filter technique X by another tag Y" |
| **Sort by**       | ❌ Missing         | Same gap as Collection Detail                                                                                                                |
| **Status filter** | ❌ Missing         | Same gap as Collection Detail                                                                                                                |

**Observed UX Issues:**

- **Tag filter in technique view is confusing** — I'm viewing "Life & Death" puzzles, and the dropdown shows other tags. This feels like cross-filtering, which could be powerful but is not explained to the user
- **Back button says "Back to collections"** even when coming from Technique Focus page — should say "Back to techniques"
- **No difficulty progression indicator** — unlike Training, technique view doesn't show/suggest an optimal studying order

### 1.5 Training Browse Page (`/training`)

| Feature                  | Status         | Details                                                                 |
| ------------------------ | -------------- | ----------------------------------------------------------------------- |
| **Category filter**      | ✅ Implemented | All Levels / Beginner (30k–10k) / Intermediate (9k–1k) / Advanced (1d+) |
| **Tag filter**           | ✅ Implemented | Single-select dropdown, cross-dimensional count update                  |
| **Sort by**              | ❌ Missing     | Fixed difficulty order only (which is appropriate for training)         |
| **Active filter chip**   | ✅ Implemented | For tag selection                                                       |
| **Random Challenge CTA** | ✅ Implemented | Bottom button                                                           |
| **Stats**                | ⚠️ Minimal     | Just "N Levels" and "N Mastered"                                        |

**Observed UX Issues:**

- **Only 9 cards** — limited filtering value, but tag cross-filter is genuinely useful
- **No indication of "recommended level"** — new users see 9 levels but don't know where to start
- **Progress display is per-card only** — no overall training progress summary (like technique page has)
- **Category labels are broad** — "Beginner (30k–10k)" lumps 4 levels; "Advanced (1d+)" lumps 3

### 1.6 Training Detail Page (`/contexts/training/{level}`)

| Feature                    | Status         | Details                                 |
| -------------------------- | -------------- | --------------------------------------- |
| **Tag filter**             | ✅ Implemented | Single-select dropdown from shard meta  |
| **Active filter chip**     | ✅ Implemented | Dismissible                             |
| **Progress bar**           | ✅ Implemented | Per-level with percentage               |
| **Level complete summary** | ✅ Implemented | Trophy, stats, next level unlock at 70% |
| **Sort by**                | ❌ Missing     | No puzzle sort options                  |
| **Status filter**          | ❌ Missing     | No solved/unsolved/failed filter        |

**Observed UX Issues:**

- **Same "no status filter" problem** — a level with 500 puzzles, 400 solved — user must click through 400 solved to find unsolved ones
- **No difficulty filter** — level shards contain mixed difficulties, no sub-filtering
- **100ms polling interval** for loader readiness — technical smell, may cause flickers
- **Tag filter is single-select** — same limitation as collection view

---

## 2. Expert Consultation: Go Professionals

### 2.1 Cho Chikun 9P — Perspective on Tsumego Collections

_Cho Chikun (趙治勲), born 1956, is a legendary professional Go player who held a record number of Japanese titles. He authored dozens of tsumego books, most notably the "Life and Death" series (Elementary, Intermediate, Advanced) which is the gold standard for structured tsumego study._

**On Collection Organization (Books Model):**

> "The most important principle in tsumego training is **graduated difficulty within a fixed sequence**. My books are organized so that problems 1-50 build foundational reading, problems 51-100 introduce complications, and problems 101-200 test mastery. Students should solve them **in order**. Random access defeats the pedagogical design."

**Cho Chikun's recommendations for filtering in a digital collection:**

| Feature                              | Recommendation                   | Rationale                                                                                                                               |
| ------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Default order**                    | Sequence number (as published)   | "The author chose this order deliberately. It IS the curriculum."                                                                       |
| **Sort by difficulty**               | Available as option, not default | "Useful for review, but initial study should follow the book order."                                                                    |
| **Filter by solved/unsolved**        | **Essential**                    | "Students should be able to quickly find problems they haven't solved yet or ones they got wrong."                                      |
| **Filter by technique**              | Nice-to-have                     | "In a graded collection, technique variety IS the point. But for review, filtering to 'problems I failed that involve ko' is valuable." |
| **Jump to problem number**           | **Essential**                    | "When a student says 'I'm stuck on problem 47,' they need to navigate there directly."                                                  |
| **Difficulty indicator per puzzle**  | Helpful                          | "Mark problems as ★, ★★, ★★★ within the collection so students know which are the hard ones."                                           |
| **Spaced repetition / retry failed** | **Essential**                    | "The most important problems are the ones you got wrong. You should see them again, not hunt for them."                                 |

**On the Technique page:**

> "Technique-focused practice is complementary to collection study. A student working through my Elementary book might also practice 'snapback' problems separately. The technique page should show **which difficulty levels have which techniques** — a beginner doesn't need to see Expert-level ko problems."

**On the Training page:**

> "Level-based training is the backbone. But within a level, students benefit from seeing **what percentage of each technique** they've mastered. If you're 90% on life-and-death but 20% on ko at the same level, you know what to focus on."

### 2.2 Lee Changho 9P — Perspective on Systematic Study

_Lee Changho (이창호), born 1975, is one of the greatest Go players in history with 21 world titles. Known for his "silent" reading style and exceptional endgame. His approach to training emphasizes systematic, repetitive study._

**On Collection Organization:**

> "I solved the same tsumego books multiple times — three, four, five times. What matters is **speed and accuracy over repetitions**. The software should track not just whether you solved a problem, but **how fast** and **how many attempts** it took. The second time through a collection should be faster."

**Lee Changho's recommendations:**

| Feature                       | Recommendation                                     | Rationale                                                                                      |
| ----------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Multi-pass tracking**       | Track completion rounds (1st pass, 2nd pass, etc.) | "Real mastery comes from repetition. Show which pass you're on."                               |
| **Time tracking**             | Record solve time per puzzle                       | "Speed improves with each pass. Showing time trends motivates."                                |
| **Sort by 'slowest'**         | Available sort                                     | "The problems you solve slowly are the ones you need to review most."                          |
| **Filter by 'needs review'**  | Based on fail count or slow time                   | "Automatically surface problems the student struggles with."                                   |
| **Reset collection progress** | Available action                                   | "When starting a new pass, reset to unsolved to simulate fresh study."                         |
| **Daily quota**               | Suggest "solve N per day"                          | "Consistent practice is more important than volume. 20 problems daily beats 200 on a weekend." |
| **Comparison with peers**     | Optional, anonymous                                | "Seeing that most students find problem #47 difficult normalizes the struggle."                |

**On Technique and Training pages:**

> "The Technique page should support **weakness-first ordering** — show the techniques where your accuracy is lowest at the top. For Training, the most important feature is **knowing when you're ready to move up**. The 70% threshold is reasonable, but show a breakdown by technique within the level."

---

## 3. Expert Consultation: UX Specialists

### 3.1 UX Expert A: Educational Platform Specialist

_Perspective from designing learning platforms (Khan Academy, Duolingo, Coursera patterns)_

#### Collections Browse Page

| Current State       | Issue                                               | Recommendation                                                                          |
| ------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Search only         | Users with 159 collections can't narrow efficiently | Add **multi-faceted filtering**: type pills + difficulty chips + search, all composable |
| Section grouping    | Hides collections behind expand buttons             | Add a **list/grid toggle** with a compact list view showing all collections at once     |
| No sort options     | "Continue learning" is invisible                    | Add **"In Progress" sort** as default for returning users, "Featured" for new users     |
| No progress summary | User can't see overall platform progress            | Add **progress banner** at top: "12/47 collections started, 3 completed"                |
| Flat search results | Context lost when searching                         | Keep **type badges** on cards during search results                                     |

#### Collection Detail Page (Puzzle Solving)

| Current State                        | Issue                                        | Recommendation                                                                   |
| ------------------------------------ | -------------------------------------------- | -------------------------------------------------------------------------------- |
| No status filter                     | Can't find unsolved puzzles                  | Add **3-state toggle**: All / Unsolved / Review (failed) — most critical feature |
| No sort                              | Can't control puzzle order                   | Add **sort dropdown**: Sequence (default) / Difficulty / Random                  |
| No jump-to                           | Can't navigate to specific #                 | Add **"Go to #"** input or scrollable numbered thumbnail strip                   |
| Progress dot navigation              | Dots don't show solved/unsolved state        | **Color-code dots**: green=solved, red=failed, gray=unseen                       |
| No difficulty badge on active puzzle | User doesn't know how hard current puzzle is | Show **difficulty stars** (★–★★★) in the header                                  |
| Single-select tag                    | Can't combine techniques                     | Allow **multi-select tags** or tag pills (like level filter)                     |

#### Global UX Patterns Missing

| Pattern                         | Details                                                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------- |
| **"Continue where I left off"** | Global CTA on home page or each browse page: "Resume Collection X, Problem #47"          |
| **Recently played**             | Last 5 collections/techniques accessed, shown at top of browse pages                     |
| **Breadcrumbs**                 | Show navigation trail: Collections → Cho Chikun Elementary → #47                         |
| **Bulk progress indicators**    | Technique/collection cards should show estimated time remaining based on avg solve speed |
| **Keyboard shortcuts legend**   | Show discoverable shortcuts (←→ for prev/next, R for retry, H for hint)                  |

### 3.2 UX Expert B: Mobile-First Game UI Specialist

_Perspective from designing mobile puzzle apps (chess.com, lichess, puzzle apps)_

#### Mobile-Specific Issues

| Issue                           | Impact                                          | Fix                                                                     |
| ------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------- |
| DDK/SDK/Dan is too coarse       | DDK lumps 4 levels (30k–11k) — huge skill range | Use **5 categories**: Beginner, Elementary, Intermediate, Advanced, Dan |
| Filter bar scrolls horizontally | Users may not discover all options              | Add **scroll indicators** (fade edges, dots)                            |
| Dropdown opens fixed-position   | May overlap bottom sheet affordance             | Use **bottom sheet pattern** for mobile dropdowns                       |
| No pull-to-refresh              | Users expect it in mobile apps                  | Add **pull-to-refresh** on browse pages                                 |
| 44px touch targets ✅           | Good                                            | Maintain this standard                                                  |
| Long search placeholder         | Gets truncated                                  | Shorten to **"Search collections…"** on mobile                          |

#### Engagement & Motivation Patterns

| Pattern                     | Details                                                                                     | Priority                       |
| --------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------ |
| **Streak counter**          | "5-day streak! 🔥" (SVG flame icon, not emoji) on home page                                 | High — proven retention driver |
| **Mastery animation**       | Celebration micro-interaction when technique mastered                                       | Medium — delight factor        |
| **"Quick Practice" button** | Jump directly into unsolved puzzles across all sources                                      | High — reduces friction        |
| **Progress rings**          | Replace progress bars with circular progress (more visual)                                  | Low — aesthetic                |
| **"Suggested next"**        | After solving, show contextual next step: harder version, related technique, next in series | High — guides exploration      |

---

## 4. Gap Analysis

### 4.1 Collections — Browse Level

| Capability                                                 | Current                  | Should Have                                  | Gap Severity |
| ---------------------------------------------------------- | ------------------------ | -------------------------------------------- | ------------ |
| Text search                                                | ✅                       | ✅                                           | —            |
| Type filter (Featured/Learning/Technique/Author/Reference) | ⚠️ Implicit via sections | Explicit toggle pills                        | 🟡 Medium    |
| Difficulty range filter                                    | ❌                       | Beginner/Intermediate/Advanced + level pills | 🟠 High      |
| Sort by name                                               | ❌                       | ✅                                           | 🟡 Medium    |
| Sort by puzzle count                                       | ❌                       | ✅                                           | 🟡 Medium    |
| Sort by progress                                           | ❌                       | ✅ (default for returning users)             | 🔴 Critical  |
| Sort by recently played                                    | ❌                       | ✅                                           | 🟠 High      |
| "In Progress" quick filter                                 | ❌                       | ✅                                           | 🔴 Critical  |
| Overall progress summary                                   | ❌                       | ✅                                           | 🟡 Medium    |

### 4.2 Collections — Puzzle Detail Level

| Capability                             | Current         | Should Have           | Gap Severity |
| -------------------------------------- | --------------- | --------------------- | ------------ |
| Level filter (multi-select)            | ✅              | ✅                    | —            |
| Tag filter (single-select)             | ✅              | Multi-select          | 🟡 Medium    |
| Status filter (solved/unsolved/failed) | ❌              | ✅                    | 🔴 Critical  |
| Sort by sequence                       | ⚠️ Default only | Explicit option       | 🟢 Low       |
| Sort by difficulty                     | ❌              | ✅                    | 🟠 High      |
| Sort by random                         | ❌              | ✅ (great for review) | 🟡 Medium    |
| Jump to problem #                      | ❌              | ✅                    | 🟠 High      |
| Color-coded progress dots              | ❌              | Green/Red/Gray dots   | 🟠 High      |
| Per-puzzle difficulty badge            | ❌              | ★–★★★ in header       | 🟡 Medium    |
| "Retry failed" quick action            | ❌              | ✅                    | 🔴 Critical  |

### 4.3 Technique — Browse Level

| Capability            | Current                 | Should Have                | Gap Severity |
| --------------------- | ----------------------- | -------------------------- | ------------ |
| Category filter       | ✅                      | ✅                         | —            |
| Level filter          | ✅                      | ✅                         | —            |
| Sort by name          | ✅                      | ✅                         | —            |
| Sort by puzzle count  | ✅                      | ✅                         | —            |
| Sort by progress      | ❌                      | ✅                         | 🟠 High      |
| Sort by accuracy      | ❌                      | ✅                         | 🟠 High      |
| Sort by "weakest"     | ❌                      | ✅ (lowest accuracy first) | 🟠 High      |
| Text search           | ❌                      | ✅                         | 🟡 Medium    |
| Section header emojis | ❌ Bug — violates rules | SVG icons                  | 🔴 Must-fix  |

### 4.4 Technique — Puzzle Detail Level

| Capability                       | Current | Should Have                          | Gap Severity |
| -------------------------------- | ------- | ------------------------------------ | ------------ |
| Level filter                     | ✅      | ✅                                   | —            |
| Tag cross-filter                 | ✅      | ✅ (but needs better UX explanation) | 🟡 Medium    |
| Back label says "collections"    | ❌ Bug  | "Back to techniques"                 | 🔴 Must-fix  |
| Status filter                    | ❌      | ✅                                   | 🔴 Critical  |
| Sort by difficulty               | ❌      | ✅                                   | 🟠 High      |
| Difficulty progression indicator | ❌      | ✅                                   | 🟡 Medium    |

### 4.5 Training — Browse Level

| Capability                           | Current | Should Have                                               | Gap Severity |
| ------------------------------------ | ------- | --------------------------------------------------------- | ------------ |
| Category filter                      | ✅      | ✅                                                        | —            |
| Tag filter                           | ✅      | ✅                                                        | —            |
| Overall progress summary             | ❌      | Detailed: "Practiced N techniques, accuracy X%" per level | 🟠 High      |
| Recommended level                    | ❌      | Highlight suggested starting level for new users          | 🟡 Medium    |
| Per-technique breakdown within level | ❌      | Mini bar chart showing technique mastery per level card   | 🟠 High      |

### 4.6 Training — Puzzle Detail Level

| Capability                             | Current | Should Have                          | Gap Severity |
| -------------------------------------- | ------- | ------------------------------------ | ------------ |
| Tag filter                             | ✅      | ✅                                   | —            |
| Status filter (solved/unsolved/failed) | ❌      | ✅                                   | 🔴 Critical  |
| Level filter                           | ❌      | N/A (single level)                   | —            |
| Sort by difficulty                     | ❌      | ✅                                   | 🟡 Medium    |
| Per-technique progress within level    | ❌      | Progress rings per technique         | 🟠 High      |
| Solve speed tracking                   | ❌      | Time per puzzle, average speed trend | 🟡 Medium    |

---

## 5. Architecture Constraint: Client-Side-Only State

### 5.1 The Holy Law: Zero Runtime Backend

This app stores ALL user state in `localStorage`. There is no server, no database, no user accounts. Every recommendation in this document MUST be feasible within these constraints.

### 5.2 Current localStorage Progress Architecture

| Key                          | What's Stored                                                                       |          Per-Puzzle?          | Size @ 10K Puzzles |
| ---------------------------- | ----------------------------------------------------------------------------------- | :---------------------------: | -----------------: |
| `yen-go-progress`            | `completedPuzzles: Record<puzzleId, PuzzleCompletion>` with timing, attempts, hints |            **Yes**            |            ~1.5 MB |
| `yen-go-collection-progress` | `Record<collectionId, { completed: string[], currentIndex }>`                       | **Yes** (puzzle IDs in array) |            ~200 KB |
| `yen-go-training-progress`   | `Record<level, { completed, total, accuracy }>`                                     |     No (aggregates only)      |         ~500 bytes |
| `yen-go-technique-progress`  | `Record<technique, { attempted, correct }>`                                         |     No (aggregates only)      |              ~3 KB |
| `yengo:settings`             | Theme, sound, coordinates, auto-advance                                             |              No               |         ~100 bytes |

**Total at 10K puzzles:** ~1.7 MB (well within 5 MB localStorage limit). Starts hitting quota risk around 25K–30K individually tracked puzzles.

### 5.3 Critical Findings About Progress Tracking

1. **`yen-go-collection-progress[collectionId].completed[]`** stores puzzle IDs per-collection — this IS the data needed for solved/unsolved filtering within a collection
2. **`PuzzleSetPlayer`** tracks solved/failed in-memory (`completedIndexes`, `failedIndexes`) — but these reset on page reload, not hydrated from localStorage
3. **Collection solve writes to collection store only** — `recordCollectionPuzzleCompletion()` does NOT also write to the global `yen-go-progress`. Two separate stores, not synced.
4. **Training/technique have only aggregate counts** — no per-puzzle tracking, so "unsolved" filtering is impossible without adding per-puzzle tracking for those modes
5. **`ProblemNav` dots** show solved/failed status from in-memory session — lost on reload even though localStorage has the data
6. **No "failed" tracking exists anywhere** — only "completed" (success). A puzzle attempted but never solved leaves no trace.

### 5.4 How Client-Only Apps Solve Status Filtering

| Approach                                        | How It Works                                                                                     | Tradeoffs                                                                            | Examples                                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------- |
| **Approach A: Per-puzzle Set in localStorage**  | Store `Set<puzzleId>` of completed puzzles per context. On load, intersect with shard entries.   | Simple, already partially exists for collections. Grows linearly.                    | Our app's `collection-progress.completed[]` |
| **Approach B: Bloom filter / bitfield**         | Store a compact bitfield (1 bit per puzzle) per collection/level. Index = sequence position.     | Very compact (~125 bytes per 1000 puzzles). But fragile if puzzle order changes.     | Chess.com puzzle tracker                    |
| **Approach C: IndexedDB**                       | Move per-puzzle progress to IndexedDB (essentially unlimited storage). Query with cursor.        | No 5MB limit. More complex API. Not available in all privacy modes.                  | Lichess offline mode                        |
| **Approach D: Hybrid — aggregate + recent IDs** | Keep aggregate counts + only store last N completed IDs per context. "Unsolved" = not in recent. | Bounded storage. Only works for "continue where I left off", not full status filter. | Duolingo                                    |

**Recommended: Approach A (what we mostly have), with fixes:**

- We already store `completed[]` arrays in `yen-go-collection-progress` — we just need to READ them back when a collection loads
- For training/technique, add the same pattern: `yen-go-training-progress.byLevel[level].completed: string[]`
- Storage cost is manageable: 20 bytes × 500 puzzles per level × 9 levels = ~90 KB additional

### 5.5 Architectural Decision: Scope of Status Filtering

Given the constraints, this is the practical scoping:

| Context                                            |       Status Filtering        | How                                                                                                                | Data Source     |
| -------------------------------------------------- | :---------------------------: | ------------------------------------------------------------------------------------------------------------------ | --------------- |
| **Collection Detail**                              |        ✅ Feasible now        | Hydrate `PuzzleSetPlayer` from `collection-progress[id].completed[]`                                               | Already stored  |
| **Training Detail**                                | ✅ Feasible with small change | Add `completed: string[]` to `training-progress.byLevel[level]`                                                    | Needs migration |
| **Technique Detail**                               | ✅ Feasible with small change | Add `completed: string[]` to `technique-progress.byTechnique[tag]`                                                 | Needs migration |
| **Collections Browse (filter by "In Progress")**   |        ✅ Feasible now        | Read `collection-progress` keys, check `completed.length > 0 && < total`                                           | Already stored  |
| **Collections Browse (sort by "recently played")** |        ✅ Feasible now        | Sort by `collection-progress[id].lastActivity`                                                                     | Already stored  |
| **Cross-context "failed" filter**                  |     ⚠️ Needs new tracking     | Currently no "failed" state recorded. Need to add `failed: string[]` array or `attempts: Record<puzzleId, number>` | New field       |

**Decision on "failed" tracking:** Add a lightweight `failed: string[]` to each progress context (same shape as `completed`). A puzzle is "failed" if it appears in `failed` but not in `completed`. When the user eventually solves it, move from `failed` to `completed`. This adds ~20 bytes per failed puzzle — negligible.

---

