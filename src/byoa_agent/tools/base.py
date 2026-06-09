from __future__ import annotations

from dataclasses import dataclass, field


class ToolError(RuntimeError):
    """Raised when an agent tool cannot complete safely."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    properties: dict
    required: list[str]
    method_name: str


REGISTRY: dict[str, ToolSpec] = {}


def tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None):
    """Register a toolbox method as an OpenAI-compatible function-calling tool."""

    def decorator(fn):
        REGISTRY[name] = ToolSpec(
            name=name,
            description=description,
            properties=properties or {},
            required=required or [],
            method_name=fn.__name__,
        )
        return fn

    return decorator


def create_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool definitions for DeepSeek Function Calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": {
                    "type": "object",
                    "properties": spec.properties,
                    "required": spec.required,
                    "additionalProperties": False,
                },
            },
        }
        for spec in REGISTRY.values()
    ]
