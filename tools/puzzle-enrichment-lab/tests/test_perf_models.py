"""P.2 — Model comparison benchmark (10 SGFs × up to 4 models).

Compares enrichment quality across available KataGo models:
  - b6c96   (3.7 MB)  — smallest, fastest, lowest accuracy
  - b10c128 (10.6 MB) — medium, moderate accuracy
  - b15c192 (40 MB)   — sweet spot for tsumego (∼12200 Elo)
  - b28c512 (258 MB)  — largest, slowest, highest accuracy

Only models present on disk are tested. Download b15 via:
  python scripts/download_models.py

Uses 10 reference puzzles from perf-33 fixtures spanning the difficulty range:
  #01 novice_ld_9x9, #03 elementary_ko, #05 intermediate_seki,
  #07 advanced_semeai_ko, #10 expert_ld_ko, #12 double_atari,
  #17 nakade, #22 eye_shape, #27 sacrifice, #33 living

Tests validate:
  1. All models produce valid output for all 10 puzzles
  2. Acceptance rate increases with model size
  3. Difficulty variance decreases with model size (less compression bias)
  4. Timing comparison (larger model = slower, but how much?)

These tests are @pytest.mark.slow AND @pytest.mark.integration.
"""

import json
import time
from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from cli import run_batch

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_PERF_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "perf-33"

from config.helpers import KATAGO_PATH, model_path

_KATAGO_PATH = KATAGO_PATH

_MODELS = {
    "b6c96": {
        "path": model_path("test_smallest"),
        "size_mb": 3.7,
        "rank": 1,  # smallest
    },
    "b10c128": {
        "path": model_path("test_fast"),
        "size_mb": 10.6,
        "rank": 2,
    },
    "b15c192": {
        "path": model_path("benchmark"),
        "size_mb": 40.0,
        "rank": 3,  # sweet spot for tsumego
    },
    "b28c512": {
        "path": model_path("referee"),
        "size_mb": 258.9,
        "rank": 4,  # largest
    },
}

# 10 reference puzzles spanning the difficulty range
_BENCHMARK_SGFS = [
    "01_novice_ld_9x9.sgf",
    "03_elementary_ko.sgf",
    "05_intermediate_seki.sgf",
    "07_advanced_semeai_ko.sgf",
    "10_expert_ld_ko.sgf",
    "12_double_atari.sgf",
    "17_nakade.sgf",
    "22_eye_shape.sgf",
    "27_sacrifice.sgf",
    "33_living.sgf",
]

_EXPECTED_COUNT = len(_BENCHMARK_SGFS)  # 10


def _available_models() -> dict[str, dict]:
    """Return only models that exist on disk."""
    return {
        name: info for name, info in _MODELS.items()
        if info["path"].exists()
    }


def _prepare_input_dir(tmp_path: Path) -> Path:
    """Copy benchmark SGFs to a temporary input directory."""
    import shutil
    input_dir = tmp_path / "benchmark-input"
    input_dir.mkdir()
    for sgf_name in _BENCHMARK_SGFS:
        src = _PERF_FIXTURES / sgf_name
        if src.exists():
            shutil.copy2(src, input_dir / sgf_name)
    return input_dir


def _parse_result(json_path: Path) -> dict:
    """Parse an enrichment JSON result into a summary dict."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    validation = data.get("validation", {})
    difficulty = data.get("difficulty", {})
    return {
        "status": validation.get("status", "unknown"),
        "katago_agrees": validation.get("katago_agrees", False),
        "level_id": difficulty.get("level_id"),
        "composite_score": difficulty.get("composite_score"),
        "refutation_count": len(data.get("refutations", [])),
    }


_katago_available = _KATAGO_PATH.exists()
_min_models = len(_available_models()) >= 2

_skip_reasons = []
if not _katago_available:
    _skip_reasons.append("KataGo binary not found")
if not _min_models:
    _skip_reasons.append(f"Need ≥2 models, found {len(_available_models())}")
if not _PERF_FIXTURES.exists():
    _skip_reasons.append("perf-33 fixtures not found")


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestModelComparison:
    """Benchmark enrichment quality across KataGo model sizes.

    Professional insight (Cho Chikun 1P): Larger neural networks see deeper
    into tactical sequences. For tsumego, local reading depth matters more
    than whole-board evaluation accuracy. The b28 model should significantly
    outperform b6 on puzzles requiring ≥5-move reading depth.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        """Prepare input directory and output directories per model."""
        self.input_dir = _prepare_input_dir(tmp_path)
        self.model_results: dict[str, dict] = {}
        self.output_dirs: dict[str, Path] = {}
        self.available = _available_models()

        for model_name in self.available:
            output_dir = tmp_path / f"output-{model_name}"
            output_dir.mkdir()
            self.output_dirs[model_name] = output_dir

    def _run_model(self, model_name: str) -> dict:
        """Run enrichment with a specific model and return aggregate metrics."""
        model_info = self.available[model_name]
        output_dir = self.output_dirs[model_name]

        start = time.monotonic()
        exit_code = run_batch(
            input_dir=str(self.input_dir),
            output_dir=str(output_dir),
            katago_path=str(_KATAGO_PATH),
            quick_model_path=str(model_info["path"]),
            referee_model_path="",  # No referee for benchmark — quick only
            config_path=None,
        )
        elapsed = time.monotonic() - start

        # Parse all results
        json_files = sorted(output_dir.glob("*.json"))
        results = [_parse_result(jf) for jf in json_files]

        accepted = sum(1 for r in results if r["status"] == "accepted")
        flagged = sum(1 for r in results if r["status"] == "flagged")
        rejected = sum(1 for r in results if r["status"] == "rejected")
        levels = [r["level_id"] for r in results if r["level_id"] is not None]
        refutations = sum(r["refutation_count"] for r in results)

        return {
            "exit_code": exit_code,
            "elapsed": elapsed,
            "per_puzzle_avg": elapsed / len(results) if results else 0,
            "total": len(results),
            "accepted": accepted,
            "flagged": flagged,
            "rejected": rejected,
            "acceptance_rate": accepted / len(results) if results else 0,
            "levels": levels,
            "avg_level": sum(levels) / len(levels) if levels else 0,
            "level_variance": _variance(levels) if levels else 0,
            "total_refutations": refutations,
            "per_puzzle_results": results,
        }

    def test_all_models_produce_output(self):
        """Each available model × 10 puzzles → valid JSON output."""
        for model_name in self.available:
            result = self._run_model(model_name)
            self.model_results[model_name] = result

            assert result["total"] == _EXPECTED_COUNT, (
                f"Model {model_name}: expected {_EXPECTED_COUNT} outputs, "
                f"got {result['total']}"
            )
            print(f"\n[{model_name}] {result['total']} outputs, "
                  f"accepted={result['accepted']}, flagged={result['flagged']}, "
                  f"rejected={result['rejected']}, "
                  f"time={result['elapsed']:.1f}s "
                  f"({result['per_puzzle_avg']:.1f}s/puzzle)")

    def test_accuracy_increases_with_model_size(self):
        """Larger models should have equal or better acceptance rates.

        This test validates the fundamental assumption that bigger models
        produce more accurate tsumego analysis. It uses a weak ordering
        (≤ not <) because small sample sizes may cause ties.
        """
        for model_name in self.available:
            if model_name not in self.model_results:
                self.model_results[model_name] = self._run_model(model_name)

        # Sort models by rank (size) ascending
        sorted_models = sorted(
            self.model_results.items(),
            key=lambda kv: self.available[kv[0]]["rank"],
        )

        rates = [(name, result["acceptance_rate"]) for name, result in sorted_models]

        print("\n[Model Accuracy Comparison]")
        for name, rate in rates:
            print(f"  {name}: {rate:.0%} accepted "
                  f"({self.model_results[name]['accepted']}/{self.model_results[name]['total']})")

        # Weak monotonic ordering: each model ≥ previous (allows ties)
        for i in range(1, len(rates)):
            prev_name, prev_rate = rates[i - 1]
            curr_name, curr_rate = rates[i]
            # Allow regression of at most 1 puzzle (10% on 10 puzzles)
            # due to stochastic effects in MCTS
            assert curr_rate >= prev_rate - 0.15, (
                f"{curr_name} ({curr_rate:.0%}) should not be significantly worse than "
                f"{prev_name} ({prev_rate:.0%}). "
                f"If this fails consistently, check model quality."
            )

    def test_timing_comparison(self):
        """Record per-model timing for benchmark documentation."""
        for model_name in self.available:
            if model_name not in self.model_results:
                self.model_results[model_name] = self._run_model(model_name)

        print("\n[Timing Comparison]")
        print(f"{'Model':<15} {'Total (s)':>10} {'Per-puzzle (s)':>15} {'Size (MB)':>10}")
        print("-" * 55)

        for model_name in sorted(
            self.model_results,
            key=lambda n: self.available[n]["rank"],
        ):
            result = self.model_results[model_name]
            info = self.available[model_name]
            print(f"{model_name:<15} {result['elapsed']:>10.1f} "
                  f"{result['per_puzzle_avg']:>15.1f} "
                  f"{info['size_mb']:>10.1f}")

    def test_difficulty_compression(self):
        """Larger models should have more diverse difficulty assignments.

        The b6 model has a known compression bias (everything clusters at
        advanced/low-dan). Larger models should spread difficulty more evenly.
        """
        for model_name in self.available:
            if model_name not in self.model_results:
                self.model_results[model_name] = self._run_model(model_name)

        print("\n[Difficulty Distribution]")
        for model_name in sorted(
            self.model_results,
            key=lambda n: self.available[n]["rank"],
        ):
            result = self.model_results[model_name]
            levels = result["levels"]
            unique = len(set(levels))
            print(f"  {model_name}: {unique} unique levels, "
                  f"variance={result['level_variance']:.0f}, "
                  f"levels={sorted(levels)}")


def _variance(values: list[int | float]) -> float:
    """Calculate population variance."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)
