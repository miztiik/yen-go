# Ambak Tsumego Download Tool

Downloads SGF puzzle files from [ambak/tsumego-bot](https://github.com/ambak/tsumego-bot) GitHub repository.

## Source Information

- **Repository**: https://github.com/ambak/tsumego-bot
- **Content**: Tsumego (life-and-death) puzzles in SGF format
- **Categories**: elementary, intermediate, advanced

## Usage

```bash
# From project root
bash tools/ambak-tsumego/download.sh
```

## Output

SGF files are downloaded to:

```
external-sources/ambak-tsumego/
└── problems/
    ├── elementary/     # ~500+ puzzles
    ├── intermediate/   # ~500+ puzzles
    └── advanced/       # ~500+ puzzles
```

## Features

- **Logging**: All operations logged to `tools/ambak-tsumego/logs/`
- **Progress tracking**: Shows file counts per category
- **Duplicate prevention**: Prompts before overwriting existing files
- **Cleanup**: Automatically removes temporary files

## After Download

Configure the puzzle manager to use these files with the `local` adapter:

```yaml
# In sources configuration
ambak-tsumego:
  adapter: local
  path: external-sources/ambak-tsumego/problems
```

Then run the pipeline:

```bash
python -m backend.puzzle_manager run --source ambak-tsumego
```

## Notes

- This is a **one-time import** script
- Only SGF files are downloaded (no other code from the repo)
- The source repo appears to contain puzzles from goproblems.com
