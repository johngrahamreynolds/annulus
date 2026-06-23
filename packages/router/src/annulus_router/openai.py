from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from annulus_core.config import AnnulusSettings


class OpenAIClient:
    def __init__(self, settings: AnnulusSettings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for frontier provider")
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=300.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def chat_completions(self, payload: dict[str, Any]) -> httpx.Response:
        return await self._client.post("/chat/completions", json=payload)

    async def stream_chat_completions(self, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        payload = {**payload, "stream": True}
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
