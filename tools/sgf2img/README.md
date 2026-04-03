# sgf2img — SGF to PNG/GIF Converter

Converts Go (Baduk/Weiqi) tsumego SGF files into high-resolution board images.

- **PNG**: Static board image — puzzle or solution state
- **GIF**: Animated walkthrough of the solution, one move per frame

## Quick Start

```bash
# Minimal — just provide the SGF file, everything else has sensible defaults
python -m tools.sgf2img png --sgf puzzle.sgf          # → puzzle.png
python -m tools.sgf2img gif --sgf puzzle.sgf          # → puzzle.gif
python -m tools.sgf2img both --sgf puzzle.sgf         # → puzzle.png + puzzle.gif
```

## Commands

| Command | Description |
|---------|-------------|
| `png`   | Export a static PNG board image |
| `gif`   | Export an animated GIF of the solution |
| `both`  | Export both PNG and GIF into a directory |

## Options

All options use explicit named flags — no positional arguments.

| Option | Default | Description |
|--------|---------|-------------|
| `--sgf FILE` | **(required)** | Path to input .sgf file |
| `--output FILE` | Inferred from `--sgf` | Output file path (png/gif commands) |
| `--output-dir DIR` | `.` (current dir) | Output directory (both command) |
| `--no-solution` | Solution included | Exclude solution moves (show puzzle state only) |
| `--no-coords` | Coordinates shown | Hide board coordinate labels (A-T, 1-19) |
| `--theme NAME` | `besogo` | Image theme: `besogo`, `none`, or path to asset directory |
| `--cell-size N` | `72` | Pixels per grid intersection (higher = larger image) |
| `--duration N` | `1000` | Milliseconds per GIF frame |

## Defaults

- **Solution**: Included by default. Use `--no-solution` to render puzzle state only.
- **Theme**: `besogo` (realistic stone images and board texture from BesoGo viewer assets). Falls back silently to flat rendering if assets are missing.
- **Coordinates**: Shown by default. Use `--no-coords` to hide.
- **Output**: Inferred from input filename. `--sgf puzzle.sgf` → `puzzle.png` / `puzzle.gif`.
- **Cell size**: 72px per grid cell. Use `--cell-size 48` for smaller or `--cell-size 96` for larger images.
- **Duration**: 1 second per move frame (1000ms). Override with `--duration 1500` etc.

## Examples

```bash
# PNG with solution (default)
python -m tools.sgf2img png --sgf prob0026.sgf

# PNG puzzle state only (no solution moves)
python -m tools.sgf2img png --sgf prob0026.sgf --no-solution

# PNG with explicit output path
python -m tools.sgf2img png --sgf prob0026.sgf --output images/problem26.png

# GIF with slower animation
python -m tools.sgf2img gif --sgf prob0026.sgf --duration 1500

# Flat rendering (no textures)
python -m tools.sgf2img png --sgf prob0026.sgf --theme none

# Custom theme from asset directory
python -m tools.sgf2img png --sgf prob0026.sgf --theme /path/to/my-stones/

# Both PNG and GIF, high resolution, no coordinates
python -m tools.sgf2img both --sgf prob0026.sgf --output-dir img/ --cell-size 96 --no-coords
```

## Themes

| Theme | Description |
|-------|-------------|
| `besogo` | Built-in realistic theme using BesoGo viewer assets (4 black, 11 white stone variants, shinkaya board texture) |
| `none` | Flat vector rendering — circles with shading, solid board color |
| `/path/` | Custom directory: expects `black*.png`, `white*.png` (RGBA), and optionally a board texture (`board*.jpg`/`wood*.jpg`/`kaya*.jpg`) |

If the besogo assets directory is missing or any asset file is corrupt/unreadable, the renderer falls back silently to flat rendering with a warning.

## Python API

```python
from tools.sgf2img import export_png, export_gif, RenderConfig, besogo_theme

# PNG with defaults (solution included, besogo theme)
export_png("puzzle.sgf", "puzzle.png", solution=True)

# PNG puzzle state only
export_png("puzzle.sgf", "puzzle_state.png", solution=False)

# GIF with custom config
cfg = RenderConfig(cell_size=96, frame_duration_ms=1200, theme=besogo_theme())
export_gif("puzzle.sgf", "puzzle.gif", config=cfg)

# Flat rendering (no theme)
flat_cfg = RenderConfig(theme=None)
export_png("puzzle.sgf", "flat.png", config=flat_cfg)
```

## Dependencies

- **Pillow** — image rendering (PNG/GIF)
- **tools.core.sgf_parser** — SGF parsing (internal, no external imports)

## Cell Size Reference

| `--cell-size` | Approx. image width (19×19) | Use case |
|---------------|----------------------------|----------|
| 36 | ~750px | Thumbnails |
| 48 | ~1000px | Web/email |
| 72 | ~1400px | Default — good balance |
| 96 | ~1900px | Print / high-DPI |
