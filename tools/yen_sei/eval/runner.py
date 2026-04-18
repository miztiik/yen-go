"""Inference + scoring loop. Notebook entry point: `evaluate(...)`."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from .judges import Judge
from .scorers import GroundedScore, StructuralScore, score_grounded, score_structural, to_dict

_USER_BOARD_RE = re.compile(r"Board: (\d+)x\d+")
_USER_TAGS_RE = re.compile(r"^Tags: (.+)$", re.MULTILINE)
_USER_BLACK_RE = re.compile(r"^Black stones: (.+)$", re.MULTILINE)
_USER_WHITE_RE = re.compile(r"^White stones: (.+)$", re.MULTILINE)


def _parse_user_prompt(text: str) -> tuple[list[str], list[str], list[str]]:
    tags: list[str] = []
    black: list[str] = []
    white: list[str] = []
    if (m := _USER_TAGS_RE.search(text)):
        tags = [t.strip() for t in m.group(1).split(",") if t.strip()]
    if (m := _USER_BLACK_RE.search(text)):
        black = [c.strip() for c in m.group(1).split(",") if c.strip()]
    if (m := _USER_WHITE_RE.search(text)):
        white = [c.strip() for c in m.group(1).split(",") if c.strip()]
    return tags, black, white


def _correct_move_from_reference(reference_assistant: str | None) -> str:
    """Pull the correct-move SGF coord out of the reference assistant JSON.

    Refine emits hints like ``"The first move is at {!cg}."`` — we use that as
    ground truth for grounded scoring.
    """
    if not reference_assistant:
        return ""
    m = re.search(r"\{!([a-s]{2})\}", reference_assistant)
    return m.group(1) if m else ""


def generate_one(model, tokenizer, messages: list[dict], max_new_tokens: int = 384) -> str:
    """Single inference call. Greedy decoding for reproducibility."""
    import torch
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def evaluate(
    model,
    tokenizer,
    test_rows: list[dict],
    out_dir: str | Path,
    judge: Optional[Judge] = None,
    max_new_tokens: int = 384,
    log_every: int = 25,
) -> dict:
    """Run all configured eval layers on `test_rows` and return summary metrics.

    Each row is the standard SFT messages payload:
        {"messages": [{"role":"system","content":...},
                      {"role":"user","content":...},
                      {"role":"assistant","content":...}]}

    Layers A + B always run. Layer C runs only if `judge` is provided.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(test_rows)
    results: list[dict] = []
    t0 = time.time()

    print(f"[eval] running on {n} test rows…")
    for i, row in enumerate(test_rows):
        msgs = row["messages"]
        prompt_msgs = [m for m in msgs if m["role"] != "assistant"]
        reference = next((m["content"] for m in msgs if m["role"] == "assistant"), None)
        user_text = next((m["content"] for m in msgs if m["role"] == "user"), "")

        generated = generate_one(model, tokenizer, prompt_msgs, max_new_tokens=max_new_tokens)

        # Layer A
        struct = score_structural(generated)

        # Layer B — pull metadata out of the prompt + reference
        tags, black, white = _parse_user_prompt(user_text)
        correct_move = _correct_move_from_reference(reference)
        ground = score_grounded(
            generated,
            correct_move_coord=correct_move,
            puzzle_tags=tags,
            setup_coords=black + white,
        )

        # Layer C
        judge_result = None
        if judge is not None:
            jr = judge.grade(
                prompt=user_text,
                generated=generated,
                reference=reference,
                metadata={"tags": tags, "correct_move_coord": correct_move},
            )
            judge_result = to_dict(jr)

        results.append({
            "idx": i,
            "structural": to_dict(struct),
            "grounded": to_dict(ground),
            "judge": judge_result,
            "generated_preview": generated[:600],
            "reference_preview": (reference or "")[:600],
        })

        if (i + 1) % log_every == 0:
            print(f"  {i + 1}/{n} ({(time.time() - t0) / 60:.1f} min elapsed)")

    if judge is not None:
        judge.finalize()

    elapsed_min = (time.time() - t0) / 60
    summary = _aggregate(results)
    summary["n"] = n
    summary["elapsed_minutes"] = round(elapsed_min, 2)

    (out_dir / "test_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "test_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    _print_summary(summary)
    return summary


def _aggregate(results: list[dict]) -> dict:
    n = max(len(results), 1)
    s = [r["structural"] for r in results]
    g = [r["grounded"] for r in results]

    pct = lambda flag_list: round(100.0 * sum(1 for x in flag_list if x) / n, 1)

    summary = {
        "structural": {
            "json_compliance_pct": pct([x["parsed_ok"] for x in s]),
            "has_correct_pct": pct([x["has_correct"] for x in s]),
            "has_wrong_pct": pct([x["has_wrong"] for x in s]),
            "avg_hints": round(sum(x["n_hints"] for x in s) / n, 2),
            "avg_chars_correct": round(sum(x["n_chars_correct"] for x in s) / n, 1),
            "avg_chars_wrong": round(sum(x["n_chars_wrong"] for x in s) / n, 1),
        },
        "grounded": {
            "mentions_correct_move_pct": pct([x["mentions_correct_move"] for x in g]),
            "mentions_tag_technique_pct": pct([x["mentions_any_tag_technique"] for x in g]),
            "no_off_board_coords_pct": pct([x["no_off_board_coords"] for x in g]),
            "looks_english_pct": pct([x["looks_english"] for x in g]),
        },
    }

    # Combined "useful answer" rate: parses, has correct comment, mentions
    # the correct coord OR a known technique. The single number to track.
    useful = sum(
        1 for r in results
        if r["structural"]["parsed_ok"]
        and r["structural"]["has_correct"]
        and (r["grounded"]["mentions_correct_move"] or r["grounded"]["mentions_any_tag_technique"])
        and r["grounded"]["looks_english"]
    )
    summary["useful_answer_pct"] = round(100.0 * useful / n, 1)
    return summary


def _print_summary(summary: dict) -> None:
    print("\n=== EVAL SUMMARY ===")
    print(f"  test rows:         {summary.get('n')}")
    print(f"  elapsed:           {summary.get('elapsed_minutes')} min")
    print(f"  USEFUL ANSWER %:   {summary['useful_answer_pct']}    <-- single headline metric")
    print("  -- Structural (Layer A) --")
    for k, v in summary["structural"].items():
        print(f"    {k:<24} {v}")
    print("  -- Grounded (Layer B) --")
    for k, v in summary["grounded"].items():
        print(f"    {k:<28} {v}")
