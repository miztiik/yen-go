# Yen-Go Documentation

Welcome to the Yen-Go documentation. This is the central hub for all project documentation.

**Last Updated**: 2026-02-01

---

## I want to...

### Understand

| Goal                                        | Go to                                                     |
| ------------------------------------------- | --------------------------------------------------------- |
| Learn the system architecture               | [Architecture Overview](architecture/README.md)           |
| Understand static-first design              | [System Overview](architecture/system-overview.md)        |
| Learn how puzzles flow through the pipeline | [Pipeline Architecture](architecture/backend/pipeline.md) |
| Understand the frontend design              | [Frontend Overview](architecture/frontend/overview.md)    |
| Learn about SGF properties                  | [Concepts: SGF Properties](concepts/sgf-properties.md)    |
| Understand difficulty levels                | [Concepts: Levels](concepts/levels.md)                    |
| Learn technique tags                        | [Concepts: Tags](concepts/tags.md)                        |
| Understand hints                            | [Concepts: Hints](concepts/hints.md)                      |

### Do

| Goal                         | Go to                                                            |
| ---------------------------- | ---------------------------------------------------------------- |
| **Play the game**            | [Getting Started: Play](getting-started/play.md)                 |
| **Set up development**       | [Getting Started: Develop](getting-started/develop.md)           |
| Run the puzzle pipeline      | [How-To: Run Pipeline](how-to/backend/run-pipeline.md)           |
| Create a new source adapter  | [How-To: Create Adapter](how-to/backend/create-adapter.md)       |
| Troubleshoot pipeline issues | [How-To: Troubleshoot](how-to/backend/troubleshoot.md)           |
| Configure puzzle sources     | [How-To: Configure Sources](how-to/backend/configure-sources.md) |
| Rollback published puzzles   | [How-To: Rollback](how-to/backend/rollback.md)                   |
| Clean up staging files       | [How-To: Cleanup](how-to/backend/cleanup.md)                     |
| Set up frontend development  | [How-To: Frontend Dev](how-to/frontend/local-development.md)     |
| Build and deploy frontend    | [How-To: Build & Deploy](how-to/frontend/build-deploy.md)        |

### Look Up

| Goal                     | Go to                                                    |
| ------------------------ | -------------------------------------------------------- |
| CLI command reference    | [Reference: CLI](reference/cli-reference.md)             |
| Adapter configuration    | [Reference: Adapters](reference/adapters/)               |
| Tag definitions          | [Reference: Tags](reference/tags.md)                     |
| Level definitions        | [Reference: Levels](reference/levels.md)                 |
| GitHub Actions workflows | [Reference: GitHub Actions](reference/github-actions.md) |

---

## Documentation Structure

```
docs/
├── getting-started/      # Entry points for new users
│   ├── play.md           # For players
│   └── develop.md        # For developers
│
├── architecture/         # WHY and HOW (design decisions)
│   ├── README.md         # System principles
│   ├── system-overview.md# Static-first design
│   ├── backend/          # Pipeline, adapters, SGF
│   └── frontend/         # Preact, state, modes
│
├── how-to/               # HOW TO (step-by-step guides)
│   ├── backend/          # Pipeline operations
│   └── frontend/         # Frontend development
│
├── concepts/             # Shared knowledge
│   ├── sgf-properties.md # SGF property reference
│   ├── levels.md         # Difficulty system
│   ├── tags.md           # Technique taxonomy
│   ├── hints.md          # Hint system
│   ├── quality.md        # Quality metrics
│   └── glossary.md       # Go/Tsumego terms
│
├── reference/            # Pure lookup (no prose)
│   ├── cli-reference.md  # CLI commands
│   ├── adapters/         # Per-adapter config
│   └── ...
│
└── archive/              # Deprecated docs
```

---

## Conventions

### Three-Tier Documentation

| Tier             | Purpose                   | Example                    |
| ---------------- | ------------------------- | -------------------------- |
| **Architecture** | Why and how it's designed | "Why static-first?"        |
| **How-To**       | Step-by-step procedures   | "How to run the pipeline"  |
| **Concepts**     | Cross-cutting knowledge   | "What are Y\* properties?" |
| **Reference**    | Pure lookup tables        | "CLI command options"      |

### Cross-References

Every document includes a "See also" section linking related docs:

```markdown
> **See also**:
>
> - [Architecture: X](path/to/x.md) — Why this works
> - [How-To: Y](path/to/y.md) — Step-by-step guide
> - [Reference: Z](path/to/z.md) — Configuration options
```

### File Naming

- **kebab-case** for all files (e.g., `puzzle-sources.md`)
- **Verb-first** for how-to guides (e.g., `create-adapter.md`)
- Only `README.md` uses uppercase

---

## Component Documentation

| Component      | Location                                                                | Purpose             |
| -------------- | ----------------------------------------------------------------------- | ------------------- |
| Frontend       | [frontend/README.md](../frontend/README.md)                             | Preact app setup    |
| Puzzle Manager | [backend/puzzle_manager/README.md](../backend/puzzle_manager/README.md) | Python pipeline     |
| Configuration  | [config/README.md](../config/README.md)                                 | Shared config files |

---

_For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md)._
