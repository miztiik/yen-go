"""
SGF to Image converter — GIF (animated) and PNG (static).

Converts Go/Tsumego SGF files into high-resolution board images with
numbered move stones. Standalone tool — imports only from tools.core.

Defaults: solution included, besogo theme, coordinates shown, 1000ms/frame.
Use ``--no-solution``, ``--theme none``, ``--no-coords`` to override.

Public API:
    export_png(sgf_path, output, solution=True, config=None)
    export_gif(sgf_path, output, config=None)
    RenderConfig — rendering configuration dataclass
    StoneTheme  — image asset paths for themed rendering
    besogo_theme() — built-in theme using BesoGo viewer assets
"""

from tools.sgf2img.exporter import export_gif, export_png
from tools.sgf2img.renderer import RenderConfig, StoneTheme, besogo_theme

__all__ = ["export_gif", "export_png", "RenderConfig", "StoneTheme", "besogo_theme"]
