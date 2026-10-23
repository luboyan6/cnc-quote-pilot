"""Actual loopback TCP and narrow mocks, independently from Chromium E2E."""

import asyncio
import socket
import struct
import sys
import unittest
from contextlib import suppress
from unittest.mock import AsyncMock, Mock, patch

from _support import POLICY

from app.modules.cnc.browser import windows_streams
from app.modules.cnc.browser.third_party.egress import BrowserEgressProxy
from app.modules.cnc.browser.windows_streams import _AcceptedSocket, _is_completed_read_reset, _shutdown, _take_socket, start_windows_server


class SocketOwnershipTests(unittest.TestCase):
    def test_only_same_terminal_read_reset64_is_close_completion(self):
        read_reset = ConnectionResetError("synthetic reader reset")
        read_reset.winerror = 64
        reader = Mock(exception=Mock(return_value=read_reset))
        self.assertTrue(_is_completed_read_reset(read_reset, reader))
        different_reset = ConnectionResetError("independent cleanup error")
        different_reset.winerror = 64
        self.assertFalse(_is_completed_read_reset(different_reset, reader))
        other_error = OSError("not a connection reset")
        other_error.winerror = 64
        self.assertFalse(_is_completed_read_reset(other_error, Mock(exception=Mock(return_value=other_error))))
        other_reset = ConnectionResetError("unrelated abort")
        other_reset.winerror = 10053
        self.assertFalse(_is_completed_read_reset(other_reset, Mock(exception=Mock(return_value=other_reset))))

    def test_only_exact_windows_peer_reset_is_ignored_by_shutdown(self):
        reset = ConnectionResetError("synthetic reset")
        reset.winerror = 10054

        def fail(error):
            def operation():
                raise error

            return operation

        _shutdown(fail(reset))
        for error in (ConnectionResetError("no winerror"), OSError("different socket failure")):
            with self.subTest(error=type(error)), self.assertRaises(type(error)) as raised:
                _shutdown(fail(error))
            self.assertIs(raised.exception, error)
        other_reset = ConnectionResetError("different winerror")
        other_reset.winerror = 10053
        with self.assertRaises(ConnectionResetError) as raised:
            _shutdown(fail(other_reset))
        self.assertIs(raised.exception, other_reset)
        ordinary = OSError("same code, different error class")
        ordinary.winerror = 10054
        with self.assertRaises(OSError):
            _shutdown(fail(ordinary))

    def test_public_detach_moves_handle_once_and_real_other_errors_propagate(self):
        raw, peer = socket.socketpair()
        owned = None
        try:
            owned = _take_socket(raw)
            self.assertEqual(raw.fileno(), -1)
            self.assertIsInstance(owned, _AcceptedSocket)
            owned.send(b"synthetic")
            self.assertEqual(peer.recv(9), b"synthetic")
            owned.close()
            with self.assertRaises(OSError):
                owned.shutdown(socket.SHUT_RDWR)
            self.assertTrue(owned.shutdown_outcome.failed)
        finally:
            raw.close()
            peer.close()
            if owned is not None:
                owned.close()

    def test_wrapper_constructor_failure_closes_detached_windows_handle(self):
        raw, peer = socket.socketpair()
        handle = raw.fileno()
        try:
            with patch.object(windows_streams, "_AcceptedSocket", side_effect=ValueError("synthetic constructor")), self.assertRaises(ValueError):
                _take_socket(raw)
            self.assertEqual(raw.fileno(), -1)
            with self.assertRaises(OSError):
                unexpected = socket.socket(fileno=handle)
                unexpected.close()
        finally:
            raw.close()
            peer.close()


class WindowsListenerTests(unittest.IsolatedAsyncioTestCase):
    def assert_released(self, server):
        self.assertEqual(server.sockets, ())
        self.assertFalse(server._raw)
        self.assertFalse(server._writers)
        self.assertFalse(server._handlers)
        self.assertFalse(server._opening)
        self.assertFalse(server._finishing)
        self.assertFalse(server._task_writers)
        self.assertTrue(server._accept_task.done())

    @staticmethod
    def assert_port_released(address):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(address)

    async def test_pending_accept_and_immediate_close_release_port_and_tasks(self):
        for let_accept_start in (False, True):
            with self.subTest(let_accept_start=let_accept_start):
                callback = AsyncMock()
                server = await start_windows_server(callback)
                address = server.sockets[0].getsockname()
                if let_accept_start:
                    await asyncio.sleep(0)
                server.close()
                await server.wait_closed()
                self.assert_released(server)
                self.assert_port_released(address)
                callback.assert_not_awaited()

    async def test_client_task_cancelled_before_start_still_closes_owned_raw_socket(self):
        callback = AsyncMock()
        server = await start_windows_server(callback)
        raw, peer = socket.socketpair()
        try:
            server._spawn_client(raw)
            server.close()  # Deliberately no await after scheduling the coroutine.
            self.assertEqual(raw.fileno(), -1)
            await server.wait_closed()
            self.assert_released(server)
            callback.assert_not_awaited()
        finally:
            peer.close()
            server.close()
            await server.wait_closed()

    async def test_active_callback_cancelled_and_real_stream_writer_closed(self):
        entered = asyncio.Event()
        cancelled = asyncio.Event()

        async def callback(reader, writer):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        server = await start_windows_server(callback)
        address = server.sockets[0].getsockname()
        reader, writer = await asyncio.open_connection(*address)
        try:
            await asyncio.wait_for(entered.wait(), 2)
            server.close()
            await server.wait_closed()
            self.assertTrue(cancelled.is_set())
            self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
            self.assert_released(server)
            self.assert_port_released(address)
        finally:
            writer.close()
            await writer.wait_closed()
            server.close()
            await server.wait_closed()

    async def test_close_during_stream_handoff_waits_then_closes_without_callback(self):
        entered, release = asyncio.Event(), asyncio.Event()
        original = windows_streams._open_stream

        async def gated_open(owned):
            entered.set()
            try:
                await release.wait()
            except BaseException:
                owned.close()  # Fixture still owns it, before delegating to Streams.
                raise
            return await original(owned)

        callback = AsyncMock()
        with patch.object(windows_streams, "_open_stream", side_effect=gated_open):
            server = await start_windows_server(callback)
            reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
            try:
                await asyncio.wait_for(entered.wait(), 2)
                server.close()
                release.set()
                await server.wait_closed()
                self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                self.assert_released(server)
                callback.assert_not_awaited()
            finally:
                release.set()
                writer.close()
                await writer.wait_closed()
                server.close()
                await server.wait_closed()

    async def test_wrapper_task_remains_owned_through_writer_wait_closed(self):
        closing, release = asyncio.Event(), asyncio.Event()
        original = windows_streams._open_stream

        class ClosingWriter:
            def __init__(self, real):
                self.real = real

            def close(self):
                self.real.close()

            def is_closing(self):
                return self.real.is_closing()

            async def wait_closed(self):
                await self.real.wait_closed()
                closing.set()
                await release.wait()

        async def wrap_writer(owned):
            reader, writer = await original(owned)
            return reader, ClosingWriter(writer)

        with patch.object(windows_streams, "_open_stream", side_effect=wrap_writer):
            server = await start_windows_server(AsyncMock())
            _reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
            try:
                await asyncio.wait_for(closing.wait(), 2)
                self.assertTrue(server._handlers)
                server.close()
                waiting = asyncio.create_task(server.wait_closed())
                await asyncio.sleep(0)
                self.assertFalse(waiting.done())
                release.set()
                await asyncio.wait_for(waiting, 2)
                self.assert_released(server)
            finally:
                release.set()
                writer.close()
                await writer.wait_closed()
                server.close()
                await server.wait_closed()

    async def test_callback_error_is_reported_after_owned_resources_close(self):
        async def failing_callback(reader, writer):
            raise ValueError("synthetic token must not leak")

        server = await start_windows_server(failing_callback)
        reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
        try:
            self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
            server.close()
            with self.assertRaises(RuntimeError) as failure:
                await server.wait_closed()
            self.assertEqual(str(failure.exception), "browser_stream_cleanup_failed")
            self.assertNotIn("token", str(failure.exception))
            self.assert_released(server)
        finally:
            writer.close()
            await writer.wait_closed()
            server.close()

    async def test_open_failure_is_reported_and_does_not_leave_raw_handles(self):
        async def failed_open(owned):
            # Test double follows the owning public API's failure contract.
            owned.close()
            raise OSError("synthetic open failure")

        callback = AsyncMock()
        with patch.object(windows_streams, "_open_stream", side_effect=failed_open):
            server = await start_windows_server(callback)
            reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
            try:
                self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                server.close()
                with self.assertRaisesRegex(RuntimeError, "^browser_stream_cleanup_failed$"):
                    await server.wait_closed()
                self.assert_released(server)
                callback.assert_not_awaited()
            finally:
                writer.close()
                await writer.wait_closed()
                server.close()

    async def test_real_streams_handoff_cancellation_closes_via_public_api(self):
        original = windows_streams._open_stream

        async def cancel_at_transport_initialization(owned):
            task = asyncio.current_task()
            asyncio.get_running_loop().call_soon(task.cancel)
            # This is the actual unpatched Streams API. Its first suspension
            # awaits transport initialization, after ownership has transferred.
            return await original(owned)

        callback = AsyncMock()
        with patch.object(windows_streams, "_open_stream", side_effect=cancel_at_transport_initialization):
            server = await start_windows_server(callback)
            address = server.sockets[0].getsockname()
            reader, writer = await asyncio.open_connection(*address)
            try:
                self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                server.close()
                with self.assertRaisesRegex(RuntimeError, "^browser_stream_cleanup_failed$"):
                    await server.wait_closed()
                self.assert_released(server)
                self.assert_port_released(address)
                callback.assert_not_awaited()
            finally:
                writer.close()
                await writer.wait_closed()
                server.close()

    async def test_completed_reader64_does_not_hide_unexpected_shutdown_failure(self):
        original = windows_streams._open_stream
        for shutdown_error in (ConnectionResetError("synthetic non-peer-reset shutdown"), OSError("synthetic shutdown failure")):
            shutdown_error.winerror = 10053

            async def wrap_stream(owned, error=shutdown_error):
                outcome = owned.shutdown_outcome  # Capture our record BEFORE handoff.
                reader, writer = await original(owned)

                class CompletedWriter:
                    def close(self):
                        writer.close()

                    def is_closing(self):
                        return writer.is_closing()

                    async def wait_closed(self):
                        await writer.wait_closed()
                        reset = ConnectionResetError("synthetic terminal read")
                        reset.winerror = 64
                        reader.set_exception(reset)

                        def failed_shutdown():
                            raise error

                        # The same local recorder used by our socket override;
                        # no actual stdlib/transport shutdown is patched.
                        with suppress(type(error)):
                            _shutdown(failed_shutdown, outcome)
                        raise reset

                return reader, CompletedWriter()

            with self.subTest(error=type(shutdown_error)), patch.object(windows_streams, "_open_stream", side_effect=wrap_stream):
                server = await start_windows_server(AsyncMock())
                reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
                try:
                    self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                    server.close()
                    with self.assertRaisesRegex(RuntimeError, "^browser_stream_cleanup_failed$"):
                        await server.wait_closed()
                    self.assert_released(server)
                finally:
                    writer.close()
                    await writer.wait_closed()
                    server.close()

    async def test_initialization_failure_closes_only_our_new_listener(self):
        listeners = []

        def fail_initialization(listener, handler):
            listeners.append(listener)
            raise ValueError("synthetic initialization failure")

        with patch.object(windows_streams, "WindowsStreamServer", side_effect=fail_initialization), self.assertRaises(ValueError):
            await start_windows_server(AsyncMock())
        self.assertEqual(len(listeners), 1)
        self.assertEqual(listeners[0].fileno(), -1)

    @unittest.skipUnless(sys.platform == "win32", "Windows RST transport regression")
    async def test_real_tcp_peer_reset_closes_transport_and_releases_listener(self):
        entered, reset_seen = asyncio.Event(), asyncio.Event()
        read_errors = []

        async def callback(reader, writer):
            entered.set()
            try:
                await reader.read()
            except ConnectionResetError as error:
                read_errors.append(error)
                reset_seen.set()

        server = await start_windows_server(callback)
        address = server.sockets[0].getsockname()
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setblocking(False)
        try:
            await asyncio.get_running_loop().sock_connect(client, address)
            await asyncio.wait_for(entered.wait(), 2)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
            client.close()  # Real abortive TCP close, not a mocked WinError.
            await asyncio.wait_for(reset_seen.wait(), 2)
            self.assertEqual(len(read_errors), 1)
            self.assertEqual(read_errors[0].winerror, 64)
            server.close()
            await server.wait_closed()
            self.assert_released(server)
            self.assert_port_released(address)
        finally:
            client.close()
            server.close()
            await server.wait_closed()

    @unittest.skipUnless(sys.platform == "win32", "Windows accepted-proxy integration")
    async def test_real_rejected_socks_request_followed_by_tcp_reset_releases_proxy(self):
        proxy = BrowserEgressProxy(POLICY.resolve)
        url = await proxy.start()
        address = ("127.0.0.1", int(url.rsplit(":", 1)[1]))
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setblocking(False)
        try:
            loop = asyncio.get_running_loop()
            await loop.sock_connect(client, address)
            await loop.sock_sendall(client, b"\x05\x01\x00")
            self.assertEqual(await loop.sock_recv(client, 2), b"\x05\x00")
            host = b"forbidden.invalid"
            await loop.sock_sendall(client, b"\x05\x01\x00\x03" + bytes([len(host)]) + host + (443).to_bytes(2, "big"))
            response = await asyncio.wait_for(loop.sock_recv(client, 10), 2)
            self.assertEqual(response[1], 2)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
            client.close()
            await proxy.close()
            self.assertFalse(proxy._handlers)
            self.assertFalse(proxy._client_writers)
            self.assert_port_released(address)
        finally:
            client.close()
            with suppress(Exception):
                await proxy.close()
