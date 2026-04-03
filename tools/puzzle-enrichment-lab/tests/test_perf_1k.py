"""P.4 — Scale test: 1,000 puzzles through the enrichment pipeline.

Validates that the enrichment pipeline handles a 1,000-puzzle batch:
  - All puzzles complete without crash
  - Memory usage doesn't grow unbounded (via output rate stability)
  - Error rate remains acceptable

Input: 1,000 SGFs from local fixtures (tests/fixtures/scale/scale-1k/).
Fixtures are pre-prepared by scripts/prepare_calibration_fixtures.py —
NO external-sources references. Files are pre-mixed from three
collections (elementary/intermediate/advanced) with name prefixes.

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

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_SCALE_1K_DIR = _FIXTURES_DIR / "scale" / "scale-1k"

# Model paths via conftest.model_path (Plan 010, D42)
from config.helpers import KATAGO_PATH, model_path

_KATAGO_PATH = KATAGO_PATH
_QUICK_MODEL = model_path("test_fast")    # b10 — fast integration workhorse
_REFEREE_MODEL = model_path("referee")    # b28 — referee tier

_SCALE = 1000
_TIMEOUT_SECONDS = 36000  # 10 hours max for 1K puzzles
_MAX_ERROR_RATE = 0.05


def _get_referee_model() -> str:
    if _REFEREE_MODEL.exists():
        return str(_REFEREE_MODEL)
    return ""


def _prepare_input(source_dir: Path, dest_dir: Path) -> int:
    """Copy all SGFs from source fixture dir to dest. Returns actual count."""
    total = 0
    for sgf in sorted(source_dir.glob("*.sgf")):
        shutil.copy2(sgf, dest_dir / sgf.name)
        total += 1
    return total


def _count_outputs(output_dir: Path) -> tuple[int, int]:
    return (
        len(list(output_dir.glob("*.json"))),
        len(list(output_dir.glob("*.sgf"))),
    )


def _parse_statuses(output_dir: Path) -> list[str]:
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
if not _SCALE_1K_DIR.exists():
    _skip_reasons.append(
        "Scale-1K fixtures not found — run: "
        "python scripts/prepare_calibration_fixtures.py"
    )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestScale1K:
    """Scale test: 1,000 puzzles through enrichment pipeline.

    Validates pipeline stability at 30× the perf-33 smoke test scale.
    Mixes three difficulty tiers (elementary/intermediate/advanced) to
    exercise the full difficulty classification range.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self.input_dir = tmp_path / "input-1k"
        self.input_dir.mkdir()
        self.output_dir = tmp_path / "output-1k"
        self.output_dir.mkdir()

        self.actual_count = _prepare_input(_SCALE_1K_DIR, self.input_dir)
        assert self.actual_count >= _SCALE * 0.9, (
            f"Expected ~{_SCALE} SGFs, found {self.actual_count}"
        )

    def _run(self) -> tuple[int, float]:
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

    def test_1k_puzzles_complete(self):
        """All ~1,000 puzzles complete without crash."""
        exit_code, elapsed = self._run()

        json_count, sgf_count = _count_outputs(self.output_dir)

        per_puzzle = elapsed / self.actual_count if self.actual_count else 0

        print(f"\n[Scale-1K] Completed in {elapsed:.1f}s "
              f"({per_puzzle:.1f}s/puzzle)")
        print(f"  Input: {self.actual_count}, "
              f"JSON: {json_count}, SGF: {sgf_count}")

        # At least 95% of inputs should produce output
        completion_rate = json_count / self.actual_count if self.actual_count else 0
        assert completion_rate >= 0.95, (
            f"Completion rate {completion_rate:.0%} below 95%. "
            f"Got {json_count}/{self.actual_count} outputs."
        )

    def test_memory_stable(self):
        """Output rate stays stable — proxy for memory stability.

        We can't directly measure memory in pytest, but if the pipeline
        slows dramatically over time, it indicates memory pressure.
        We check that the last 25% of outputs aren't significantly
        slower than the first 25%.
        """
        self._run()

        json_files = sorted(
            self.output_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
        )

        if len(json_files) < 40:
            pytest.skip("Too few outputs for memory stability check")

        quarter = len(json_files) // 4

        # Compare timestamps of first vs last quarter
        first_q = json_files[:quarter]
        last_q = json_files[-quarter:]

        first_span = first_q[-1].stat().st_mtime - first_q[0].stat().st_mtime
        last_span = last_q[-1].stat().st_mtime - last_q[0].stat().st_mtime

        # Allow last quarter to be up to 3x slower (warmup effects, cache pressure)
        if first_span > 0:
            slowdown_ratio = last_span / first_span
            print(f"\n[Memory Stability] First quarter: {first_span:.1f}s, "
                  f"Last quarter: {last_span:.1f}s, "
                  f"Slowdown ratio: {slowdown_ratio:.1f}x")
            assert slowdown_ratio < 3.0, (
                f"Pipeline slowed {slowdown_ratio:.1f}x in last quarter — "
                f"possible memory leak"
            )

    def test_error_rate(self):
        """Error rate stays below threshold at 1K scale."""
        self._run()
        statuses = _parse_statuses(self.output_dir)

        errors = sum(1 for s in statuses if s == "error")
        error_rate = errors / len(statuses) if statuses else 0

        accepted = sum(1 for s in statuses if s == "accepted")
        flagged = sum(1 for s in statuses if s == "flagged")
        rejected = sum(1 for s in statuses if s == "rejected")

        print("\n[Scale-1K Status Distribution]")
        print(f"  Accepted: {accepted} ({accepted / len(statuses):.0%})")
        print(f"  Flagged:  {flagged} ({flagged / len(statuses):.0%})")
        print(f"  Rejected: {rejected} ({rejected / len(statuses):.0%})")
        print(f"  Errors:   {errors} ({error_rate:.0%})")

        assert error_rate <= _MAX_ERROR_RATE, (
            f"Error rate {error_rate:.0%} exceeds {_MAX_ERROR_RATE:.0%}"
        )

    def test_difficulty_distribution(self):
        """Difficulty distribution should span multiple levels.

        With puzzles from three Cho Chikun collections, we expect at least
        3 distinct difficulty levels in the output.
        """
        self._run()

        levels = set()
        for jf in sorted(self.output_dir.glob("*.json"))[:200]:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                level_id = data.get("difficulty", {}).get("level_id")
                if level_id is not None:
                    levels.add(level_id)
            except (json.JSONDecodeError, OSError):
                continue

        print(f"\n[Scale-1K Difficulty] {len(levels)} unique levels: {sorted(levels)}")

        assert len(levels) >= 3, (
            f"Expected ≥3 unique difficulty levels, got {len(levels)}: {sorted(levels)}"
        )
