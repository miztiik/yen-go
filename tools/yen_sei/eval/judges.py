"""Layer C judges. The notebook depends only on `Judge`; pick a backend at runtime.

Backends planned:
- ManualJudge   — writes a queue file; you grade rows by hand. Default.
- OpenAIJudge   — remote LLM-as-judge (GPT-4o or similar). Needs OPENAI_API_KEY.
                  Stub class below; implement when you decide the cost is worth it.
- LocalJudge    — Ollama / vLLM. Same interface, different transport.
- SubagentJudge — Copilot subagent (e.g. Go-Advisor persona) via runSubagent.
                  Implementation lives in the IDE-side agent harness, not here.

Implementing OpenAI/Local/Subagent backends is a Level-2 change later.
The notebook code never has to change — only the Judge instance does.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class JudgeResult:
    score: float                    # 0..5, comparable across backends
    rubric: dict                    # backend-specific per-criterion breakdown
    rationale: str = ""             # one-paragraph reason
    backend: str = ""               # "manual" | "openai" | "local" | "subagent"
    raw: dict = field(default_factory=dict)


class Judge(Protocol):
    """Pluggable subjective grader. All backends conform to this interface."""

    def grade(
        self,
        prompt: str,
        generated: str,
        reference: str | None,
        metadata: dict,
    ) -> JudgeResult: ...

    def finalize(self) -> None:
        """Optional: flush queue files, close connections, etc."""


class ManualJudge:
    """Writes each item to a JSONL queue file for a human to grade later.

    Usage:
        judge = ManualJudge(queue_path=out_dir / "judge_queue.jsonl", sample_n=20)
        ... evaluate(model, ..., judge=judge) ...
        judge.finalize()
        # Open the queue file, fill in `score` (0..5) and `rationale`, save.

    `evaluate` will call `grade()` on a random sample of `sample_n` rows and
    return placeholder `JudgeResult(score=-1, ...)` so summary stats reflect
    "not yet graded".
    """

    def __init__(self, queue_path: Path | str, sample_n: int = 20):
        self.queue_path = Path(queue_path)
        self.sample_n = sample_n
        self._buffer: list[dict] = []

    def grade(
        self,
        prompt: str,
        generated: str,
        reference: str | None,
        metadata: dict,
    ) -> JudgeResult:
        # Buffer for finalize(); return sentinel score.
        self._buffer.append({
            "prompt": prompt,
            "generated": generated,
            "reference": reference,
            "metadata": metadata,
            "score": None,            # human fills in 0..5
            "rationale": "",          # human fills in
        })
        return JudgeResult(score=-1.0, rubric={}, rationale="awaiting human review", backend="manual")

    def finalize(self) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        # Sample down to sample_n if buffer is larger
        items = self._buffer
        if len(items) > self.sample_n:
            import random
            random.seed(42)
            items = random.sample(items, self.sample_n)
        with self.queue_path.open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")


def to_dict(r: JudgeResult) -> dict:
    return asdict(r)
