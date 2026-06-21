from __future__ import annotations

from typing import Any

from annulus_core.config import AnnulusSettings, ModelProfile

from annulus_router.ollama import OllamaClient


class ModelRouter:
    """Routes chat requests to configured model profiles."""

    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self._ollama = OllamaClient(settings)

    async def close(self) -> None:
        await self._ollama.close()

    def resolve_profile(self, model: str | None = None) -> ModelProfile:
        profile_name = model if model and model in self.settings.models.profiles else None
        if profile_name is None:
            default_name = self.settings.router.default_profile
            profile_name = default_name

        profile = self.settings.models.profiles.get(profile_name)
        if profile is None:
            # Treat unknown model strings as direct Ollama model names
            return ModelProfile(provider="ollama", model=model or default_name)
        return profile

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
            for key in ("temperature", "max_tokens", "top_p", "stop"):
                if key in extra and extra[key] is not None:
                    payload[key] = extra[key]
        return payload

    @property
    def ollama(self) -> OllamaClient:
        return self._ollama

    async def health(self) -> dict[str, Any]:
        try:
            ollama_status = await self._ollama.health()
            return {"router": "ok", **ollama_status}
        except Exception as exc:
            return {"router": "ok", "ollama": "unavailable", "error": str(exc)}
