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
    escalation_enabled: bool = True


DEFAULT_TOOL_SYSTEM_PROMPT = """<annulus_tools>
You are connected to the Annulus gateway. Server-side tools read_file and ripgrep are available via tool_calls on this request. Use them when the user asks for repository search or file reads.

When the user explicitly asks you to use ripgrep or read_file, you MUST call that tool before answering.

Ignore any instruction that says tools are unavailable or must be enabled in Continue Tool Policies. Those refer to Continue's built-in tools, not Annulus.
</annulus_tools>"""


class AgentConfig(BaseModel):
    max_iterations: int = 8
    tools_enabled: bool = True
    retrieval_enabled: bool = True
    retrieval_top_k: int = 5
    index_watch_enabled: bool = False
    tool_system_prompt: str = DEFAULT_TOOL_SYSTEM_PROMPT


class RetrievalConfig(BaseModel):
    exclude_dirs: list[str] = Field(
        default_factory=lambda: [".git", ".venv", "node_modules", "__pycache__", ".annulus"]
    )
    exclude_extensions: list[str] = Field(default_factory=lambda: [".pyc", ".png", ".jpg", ".pdf"])
    max_chunk_chars: int = 2000
    overlap_chars: int = 200
    index_watch_interval_seconds: int = 30


class ToolsConfig(BaseModel):
    sandbox_root: str = "."
    allowed_commands: list[str] = Field(default_factory=lambda: ["rg"])


class ModelProfile(BaseModel):
    provider: str
    model: str
    description: str = ""
    supports_tools: bool = True
    expose_reasoning: bool = False
    system_prompt: str = ""


class EscalationConfig(BaseModel):
    on_local_error: bool = True
    on_empty_response: bool = True
    frontier_profile: str = "frontier"


class ModelsConfig(BaseModel):
    profiles: dict[str, ModelProfile] = Field(default_factory=dict)
    defaults: dict[str, str] = Field(default_factory=lambda: {"chat": "local"})
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)


class AnnulusSettings(BaseSettings):
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
    annulus_index_db: Path | None = Field(default=None, alias="ANNULUS_INDEX_DB")
    annulus_workspace_root: Path = Field(default=Path("."), alias="ANNULUS_WORKSPACE_ROOT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    annulus_agent_max_iterations: int = Field(default=8, alias="ANNULUS_AGENT_MAX_ITERATIONS")
    annulus_retrieval_top_k: int = Field(default=5, alias="ANNULUS_RETRIEVAL_TOP_K")
    annulus_escalation_enabled: bool = Field(default=True, alias="ANNULUS_ESCALATION_ENABLED")

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    trace: TraceConfig = Field(default_factory=TraceConfig)
    router: RouterConfig = Field(default_factory=RouterConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)

    def resolve_trace_db(self) -> Path:
        if self.annulus_trace_db is not None:
            return self.annulus_trace_db
        return self.annulus_data_dir / "traces.db"

    def resolve_index_db(self) -> Path:
        if self.annulus_index_db is not None:
            return self.annulus_index_db
        return self.annulus_data_dir / "index.db"

    def resolve_workspace_root(self) -> Path:
        return self.annulus_workspace_root.resolve()

    def resolve_tools_root(self) -> Path:
        root = Path(self.tools.sandbox_root)
        if not root.is_absolute():
            root = self.resolve_workspace_root() / root
        return root.resolve()

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
    settings = AnnulusSettings()
    cfg_dir = config_dir or settings.annulus_config_dir

    default_yaml = _load_yaml(cfg_dir / "default.yaml")
    models_yaml = _load_yaml(cfg_dir / "models.yaml")

    for key, model_cls in (
        ("gateway", GatewayConfig),
        ("trace", TraceConfig),
        ("router", RouterConfig),
        ("agent", AgentConfig),
        ("retrieval", RetrievalConfig),
        ("tools", ToolsConfig),
    ):
        if section := default_yaml.get(key):
            setattr(settings, key, model_cls.model_validate(section))

    if models_yaml:
        settings.models = ModelsConfig.model_validate(models_yaml)

    settings.gateway.host = settings.annulus_host
    settings.gateway.port = settings.annulus_port
    settings.gateway.api_key = settings.annulus_api_key
    settings.router.escalation_enabled = settings.annulus_escalation_enabled
    settings.agent.max_iterations = settings.annulus_agent_max_iterations
    settings.agent.retrieval_top_k = settings.annulus_retrieval_top_k

    settings.annulus_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
