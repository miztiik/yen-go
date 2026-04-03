"""Infrastructure config models.

Groups: paths, calibration, logging extras, and test defaults.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    """Centralized output directory paths (Q10).

    All runtime artifacts are consolidated under .lab-runtime/.
    Paths are relative to the puzzle-enrichment-lab tool root.
    """
    description: str = ""
    runtime_dir: str = Field(
        default=".lab-runtime",
        description="Root runtime directory for all artifacts",
    )
    logs_dir: str = Field(
        default=".lab-runtime/logs",
        description="Enrichment log files (per-run and aggregate)",
    )
    katago_logs_dir: str = Field(
        default=".lab-runtime/katago-logs",
        description="KataGo native log files (startup diagnostics, model info)",
    )
    outputs_dir: str = Field(
        default=".lab-runtime/outputs",
        description="Default output directory for enriched SGFs and JSON",
    )
    calibration_results_dir: str = Field(
        default=".lab-runtime/calibration-results",
        description="Persistent calibration results for offline review",
    )


class CalibrationConfig(BaseModel):
    """Calibration test configuration (Plan 010, D46)."""
    description: str = ""
    sample_size: int = Field(default=5, ge=1, le=100)
    seed: int | None = Field(default=42, description="Random seed (null for truly random)")
    batch_timeout: int = Field(default=1800, ge=60, le=7200)
    level_tolerance: int = Field(default=20, ge=0, le=100)
    fixture_dirs: list[str] = Field(
        default_factory=lambda: ["cho-elementary", "cho-intermediate", "cho-advanced"],
    )
    randomize_fixtures: bool = Field(
        default=True,
        description="If true (default), seed is ignored and a random sample is picked each run. Set false for deterministic mode.",
    )
    restart_every_n: int = Field(
        default=10, ge=0,
        description="Restart KataGo engine every N puzzles (0=never). Crash mitigation for iGPU OpenCL drivers.",
    )
    surprise_weighting: bool = Field(
        default=False,
        description="PI-11: Weight calibration positions by surprise (|T0_winrate - T2_winrate|)",
    )
    surprise_weight_scale: float = Field(
        default=2.0, ge=0.0,
        description="PI-11: Scale factor for surprise weighting. weight = 1 + scale * |T0_wr - T2_wr|",
    )


def compute_surprise_weight(
    t0_winrate: float,
    t2_winrate: float,
    *,
    enabled: bool = False,
    scale: float = 2.0,
) -> float:
    """PI-11: Compute surprise-based calibration weight for a position.

    Surprise score = |T0_winrate - T2_winrate| (how much the engine
    disagrees with itself across visit tiers T0=50v and T2=2000v).

    Returns 1.0 when disabled (uniform weighting).
    """
    if not enabled:
        return 1.0
    surprise_score = abs(t0_winrate - t2_winrate)
    return 1.0 + scale * surprise_score


class LoggingExtraConfig(BaseModel):
    """Logging configuration additions (Plan 010, D45)."""
    description: str = ""
    per_run_files: bool = Field(
        default=True,
        description="Create logs/{run_id}-enrichment.log per run",
    )
    use_relative_paths: bool = Field(
        default=True,
        description="Strip workspace root from logged paths",
    )


class TestDefaultsConfig(BaseModel):
    """Shared defaults for integration/performance tests.

    Centralizes magic numbers (timeouts, visit counts, thread counts)
    that were duplicated across test files.
    """
    startup_timeout: float = Field(
        default=180.0, gt=0,
        description="Engine startup timeout in seconds (OpenCL autotuning can be slow)",
    )
    query_timeout: float = Field(
        default=30.0, gt=0,
        description="Default per-query timeout in seconds",
    )
    default_max_visits: int = Field(
        default=50, ge=1,
        description="Default max visits for test engines (low for speed)",
    )
    num_threads: int = Field(
        default=1, ge=1, le=64,
        description="Number of threads for test engines",
    )
