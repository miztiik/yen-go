"""yen-sei configuration: paths, constants, model settings.

DATA ISOLATION POLICY:
    yen-sei NEVER reads from or writes to external-sources/ directly
    during harvest/refine/train stages.
    The `ingest` stage scans external-sources/, scores puzzles, and copies
    qualified files into data/sources/ as a flat directory.
    All downstream stages read only from data/.
"""

from __future__ import annotations

from pathlib import Path

# Root of the yen-sei tool
TOOL_ROOT = Path(__file__).parent

# Project root (yen-go)
PROJECT_ROOT = TOOL_ROOT.parent.parent

# ── External sources root (read-only, scanned by selector) ───────────
EXT_ROOT = PROJECT_ROOT / "external-sources"

# ── Data directory layout (all gitignored) ──────────────────────────
DATA_DIR = TOOL_ROOT / "data"

# Ingest output: flat directory of qualified SGFs ({source}_{name}.sgf)
SOURCES_DIR = DATA_DIR / "sources"

# Harvest output: extracted (position, comment) pairs
RAW_DIR = DATA_DIR / "raw"
RAW_JSONL = RAW_DIR / "raw.jsonl"

# Refine output: filtered, normalized, ChatML formatted
REFINED_DIR = DATA_DIR / "refined"
SFT_JSONL = REFINED_DIR / "sft.jsonl"
SFT_METADATA_JSONL = REFINED_DIR / "sft_metadata.jsonl"
TRAIN_JSONL = REFINED_DIR / "train.jsonl"
VAL_JSONL = REFINED_DIR / "val.jsonl"
TEST_JSONL = REFINED_DIR / "test.jsonl"

# Synthetic examples from Tier 1 model
SYNTHETIC_DIR = DATA_DIR / "synthetic"
SYNTHETIC_JSONL = SYNTHETIC_DIR / "synthetic.jsonl"

# Model artifacts
MODELS_DIR = DATA_DIR / "models"

# ── Selection ─────────────────────────────────────────────────────────
SELECTION_MIN_SCORE = 0.5  # Tier A threshold

# Refine stage defaults
DEFAULT_MIN_COMMENT_LENGTH = 80

# Train/val/test split ratios
SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}

# Model targets
TIER1_MODEL = "google/gemma-4-e2b"
TIER2_MODEL = "Qwen/Qwen3-0.6B"
