from __future__ import annotations

from pathlib import Path

from tools.yen_sei import data_paths


def test_stamped_path_uses_numeric_prefix(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data_paths, "DATA_DIR", tmp_path)

    p = data_paths.stamped_path("qualification", "jsonl", tmp_path, ts="20260419T1200")
    assert p.name == "20260419120000_qualification.jsonl"

    latest = data_paths.latest_pointer("qualification", "jsonl", tmp_path, ts="20260419T1200")
    assert latest.name == "20260419120000_qualification_latest.jsonl"


def test_resolve_latest_supports_prefix_and_legacy_suffix(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data_paths, "DATA_DIR", tmp_path)

    legacy = tmp_path / "qualification_20260419T1258.jsonl"
    legacy.write_text("legacy\n", encoding="utf-8")

    newer = tmp_path / "20260419130000_qualification.jsonl"
    newer.write_text("new\n", encoding="utf-8")

    resolved = data_paths.resolve_latest("qualification", "jsonl", tmp_path)
    assert resolved == newer

    legacy_pointer = tmp_path / "qualification_latest.jsonl"
    legacy_pointer.write_text("legacy-ptr\n", encoding="utf-8")
    pref_pointer = tmp_path / "20260419130000_qualification_latest.jsonl"
    pref_pointer.write_text("pref-ptr\n", encoding="utf-8")

    resolved_ptr = data_paths.resolve_latest_pointer("qualification", "jsonl", tmp_path)
    assert resolved_ptr == pref_pointer
