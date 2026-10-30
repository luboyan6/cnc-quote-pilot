"""Per-turn OpenAI-compatible async model; never mutate process globals."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import httpx
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


@asynccontextmanager
async def model_from_config(config: Mapping[str, Any]) -> AsyncIterator[ChatOpenAI]:
    """Require a complete selected configuration; no field-level fallback."""
    model_id, base_url, api_key = (config.get(key) for key in ("model_id", "base_url", "api_key"))
    temperature = config.get("temperature", 0.7)
    if not all(isinstance(value, str) and value.strip() for value in (model_id, base_url, api_key)):
        raise ValueError("AI_MODEL_CONFIG_INVALID")
    if not str(base_url).startswith(("http://", "https://")) or not isinstance(temperature, int | float) or not 0 <= temperature <= 2:
        raise ValueError("AI_MODEL_CONFIG_INVALID")
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        yield ChatOpenAI(
            model=str(model_id),
            base_url=str(base_url),
            api_key=SecretStr(str(api_key)),
            temperature=float(temperature),
            http_async_client=client,
        )
