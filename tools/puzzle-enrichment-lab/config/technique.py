"""Technique and ko detection config models.

Groups: per-technique detector configs and the top-level
technique detection + ko detection models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LadderDetectionConfig(BaseModel):
    min_pv_length: int = Field(default=4, ge=1, le=50)
    diagonal_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class SnapbackDetectionConfig(BaseModel):
    policy_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    winrate_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    delta_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    min_pv_length: int = Field(default=3, ge=1, le=30, description="Min PV length for capture pattern verification")


class NetDetectionConfig(BaseModel):
    policy_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    winrate_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    min_refutations: int = Field(default=2, ge=1, le=10)
    delta_spread: float = Field(default=0.1, ge=0.0, le=1.0)


class SekiDetectionConfig(BaseModel):
    winrate_low: float = Field(default=0.40, ge=0.0, le=1.0)
    winrate_high: float = Field(default=0.60, ge=0.0, le=1.0)
    score_threshold: float = Field(default=5.0, ge=0.0, description="Score lead threshold for seki signal")


class DirectCaptureDetectionConfig(BaseModel):
    max_depth: int = Field(default=2, ge=1, le=20)
    winrate_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    max_visits: int = Field(default=500, ge=1, le=100000)


class ThrowInDetectionConfig(BaseModel):
    edge_lines: int = Field(default=2, ge=1, le=9)


class NakadeDetectionConfig(BaseModel):
    min_opponent_neighbors: int = Field(default=3, ge=1, le=4, description="Min opponent stones adjacent to move")
    winrate_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class DoubleAtariDetectionConfig(BaseModel):
    winrate_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class SacrificeDetectionConfig(BaseModel):
    policy_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    winrate_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    pv_min_length: int = Field(default=3, ge=1, le=30)


class EscapeDetectionConfig(BaseModel):
    min_liberty_gain: int = Field(default=2, ge=1, le=10)
    max_initial_liberties: int = Field(default=2, ge=1, le=10)
    winrate_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class TechniqueDetectionConfig(BaseModel):
    """Technique detection thresholds (Plan 010, D41)."""
    description: str = ""
    ladder: LadderDetectionConfig = Field(default_factory=LadderDetectionConfig)
    snapback: SnapbackDetectionConfig = Field(default_factory=SnapbackDetectionConfig)
    net: NetDetectionConfig = Field(default_factory=NetDetectionConfig)
    seki: SekiDetectionConfig = Field(default_factory=SekiDetectionConfig)
    direct_capture: DirectCaptureDetectionConfig = Field(
        default_factory=DirectCaptureDetectionConfig,
    )
    throw_in: ThrowInDetectionConfig = Field(default_factory=ThrowInDetectionConfig)
    nakade: NakadeDetectionConfig = Field(default_factory=NakadeDetectionConfig)
    double_atari: DoubleAtariDetectionConfig = Field(default_factory=DoubleAtariDetectionConfig)
    sacrifice: SacrificeDetectionConfig = Field(default_factory=SacrificeDetectionConfig)
    escape: EscapeDetectionConfig = Field(default_factory=EscapeDetectionConfig)


class KoDetectionConfig(BaseModel):
    """Ko detection thresholds (Plan 010, D41)."""
    description: str = ""
    min_pv_length: int = Field(default=3, ge=1, le=50)
    min_repeat_count: int = Field(default=2, ge=1, le=10)
    long_ko_threshold: int = Field(default=3, ge=1, le=10)
    double_ko_coords: int = Field(default=2, ge=1, le=10)
