> ⚠️ **DEPRECATED** - This document describes KataGo integration which was removed in v3.2 (Spec 013).
> Curated sources are pre-validated, so runtime solving is no longer needed.
> Kept for historical reference only.

---

# KataGo Integration & Solution Enhancement

## Overview

The Solve stage (Stage 5) has been upgraded to use a unified solver framework that supports:

- **KataGo** (primary) - High-accuracy neural network solver
- **smargo** (fallback) - Python MCTS solver

Key change: Instead of rejecting puzzles when solvers disagree, the system now **enhances** solution trees by adding solver-discovered moves.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Solve Stage v2.0                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────────┐   │
│  │  KataGo      │ or  │   smargo     │  →  │  Solution      │   │
│  │  Solver      │     │   Solver     │     │  Enhancer      │   │
│  └──────────────┘     └──────────────┘     └────────────────┘   │
│         │                    │                     │             │
│         └────────┬───────────┘                     │             │
│                  ▼                                 │             │
│         ┌──────────────┐                           │             │
│         │  Solution    │◄──────────────────────────┘             │
│         │  Analysis    │                                         │
│         └──────────────┘                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration (No Longer Active)

```json
{
  "solve": {
    "solver": "katago",
    "fallback_solver": "smargo",
    "timeout_seconds": 60,
    "visits": 200,
    "skip_on_unavailable": true,
    "rejection_policy": "enhancement",
    "enable_enhancement": true,
    "min_winrate_for_valid_move": 0.55,
    "max_alternatives_to_add": 3
  }
}
```

## KataGo Setup (Historical)

1. Download KataGo from releases
2. Download model file
3. Set environment variables:
   ```bash
   export KATAGO_PATH=/path/to/katago
   export KATAGO_MODEL=/path/to/model.bin.gz
   ```

## Current Status

As of v3.2 (Spec 013), the solve stage is skipped by default. Curated puzzle sources have pre-validated solutions, eliminating the need for runtime AI verification.

See [architecture/backend/stages.md](../architecture/backend/stages.md) for current pipeline.
