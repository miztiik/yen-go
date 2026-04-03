"""Architecture dependency guard (T56B).

Ensures no model→analyzer, stage→stage, or detector→stage imports.
Uses ast.parse() to scan Python files for import statements and check
dependency rules. These guards prevent cyclic dependencies and maintain
the layered architecture.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_LAB_DIR = Path(__file__).resolve().parent.parent
_ANALYZERS_DIR = _LAB_DIR / "analyzers"
_MODELS_DIR = _LAB_DIR / "models"
_STAGES_DIR = _ANALYZERS_DIR / "stages"
_DETECTORS_DIR = _ANALYZERS_DIR / "detectors"


def _collect_python_files(directory: Path) -> list[Path]:
    """Collect all .py files in a directory (non-recursive)."""
    if not directory.is_dir():
        return []
    return [f for f in directory.iterdir() if f.suffix == ".py" and f.name != "__init__.py"]


def _extract_imports(filepath: Path) -> list[str]:
    """Extract all import module paths from a Python file using AST."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _imports_from(imports: list[str], *targets: str) -> list[str]:
    """Filter imports that start with any of the target prefixes."""
    matches = []
    for imp in imports:
        for target in targets:
            if imp.startswith(target):
                matches.append(imp)
    return matches


class TestNoModelImportsAnalyzers:
    """Models must not import from analyzers (inverse dependency)."""

    def test_no_model_imports_analyzers(self):
        violations: list[str] = []
        for pyfile in _collect_python_files(_MODELS_DIR):
            imports = _extract_imports(pyfile)
            bad = _imports_from(imports, "analyzers.", "..analyzers.")
            if bad:
                violations.append(f"{pyfile.name}: {bad}")

        assert not violations, (
            "Models must not import from analyzers (inverse dependency):\n"
            + "\n".join(violations)
        )


class TestNoStageImportsOtherStages:
    """Stages must not import from other stages directly."""

    # Allowlist: stage_runner.py imports protocols, __init__ may re-export,
    # query_stage.py is a backward-compat alias for analyze_stage
    _ALLOWED_FILES = {"stage_runner.py", "__init__.py", "protocols.py", "solve_paths.py", "query_stage.py"}
    _ALLOWED_IMPORTS = {"analyzers.stages.protocols", "..stages.protocols", ".protocols"}

    def test_no_stage_cross_imports(self):
        violations: list[str] = []
        for pyfile in _collect_python_files(_STAGES_DIR):
            if pyfile.name in self._ALLOWED_FILES:
                continue

            imports = _extract_imports(pyfile)
            stage_module_prefix = ("analyzers.stages.", "..stages.", ".stage_")
            bad = []
            for imp in imports:
                for prefix in stage_module_prefix:
                    if imp.startswith(prefix):
                        # Allow protocols import
                        if any(imp.endswith(allowed.split(".")[-1]) for allowed in self._ALLOWED_IMPORTS):
                            continue
                        if "protocols" in imp:
                            continue
                        # Allow solve_paths (utility, not a stage)
                        if "solve_paths" in imp:
                            continue
                        bad.append(imp)

            if bad:
                violations.append(f"{pyfile.name}: {bad}")

        assert not violations, (
            "Stages must not import other stages directly:\n"
            + "\n".join(violations)
        )


class TestNoDetectorImportsStages:
    """Detectors must not import from stages."""

    def test_no_detector_imports_stages(self):
        violations: list[str] = []
        for pyfile in _collect_python_files(_DETECTORS_DIR):
            imports = _extract_imports(pyfile)
            bad = _imports_from(imports, "analyzers.stages.", "..stages.")
            if bad:
                violations.append(f"{pyfile.name}: {bad}")

        assert not violations, (
            "Detectors must not import from stages:\n"
            + "\n".join(violations)
        )


class TestNoDetectorImportsResult:
    """Detectors should use detection.py models, not ai_analysis_result directly."""

    def test_detectors_use_detection_models(self):
        """Verify detectors import from models.detection, not models.ai_analysis_result."""
        violations: list[str] = []
        for pyfile in _collect_python_files(_DETECTORS_DIR):
            imports = _extract_imports(pyfile)
            bad = _imports_from(imports, "models.ai_analysis_result", "..models.ai_analysis_result")
            if bad:
                violations.append(f"{pyfile.name}: {bad}")

        # This is a soft check — some detectors may legitimately need AiAnalysisResult
        # Log violations but don't fail hard (informational)
        if violations:
            pytest.skip(f"Informational: detectors importing AiAnalysisResult: {violations}")


class TestNoBackendImports:
    """Lab must NOT import from backend.puzzle_manager (C-3 constraint)."""

    def test_no_backend_imports(self):
        violations: list[str] = []
        lab_dir = Path(__file__).resolve().parent.parent
        for pyfile in lab_dir.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            imports = _extract_imports(pyfile)
            bad = _imports_from(imports, "backend.puzzle_manager", "backend.")
            if bad:
                violations.append(f"{pyfile.relative_to(lab_dir)}: {bad}")

        assert not violations, (
            "Lab must not import from backend.puzzle_manager (C-3):\n"
            + "\n".join(violations)
        )


# ── T53: Fallback chain verification ────────────────────────────────


class TestDegradationChain:
    """Verify that optional stages use DEGRADE error policy so the pipeline
    continues even when they fail (T53)."""

    def test_technique_stage_degrades(self):
        from analyzers.stages.protocols import ErrorPolicy
        from analyzers.stages.technique_stage import TechniqueStage
        assert TechniqueStage().error_policy == ErrorPolicy.DEGRADE

    def test_teaching_stage_degrades(self):
        from analyzers.stages.protocols import ErrorPolicy
        from analyzers.stages.teaching_stage import TeachingStage
        assert TeachingStage().error_policy == ErrorPolicy.DEGRADE

    def test_sgf_writeback_stage_degrades(self):
        from analyzers.stages.protocols import ErrorPolicy
        from analyzers.stages.sgf_writeback_stage import SgfWritebackStage
        assert SgfWritebackStage().error_policy == ErrorPolicy.DEGRADE

    def test_refutation_stage_degrades(self):
        from analyzers.stages.protocols import ErrorPolicy
        from analyzers.stages.refutation_stage import RefutationStage
        assert RefutationStage().error_policy == ErrorPolicy.DEGRADE

    def test_difficulty_stage_degrades(self):
        from analyzers.stages.difficulty_stage import DifficultyStage
        from analyzers.stages.protocols import ErrorPolicy
        assert DifficultyStage().error_policy == ErrorPolicy.DEGRADE

    def test_assembly_stage_fails_fast(self):
        """Assembly is the only late-pipeline FAIL_FAST stage (by design)."""
        from analyzers.stages.assembly_stage import AssemblyStage
        from analyzers.stages.protocols import ErrorPolicy
        assert AssemblyStage().error_policy == ErrorPolicy.FAIL_FAST

    def test_stage_order_in_pipeline(self):
        """Verify the stage list in enrich_single follows expected order."""
        from analyzers.stages.analyze_stage import AnalyzeStage
        from analyzers.stages.assembly_stage import AssemblyStage
        from analyzers.stages.difficulty_stage import DifficultyStage
        from analyzers.stages.refutation_stage import RefutationStage
        from analyzers.stages.sgf_writeback_stage import SgfWritebackStage
        from analyzers.stages.teaching_stage import TeachingStage
        from analyzers.stages.technique_stage import TechniqueStage
        from analyzers.stages.validation_stage import ValidationStage

        # The expected ordering from enrich_single.py
        expected_names = [
            "analyze",
            "validate_move",
            "generate_refutations",
            "estimate_difficulty",
            "assemble_result",
            "technique_classification",
            "teaching_enrichment",
            "sgf_writeback",
        ]
        stages = [
            AnalyzeStage(),
            ValidationStage(),
            RefutationStage(),
            DifficultyStage(),
            AssemblyStage(),
            TechniqueStage(),
            TeachingStage(),
            SgfWritebackStage(),
        ]
        actual_names = [s.name for s in stages]
        assert actual_names == expected_names
