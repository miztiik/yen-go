"""Dry-run heuristic screening of named test sets.

Runs BEFORE any training/inference: walks each test_{id}.jsonl +
test_{id}_metadata.jsonl pair and reports cheap structural / coverage
metrics so we can compare test set composition without spending GPU time.

Per-set output:
  - n_rows
  - board-size distribution
  - side-to-move distribution (Black / White)
  - tag distribution (top 10)
  - technique-tag coverage (rows with >=1 known technique tag)
  - correct_first_move coverage (rows with non-empty correct_first_move)
  - wrong_first_moves stats (avg count, % with >=1 wrong move)
  - has_reference_prose count
  - source distribution

Top-level "comparison" prints a side-by-side table on the few headline
columns: n, %tagged, %has_correct_move, board mix, source mix.

Usage:
    python -m tools.yen_sei.eval.dryrun
    python -m tools.yen_sei.eval.dryrun --refined-dir tools/yen_sei/data/refined
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.core.go_teaching_constants import GO_TECHNIQUE_PATTERN
from tools.yen_sei.config import REFINED_DIR


def _load_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def _is_technique_tag(tag: str) -> bool:
    if not tag:
        return False
    return bool(GO_TECHNIQUE_PATTERN.search(tag.lower().replace("-", " ")))


def _summarise_one(test_set_id: str, sidecars: list[dict]) -> dict:
    n = len(sidecars)
    if n == 0:
        return {"test_set_id": test_set_id, "n": 0}

    board = Counter(s.get("board_size") for s in sidecars)
    side = Counter(s.get("side_to_move") for s in sidecars)
    sources = Counter(s.get("source") for s in sidecars)
    has_correct = sum(1 for s in sidecars if s.get("correct_first_move"))
    has_ref_prose = sum(1 for s in sidecars if s.get("has_reference_prose"))
    wrong_counts = [len(s.get("wrong_first_moves") or []) for s in sidecars]
    has_wrong = sum(1 for c in wrong_counts if c >= 1)
    avg_wrong = round(sum(wrong_counts) / max(n, 1), 2)

    tag_counter: Counter = Counter()
    rows_with_tag = 0
    rows_with_technique_tag = 0
    for s in sidecars:
        tags = s.get("tags") or []
        if tags:
            rows_with_tag += 1
        for t in tags:
            tag_counter[t] += 1
        if any(_is_technique_tag(t) for t in tags):
            rows_with_technique_tag += 1

    return {
        "test_set_id": test_set_id,
        "n": n,
        "pct_has_correct_first_move": round(100.0 * has_correct / n, 1),
        "pct_has_wrong_first_move": round(100.0 * has_wrong / n, 1),
        "avg_wrong_first_moves": avg_wrong,
        "pct_tagged": round(100.0 * rows_with_tag / n, 1),
        "pct_with_technique_tag": round(100.0 * rows_with_technique_tag / n, 1),
        "pct_has_reference_prose": round(100.0 * has_ref_prose / n, 1),
        "board_size_dist": dict(board.most_common()),
        "side_dist": dict(side.most_common()),
        "source_dist": dict(sources.most_common()),
        "top_tags": dict(tag_counter.most_common(10)),
    }


def _print_per_set(s: dict) -> None:
    if s["n"] == 0:
        print(f"\n{s['test_set_id']}: EMPTY")
        return
    print(f"\n=== {s['test_set_id']} (n={s['n']}) ===")
    print(f"  has_correct_first_move:   {s['pct_has_correct_first_move']}%")
    print(f"  has_wrong_first_move:     {s['pct_has_wrong_first_move']}% "
          f"(avg {s['avg_wrong_first_moves']} per row)")
    print(f"  tagged at all:            {s['pct_tagged']}%")
    print(f"  with known technique tag: {s['pct_with_technique_tag']}%")
    print(f"  has_reference_prose:      {s['pct_has_reference_prose']}%")
    print(f"  board sizes:  {s['board_size_dist']}")
    print(f"  side to move: {s['side_dist']}")
    print(f"  sources:      {s['source_dist']}")
    if s["top_tags"]:
        print(f"  top tags:     {s['top_tags']}")


def _print_comparison(per_set: list[dict]) -> None:
    if not per_set:
        return
    cols = ["n", "pct_has_correct_first_move", "pct_with_technique_tag",
            "pct_has_reference_prose"]
    short = {"pct_has_correct_first_move": "%has_corr",
             "pct_with_technique_tag": "%tech_tag",
             "pct_has_reference_prose": "%ref_prose"}
    print("\n=== TEST-SET COMPARISON ===")
    header = f"{'test_set':<32}" + "".join(f"{short.get(c, c):>12}" for c in cols)
    print(header)
    print("-" * len(header))
    for s in per_set:
        line = f"{s['test_set_id']:<32}" + "".join(f"{str(s.get(c, '')):>12}" for c in cols)
        print(line)


def run_dryrun(refined_dir: str | Path | None = None) -> dict:
    refined = Path(refined_dir) if refined_dir else REFINED_DIR
    if not refined.exists():
        raise SystemExit(f"refined dir not found: {refined}")

    test_files = sorted(
        p for p in refined.glob("test_*.jsonl")
        if not p.name.endswith("_metadata.jsonl")
    )
    if not test_files:
        raise SystemExit(
            f"No test_*.jsonl found in {refined}. "
            f"Run `python -m tools.yen_sei eval-prep` first."
        )

    per_set: list[dict] = []
    for chat_path in test_files:
        ts_id = chat_path.stem.removeprefix("test_")
        meta_path = refined / f"test_{ts_id}_metadata.jsonl"
        sidecars = _load_jsonl(meta_path)
        if not sidecars:
            print(f"[warn] no sidecar for {ts_id}; falling back to chat-rows count only")
            chat_rows = _load_jsonl(chat_path)
            per_set.append({"test_set_id": ts_id, "n": len(chat_rows)})
            continue
        s = _summarise_one(ts_id, sidecars)
        per_set.append(s)
        _print_per_set(s)

    _print_comparison(per_set)

    out_path = refined / "test_sets_dryrun.json"
    out_path.write_text(json.dumps({"per_set": per_set}, indent=2), encoding="utf-8")
    print(f"\nDryrun summary -> {out_path}")
    return {"per_set": per_set}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refined-dir", type=str, default=None,
                    help="Override the data/refined dir to scan.")
    args = ap.parse_args()
    run_dryrun(refined_dir=args.refined_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
