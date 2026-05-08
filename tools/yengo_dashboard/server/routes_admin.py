"""Short-running admin routes for yengo_dashboard.

These wrap ``puzzle_manager`` subcommands that complete in well under a
second and have no streaming output worth surfacing live: setting/clearing
the active adapter and querying the publish-log audit trail. They go
straight through ``PipelineRunner`` (synchronous subprocess) rather than
``RunController`` (long-lived stream + busy-guard).

Adapter mutations DO NOT participate in the single-active-run guard. The
config-lock the CLI takes internally is the right serialization point —
it's what protects ``sources.json`` from concurrent edits whether the
edit comes from the cockpit or a terminal. ``--force/-f`` is forwarded so
the operator can break a stale lock without leaving the UI.

Endpoints
---------

- ``POST /api/adapter/enable``     — ``enable-adapter ADAPTER_ID [--force]``
- ``POST /api/adapter/disable``    — ``disable-adapter [--force]``
- ``GET  /api/publish-log/search`` — ``publish-log search --format json …``
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from tools.yengo_dashboard.server.models import (
    AdapterScaffoldRequest,
    AdapterScaffoldResponse,
    CliInvocationResponse,
    DisableAdapterRequest,
    EnableAdapterRequest,
    LevelsRenamePreviewRequest,
    PublishLogSearchResponse,
    TagsMergePreviewRequest,
    TagsRenamePreviewRequest,
    TaxonomyMutationApplyResponse,
    TaxonomyMutationPreviewResponse,
)
from tools.yengo_dashboard.server.pipeline_runner import PipelineCommandError, PipelineRunner


def build_admin_router(*, runner: PipelineRunner) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["admin"])

    @router.post("/adapter/enable", response_model=CliInvocationResponse)
    def enable_adapter(body: EnableAdapterRequest) -> CliInvocationResponse:
        # Like lock_release: never raises on non-zero exit. The CLI's stderr
        # ("config locked", "unknown adapter id", etc.) is the operator-facing
        # answer and must reach the UI verbatim, not be hidden behind a 502.
        result = runner.enable_adapter(body.adapter_id, force=body.force)
        return CliInvocationResponse(**result)

    @router.post("/adapter/disable", response_model=CliInvocationResponse)
    def disable_adapter(body: DisableAdapterRequest) -> CliInvocationResponse:
        result = runner.disable_adapter(force=body.force)
        return CliInvocationResponse(**result)

    @router.get("/publish-log/search", response_model=PublishLogSearchResponse)
    def publish_log_search(
        run_id: str | None = Query(default=None),
        puzzle_id: str | None = Query(default=None),
        source: str | None = Query(default=None),
        trace_id: str | None = Query(default=None),
        date: str | None = Query(default=None, description="YYYY-MM-DD"),
        from_: str | None = Query(default=None, alias="from", description="YYYY-MM-DD"),
        to: str | None = Query(default=None, description="YYYY-MM-DD"),
        limit: int | None = Query(default=None, ge=1),
    ) -> PublishLogSearchResponse:
        params = {
            "run_id": run_id,
            "puzzle_id": puzzle_id,
            "source": source,
            "trace_id": trace_id,
            "date": date,
            "from": from_,
            "to": to,
            "limit": limit,
        }
        try:
            payload = runner.publish_log_search(params)
        except PipelineCommandError as exc:
            # The CLI rejects searches with no filter at all. Translate that
            # to 400 so the UI can show the operator a meaningful error
            # without round-tripping a generic 502. The CLI's hint message
            # ("Use one of: --run-id, ...") goes to stdout, not stderr, so
            # we surface both streams.
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "publish-log search failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return PublishLogSearchResponse(raw=payload)

    @router.post("/tags/rename/preview", response_model=TaxonomyMutationPreviewResponse)
    def tags_rename_preview(body: TagsRenamePreviewRequest) -> TaxonomyMutationPreviewResponse:
        """Theme 11: dry-run preview of `tags rename` (read-only)."""
        try:
            payload = runner.tags_rename_preview(old=body.old, new=body.new)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager tags rename preview failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationPreviewResponse(raw=payload)

    @router.post("/tags/rename/apply", response_model=TaxonomyMutationApplyResponse)
    def tags_rename_apply(body: TagsRenamePreviewRequest) -> TaxonomyMutationApplyResponse:
        """Theme 11 (4a): apply `tags rename` (rewrites SGFs + config/tags.json)."""
        try:
            payload = runner.tags_rename_apply(old=body.old, new=body.new)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager tags rename apply failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationApplyResponse(raw=payload)

    @router.post("/tags/merge/preview", response_model=TaxonomyMutationPreviewResponse)
    def tags_merge_preview(body: TagsMergePreviewRequest) -> TaxonomyMutationPreviewResponse:
        """Theme 11: dry-run preview of `tags merge` (read-only)."""
        try:
            payload = runner.tags_merge_preview(sources=body.sources, target=body.target)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager tags merge preview failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationPreviewResponse(raw=payload)

    @router.post("/tags/merge/apply", response_model=TaxonomyMutationApplyResponse)
    def tags_merge_apply(body: TagsMergePreviewRequest) -> TaxonomyMutationApplyResponse:
        """Theme 11 (4a): apply `tags merge` (rewrites SGFs + config/tags.json)."""
        try:
            payload = runner.tags_merge_apply(sources=body.sources, target=body.target)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager tags merge apply failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationApplyResponse(raw=payload)

    @router.post("/levels/rename/preview", response_model=TaxonomyMutationPreviewResponse)
    def levels_rename_preview(body: LevelsRenamePreviewRequest) -> TaxonomyMutationPreviewResponse:
        """Theme 11: dry-run preview of `levels rename` (read-only)."""
        try:
            payload = runner.levels_rename_preview(old=body.old, new=body.new)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager levels rename preview failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationPreviewResponse(raw=payload)

    @router.post("/levels/rename/apply", response_model=TaxonomyMutationApplyResponse)
    def levels_rename_apply(body: LevelsRenamePreviewRequest) -> TaxonomyMutationApplyResponse:
        """Theme 11 (4a): apply `levels rename` (rewrites SGFs + config/puzzle-levels.json)."""
        try:
            payload = runner.levels_rename_apply(old=body.old, new=body.new)
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager levels rename apply failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return TaxonomyMutationApplyResponse(raw=payload)

    @router.post("/adapter-scaffold/preview", response_model=AdapterScaffoldResponse)
    def adapter_scaffold_preview(body: AdapterScaffoldRequest) -> AdapterScaffoldResponse:
        """Theme 12: dry-run preview of `adapter-scaffold`."""
        try:
            payload = runner.adapter_scaffold(
                new_id=body.new_id, kind=body.kind,
                name=body.name, path=body.path,
                dry_run=True, force=body.force,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager adapter-scaffold preview failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterScaffoldResponse(raw=payload)

    @router.post("/adapter-scaffold/apply", response_model=AdapterScaffoldResponse)
    def adapter_scaffold_apply(body: AdapterScaffoldRequest) -> AdapterScaffoldResponse:
        """Theme 12: apply `adapter-scaffold` (writes adapter package + sources.json)."""
        try:
            payload = runner.adapter_scaffold(
                new_id=body.new_id, kind=body.kind,
                name=body.name, path=body.path,
                dry_run=False, force=body.force,
            )
        except PipelineCommandError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "puzzle_manager adapter-scaffold apply failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.strip()[:500],
                    "stdout": exc.stdout.strip()[:500],
                },
            ) from exc
        return AdapterScaffoldResponse(raw=payload)

    return router
