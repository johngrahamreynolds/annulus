from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from annulus_core.config import AnnulusSettings


class OllamaClient:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.base_url = settings.ollama_host.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def chat_completions(self, payload: dict[str, Any]) -> httpx.Response:
        return await self._client.post("/v1/chat/completions", json=payload)

    async def stream_chat_completions(self, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        payload = {**payload, "stream": True}
        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    async def health(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            result["ollama"] = "ok"
            result["models"] = response.json()
        except Exception as exc:
            result["ollama"] = "unavailable"
            result["ollama_error"] = str(exc)
            return result

        try:
            compat = await self._client.get("/v1/models")
            if compat.status_code == 404:
                result["ollama_openai_compat"] = "missing"
                result["ollama_error"] = (
                    "Ollama is reachable but GET /v1/models returned 404. "
                    "Upgrade Ollama to a version with OpenAI-compatible API "
                    "(/v1/chat/completions). See .devcontainer/eval/README.md."
                )
            elif compat.status_code >= 400:
                result["ollama_openai_compat"] = "error"
                result["ollama_openai_compat_error"] = compat.text[:300]
            else:
                result["ollama_openai_compat"] = "ok"
        except Exception as exc:
            result["ollama_openai_compat"] = "unavailable"
            result["ollama_openai_compat_error"] = str(exc)

        return result
