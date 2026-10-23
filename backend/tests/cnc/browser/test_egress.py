import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

from _support import POLICY

from app.modules.cnc.browser.third_party.egress import BrowserEgressProxy, _open_first


async def socks_request(proxy_url, host, port):
    parsed = urlsplit(proxy_url)
    reader, writer = await asyncio.open_connection(parsed.hostname, parsed.port)
    writer.write(b"\x05\x01\x00")
    await writer.drain()
    if await reader.readexactly(2) != b"\x05\x00":
        raise AssertionError("SOCKS negotiation failed")
    encoded = host.encode("ascii")
    writer.write(b"\x05\x01\x00\x03" + bytes([len(encoded)]) + encoded + port.to_bytes(2, "big"))
    await writer.drain()
    return reader, writer


class EgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_rejects_non443_unknown_and_mixed_dns_before_connect(self):
        for port, host, answers in (
            (80, "fixture.example.com", ["8.8.8.8"]),
            (443, "unknown.test", ["8.8.8.8"]),
            (443, "fixture.example.com", ["8.8.8.8", "127.0.0.1"]),
        ):
            with self.subTest(port=port, host=host):
                proxy = BrowserEgressProxy(POLICY.resolve)
                url = await proxy.start()
                records = [(2, 1, 6, "", (ip, 443)) for ip in answers]
                try:
                    with (
                        patch("app.modules.cnc.browser.policy.socket.getaddrinfo", return_value=records),
                        patch("app.modules.cnc.browser.third_party.egress._open_first", new_callable=AsyncMock) as connect,
                    ):
                        reader, writer = await socks_request(url, host, port)
                        response = await asyncio.wait_for(reader.readexactly(10), 2)
                        self.assertEqual(response[1], 2)
                        connect.assert_not_awaited()
                        writer.close()
                        await writer.wait_closed()
                finally:
                    await proxy.close()
                self.assertFalse(proxy._handlers)

    async def test_proxy_passes_only_vetted_ips_to_connection_and_logs_no_raw_fault(self):
        proxy = BrowserEgressProxy(lambda host: ["8.8.8.8"])
        url = await proxy.start()
        try:
            with patch("app.modules.cnc.browser.third_party.egress._open_first", new_callable=AsyncMock, return_value=None) as connect:
                reader, writer = await socks_request(url, "fixture.example.com", 443)
                await asyncio.wait_for(reader.readexactly(10), 2)
                connect.assert_awaited_once_with(["8.8.8.8"], 443)
                writer.close()
                await writer.wait_closed()
        finally:
            await proxy.close()
        with patch("app.modules.cnc.browser.third_party.egress.asyncio.open_connection", new_callable=AsyncMock, return_value=("reader", "writer")) as connect:
            self.assertEqual(await _open_first(["8.8.8.8"], 443), ("reader", "writer"))
            connect.assert_awaited_once_with("8.8.8.8", 443)

        def denied(host):
            raise ValueError("password=synthetic-secret")

        proxy = BrowserEgressProxy(denied)
        url = await proxy.start()
        try:
            with self.assertLogs("app.modules.cnc.browser.third_party.egress", level="WARNING") as logged:
                reader, writer = await socks_request(url, "sensitive.example.com", 443)
                await asyncio.wait_for(reader.readexactly(10), 2)
                writer.close()
                await writer.wait_closed()
            self.assertNotIn("sensitive", str(logged.output))
            self.assertNotIn("synthetic-secret", str(logged.output))
        finally:
            await proxy.close()

    async def test_close_cancels_resolving_handlers_before_any_late_connection(self):
        started = threading.Event()
        release = threading.Event()

        def slow_resolve(host):
            started.set()
            release.wait(2)
            return ["8.8.8.8"]

        proxy = BrowserEgressProxy(slow_resolve)
        url = await proxy.start()
        with patch("app.modules.cnc.browser.third_party.egress._open_first", new_callable=AsyncMock) as connect:
            reader, writer = await socks_request(url, "fixture.example.com", 443)
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                await proxy.close()
                release.set()
                self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                connect.assert_not_awaited()
                self.assertFalse(proxy._handlers)
                self.assertFalse(proxy._client_writers)
            finally:
                release.set()
                writer.close()
                await writer.wait_closed()
                await proxy.close()
