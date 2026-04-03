# Mastery System (Frontend)

> **See also**:
>
> - [Concepts: Levels](./levels.md) — Difficulty level system
> - [Concepts: Quality](./quality.md) — Puzzle quality metrics
> - [Source Code: lib/mastery.ts](../../frontend/src/lib/mastery.ts) — Implementation

**Last Updated**: 2026-02-24

**Single Source of Truth**: [`frontend/src/lib/mastery.ts`](../../frontend/src/lib/mastery.ts)

YenGo uses an **accuracy-based mastery system** to track user skill progression across Training, Collections, and Technique pages.

---

## Key Principle: Skill Over Completion

Mastery is based on **accuracy** (how well you solve puzzles), not just **completion** (how many you've seen).

```
accuracy = (correct / attempted) × 100
```

This ensures users who rush through puzzles incorrectly don't appear "mastered" while users who solve fewer puzzles perfectly get appropriate credit.

---

## Mastery Levels

| Level | Slug         | Display Label | Criteria                         |
| ----- | ------------ | ------------- | -------------------------------- |
| 1     | `new`        | Begin         | 0 attempts                       |
| 2     | `started`    | Continue      | 1-4 attempts (insufficient data) |
| 3     | `learning`   | Learning      | <50% accuracy                    |
| 4     | `practiced`  | Practiced     | 50-69% accuracy                  |
| 5     | `proficient` | Proficient    | 70-84% accuracy                  |
| 6     | `mastered`   | Mastered      | ≥85% accuracy + volume threshold |

---

## Thresholds

### Accuracy Thresholds

```typescript
MASTERY_THRESHOLDS = {
  learning: 50, // <50% = struggling
  practiced: 70, // 50-69% = getting better
  proficient: 85, // 70-84% = good
  mastered: 85, // ≥85% + volume = mastered
};
```

### Volume Thresholds

Volume thresholds prevent mastery claims from small samples:

```typescript
VOLUME_THRESHOLDS = {
  minForJudgment: 5, // Need ≥5 attempts to judge skill
  minForMastery: 10, // Need ≥10 for mastery (or 50% of total)
};
```

**Mastery volume rule**: `min(10, ceil(total × 0.5))`

- If 20 puzzles available → need ≥10 solved
- If 6 puzzles available → need ≥3 solved (50%)
- If 100 puzzles available → need ≥10 solved (capped)

---

## Algorithm

```
getMasteryFromAccuracy(accuracy, attempted, total):
  if attempted == 0         → 'new'
  if attempted < 5          → 'started'
  if accuracy < 50%         → 'learning'
  if accuracy < 70%         → 'practiced'
  if accuracy < 85%         → 'proficient'
  if attempted < minForMastery → 'proficient'
  else                      → 'mastered'
```

---

## API Reference

### `getMasteryFromAccuracy(accuracy, attempted, total)`

Core algorithm. Use when you have raw accuracy/attempted/total values.

```typescript
import { getMasteryFromAccuracy } from "@/lib/mastery";

const level = getMasteryFromAccuracy(
  82, // 82% accuracy
  15, // 15 puzzles attempted
  50, // 50 total puzzles
);
// Returns: 'proficient' (82% < 85% threshold)
```

### `getMasteryFromProgress(progress)`

Wrapper for progress objects. Primary interface for Training and Collections.

```typescript
import { getMasteryFromProgress } from "@/lib/mastery";

const level = getMasteryFromProgress({
  completed: 10,
  total: 50,
  accuracy: 90, // Optional, defaults to 100%
});
// Returns: 'mastered' (90% ≥ 85% and 10 ≥ minForMastery)
```

### `getMasteryFromPercent(pct, hasAnyProgress)` ⚠️ DEPRECATED

Legacy completion-based calculation. Use `getMasteryFromAccuracy` instead.

---

## Usage by Page

| Page            | Data Source                      | How Accuracy Is Computed             |
| --------------- | -------------------------------- | ------------------------------------ |
| **Training**    | `TrainingProgress.byLevel[slug]` | `levelProgress.accuracy` (stored)    |
| **Collections** | `CollectionProgressSummary`      | Default 100% (no accuracy field yet) |
| **Technique**   | `TechniqueStats`                 | `(correct / attempted) × 100`        |

### Training Example

```typescript
// TrainingSelectionPage.tsx
function getLocalMastery(level: SkillLevel): MasteryLevel {
  const levelProgress = progress.byLevel[level.slug];
  return getMasteryFromProgress({
    completed: levelProgress?.completed ?? 0,
    total: snapshotTotalForLevel,
    accuracy: levelProgress?.accuracy,
  });
}
```

### Technique Example

```typescript
// TechniqueCard.tsx
const accuracy =
  stats && stats.attempted > 0
    ? Math.round((stats.correct / stats.attempted) * 100)
    : 0;
const masteryLevel = getMasteryFromAccuracy(
  accuracy,
  stats?.attempted ?? 0,
  technique.puzzleCount,
);
```

---

## Visual Styling

Each mastery level has distinct styling via `getMasteryStyle()` in the consuming components:

| Level        | Background              | Text Color                  |
| ------------ | ----------------------- | --------------------------- |
| `new`        | var(--color-bg-soft)    | var(--color-text-secondary) |
| `started`    | Semi-transparent accent | var(--color-accent-text)    |
| `learning`   | Red tint                | Dark red                    |
| `practiced`  | Yellow tint             | Dark yellow                 |
| `proficient` | Green tint              | Dark green                  |
| `mastered`   | Accent gradient         | White                       |

---

## Design Decisions

### Why Accuracy-Based?

1. **Skill matters more than volume** — Solving 100 puzzles at 40% accuracy shouldn't outrank 20 at 90%
2. **Prevents rushing** — Users can't just click through to "complete" a level
3. **Meaningful feedback** — "Learning" vs "Mastered" tells users their actual skill level

### Why Volume Thresholds?

1. **Statistical significance** — 2 correct out of 2 (100%) shouldn't mean "mastered"
2. **Prevents gaming** — Can't cherry-pick easy puzzles to inflate mastery
3. **Fair comparison** — Mastery means "demonstrated competence over meaningful sample"

### Why 5/10 as Minimums?

- **5 minimum for judgment**: Enough attempts to distinguish skill from luck
- **10 minimum for mastery**: Standard "order of magnitude" for confidence
- **50% of total fallback**: For small pools (e.g., 6 ko puzzles), require half coverage

---

## Future Enhancements

- [ ] Add accuracy tracking to Collections (`CollectionProgressSummary.accuracy`)
- [ ] Decay mastery over time (spaced repetition)
- [ ] Per-technique accuracy in Training (currently aggregated by level)
