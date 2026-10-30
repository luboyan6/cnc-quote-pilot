"""Check a configured model's local cancellation before its first response.

Only a synthetic prompt is sent. The application database is not accessed and
configuration, model output and request URLs are never printed.
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ["LANGSMITH_TRACING"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
logging.disable(logging.CRITICAL)


async def main():
    import httpx
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    from pydantic import SecretStr

    from app.config.setting import settings
    from app.modules.ai.agent.service import AgentService

    if not all((settings.OPENAI_MODEL, settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY)):
        print(json.dumps({"configuration_complete": False}))
        return 1
    after_first = "--after-first" in sys.argv
    after_send = "--after-send" in sys.argv
    request_started, request_sent, resource_closed, first_text = asyncio.Event(), asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def trace_transport(name, _info):
        # httpcore fires this only after it has sent the HTTP request body.
        # It does not prove the provider has received or processed it.
        if name.endswith(".send_request_body.complete"):
            request_sent.set()

    async def observe_request(request):
        request.extensions["trace"] = trace_transport
        request_started.set()

    @asynccontextmanager
    async def factory(_config):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), event_hooks={"request": [observe_request]}) as client:
                yield ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    base_url=settings.OPENAI_BASE_URL,
                    api_key=SecretStr(settings.OPENAI_API_KEY),
                    temperature=0,
                    http_async_client=client,
                    max_retries=0,
                )
        finally:
            resource_closed.set()

    service = AgentService(InMemorySaver(), model_factory=factory)
    events = []

    async def consume():
        async for event in service.stream(
            actor_id=7,
            session_id="synthetic-stop-session",
            turn_id="synthetic-stop-turn",
            message="请直接逐行输出从 1 到 500 的整数，不要解释。",
            skills=[],
            model_config={},
            tools=[],
        ):
            events.append(event.type)
            if event.type == "text.delta":
                first_text.set()

    consumer = asyncio.create_task(consume())
    try:
        target = first_text if after_first else request_sent if after_send else request_started
        await asyncio.wait_for(target.wait(), timeout=60)
        start = time.monotonic()
        stopped = await asyncio.wait_for(service.stop(7, "synthetic-stop-session", "synthetic-stop-turn"), timeout=5)
        await asyncio.wait_for(consumer, timeout=5)
        elapsed = time.monotonic() - start
        result = {
            "synthetic_prompt_only": True,
            "request_started": request_started.is_set(),
            "request_sent": request_sent.is_set(),
            "stopped": stopped,
            "resource_closed": resource_closed.is_set(),
            "before_first_text": "text.delta" not in events,
            "first_text_observed": first_text.is_set(),
            "terminal_events": [event for event in events if event.startswith("turn.") and event != "turn.started"],
            "elapsed_ms": round(elapsed * 1000),
        }
        print(json.dumps(result))
        expected_phase = first_text.is_set() if after_first else "text.delta" not in events
        return 0 if stopped and resource_closed.is_set() and expected_phase and result["terminal_events"] == ["turn.stopped"] and elapsed < 1 else 1
    except Exception as exc:
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        await service.close()
        print(json.dumps({"synthetic_prompt_only": True, "error_type": type(exc).__name__, "resource_closed": resource_closed.is_set(), "events": events}))
        return 1
    finally:
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        await service.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
