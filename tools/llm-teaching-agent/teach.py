"""LLM Teaching Agent CLI.

Generates teaching comments and hints for Go puzzles using an LLM,
taking KataGo enrichment output as input.

Usage:
    python teach.py --input enrichment.json --output teaching.json
    python teach.py --input enrichment.json --output teaching.json --persona lee_sedol
    python teach.py --input enrichment.json --dry-run  # shows prompt, no API call
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


def _load_config(config_path: Path | None = None) -> dict:
    """Load config from JSON file, falling back to config.example.json."""
    if config_path and config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))

    default = _TOOL_DIR / "config.json"
    if default.exists():
        return json.loads(default.read_text(encoding="utf-8"))

    example = _TOOL_DIR / "config.example.json"
    if example.exists():
        logger.warning("Using config.example.json (copy to config.json and set your API key)")
        return json.loads(example.read_text(encoding="utf-8"))

    return {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Go teaching comments from KataGo enrichment data using an LLM.",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=None,
        help="Path to enrichment JSON file (AiAnalysisResult output).",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for teaching JSON. Defaults to <input>.teaching.json.",
    )
    parser.add_argument(
        "--persona",
        type=str,
        default=None,
        help="Teacher persona name (e.g. cho_chikun, lee_sedol, generic_teacher).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the model name from config.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override the API base URL from config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the prompt without making an API call.",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available personas and exit.",
    )

    args = parser.parse_args()

    # List personas
    if args.list_personas:
        from agent.personas import list_personas
        personas = list_personas()
        print("Available personas:")
        for p in personas:
            print(f"  - {p}")
        return

    # Require --input for all non-listing operations
    if not args.input:
        parser.error("--input is required (unless using --list-personas)")

    # Load enrichment data
    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    enrichment_data = json.loads(args.input.read_text(encoding="utf-8"))
    teaching_signals = enrichment_data.get("teaching_signals")
    if not teaching_signals:
        logger.error("No teaching_signals found in %s", args.input)
        sys.exit(1)

    # Load config
    config_data = _load_config(args.config)

    # Apply CLI overrides
    if args.model:
        config_data.setdefault("provider", {})["model"] = args.model
    if args.base_url:
        config_data.setdefault("provider", {})["base_url"] = args.base_url

    # Resolve persona
    persona_name = args.persona or config_data.get("persona", "generic_teacher")

    from agent.personas import load_persona
    from agent.prompt_builder import build_system_prompt, build_user_prompt

    persona_text = load_persona(persona_name)
    system_prompt = build_system_prompt(persona_text)
    user_prompt = build_user_prompt(enrichment_data)

    # Dry run: print prompts and exit
    if args.dry_run:
        print("=" * 60)
        print("SYSTEM PROMPT")
        print("=" * 60)
        print(system_prompt)
        print()
        print("=" * 60)
        print("USER PROMPT")
        print("=" * 60)
        print(user_prompt)
        return

    # Call LLM
    from agent.llm_client import LLMConfig, TeachingLLMClient
    from agent.response_parser import parse_llm_response

    llm_config = LLMConfig.from_dict(config_data)
    client = TeachingLLMClient(llm_config)

    logger.info("Generating teaching comments with %s/%s...", llm_config.base_url, llm_config.model)
    raw_response = client.generate(system_prompt, user_prompt)

    # Validate response
    teaching_output = parse_llm_response(raw_response)

    # Write output
    output_path = args.output or args.input.with_suffix(".teaching.json")
    output_data = teaching_output.model_dump()
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Teaching output written to %s", output_path)
    logger.info(
        "Generated: %d correct comment, %d wrong comments, %d hints",
        1 if teaching_output.teaching_comments.correct_comment else 0,
        len(teaching_output.teaching_comments.wrong_comments),
        len(teaching_output.hints),
    )


if __name__ == "__main__":
    main()
