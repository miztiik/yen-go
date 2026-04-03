"""Tests for Task A.5.3: CLI entry point.

Tests the argparse-based CLI for the enrichment lab:
    - Subcommands: enrich, apply, validate, batch
  - Exit codes: 0=accepted, 1=error, 2=flagged
  - Config override: --config custom.json
  - Batch mode: sequential loop over directory

All tests are unit tests that mock engine/enrichment internals.
Only test_help_output uses subprocess (validates --help flag).
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from analyzers.validate_correct_move import ValidationStatus
from cli import build_parser, main, run_apply, run_batch, run_enrich, run_validate
from config import load_enrichment_config
from models.ai_analysis_result import (
    AI_ANALYSIS_SCHEMA_VERSION,
    AiAnalysisResult,
    DifficultySnapshot,
    MoveValidation,
)


def _make_test_config():
    """Return a deep copy of the real EnrichmentConfig for test isolation.

    Uses the production config (config/katago-enrichment.json) so all
    downstream code — compute_config_hash, _resolve_model_path,
    _apply_cli_overrides — works against a real Pydantic model.
    Deep copy prevents cross-test mutation from _apply_cli_overrides.
    """
    return load_enrichment_config().model_copy(deep=True)

# ---------------------------------------------------------------------------
# Fixture: minimal SGF for testing
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_SIMPLE_SGF = _FIXTURE_DIR / "simple_life_death.sgf"


def _make_result(status: ValidationStatus = ValidationStatus.ACCEPTED, flags: list[str] | None = None) -> AiAnalysisResult:
    """Create a minimal AiAnalysisResult with given status."""
    return AiAnalysisResult(
        schema_version=AI_ANALYSIS_SCHEMA_VERSION,
        puzzle_id="test-puzzle-001",
        validation=MoveValidation(
            status=status,
            flags=flags or [],
            correct_move_gtp="D4",
            katago_top_move_gtp="D4",
            katago_agrees=(status == ValidationStatus.ACCEPTED),
            correct_move_winrate=0.85,
            correct_move_policy=0.3,
            validator_used="life_and_death",
        ),
        refutations=[],
        difficulty=DifficultySnapshot(
            policy_prior_correct=0.3,
            visits_to_solve=100,
            composite_score=50.0,
            suggested_level="intermediate",
            suggested_level_id=140,
            confidence="medium",
        ),
    )


# ===========================================================================
# Parser tests
# ===========================================================================

@pytest.mark.unit
class TestBuildParser:
    """Test that the argparse parser is correctly constructed."""

    def test_help_output(self):
        """--help flag should be recognized by parser."""
        parser = build_parser()
        # argparse raises SystemExit(0) on --help
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_enrich_subcommand_args(self):
        """'enrich' subcommand accepts --sgf and --output."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--output", "result.json",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/quick.bin.gz",
        ])
        assert args.command == "enrich"
        assert args.sgf == "input.sgf"
        assert args.output == "result.json"

    def test_validate_subcommand_args(self):
        """'validate' subcommand accepts --sgf."""
        parser = build_parser()
        args = parser.parse_args([
            "validate",
            "--sgf", "input.sgf",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/quick.bin.gz",
        ])
        assert args.command == "validate"
        assert args.sgf == "input.sgf"

    def test_apply_subcommand_args(self):
        """'apply' subcommand accepts --sgf, --result, and --output."""
        parser = build_parser()
        args = parser.parse_args([
            "apply",
            "--sgf", "input.sgf",
            "--result", "result.json",
            "--output", "enriched.sgf",
        ])
        assert args.command == "apply"
        assert args.sgf == "input.sgf"
        assert args.result == "result.json"
        assert args.output == "enriched.sgf"

    def test_batch_subcommand_args(self):
        """'batch' subcommand accepts --input-dir and --output-dir."""
        parser = build_parser()
        args = parser.parse_args([
            "batch",
            "--input-dir", "sgf_dir/",
            "--output-dir", "output_dir/",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/quick.bin.gz",
        ])
        assert args.command == "batch"
        assert args.input_dir == "sgf_dir/"
        assert args.output_dir == "output_dir/"

    def test_config_override_arg(self):
        """--config overrides default config path."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--output", "result.json",
            "--config", "custom.json",
            "--katago", "/path/to/katago",
            "--quick-model", "/path/to/quick.bin.gz",
        ])
        assert args.config == "custom.json"


# ===========================================================================
# Exit code tests (mock the enrichment pipeline)
# ===========================================================================

@pytest.mark.unit
class TestExitCodes:
    """Test exit codes from the enrich subcommand."""

    def test_exit_code_0_on_accepted(self, tmp_path):
        """Successful enrichment with ACCEPTED status → exit code 0."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")
        output_file = tmp_path / "result.json"

        result = _make_result(ValidationStatus.ACCEPTED)

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_enrich(
                sgf_path=str(sgf_file),
                output_path=str(output_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 0

    def test_exit_code_1_on_error(self, tmp_path):
        """Enrichment failure (REJECTED with error flags) → exit code 1."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")
        output_file = tmp_path / "result.json"

        result = _make_result(ValidationStatus.REJECTED, flags=["SGF parse failure"])

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_enrich(
                sgf_path=str(sgf_file),
                output_path=str(output_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 1

    def test_exit_code_2_on_flagged(self, tmp_path):
        """Flagged result → exit code 2."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")
        output_file = tmp_path / "result.json"

        result = _make_result(ValidationStatus.FLAGGED)

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_enrich(
                sgf_path=str(sgf_file),
                output_path=str(output_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 2

    def test_missing_sgf_file_error(self, tmp_path):
        """Non-existent SGF file → exit code 1."""
        output_file = tmp_path / "result.json"
        code = run_enrich(
            sgf_path=str(tmp_path / "nonexistent.sgf"),
            output_path=str(output_file),
            katago_path="/path/to/katago",
            quick_model_path="/path/to/quick.bin.gz",
            referee_model_path="",
            config_path=None,
        )
        assert code == 1


# ===========================================================================
# Validate subcommand tests
# ===========================================================================

@pytest.mark.unit
class TestRunValidate:
    """Test the validate subcommand logic."""

    def test_validate_accepted(self, tmp_path):
        """validate with ACCEPTED result → exit code 0."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")

        result = _make_result(ValidationStatus.ACCEPTED)

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_validate(
                sgf_path=str(sgf_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 0

    def test_validate_rejected(self, tmp_path):
        """validate with REJECTED result → exit code 1."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")

        result = _make_result(ValidationStatus.REJECTED, flags=["not in top-N"])

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_validate(
                sgf_path=str(sgf_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 1


# ===========================================================================
# Apply subcommand tests
# ===========================================================================

@pytest.mark.unit
class TestRunApply:
    """Test the apply subcommand logic."""

    def test_apply_success(self, tmp_path):
        """apply with valid SGF + result JSON writes enriched SGF and returns 0."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")
        result_file = tmp_path / "result.json"
        output_file = tmp_path / "enriched.sgf"

        result = _make_result(ValidationStatus.ACCEPTED)
        result_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        with patch("cli.enrich_sgf", return_value="(;FF[4]GM[1]SZ[19]YG[intermediate];B[cc])"):
            code = run_apply(
                sgf_path=str(sgf_file),
                result_path=str(result_file),
                output_path=str(output_file),
            )

        assert code == 0
        assert output_file.exists()

    def test_apply_missing_result_file(self, tmp_path):
        """apply with missing result JSON returns exit code 1."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")

        code = run_apply(
            sgf_path=str(sgf_file),
            result_path=str(tmp_path / "missing.json"),
            output_path=str(tmp_path / "enriched.sgf"),
        )

        assert code == 1


# ===========================================================================
# Batch subcommand tests
# ===========================================================================

@pytest.mark.unit
class TestRunBatch:
    """Test the batch subcommand logic."""

    def test_batch_processes_all_sgfs(self, tmp_path):
        """batch mode iterates over all .sgf files in input-dir."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create 3 SGF files
        for i in range(3):
            (input_dir / f"puzzle_{i}.sgf").write_text(
                "(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8"
            )

        result = _make_result(ValidationStatus.ACCEPTED)

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result) as mock_enrich, \
             patch("cli.enrich_sgf", return_value="(;FF[4]GM[1]SZ[19]AB[dd]YG[intermediate];B[cc])"), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_batch(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        assert code == 0
        assert mock_enrich.call_count == 3
        # Verify output files created
        output_sgfs = list(output_dir.glob("*.sgf"))
        assert len(output_sgfs) == 3

    def test_batch_empty_dir(self, tmp_path):
        """batch with no .sgf files → exit code 0 (nothing to do)."""
        input_dir = tmp_path / "empty_input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        code = run_batch(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            katago_path="/path/to/katago",
            quick_model_path="/path/to/quick.bin.gz",
            referee_model_path="",
            config_path=None,
        )
        assert code == 0

    def test_batch_partial_failure(self, tmp_path):
        """batch with one failure → still processes remaining, returns exit code 1."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create 2 SGF files
        (input_dir / "good.sgf").write_text(
            "(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8"
        )
        (input_dir / "bad.sgf").write_text(
            "(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8"
        )

        accepted = _make_result(ValidationStatus.ACCEPTED)
        rejected = _make_result(ValidationStatus.REJECTED, flags=["error"])

        # First call succeeds, second fails
        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, side_effect=[accepted, rejected]), \
             patch("cli.enrich_sgf", return_value="(;FF[4]GM[1]SZ[19]YG[intermediate];B[cc])"), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()):
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_batch(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=None,
            )

        # Exit code 1 because at least one puzzle was rejected
        assert code == 1


# ===========================================================================
# Config override test
# ===========================================================================

@pytest.mark.unit
class TestConfigOverride:
    """Test --config flag integration."""

    def test_config_override_loads_custom(self, tmp_path):
        """--config custom.json → load_enrichment_config called with custom path."""
        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")
        output_file = tmp_path / "result.json"
        config_file = tmp_path / "custom.json"
        config_file.write_text("{}", encoding="utf-8")

        result = _make_result(ValidationStatus.ACCEPTED)

        with patch("cli.enrich_single_puzzle", new_callable=AsyncMock, return_value=result), \
             patch("cli.SingleEngineManager") as mock_mgr_cls, \
             patch("cli.load_enrichment_config", return_value=_make_test_config()) as mock_load_config:
            mock_mgr = AsyncMock()
            mock_mgr_cls.return_value = mock_mgr
            code = run_enrich(
                sgf_path=str(sgf_file),
                output_path=str(output_file),
                katago_path="/path/to/katago",
                quick_model_path="/path/to/quick.bin.gz",
                referee_model_path="",
                config_path=str(config_file),
            )

        # load_enrichment_config should be called with the custom path
        mock_load_config.assert_called_once_with(Path(str(config_file)))
        assert code == 0


# ===========================================================================
# Main entry point test
# ===========================================================================

@pytest.mark.unit
class TestMainDispatch:
    """Test the main() function dispatches to correct subcommand."""

    def test_main_no_args_shows_help(self, capsys):
        """main() with no args → prints usage, exit code 1."""
        # argparse exits with code 2 when a required subcommand is missing
        with pytest.raises(SystemExit) as exc_info:
            main([])
        # argparse error exits with 2
        assert exc_info.value.code == 2


# ===========================================================================
# RT-1: --gui flag on enrich subcommand
# ===========================================================================

@pytest.mark.unit
class TestGuiFlag:
    """Test that --gui flag is correctly parsed and dispatched."""

    def test_gui_flag_parsed(self):
        """'enrich --gui' is recognized by the parser."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--katago", "/path/to/katago",
            "--gui",
        ])
        assert args.command == "enrich"
        assert args.gui is True
        assert args.output is None  # --output not required with --gui

    def test_gui_flag_with_output(self):
        """'enrich --gui --output ...' is recognized."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--output", "result.json",
            "--katago", "/path/to/katago",
            "--gui",
        ])
        assert args.gui is True
        assert args.output == "result.json"

    def test_gui_flag_host_port(self):
        """--host and --port defaults are correct."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--katago", "/path/to/katago",
            "--gui",
            "--host", "0.0.0.0",
            "--port", "9000",
        ])
        assert args.host == "0.0.0.0"
        assert args.port == 9000

    def test_no_gui_subcommand(self):
        """'gui' is NOT a valid subcommand anymore."""
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["gui", "--katago", "/path/to/katago"])
        assert exc_info.value.code == 2

    def test_output_required_without_gui(self):
        """Without --gui, --output must be provided (dispatcher validates)."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--katago", "/path/to/katago",
        ])
        # Parser allows it (--output defaults to None), but main() should error
        assert args.output is None
        assert getattr(args, "gui", False) is False


# ===========================================================================
# RT-2: Subprocess isolation — gui/ bridge launched as subprocess
# ===========================================================================

@pytest.mark.unit
class TestSubprocessIsolation:
    """Test that --gui uses subprocess.Popen, not direct import."""

    def test_no_gui_import_in_run_enrich(self):
        """run_enrich() does NOT import from gui.bridge."""
        import cli as cli_mod

        # Re-read the source code and verify no 'from gui.bridge import' exists
        source = Path(cli_mod.__file__).read_text(encoding="utf-8")
        assert "from gui.bridge import" not in source

    def test_run_enrich_with_gui_uses_popen(self, tmp_path):
        """_run_enrich_with_gui launches bridge.py via Popen."""
        from cli import _run_enrich_with_gui

        sgf_file = tmp_path / "puzzle.sgf"
        sgf_file.write_text("(;FF[4]GM[1]SZ[19]AB[dd];B[cc])", encoding="utf-8")

        _make_result(ValidationStatus.ACCEPTED)

        # Build a mock namespace mimicking parsed args
        import argparse
        mock_args = argparse.Namespace(
            sgf=str(sgf_file),
            output=str(tmp_path / "result.json"),
            katago="/path/to/katago",
            katago_config="",
            config=None,
            gui=True,
            host="127.0.0.1",
            port=8999,
            quick_only=False,
            visits=None,
            symmetries=None,
            emit_sgf=None,
        )

        with patch("subprocess.Popen") as mock_popen, \
             patch("webbrowser.open") as mock_browser, \
             patch("cli.run_enrich", return_value=0):
            mock_proc = MagicMock()
            mock_popen.return_value = mock_proc

            code = _run_enrich_with_gui(mock_args)

        assert code == 0
        mock_popen.assert_called_once()
        mock_proc.terminate.assert_called()
        mock_browser.assert_called_once()


# ===========================================================================
# T42: Debug export CLI flag and function tests (AC-9)
# ===========================================================================

@pytest.mark.unit
class TestDebugExportFlag:
    """Test --debug-export flag is parsed correctly."""

    def test_debug_export_flag_parsed(self):
        """'enrich --debug-export' is recognized by the parser."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--output", "result.json",
            "--katago", "/path/to/katago",
            "--debug-export",
        ])
        assert args.debug_export is True

    def test_debug_export_flag_default_false(self):
        """--debug-export defaults to False."""
        parser = build_parser()
        args = parser.parse_args([
            "enrich",
            "--sgf", "input.sgf",
            "--output", "result.json",
            "--katago", "/path/to/katago",
        ])
        assert args.debug_export is False


@pytest.mark.unit
class TestDebugExportFunction:
    """Test debug artifact export produces valid JSON."""

    def test_build_debug_artifact_structure(self):
        """build_debug_artifact returns dict with expected keys."""
        from analyzers.debug_export import build_debug_artifact

        result = _make_result(ValidationStatus.ACCEPTED)
        artifact = build_debug_artifact(result, "test-run-001")

        assert "puzzle_id" in artifact
        assert "run_id" in artifact
        assert "trap_moves" in artifact
        assert "detector_matrix" in artifact
        assert artifact["run_id"] == "test-run-001"

    def test_detector_matrix_has_28_entries(self):
        """detector_matrix contains all 28 detector slugs."""
        from analyzers.debug_export import ALL_DETECTOR_SLUGS, build_debug_artifact

        result = _make_result(ValidationStatus.ACCEPTED)
        artifact = build_debug_artifact(result, "test-run")

        assert len(artifact["detector_matrix"]) == 28
        for slug in ALL_DETECTOR_SLUGS:
            assert slug in artifact["detector_matrix"]

    def test_detector_matrix_reflects_technique_tags(self):
        """Detectors in technique_tags show as True in the matrix."""
        from analyzers.debug_export import build_debug_artifact

        result = _make_result(ValidationStatus.ACCEPTED)
        result.technique_tags = ["ladder", "ko", "life-and-death"]

        artifact = build_debug_artifact(result, "test-run")

        assert artifact["detector_matrix"]["ladder"] is True
        assert artifact["detector_matrix"]["ko"] is True
        assert artifact["detector_matrix"]["life-and-death"] is True
        assert artifact["detector_matrix"]["snapback"] is False

    def test_trap_moves_from_refutations(self):
        """trap_moves populated from first 5 refutations."""
        from analyzers.debug_export import build_debug_artifact

        result = _make_result(ValidationStatus.ACCEPTED)
        result.refutations = [
            AiAnalysisResult.model_fields["refutations"].default_factory()[0:0]  # empty list trick
        ]
        # Build with actual refutation entries
        from models.ai_analysis_result import RefutationEntry
        result.refutations = [
            RefutationEntry(wrong_move="cd", delta=-0.3, refutation_pv=["cd", "de"]),
            RefutationEntry(wrong_move="ef", delta=-0.5, refutation_pv=["ef", "fg"]),
        ]

        artifact = build_debug_artifact(result, "test-run")

        assert len(artifact["trap_moves"]) == 2
        assert artifact["trap_moves"][0]["wrong_move"] == "cd"
        assert artifact["trap_moves"][0]["delta"] == -0.3
        assert artifact["trap_moves"][1]["wrong_move"] == "ef"

    def test_export_writes_file(self, tmp_path):
        """export_debug_artifact writes JSON file to disk."""
        from analyzers.debug_export import export_debug_artifact

        result = _make_result(ValidationStatus.ACCEPTED)
        result.puzzle_id = "test-puzzle-42"

        debug_file = export_debug_artifact(
            result, "run-abc", base_dir=str(tmp_path / "debug"),
        )

        assert debug_file.exists()
        assert debug_file.name == "test-puzzle-42.debug.json"

        import json
        data = json.loads(debug_file.read_text(encoding="utf-8"))
        assert data["puzzle_id"] == "test-puzzle-42"
        assert data["run_id"] == "run-abc"
        assert "trap_moves" in data
        assert "detector_matrix" in data
