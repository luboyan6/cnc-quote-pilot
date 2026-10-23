"""Uvicorn's Windows worker loop must support Playwright subprocesses."""

import asyncio
import sys


def subprocess_event_loop() -> asyncio.AbstractEventLoop:
    """Importable Uvicorn loop factory, including reload and spawned workers."""
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()
