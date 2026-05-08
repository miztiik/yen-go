"""Pydantic shape for ``ops catalog`` (Theme 16a).

Theme 16a wire contract: enumerates every mutating CLI subcommand with its
blast-radius classification so the dashboard can render consistent guardrails
(typed-confirm, preview gate, section grouping) from a single source of truth
instead of re-encoding the taxonomy in JS.

The catalog is the authority. If a CLI mutating subcommand is added without
registering an entry here, the drift-fence test
(``tests/unit/test_ops_catalog.py``) fails — that's the intended pressure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Layers a destructive op can touch. Names are presentation-stable: the
# dashboard groups buttons by these tokens, so renaming one is a wire break.
OpsScope = Literal[
    "staging",            # .pm-runtime/staging/ working files
    "ingest_state",       # per-source .yengo-ingest.sqlite + runtime state
    "published_corpus",   # yengo-puzzle-collections/sgf/**
    "search_db",          # yengo-search.db (browser-shipped index)
    "inventory_snapshot", # yengo-puzzle-collections/inventory.json
    "files",              # filesystem-level cleanup beyond a single layer
    "logs",               # .pm-runtime/logs/
    "runtime_state",      # .pm-runtime/state/ (current_run.json, runs/*.json)
]

# "by-audit-trail" means the action *can* be undone but only by replaying the
# audit log / publish log — not by a single counter-command. The UI treats
# this as "reversible-with-ceremony", which is louder than a plain reversible.
OpsReversible = bool | Literal["by-audit-trail"]


class OpsCatalogEntry(BaseModel):
    """One mutating CLI subcommand and its blast-radius classification."""

    op: str = Field(
        ...,
        description=(
            "CLI invocation token as the operator would type it, e.g. "
            "`clean`, `run --fresh`, `inventory fix`. Includes the "
            "discriminating flag when the same subcommand has multiple "
            "blast-radius modes."
        ),
    )
    scope: list[OpsScope] = Field(
        ...,
        min_length=1,
        description="On-disk layers the op mutates. Order is presentation order.",
    )
    reversible: OpsReversible = Field(
        ...,
        description=(
            "True if a single counter-command restores prior state, False if "
            "data is gone, or 'by-audit-trail' if recoverable only via replay."
        ),
    )
    preview_supported: bool = Field(
        ...,
        description=(
            "True if the op accepts ``--dry-run --json`` and emits a Pydantic "
            "preview the dashboard can render before commit."
        ),
    )
    section: Literal["maintenance", "destructive", "diagnostic"] = Field(
        ...,
        description=(
            "Operations-page grouping. ``destructive`` triggers the "
            "typed-confirm dialog client-side."
        ),
    )
    summary: str = Field(
        ...,
        description="One-line operator-facing description for tooltips.",
    )


# Single source of truth. The drift-fence test asserts that every
# `cmd_*` function in cli.py that mutates state has a row here.
OPS_CATALOG: list[OpsCatalogEntry] = [
    OpsCatalogEntry(
        op="clean",
        scope=["staging", "logs", "runtime_state"],
        reversible=True,
        preview_supported=True,
        section="maintenance",
        summary="Remove .pm-runtime/{staging,logs,state} files (per --target).",
    ),
    OpsCatalogEntry(
        op="run --fresh",
        scope=["staging", "ingest_state", "runtime_state"],
        reversible=False,
        preview_supported=False,
        section="destructive",
        summary="Wipe per-source ingest DB + runtime state, then run pipeline.",
    ),
    OpsCatalogEntry(
        op="rollback",
        scope=["published_corpus", "search_db"],
        reversible="by-audit-trail",
        preview_supported=True,
        section="destructive",
        summary="Remove a published run's puzzles from the corpus + search DB.",
    ),
    OpsCatalogEntry(
        op="vacuum-db",
        scope=["search_db"],
        reversible=True,
        preview_supported=True,
        section="maintenance",
        summary="Compact yengo-search.db; --rebuild reconstructs from corpus.",
    ),
    OpsCatalogEntry(
        op="inventory rebuild",
        scope=["inventory_snapshot"],
        reversible=True,
        preview_supported=True,
        section="maintenance",
        summary="Rebuild inventory.json snapshot from yengo-search.db.",
    ),
    OpsCatalogEntry(
        op="inventory reconcile",
        scope=["inventory_snapshot"],
        reversible=True,
        preview_supported=True,
        section="maintenance",
        summary="Re-derive inventory aggregates without touching files.",
    ),
    OpsCatalogEntry(
        op="inventory fix",
        scope=["inventory_snapshot", "files"],
        reversible=False,
        preview_supported=True,
        section="destructive",
        summary="Delete orphan SGFs / DB rows flagged by inventory --check.",
    ),
    OpsCatalogEntry(
        op="enable-adapter",
        scope=["ingest_state"],
        reversible=True,
        preview_supported=False,
        section="maintenance",
        summary="Mark an adapter active in sources.json (config-lock guarded).",
    ),
    OpsCatalogEntry(
        op="disable-adapter",
        scope=["ingest_state"],
        reversible=True,
        preview_supported=False,
        section="maintenance",
        summary="Clear the active adapter in sources.json.",
    ),
    OpsCatalogEntry(
        op="config-lock release",
        scope=["runtime_state"],
        reversible=True,
        preview_supported=False,
        section="maintenance",
        summary="Release a stuck pipeline config-lock (use --force if foreign).",
    ),
    OpsCatalogEntry(
        op="adapter-scaffold",
        scope=["ingest_state", "files"],
        reversible=False,
        preview_supported=True,
        section="destructive",
        summary="Generate a new adapter package + sources.json stub from a template.",
    ),
    OpsCatalogEntry(
        op="source-ingest-state --reset",
        scope=["ingest_state"],
        reversible=False,
        preview_supported=True,
        section="destructive",
        summary="Wipe a single source's .yengo-ingest.sqlite (forces full re-ingest).",
    ),
]


def get_ops_catalog() -> list[OpsCatalogEntry]:
    """Return a fresh list copy of the catalog (callers may mutate freely)."""
    return list(OPS_CATALOG)
