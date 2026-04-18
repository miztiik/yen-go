"""TrainingExample: refine output schema (ChatML format).

Represents one training example ready for SFT, in the ChatML
conversation format expected by Qwen3 and Gemma 4 training scripts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a ChatML conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class ExampleMetadata(BaseModel):
    """Provenance and split info for a training example."""

    source: str = Field(description="Data source: 'ogs', 'goproblems', 'gogameguru', 'synthetic'")
    tier: str = Field(default="bronze", description="Curation tier: 'gold', 'silver', or 'bronze'")
    file_path: str = Field(description="Source SGF filename (e.g., 'gold_goproblems_6840.sgf')")
    split: Literal["train", "val", "test"] = Field(description="Dataset split assignment")
    comment_quality_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Heuristic quality score: 0.0 = bare marker, 1.0 = rich teaching content",
    )
    sample_weight: float = Field(default=1.0, ge=0.0, description="Tier-based upsampling weight applied during refine")


class TrainingExample(BaseModel):
    """ChatML conversation for SFT training.

    Output of the refine stage. Input to the train/distill notebooks.
    """

    messages: list[ChatMessage] = Field(min_length=3, max_length=3)
    metadata: ExampleMetadata
