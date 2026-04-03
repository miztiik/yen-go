"""
Board renderer — draws Go board positions with Pillow.

Produces high-resolution board images with:
- Board texture tiling (image asset) or flat color fallback
- Grid lines with star points
- Realistic stone images (RGBA assets) or drawn circle fallback
- Move numbers on stones
- Board coordinate labels (A-T, 1-19)

Supports image-based themes: provide paths to stone PNGs and board
texture JPGs. Ships with a built-in ``besogo`` theme that uses the
assets from ``tools/sgf-viewer-besogo/img/``.
"""

from __future__ import annotations

import logging
import random
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Theme: image-based stones and board texture
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StoneTheme:
    """Image assets for realistic board rendering.

    Each field is a list of file paths. Multiple images per color give
    natural variation (randomly picked per stone, like BesoGo).

    Attributes:
        black_stones: Paths to black stone PNG images (RGBA, any size).
        white_stones: Paths to white stone PNG images (RGBA, any size).
        board_texture: Path to a board texture image (JPG/PNG, tiled).
            If None, falls back to flat ``board_color``.
    """

    black_stones: list[Path] = field(default_factory=list)
    white_stones: list[Path] = field(default_factory=list)
    board_texture: Path | None = None


def besogo_theme() -> StoneTheme:
    """Built-in theme using BesoGo viewer assets.

    Returns a StoneTheme pointing to ``tools/sgf-viewer-besogo/img/``.
    The caller's working directory must be the repo root.

    If the asset directory is missing, returns an empty theme
    (renderer will fall back to flat drawing).
    """
    base = Path("tools/sgf-viewer-besogo/img")
    if not base.is_dir():
        warnings.warn(
            f"BesoGo asset directory not found ({base}); "
            "falling back to flat rendering",
            stacklevel=2,
        )
        return StoneTheme()
    blacks = sorted(base.glob("black*.png"))
    whites = sorted(base.glob("white*.png"))
    board = base / "shinkaya1.jpg"
    if not board.exists():
        board = base / "wood.jpg"
    return StoneTheme(
        black_stones=blacks,
        white_stones=whites,
        board_texture=board if board.exists() else None,
    )


@dataclass(frozen=True)
class RenderConfig:
    """Rendering configuration.

    Attributes:
        cell_size: Pixels between grid lines. Controls resolution.
            48 = ~1000px for 19x19, 72 = ~1500px, 96 = ~2000px.
        padding: Extra space around the board edge (pixels).
        board_color: RGB tuple for board background (used when no theme).
        line_color: RGB tuple for grid lines.
        line_width: Grid line width in pixels.
        star_radius: Star point dot radius in pixels.
        frame_duration_ms: Milliseconds per frame in animated GIF.
        show_coordinates: Whether to draw A-T / 1-19 labels.
        font_size_ratio: Move-number font size as fraction of stone radius.
        theme: Optional StoneTheme with image assets. When provided,
            stone images and board texture override flat drawing.
    """

    cell_size: int = 72
    padding: int = 40
    board_color: tuple[int, int, int] = (214, 171, 106)
    line_color: tuple[int, int, int] = (35, 35, 35)
    line_width: int = 2
    star_radius: int = 5
    frame_duration_ms: int = 1000
    show_coordinates: bool = True
    font_size_ratio: float = 0.55
    theme: StoneTheme | None = None


# ---------------------------------------------------------------------------
# Star points
# ---------------------------------------------------------------------------

_STAR_POINTS: Final[dict[int, list[tuple[int, int]]]] = {
    9: [(2, 2), (6, 2), (4, 4), (2, 6), (6, 6)],
    13: [(3, 3), (9, 3), (6, 6), (3, 9), (9, 9)],
    19: [
        (3, 3), (9, 3), (15, 3),
        (3, 9), (9, 9), (15, 9),
        (3, 15), (9, 15), (15, 15),
    ],
}

# Letters for coordinate labels (skip 'I')
_COL_LABELS: Final[str] = "ABCDEFGHJKLMNOPQRST"


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a clean TrueType font; fall back to default."""
    # Try common system fonts that render well for move numbers
    candidates = [
        "arial.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf",
        "FreeSansBold.ttf",
        "Verdana.ttf",
        "Tahoma.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class BoardRenderer:
    """Renders Go board positions to PIL Images.

    Supports two rendering modes:
    1. **Flat** (default): Draws circles with shading, flat board color.
    2. **Themed**: Composites stone image assets (RGBA) onto a tiled board
       texture. Pass a ``StoneTheme`` via ``RenderConfig.theme``.
    """

    def __init__(self, board_size: int, cfg: RenderConfig | None = None) -> None:
        self.size = board_size
        self.cfg = cfg or RenderConfig()
        self._stone_radius = int(self.cfg.cell_size * 0.47)
        font_px = max(10, int(self._stone_radius * 2 * self.cfg.font_size_ratio))
        self._font = _get_font(font_px)
        self._coord_font = _get_font(max(10, self.cfg.cell_size // 3))

        # Pre-compute coordinate label offset — must be large enough so that
        # edge stones (radius extends past the outermost grid line) never
        # overlap the coordinate labels.
        coord_font_height = max(10, self.cfg.cell_size // 3)
        label_gap = 8  # minimum pixels between stone edge and label edge
        self._coord_margin = (
            (self._stone_radius + coord_font_height + 2 * label_gap)
            if self.cfg.show_coordinates
            else 0
        )
        # Distance from grid line to label center: stone clears, then label centered
        self._coord_label_offset = self._stone_radius + coord_font_height // 2 + label_gap
        self._total_padding = self.cfg.padding + self._coord_margin

        # Pre-load and resize theme assets once
        self._black_imgs: list[Image.Image] = []
        self._white_imgs: list[Image.Image] = []
        self._board_texture: Image.Image | None = None
        stone_size = self._stone_radius * 2

        if self.cfg.theme:
            for p in self.cfg.theme.black_stones:
                if p.exists():
                    try:
                        img = Image.open(p).convert("RGBA")
                        self._black_imgs.append(
                            img.resize((stone_size, stone_size), Image.Resampling.LANCZOS)
                        )
                    except Exception:
                        log.warning("Failed to load black stone asset %s", p)
            for p in self.cfg.theme.white_stones:
                if p.exists():
                    try:
                        img = Image.open(p).convert("RGBA")
                        self._white_imgs.append(
                            img.resize((stone_size, stone_size), Image.Resampling.LANCZOS)
                        )
                    except Exception:
                        log.warning("Failed to load white stone asset %s", p)
            if self.cfg.theme.board_texture and self.cfg.theme.board_texture.exists():
                try:
                    self._board_texture = Image.open(
                        self.cfg.theme.board_texture
                    ).convert("RGB")
                except Exception:
                    log.warning(
                        "Failed to load board texture %s",
                        self.cfg.theme.board_texture,
                    )

            # Warn once if theme was requested but no assets loaded
            if not self._black_imgs and not self._white_imgs:
                warnings.warn(
                    "Theme specified but no stone assets loaded; "
                    "falling back to flat rendering",
                    stacklevel=2,
                )

        # Use deterministic random so identical inputs produce identical output
        self._rng = random.Random(42)

    # -- coordinate helpers --------------------------------------------------

    def _grid_xy(self, col: int, row: int) -> tuple[int, int]:
        """Grid intersection (col, row) → pixel (x, y)."""
        x = self._total_padding + col * self.cfg.cell_size
        y = self._total_padding + row * self.cfg.cell_size
        return x, y

    def _image_size(self) -> tuple[int, int]:
        w = self._total_padding * 2 + self.cfg.cell_size * (self.size - 1)
        h = w  # square
        return w, h

    # -- drawing primitives --------------------------------------------------

    def _draw_board_background(self, img: Image.Image) -> None:
        """Fill the image with board texture (scaled to fit) or flat color."""
        if self._board_texture:
            tex = self._board_texture.resize(
                (img.width, img.height), Image.Resampling.LANCZOS,
            )
            img.paste(tex, (0, 0))
        else:
            img.paste(self.cfg.board_color, (0, 0, img.width, img.height))

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw grid lines."""
        for i in range(self.size):
            # Vertical line
            x0, y0 = self._grid_xy(i, 0)
            x1, y1 = self._grid_xy(i, self.size - 1)
            draw.line((x0, y0, x1, y1), fill=self.cfg.line_color, width=self.cfg.line_width)
            # Horizontal line
            x0, y0 = self._grid_xy(0, i)
            x1, y1 = self._grid_xy(self.size - 1, i)
            draw.line((x0, y0, x1, y1), fill=self.cfg.line_color, width=self.cfg.line_width)

    def _draw_star_points(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw star point dots."""
        points = _STAR_POINTS.get(self.size, [])
        r = self.cfg.star_radius
        for col, row in points:
            cx, cy = self._grid_xy(col, row)
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                fill=self.cfg.line_color,
            )

    def _draw_coordinates(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw A-T column and 1-19 row labels."""
        if not self.cfg.show_coordinates:
            return
        label_color = (80, 60, 40)
        offset = self._coord_label_offset

        for i in range(self.size):
            # Column labels (top and bottom)
            letter = _COL_LABELS[i] if i < len(_COL_LABELS) else str(i)
            cx, _ = self._grid_xy(i, 0)
            _, by = self._grid_xy(0, self.size - 1)
            _draw_centered_text(draw, cx, self._total_padding - offset, letter, self._coord_font, label_color)
            _draw_centered_text(draw, cx, by + offset, letter, self._coord_font, label_color)

            # Row labels (left and right) — Go convention: 19 at top, 1 at bottom
            num = str(self.size - i)
            _, cy = self._grid_xy(0, i)
            lx, _ = self._grid_xy(0, 0)
            rx, _ = self._grid_xy(self.size - 1, 0)
            _draw_centered_text(draw, lx - offset, cy, num, self._coord_font, label_color)
            _draw_centered_text(draw, rx + offset, cy, num, self._coord_font, label_color)

    def _draw_stone(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        col: int,
        row: int,
        color: str,
        number: int | None = None,
        *,
        last_move: bool = False,
    ) -> None:
        """Draw a single stone with optional move number.

        Uses image assets from theme if available; otherwise draws
        circles with shading.

        Args:
            draw: ImageDraw instance.
            img: The PIL Image (needed for alpha compositing).
            col: Board column (0-indexed).
            row: Board row (0-indexed).
            color: "B" for black, "W" for white.
            number: Optional move number to display on stone.
            last_move: Whether to highlight as last move played.
        """
        cx, cy = self._grid_xy(col, row)
        r = self._stone_radius

        # Choose rendering mode: image asset or drawn circle
        stone_pool = self._black_imgs if color == "B" else self._white_imgs

        if stone_pool:
            # Image-based rendering
            stone_img = self._rng.choice(stone_pool)
            # Paste with alpha at top-left of stone
            paste_x = cx - r
            paste_y = cy - r
            img.paste(stone_img, (paste_x, paste_y), stone_img)
            text_color = (240, 240, 240) if color == "B" else (20, 20, 20)
        elif color == "B":
            # Drawn black stone with subtle gradient effect
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                fill=(30, 30, 30),
                outline=(10, 10, 10),
                width=2,
            )
            hr = r // 3
            hx, hy = cx - r // 4, cy - r // 4
            draw.ellipse(
                (hx - hr, hy - hr, hx + hr, hy + hr),
                fill=(80, 80, 80),
            )
            text_color = (240, 240, 240)
        else:
            # Drawn white stone
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                fill=(235, 235, 230),
                outline=(140, 140, 140),
                width=2,
            )
            hr = r // 3
            hx, hy = cx - r // 4, cy - r // 4
            draw.ellipse(
                (hx - hr, hy - hr, hx + hr, hy + hr),
                fill=(255, 255, 255),
            )
            text_color = (20, 20, 20)

        # Last-move marker ring
        if last_move and number is None:
            marker_color = (220, 50, 50)
            ring_r = r - 4
            draw.ellipse(
                (cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r),
                outline=marker_color,
                width=3,
            )

        # Move number
        if number is not None:
            label = str(number)
            _draw_centered_text(draw, cx, cy, label, self._font, text_color)

    # -- public API ----------------------------------------------------------

    def render(
        self,
        black_stones: set[tuple[int, int]],
        white_stones: set[tuple[int, int]],
        moves: list[tuple[str, int, int]] | None = None,
        move_offset: int = 0,
    ) -> Image.Image:
        """Render a complete board position.

        Args:
            black_stones: Set of (col, row) for setup black stones.
            white_stones: Set of (col, row) for setup white stones.
            moves: Optional list of (color, col, row) for solution moves.
                Moves are numbered starting from move_offset + 1.
            move_offset: Starting number offset for move numbering.

        Returns:
            PIL Image of the board.
        """
        w, h = self._image_size()
        img = Image.new("RGB", (w, h), self.cfg.board_color)
        draw = ImageDraw.Draw(img)

        self._draw_board_background(img)
        self._draw_grid(draw)
        self._draw_star_points(draw)
        self._draw_coordinates(draw)

        # Track occupied positions for move overlap detection
        occupied: dict[tuple[int, int], str] = {}

        # Setup stones (no numbers)
        for col, row in black_stones:
            self._draw_stone(draw, img, col, row, "B")
            occupied[(col, row)] = "B"

        for col, row in white_stones:
            self._draw_stone(draw, img, col, row, "W")
            occupied[(col, row)] = "W"

        # Solution moves (numbered)
        if moves:
            for i, (color, col, row) in enumerate(moves):
                num = move_offset + i + 1
                occupied[(col, row)] = color
                self._draw_stone(draw, img, col, row, color, number=num)

        return img

    def render_frames(
        self,
        black_stones: set[tuple[int, int]],
        white_stones: set[tuple[int, int]],
        moves: list[tuple[str, int, int]],
    ) -> list[Image.Image]:
        """Render one frame per move for GIF animation.

        Frame 0: Setup stones only (puzzle position).
        Frame 1..N: Each successive move added.

        All frames include move numbers on all played stones so far.

        Returns:
            List of PIL Images (one per frame).
        """
        frames: list[Image.Image] = []

        # Frame 0: puzzle position
        frames.append(self.render(black_stones, white_stones))

        # One frame per move, accumulating
        for step in range(1, len(moves) + 1):
            frames.append(
                self.render(black_stones, white_stones, moves[:step])
            )

        return frames


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int],
) -> None:
    """Draw text centered at (cx, cy)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Adjust for baseline offset
    draw.text(
        (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
        text,
        fill=color,
        font=font,
    )
