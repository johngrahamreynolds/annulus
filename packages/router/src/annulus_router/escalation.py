from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from annulus_core.config import AnnulusSettings, ModelProfile


@dataclass
class CompletionResult:
    data: dict[str, Any]
    profile: ModelProfile
    profile_name: str
    escalated: bool = False


class EscalationPolicy:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.router.escalation_enabled

    def should_escalate(
        self,
        *,
        profile_name: str,
        profile: ModelProfile,
        error: Exception | None = None,
        response: dict[str, Any] | None = None,
    ) -> bool:
        if not self.enabled:
            return False
        if profile.provider != "ollama":
            return False
        if profile_name == self.settings.models.escalation.frontier_profile:
            return False

        esc = self.settings.models.escalation
        if error is not None and esc.on_local_error:
            return True
        if response is not None and esc.on_empty_response and _is_empty_response(response):
            return True
        return False

    def frontier_profile(self) -> tuple[str, ModelProfile]:
        name = self.settings.models.escalation.frontier_profile
        profile = self.settings.models.profiles.get(name)
        if profile is None:
            raise ValueError(f"Frontier profile '{name}' is not configured")
        return name, profile


def _is_empty_response(data: dict[str, Any]) -> bool:
    try:
        message = data["choices"][0]["message"]
        if message.get("tool_calls"):
            return False
        content = message.get("content")
        return not content or not str(content).strip()
    except (KeyError, IndexError, TypeError):
        return True
