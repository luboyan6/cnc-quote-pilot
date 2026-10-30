"""Postgres saver on a dedicated selector loop, compatible with Windows Proactor."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import AsyncIterator, Coroutine, Sequence
from contextlib import asynccontextmanager
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, ChannelVersions, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import AsyncConnection


class _SelectorBridge:
    """One bounded, owned event loop for psycopg operations, never inference."""

    def __init__(self) -> None:
        self.loop = asyncio.SelectorEventLoop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="agent-checkpoint", daemon=True)
        self.thread.start()

    async def call(self, operation: Coroutine[Any, Any, Any]) -> Any:
        result: concurrent.futures.Future[Any] = concurrent.futures.Future()
        settled = threading.Event()
        cancel_requested = threading.Event()
        holder: list[asyncio.Task[Any]] = []

        def begin() -> None:
            task = self.loop.create_task(operation)
            holder.append(task)

            def complete(done: asyncio.Task[Any]) -> None:
                try:
                    if done.cancelled():
                        result.cancel()
                    elif (exc := done.exception()) is not None:
                        result.set_exception(exc)
                    else:
                        result.set_result(done.result())
                finally:
                    settled.set()

            task.add_done_callback(complete)
            if cancel_requested.is_set():
                task.cancel()

        self.loop.call_soon_threadsafe(begin)
        try:
            return await asyncio.shield(asyncio.wrap_future(result))
        except asyncio.CancelledError:
            cancel_requested.set()

            def cancel() -> None:
                if holder:
                    holder[0].cancel()

            self.loop.call_soon_threadsafe(cancel)
            waiter = asyncio.create_task(asyncio.to_thread(settled.wait))
            while not waiter.done():
                try:
                    await asyncio.shield(waiter)
                except asyncio.CancelledError:
                    continue
            raise

    async def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        await asyncio.to_thread(self.thread.join)
        self.loop.close()


class BridgedPostgresSaver(BaseCheckpointSaver):
    """Expose the standard async saver on the application's running loop."""

    def __init__(self, bridge: _SelectorBridge, saver: AsyncPostgresSaver, serde: JsonPlusSerializer) -> None:
        super().__init__(serde=serde)
        self._bridge = bridge
        self._saver = saver

    def get_next_version(self, current: Any, channel: Any) -> str:
        return self._saver.get_next_version(current, channel)

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await self._bridge.call(self._saver.aget_tuple(config))

    async def alist(self, config: RunnableConfig | None, *, filter: dict[str, Any] | None = None, before: RunnableConfig | None = None, limit: int | None = None) -> AsyncIterator[CheckpointTuple]:
        async def collect() -> list[CheckpointTuple]:
            return [item async for item in self._saver.alist(config, filter=filter, before=before, limit=limit)]

        for item in await self._bridge.call(collect()):
            yield item

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: ChannelVersions) -> RunnableConfig:
        return await self._bridge.call(self._saver.aput(config, checkpoint, metadata, new_versions))

    async def aput_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        await self._bridge.call(self._saver.aput_writes(config, writes, task_id, task_path))

    async def adelete_thread(self, thread_id: str) -> None:
        await self._bridge.call(self._saver.adelete_thread(thread_id))


@asynccontextmanager
async def postgres_checkpointer(conninfo: str) -> AsyncIterator[BridgedPostgresSaver]:
    """Open a strict saver without creating or upgrading its database tables."""
    bridge = _SelectorBridge()
    serde = JsonPlusSerializer(allowed_msgpack_modules=None, allowed_json_modules=None)
    manager = AsyncPostgresSaver.from_conn_string(conninfo, serde=serde)

    async def open_saver() -> AsyncPostgresSaver:
        saver = await manager.__aenter__()
        try:
            connection = cast(AsyncConnection, saver.conn)
            cursor = await connection.execute(
                "SELECT to_regclass('checkpoints') IS NOT NULL AS checkpoints_ready, "
                "to_regclass('checkpoint_writes') IS NOT NULL AS writes_ready, "
                "to_regclass('checkpoint_blobs') IS NOT NULL AS blobs_ready"
            )
            row = await cursor.fetchone()
            values = row.values() if isinstance(row, dict) else row
            if not values or not all(values):
                raise RuntimeError("AI_CHECKPOINT_SCHEMA_NOT_INITIALIZED")
            return saver
        except BaseException:
            await manager.__aexit__(None, None, None)
            raise

    opened = False
    open_task = asyncio.create_task(bridge.call(open_saver()))
    try:
        try:
            saver = await asyncio.shield(open_task)
        except asyncio.CancelledError:
            # If cancellation races with a successful connection, wait for the
            # opener and then close it; otherwise a lost return leaks the socket.
            while not open_task.done():
                try:
                    await asyncio.shield(open_task)
                except asyncio.CancelledError:
                    continue
            if not open_task.cancelled() and open_task.exception() is None:
                opened = True
            raise
        opened = True
        yield BridgedPostgresSaver(bridge, saver, serde)
    finally:
        try:
            if opened:
                await bridge.call(manager.__aexit__(None, None, None))
        finally:
            await bridge.close()
