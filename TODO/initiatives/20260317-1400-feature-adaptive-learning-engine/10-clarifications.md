# Clarifications — Adaptive Learning Engine

> Last Updated: 2026-03-17

## Context

Research identified that YenGo has a mature pipeline (2,000+ puzzles, 28 technique detectors, KataGo enrichment, SQLite WASM, 14 pages, 2,000+ tests) but the **user engagement loop is broken**: users solve puzzles with no feedback on growth, no awareness of weaknesses, and no intelligent guidance on what to solve next.

The biggest gap is between "puzzle app" and "learning platform."

## Planning Confidence Score

- **Score: 85/100**
  - Architecture seams are clear (frontend-only, localStorage + SQLite WASM) → no penalty
  - Two+ viable approaches with known tradeoffs → -10
  - No external precedent needed (SRS/adaptive patterns well-documented) → no penalty
  - Quality/performance impact is low-risk (client-side only) → -5
  - Test strategy is clear (Vitest, existing service test patterns) → no penalty
  - Rollout is straightforward (new pages, no breaking changes) → no penalty
- **Risk Level: low** — Greenfield feature, no existing code at risk, entirely client-side

## Research Invocation Decision

Research was invoked (two rounds) and confirmed:
1. All required data infrastructure exists (progress tracker, SQLite WASM, achievement model)
2. No competing implementation in the codebase
3. The gap is confirmed: zero stats visualization, zero adaptive routing, zero SRS

## Round 1 — High-Impact Clarifications

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **What is the primary user goal for this feature?** | A) See historical stats (passive dashboard) / B) Get guided next-puzzle recommendations (active coach) / C) Both — a stats dashboard PLUS an adaptive "Smart Practice" mode | C | Likes all features but needs to see concrete screens first | ✅ resolved (pending visual confirmation) |
| Q2 | **Is backward compatibility required, and should old code be removed?** | A) No backward compat needed (greenfield) / B) Must coexist with existing training modes | A | "I agree on no backward compatibility required" | ✅ resolved |
| Q3 | **Should the achievement system be activated as part of this initiative, or kept separate?** | A) Yes — wire up the 22 pre-defined achievements and show toast notifications / B) No — keep achievements as a separate future initiative / C) Partial — activate achievement evaluation but skip the UI page | A | Likes most features | ✅ resolved |
| Q4 | **What SRS algorithm for retry scheduling?** | A) Simple box system (Leitner 3-box) / B) SM-2 (SuperMemo classic) / C) No SRS — just "retry failed" queue / D) Custom lightweight interval based on error count + time | Revised: **D** — With 750K puzzles, a lightweight interval system (Leitner 3-box) is justified | User corrected puzzle scale to 500K-750K | ✅ resolved (superseded by Q10:B — simple per-module retry queue) |
| Q5 | **Should the adaptive engine suggest specific techniques to work on, or just difficulty levels?** | A) Technique-aware / B) Difficulty-only / C) Both | C | Likes this | ✅ resolved |
| Q6 | **Chart/visualization approach?** | A) SVG micro-charts / B) Lightweight chart library / C) CSS-only progress bars | A | Wants to see concrete visualization examples | ❌ pending (see wireframes below) |
| Q7 | **Where does this feature live in the navigation?** | A) Profile button in header / B) New home tile / C) Both | Revised: **A** — User Profile button in header (currently a dead button) | "Not on the home page. User profile button? Lightning icon? What do you recommend?" | ❌ pending (see UX analysis below) |

## Round 2 — Navigation Placement & Visual Design

### User Feedback Summary (Round 1)

1. **Scale correction**: 500K–750K puzzles, not 2K. This changes the SRS decision — with that volume, a proper retry/interval system is justified.
2. **No home page placement**: Stats should NOT be on the home grid.
3. **Needs to see screens**: User wants concrete visual wireframes before committing.
4. **Needs UX recommendation**: Where exactly does this live in navigation?
5. **User preferences concern**: Some features need proper user preference storage — localStorage may not be enough.

### UX Analysis: Where Should This Page Live?

Current app header (every page, always visible):

```
┌─────────────────────────────────────────────────────────┐
│ [YenGo Logo]              [🔥 7] [⚙] [👤]              │
│                           streak  gear profile           │
└─────────────────────────────────────────────────────────┘
```

The **UserProfile button** (👤) in the top-right corner currently does **nothing** — it's a dead `<button>` with no click handler. This is the natural entry point.

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q8 | **Entry point: Profile button (👤) → My Progress page?** | A) Yes — tap the profile silhouette → navigates to `/progress` / B) No — use a different icon/position / C) Add a `TrendUpIcon` (📈) NEXT to the profile button as a separate stats entry | **A** — The profile silhouette is universally understood as "my stuff." Every major app (Duolingo, Chess.com, Lichess) uses the profile icon to reach stats/progress. It's already in the header on every page. Zero new UI chrome needed. | | ❌ pending |
| Q9 | **Should the progress page have sub-tabs/sections, or be a single scrollable page?** | A) Single scrollable page with card sections / B) Tabbed page (Overview / Techniques / Achievements) / C) Accordion sections | **A** — Single scroll. Tabs add complexity and hide information. The DailySummary pattern already works well as stacked cards. Mobile-first scrolling is natural. | | ❌ pending |
| Q10 | **At 750K puzzles, should we use Leitner 3-box for retry scheduling instead of a simple queue?** | A) Yes — Leitner 3-box (new/learning/mastered) / B) Still simple retry queue / C) Defer SRS to a future initiative | **A** — With 750K puzzles, there's enough volume to benefit from spaced intervals. Leitner 3-box is trivial to implement (3 arrays in localStorage, box promotion on correct, demotion on wrong). | | ❌ pending |

---

## Wireframe: My Progress Page (Mobile-First)

Entry: User taps **👤 profile button** in header → navigates to `/progress`

### Screen 1: Progress Overview (top of scroll)

```
┌─────────────────────────────────────────────────────────┐
│ [←]  My Progress                            [⚙] [👤●]  │  ← PageHeader with back arrow
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │        ◉ Current Rank: Upper-Intermediate       │    │  ← Rank badge (from estimateUserLevel)
│  │    ████████████████████░░░░░  68% to Advanced   │    │  ← Progress bar to next rank
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  1,247   │ │   82%    │ │  🔥 14   │ │  3m 12s  │   │  ← 4-stat row (like DailySummary)
│  │ Solved   │ │ Accuracy │ │ Streak   │ │ Avg Time │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                         │
```

### Screen 2: Technique Radar (middle of scroll)

```
│  ┌─────────────────────────────────────────────────┐    │
│  │  Technique Accuracy                             │    │
│  │  ─────────────────────────────────              │    │
│  │                                                 │    │
│  │  Life & Death  ██████████████████░░  92%  ↑3%  │    │  ← Horizontal bar chart
│  │  Ladder        █████████████████░░░  85%  ↑1%  │    │  ← Sorted by accuracy
│  │  Tesuji        ████████████████░░░░  78%  ─    │    │  ← Trend arrows (vs last 30 days)
│  │  Ko            ██████████░░░░░░░░░░  52%  ↓5%  │    │  ← RED = weakest technique
│  │  Net           ████████░░░░░░░░░░░░  43%  ↑2%  │    │
│  │  Snapback      ██████░░░░░░░░░░░░░░  31%  new  │    │
│  │                                                 │    │
│  │  💡 "Your ko accuracy dropped 5% this month.   │    │  ← Smart insight callout
│  │     Try 10 ko puzzles to rebuild your skills."  │    │
│  │  [Practice Ko Now →]                            │    │  ← CTA → navigates to /technique/ko
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
```

### Screen 3: Difficulty Progression (continues scrolling)

```
│  ┌─────────────────────────────────────────────────┐    │
│  │  Accuracy by Difficulty                         │    │
│  │  ─────────────────────────────────              │    │
│  │                                                 │    │
│  │  100%│                                          │    │
│  │      │  ██                                      │    │  ← Bar chart by difficulty level
│  │   80%│  ██  ██                                  │    │
│  │      │  ██  ██  ██                              │    │
│  │   60%│  ██  ██  ██  ██                          │    │
│  │      │  ██  ██  ██  ██  ██                      │    │
│  │   40%│  ██  ██  ██  ██  ██  ██                  │    │
│  │      │  ██  ██  ██  ██  ██  ██  ░░              │    │
│  │   20%│  ██  ██  ██  ██  ██  ██  ░░  ░░          │    │
│  │      └──NOV─BEG─ELE─INT─UPP─ADV─LDN─HDN────── │    │
│  │                                                 │    │
│  │  ✓ Strong at: Elementary, Intermediate          │    │
│  │  ⚡ Challenge: Try Advanced level next           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
```

### Screen 4: Activity Heatmap & Achievements (bottom of scroll)

```
│  ┌─────────────────────────────────────────────────┐    │
│  │  Activity (Last 90 Days)                        │    │
│  │  ─────────────────────────────────              │    │
│  │                                                 │    │
│  │  Mon  ░░▓▓░░▓▓██▓▓░░▓▓░░██▓▓▓▓██░░██▓▓░░▓▓██ │    │  ← GitHub-style heatmap
│  │  Wed  ▓▓██▓▓▓▓░░██▓▓░░██░░▓▓██░░▓▓░░██▓▓░░▓▓ │    │     ░=0  ▓=1-5  █=5+
│  │  Fri  ██▓▓██░░▓▓░░██▓▓██▓▓░░▓▓██░░██▓▓██▓▓░░ │    │
│  │  Sun  ░░▓▓░░▓▓██▓▓░░▓▓░░██▓▓██░░▓▓░░██▓▓██▓▓ │    │
│  │                                                 │    │
│  │  Best streak: 14 days  |  Total days: 47        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Achievements  (8 / 22 unlocked)                │    │
│  │  ─────────────────────────────────              │    │
│  │                                                 │    │
│  │  🥉 First Steps       ✓    🥈 Perfect Ten    ✓  │    │  ← Grid of achievement badges
│  │  🥈 Fifty Puzzles     ✓    🥇 Streak 30     ✓  │    │     Locked ones shown dimmed
│  │  🥉 Rush Beginner     ✓    ░░ Rush 50       ░  │    │
│  │  🥈 No Hints Master   ✓    ░░ Thousand      ░  │    │
│  │  🥇 Speed Demon       ✓    ░░ Streak 365    ░  │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  [🔄 Smart Practice]                            │    │  ← Primary CTA at bottom
│  │  "12 ko puzzles + 8 net puzzles queued          │    │  ← Based on weak techniques
│  │   from your retry queue"                        │    │
│  │  [Start Session →]                              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Smart Practice Flow (when user taps "Start Session")

```
┌─────────────────────────────────────────────────────────┐
│ [←]  Smart Practice                    12 remaining     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Focus: Ko (weakest technique)                  │    │  ← Technique being trained
│  │  Progress: ████████░░░░░  4/12                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │                                                 │    │
│  │              ┌─────────────────┐                │    │
│  │              │                 │                │    │
│  │              │    Go Board     │                │    │  ← Standard PuzzleView
│  │              │   (19x19)       │                │    │
│  │              │                 │                │    │
│  │              └─────────────────┘                │    │
│  │                                                 │    │
│  │         [Hint]  [Skip]  [Solution]              │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Post-Session Summary (reuses DailySummary card pattern)

```
┌─────────────────────────────────────────────────────────┐
│ [←]  Session Complete                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │            🏆 Smart Practice Complete            │    │
│  │                                                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │    │
│  │  │    75%   │  │   12    │  │  2m 45s  │      │    │
│  │  │ Accuracy │  │ Puzzles │  │ Avg Time │      │    │
│  │  └──────────┘  └──────────┘  └──────────┘      │    │
│  │                                                 │    │
│  │  Ko accuracy: 52% → 58% (+6%)                   │    │  ← Shows improvement
│  │  3 puzzles moved to retry queue                 │    │
│  │                                                 │    │
│  │  [Back to Progress]  [Practice More →]          │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Round 2 — Remaining Clarifications

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q8 | **Entry point: Profile button (👤) → My Progress page?** The profile button in the header is currently a dead button with no functionality. Should tapping it navigate to `/progress`? | A) Yes — profile button → `/progress` / B) Use TrendUpIcon (📈) instead / C) Use LightningIcon (⚡) instead / D) Other | **A** — Profile silhouette is the universal "my stuff" pattern. Duolingo, Chess.com, Lichess all use it. Already visible on every page. | A — "profile button is fine" | ✅ resolved |
| Q9 | **Single scrollable page vs tabbed?** | A) Single scroll (as wireframed above) / B) Tabs: Overview / Techniques / Achievements / C) Other | **A** — Scroll is simpler, shows everything at once, mobile-native | A — "if it is all in one single page it is easy to throw away the code. Then we can go to tabbed if necessary." | ✅ resolved |
| Q10 | **At 750K puzzles, Leitner 3-box or simple retry queue?** | A) Leitner 3-box (new → learning → mastered) / B) Simple retry queue (FIFO) / C) Defer SRS entirely | Revised to **B** per user feedback | B — "There's never going to be somebody trying 750K puzzles. They try some modules, go back, iterate, loop back." Simple per-module retry is more realistic than global SRS. | ✅ resolved |
| Q11 | **User preference storage concern — what specifically needs DB storage?** All progress data is currently in localStorage (Holy Law #3). What user preferences did you have in mind that need a database? This would mean breaking the Zero Backend constraint. | A) Keep everything in localStorage (current architecture) / B) Add optional cloud sync later (separate initiative) / C) Other — please specify what needs DB | **A** — For this initiative, localStorage is sufficient. Cloud sync is a separate initiative that requires auth infrastructure. | A — "We can use the preferences, should not be a problem." | ✅ resolved |
| Q12 | **Do the wireframes above match what you envision?** Review each section: (1) Rank + 4-stat summary, (2) Technique radar bars, (3) Difficulty bar chart, (4) Activity heatmap, (5) Achievement badges, (6) Smart Practice CTA | A) Yes, build this / B) Mostly — with changes (specify) / C) Too complex — simplify / D) Missing something | A | Accepted via scrollable layout choice. Wireframes are ASCII art in this document (Screens 1-4 + Smart Practice flow). | ✅ resolved |

## Critical Design Constraint (from user, Round 2)

> **MODULARITY / REMOVABILITY**: The entire feature MUST be designed so it can be cleanly decommissioned. Clean interfaces, modular boundaries, easy to discard. Every file, route, service, and component for this feature should be isolated so the feature can be removed by deleting a known set of files and reverting a small number of integration points.

### Removability Contract

To decommission this feature, an engineer should be able to:
1. Delete the `pages/ProgressPage.tsx` file
2. Delete the `components/Progress/` directory
3. Delete the `services/progressAnalytics.ts` service
4. Delete the `services/retryQueue.ts` service
5. Delete the `services/achievementEngine.ts` service
6. Remove the `/progress` route from `routes.ts` (1 line)
7. Remove the `onClick` handler from `UserProfile.tsx` (1 line)
8. Remove the route case from `app.tsx` (1 block)

No other files should need changes. No shared utilities should depend on this feature.
