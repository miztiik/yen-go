"""Tests for tools.sgf2img."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tools.sgf2img.exporter import export_gif, export_png
from tools.sgf2img.renderer import BoardRenderer, RenderConfig, StoneTheme, besogo_theme

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SGF = (
    "(;SZ[9]FF[4]GM[1]PL[B]"
    "AB[cc][dc][ec]AW[cd][dd][ed]"
    "(;B[ce]C[Correct](;W[de]))"
    "(;B[df]C[Wrong]))"
)

MULTI_MOVE_SGF = (
    "(;SZ[9]FF[4]GM[1]PL[B]"
    "AB[ee][ef][fe]AW[dd][de][ed]"
    "(;B[df](;W[cf](;B[dg]C[Correct]))))"
)


@pytest.fixture
def simple_sgf_file(tmp_path: Path) -> Path:
    p = tmp_path / "simple.sgf"
    p.write_text(SIMPLE_SGF, encoding="utf-8")
    return p


@pytest.fixture
def multi_move_sgf_file(tmp_path: Path) -> Path:
    p = tmp_path / "multi.sgf"
    p.write_text(MULTI_MOVE_SGF, encoding="utf-8")
    return p


@pytest.fixture
def small_cfg() -> RenderConfig:
    """Small cell size for fast tests."""
    return RenderConfig(cell_size=24, padding=12, show_coordinates=False)


# ---------------------------------------------------------------------------
# Renderer tests
# ---------------------------------------------------------------------------

class TestBoardRenderer:
    def test_render_empty_board(self, small_cfg: RenderConfig) -> None:
        renderer = BoardRenderer(9, small_cfg)
        img = renderer.render(set(), set())
        assert isinstance(img, Image.Image)
        assert img.mode == "RGB"
        assert img.width == img.height  # square

    def test_render_with_stones(self, small_cfg: RenderConfig) -> None:
        renderer = BoardRenderer(9, small_cfg)
        black = {(2, 2), (3, 2), (4, 2)}
        white = {(2, 3), (3, 3), (4, 3)}
        img = renderer.render(black, white)
        assert img.width > 0

    def test_render_with_moves(self, small_cfg: RenderConfig) -> None:
        renderer = BoardRenderer(9, small_cfg)
        black = {(2, 2)}
        white = {(2, 3)}
        moves = [("B", 4, 4), ("W", 5, 5)]
        img = renderer.render(black, white, moves)
        assert img.width > 0

    def test_render_frames_count(self, small_cfg: RenderConfig) -> None:
        renderer = BoardRenderer(9, small_cfg)
        moves = [("B", 4, 4), ("W", 5, 5), ("B", 6, 6)]
        frames = renderer.render_frames(set(), set(), moves)
        # Frame 0 (setup) + 3 move frames = 4
        assert len(frames) == 4

    def test_different_board_sizes(self, small_cfg: RenderConfig) -> None:
        for size in (9, 13, 19):
            renderer = BoardRenderer(size, small_cfg)
            img = renderer.render(set(), set())
            assert img.width == img.height

    def test_render_with_coordinates(self) -> None:
        cfg = RenderConfig(cell_size=24, padding=12, show_coordinates=True)
        renderer = BoardRenderer(9, cfg)
        img = renderer.render(set(), set())
        assert img.width > 0

    def test_high_resolution(self) -> None:
        cfg = RenderConfig(cell_size=96)
        renderer = BoardRenderer(19, cfg)
        img = renderer.render(set(), set())
        # At 96px/cell, 19x19 should be > 1700px
        assert img.width > 1700


# ---------------------------------------------------------------------------
# Exporter tests — PNG
# ---------------------------------------------------------------------------

class TestExportPng:
    def test_puzzle_state_default(
        self, simple_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "puzzle.png"
        result = export_png(simple_sgf_file, out, config=small_cfg)
        assert result == out
        assert out.exists()
        img = Image.open(out)
        assert img.format == "PNG"

    def test_solution_state(
        self, simple_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "solution.png"
        result = export_png(simple_sgf_file, out, solution=True, config=small_cfg)
        assert result == out
        assert out.exists()
        # Solution PNG should be different from puzzle PNG
        puzzle_out = tmp_path / "puzzle.png"
        export_png(simple_sgf_file, puzzle_out, solution=False, config=small_cfg)
        assert out.stat().st_size != puzzle_out.stat().st_size

    def test_multi_move_solution(
        self, multi_move_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "multi_sol.png"
        export_png(multi_move_sgf_file, out, solution=True, config=small_cfg)
        assert out.exists()


# ---------------------------------------------------------------------------
# Exporter tests — GIF
# ---------------------------------------------------------------------------

class TestExportGif:
    def test_basic_gif(
        self, simple_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "test.gif"
        result = export_gif(simple_sgf_file, out, config=small_cfg)
        assert result == out
        assert out.exists()
        img = Image.open(out)
        assert img.format == "GIF"
        # Should have multiple frames
        assert img.n_frames >= 2

    def test_multi_move_gif(
        self, multi_move_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "multi.gif"
        export_gif(multi_move_sgf_file, out, config=small_cfg)
        img = Image.open(out)
        # 3 moves + 1 setup frame = 4 frames
        assert img.n_frames == 4

    def test_gif_loops(
        self, simple_sgf_file: Path, tmp_path: Path, small_cfg: RenderConfig,
    ) -> None:
        out = tmp_path / "loop.gif"
        export_gif(simple_sgf_file, out, config=small_cfg, loop=0)
        assert out.exists()
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCli:
    def test_png_cli(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        from tools.sgf2img.__main__ import main

        out = str(tmp_path / "cli_test.png")
        rc = main(["png", "--sgf", str(simple_sgf_file), "--output", out, "--cell-size", "24", "--no-coords", "--theme", "none"])
        assert rc == 0
        assert Path(out).exists()

    def test_png_cli_inferred_output(
        self, simple_sgf_file: Path,
    ) -> None:
        """Output inferred from input filename when --output omitted."""
        from tools.sgf2img.__main__ import main

        rc = main(["png", "--sgf", str(simple_sgf_file), "--cell-size", "24", "--no-coords", "--theme", "none"])
        assert rc == 0
        inferred = simple_sgf_file.with_suffix(".png")
        assert inferred.exists()
        inferred.unlink()  # cleanup

    def test_png_cli_no_solution(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        from tools.sgf2img.__main__ import main

        out = str(tmp_path / "no_sol.png")
        rc = main(["png", "--sgf", str(simple_sgf_file), "--output", out, "--no-solution", "--cell-size", "24", "--theme", "none"])
        assert rc == 0
        assert Path(out).exists()

    def test_gif_cli(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        from tools.sgf2img.__main__ import main

        out = str(tmp_path / "cli_test.gif")
        rc = main(["gif", "--sgf", str(simple_sgf_file), "--output", out, "--cell-size", "24", "--theme", "none"])
        assert rc == 0
        assert Path(out).exists()

    def test_both_cli(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        from tools.sgf2img.__main__ import main

        out_dir = str(tmp_path / "both_out")
        rc = main(["both", "--sgf", str(simple_sgf_file), "--output-dir", out_dir, "--cell-size", "24", "--theme", "none"])
        assert rc == 0
        d = Path(out_dir)
        assert (d / "simple.png").exists()
        assert (d / "simple.gif").exists()

    def test_both_cli_no_solution(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        from tools.sgf2img.__main__ import main

        out_dir = str(tmp_path / "both_nosol")
        rc = main(["both", "--sgf", str(simple_sgf_file), "--output-dir", out_dir, "--no-solution", "--cell-size", "24", "--theme", "none"])
        assert rc == 0
        d = Path(out_dir)
        assert (d / "simple.png").exists()
        assert (d / "simple.gif").exists()


# ---------------------------------------------------------------------------
# Theme tests
# ---------------------------------------------------------------------------

class TestStoneTheme:
    def test_besogo_theme_factory(self) -> None:
        theme = besogo_theme()
        assert len(theme.black_stones) >= 1
        assert len(theme.white_stones) >= 1
        assert theme.board_texture is not None
        assert theme.board_texture.exists()

    def test_empty_theme_fallback(self) -> None:
        """Empty theme (no assets) should fall back to drawn circles."""
        theme = StoneTheme()
        cfg = RenderConfig(cell_size=24, padding=12, show_coordinates=False, theme=theme)
        renderer = BoardRenderer(9, cfg)
        img = renderer.render({(2, 2)}, {(3, 3)})
        assert img.width > 0

    def test_themed_renderer_with_besogo(self) -> None:
        theme = besogo_theme()
        cfg = RenderConfig(cell_size=36, padding=12, show_coordinates=False, theme=theme)
        renderer = BoardRenderer(9, cfg)
        black = {(2, 2), (3, 2), (4, 2)}
        white = {(2, 3), (3, 3), (4, 3)}
        img = renderer.render(black, white)
        assert img.width > 0

    def test_themed_with_moves(self) -> None:
        theme = besogo_theme()
        cfg = RenderConfig(cell_size=36, padding=12, show_coordinates=False, theme=theme)
        renderer = BoardRenderer(9, cfg)
        moves = [("B", 4, 4), ("W", 5, 5)]
        img = renderer.render(set(), set(), moves)
        assert img.width > 0

    def test_themed_png_export(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        theme = besogo_theme()
        cfg = RenderConfig(cell_size=36, padding=12, theme=theme)
        out = tmp_path / "themed.png"
        export_png(simple_sgf_file, out, solution=True, config=cfg)
        assert out.exists()
        # Themed PNG should be larger than flat due to texture detail
        flat_out = tmp_path / "flat.png"
        flat_cfg = RenderConfig(cell_size=36, padding=12)
        export_png(simple_sgf_file, flat_out, solution=True, config=flat_cfg)
        assert out.stat().st_size > flat_out.stat().st_size

    def test_themed_gif_export(
        self, simple_sgf_file: Path, tmp_path: Path,
    ) -> None:
        theme = besogo_theme()
        cfg = RenderConfig(cell_size=36, padding=12, theme=theme)
        out = tmp_path / "themed.gif"
        export_gif(simple_sgf_file, out, config=cfg)
        assert out.exists()
        img = Image.open(out)
        assert img.n_frames >= 2

    def test_custom_theme_from_directory(self, tmp_path: Path) -> None:
        """Custom theme with synthetic assets."""
        # Create tiny synthetic stone images
        for i in range(2):
            b = Image.new("RGBA", (32, 32), (30, 30, 30, 255))
            b.save(tmp_path / f"black{i}.png")
            w = Image.new("RGBA", (32, 32), (235, 235, 230, 255))
            w.save(tmp_path / f"white{i}.png")
        # Create a tiny board texture
        board = Image.new("RGB", (64, 64), (214, 171, 106))
        board.save(tmp_path / "board.jpg")

        theme = StoneTheme(
            black_stones=sorted(tmp_path.glob("black*.png")),
            white_stones=sorted(tmp_path.glob("white*.png")),
            board_texture=tmp_path / "board.jpg",
        )
        cfg = RenderConfig(cell_size=24, padding=8, theme=theme)
        renderer = BoardRenderer(9, cfg)
        img = renderer.render({(1, 1)}, {(2, 2)}, [("B", 3, 3)])
        assert img.width > 0

    def test_theme_cli(self, simple_sgf_file: Path, tmp_path: Path) -> None:
        from tools.sgf2img.__main__ import main

        out = str(tmp_path / "cli_themed.png")
        rc = main([
            "png", "--sgf", str(simple_sgf_file), "--output", out,
            "--cell-size", "36", "--theme", "besogo",
        ])
        assert rc == 0
        assert Path(out).exists()
