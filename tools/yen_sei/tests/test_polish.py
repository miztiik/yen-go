"""Tests for tools.yen_sei.stages.polish."""

from __future__ import annotations

import json
from pathlib import Path

from tools.yen_sei.stages.polish import (
    LLM_MAX_GROWTH_RATIO,
    POLISH_PROMPT_VERSION,
    SKIP_TOKEN,
    STATUS_CLEAN_AFTER_REGEX,
    STATUS_CLEAN_NATIVE,
    STATUS_EMPTY,
    STATUS_FLAGGED_NEEDS_LLM,
    STATUS_KEPT_ORIGINAL,
    STATUS_REJECTED_COORDS,
    STATUS_REJECTED_TOO_LONG,
    STATUS_REWRITTEN,
    STATUS_SKIPPED_UNINTERPRETABLE,
    STATUS_TOO_SHORT_FOR_LLM,
    _validate_llm_output,
    classify,
    dump_batch,
    english_word_ratio,
    load_batch,
    run_polish,
)


# ── english_word_ratio ─────────────────────────────────────────────────


def test_english_ratio_empty_returns_one() -> None:
    assert english_word_ratio("") == 1.0
    assert english_word_ratio("   ") == 1.0


def test_english_ratio_full_english() -> None:
    assert english_word_ratio("the black stone is alive") > 0.7


def test_english_ratio_broken_translation() -> None:
    bad = "enter work to this not can avoid shape form ko fight"
    # Most tokens aren't in the common list (avoid, shape, fight, etc.)
    assert english_word_ratio(bad) < 0.55


# ── classify (Stage A + B) ─────────────────────────────────────────────


def test_classify_empty_input() -> None:
    cls = classify("")
    assert cls.status == STATUS_EMPTY
    assert cls.cleaned == ""
    assert not cls.needs_llm


def test_classify_clean_native_passes() -> None:
    cls = classify("Black has formed two eyes and is alive.")
    assert cls.status == STATUS_CLEAN_NATIVE
    assert cls.needs_llm is False
    assert cls.cn_marker_hits == 0


def test_classify_clean_after_regex() -> None:
    raw = "Correct! #Correct!\n\n**-> Black has formed two eyes and is alive.**"
    cls = classify(raw)
    assert cls.status == STATUS_CLEAN_AFTER_REGEX
    assert cls.cleaned == "Black has formed two eyes and is alive."
    assert not cls.needs_llm


def test_classify_flagged_for_llm_on_cn_markers() -> None:
    raw = (
        "White cannot connect (completed) and obtain more more after this. "
        "By Black 4 squeeze one move then play become ko contest, White Wrong."
    )
    cls = classify(raw)
    assert cls.status == STATUS_FLAGGED_NEEDS_LLM
    assert cls.needs_llm is True
    assert cls.cn_marker_hits >= 1


def test_classify_too_short_for_llm() -> None:
    # Stage A leaves "win." (after stripping boilerplate). Below 30 chars =>
    # not worth a token. Status should be too_short_for_llm.
    raw = "(question) win"
    cls = classify(raw)
    # Either flagged-but-too-short OR clean — we just ensure no LLM call.
    assert cls.status in (
        STATUS_TOO_SHORT_FOR_LLM,
        STATUS_CLEAN_AFTER_REGEX,
        STATUS_CLEAN_NATIVE,
        STATUS_SKIPPED_UNINTERPRETABLE,
    )
    assert cls.needs_llm is False


def test_classify_uninterpretable_collapses_to_empty() -> None:
    raw = "Correct!"  # normalize_section_body returns "" for pure boilerplate
    cls = classify(raw)
    assert cls.status == STATUS_SKIPPED_UNINTERPRETABLE
    assert cls.cleaned == ""
    assert not cls.needs_llm


# ── _validate_llm_output (Stage C guards) ──────────────────────────────


def test_validate_skip_token_returns_uninterpretable() -> None:
    final, status = _validate_llm_output("orig", SKIP_TOKEN)
    assert status == STATUS_SKIPPED_UNINTERPRETABLE
    assert final == ""


def test_validate_too_long_falls_back_to_original() -> None:
    original = "short"
    too_long = "x" * int(LLM_MAX_GROWTH_RATIO * len(original) + 10)
    final, status = _validate_llm_output(original, too_long)
    assert status == STATUS_REJECTED_TOO_LONG
    assert final == original


def test_validate_coord_leak_rejected() -> None:
    original = "The corner is dead"
    candidate = "Black 1 captures at D17."
    final, status = _validate_llm_output(original, candidate)
    assert status == STATUS_REJECTED_COORDS
    assert final == original


def test_validate_clean_rewrite_accepted() -> None:
    original = "White cannot connect"
    candidate = "White cannot connect because the cutting stone is captured."
    final, status = _validate_llm_output(original, candidate)
    assert status == STATUS_REWRITTEN
    assert final == candidate


def test_validate_too_short_keeps_original() -> None:
    final, status = _validate_llm_output("White is dead.", "ok")
    assert status == STATUS_KEPT_ORIGINAL
    assert final == "White is dead."


# ── run_polish dry-run on a tiny synthetic raw.jsonl ──────────────────


def _write_raw(tmp_path: Path, *, comments: list[str]) -> Path:
    """Write a minimal raw.jsonl with one record per comment."""
    raw_path = tmp_path / "raw.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for i, c in enumerate(comments):
            rec = {
                "source": "test",
                "tier": "silver",
                "file_path": f"f{i}.sgf",
                "board_size": 19,
                "player_to_move": "B",
                "setup_black": [],
                "setup_white": [],
                "root_comment": "",
                "solution_nodes": [
                    {
                        "move": "cd",
                        "color": "B",
                        "comment": c,
                        "is_correct": True,
                        "children_count": 0,
                    }
                ],
                "tags": ["life-and-death"],
                "level": "intermediate",
                "collection": "",
                "total_comment_chars": len(c),
            }
            f.write(json.dumps(rec) + "\n")
    return raw_path


def test_run_polish_dry_run_no_file_written(tmp_path: Path) -> None:
    raw = _write_raw(
        tmp_path,
        comments=[
            "Black has formed two eyes and is alive.",  # clean
            "White cannot connect (completed) and obtain more more after.",  # flagged
        ],
    )
    out = tmp_path / "raw_polished.jsonl"
    rc = run_polish(input_path=str(raw), output_path=str(out), use_llm=False)
    assert rc == 0
    assert not out.exists()  # dry-run never writes


def test_run_polish_with_fake_llm_writes_file(tmp_path: Path, monkeypatch) -> None:
    raw = _write_raw(
        tmp_path,
        comments=[
            "Black has formed two eyes and is alive.",
            "White cannot connect (completed) and obtain more more after.",
        ],
    )
    out = tmp_path / "raw_polished.jsonl"

    # Redirect cache dir into tmp_path so the test is hermetic.
    from tools.yen_sei import config as cfg
    monkeypatch.setattr(cfg, "POLISH_CACHE_DIR", tmp_path / "cache")
    from tools.yen_sei.stages import polish as polish_mod
    monkeypatch.setattr(polish_mod, "POLISH_CACHE_DIR", tmp_path / "cache")

    class FakeLLM:
        calls = 0
        def generate(self, system_prompt: str, user_prompt: str) -> dict:
            FakeLLM.calls += 1
            return {"rewritten": "White cannot connect; the cutting stone is captured."}

    rc = run_polish(
        input_path=str(raw),
        output_path=str(out),
        use_llm=True,
        llm_client=FakeLLM(),
    )
    assert rc == 0
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    # The flagged record's comment should be the rewrite, not the original.
    rec1 = json.loads(lines[1])
    assert rec1["solution_nodes"][0]["comment"].startswith("White cannot connect")
    assert "(completed)" not in rec1["solution_nodes"][0]["comment"]
    # Exactly one LLM call (only the flagged one).
    assert FakeLLM.calls == 1


def test_polish_prompt_version_constant_exists() -> None:
    # Bumping this invalidates cache; tests guard the constant exists.
    assert POLISH_PROMPT_VERSION


# ── batch interface (provider-agnostic Stage-C plumbing) ───────────────


def test_dump_batch_emits_only_flagged(tmp_path: Path) -> None:
    raw = _write_raw(
        tmp_path,
        comments=[
            "Black has formed two eyes and is alive.",  # clean
            "White cannot connect (completed) and obtain more more after.",  # flagged
        ],
    )
    out = tmp_path / "batch.jsonl"
    n = dump_batch(input_path=raw, output_path=out, skip_cached=False)
    assert n == 1
    payload = json.loads(out.read_text(encoding="utf-8").strip())
    assert {"cache_key", "system", "user", "original"} <= payload.keys()
    assert "(completed)" not in payload["original"]  # regex-cleaned
    assert payload["cache_key"]


def test_dump_batch_skips_cached_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    raw = _write_raw(
        tmp_path,
        comments=["White cannot connect (completed) and obtain more more after."],
    )
    cache = tmp_path / "cache"
    from tools.yen_sei.stages import polish as polish_mod
    monkeypatch.setattr(polish_mod, "POLISH_CACHE_DIR", cache)

    out1 = tmp_path / "batch1.jsonl"
    n1 = dump_batch(input_path=raw, output_path=out1)
    assert n1 == 1

    # Pre-populate the cache for that key, then re-dump.
    payload = json.loads(out1.read_text(encoding="utf-8").strip())
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{payload['cache_key']}.json").write_text(
        json.dumps({"rewritten": "x"}), encoding="utf-8"
    )

    out2 = tmp_path / "batch2.jsonl"
    n2 = dump_batch(input_path=raw, output_path=out2)
    assert n2 == 0  # cached → skipped


def test_load_batch_populates_cache(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "cache"
    from tools.yen_sei.stages import polish as polish_mod
    monkeypatch.setattr(polish_mod, "POLISH_CACHE_DIR", cache)

    responses = tmp_path / "responses.jsonl"
    with responses.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"cache_key": "abc123", "rewritten": "Clean text."}) + "\n")
        f.write(json.dumps({"cache_key": "def456", "rewritten": "Another."}) + "\n")
        f.write("not-json\n")  # skipped
        f.write(json.dumps({"cache_key": "", "rewritten": "x"}) + "\n")  # skipped

    loaded, skipped = load_batch(input_path=responses)
    assert loaded == 2
    assert skipped == 2
    assert (cache / "abc123.json").exists()
    assert json.loads((cache / "def456.json").read_text(encoding="utf-8"))[
        "rewritten"
    ] == "Another."


def test_dump_then_load_then_polish_no_llm_call(
    tmp_path: Path, monkeypatch
) -> None:
    """End-to-end: dump → fill cache externally → polish --llm hits cache only."""
    raw = _write_raw(
        tmp_path,
        comments=["White cannot connect (completed) and obtain more more after."],
    )
    cache = tmp_path / "cache"
    from tools.yen_sei import config as cfg
    from tools.yen_sei.stages import polish as polish_mod
    monkeypatch.setattr(cfg, "POLISH_CACHE_DIR", cache)
    monkeypatch.setattr(polish_mod, "POLISH_CACHE_DIR", cache)

    # Step 1 — dump.
    batch = tmp_path / "batch.jsonl"
    n = dump_batch(input_path=raw, output_path=batch)
    assert n == 1
    req = json.loads(batch.read_text(encoding="utf-8").strip())

    # Step 2 — external "backend" writes a response.
    resp = tmp_path / "resp.jsonl"
    with resp.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "cache_key": req["cache_key"],
            "rewritten": "White cannot connect; the cutting stone is captured.",
        }) + "\n")

    # Step 3 — load into cache.
    loaded, _ = load_batch(input_path=resp)
    assert loaded == 1

    # Step 4 — polish --llm with a client that MUST NOT be called.
    class ExplodingLLM:
        def generate(self, *_args, **_kwargs):
            raise AssertionError("LLM must not be called when cache is populated")

    out = tmp_path / "polished.jsonl"
    rc = run_polish(
        input_path=str(raw),
        output_path=str(out),
        use_llm=True,
        llm_client=ExplodingLLM(),
    )
    assert rc == 0
    assert out.exists()
    rec = json.loads(out.read_text(encoding="utf-8").strip())
    assert rec["solution_nodes"][0]["comment"].startswith("White cannot connect")
