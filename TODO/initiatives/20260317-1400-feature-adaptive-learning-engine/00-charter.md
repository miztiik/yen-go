# Charter — Adaptive Learning Engine

> Last Updated: 2026-03-18
> Initiative: `20260317-1400-feature-adaptive-learning-engine`

## Goal

Transform YenGo from a puzzle-solving app into an intelligent learning platform by adding a **My Progress page** (accessed via the profile button), a **technique-aware analytics engine**, a **simple retry queue**, and **achievement activation** — all entirely client-side, fully modular, and safely removable.

## Goals

1. **G1 — Progress Visibility**: Users can see their total stats, accuracy by technique, accuracy by difficulty, activity heatmap, and streak history on a single scrollable page.
2. **G2 — Technique Weakness Detection**: The system identifies the user's weakest techniques by cross-referencing solve history (localStorage) with puzzle tag metadata (SQLite WASM), and recommends targeted practice.
3. **G3 — Smart Practice Mode**: A "Smart Practice" session auto-generates a puzzle set from the user's weakest techniques, using existing PuzzleSetPlayer infrastructure.
4. **G4 — Retry Queue**: Failed puzzles are persisted to localStorage and surface for re-attempt. Simple FIFO per-module (not global SRS). Users iterate within techniques/collections, not across the full 750K corpus.
5. **G5 — Achievement Activation**: Wire the 22 pre-defined achievements (already modeled in `achievement.ts`) to an evaluation service + toast notification system.
6. **G6 — Full Modularity**: The entire feature is removable by deleting a known set of files (≤8 files) and reverting ≤3 integration points. No shared utilities depend on this feature.

## Non-Goals

- **NG1**: No cloud sync, no user accounts, no backend API (Holy Law #1 and #3)
- **NG2**: No global SRS / Leitner system — retry is per-module, not cross-corpus
- **NG3**: No home page changes — entry is exclusively via the profile button in the header
- **NG4**: No new npm dependencies for charts — SVG micro-charts only
- **NG5**: No modification of existing puzzle-solving pages (Daily, Rush, Training, etc.) — this is additive only
- **NG6**: No PWA/push notification for achievements — toast in-app only

## Constraints

| ID | Constraint | Source |
|----|-----------|--------|
| C1 | Zero runtime backend | Holy Law #1 |
| C2 | All user data in localStorage | Holy Law #3 |
| C3 | TypeScript strict mode, no `any` | Holy Law #5 |
| C4 | No emojis in production UI — SVG icons only | Frontend Design Conventions |
| C5 | No new npm dependencies for visualization | User decision (Q6:A) |
| C6 | Feature must be fully decommissionable | User requirement (Round 2) |
| C7 | Profile button (👤) is the sole entry point | User decision (Q8:A) |
| C8 | Single scrollable page, no tabs | User decision (Q9:A) |
| C9 | Simple retry queue per module, not global SRS | User decision (Q10:B) |
| C10 | All wireframe emojis are conceptual placeholders — implementation MUST use SVG icons per C4. Plan must include SVG icon tasks for: rank badge, achievement tier badges (bronze/silver/gold/platinum), trend arrows, heatmap cells, smart practice CTA icon | Governance RC-4 |

## Acceptance Criteria

| AC | Description | Verification |
|----|------------|--------------|
| AC1 | Tapping the profile button navigates to `/progress` | Manual test + route unit test |
| AC2 | Progress page shows: rank, total solved, accuracy, streak, avg time | Vitest component test |
| AC3 | Technique accuracy bars are rendered from joined localStorage + SQLite data | Vitest service test |
| AC4 | Difficulty chart shows accuracy per skill level (9 levels) | Vitest component test |
| AC5 | Activity heatmap shows last 90 days of solve activity | Vitest component test |
| AC6 | Achievements section shows 22 achievements with unlock/lock state | Vitest component test |
| AC7 | Smart Practice generates a set from weakest techniques | Vitest service test |
| AC8 | Retry queue persists failed puzzle IDs to localStorage | Vitest service test |
| AC9 | Achievement toast appears on unlock | Vitest component test |
| AC10 | Removing 8 files + reverting 3 integration points fully decommissions the feature | Manual verification |
| AC11 | All existing tests continue to pass | CI regression |
| AC12 | No new npm dependencies added | `package.json` diff check |

## Scope Boundary

### Files Created (new, all removable)
- `frontend/src/pages/ProgressPage.tsx`
- `frontend/src/components/Progress/` (directory with section components)
- `frontend/src/services/progressAnalytics.ts`
- `frontend/src/services/retryQueue.ts`
- `frontend/src/services/achievementEngine.ts`
- `frontend/src/components/Progress/AchievementToast.tsx`

### Files Modified (minimal integration points)
- `frontend/src/lib/routing/routes.ts` — add `progress` route type (1 union member + parse/serialize)
- `frontend/src/app.tsx` — add route case + navigation handler (~10 lines)
- `frontend/src/components/Layout/UserProfile.tsx` — add onClick handler (1 prop + 1 line)

### Files NOT Modified
- No backend changes
- No config changes
- No existing page modifications
- No existing service modifications
- No test infrastructure changes
