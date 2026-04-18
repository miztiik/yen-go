"""validate stage: Check refine output against TeachingOutput schema.

Parses every example in the SFT JSONL, validates structure, and reports
degenerate cases (empty fields, missing hints). Non-zero exit if failure
rate exceeds threshold.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from tools.core.teaching_schema import TeachingOutput
from tools.yen_sei.config import SFT_JSONL
from tools.yen_sei.models.training_example import TrainingExample
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)


def run_validate(
    input_path: str | None = None,
    max_failure_rate: float = 0.05,
) -> int:
    """Validate refined SFT examples against the TeachingOutput schema.

    Returns 0 if pass, 1 if failure rate exceeds threshold.
    """
    set_context(stage="validate")
    sft_path = Path(input_path) if input_path else SFT_JSONL

    if not sft_path.exists():
        logger.error("Input file not found: %s. Run 'refine' first.", sft_path)
        return 1

    total = 0
    failures: list[tuple[int, str]] = []
    warnings: dict[str, int] = {
        "empty_correct_comment": 0,
        "no_wrong_comments": 0,
        "empty_hints": 0,
        "short_hints": 0,
    }

    with sft_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            total += 1
            try:
                example = TrainingExample.model_validate_json(line)

                # Extract assistant response
                if len(example.messages) != 3:
                    failures.append((i, f"Expected 3 messages, got {len(example.messages)}"))
                    continue

                assistant_content = example.messages[2].content
                data = json.loads(assistant_content)
                output = TeachingOutput.model_validate(data)

                # Check for degenerate cases
                if not output.teaching_comments.correct_comment.strip():
                    warnings["empty_correct_comment"] += 1
                if not output.teaching_comments.wrong_comments:
                    warnings["no_wrong_comments"] += 1
                if not output.hints:
                    warnings["empty_hints"] += 1
                elif len(output.hints) < 2:
                    warnings["short_hints"] += 1

            except json.JSONDecodeError as e:
                failures.append((i, f"Invalid JSON in assistant response: {e}"))
            except Exception as e:
                failures.append((i, f"Validation error: {e}"))

    # Report
    failure_rate = len(failures) / max(total, 1)
    passed = total - len(failures)

    print(f"\n{'='*50}")
    print("VALIDATION REPORT")
    print(f"{'='*50}")
    print(f"Total examples:  {total}")
    print(f"Valid:           {passed}")
    print(f"Failures:        {len(failures)} ({failure_rate:.1%})")
    print(f"\nWarnings (valid but potentially low-quality):")
    for warning, count in warnings.items():
        pct = count / max(total, 1) * 100
        print(f"  {warning}: {count} ({pct:.1f}%)")

    if failures:
        print(f"\nFirst 10 failures:")
        for idx, err in failures[:10]:
            print(f"  Line {idx}: {err}")

    if failure_rate > max_failure_rate:
        print(f"\nFAILED: Failure rate {failure_rate:.1%} exceeds threshold {max_failure_rate:.0%}")
        return 1

    print(f"\nPASSED: Failure rate {failure_rate:.1%} within threshold {max_failure_rate:.0%}")
    return 0
