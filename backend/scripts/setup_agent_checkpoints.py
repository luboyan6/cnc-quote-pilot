"""Explicit deployment command for the standard LangGraph checkpoint tables."""

import asyncio
import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


async def setup(dsn: str) -> None:
    serde = JsonPlusSerializer(allowed_msgpack_modules=None, allowed_json_modules=None)
    async with AsyncPostgresSaver.from_conn_string(dsn, serde=serde) as saver:
        await saver.setup()


def main() -> None:
    dsn = os.environ.get("CNC_AGENT_CHECKPOINT_DSN", "")
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Set CNC_AGENT_CHECKPOINT_DSN to the intended PostgreSQL connection URL")
    # Psycopg async requires a selector on Windows; this short-lived setup
    # command does not alter the web server's Proactor/Playwright loop.
    asyncio.run(setup(dsn), loop_factory=asyncio.SelectorEventLoop)
    print("Agent checkpoint schema is ready.")


if __name__ == "__main__":
    main()
