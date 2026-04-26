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
# Polished raw output (P0-3): same schema as RAW_JSONL plus per-node
# `comment_polished` and `comment_polish_status` fields. Refine prefers
# this when present.
RAW_POLISHED_JSONL = RAW_DIR / "raw_polished.jsonl"
POLISH_CACHE_DIR = RAW_DIR / "polish_cache"

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
SPLIT_RATIOS = {"train": 0.9, "val": 0.1, "test": 0.0}

# Model targets
TIER1_MODEL = "google/gemma-4-e2b"
TIER2_MODEL = "Qwen/Qwen3-0.6B"

# SFT system prompt — single source of truth for refine + eval_prep.
# Voice: Cho Chikun style (direct, precise, short sentences, no filler).
# Constraint: model generates teaching prose only, never coordinates.
SYSTEM_PROMPT = (
    "You are a professional Go teacher. When explaining tsumego, describe why moves "
    "succeed or fail in terms of liberties, eye shape, vital points, and technique "
    "\u2014 name the tesuji when one applies. Be direct and precise like Cho Chikun: "
    "short sentences, no filler. Do not output move coordinates or solution "
    "sequences; explain only the strategic reasoning behind the position."
)
