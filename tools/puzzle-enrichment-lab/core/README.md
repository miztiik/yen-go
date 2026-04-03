# Core — KaTrain SGF Parser

Stripped copy of [KaTrain's](https://github.com/sanderland/katrain) pure-Python SGF parser (MIT License).

## Contents

| File | Description |
|------|-------------|
| `sgf_parser.py` | `Move`, `SGFNode`, `SGF.parse_sgf()` — core SGF parsing and serialization |
| `tsumego_analysis.py` | Tsumego-specific wrappers: `parse_sgf()`, `extract_position()`, `extract_correct_first_move()`, `compose_enriched_sgf()` |

## Stripped Items

The following KaTrain features were removed (not needed for tsumego analysis):

- `chardet` dependency and `parse_file()` (file-based parsing with encoding detection)
- `parse_gib()` and `parse_ngf()` (multi-format game record support)

## Key API Differences from Old Parser

| Old (`SgfNode`) | New (`SGFNode`) |
|-----------------|-----------------|
| `node.get("key")` | `node.get_property("key")` (or `node.get("key")` via alias) |
| `node.get_all("key")` | `node.get_list_property("key")` (or `node.get_all("key")` via alias) |
| `node.move → (Color, coord)` | `node.move → Move` object with `.player`, `.sgf()`, `.gtp()` |
| `node.comment` | `node.comment` (same) |
| `SgfNode(properties={...})` | `SGFNode(properties={...})` |

Last Updated: 2026-03-13
