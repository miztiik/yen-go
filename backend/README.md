# Backend

The Yen-Go backend contains Python packages for puzzle processing.

## Packages

### puzzle_manager

The puzzle manager implements a 3-stage pipeline for processing Go tsumego puzzles:

1. **INGEST** - Fetch puzzles from sources, parse SGF, validate
2. **ANALYZE** - Classify difficulty, detect techniques, enrich
3. **PUBLISH** - Write to output, build indexes

See [puzzle_manager/README.md](puzzle_manager/README.md) for details.

## Quick Start

```bash
# Run the puzzle manager pipeline
python -m backend.puzzle_manager run

# Check status
python -m backend.puzzle_manager status

# Validate config
python -m backend.puzzle_manager validate
```

## Requirements

- Python 3.12+
- pydantic>=2.5.0
- httpx>=0.26.0
- tenacity>=8.2.0

## Development

```bash
# Install development dependencies
pip install -e "backend/puzzle_manager[dev]"

# Run tests
pytest backend/puzzle_manager/tests/

# Run linting
ruff check backend/

# Run type checking
mypy backend/
```
