"""
CLI entry point for sgf2img.

Usage:
    python -m tools.sgf2img png --sgf puzzle.sgf [--output out.png]
    python -m tools.sgf2img gif --sgf puzzle.sgf [--output out.gif]
    python -m tools.sgf2img both --sgf puzzle.sgf [--output-dir ./out/]

All options use explicit named flags — no positional arguments.

Defaults:
    --output         Inferred from input: stem + .png/.gif
    --output-dir     Current directory (for 'both' command)
    --theme          besogo (falls back to flat if assets missing)
    --cell-size      72 pixels per grid cell
    --duration       1000ms per GIF frame
    Solution         Included by default; use --no-solution to exclude
    Coordinates      Shown by default; use --no-coords to hide
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sgf2img.exporter import export_gif, export_png
from tools.sgf2img.renderer import RenderConfig, StoneTheme, besogo_theme


def _resolve_theme(name: str) -> StoneTheme | None:
    """Resolve theme name to a StoneTheme.

    Returns None only when explicitly set to 'none'.
    """
    if name == "none":
        return None
    if name == "besogo":
        return besogo_theme()
    # Custom directory: expect black*.png, white*.png, and an optional board texture
    p = Path(name)
    if p.is_dir():
        blacks = sorted(p.glob("black*.png"))
        whites = sorted(p.glob("white*.png"))
        board = None
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            candidates = sorted(p.glob(ext))
            for c in candidates:
                if "board" in c.stem.lower() or "wood" in c.stem.lower() or "kaya" in c.stem.lower():
                    board = c
                    break
            if board:
                break
        return StoneTheme(black_stones=blacks, white_stones=whites, board_texture=board)
    print(f"Warning: theme '{name}' not found, falling back to flat rendering", file=sys.stderr)
    return None


def _infer_output(sgf_path: str, ext: str) -> str:
    """Derive output filename from input SGF path by swapping extension."""
    return str(Path(sgf_path).with_suffix(ext))


def _build_config(args: argparse.Namespace) -> RenderConfig:
    theme = _resolve_theme(args.theme)
    return RenderConfig(
        cell_size=args.cell_size,
        frame_duration_ms=args.duration,
        show_coordinates=not args.no_coords,
        theme=theme,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sgf2img",
        description="Convert SGF Go puzzles to PNG/GIF images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s png --sgf puzzle.sgf                   → puzzle.png (with solution, besogo theme)
  %(prog)s gif --sgf puzzle.sgf                   → puzzle.gif
  %(prog)s png --sgf puzzle.sgf --output out.png  → out.png
  %(prog)s png --sgf puzzle.sgf --no-solution     → puzzle state only (no moves)
  %(prog)s png --sgf puzzle.sgf --theme none       → flat rendering (no textures)
  %(prog)s both --sgf puzzle.sgf --output-dir img/ → img/puzzle.png + img/puzzle.gif
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- png --
    p_png = sub.add_parser(
        "png",
        help="Export a static PNG board image",
        description="Render an SGF puzzle as a PNG image. Solution moves are shown by default.",
    )
    p_png.add_argument("--sgf", required=True, help="Path to input .sgf file")
    p_png.add_argument(
        "--output", default=None,
        help="Output .png file path (default: inferred from --sgf filename)",
    )

    # -- gif --
    p_gif = sub.add_parser(
        "gif",
        help="Export an animated GIF of the solution",
        description="Render an SGF puzzle as an animated GIF showing the solution move by move.",
    )
    p_gif.add_argument("--sgf", required=True, help="Path to input .sgf file")
    p_gif.add_argument(
        "--output", default=None,
        help="Output .gif file path (default: inferred from --sgf filename)",
    )

    # -- both --
    p_both = sub.add_parser(
        "both",
        help="Export both PNG and GIF into a directory",
        description=(
            "Render an SGF puzzle as both PNG and GIF.\n"
            "Produces: {stem}.png (with solution) and {stem}.gif.\n"
            "Add --no-solution to get puzzle-state-only PNG."
        ),
    )
    p_both.add_argument("--sgf", required=True, help="Path to input .sgf file")
    p_both.add_argument(
        "--output-dir", default=".",
        help="Output directory for generated files (default: current directory)",
    )

    # -- shared options --
    for p in (p_png, p_gif, p_both):
        p.add_argument(
            "--no-solution", action="store_true", default=False,
            help="Exclude solution moves (default: solution is included)",
        )
        p.add_argument(
            "--cell-size", type=int, default=72,
            help="Pixels per grid intersection (default: 72; higher = larger image)",
        )
        p.add_argument(
            "--duration", type=int, default=1000,
            help="Milliseconds per GIF frame (default: 1000)",
        )
        p.add_argument(
            "--no-coords", action="store_true", default=False,
            help="Hide board coordinate labels (default: coordinates shown)",
        )
        p.add_argument(
            "--theme", type=str, default="besogo",
            help=(
                "Image theme for stone/board textures (default: besogo). "
                "Use 'none' for flat rendering, or a directory path for custom assets."
            ),
        )

    args = parser.parse_args(argv)
    cfg = _build_config(args)
    solution = not args.no_solution

    if args.command == "png":
        output = args.output or _infer_output(args.sgf, ".png")
        out = export_png(args.sgf, output, solution=solution, config=cfg)
        print(f"PNG saved: {out}")

    elif args.command == "gif":
        output = args.output or _infer_output(args.sgf, ".gif")
        out = export_gif(args.sgf, output, config=cfg)
        print(f"GIF saved: {out}")

    elif args.command == "both":
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(args.sgf).stem

        # PNG (with or without solution)
        png_out = export_png(
            args.sgf, out_dir / f"{stem}.png", solution=solution, config=cfg,
        )
        print(f"PNG saved: {png_out}")

        # GIF (always animated with solution)
        gif_out = export_gif(args.sgf, out_dir / f"{stem}.gif", config=cfg)
        print(f"GIF saved: {gif_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
