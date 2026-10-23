"""Exercise Uvicorn's actual worker loop without starting the app or database."""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import uvicorn

import main
from app.config.setting import settings


async def subprocess_probe_app(scope, receive, send):
    child = await asyncio.create_subprocess_exec(sys.executable, "-c", "print('subprocess-ok')", stdout=asyncio.subprocess.PIPE)
    output, _ = await asyncio.wait_for(child.communicate(), timeout=5)
    await send({"type": "http.response.start", "status": 200 if child.returncode == 0 else 500, "headers": [(b"content-length", str(len(output)).encode())]})
    await send({"type": "http.response.body", "body": output})


class ServerLoopTests(unittest.TestCase):
    def test_windows_cli_avoids_shared_listener_for_debug_and_multiple_workers(self):
        for debug, workers in ((True, 1), (True, 2), (False, 1), (False, 2)):
            with self.subTest(debug=debug, workers=workers):
                with (
                    patch.dict(os.environ),
                    patch.object(main.sys, "platform", "win32"),
                    patch.object(settings, "DEBUG", debug),
                    patch.object(settings, "WORKERS", workers),
                    patch.object(main.uvicorn, "run") as run_server,
                ):
                    main.run()
                options = run_server.call_args.kwargs
                self.assertFalse(options["reload"])
                self.assertEqual(options["workers"], 1)
                self.assertEqual(options["loop"], "app.core.server_loop:subprocess_event_loop")
                self.assertFalse(uvicorn.Config(**options).use_subprocess)

    def test_non_windows_cli_preserves_reload_and_workers(self):
        for debug, workers in ((True, 1), (False, 2)):
            with self.subTest(debug=debug, workers=workers):
                with (
                    patch.dict(os.environ),
                    patch.object(main.sys, "platform", "linux"),
                    patch.object(settings, "DEBUG", debug),
                    patch.object(settings, "WORKERS", workers),
                    patch.object(main.uvicorn, "run") as run_server,
                ):
                    main.run()
                options = run_server.call_args.kwargs
                self.assertEqual(options["reload"], debug)
                self.assertEqual(options["workers"], workers)
                self.assertEqual(options["loop"], "auto")

    @unittest.skipUnless(sys.platform == "win32", "Windows subprocess loop regression")
    def test_cli_loop_supports_subprocesses(self):
        with patch.dict(os.environ), patch.object(main.uvicorn, "run") as run_server:
            main.run()
        loop_name = run_server.call_args.kwargs["loop"]

        async def probe():
            child = await asyncio.create_subprocess_exec(sys.executable, "-c", "pass")
            self.assertEqual(await asyncio.wait_for(child.wait(), timeout=10), 0)

        factory = uvicorn.Config("unused:app", loop=loop_name).get_loop_factory()
        self.assertIsNotNone(factory)
        with asyncio.Runner(loop_factory=factory) as runner:
            runner.run(probe())

    @unittest.skipUnless(sys.platform == "win32", "Windows listener restart regression")
    def test_windows_http_and_subprocesses_after_restart_on_same_port(self):
        with (
            patch.dict(os.environ),
            patch.object(settings, "DEBUG", True),
            patch.object(settings, "WORKERS", 2),
            patch.object(main.uvicorn, "run") as run_server,
        ):
            main.run()
        options = run_server.call_args.kwargs
        options.update(app=subprocess_probe_app, factory=False, host="127.0.0.1", port=0, lifespan="off", ws="none", log_level="error")
        self.assertFalse(uvicorn.Config(**options).use_subprocess)

        async def probe():
            errors = []
            asyncio.get_running_loop().set_exception_handler(lambda loop, context: errors.append(context))
            server = uvicorn.Server(uvicorn.Config(**options))
            serving = asyncio.create_task(server.serve())
            try:
                async with asyncio.timeout(5):
                    while not server.started:
                        if serving.done():
                            await serving
                            self.fail("Server exited before accepting requests")
                        await asyncio.sleep(0.01)
                port = server.servers[0].sockets[0].getsockname()[1]
                reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), timeout=5)
                try:
                    writer.write(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                    await writer.drain()
                    response = await asyncio.wait_for(reader.read(), timeout=10)
                    self.assertTrue(response.startswith(b"HTTP/1.1 200 OK\r\n"), response)
                    self.assertEqual(response.split(b"\r\n\r\n", 1)[1].strip(), b"subprocess-ok")
                finally:
                    writer.close()
                    await writer.wait_closed()
                return port
            finally:
                server.should_exit = True
                await asyncio.wait_for(serving, timeout=5)
                self.assertEqual(errors, [])

        for generation in (1, 2):
            with self.subTest(generation=generation):
                with asyncio.Runner(loop_factory=uvicorn.Config(**options).get_loop_factory()) as runner:
                    options["port"] = runner.run(probe())


if __name__ == "__main__":
    unittest.main()
