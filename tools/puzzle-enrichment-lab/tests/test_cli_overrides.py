"""Tests for P.2 CLI override args: --visits, --symmetries, --num-puzzles.

All tests are unit tests (no KataGo required). Verifies that:
  - _apply_cli_overrides() patches config fields in-place
  - --visits / --symmetries are wired into enrich, validate, batch parsers
  - --num-puzzles slices the SGF list in batch mode

Covers plan section: Task 1 (CLI Configurability).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_LAB_DIR = Path(__file__).resolve().parent.parent

from cli import _apply_cli_overrides, build_parser, run_batch
from config import load_enrichment_config

# ---------------------------------------------------------------------------
# _apply_cli_overrides unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVisitsOverride:
    """_apply_cli_overrides patches config fields when values are provided."""

    def _config(self):
        return load_enrichment_config()

    def test_visits_sets_deep_enrich(self):
        """--visits N sets config.deep_enrich.visits to N."""
        cfg = self._config()
        original = cfg.deep_enrich.visits
        _apply_cli_overrides(cfg, visits=200, symmetries=None)
        assert cfg.deep_enrich.visits == 200
        assert cfg.deep_enrich.visits != original or original == 200

    def test_visits_sets_analysis_defaults(self):
        """--visits N also updates config.analysis_defaults.default_max_visits."""
        cfg = self._config()
        _apply_cli_overrides(cfg, visits=300, symmetries=None)
        assert cfg.analysis_defaults.default_max_visits == 300

    def test_symmetries_sets_deep_enrich(self):
        """--symmetries N sets config.deep_enrich.root_num_symmetries_to_sample to N."""
        cfg = self._config()
        _apply_cli_overrides(cfg, visits=None, symmetries=4)
        assert cfg.deep_enrich.root_num_symmetries_to_sample == 4

    def test_no_override_preserves_config(self):
        """Passing None for both visits and symmetries leaves config unchanged."""
        cfg = self._config()
        expected_visits = cfg.deep_enrich.visits
        expected_sym = cfg.deep_enrich.root_num_symmetries_to_sample
        _apply_cli_overrides(cfg, visits=None, symmetries=None)
        assert cfg.deep_enrich.visits == expected_visits
        assert cfg.deep_enrich.root_num_symmetries_to_sample == expected_sym

    def test_visits_override_independent_from_symmetries(self):
        """Setting only visits does not change symmetries."""
        cfg = self._config()
        expected_sym = cfg.deep_enrich.root_num_symmetries_to_sample
        _apply_cli_overrides(cfg, visits=500, symmetries=None)
        assert cfg.deep_enrich.root_num_symmetries_to_sample == expected_sym


# ---------------------------------------------------------------------------
# Parser wiring tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVisitsArgParsing:
    """Parser correctly wires --visits and --symmetries for enrich/validate/batch."""

    def test_enrich_accepts_visits(self):
        """`enrich` subcommand accepts --visits N."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "puzzle.sgf",
            "--output", "out.json",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--visits", "200",
        ])
        assert args.visits == 200

    def test_enrich_accepts_symmetries(self):
        """`enrich` subcommand accepts --symmetries N."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "puzzle.sgf",
            "--output", "out.json",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--symmetries", "4",
        ])
        assert args.symmetries == 4

    def test_validate_accepts_visits(self):
        """`validate` subcommand accepts --visits N."""
        parser = build_parser()
        args = parser.parse_args([
            "validate",
            "--sgf", "puzzle.sgf",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--visits", "500",
        ])
        assert args.visits == 500

    def test_validate_accepts_symmetries(self):
        """`validate` subcommand accepts --symmetries N."""
        parser = build_parser()
        args = parser.parse_args([
            "validate",
            "--sgf", "puzzle.sgf",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--symmetries", "2",
        ])
        assert args.symmetries == 2

    def test_batch_accepts_visits(self):
        """`batch` subcommand accepts --visits N."""
        parser = build_parser()
        args = parser.parse_args([
            "batch",
            "--input-dir", "sgf_dir/",
            "--output-dir", "out_dir/",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--visits", "1000",
        ])
        assert args.visits == 1000

    def test_batch_accepts_num_puzzles(self):
        """`batch` subcommand accepts --num-puzzles N."""
        parser = build_parser()
        args = parser.parse_args([
            "batch",
            "--input-dir", "sgf_dir/",
            "--output-dir", "out_dir/",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
            "--num-puzzles", "5",
        ])
        assert args.num_puzzles == 5

    def test_visits_default_is_none(self):
        """--visits defaults to None (meaning: use config value)."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "puzzle.sgf",
            "--output", "out.json",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
        ])
        assert args.visits is None

    def test_num_puzzles_default_is_none(self):
        """--num-puzzles defaults to None (meaning: process all)."""
        parser = build_parser()
        args = parser.parse_args([
            "batch",
            "--input-dir", "sgf_dir/",
            "--output-dir", "out_dir/",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/model.bin.gz",
        ])
        assert args.num_puzzles is None


# ---------------------------------------------------------------------------
# --num-puzzles batch slicing tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNumPuzzlesBatch:
    """--num-puzzles stops batch after N files."""

    def _make_sgf_files(self, tmp_path: Path, count: int) -> list[Path]:
        """Create N minimal SGF files in tmp_path."""
        files = []
        for i in range(count):
            f = tmp_path / f"puzzle_{i:03d}.sgf"
            f.write_text(f"(;GM[1]FF[4]SZ[9]AB[aa]AW[ab];B[ac]C[Correct.])  ; puzzle {i}", encoding="utf-8")
            files.append(f)
        return files

    def test_num_puzzles_limits_to_one(self, tmp_path):
        """--num-puzzles 1 processes only the first file."""
        self._make_sgf_files(tmp_path, 5)
        processed = []

        async def mock_enrich(sgf_text, engine_manager, config, source_file="", run_id=""):
            processed.append(source_file)
            from analyzers.validate_correct_move import ValidationStatus
            from models.ai_analysis_result import (
                AI_ANALYSIS_SCHEMA_VERSION,
                AiAnalysisResult,
                DifficultySnapshot,
                MoveValidation,
            )
            return AiAnalysisResult(
                schema_version=AI_ANALYSIS_SCHEMA_VERSION,
                puzzle_id="test",
                validation=MoveValidation(
                    status=ValidationStatus.ACCEPTED,
                    flags=[],
                    correct_move_gtp="A1",
                    katago_top_move_gtp="A1",
                    katago_agrees=True,
                    correct_move_winrate=0.9,
                    correct_move_policy=0.5,
                    validator_used="life_and_death",
                ),
                refutations=[],
                difficulty=DifficultySnapshot(
                    policy_prior_correct=0.5,
                    visits_to_solve=50,
                    composite_score=30.0,
                    suggested_level="novice",
                    suggested_level_id=110,
                    confidence="medium",
                ),
            )

        with (
            patch("cli.load_enrichment_config", return_value=load_enrichment_config()),
            patch("cli.SingleEngineManager") as mock_dm_cls,
            patch("cli.enrich_single_puzzle", side_effect=mock_enrich),
            patch("cli.enrich_sgf", return_value="(;GM[1])"),
        ):
            mock_dm = MagicMock()
            mock_dm.start = AsyncMock()
            mock_dm.shutdown = AsyncMock()
            mock_dm_cls.return_value = mock_dm

            run_batch(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                katago_path="/fake/katago",
                quick_model_path="/fake/model.bin.gz",
                referee_model_path="",
                config_path=None,
                num_puzzles=1,
            )

        assert len(processed) == 1

    def test_num_puzzles_zero_processes_all(self, tmp_path):
        """--num-puzzles 0 (falsy) processes all files."""
        self._make_sgf_files(tmp_path, 3)
        processed = []

        async def mock_enrich(sgf_text, engine_manager, config, source_file="", run_id=""):
            processed.append(source_file)
            from analyzers.validate_correct_move import ValidationStatus
            from models.ai_analysis_result import (
                AI_ANALYSIS_SCHEMA_VERSION,
                AiAnalysisResult,
                DifficultySnapshot,
                MoveValidation,
            )
            return AiAnalysisResult(
                schema_version=AI_ANALYSIS_SCHEMA_VERSION,
                puzzle_id="test",
                validation=MoveValidation(
                    status=ValidationStatus.ACCEPTED,
                    flags=[],
                    correct_move_gtp="A1",
                    katago_top_move_gtp="A1",
                    katago_agrees=True,
                    correct_move_winrate=0.9,
                    correct_move_policy=0.5,
                    validator_used="life_and_death",
                ),
                refutations=[],
                difficulty=DifficultySnapshot(
                    policy_prior_correct=0.5,
                    visits_to_solve=50,
                    composite_score=30.0,
                    suggested_level="novice",
                    suggested_level_id=110,
                    confidence="medium",
                ),
            )

        with (
            patch("cli.load_enrichment_config", return_value=load_enrichment_config()),
            patch("cli.SingleEngineManager") as mock_dm_cls,
            patch("cli.enrich_single_puzzle", side_effect=mock_enrich),
            patch("cli.enrich_sgf", return_value="(;GM[1])"),
        ):
            mock_dm = MagicMock()
            mock_dm.start = AsyncMock()
            mock_dm.shutdown = AsyncMock()
            mock_dm_cls.return_value = mock_dm

            run_batch(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                katago_path="/fake/katago",
                quick_model_path="/fake/model.bin.gz",
                referee_model_path="",
                config_path=None,
                num_puzzles=0,
            )

        assert len(processed) == 3
