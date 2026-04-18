"""yen-sei evaluation harness.

Three layers:

- Layer A (`structural`): JSON validity, field presence, length sanity.
  Free, deterministic, runs on 100% of test rows.
- Layer B (`grounded`): position-anchored objective checks. Did the model
  mention the actual correct move coordinate? At least one technique tag
  from the puzzle's `tags`? Did it avoid hallucinated stones? Is it English?
  Free, deterministic, runs on 100% of test rows.
- Layer C (`judge`): pluggable subjective judge (Manual / OpenAI / local-LLM /
  subagent). The notebook depends only on the `Judge` Protocol — swap
  implementations without changing eval code. See `judges.py` docstrings.

Usage from a notebook:

    from tools.yen_sei.eval import evaluate
    summary = evaluate(model, tokenizer, test_rows, out_dir="…", judge=None)

`judge` defaults to None (only A+B); pass a `ManualJudge(out_dir)` to also
write a sample queue for human review.
"""
from .runner import evaluate, generate_one
from .scorers import score_grounded, score_structural
from .judges import Judge, JudgeResult, ManualJudge

__all__ = [
    "evaluate",
    "generate_one",
    "score_structural",
    "score_grounded",
    "Judge",
    "JudgeResult",
    "ManualJudge",
]
