"""
SGF → PNG / GIF exporter.

Parses SGF using tools.core.sgf_parser, extracts setup stones and
solution moves, then delegates to BoardRenderer for image generation.

Public API:
    export_png(sgf_path, output, solution=False, config=None)
    export_gif(sgf_path, output, config=None)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from tools.core.sgf_parser import SgfNode, SgfTree, parse_sgf
from tools.sgf2img.renderer import BoardRenderer, RenderConfig

# ---------------------------------------------------------------------------
# SGF data extraction
# ---------------------------------------------------------------------------

def _extract_setup_stones(
    tree: SgfTree,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Extract setup stones as (col, row) sets."""
    black = {(p.x, p.y) for p in tree.black_stones}
    white = {(p.x, p.y) for p in tree.white_stones}
    return black, white


def _extract_mainline_moves(tree: SgfTree) -> list[tuple[str, int, int]]:
    """Walk the solution tree trunk (first child at each level).

    Returns list of (color_str, col, row) tuples.
    """
    moves: list[tuple[str, int, int]] = []
    node = tree.solution_tree
    while node.children:
        child = node.children[0]  # trunk
        if child.move is not None and child.color is not None:
            moves.append((child.color.value, child.move.x, child.move.y))
        node = child
    return moves


def _extract_all_variation_paths(
    tree: SgfTree,
) -> list[list[tuple[str, int, int]]]:
    """Extract every root-to-leaf path through the solution tree.

    Returns a list of move sequences (one per variation path).
    """
    paths: list[list[tuple[str, int, int]]] = []

    def _walk(node: SgfNode, current: list[tuple[str, int, int]]) -> None:
        if node.move is not None and node.color is not None:
            current = [*current, (node.color.value, node.move.x, node.move.y)]
        if not node.children:
            if current:
                paths.append(current)
            return
        for child in node.children:
            _walk(child, current)

    _walk(tree.solution_tree, [])
    return paths


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_png(
    sgf_path: str | Path,
    output: str | Path,
    *,
    solution: bool = False,
    config: RenderConfig | None = None,
) -> Path:
    """Export a single PNG image of the board.

    Args:
        sgf_path: Path to .sgf file.
        output: Output .png file path.
        solution: If False (default), render puzzle state (setup stones only).
            If True, render with the main-line solution moves numbered.
        config: Optional rendering configuration.

    Returns:
        Path to the written PNG file.
    """
    sgf_path = Path(sgf_path)
    output = Path(output)
    cfg = config or RenderConfig()

    tree = parse_sgf(sgf_path.read_text(encoding="utf-8"))
    black, white = _extract_setup_stones(tree)
    moves = _extract_mainline_moves(tree) if solution else None

    renderer = BoardRenderer(tree.board_size, cfg)
    img = renderer.render(black, white, moves)
    img.save(str(output), "PNG")
    return output


def export_gif(
    sgf_path: str | Path,
    output: str | Path,
    *,
    config: RenderConfig | None = None,
    loop: int = 0,
) -> Path:
    """Export an animated GIF showing the solution move by move.

    Frame 0 shows the puzzle position (setup stones only), held for
    2x the normal duration. Each subsequent frame adds the next trunk
    move with its number. The final frame is held for 4x duration.

    Args:
        sgf_path: Path to .sgf file.
        output: Output .gif file path.
        config: Optional rendering configuration.
        loop: GIF loop count (0 = loop forever).

    Returns:
        Path to the written GIF file.
    """
    sgf_path = Path(sgf_path)
    output = Path(output)
    cfg = config or RenderConfig()

    tree = parse_sgf(sgf_path.read_text(encoding="utf-8"))
    black, white = _extract_setup_stones(tree)
    moves = _extract_mainline_moves(tree)

    renderer = BoardRenderer(tree.board_size, cfg)
    frames = renderer.render_frames(black, white, moves)

    if not frames:
        # Edge case: no moves — just save single frame
        img = renderer.render(black, white)
        img.save(str(output), "PNG")
        return output

    # Convert to palette mode for GIF
    palette_frames = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT) for f in frames]

    # Build duration list: first frame 2x, middle 1x, last frame 4x
    base = cfg.frame_duration_ms
    durations = [base * 2]  # opening position held longer
    for _ in range(1, len(palette_frames) - 1):
        durations.append(base)
    if len(palette_frames) > 1:
        durations.append(base * 4)  # final position held longest

    palette_frames[0].save(
        str(output),
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=loop,
        optimize=True,
    )
    return output
