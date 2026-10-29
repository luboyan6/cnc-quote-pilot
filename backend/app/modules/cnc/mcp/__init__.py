"""Optional embedded MCP integration; importing this module does not load the SDK."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.routing import Route

from app.config.setting import settings


def register_mcp(app: FastAPI) -> None:
    """Register one independent MCP server per application when explicitly enabled."""
    if not settings.MCP_ENABLED:
        return

    from .server import CncMCPServer

    server = CncMCPServer(app, settings)
    app.state.cnc_mcp = server
    # A direct ASGI route works both with and without the deployment ROOT_PATH;
    # nesting a second Starlette router would require the prefix in the raw URL.
    app.router.routes.append(Route("/mcp/", endpoint=server.app, methods=["GET", "POST", "DELETE"], name="cnc-management-mcp"))


@asynccontextmanager
async def mcp_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Mounted ASGI applications do not enter their own lifespan automatically."""
    server = getattr(app.state, "cnc_mcp", None)
    if server is None:
        yield
    else:
        async with server.session_manager.run():
            yield
