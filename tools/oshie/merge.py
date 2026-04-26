"""Merge LLM teaching output back into enrichment JSON.

Takes the teaching output from the LLM agent and merges it into the
original enrichment JSON file, updating teaching_comments and hints.

Usage:
    python merge.py --enrichment enrichment.json --teaching teaching.json
    python merge.py --enrichment enrichment.json --teaching teaching.json --output merged.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure agent package is importable
_TOOL_DIR = Path(__file__).resolve().parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))


def merge_teaching(enrichment: dict, teaching: dict) -> dict:
    """Merge LLM teaching output into enrichment data.

    Updates the enrichment dict in-place with:
    - teaching_comments.correct_comment
    - teaching_comments.wrong_comments
    - teaching_comments.summary
    - hints (3-tier list)

    Args:
        enrichment: The full AiAnalysisResult dict.
        teaching: The validated TeachingOutput dict from LLM.

    Returns:
        The updated enrichment dict.
    """
    tc = teaching.get("teaching_comments", {})

    # Merge teaching comments
    if "teaching_comments" not in enrichment:
        enrichment["teaching_comments"] = {}

    if tc.get("correct_comment"):
        enrichment["teaching_comments"]["correct_comment"] = tc["correct_comment"]
    if tc.get("wrong_comments"):
        enrichment["teaching_comments"]["wrong_comments"] = tc["wrong_comments"]
    if tc.get("summary"):
        enrichment["teaching_comments"]["summary"] = tc["summary"]

    # Merge hints
    hints = teaching.get("hints", [])
    if hints:
        enrichment["hints"] = hints

    # Mark as LLM-enriched
    enrichment.setdefault("metadata", {})["teaching_source"] = "llm"

    return enrichment


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge LLM teaching output into enrichment JSON.",
    )
    parser.add_argument(
        "--enrichment", "-e",
        type=Path,
        required=True,
        help="Path to the original enrichment JSON file.",
    )
    parser.add_argument(
        "--teaching", "-t",
        type=Path,
        required=True,
        help="Path to the LLM teaching output JSON.",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path. Defaults to overwriting the enrichment file.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate teaching JSON against schema before merging.",
    )

    args = parser.parse_args()

    if not args.enrichment.exists():
        logger.error("Enrichment file not found: %s", args.enrichment)
        sys.exit(1)
    if not args.teaching.exists():
        logger.error("Teaching file not found: %s", args.teaching)
        sys.exit(1)

    enrichment = json.loads(args.enrichment.read_text(encoding="utf-8"))
    teaching = json.loads(args.teaching.read_text(encoding="utf-8"))

    if args.validate:
        from agent.response_parser import parse_llm_response
        parse_llm_response(teaching)  # raises on invalid
        logger.info("Teaching JSON validated OK")

    merged = merge_teaching(enrichment, teaching)

    output_path = args.output or args.enrichment
    output_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Merged output written to %s", output_path)


if __name__ == "__main__":
    main()
