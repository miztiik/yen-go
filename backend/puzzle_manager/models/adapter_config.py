"""Pydantic wire contracts for ``adapter-config`` CLI subcommands (Theme 7).

Theme 7a (this slice): read-only inspection — ``list``, ``show``, ``validate-all``.

Mutating subcommands (``add``/``clone``/``update``/``remove``) and the
``bootstrap`` wizard are layered on later slices and reuse these models
where shapes overlap.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AdapterSourceEntry(BaseModel):
    """One row in ``sources.json`` augmented with read-only derived flags.

    The base shape (``id``/``name``/``adapter``/``config``) mirrors the
    on-disk schema 1:1 so callers can round-trip. Derived fields
    (``active``, ``path_exists``) are computed by the CLI for the table
    columns the dashboard List pane renders.
    """

    id: str
    name: str
    adapter: str
    config: dict[str, Any] = Field(default_factory=dict)
    active: bool = False
    path_exists: bool | None = Field(
        default=None,
        description=(
            "True/False when the source's ``config.path`` points at an existing "
            "directory; None when the adapter kind has no path-based config "
            "(e.g., HTTP-only adapters like sanderland)."
        ),
    )


class AdapterConfigList(BaseModel):
    """Payload for ``adapter-config list --json``."""

    active_adapter: str | None
    sources: list[AdapterSourceEntry]


class AdapterConfigShow(BaseModel):
    """Payload for ``adapter-config show ID --json``.

    Carries the single source entry plus the schema fragment for its
    adapter kind so the dashboard form can render schema-driven fields
    without re-encoding the schema. ``available_kinds`` lists every
    adapter registered in the running pipeline so the operator can
    switch kinds when editing.
    """

    source: AdapterSourceEntry
    adapter_kind: str
    schema_for_kind: dict[str, Any] | None = Field(
        default=None,
        description=(
            "JSON Schema fragment for this adapter kind, sourced from "
            "``sources.schema.json``'s ``$defs`` (e.g., ``LocalConfig``). "
            "None when no per-kind schema exists — the form should render a "
            "generic key/value editor in that case."
        ),
    )
    available_kinds: list[str]


class AdapterValidationIssue(BaseModel):
    """One validation problem on a single source entry."""

    code: str
    message: str
    field: str | None = None


class AdapterValidationRow(BaseModel):
    """``adapter-config validate-all`` row — one per configured source."""

    id: str
    ok: bool
    errors: list[AdapterValidationIssue] = Field(default_factory=list)


class AdapterValidationReport(BaseModel):
    """Payload for ``adapter-config validate-all --json``."""

    ok: bool
    rows: list[AdapterValidationRow]
