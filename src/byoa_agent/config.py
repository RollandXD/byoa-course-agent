from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when the agent cannot be configured from the environment."""


@dataclass(frozen=True)
class AgentConfig:
    api_key: str
    base_url: str
    model: str
    workspace: Path

    @classmethod
    def from_env(cls, workspace: str | Path) -> "AgentConfig":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "DEEPSEEK_API_KEY is not set. Export your DeepSeek API key before running the agent."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            workspace=Path(workspace).resolve(),
        )

