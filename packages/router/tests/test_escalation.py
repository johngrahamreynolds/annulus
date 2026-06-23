from __future__ import annotations

from annulus_core.config import EscalationConfig, ModelProfile, ModelsConfig
from annulus_router.escalation import EscalationPolicy, _is_empty_response


def test_empty_response_detection():
    assert _is_empty_response({"choices": [{"message": {"content": ""}}]})
    assert not _is_empty_response({"choices": [{"message": {"content": "hi"}}]})


def test_escalation_on_error():
    class Settings:
        router = type("R", (), {"escalation_enabled": True})()
        models = ModelsConfig(
            escalation=EscalationConfig(on_local_error=True, frontier_profile="frontier"),
            profiles={
                "local": ModelProfile(provider="ollama", model="m"),
                "frontier": ModelProfile(provider="openai", model="gpt"),
            },
        )

    policy = EscalationPolicy(Settings())  # type: ignore[arg-type]
    assert policy.should_escalate(
        profile_name="local",
        profile=Settings.models.profiles["local"],  # type: ignore[attr-defined]
        error=RuntimeError("boom"),
    )
