from __future__ import annotations

import json
import re

from backend.puzzle_manager.core.db_models import (
    CollectionMeta,
    DbVersionInfo,
    PuzzleEntry,
    generate_db_version,
    sgf_to_puzzle_entry,
)


class TestPuzzleEntryDefaults:
    def test_puzzle_entry_defaults(self) -> None:
        entry = PuzzleEntry(content_hash="abcdef0123456789", batch="0001", level_id=120)
        assert entry.quality == 0
        assert entry.content_type == 2
        assert entry.cx_depth == 0
        assert entry.cx_refutations == 0
        assert entry.cx_solution_len == 0
        assert entry.cx_unique_resp == 0
        assert entry.ac == 0
        assert entry.tag_ids == []
        assert entry.collection_ids == []
        assert entry.attrs == {}

    def test_puzzle_entry_puzzle_id(self) -> None:
        entry = PuzzleEntry(content_hash="abcdef0123456789", batch="0001", level_id=120)
        assert entry.puzzle_id == "abcdef0123456789"

    def test_puzzle_entry_compact_path(self) -> None:
        entry = PuzzleEntry(content_hash="abcdef0123456789", batch="0002", level_id=130)
        assert entry.compact_path == "0002/abcdef0123456789"


class TestCollectionMetaDefaults:
    def test_collection_meta_defaults(self) -> None:
        meta = CollectionMeta(collection_id=5, slug="cho-elementary", name="Cho Elementary")
        assert meta.category is None
        assert meta.puzzle_count == 0
        assert meta.attrs == {}


class TestDbVersionInfo:
    def test_db_version_info_to_dict(self) -> None:
        info = DbVersionInfo(
            db_version="20260313-aabbccdd",
            puzzle_count=42,
            generated_at="2026-03-13T10:00:00Z",
        )
        d = info.to_dict()
        assert d == {
            "db_version": "20260313-aabbccdd",
            "puzzle_count": 42,
            "generated_at": "2026-03-13T10:00:00Z",
            "schema_version": 2,
        }


class TestGenerateDbVersion:
    def test_generate_db_version_format(self) -> None:
        version = generate_db_version()
        assert re.fullmatch(r"\d{8}-[0-9a-f]{8}", version), f"Bad format: {version}"

    def test_deterministic_with_same_hashes(self) -> None:
        hashes = ["abc123", "def456", "789xyz"]
        v1 = generate_db_version(hashes)
        v2 = generate_db_version(hashes)
        assert v1 == v2, "Same hashes must produce same version"

    def test_different_hashes_different_version(self) -> None:
        v1 = generate_db_version(["abc123"])
        v2 = generate_db_version(["def456"])
        # Same date prefix, different hash suffix
        assert v1[:9] == v2[:9]  # YYYYMMDD-
        assert v1[9:] != v2[9:]

    def test_order_independent(self) -> None:
        v1 = generate_db_version(["abc", "def", "ghi"])
        v2 = generate_db_version(["ghi", "abc", "def"])
        assert v1 == v2, "Hash order should not matter (sorted internally)"


def _make_sgf_with_ym(ct: int | None = None) -> str:
    """Build a minimal valid SGF with optional content_type in YM."""
    ym_obj: dict = {"t": "0000000000000000", "i": "test-run"}
    if ct is not None:
        ym_obj["ct"] = ct
    ym_json = json.dumps(ym_obj, separators=(",", ":"))
    return (
        f"(;FF[4]GM[1]SZ[19]"
        f"YV[13]YG[elementary]YT[life-and-death]"
        f"YQ[q:2;rc:0;hc:0;ac:0]YX[d:1;r:2;s:11;u:1]"
        f"YK[none]YO[strict]YC[TL]"
        f"YM[{ym_json}]"
        f"AB[pd][qf]AW[qd][pe]"
        f";B[oe]"
        f"(;W[of];B[ne])"
        f"(;W[ne];B[of]))"
    )


class TestSgfToPuzzleEntryContentType:
    """Verify sgf_to_puzzle_entry reads content_type from YM pipeline meta."""

    def test_curated_content_type_from_ym(self, test_id_maps) -> None:
        sgf = _make_sgf_with_ym(ct=1)
        entry = sgf_to_puzzle_entry(sgf, "abcdef0123456789", test_id_maps)
        assert entry is not None
        assert entry.content_type == 1

    def test_training_content_type_from_ym(self, test_id_maps) -> None:
        sgf = _make_sgf_with_ym(ct=3)
        entry = sgf_to_puzzle_entry(sgf, "abcdef0123456789", test_id_maps)
        assert entry is not None
        assert entry.content_type == 3

    def test_defaults_to_practice_when_no_ct(self, test_id_maps) -> None:
        sgf = _make_sgf_with_ym(ct=None)
        entry = sgf_to_puzzle_entry(sgf, "abcdef0123456789", test_id_maps)
        assert entry is not None
        assert entry.content_type == 2
