# Research: Frontend Navigation & UX Placement for "My Progress / Stats" Page

**Last Updated**: 2026-03-18  
**Research Question**: What is the exact current navigation structure, routing, page layout, and icon system in the YenGo frontend, and where should a new "My Progress / Stats" page be placed?  
**Boundaries**: Frontend code only (`frontend/src/`). No backend / pipeline code in scope.

---

## 1. Internal Code Evidence

### 1A. Routing — Complete Route Table

**Source**: `frontend/src/lib/routing/routes.ts`

The app uses a custom hash/history-based SPA router (no React Router). All routes are defined as a discriminated union type `Route` and parsed in `parseRoute()`.

| R-ID | Route Type | URL Path | Component | Description |
|------|-----------|----------|-----------|-------------|
| R-1 | `home` | `/` | `HomePageGrid` | Landing page with 6-tile grid |
| R-2 | `context` (collection) | `/contexts/collection/{slug}` or `/collection/{slug}` | `CollectionViewPage` | Puzzle set player for a collection |
| R-3 | `context` (technique) | `/contexts/technique/{slug}` or `/technique/{slug}` | `TechniqueViewPage` | Puzzle set player for a technique tag |
| R-4 | `context` (training) | `/contexts/training/{slug}` or `/training/{slug}` | `TrainingViewPage` | Puzzle set player for a difficulty level |
| R-5 | `context` (quality) | `/contexts/quality/{slug}` | Falls back to `HomePageGrid` | Future: quality browsing (not implemented) |
| R-6 | `modes-daily` | `/modes/daily` | `DailyBrowsePage` | Daily challenge mode selection / calendar |
| R-7 | `modes-daily-date` | `/modes/daily/{YYYY-MM-DD}` | `DailyChallengePage` | Specific daily challenge puzzle solving |
| R-8 | `modes-rush` | `/modes/rush` | `RushBrowsePage` → `PuzzleRushPage` | Puzzle Rush setup + gameplay |
| R-9 | `modes-random` | `/modes/random` | `RandomPage` → `RandomChallengePage` | Random puzzle selection + solving |
| R-10 | `collections-browse` | `/collections` | `CollectionsBrowsePage` | Browse all collections |
| R-11 | `technique-browse` | `/technique` | `TechniqueBrowsePage` | Browse technique categories |
| R-12 | `training-browse` | `/training` | `TrainingBrowsePage` | Browse training levels |
| R-13 | `learning-browse` | `/learn` | `LearningPage` | Learn Go topics |

**Key finding**: There is NO existing `/progress` or `/stats` route. The Route union type would need a new member.

### 1B. Global App Shell Structure

**Source**: `frontend/src/App.tsx` (lines 710–718)

```tsx
<div className="flex min-h-screen flex-col bg-[var(--color-bg-primary)]">
  <AppHeader streak={streak} compact={isPuzzlePlayerRoute} />
  <div class="route-fade-in" key={route.type}>
    {renderRouteContent()}
  </div>
</div>
```

**Structure**:
- **AppHeader** — Always visible on every page (56px height, 44px compact)
- **Route content** — Renders below header, fills remaining viewport
- Compact header mode activates on `context` routes, `modes-daily-date`, and `modes-rush` (puzzle-solving pages: icon-only logo, smaller height)
- No bottom tab bar, no sidebar navigation, no hamburger menu

### 1C. AppHeader Layout

**Source**: `frontend/src/components/Layout/AppHeader.tsx`

```
[YenGo Logo / Link Home]  ---- spacer ----  [StreakBadge?] [SettingsGear] [UserProfile]
```

| Position | Element | Behavior |
|----------|---------|----------|
| Left | `YenGoLogoWithText` (full) or `YenGoLogo` (compact) | Links home via `pushState` |
| Right | `StreakBadge` | Only shows when streak > 0 |
| Right | `SettingsGear` | Gear icon → dropdown (dark mode, sound, coords toggles) |
| Right | `UserProfile` | User silhouette icon → no action currently (just a button, no dropdown) |

**Key finding**: The `UserProfile` button in the top-right currently does **nothing**. It's a placeholder avatar button with no click handler. This is a natural entry point for a "My Progress" page.

### 1D. Home Page Grid Layout

**Source**: `frontend/src/pages/HomePageGrid.tsx`

The home page renders a `PageLayout variant="single-column"` with a hero section and 6 tiles in a `HomeGrid`:

| Position | Tile Variant | Title | Icon | Stat / Progress |
|----------|-------------|-------|------|-----------------|
| 1 | `daily` | Daily Challenge | `CalendarIcon` (amber) | Streak display, X/Y solved progress bar |
| 2 | `rush` | Puzzle Rush | `LightningIcon` (rose) | Best score display |
| 3 | `collections` | Collections | `BookIcon` (purple) | Collection count, technique tags |
| 4 | `training` | Training | `GraduationCapIcon` (blue) | Current level, progress % |
| 5 | `technique` | Technique | Custom target SVG (emerald) | Technique tags |
| 6 | `learning` | Learn Go | `SeedlingIcon` (teal) | Topic tags |

The grid is responsive: 1 col mobile → 2 col tablet (640px) → 3 col desktop (1024px).

### 1E. PageLayout System

**Source**: `frontend/src/components/Layout/PageLayout.tsx`

Two variants:
- `puzzle` — 2-column (board + sidebar), used by puzzle-solving pages
- `single-column` — Full-width content, used by browse pages and home

Browse pages use `PageLayout variant="single-column"` + `PageHeader` (shared component with back button, icon circle, title, subtitle, stat badges).

### 1F. Page Pattern for Browse Pages

**Source**: `TechniqueBrowsePage.tsx`, `TrainingBrowsePage.tsx`, etc.

Every browse page follows:
1. `PageLayout variant="single-column"` wrapper
2. `PageHeader` component (accent-tinted bg, icon, title, subtitle, back button, stat badges)
3. Content area (cards, grids, filters)

Back navigation: Each browse page has an `onNavigateHome` or `onNavigateBack` callback that navigates to `{ type: 'home' }`.

### 1G. Complete Icon Inventory

**Source**: `frontend/src/components/shared/icons/`

| I-ID | Icon | File | Usage Context |
|------|------|------|--------------|
| I-1 | `BookIcon` | BookIcon.tsx | Collections tile |
| I-2 | `CalendarIcon` | CalendarIcon.tsx | Daily challenge tile |
| I-3 | `CheckIcon` | CheckIcon.tsx | Completion indicator |
| I-4 | `ChevronDownIcon` | ChevronDownIcon.tsx | Dropdowns |
| I-5 | `ChevronLeftIcon` | ChevronLeftIcon.tsx | Back navigation |
| I-6 | `ChevronRightIcon` | ChevronRightIcon.tsx | Forward navigation |
| I-7 | `CollectionIcon` | CollectionIcon.tsx | Collection references |
| I-8 | `CoordsIcon` | CoordsIcon.tsx | Board coordinate toggle |
| I-9 | `DiceIcon` | DiceIcon.tsx | Random mode tile |
| I-10 | `DoubleChevronLeftIcon` | DoubleChevronLeftIcon.tsx | Jump navigation |
| I-11 | `DoubleChevronRightIcon` | DoubleChevronRightIcon.tsx | Jump navigation |
| I-12 | `FlipDiagIcon` | FlipDiagIcon.tsx | Board transform |
| I-13 | `FlipHIcon` | FlipHIcon.tsx | Board transform |
| I-14 | `FlipVIcon` | FlipVIcon.tsx | Board transform |
| I-15 | `GraduationCapIcon` | GraduationCapIcon.tsx | Training tile |
| I-16 | `GridIcon` | GridIcon.tsx | Grid view toggle |
| I-17 | `HeartIcon` | HeartIcon.tsx | Favorite |
| I-18 | `HintIcon` | HintIcon.tsx | Hint action |
| I-19 | `LightningIcon` | LightningIcon.tsx | Rush mode tile (rose/pink) |
| I-20 | `ListIcon` | ListIcon.tsx | List view toggle |
| I-21 | `ObjectiveFlagIcon` | ObjectiveFlagIcon.tsx | Objective category |
| I-22 | `RandomizeIcon` | RandomizeIcon.tsx | Randomize action |
| I-23 | `ResetIcon` | ResetIcon.tsx | Reset action |
| I-24 | `ReviewIcon` | ReviewIcon.tsx | Review solution |
| I-25 | `RotateCCWIcon` | RotateCCWIcon.tsx | Board rotate |
| I-26 | `RotateCWIcon` | RotateCWIcon.tsx | Board rotate |
| I-27 | `SearchIcon` | SearchIcon.tsx | Search |
| I-28 | `SeedlingIcon` | SeedlingIcon.tsx | Learn Go tile |
| I-29 | `SkipIcon` | SkipIcon.tsx | Skip puzzle |
| I-30 | `SolutionIcon` | SolutionIcon.tsx | View solution |
| I-31 | `StarIcon` | StarIcon.tsx | Quality rating (outline + filled) |
| I-32 | `StreakIcon` | StreakIcon.tsx | Streak display |
| I-33 | `SwapColorsIcon` | SwapColorsIcon.tsx | Board colors |
| I-34 | `TechniqueKeyIcon` | TechniqueKeyIcon.tsx | Technique category |
| I-35 | `TesujiIcon` | TesujiIcon.tsx | Tesuji category |
| I-36 | `TrendUpIcon` | TrendUpIcon.tsx | Improvement/stats encouragement |
| I-37 | `TrophyIcon` | TrophyIcon.tsx | Level/challenge completion |
| I-38 | `UndoIcon` | UndoIcon.tsx | Undo action |
| I-39 | `ZoomIcon` | ZoomIcon.tsx | Zoom action |

**Key finding**: `TrendUpIcon` (📈 chart-up), `TrophyIcon` (🏆), and `StarIcon` (⭐) already exist and are natural choices for a Stats/Progress page. There is NO dedicated "bar chart", "pie chart", or "user stats" icon — a new one would need to be created OR `TrendUpIcon` can be reused.

### 1H. CSS Framework & Mobile-First Approach

**Source**: `frontend/src/styles/app.css`, `frontend/index.html`

- **CSS**: Tailwind CSS v4 with `@theme` design tokens. Custom CSS properties (`--color-*`, `--color-mode-*`) for theming.
- **Mobile-first**: Yes. The `<meta name="viewport">` sets `width=device-width, initial-scale=1.0`. Grid breakpoints are mobile-first (1 col default → 2 col at 640px → 3 col at 1024px).
- **PWA**: `apple-mobile-web-app-capable` enabled. App designed for touch-first mobile experience.
- **Dark mode**: Supported via CSS media query + user toggle in SettingsGear.

### 1I. Progress Data Already Available (localStorage)

**Source**: `frontend/src/services/progress/` module

The progress system already tracks:
- `recordPuzzleCompletion` / `isPuzzleCompleted` / `getPuzzleCompletion` — per-puzzle solve history
- `getStatistics()` — aggregated stats (rush high scores, etc.)
- `getStreakData()` / `updateStreakData()` — streak tracking
- `getAchievements()` — achievement system
- `getRushHighScore()` / `getRushHighScoreByDuration()` — rush scores
- `loadCollectionProgress()` — per-collection progress
- `loadDailyProgress()` — daily challenge history
- `exportProgress()` / `importProgress()` — full export/import

### 1J. PuzzleSetPlayer & Session Tracking

**Source**: `frontend/src/components/PuzzleSetPlayer/index.tsx`

PuzzleSetPlayer tracks per-session:
- `completedIndexes: Set<number>` — puzzles solved in current session
- `failedIndexes: Set<number>` — puzzles answered incorrectly
- `initialCompletedIds` — pre-completed IDs from localStorage (cross-session persistence)
- `onPuzzleComplete(puzzleId, isCorrect)` callback — fires on each puzzle terminal state

The `renderSummary` prop allows custom summary views (used by `DailySummary`).

### 1K. DailySummary Component

**Source**: `frontend/src/components/DailyChallenge/DailySummary.tsx`

Post-session feedback UI that shows:
- Overall accuracy percentage
- Accuracy by skill level
- Time taken
- Trophy/Star/TrendUp icon based on accuracy
- "Play Again" and "Go Home" buttons

This is the only existing post-session summary component. Collections and training have no equivalent summary screen.

---

## 2. External References

| E-ID | Reference | Relevance |
|------|-----------|-----------|
| E-1 | Chess.com mobile app "Stats" tab | Bottom tab bar with dedicated Stats icon — shows solve rate by theme, rating graph, streak history. Yen-Go is similar puzzle-drill app but lacks bottom nav. |
| E-2 | Lichess Puzzle dashboard (`/training/dashboard`) | Top-level nav link to full-page stats dashboard with solve history, accuracy by theme, progress graphs. Uses dedicated route path (`/training/dashboard`). |
| E-3 | Duolingo profile/stats page | Profile avatar tap → full stats page with streak, XP, leaderboard, achievements. Very similar to Yen-Go's `UserProfile` button which currently does nothing. |
| E-4 | Apple HIG "Tab Bars" guidelines | Recommends max 5 tabs for mobile. Yen-Go has no tab bar; adding one solely for stats would be over-engineered. Better: leverage existing header entry point. |

---

## 3. Candidate Adaptations for Yen-Go

### Option A: UserProfile Button → Progress Page

**Mechanism**: Make the existing `UserProfile` avatar button in `AppHeader` navigate to `/progress`.

- **Pros**: Zero new navigation chrome. Leverages existing UI real estate. Follows Duolingo pattern (E-3). The button already exists and does nothing.
- **Cons**: Users may not discover it without onboarding. Avatar icon doesn't obviously convey "stats".
- **Effort**: Low. Add route type to union, add page component, wire click handler in `UserProfile`.

### Option B: New Home Page Tile (7th Tile)

**Mechanism**: Add a 7th "My Progress" tile to the HomePageGrid.

- **Pros**: Highly discoverable. Consistent with existing navigation pattern. Shows stats preview on tile itself.
- **Cons**: 7 tiles creates uneven grid (3-col desktop: 3+3+1). May feel cluttered. Breaks current balanced 2×3 grid.
- **Effort**: Low-medium. Add tile variant, route, page component.

### Option C: UserProfile Button + Home Page Tile (Hybrid)

**Mechanism**: Both Option A and B. Profile button always available (quick access), home tile provides discoverability.

- **Pros**: Best discoverability. Two entry points match the importance of progress tracking.
- **Cons**: 7th tile grid imbalance still applies. Slightly more implementation effort.
- **Effort**: Medium. Sum of A + B.

### Option D: Expandable Header Streak → Stats Drawer

**Mechanism**: Make the existing `StreakBadge` in AppHeader clickable → opens a slide-down stats drawer/panel (not a full page).

- **Pros**: Contextual. No new route needed. Quick glance at stats without leaving current page.
- **Cons**: Limited real estate in a drawer. Can't show full history/charts. Not persistent (no URL, not bookmarkable). Only visible when streak > 0.
- **Effort**: Medium. New drawer component, animation, touch gestures.

---

## 4. Risks, License/Compliance Notes, and Rejection Reasons

| Risk | Severity | Mitigation |
|------|----------|------------|
| 7th tile grid imbalance (Option B/C) | Low | Can solve with CSS: span the 7th tile 2 columns on desktop, or reorganize to 4+4 at a "2×4" layout |
| `UserProfile` button not discoverable (Option A) | Medium | Add subtle tooltip/badge; can combine with Option B for dual entry |
| Stats page needs no runtime backend | N/A | All data comes from localStorage — fully compliant with Holy Law #1 (Zero Runtime Backend) and #3 (Local-First) |
| No "bar chart" icon exists | Low | Reuse `TrendUpIcon` or create a minimal new icon (< 30 lines SVG) |
| Additional route increases bundle | Negligible | Single new page component, code-split naturally by route rendering |

**Rejection reasons for other approaches**:
- **Bottom tab bar**: Over-engineered for a single new page. Would require major layout refactoring across all pages. Not recommended.
- **Sidebar drawer**: No existing sidebar infrastructure. Would be a Level 4 structural change.
- **Settings panel integration**: SettingsGear dropdown is too small for meaningful stats display.

---

## 5. Planner Recommendations

1. **Recommended: Option C (Hybrid — UserProfile + Home Tile)**  
   Wire the existing `UserProfile` avatar button to navigate to `/progress` AND add a 7th "My Progress" home tile with `TrendUpIcon`. This provides both discoverability (tile) and always-available quick access (header). The 7th tile grid issue is solvable with a 2-column span or placing it as a prominent top banner instead.

2. **Quick Win Alternative: Option A (UserProfile → /progress only)**  
   Minimum viable approach. The `UserProfile` button currently does nothing — repurposing it to open a progress page is the smallest change with immediate value. Defer tile addition to a follow-up iteration.

3. **Route path**: Use `/progress` with route type `progress-dashboard`. Follows existing pattern (nouns for browse pages: `/collections`, `/training`, `/technique`).

4. **Page pattern**: Use `PageLayout variant="single-column"` + `PageHeader` with `TrendUpIcon` or `TrophyIcon`, consistent with all other browse pages. Back button → home.

---

## 6. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |

**Rationale**: All internal code evidence is from direct file reads. The routing system, header layout, and progress APIs are well-understood. The main uncertainty is UX preference (tile vs header vs both), which is a design decision, not a technical risk.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should the 7th home tile span 2 columns on desktop, or should we reorganize the grid to 4+4? | A: Span 2 cols / B: Reorganize grid / C: Skip tile, use header only | C (start with header only, add tile later) | | ❌ pending |
| Q2 | Should `UserProfile` button gain a visual indicator (badge/dot) when there are new achievements? | A: Yes, subtle dot / B: No, keep clean / C: Defer to later | B | | ❌ pending |
| Q3 | What stats should appear on the progress page? (Streak history, accuracy by level, solve count, rush scores, daily completion calendar, collection progress) | A: All / B: Core only (streak + accuracy + solve count) / C: User decides scope | A | | ❌ pending |
