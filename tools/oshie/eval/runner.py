"""Eval runner -- orchestrator with CLI interface.

Usage:
    python -m tools.oshie.eval.runner --prompt v2 --puzzles 10 --endpoint http://127.0.0.1:8080
    python -m tools.oshie.eval.runner --prompt v2 --puzzles 5 --judge --analyze
    python -m tools.oshie.eval.runner --history
    python -m tools.oshie.eval.runner --prompt v2 --seed-only --puzzles 4

Each run:
1. Samples a FRESH set of puzzles (no repeat from prior runs unless --seed-only)
2. Calls the LLM for each puzzle (answerer sub-agent)
3. Scores with Layer A+B (deterministic)
4. Optionally scores with Layer C judge (LLM sub-agent)
5. Optionally runs the analyzer (prompt engineer sub-agent)
6. Saves full results JSON and appends to history.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .analyzer import AnalysisReport, analyze_run, to_dict as analyzer_to_dict
from .history import (
    RunRecord,
    append_record,
    compute_puzzle_set_hash,
    generate_run_id,
    get_previous_puzzle_ids,
    load_history,
    print_history_table,
)
from .judge import JudgeVerdict, judge_response, to_dict as judge_to_dict
from .llm_caller import LLMResponse, call_llm, check_server
from .log_setup import log_puzzle_io, setup_run_logger
from .puzzle_pool import TestPuzzle, puzzles_to_json, sample_diverse, sample_from_evaluation_fixtures
from .scorers import WEIGHTS, EvalResult, score_response, to_dict as scorer_to_dict

logger = logging.getLogger(__name__)

_EVAL_DIR = Path(__file__).resolve().parent
_PROMPTS_DIR = _EVAL_DIR / "prompts"
_RUNS_DIR = _EVAL_DIR / "runs"


def _load_prompt(version: str) -> str:
    """Load system prompt by version name."""
    prompt_file = _PROMPTS_DIR / f"{version}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8").strip()


def _progress_callback(puzzle_name: str):
    """Create a progress callback for a specific puzzle."""
    def cb(think_tok: int, content_tok: int, elapsed: float):
        phase = "THINK" if content_tok == 0 else "OUT"
        rate = (think_tok + content_tok) / max(elapsed, 0.1)
        print(
            f"    [{elapsed:5.1f}s] {phase} | t:{think_tok} c:{content_tok} | {rate:.0f} t/s",
            flush=True,
        )
    return cb


def run_eval(
    prompt_version: str,
    n_puzzles: int = 10,
    endpoint: str = "http://127.0.0.1:8080",
    model: str = "gemma-4-26B-A4B-it-Q8_0.gguf",
    max_tokens: int = 64000,
    seed: int | None = None,
    eval_fixtures: bool = False,
    run_judge: bool = False,
    run_analyzer: bool = False,
    change_summary: str = "",
) -> dict:
    """Run a complete evaluation cycle.

    Args:
        prompt_version: Name of prompt file (e.g. "v2").
        n_puzzles: Number of puzzles to test.
        endpoint: LLM server URL.
        model: Model name.
        max_tokens: Shared budget for thinking + output tokens.
        seed: Random seed (None = random each time for fresh puzzles).
        eval_fixtures: If True, use only evaluation fixtures from
            train_test_dataset/fixtures/evaluation/ (professional Cho Chikun SGFs).
        run_judge: Enable Layer C LLM judging.
        run_analyzer: Enable prompt improvement analysis.
        change_summary: Description of what changed in this prompt version.

    Returns:
        Dict with results, summary, judge verdicts, and suggestions.
    """
    system_prompt = _load_prompt(prompt_version)
    run_id = generate_run_id()

    # Set up persistent file logging
    run_logger, run_log_path = setup_run_logger(
        run_id=run_id,
        prompt_version=prompt_version,
        metadata={
            "model": model,
            "endpoint": endpoint,
            "max_tokens": max_tokens,
            "n_puzzles": n_puzzles,
            "eval_fixtures": eval_fixtures,
            "seed": seed,
            "run_judge": run_judge,
            "run_analyzer": run_analyzer,
            "change_summary": change_summary,
        },
    )
    run_logger.info("Run started: %s (prompt=%s, n=%d, max_tokens=%d)", run_id, prompt_version, n_puzzles, max_tokens)

    print(f"\n{'='*70}")
    print(f"OSHIE EVAL RUN: {run_id}")
    print(f"  Prompt: {prompt_version}")
    print(f"  Puzzles: {n_puzzles}")
    print(f"  Endpoint: {endpoint}")
    print(f"  Judge: {'yes' if run_judge else 'no'}")
    print(f"  Analyzer: {'yes' if run_analyzer else 'no'}")
    print(f"{'='*70}\n")

    # Check server
    server_info = check_server(endpoint)
    if not server_info:
        print(f"ERROR: Cannot reach LLM server at {endpoint}")
        return {"error": "server_unreachable"}
    print(f"Server OK: {json.dumps(server_info.get('data', [{}])[0].get('id', 'unknown'))}")

    # Sample puzzles (fresh set, avoiding prior runs)
    print(f"\nSampling {n_puzzles} puzzles...")
    if eval_fixtures:
        puzzles = sample_from_evaluation_fixtures(n=n_puzzles, seed=seed)
        print(f"  Using {len(puzzles)} evaluation fixtures (Cho Chikun SGFs)")
    else:
        exclude = get_previous_puzzle_ids() if seed is None else set()
        puzzles = sample_diverse(
            n=n_puzzles,
            seed=seed,
            include_eval_fixtures=min(2, n_puzzles // 3),
            exclude_hashes=exclude,
        )
        print(f"  Sampled {len(puzzles)} puzzles ({len(exclude)} excluded from prior runs)")

    if not puzzles:
        print("ERROR: No puzzles available")
        return {"error": "no_puzzles"}

    # Show puzzle set
    puzzle_set_hash = compute_puzzle_set_hash([p.puzzle_id for p in puzzles])
    print(f"  Set hash: {puzzle_set_hash}")
    for i, p in enumerate(puzzles):
        print(f"  [{i+1}] {p.puzzle_id} -- {p.technique} ({p.difficulty}) [{p.source}]")

    # ── Phase 1: Answerer (LLM generates teaching comments) ──────
    print(f"\n--- Phase 1: Answerer ({len(puzzles)} puzzles) ---")
    results: list[EvalResult] = []
    responses: list[LLMResponse] = []
    user_prompts: list[str] = []
    t0 = time.time()

    for i, puzzle in enumerate(puzzles):
        print(f"\n  [{i+1}/{len(puzzles)}] {puzzle.puzzle_id} ({puzzle.technique})")
        user_prompt = puzzle.to_user_prompt()
        user_prompts.append(user_prompt)

        resp = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            endpoint=endpoint,
            model=model,
            max_tokens=max_tokens,
            progress_cb=_progress_callback(puzzle.puzzle_id),
        )
        responses.append(resp)

        print(f"    Done: {resp.elapsed_s:.0f}s | think:{resp.think_tokens} out:{resp.content_tokens} | {resp.finish_reason}")

        if resp.finish_reason == "error":
            print(f"    ERROR: {resp.error}")

        # Score with Layer A + B
        expected_wrong = [wm.get("sgf", "") for wm in puzzle.wrong_moves]
        result = score_response(
            content=resp.content,
            puzzle_id=puzzle.puzzle_id,
            puzzle_name=f"{puzzle.technique}:{puzzle.difficulty}",
            prompt_version=prompt_version,
            technique=puzzle.technique,
            difficulty=puzzle.difficulty,
            correct_move_sgf=puzzle.correct_move_sgf,
            correct_move_gtp=puzzle.correct_move_gtp,
            technique_tags=puzzle.technique_tags,
            expected_wrong_coords=expected_wrong,
            think_tokens=resp.think_tokens,
            content_tokens=resp.content_tokens,
            elapsed_s=resp.elapsed_s,
            finish_reason=resp.finish_reason,
        )
        results.append(result)
        print(f"    Score: {result.weighted_total:.3f}")
        for d in result.dimensions:
            status = "OK" if d.score >= 0.5 else "LOW"
            print(f"      {d.name}: {d.score:.2f} [{status}] {d.details[:60]}")

        # Persistent per-puzzle I/O log
        dim_scores = {d.name: d.score for d in result.dimensions}
        puzzle_log = log_puzzle_io(
            run_id=run_id,
            puzzle_index=i + 1,
            puzzle_id=puzzle.puzzle_id,
            prompt_version=prompt_version,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            reasoning=resp.reasoning,
            content=resp.content,
            score=result.weighted_total,
            think_tokens=resp.think_tokens,
            content_tokens=resp.content_tokens,
            elapsed_s=resp.elapsed_s,
            finish_reason=resp.finish_reason,
            dimension_scores=dim_scores,
        )
        run_logger.info(
            "[%d/%d] %s score=%.3f think=%d out=%d %.0fs %s -> %s",
            i + 1, len(puzzles), puzzle.puzzle_id, result.weighted_total,
            resp.think_tokens, resp.content_tokens, resp.elapsed_s,
            resp.finish_reason, puzzle_log.name,
        )

    answerer_elapsed = time.time() - t0

    # ── Phase 2: Judge (optional Layer C) ────────────────────────
    judge_verdicts: list[dict] = []
    if run_judge:
        print(f"\n--- Phase 2: Judge ({len(puzzles)} puzzles) ---")
        for i, (puzzle, result) in enumerate(zip(puzzles, results)):
            print(f"  [{i+1}/{len(puzzles)}] Judging {puzzle.puzzle_id}...")
            verdict = judge_response(
                puzzle_info={
                    "name": puzzle.puzzle_id,
                    "technique": puzzle.technique,
                    "difficulty": puzzle.difficulty,
                    "board_size": puzzle.board_size,
                    "correct_move_sgf": puzzle.correct_move_sgf,
                    "correct_move_gtp": puzzle.correct_move_gtp,
                    "wrong_moves": puzzle.wrong_moves,
                },
                model_output=result.raw_content,
                endpoint=endpoint,
                model=model,
                max_tokens=max_tokens,
            )
            judge_verdicts.append(judge_to_dict(verdict))
            if verdict.error:
                print(f"    Judge error: {verdict.error[:100]}")
            else:
                print(f"    Judge score: {verdict.weighted_score:.3f}")
                for dim, score in verdict.dimension_scores.items():
                    print(f"      {dim}: {score:.1f}/5")

    # ── Phase 3: Analyzer (optional prompt engineer) ─────────────
    analysis: dict | None = None
    if run_analyzer:
        print(f"\n--- Phase 3: Analyzer ---")
        report = analyze_run(
            results=results,
            current_prompt=system_prompt,
            endpoint=endpoint,
            model=model,
            max_tokens=max_tokens,
        )
        analysis = analyzer_to_dict(report)
        if report.error:
            print(f"  Analyzer error: {report.error[:200]}")
        else:
            print(f"  Weakest dimensions: {', '.join(report.weakest_dimensions)}")
            print(f"  Suggestions ({len(report.suggestions)}):")
            for s in report.suggestions:
                print(f"    [{s.priority}] {s.change_type}: {s.description[:80]}")
                if s.proposed_text:
                    print(f"           text: {s.proposed_text[:100]}")

    # ── Summary ──────────────────────────────────────────────────
    total_elapsed = time.time() - t0
    summary = _compute_summary(results, judge_verdicts)

    print(f"\n{'='*70}")
    print("EVAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Prompt version:    {prompt_version}")
    print(f"  Puzzles tested:    {len(results)}")
    print(f"  Weighted average:  {summary['weighted_avg']:.3f}")
    print(f"  Pass rate (>=0.6): {summary['pass_rate']:.1f}%")
    print(f"  Empty content:     {summary['empty_content_count']}")
    print(f"  Avg think tokens:  {summary['avg_think_tokens']:.0f}")
    print(f"  Avg content tokens:{summary['avg_content_tokens']:.0f}")
    print(f"  Avg time/puzzle:   {summary['avg_elapsed_s']:.0f}s")
    print(f"  Total time:        {total_elapsed:.0f}s")
    print(f"\n  --- Dimensions ---")
    for dim, avg in sorted(summary["dimension_avgs"].items()):
        bar = "#" * int(avg * 20)
        print(f"    {dim:<25} {avg:.3f} |{bar}")

    if judge_verdicts:
        print(f"\n  --- Judge Scores ---")
        print(f"    Weighted average: {summary.get('judge_weighted_avg', 0):.3f}")
        for dim, avg in sorted(summary.get("judge_dimension_avgs", {}).items()):
            print(f"    {dim:<25} {avg:.1f}/5")

    # ── Save results ─────────────────────────────────────────────
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_file = _RUNS_DIR / f"{prompt_version}_{run_id}.json"

    # Build per-puzzle I/O log: input prompt + full output + reasoning
    io_traces: list[dict] = []
    for i, (puzzle, resp, result) in enumerate(zip(puzzles, responses, results)):
        io_traces.append({
            "puzzle_id": puzzle.puzzle_id,
            "user_prompt": user_prompts[i],
            "reasoning": resp.reasoning,
            "content": resp.content,
            "think_tokens": resp.think_tokens,
            "content_tokens": resp.content_tokens,
            "elapsed_s": round(resp.elapsed_s, 1),
            "finish_reason": resp.finish_reason,
            "score": round(result.weighted_total, 4),
        })

    run_data = {
        "run_id": run_id,
        "prompt_version": prompt_version,
        "change_summary": change_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "model": model,
        "max_tokens": max_tokens,
        "puzzle_set_hash": puzzle_set_hash,
        "system_prompt": system_prompt,
        "puzzles": puzzles_to_json(puzzles),
        "io_traces": io_traces,
        "results": [scorer_to_dict(r) for r in results],
        "judge_verdicts": judge_verdicts if judge_verdicts else None,
        "analysis": analysis,
        "summary": summary,
    }
    run_file.write_text(json.dumps(run_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Results saved: {run_file.relative_to(_EVAL_DIR.parent)}")

    # Append to history
    record = RunRecord(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        prompt_version=prompt_version,
        change_summary=change_summary or f"{prompt_version} eval",
        n_puzzles=len(results),
        puzzle_set_hash=puzzle_set_hash,
        weighted_avg=summary["weighted_avg"],
        dimension_avgs=summary["dimension_avgs"],
        pass_rate=summary["pass_rate"],
        empty_content_count=summary["empty_content_count"],
        avg_think_tokens=summary["avg_think_tokens"],
        avg_content_tokens=summary["avg_content_tokens"],
        avg_elapsed_s=summary["avg_elapsed_s"],
        total_elapsed_s=total_elapsed,
        judge_weighted_avg=summary.get("judge_weighted_avg"),
        judge_dimension_avgs=summary.get("judge_dimension_avgs", {}),
    )
    history_path = append_record(record)
    print(f"  History updated: {history_path.relative_to(_EVAL_DIR.parent)}")

    # Log summary to run log
    run_logger.info(
        "Run complete: weighted_avg=%.3f pass_rate=%.1f%% empty=%d puzzles=%d total=%.0fs",
        summary["weighted_avg"], summary["pass_rate"],
        summary["empty_content_count"], len(results), total_elapsed,
    )
    for dim, avg in sorted(summary["dimension_avgs"].items()):
        run_logger.info("  %s: %.3f", dim, avg)
    run_logger.info("Logs dir: %s", run_log_path.parent)
    print(f"  Logs: {run_log_path.relative_to(_EVAL_DIR.parent.parent)}")

    return run_data


def _compute_summary(
    results: list[EvalResult],
    judge_verdicts: list[dict],
) -> dict:
    """Compute aggregate summary metrics."""
    n = max(len(results), 1)

    # Per-dimension averages
    dim_avgs: dict[str, float] = {}
    for name in WEIGHTS:
        scores = [
            next((d.score for d in r.dimensions if d.name == name), 0.0)
            for r in results
        ]
        dim_avgs[name] = sum(scores) / n

    weighted_avg = sum(r.weighted_total for r in results) / n
    pass_count = sum(1 for r in results if r.weighted_total >= 0.6)
    empty_count = sum(1 for r in results if r.finish_reason == "empty_content")

    summary = {
        "weighted_avg": round(weighted_avg, 4),
        "dimension_avgs": {k: round(v, 4) for k, v in dim_avgs.items()},
        "pass_rate": round(100.0 * pass_count / n, 1),
        "empty_content_count": empty_count,
        "avg_think_tokens": round(sum(r.think_tokens for r in results) / n, 1),
        "avg_content_tokens": round(sum(r.content_tokens for r in results) / n, 1),
        "avg_elapsed_s": round(sum(r.elapsed_s for r in results) / n, 1),
    }

    # Judge summary
    if judge_verdicts:
        valid = [v for v in judge_verdicts if not v.get("error")]
        if valid:
            summary["judge_weighted_avg"] = round(
                sum(v.get("weighted_score", 0) for v in valid) / len(valid), 4
            )
            judge_dims: dict[str, list[float]] = {}
            for v in valid:
                for dim, score in v.get("dimension_scores", {}).items():
                    if dim not in judge_dims:
                        judge_dims[dim] = []
                    judge_dims[dim].append(score)
            summary["judge_dimension_avgs"] = {
                dim: round(sum(scores) / len(scores), 2)
                for dim, scores in judge_dims.items()
            }

    return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="oshie eval harness -- repeatable LLM teaching quality evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test with evaluation fixtures only
  python -m tools.oshie.eval.runner --prompt v3.1 --eval-fixtures --puzzles 3

  # Full run with fresh puzzles + judge + analyzer
  python -m tools.oshie.eval.runner --prompt v3.1 --puzzles 10 --judge --analyze

  # View run history
  python -m tools.oshie.eval.runner --history

  # Compare prompt versions
  python -m tools.oshie.eval.runner --prompt v4 --puzzles 10 --judge \\
      --change "Added few-shot example for move sequences"
        """,
    )
    parser.add_argument("--prompt", type=str, help="Prompt version (e.g. v2)")
    parser.add_argument("--puzzles", type=int, default=10, help="Number of puzzles (default: 10)")
    parser.add_argument("--endpoint", type=str, default="http://127.0.0.1:8080",
                        help="LLM server URL")
    parser.add_argument("--model", type=str, default="gemma-4-26B-A4B-it-Q8_0.gguf",
                        help="Model name")
    parser.add_argument("--max-tokens", type=int, default=64000,
                        help="Token budget per puzzle (thinking + output combined). "
                             "Server n_ctx is the hard ceiling (check /slots endpoint). "
                             "After ~500-700 tok prompt overhead, set close to n_ctx. "
                             "Higher = more thinking = better quality but slower (~22 tok/s).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed (omit for fresh puzzles each run)")
    parser.add_argument("--eval-fixtures", action="store_true",
                        help="Use only evaluation fixtures (Cho Chikun SGFs from train_test_dataset)")
    parser.add_argument("--judge", action="store_true", help="Enable Layer C LLM judging")
    parser.add_argument("--analyze", action="store_true", help="Enable prompt improvement analysis")
    parser.add_argument("--change", type=str, default="",
                        help="Short description of what changed in this prompt version")
    parser.add_argument("--history", action="store_true", help="Print run history table")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.history:
        print_history_table()
        return

    if not args.prompt:
        parser.error("--prompt is required (e.g. --prompt v2)")

    run_eval(
        prompt_version=args.prompt,
        n_puzzles=args.puzzles,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        seed=args.seed,
        eval_fixtures=args.eval_fixtures,
        run_judge=args.judge,
        run_analyzer=args.analyze,
        change_summary=args.change,
    )


if __name__ == "__main__":
    main()
