# My Progress Page

**Last Updated**: 2026-03-19

The My Progress page shows your puzzle-solving analytics and helps you improve by targeting weak techniques.

## Accessing the Page

Click the **profile icon** (top-right corner of the header, next to the settings gear) to navigate to My Progress.

## Features

### Progress Overview

Shows your key stats at a glance:
- **Total Puzzles Solved** — cumulative count across all modes
- **Overall Accuracy** — percentage of puzzles solved correctly on first attempt
- **Current Streak** — consecutive days with at least one puzzle solved
- **Longest Streak** — your personal best streak record

### Technique Radar

Horizontal bars showing your accuracy per technique (Life & Death, Ladder, Ko, etc.):
- Green arrow = improving trend (last 30 days)
- Red arrow = declining trend
- "Low data" label when fewer than 10 puzzles attempted
- Smart insight recommends practice for your weakest technique

### Difficulty Chart

SVG bar chart showing accuracy by difficulty level (Novice through Expert).

### Activity Heatmap

91-day activity grid showing daily puzzle completion counts. Darker cells = more puzzles solved that day.

### Achievements

Badge tiles for 22 achievements across categories:
- Solve milestones (1, 10, 50, 100, 500, 1000)
- Perfect solve streaks
- Streak achievements
- Rush high scores
- Time milestones
- Hint discipline

New achievements trigger a toast notification that auto-dismisses after 5 seconds.

### Smart Practice

The CTA at the bottom identifies your weakest techniques and launches a targeted practice session:
1. Queries your worst 3 techniques by accuracy
2. Finds unsolved puzzles matching those techniques
3. Shuffles and presents up to 15 puzzles
4. Failed puzzles are added to a retry queue for future practice

## Data Sources

All data comes from existing localStorage progress records cross-referenced with the SQLite puzzle index (`yengo-search.db`). No new data collection, no network requests beyond initial DB load.

> **See also**:
>
> - [Architecture: Puzzle Modes](../../architecture/frontend/puzzle-modes.md) — Mode architecture overview
> - [How-To: Rush Mode](./rush-mode.md) — Similar feature guide pattern
> - [Concepts: SQLite Index](../../concepts/sqlite-index-architecture.md) — Database architecture
