"""Agent resource acquisition and an explicit, fail-closed integration gate."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.engine import make_url

from .checkpoint import postgres_checkpointer
from .service import AgentService

# Chat ownership/history/protocol integration must be completed and reviewed
# before this switch is changed. A present saver schema alone is insufficient.
SOURCE_CHAT_INTEGRATION_READY = False


def require_chat_integration(settings: Any) -> None:
    if not SOURCE_CHAT_INTEGRATION_READY:
        raise RuntimeError("AI_SOURCE_CHAT_INTEGRATION_NOT_READY")
    if settings.WORKERS != 1:
        raise RuntimeError("AI_SOURCE_REQUIRES_SINGLE_WORKER")
    if settings.DATABASE_TYPE != "postgres":
        raise RuntimeError("AI_SOURCE_REQUIRES_POSTGRES")


@asynccontextmanager
async def open_agent_service(settings: Any) -> AsyncIterator[AgentService]:
    if settings.WORKERS != 1 or settings.DATABASE_TYPE != "postgres":
        raise RuntimeError("AI_SOURCE_DEPLOYMENT_UNSUPPORTED")
    dsn = make_url(settings.DB_URI).set(drivername="postgresql").render_as_string(hide_password=False)
    async with postgres_checkpointer(dsn) as saver:
        service = AgentService(saver)
        try:
            yield service
        finally:
            await service.close()
