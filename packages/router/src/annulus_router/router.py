from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from annulus_core.config import AnnulusSettings, ModelProfile

from annulus_router.escalation import CompletionResult, EscalationPolicy
from annulus_router.ollama import OllamaClient
from annulus_router.openai import OpenAIClient


class ModelRouter:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self._ollama = OllamaClient(settings)
        self._openai: OpenAIClient | None = None
        self._escalation = EscalationPolicy(settings)

    async def close(self) -> None:
        await self._ollama.close()
        if self._openai is not None:
            await self._openai.close()

    def _openai_client(self) -> OpenAIClient:
        if self._openai is None:
            self._openai = OpenAIClient(self.settings)
        return self._openai

    def resolve_profile(self, model: str | None = None) -> tuple[str, ModelProfile]:
        if model and model in self.settings.models.profiles:
            return model, self.settings.models.profiles[model]

        default_name = self.settings.router.default_profile
        profile = self.settings.models.profiles.get(default_name)
        if profile is not None:
            return default_name, profile

        if model:
            return model, ModelProfile(provider="ollama", model=model, supports_tools=True)
        return default_name, ModelProfile(
            provider="ollama", model=default_name, supports_tools=True
        )

    def build_payload(
        self,
        *,
        profile: ModelProfile,
        messages: list[dict[str, Any]],
        stream: bool,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
            "stream": stream,
        }
        if extra:
            for key in ("temperature", "max_tokens", "top_p", "stop", "tools", "tool_choice"):
                if key in extra and extra[key] is not None:
                    payload[key] = extra[key]
        return payload

    async def complete(
        self,
        *,
        profile_name: str,
        profile: ModelProfile,
        payload: dict[str, Any],
    ) -> CompletionResult:
        payload = {**payload, "stream": False}
        try:
            data = await self._request_json(profile, payload)
            if self._escalation.should_escalate(
                profile_name=profile_name, profile=profile, response=data
            ):
                return await self._escalate(payload, reason="empty_response")
            return CompletionResult(
                data=data, profile=profile, profile_name=profile_name, escalated=False
            )
        except Exception as exc:
            if self._escalation.should_escalate(
                profile_name=profile_name, profile=profile, error=exc
            ):
                return await self._escalate(payload, reason=str(exc))
            raise

    async def _escalate(self, payload: dict[str, Any], *, reason: str) -> CompletionResult:
        frontier_name, frontier_profile = self._escalation.frontier_profile()
        if frontier_profile.provider != "openai":
            raise ValueError(f"Unsupported frontier provider: {frontier_profile.provider}")
        payload = {
            **payload,
            "model": frontier_profile.model,
        }
        data = await self._request_json(frontier_profile, payload)
        data.setdefault("system_fingerprint", f"annulus-escalated:{reason}")
        return CompletionResult(
            data=data,
            profile=frontier_profile,
            profile_name=frontier_name,
            escalated=True,
        )

    async def _request_json(self, profile: ModelProfile, payload: dict[str, Any]) -> dict[str, Any]:
        if profile.provider == "ollama":
            response = await self._ollama.chat_completions(payload)
        elif profile.provider == "openai":
            response = await self._openai_client().chat_completions(payload)
        else:
            raise ValueError(f"Unsupported provider: {profile.provider}")

        if response.status_code >= 400:
            raise RuntimeError(response.text)
        return response.json()

    async def stream(
        self,
        *,
        profile: ModelProfile,
        payload: dict[str, Any],
    ) -> AsyncIterator[bytes]:
        payload = {**payload, "stream": True}
        if profile.provider == "ollama":
            async for chunk in self._ollama.stream_chat_completions(payload):
                yield chunk
        elif profile.provider == "openai":
            async for chunk in self._openai_client().stream_chat_completions(payload):
                yield chunk
        else:
            raise ValueError(f"Unsupported provider: {profile.provider}")

    @property
    def ollama(self) -> OllamaClient:
        return self._ollama

    async def health(self) -> dict[str, Any]:
        result: dict[str, Any] = {"router": "ok"}
        try:
            result.update(await self._ollama.health())
        except Exception as exc:
            result["ollama"] = "unavailable"
            result["ollama_error"] = str(exc)

        if self.settings.openai_api_key:
            result["frontier"] = "configured"
        else:
            result["frontier"] = "missing_api_key"
        return result
