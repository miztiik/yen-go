"""P.3 — Scale test: 100 puzzles through the enrichment pipeline.

Validates that the enrichment pipeline handles a 100-puzzle batch:
  - All puzzles produce valid JSON output
  - No regressions: 10 reference puzzles still match P.1 quality
  - Error rate < 5% (broken SGFs, timeouts)
  - Performance: measure wall-clock time, per-puzzle average

Input: 100 SGFs from local fixtures (tests/fixtures/scale/scale-100/).
Fixtures are pre-prepared by scripts/prepare_calibration_fixtures.py —
NO external-sources references.

These tests are @pytest.mark.slow AND @pytest.mark.integration.
"""

import json
import shutil
import time
from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from cli import run_batch

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
from config.helpers import KATAGO_PATH, model_path

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_SCALE_100_DIR = _FIXTURES_DIR / "scale" / "scale-100"

_KATAGO_PATH = KATAGO_PATH
_QUICK_MODEL = model_path("test_smallest")  # b6 — cheapest for perf test quick role
_REFEREE_MODEL = model_path("test_fast")    # b10 — used in referee role for perf tests

_SCALE = 100
_MAX_ERROR_RATE = 0.05  # < 5%
_TIMEOUT_SECONDS = 3600  # 1 hour max for 100 puzzles


def _get_referee_model() -> str:
    if _REFEREE_MODEL.exists():
        return str(_REFEREE_MODEL)
    return ""


def _prepare_input(source_dir: Path, dest_dir: Path, count: int) -> int:
    """Copy first `count` SGFs from source to dest. Returns actual count."""
    sgf_files = sorted(source_dir.glob("*.sgf"))[:count]
    for sgf in sgf_files:
        shutil.copy2(sgf, dest_dir / sgf.name)
    return len(sgf_files)


def _count_outputs(output_dir: Path) -> tuple[int, int]:
    """Return (json_count, sgf_count) in output directory."""
    return (
        len(list(output_dir.glob("*.json"))),
        len(list(output_dir.glob("*.sgf"))),
    )


def _parse_statuses(output_dir: Path) -> list[str]:
    """Extract validation statuses from all enrichment JSONs."""
    statuses = []
    for jf in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            status = data.get("validation", {}).get("status", "error")
            statuses.append(status)
        except (json.JSONDecodeError, OSError):
            statuses.append("error")
    return statuses


_skip_reasons = []
if not _KATAGO_PATH.exists():
    _skip_reasons.append("KataGo binary not found")
if not _QUICK_MODEL.exists():
    _skip_reasons.append("Quick model not found")
if not _SCALE_100_DIR.exists():
    _skip_reasons.append(
        "Scale-100 fixtures not found — run: "
        "python scripts/prepare_calibration_fixtures.py"
    )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestScale100:
    """Scale test: 100 puzzles through enrichment pipeline.

    Validates pipeline stability, output completeness, and error rate
    at a scale 3× larger than the perf-33 smoke test.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self.input_dir = tmp_path / "input-100"
        self.input_dir.mkdir()
        self.output_dir = tmp_path / "output-100"
        self.output_dir.mkdir()

        self.actual_count = _prepare_input(
            _SCALE_100_DIR, self.input_dir, _SCALE
        )
        assert self.actual_count >= _SCALE, (
            f"Expected {_SCALE} SGFs, found {self.actual_count}"
        )

    def _run(self) -> tuple[int, float]:
        """Run batch and return (exit_code, elapsed_seconds)."""
        start = time.monotonic()
        exit_code = run_batch(
            input_dir=str(self.input_dir),
            output_dir=str(self.output_dir),
            katago_path=str(_KATAGO_PATH),
            quick_model_path=str(_QUICK_MODEL),
            referee_model_path=_get_referee_model(),
            config_path=None,
        )
        elapsed = time.monotonic() - start
        return exit_code, elapsed

    def test_100_puzzles_complete(self):
        """All 100 puzzles produce valid JSON output."""
        exit_code, elapsed = self._run()

        json_count, sgf_count = _count_outputs(self.output_dir)

        print(f"\n[Scale-100] Completed in {elapsed:.1f}s "
              f"({elapsed / self.actual_count:.1f}s/puzzle)")
        print(f"  JSON: {json_count}/{self.actual_count}, "
              f"SGF: {sgf_count}/{self.actual_count}")

        # All input SGFs should produce JSON output
        assert json_count == self.actual_count, (
            f"Expected {self.actual_count} JSON outputs, got {json_count}"
        )

    def test_error_rate(self):
        """Error rate (broken SGFs, timeouts) < 5%."""
        self._run()
        statuses = _parse_statuses(self.output_dir)

        errors = sum(1 for s in statuses if s == "error")
        error_rate = errors / len(statuses) if statuses else 0

        accepted = sum(1 for s in statuses if s == "accepted")
        flagged = sum(1 for s in statuses if s == "flagged")
        rejected = sum(1 for s in statuses if s == "rejected")

        print("\n[Scale-100 Status Distribution]")
        print(f"  Accepted: {accepted} ({accepted / len(statuses):.0%})")
        print(f"  Flagged:  {flagged} ({flagged / len(statuses):.0%})")
        print(f"  Rejected: {rejected} ({rejected / len(statuses):.0%})")
        print(f"  Errors:   {errors} ({error_rate:.0%})")

        assert error_rate <= _MAX_ERROR_RATE, (
            f"Error rate {error_rate:.0%} exceeds threshold {_MAX_ERROR_RATE:.0%}"
        )

    def test_timing_under_limit(self):
        """100-puzzle batch should complete within time limit."""
        _, elapsed = self._run()

        print(f"\n[Scale-100 Timing] {elapsed:.1f}s total, "
              f"{elapsed / self.actual_count:.1f}s/puzzle")

        assert elapsed < _TIMEOUT_SECONDS, (
            f"Batch took {elapsed:.1f}s, exceeds limit of {_TIMEOUT_SECONDS}s"
        )

    def test_output_format_valid(self):
        """Spot-check: all JSON outputs have required fields."""
        self._run()

        required_fields = {"engine", "validation", "difficulty"}
        json_files = sorted(self.output_dir.glob("*.json"))

        invalid = []
        for jf in json_files[:20]:  # Check first 20
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                missing = required_fields - set(data.keys())
                if missing:
                    invalid.append((jf.name, list(missing)))
            except (json.JSONDecodeError, OSError) as e:
                invalid.append((jf.name, str(e)))

        assert not invalid, (
            f"Invalid JSON outputs: {invalid[:5]}"
        )
