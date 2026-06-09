from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..permissions import PermissionGate
from .base import REGISTRY, ToolError
from .general import GeneralTools
from .course import CourseTools


class AgentToolbox(GeneralTools, CourseTools):
    """All local tools exposed to the model, sandboxed to the course workspace.

    Reads are allowed anywhere inside ``workspace`` (the course directory that
    contains this repository); writes and shell commands are restricted to
    ``project_root`` and pass through the permission gate.
    """

    def __init__(
        self,
        workspace: Path,
        log_path: Path | None = None,
        project_root: Path | None = None,
        permissions: PermissionGate | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.project_root = (Path(project_root) if project_root else Path.cwd()).resolve()
        self.log_path = log_path
        self.permissions = permissions or PermissionGate(mode="auto")
        self.extracted_context: dict[str, str] = {}
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def dispatch(self, name: str, arguments: dict) -> str:
        spec = REGISTRY.get(name)
        if spec is None:
            raise ToolError(f"Unknown tool: {name}")
        return getattr(self, spec.method_name)(arguments)

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
