"""Windows-only accepted-stream adapter using public socket/asyncio APIs.

Python 3.12 Proactor calls shutdown before socket.close. A peer reset can raise
WinError 10054 at that point, preventing normal transport cleanup. Only sockets
accepted by OUR listener are wrapped, before passing ownership to Streams. The
wrapper treats that exact already-reset condition as no remaining half-close;
every other error is still a failure. No transport socket/private state, stdlib
patch, exception filter, thread, SOCKS code or DNS policy belongs here.
"""

import asyncio
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial

StreamHandler = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]
_CLOSE_TIMEOUT_SECONDS = 1.5  # Inside the proxy's existing two-second close bound.


def _is_peer_reset(error: BaseException) -> bool:
    return isinstance(error, ConnectionResetError) and getattr(error, "winerror", None) == 10054


def _is_completed_read_reset(error: BaseException, reader: asyncio.StreamReader) -> bool:
    # Windows Proactor reports ERROR_NETNAME_DELETED (64) as the terminal read
    # reset too. Accept ONLY the identical reset already delivered by this
    # public reader, not an independent shutdown/write/cleanup exception.
    return _is_peer_reset(error) or (isinstance(error, ConnectionResetError) and getattr(error, "winerror", None) == 64 and error is reader.exception())


@dataclass
class _ShutdownOutcome:
    failed: bool = False


def _shutdown(action: Callable[[], None], outcome: _ShutdownOutcome | None = None) -> None:
    try:
        action()
    except Exception as error:
        if not _is_peer_reset(error):
            if outcome is not None:
                outcome.failed = True
            raise


class _AcceptedSocket(socket.socket):
    def __init__(self, family: int = socket.AF_INET, type: int = socket.SOCK_STREAM, proto: int = 0, fileno: int | None = None) -> None:
        super().__init__(family, type, proto, fileno)
        self.shutdown_outcome = _ShutdownOutcome()

    def shutdown(self, how: int) -> None:
        _shutdown(partial(super().shutdown, how), self.shutdown_outcome)


def _take_socket(raw: socket.socket) -> _AcceptedSocket:
    """Only call on our raw accepted socket, before ANY transport owns it."""
    family, kind, protocol = raw.family, raw.type, raw.proto
    handle = raw.detach()
    try:
        owned = _AcceptedSocket(family, kind, protocol, fileno=handle)
    except BaseException:
        # Windows SOCKET handles require socket.close, never os.close.
        socket.close(handle)
        raise
    try:
        owned.setblocking(False)
    except BaseException:
        owned.close()
        raise
    return owned


async def _open_stream(owned: _AcceptedSocket) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    # Public API transfers ownership. Only StreamWriter methods are used after
    # this call; never inspect/close the raw socket behind its transport.
    return await asyncio.open_connection(sock=owned)


class WindowsStreamServer:
    """Small server interface consumed by BrowserEgressProxy, not a general server.

    Closing rejects new accepts and cancels active callbacks. In-flight Streams
    handoffs finish before their returned writers close; the wait is bounded.
    Raw sockets remain tracked until detach or explicit close, including tasks
    cancelled before their first instruction. Wrapper tasks stay tracked through
    writer.wait_closed even if the user callback already removed its own entry.
    """

    def __init__(self, listener: socket.socket, handler: StreamHandler) -> None:
        self._listener = listener
        self._handler = handler
        self._loop = asyncio.get_running_loop()
        self._closing = False
        self._failed = False
        self._raw: set[socket.socket] = set()
        self._writers: set[asyncio.StreamWriter] = set()
        self._handlers: set[asyncio.Task] = set()
        self._opening: set[asyncio.Task] = set()
        self._finishing: set[asyncio.Task] = set()
        self._task_writers: dict[asyncio.Task, asyncio.StreamWriter] = {}
        self._outcomes: list[_ShutdownOutcome] = []
        self._accept_task: asyncio.Task | None = None

    @property
    def sockets(self) -> tuple[socket.socket, ...]:
        # For the owner's bound-port lookup; callers do not acquire ownership.
        return () if self._closing else (self._listener,)

    def _close_raw(self, raw: socket.socket) -> None:
        if raw in self._raw:
            self._raw.discard(raw)
            try:
                raw.close()
            except Exception:
                self._failed = True

    def _client_done(self, raw: socket.socket, task: asyncio.Task) -> None:
        self._close_raw(raw)  # Also runs when the coroutine never started.
        self._opening.discard(task)
        self._finishing.discard(task)
        self._task_writers.pop(task, None)
        self._handlers.discard(task)
        if not task.cancelled() and task.exception() is not None:
            self._failed = True

    def _spawn_client(self, raw: socket.socket) -> None:
        self._raw.add(raw)
        if self._closing:
            self._close_raw(raw)
            return
        coroutine = self._serve(raw)
        try:
            task = asyncio.create_task(coroutine)
        except BaseException:
            coroutine.close()
            self._close_raw(raw)
            raise
        self._handlers.add(task)
        task.add_done_callback(partial(self._client_done, raw))

    async def _accept(self) -> None:
        try:
            while not self._closing:
                raw, _address = await self._loop.sock_accept(self._listener)
                self._spawn_client(raw)
        except asyncio.CancelledError:
            if not self._closing:
                self._failed = True
            raise
        except Exception:
            self._failed = True
            self.close()

    async def _serve(self, raw: socket.socket) -> None:
        task = asyncio.current_task()
        assert task is not None
        writer: asyncio.StreamWriter | None = None
        try:
            if self._closing:
                return
            owned = _take_socket(raw)
            # Keep only our independent outcome record after Streams takes the
            # socket. No later transport socket inspection or manual close.
            self._outcomes.append(owned.shutdown_outcome)
            self._raw.discard(raw)  # Detached: this raw object owns no handle.
            self._opening.add(task)
            try:
                reader, writer = await _open_stream(owned)
            finally:
                self._opening.discard(task)
            self._writers.add(writer)
            self._task_writers[task] = writer
            if not self._closing:
                await self._handler(reader, writer)
        except asyncio.CancelledError:
            if not self._closing:
                self._failed = True
            raise
        except Exception:
            # Owner observes a fixed failure in wait_closed; never log raw data.
            self._failed = True
        finally:
            self._close_raw(raw)
            if writer is not None:
                self._finishing.add(task)
                try:
                    writer.close()
                except Exception:
                    self._failed = True
                try:
                    await writer.wait_closed()
                except asyncio.CancelledError:
                    self._failed = True
                    raise
                except Exception as error:
                    # wait_closed can report the already-delivered peer reset,
                    # after the corrected transport has completed actual close.
                    if not _is_completed_read_reset(error, reader):
                        self._failed = True
                finally:
                    self._writers.discard(writer)
                    self._finishing.discard(task)
                    self._task_writers.pop(task, None)

    def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._accept_task is not None:
            self._accept_task.cancel()
        try:
            self._listener.close()
        except Exception:
            self._failed = True
        for raw in list(self._raw):
            self._close_raw(raw)
        already_closing = set()
        for task, writer in self._task_writers.items():
            if writer.is_closing():
                already_closing.add(task)
        for writer in list(self._writers):
            try:
                writer.close()
            except Exception:
                self._failed = True
        for task in list(self._handlers):
            if task not in self._opening and task not in self._finishing and task not in already_closing:
                task.cancel()

    async def wait_closed(self) -> None:
        if not self._closing:
            raise RuntimeError("browser_stream_close_required")
        tasks = set(self._handlers)
        if self._accept_task is not None:
            tasks.add(self._accept_task)
        if tasks:
            _done, pending = await asyncio.wait(tasks, timeout=_CLOSE_TIMEOUT_SECONDS * 2 / 3)
            if pending:
                self._failed = True
                for task in pending:
                    task.cancel()
                _done, pending = await asyncio.wait(pending, timeout=_CLOSE_TIMEOUT_SECONDS / 3)
                if pending:
                    self._failed = True
        if self._failed or any(outcome.failed for outcome in self._outcomes):
            raise RuntimeError("browser_stream_cleanup_failed") from None


async def start_windows_server(handler: StreamHandler) -> WindowsStreamServer:
    """Bind only our ephemeral loopback listener; no remote-listening option."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setblocking(False)
        listener.bind(("127.0.0.1", 0))
        listener.listen(socket.SOMAXCONN)
        server = WindowsStreamServer(listener, handler)
        coroutine = server._accept()
        try:
            server._accept_task = asyncio.create_task(coroutine)
        except BaseException:
            coroutine.close()
            raise
        return server
    except BaseException:
        listener.close()
        raise
