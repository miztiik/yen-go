# SGF Viewer (BesoGo)

Standalone SGF viewer for reviewing Go games and tsumego puzzles offline.

## Quick Start

### Local Usage

1. Open `index.html` in your browser (works from `file://` URLs)
2. The sample tsumego puzzle loads automatically
3. Use navigation controls or keyboard shortcuts to review moves

### Hosted Usage

Host this directory on any static server (e.g., GitHub Pages, local HTTP server):

```bash
# Python 3
python -m http.server 8000

# Node.js
npx http-server
```

Then navigate to `http://localhost:8000`

## Loading SGF Files

### Via URL Query Parameter

Append `?sgf=<url>` to load a specific SGF file:

```
index.html?sgf=https://example.com/puzzle.sgf
```

**Note**: The SGF URL must be CORS-enabled or from the same origin.

### Error Handling

- If the URL is unreachable, an error message displays and `sample.sgf` loads as fallback
- The viewer remains usable even when remote SGF fails to load

## Navigation

### Keyboard Shortcuts

- `←` / `→` - Previous/next move
- `Shift+←` - Previous branching node
- `Page Up` / `Page Down` - Jump 10 moves
- `Home` / `End` - First/last move

### Mouse Controls

- **Mouse wheel** - Scroll through moves
- **Click variations** - Select branches in tree panel
- **Control buttons** - Use on-screen navigation

## Features

- **Fully offline** - All assets bundled; works without internet
- **Realistic rendering** - Wood board theme with realistic stone textures
- **Variation support** - Navigate complex game trees
- **Comments display** - View move commentary and game info
- **Zero dependencies** - Self-contained; no installation required

## Directory Structure

```

sgf-viewer-besogo/
├── index.html          # Main viewer page
├── sample.sgf          # Demo tsumego puzzle
├── css/                # BesoGo stylesheets
│   ├── besogo.css
│   ├── besogo-fill.css
│   └── board-wood.css
├── js/                 # BesoGo library
│   └── besogo-all-min.js
└── img/                # Board and stone textures
    ├── black0.png ... black3.png
    ├── white0.png ... white10.png
    └── wood.jpg
```

## Troubleshooting

| Issue                    | Solution                                               |
| ------------------------ | ------------------------------------------------------ |
| Blank screen             | Check browser console; verify all CSS/JS files present |
| SGF not loading from URL | Confirm URL is reachable and CORS-enabled              |
| No keyboard navigation   | Click viewer area to focus                             |
| Missing textures         | Verify `img/` directory contains all stone/board files |

## Technology

- **BesoGo** - SGF viewer library
- **Repository** - [yewang/besogo](https://github.com/yewang/besogo)
- **Version** - Latest from gh-pages branch

## License

This viewer uses BesoGo under the MIT License. See BesoGo repository for details.
