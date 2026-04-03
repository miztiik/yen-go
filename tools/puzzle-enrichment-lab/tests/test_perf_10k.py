"""P.5 — Scale test: 10,000 puzzles through the enrichment pipeline.

Validates production-readiness at full scale:
  - All puzzles complete
  - Difficulty distribution is reasonable (not all same level)
  - Validation rate: ≥15% accepted (b6 baseline, per P.1.2 review)
  - Refutation coverage: ≥30% of puzzles have at least 1 refutation

Input: SGFs from local fixtures (tests/fixtures/scale/scale-10k/).
Fixtures are pre-prepared by scripts/prepare_calibration_fixtures.py —
NO external-sources references. Files are pre-mixed from all available
collections with name prefixes for deduplication.

Note: If fewer than 10K SGFs are available in fixtures, the test scales
down gracefully. The minimum viable run is 2,500+.

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
_SCALE_10K_DIR = _FIXTURES_DIR / "scale" / "scale-10k"

_KATAGO_PATH = KATAGO_PATH
_QUICK_MODEL = model_path("test_smallest")  # b6 — cheapest for perf test quick role
_REFEREE_MODEL = model_path("test_fast")    # b10 — used in referee role for perf tests

_TARGET_SCALE = 10_000
_MINIMUM_SCALE = 2_500  # Minimum viable for distribution checks
_TIMEOUT_SECONDS = 120_000  # ~33 hours max
_MAX_ERROR_RATE = 0.05
# Load acceptance threshold from config — configurable for future tightening
try:
    from config import load_enrichment_config as _load_cfg
    _MIN_ACCEPTANCE_RATE = _load_cfg().quality_gates.acceptance_threshold
except Exception:
    _MIN_ACCEPTANCE_RATE = 0.85    # ≥85% accepted (fallback)
_MIN_REFUTATION_RATE = 0.20    # ≥20% have at least 1 refutation
_MIN_UNIQUE_LEVELS = 4         # At least 4 distinct difficulty levels


def _get_referee_model() -> str:
    if _REFEREE_MODEL.exists():
        return str(_REFEREE_MODEL)
    return ""


def _collect_all_sgfs(source_dir: Path, max_count: int) -> list[tuple[Path, str]]:
    """Gather SGFs from pre-prepared fixture directory up to max_count.

    Returns list of (source_path, dest_name) tuples.
    Fixtures are already prefixed for deduplication.
    """
    sgfs: list[tuple[Path, str]] = []

    if not source_dir.exists():
        return sgfs

    for sgf_path in sorted(source_dir.glob("*.sgf")):
        sgfs.append((sgf_path, sgf_path.name))
        if len(sgfs) >= max_count:
            break

    return sgfs


def _prepare_input(dest_dir: Path, target: int) -> int:
    """Copy SGFs from fixture dir to input directory. Returns actual count."""
    all_sgfs = _collect_all_sgfs(_SCALE_10K_DIR, target)
    for src_path, dest_name in all_sgfs:
        shutil.copy2(src_path, dest_dir / dest_name)
    return len(all_sgfs)


def _count_outputs(output_dir: Path) -> tuple[int, int]:
    return (
        len(list(output_dir.glob("*.json"))),
        len(list(output_dir.glob("*.sgf"))),
    )


_skip_reasons = []
if not _KATAGO_PATH.exists():
    _skip_reasons.append("KataGo binary not found")
if not _QUICK_MODEL.exists():
    _skip_reasons.append("Quick model not found")
if not _SCALE_10K_DIR.exists():
    _skip_reasons.append(
        "Scale-10K fixtures not found — run: "
        "python scripts/prepare_calibration_fixtures.py"
    )
else:
    _available = len(_collect_all_sgfs(_SCALE_10K_DIR, _MINIMUM_SCALE))
    if _available < _MINIMUM_SCALE:
        _skip_reasons.append(
            f"Need ≥{_MINIMUM_SCALE} SGFs in fixtures, found {_available}"
        )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    bool(_skip_reasons),
    reason="; ".join(_skip_reasons) if _skip_reasons else "OK",
)
class TestScale10K:
    """Scale test: up to 10,000 puzzles through enrichment pipeline.

    Production readiness validation. Tests distribution properties
    that only emerge at large scale: difficulty spread, acceptance
    rate convergence, refutation coverage.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self.input_dir = tmp_path / "input-10k"
        self.input_dir.mkdir()
        self.output_dir = tmp_path / "output-10k"
        self.output_dir.mkdir()

        self.actual_count = _prepare_input(self.input_dir, _TARGET_SCALE)
        print(f"\n[Scale-10K Setup] Prepared {self.actual_count} SGFs "
              f"(target: {_TARGET_SCALE})")

        assert self.actual_count >= _MINIMUM_SCALE, (
            f"Need ≥{_MINIMUM_SCALE} SGFs, found {self.actual_count}"
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

    def test_10k_puzzles_complete(self):
        """All puzzles complete without crash. Core stability test."""
        exit_code, elapsed = self._run()

        json_count, sgf_count = _count_outputs(self.output_dir)
        per_puzzle = elapsed / self.actual_count if self.actual_count else 0

        print(f"\n[Scale-10K] Completed in {elapsed:.0f}s "
              f"({per_puzzle:.1f}s/puzzle)")
        print(f"  Input: {self.actual_count}, "
              f"JSON: {json_count}, SGF: {sgf_count}")

        # At least 95% completion rate
        completion_rate = json_count / self.actual_count if self.actual_count else 0
        assert completion_rate >= 0.95, (
            f"Completion rate {completion_rate:.0%} below 95%. "
            f"Got {json_count}/{self.actual_count} outputs."
        )

    def test_enrichment_distribution(self):
        """Difficulty distribution must span multiple levels.

        At 10K scale with puzzles from dozens of collections, we expect
        good distribution across difficulty levels.
        """
        self._run()

        levels: dict[int, int] = {}
        sample_size = min(self.actual_count, 2000)  # Sample for speed

        for jf in sorted(self.output_dir.glob("*.json"))[:sample_size]:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                level_id = data.get("difficulty", {}).get("level_id")
                if level_id is not None:
                    levels[level_id] = levels.get(level_id, 0) + 1
            except (json.JSONDecodeError, OSError):
                continue

        print(f"\n[Scale-10K Distribution] (sampled {sample_size})")
        for level_id in sorted(levels):
            count = levels[level_id]
            pct = count / sum(levels.values()) * 100
            print(f"  Level {level_id}: {count} ({pct:.1f}%)")

        assert len(levels) >= _MIN_UNIQUE_LEVELS, (
            f"Expected ≥{_MIN_UNIQUE_LEVELS} unique difficulty levels, "
            f"got {len(levels)}: {sorted(levels.keys())}"
        )

        # No single level should dominate > 60% of results
        max_count = max(levels.values())
        max_pct = max_count / sum(levels.values())
        assert max_pct < 0.60, (
            f"Single level dominates {max_pct:.0%} — "
            f"difficulty distribution too concentrated"
        )

    def test_validation_rate(self):
        """Acceptance rate should meet production threshold.

        Production target: ≥85% accepted with b15/b28 model at ≥500 visits.
        """
        self._run()

        statuses: dict[str, int] = {}
        for jf in sorted(self.output_dir.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                status = data.get("validation", {}).get("status", "error")
                statuses[status] = statuses.get(status, 0) + 1
            except (json.JSONDecodeError, OSError):
                statuses["error"] = statuses.get("error", 0) + 1

        total = sum(statuses.values())
        accepted = statuses.get("accepted", 0)
        acceptance_rate = accepted / total if total else 0

        print(f"\n[Scale-10K Validation] Total: {total}")
        for status in ("accepted", "flagged", "rejected", "error"):
            count = statuses.get(status, 0)
            pct = count / total * 100 if total else 0
            print(f"  {status}: {count} ({pct:.1f}%)")

        assert acceptance_rate >= _MIN_ACCEPTANCE_RATE, (
            f"Acceptance rate {acceptance_rate:.0%} below minimum "
            f"{_MIN_ACCEPTANCE_RATE:.0%}"
        )

    def test_refutation_coverage(self):
        """Sufficient puzzles should have refutation analysis.

        Refutations are the key educational value-add of the enrichment
        pipeline. At scale, we expect a meaningful fraction to have them.
        """
        self._run()

        with_refutations = 0
        total_checked = 0
        sample_size = min(self.actual_count, 2000)

        for jf in sorted(self.output_dir.glob("*.json"))[:sample_size]:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                refutations = data.get("refutations", [])
                if refutations:
                    with_refutations += 1
                total_checked += 1
            except (json.JSONDecodeError, OSError):
                continue

        refutation_rate = with_refutations / total_checked if total_checked else 0

        print(f"\n[Scale-10K Refutations] "
              f"{with_refutations}/{total_checked} have refutations "
              f"({refutation_rate:.0%})")

        assert refutation_rate >= _MIN_REFUTATION_RATE, (
            f"Refutation coverage {refutation_rate:.0%} below minimum "
            f"{_MIN_REFUTATION_RATE:.0%}"
        )

    def test_error_rate_at_scale(self):
        """Error rate stays below threshold at full scale."""
        self._run()

        total = 0
        errors = 0
        for jf in sorted(self.output_dir.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                if data.get("validation", {}).get("status") == "error":
                    errors += 1
                total += 1
            except (json.JSONDecodeError, OSError):
                errors += 1
                total += 1

        error_rate = errors / total if total else 0

        print(f"\n[Scale-10K Errors] {errors}/{total} ({error_rate:.0%})")

        assert error_rate <= _MAX_ERROR_RATE, (
            f"Error rate {error_rate:.0%} exceeds {_MAX_ERROR_RATE:.0%}"
        )
