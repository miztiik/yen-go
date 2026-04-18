"""Event emitter for yen-sei pipeline.

Bridges pipeline stages to SSE streams and log files.
Inspired by tools/puzzle-enrichment-lab/bridge.py event queue pattern.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from tools.yen_sei.models.pipeline_event import PipelineEvent


class EventEmitter:
    """Async event emitter that bridges pipeline stages to SSE consumers."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[PipelineEvent | None] = asyncio.Queue()
        self._trace_id = uuid.uuid4().hex[:12]

    @property
    def trace_id(self) -> str:
        return self._trace_id

    async def emit(
        self,
        stage: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        progress_pct: float | None = None,
    ) -> None:
        """Push an event onto the queue."""
        event = PipelineEvent(
            stage=stage,
            event_type=event_type,  # type: ignore[arg-type]
            data=data or {},
            trace_id=self._trace_id,
            progress_pct=progress_pct,
        )
        await self._queue.put(event)

    async def close(self) -> None:
        """Signal end of event stream."""
        await self._queue.put(None)

    async def stream(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings. Terminates on None sentinel."""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event.to_sse()


class SyncEventEmitter:
    """Synchronous event emitter for non-async pipeline stages (harvest, refine)."""

    def __init__(self) -> None:
        self._trace_id = uuid.uuid4().hex[:12]
        self._events: list[PipelineEvent] = []

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def events(self) -> list[PipelineEvent]:
        return self._events

    def emit(
        self,
        stage: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        progress_pct: float | None = None,
    ) -> None:
        """Record an event."""
        event = PipelineEvent(
            stage=stage,
            event_type=event_type,  # type: ignore[arg-type]
            data=data or {},
            trace_id=self._trace_id,
            progress_pct=progress_pct,
        )
        self._events.append(event)
