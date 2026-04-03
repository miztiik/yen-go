# Go Tips System

> **See also**:
>
> - [Architecture: UI Layout](../architecture/frontend/ui-layout.md) — Boot sequence, GoTipDisplay
> - [How-To: SolverView](../how-to/frontend/solver-view.md) — Component usage
> - [Concepts: Levels](./levels.md) — 9-level difficulty system

**Last Updated**: 2026-02-09

**Single Source of Truth**: [`config/go-tips.json`](../../config/go-tips.json)

---

## Tone Guidelines: The Sensei Persona

Content should be written with the poise and groundedness of a Go teacher ($Sensei$).

- **Poise & Poignancy**: Avoid "cheerful" or contemporary filler adjectives.
- **Action-Oriented**: Use strong verbs and direct guidance.
- **Technical Accuracy**: Prefer exact Go terminology (e.g., $Hoshi$ instead of "Star point").
- **Simplicity**: Statements should be simple yet profound, speaking with authority.

---

## GoTipsConfig Schema

```json
{
  "version": "1.1",
  "tips": [
    {
      "text": "Liberty (Dame): The breath of a stone. Without it, the stone perishes.",
      "category": "definition",
      "levels": ["novice", "beginner"]
    }
  ]
}
```

### GoTip Structure

| Field      | Type                                 | Required | Description                                                     |
| ---------- | ------------------------------------ | -------- | --------------------------------------------------------------- |
| `text`     | `string`                             | Yes      | The tip text displayed to the user                              |
| `category` | `"tip" \| "proverb" \| "definition"` | Yes      | Content category. Sorted in file as: Definition → Tip → Proverb |
| `levels`   | `string[]`                           | Yes      | Applicable difficulty levels (slugs from `puzzle-levels.json`)  |

---

## Category Taxonomy

### Definitions (~30%)

Technical terms and core concepts. Replaces vague English with technical Go vocabulary.

**Examples**:

- "Liberty (Dame): The breath of a stone. Without it, the stone perishes."
- "Sente: The power of initiative. Force the opponent to respond to your lead."
- "Aji: Lingering potential. A hidden weakness waiting to be exploited."

### Tips (~50%)

Practical advice for puzzle solving and strategic play. Poised, teacher-like guidance.

**Examples**:

- "Count the liberties before you commit to the fight."
- "Strike at the vital point to collapse the opponent's shape."
- "Strengthen your own groups before invading the opponent’s."

### Proverbs (~20%)

Traditional Go wisdom. Keep the language grounded and focus on tactical truths.

**Examples**:

- "The enemy's vital point is your vital point."
- "Play away from thickness."
- "Strange occurrences happen at the 1-2 point."

---

## Level Coverage

Tips are tagged with applicable difficulty levels. A tip can span multiple levels:

| Level              | Slug                 | Typical Tip Focus              |
| ------------------ | -------------------- | ------------------------------ |
| Novice             | `novice`             | Basic rules, eyes, territory   |
| Beginner           | `beginner`           | Capturing, patterns, shape     |
| Elementary         | `elementary`         | Tactics, reading 3+ moves      |
| Intermediate       | `intermediate`       | Strategy, whole-board thinking |
| Upper-Intermediate | `upper-intermediate` | Positional judgment, ko        |
| Advanced           | `advanced`           | Complex fighting, influence    |
| Low Dan            | `low-dan`            | Timing, aji utilization        |
| High Dan           | `high-dan`           | Endgame precision, probing     |
| Expert             | `expert`             | Professional-level insight     |

---

## Frontend Integration

### Boot Loading

```tsx
// In GoTipDisplay component:
import { getBootConfigs } from "../boot";

const configs = getBootConfigs();
const tips = configs?.tips ?? [];
const randomTip = tips[Math.floor(Math.random() * tips.length)];
```

### TypeScript Types

```typescript
// Defined in config-loader.ts
interface GoTip {
  text: string;
  category: "tip" | "proverb" | "definition";
  levels: string[];
}

interface GoTipsConfig {
  version: string;
  tips: GoTip[];
}
```

---

## Contribution Guide

### Adding Tips

1. Edit `config/go-tips.json`
2. Add a new entry to the `tips` array:
   ```json
   {
     "text": "Your new tip text here",
     "category": "tip",
     "levels": ["beginner", "elementary"]
   }
   ```
3. Follow these rules:
   - Text should be concise (one sentence preferred)
   - Choose the most specific category
   - Tag with ALL applicable levels (not just one)
   - Don't duplicate existing tips (search first)
   - Use em-dash (—) for inline definitions

### Category Selection Guide

| If the content...            | Category     |
| ---------------------------- | ------------ |
| Gives actionable advice      | `tip`        |
| Is traditional wisdom/saying | `proverb`    |
| Defines a Go term            | `definition` |

### Quality Checklist

- [ ] Tip is accurate (verified Go knowledge)
- [ ] Category is correct
- [ ] Levels are appropriate (not too broad or too narrow)
- [ ] No duplicates in the file
- [ ] Text is concise and clear
