from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .extractors import extract_docx_text as read_docx_text
from .extractors import extract_pptx_text as read_pptx_text


class ToolError(RuntimeError):
    """Raised when an agent tool cannot complete safely."""


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def create_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool definitions for DeepSeek Function Calling."""
    return [
        _schema(
            "list_workspace_files",
            "List course workspace files that the agent is allowed to inspect.",
            {
                "pattern": {
                    "type": "string",
                    "description": "Glob-style pattern such as *.pptx, *.docx, or *.",
                }
            },
            ["pattern"],
        ),
        _schema(
            "list_project_files",
            "List repository files for the implemented BYOA agent project.",
            {
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum repository path depth to include.",
                    "minimum": 1,
                    "maximum": 5,
                }
            },
            ["max_depth"],
        ),
        _schema(
            "extract_pptx_text",
            "Extract ordered slide text from a PPTX course material file.",
            {"path": {"type": "string", "description": "Workspace-relative PPTX path."}},
            ["path"],
        ),
        _schema(
            "extract_docx_text",
            "Extract paragraph text from a DOCX report or template file.",
            {"path": {"type": "string", "description": "Workspace-relative DOCX path."}},
            ["path"],
        ),
        _schema(
            "search_extracted_context",
            "Search text that was previously loaded by extraction tools.",
            {
                "query": {"type": "string", "description": "Keyword or phrase to search."},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matching snippets to return.",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            ["query", "limit"],
        ),
    ]


@dataclass
class CourseAgentTools:
    workspace: Path
    log_path: Path | None = None
    project_root: Path | None = None
    extracted_context: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        if self.project_root is None:
            self.project_root = Path.cwd().resolve()
        else:
            self.project_root = self.project_root.resolve()
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def dispatch(self, name: str, arguments: dict) -> str:
        registry: dict[str, Callable[[dict], str]] = {
            "list_workspace_files": self.list_workspace_files,
            "list_project_files": self.list_project_files,
            "extract_pptx_text": self.extract_pptx_text,
            "extract_docx_text": self.extract_docx_text,
            "search_extracted_context": self.search_extracted_context,
        }
        if name not in registry:
            raise ToolError(f"Unknown tool: {name}")
        return registry[name](arguments)

    def list_workspace_files(self, arguments: dict) -> str:
        pattern = arguments.get("pattern") or "*"
        files = []
        for path in sorted(self.workspace.iterdir()):
            if path.is_file() and fnmatch.fnmatch(path.name, pattern):
                files.append(
                    {
                        "path": path.name,
                        "size_bytes": path.stat().st_size,
                    }
                )
        result = json.dumps({"files": files}, ensure_ascii=False, indent=2)
        self._log("list_workspace_files", arguments, "ok", result)
        return result

    def list_project_files(self, arguments: dict) -> str:
        max_depth = int(arguments.get("max_depth", 3))
        ignored_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        files = []
        assert self.project_root is not None
        for path in sorted(self.project_root.rglob("*")):
            relative = path.relative_to(self.project_root)
            if any(part in ignored_dirs for part in relative.parts):
                continue
            if len(relative.parts) > max_depth:
                continue
            if path.is_file():
                files.append({"path": relative.as_posix(), "size_bytes": path.stat().st_size})
        result = json.dumps({"files": files}, ensure_ascii=False, indent=2)
        self._log("list_project_files", arguments, "ok", result)
        return result

    def extract_pptx_text(self, arguments: dict) -> str:
        path = self._resolve_allowed_file(arguments.get("path"), ".pptx")
        text = read_pptx_text(path)
        self.extracted_context[path.name] = text
        result = json.dumps({"path": path.name, "text": text}, ensure_ascii=False)
        self._log("extract_pptx_text", arguments, "ok", result)
        return result

    def extract_docx_text(self, arguments: dict) -> str:
        path = self._resolve_allowed_file(arguments.get("path"), ".docx")
        text = read_docx_text(path)
        self.extracted_context[path.name] = text
        result = json.dumps({"path": path.name, "text": text}, ensure_ascii=False)
        self._log("extract_docx_text", arguments, "ok", result)
        return result

    def search_extracted_context(self, arguments: dict) -> str:
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ToolError("query is required")
        limit = int(arguments.get("limit", 5))
        matches = []
        query_lower = query.lower()
        for source, text in self.extracted_context.items():
            for line_number, line in enumerate(text.splitlines(), 1):
                if query_lower in line.lower():
                    matches.append(
                        {
                            "source": source,
                            "line": line_number,
                            "text": line,
                        }
                    )
                    if len(matches) >= limit:
                        result = json.dumps({"matches": matches}, ensure_ascii=False, indent=2)
                        self._log("search_extracted_context", arguments, "ok", result)
                        return result
        result = json.dumps({"matches": matches}, ensure_ascii=False, indent=2)
        self._log("search_extracted_context", arguments, "ok", result)
        return result

    def _resolve_allowed_file(self, value: object, suffix: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ToolError("path is required")
        path = (self.workspace / value).resolve()
        try:
            path.relative_to(self.workspace)
        except ValueError as exc:
            raise ToolError(f"path is outside workspace: {value}") from exc
        if path.suffix.lower() != suffix:
            raise ToolError(f"expected a {suffix} file: {value}")
        if not path.exists() or not path.is_file():
            raise ToolError(f"file not found: {value}")
        return path

    def _log(self, tool: str, arguments: dict, status: str, result: str) -> None:
        if self.log_path is None:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": arguments,
            "status": status,
            "result_preview": result[:1000],
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
