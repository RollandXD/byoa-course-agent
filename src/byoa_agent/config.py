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
    def from_env(cls, workspace: str | Path, env_file: str | Path | None = None) -> "AgentConfig":
        values = _read_env_file(Path(env_file)) if env_file is not None else {}
        api_key = os.environ.get("DEEPSEEK_API_KEY", values.get("DEEPSEEK_API_KEY", "")).strip()
        if not api_key:
            raise ConfigError(
                "DEEPSEEK_API_KEY is not set. Export your DeepSeek API key before running the agent."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get(
                "DEEPSEEK_BASE_URL", values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            ).rstrip("/"),
            model=os.environ.get("DEEPSEEK_MODEL", values.get("DEEPSEEK_MODEL", "deepseek-v4-flash")),
            workspace=Path(workspace).resolve(),
        )


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
