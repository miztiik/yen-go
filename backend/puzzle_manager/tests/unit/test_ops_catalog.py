"""Unit tests for ``ops catalog`` (Theme 16a).

Two layers:

1. **Catalog shape** — Pydantic validates each entry; every section/scope token
   the dashboard depends on is present.
2. **Drift fence** — every CLI subcommand that mutates on-disk state has a
   row in :data:`OPS_CATALOG`. Adding a new mutating subcommand without
   registering it must fail this test (that's the whole point — the catalog
   is the single source of truth, not a hint).
"""

from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace

import pytest

from backend.puzzle_manager.cli import cmd_ops
from backend.puzzle_manager.models.ops_catalog import (
    OPS_CATALOG,
    OpsCatalogEntry,
    get_ops_catalog,
)

# Canonical list of mutating CLI invocation tokens. If you add a new one,
# add it here AND register it in OPS_CATALOG. The drift-fence test below
# enforces both directions.
EXPECTED_MUTATING_OPS = {
    "clean",
    "run --fresh",
    "rollback",
    "vacuum-db",
    "inventory rebuild",
    "inventory reconcile",
    "inventory fix",
    "enable-adapter",
    "disable-adapter",
    "config-lock release",
    "source-ingest-state --reset",
    "adapter-scaffold",
}


class TestCatalogShape:
    def test_every_entry_validates(self) -> None:
        # Pydantic re-validation catches drift if someone hand-edits the list.
        for entry in OPS_CATALOG:
            roundtrip = OpsCatalogEntry.model_validate(entry.model_dump())
            assert roundtrip == entry

    def test_destructive_entries_have_irreversible_or_audit_recovery(self) -> None:
        # Section is presentation; this asserts the *meaning* lines up.
        # An op flagged "destructive" must NOT be plain reversible=True.
        for entry in OPS_CATALOG:
            if entry.section == "destructive":
                assert entry.reversible is not True, (
                    f"{entry.op}: destructive section but reversible=True "
                    "(should be False or 'by-audit-trail')"
                )

    def test_get_ops_catalog_returns_independent_copy(self) -> None:
        a = get_ops_catalog()
        b = get_ops_catalog()
        a.clear()
        assert b, "get_ops_catalog() must not share list state with OPS_CATALOG"
        assert OPS_CATALOG, "module-level OPS_CATALOG mutated via copy"


class TestDriftFence:
    def test_catalog_covers_every_known_mutating_op(self) -> None:
        registered = {entry.op for entry in OPS_CATALOG}
        missing = EXPECTED_MUTATING_OPS - registered
        extra = registered - EXPECTED_MUTATING_OPS
        assert not missing, (
            f"OPS_CATALOG is missing entries for: {sorted(missing)}. "
            "Adding a new mutating CLI subcommand requires registering it in "
            "backend/puzzle_manager/models/ops_catalog.py."
        )
        assert not extra, (
            f"OPS_CATALOG has entries not in EXPECTED_MUTATING_OPS: {sorted(extra)}. "
            "Either remove the catalog row or update EXPECTED_MUTATING_OPS."
        )

    def test_no_duplicate_ops(self) -> None:
        ops = [entry.op for entry in OPS_CATALOG]
        assert len(ops) == len(set(ops)), f"duplicate op token: {ops}"


class TestCmdOpsHandler:
    def test_json_emits_valid_catalog(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cmd_ops(Namespace(ops_action="catalog", json=True))
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        assert len(payload) == len(OPS_CATALOG)
        # Every emitted row must round-trip through the model.
        for row in payload:
            OpsCatalogEntry.model_validate(row)

    def test_human_format_includes_every_op(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cmd_ops(Namespace(ops_action="catalog", json=False))
        assert rc == 0
        out = capsys.readouterr().out
        for entry in OPS_CATALOG:
            assert entry.op in out, f"op token {entry.op!r} missing from human output"

    def test_no_subaction_prints_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cmd_ops(Namespace(ops_action=None))
        assert rc == 0
        assert "ops catalog" in capsys.readouterr().out


@pytest.mark.cli
class TestSubprocess:
    def test_ops_catalog_json_via_subprocess(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "backend.puzzle_manager", "ops", "catalog", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        ops = {row["op"] for row in payload}
        assert "clean" in ops
        assert "rollback" in ops
        assert "inventory fix" in ops
