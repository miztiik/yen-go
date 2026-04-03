# gogamev4.0 — Analysis Engine & Mistake Detector: Distilled Algorithms

**Source:** [zhoumeng-creater/gogamev4.0](https://github.com/zhoumeng-creater/gogamev4.0) `features/analysis.py`  
**License:** MIT  
**Relevance:** Move quality classification, weak group detection, suggestion engine

---

## Overview

gogamev4.0's analysis module provides:

1. **MistakeDetector** — classify move quality by winrate loss thresholds
2. **PositionAnalyzer** — find weak groups and assess escape/eye potential
3. **SuggestionEngine** — generate contextual move suggestions with reasons

For yen-go: the **classification thresholds** and **weak group detection**
are directly applicable to puzzle quality scoring.

---

## Algorithm 1: Mistake Classification (MistakeDetector)

**Purpose:** Classify a move's quality based on how much it changes the
evaluation (winrate loss relative to the best move).

**Thresholds:**

| Classification | Winrate Loss      | Description                                    |
| -------------- | ----------------- | ---------------------------------------------- |
| BLUNDER        | > 20%             | Severe error — completely changes game outcome |
| MISTAKE        | > 10%             | Significant error — noticeable disadvantage    |
| INACCURACY     | > 5%              | Suboptimal — better moves exist                |
| GOOD           | < -5% (gain)      | Opponent made error, player gains              |
| EXCELLENT      | < -15% (big gain) | Exceptional move                               |

**Pseudocode:**

```python
def classify_mistake(winrate_loss: float) -> MistakeType:
    if winrate_loss > 0.20:
        return BLUNDER
    elif winrate_loss > 0.10:
        return MISTAKE
    elif winrate_loss > 0.05:
        return INACCURACY
    elif winrate_loss < -0.15:
        return EXCELLENT
    elif winrate_loss < -0.05:
        return GOOD
    else:
        return None  # Normal move
```

**Yen-go adaptation — Refutation Quality Scoring:**

We don't have winrate analysis (no AI engine), but we CAN adapt this
concept to measure **refutation quality** in solution trees:

```
For each wrong-move branch in the solution tree:
  refutation_depth = how many moves until the situation is resolved
  refutation_severity = depth × opponent_captures / max_possible

Low severity = trivially wrong (no teaching value)
High severity = deeply wrong (excellent refutation, teaches something)
```

This maps to puzzle quality:

- Puzzles where all wrong moves are instantly punished → lower quality (shallow)
- Puzzles where wrong moves lead to deep, instructive sequences → higher quality

---

## Algorithm 2: Weak Group Detection (PositionAnalyzer)

**Purpose:** Find groups that are in danger on the board and classify
their vulnerability level.

**Classification:**

| Liberties | Group Size | Status        | Description                    |
| --------- | ---------- | ------------- | ------------------------------ |
| 1         | any        | **critical**  | In atari — immediate danger    |
| 2         | any        | **weak**      | One move from atari            |
| 3         | > 5 stones | **unsettled** | Large group with few liberties |
| ≥ 4       | any        | (not flagged) | Likely safe                    |

**For each weak group, assess:**

- `can_escape`: liberties ≥ 3 (heuristic)
- `can_make_eyes`: internal space ≥ 6 points (from territory.py)

**Pseudocode:**

```python
def find_weak_groups(board):
    weak = []
    for group in board.get_all_groups():
        libs = group.num_liberties
        size = len(group.stones)

        if libs == 1:
            status = 'critical'
        elif libs == 2:
            status = 'weak'
        elif libs == 3 and size > 5:
            status = 'unsettled'
        else:
            continue  # Skip safe groups

        weak.append({
            'group': group,
            'status': status,
            'liberties': libs,
            'size': size,
            'can_escape': can_escape(board, group),
            'can_make_eyes': can_make_eyes(board, group),
        })
    return weak
```

**Yen-go use — Initial Position Quality:**

Analyze the **initial position** (before any moves) of each puzzle:

1. Count weak groups by color and status
2. Verify the puzzle objective makes sense:
   - "Kill" puzzle → opponent should have at least one weak/unsettled group
   - "Live" puzzle → player should have a threatened group
   - "Capture" puzzle → opponent should have critical/weak groups
3. Flag puzzles where the objective contradicts the position analysis
   (e.g., "kill" but opponent has no weak groups → likely broken puzzle)

This directly feeds into quality scoring (q:1 for broken, q:2+ for valid).

---

## Algorithm 3: Suggestion Engine — Move Reasoning

**Purpose:** Generate human-readable reasons for why a move is good.

**Reasoning categories:**

| Condition                          | Reason                             |
| ---------------------------------- | ---------------------------------- |
| Winrate > 0.6                      | "Maintain advantage"               |
| Winrate 0.4-0.6                    | "Keep balance"                     |
| Winrate < 0.4                      | "Fight back"                       |
| Position in corner (x<5 AND y<5)   | "Secure corner"                    |
| Position on edge (x<3 OR x>15)     | "Expand side territory"            |
| Position in center                 | "Control center"                   |
| Adjacent critical group (own)      | "Urgent: rescue endangered group"  |
| Adjacent critical group (opponent) | "Urgent: capture vulnerable group" |

**Yen-go adaptation — Hint Generation:**

This category-based reasoning can enhance YH (hints):

```python
def generate_positional_hint(board, first_move_x, first_move_y, player_color):
    hints = []

    # Check for urgent situations
    for group in find_weak_groups(board):
        if group['status'] == 'critical':
            if group['group'].color == player_color:
                hints.append("A group is in danger of being captured!")
            else:
                hints.append("An opponent group can be captured.")

    # Position-based hints
    if is_corner(first_move_x, first_move_y):
        hints.append("Corner focus")
    elif is_edge(first_move_x, first_move_y):
        hints.append("Edge technique")

    return hints[:3]  # YH max 3 hints
```

---

## Algorithm 4: Influence-Based Position Assessment

**Purpose:** The analysis engine combines territory estimation with
influence maps to produce an overall position assessment.

**Key metric:** `estimated_score = territory['black'] - territory['white']`

**Yen-go use — Position Balance as Difficulty Signal:**

```python
def assess_position_balance(board):
    """Compute how balanced the initial position is.

    Balanced positions (score near 0) tend to be harder puzzles
    because the outcome depends on precise play.

    Unbalanced positions (one side clearly winning) are either:
    - Easy puzzles (just maintain advantage)
    - Or the puzzle is about reversing the situation (harder)
    """
    territory = Territory(board)
    result = territory.calculate_territory()
    balance = abs(result['black'] - result['white'])

    if balance < 3:
        return 'balanced'    # Likely harder
    elif balance < 10:
        return 'moderate'    # Medium
    else:
        return 'unbalanced'  # Likely easier OR dramatic reversal
```

---

## Combined Quality Scoring Model

Synthesizing insights from both GoGoGo and gogamev4.0:

```
                         ┌─────────────────────────────┐
                         │   PUZZLE QUALITY SCORER      │
                         └──────────┬──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
     ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
     │  Data Richness   │  │  Tactical Depth  │  │ Position Valid. │
     │  (existing YQ)   │  │  (NEW - GoGoGo)  │  │ (NEW - gogame)  │
     └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
              │                     │                     │
     • refutation count    • ladder detected      • weak groups match
     • comment level       • snapback detected       objective
     • solution tree       • capture verified     • eye count valid
       depth               • life/death verified  • position not broken
     • teaching text       • instinct patterns    • group status
                           • tactical planes        assessment
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │  Composite Score │
                           │     (q: 1-5)     │
                           └─────────────────┘
```

The existing `compute_puzzle_quality_level()` in `core/quality.py` handles
Data Richness. Tactical Depth and Position Validation are the NEW components
that this plan adds.

---

## Mapping to Yen-Go Pipeline

| gogamev4.0 Concept        | Yen-Go Application                             | Module                      |
| ------------------------- | ---------------------------------------------- | --------------------------- |
| MistakeType thresholds    | Refutation depth quality classification        | `core/quality.py`           |
| Weak group detection      | Initial position validation, difficulty signal | `core/tactical_analyzer.py` |
| Move reasoning categories | Hint generation enhancement                    | `core/enrichment/hints.py`  |
| Position balance score    | Difficulty classifier input                    | `core/classifier.py`        |
| Territory estimation      | Puzzle outcome verification                    | `core/tactical_analyzer.py` |
