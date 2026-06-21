from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    api_key: str = "dev-local-key"


class TraceConfig(BaseModel):
    enabled: bool = True


class RouterConfig(BaseModel):
    default_profile: str = "local"


class ModelProfile(BaseModel):
    provider: str
    model: str
    description: str = ""


class ModelsConfig(BaseModel):
    profiles: dict[str, ModelProfile] = Field(default_factory=dict)
    defaults: dict[str, str] = Field(default_factory=lambda: {"chat": "local"})


class AnnulusSettings(BaseSettings):
    """Environment-backed settings with YAML overlay."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    annulus_host: str = Field(default="0.0.0.0", alias="ANNULUS_HOST")
    annulus_port: int = Field(default=8080, alias="ANNULUS_PORT")
    annulus_api_key: str = Field(default="dev-local-key", alias="ANNULUS_API_KEY")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_HOST")
    annulus_config_dir: Path = Field(default=Path("config"), alias="ANNULUS_CONFIG_DIR")
    annulus_data_dir: Path = Field(default=Path(".annulus"), alias="ANNULUS_DATA_DIR")
    annulus_trace_db: Path | None = Field(default=None, alias="ANNULUS_TRACE_DB")

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    trace: TraceConfig = Field(default_factory=TraceConfig)
    router: RouterConfig = Field(default_factory=RouterConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)

    def resolve_trace_db(self) -> Path:
        if self.annulus_trace_db is not None:
            return self.annulus_trace_db
        return self.annulus_data_dir / "traces.db"

    def gateway_base_url(self) -> str:
        host = self.annulus_host
        if host == "0.0.0.0":
            host = "127.0.0.1"
        return f"http://{host}:{self.annulus_port}"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_settings(config_dir: Path | None = None) -> AnnulusSettings:
    """Load settings from environment, then merge YAML config files."""
    settings = AnnulusSettings()
    cfg_dir = config_dir or settings.annulus_config_dir

    default_yaml = _load_yaml(cfg_dir / "default.yaml")
    models_yaml = _load_yaml(cfg_dir / "models.yaml")

    if gateway := default_yaml.get("gateway"):
        settings.gateway = GatewayConfig.model_validate(gateway)
    if trace := default_yaml.get("trace"):
        settings.trace = TraceConfig.model_validate(trace)
    if router := default_yaml.get("router"):
        settings.router = RouterConfig.model_validate(router)
    if models_yaml:
        settings.models = ModelsConfig.model_validate(models_yaml)

    # Environment overrides YAML for gateway bind/auth
    settings.gateway.host = settings.annulus_host
    settings.gateway.port = settings.annulus_port
    settings.gateway.api_key = settings.annulus_api_key

    settings.annulus_data_dir.mkdir(parents=True, exist_ok=True)

    return settings
