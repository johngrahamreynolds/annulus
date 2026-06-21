from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from annulus_core.config import AnnulusSettings


class OllamaClient:
    """Passthrough client for Ollama's OpenAI-compatible API."""

    def __init__(self, settings: AnnulusSettings) -> None:
        self.base_url = settings.ollama_host.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def chat_completions(self, payload: dict[str, Any]) -> httpx.Response:
        return await self._client.post("/v1/chat/completions", json=payload)

    async def stream_chat_completions(
        self, payload: dict[str, Any]
    ) -> AsyncIterator[bytes]:
        payload = {**payload, "stream": True}
        async with self._client.stream(
            "POST", "/v1/chat/completions", json=payload
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    async def health(self) -> dict[str, Any]:
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        return {"ollama": "ok", "models": response.json()}
