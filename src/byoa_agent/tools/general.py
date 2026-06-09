from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from pathlib import Path

from .base import ToolError, tool


IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".claude"}
BINARY_SUFFIXES = {".pptx", ".docx", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pyc", ".lock"}
MAX_FILE_CHARS = 20_000
MAX_COMMAND_OUTPUT = 5_000
MAX_LIST_ENTRIES = 200


class GeneralTools:
    """Claude Code style coding tools: file read/write/edit, glob, grep, shell."""

    @tool(
        "read_file",
        "Read a UTF-8 text file inside the course workspace. Binary course files such as "
        "PPTX/DOCX must be read with the extract tools instead.",
        {
            "path": {"type": "string", "description": "Workspace-relative file path."},
            "offset": {"type": "integer", "description": "1-based line number to start from.", "minimum": 1},
            "limit": {"type": "integer", "description": "Maximum number of lines to return.", "minimum": 1},
        },
        ["path"],
    )
    def read_file(self, arguments: dict) -> str:
        path = self._resolve_read_path(arguments.get("path"))
        if path.suffix.lower() in BINARY_SUFFIXES:
            raise ToolError(
                f"{path.name} 是二进制文件，请改用 extract_pptx_text / extract_docx_text"
            )
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolError(f"not a UTF-8 text file: {path.name}") from exc
        lines = text.splitlines()
        offset = int(arguments.get("offset", 1))
        limit = int(arguments.get("limit", len(lines)))
        selected = lines[offset - 1 : offset - 1 + limit]
        content = "\n".join(selected)
        truncated = False
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS]
            truncated = True
        result = json.dumps(
            {
                "path": self._display_path(path),
                "total_lines": len(lines),
                "content": content,
                "truncated": truncated,
            },
            ensure_ascii=False,
        )
        self._log("read_file", arguments, "ok", result)
        return result

    @tool(
        "write_file",
        "Create or overwrite a UTF-8 text file inside this project repository. "
        "Requires user permission.",
        {
            "path": {"type": "string", "description": "Project-relative file path."},
            "content": {"type": "string", "description": "Full file content to write."},
        },
        ["path", "content"],
    )
    def write_file(self, arguments: dict) -> str:
        path = self._resolve_write_path(arguments.get("path"))
        content = arguments.get("content")
        if not isinstance(content, str):
            raise ToolError("content is required")
        denied = self._require_permission("write_file", f"写入 {self._display_path(path)} ({len(content)} 字符)")
        if denied is not None:
            self._log("write_file", {"path": arguments.get("path")}, "denied", denied)
            return denied
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        result = json.dumps(
            {"path": self._display_path(path), "bytes_written": len(content.encode("utf-8"))},
            ensure_ascii=False,
        )
        self._log("write_file", {"path": arguments.get("path")}, "ok", result)
        return result

    @tool(
        "edit_file",
        "Replace an exact text snippet in a project file. old_string must appear exactly once. "
        "Requires user permission.",
        {
            "path": {"type": "string", "description": "Project-relative file path."},
            "old_string": {"type": "string", "description": "Exact existing text to replace."},
            "new_string": {"type": "string", "description": "Replacement text."},
        },
        ["path", "old_string", "new_string"],
    )
    def edit_file(self, arguments: dict) -> str:
        path = self._resolve_write_path(arguments.get("path"))
        if not path.is_file():
            raise ToolError(f"file not found: {arguments.get('path')}")
        old_string = arguments.get("old_string")
        new_string = arguments.get("new_string")
        if not isinstance(old_string, str) or not old_string:
            raise ToolError("old_string is required")
        if not isinstance(new_string, str):
            raise ToolError("new_string is required")
        text = path.read_text(encoding="utf-8")
        occurrences = text.count(old_string)
        if occurrences == 0:
            raise ToolError("old_string not found in file")
        if occurrences > 1:
            raise ToolError(f"old_string matches {occurrences} locations; provide more context")
        denied = self._require_permission("edit_file", f"编辑 {self._display_path(path)}")
        if denied is not None:
            self._log("edit_file", {"path": arguments.get("path")}, "denied", denied)
            return denied
        path.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        result = json.dumps({"path": self._display_path(path), "replacements": 1}, ensure_ascii=False)
        self._log("edit_file", {"path": arguments.get("path")}, "ok", result)
        return result

    @tool(
        "list_files",
        "List files in the course workspace (which contains this project repository) "
        "matching a glob-style name pattern.",
        {
            "pattern": {
                "type": "string",
                "description": "Glob-style filename pattern such as *.py, *.pptx, or * for everything.",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory depth to walk.",
                "minimum": 1,
                "maximum": 6,
            },
        },
        ["pattern"],
    )
    def list_files(self, arguments: dict) -> str:
        pattern = arguments.get("pattern") or "*"
        max_depth = int(arguments.get("max_depth", 4))
        files = []
        for path in sorted(self.workspace.rglob("*")):
            relative = path.relative_to(self.workspace)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            if len(relative.parts) > max_depth:
                continue
            if path.is_file() and fnmatch.fnmatch(path.name, pattern):
                files.append({"path": relative.as_posix(), "size_bytes": path.stat().st_size})
            if len(files) >= MAX_LIST_ENTRIES:
                break
        result = json.dumps({"files": files}, ensure_ascii=False, indent=2)
        self._log("list_files", arguments, "ok", result)
        return result

    @tool(
        "grep_files",
        "Search text files in the workspace for a regular expression and return matching lines.",
        {
            "pattern": {"type": "string", "description": "Python regular expression to search for."},
            "glob": {"type": "string", "description": "Optional filename glob filter such as *.py."},
            "limit": {
                "type": "integer",
                "description": "Maximum number of matching lines to return.",
                "minimum": 1,
                "maximum": 50,
            },
        },
        ["pattern"],
    )
    def grep_files(self, arguments: dict) -> str:
        raw_pattern = str(arguments.get("pattern", "")).strip()
        if not raw_pattern:
            raise ToolError("pattern is required")
        try:
            regex = re.compile(raw_pattern)
        except re.error as exc:
            raise ToolError(f"invalid regular expression: {exc}") from exc
        name_glob = arguments.get("glob") or "*"
        limit = int(arguments.get("limit", 20))
        matches = []
        for path in sorted(self.workspace.rglob("*")):
            relative = path.relative_to(self.workspace)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
                continue
            if not fnmatch.fnmatch(path.name, name_glob):
                continue
            if path.stat().st_size > 1_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(
                        {"file": relative.as_posix(), "line": line_number, "text": line.strip()[:200]}
                    )
                    if len(matches) >= limit:
                        break
            if len(matches) >= limit:
                break
        result = json.dumps({"matches": matches}, ensure_ascii=False, indent=2)
        self._log("grep_files", arguments, "ok", result)
        return result

    @tool(
        "run_command",
        "Run a shell command inside this project repository, for example the unit tests. "
        "Requires user permission.",
        {
            "command": {"type": "string", "description": "Shell command line to execute."},
        },
        ["command"],
    )
    def run_command(self, arguments: dict) -> str:
        command = str(arguments.get("command", "")).strip()
        if not command:
            raise ToolError("command is required")
        denied = self._require_permission("run_command", command)
        if denied is not None:
            self._log("run_command", arguments, "denied", denied)
            return denied
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"command timed out after 60s: {command}") from exc
        result = json.dumps(
            {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-MAX_COMMAND_OUTPUT:],
                "stderr": completed.stderr[-MAX_COMMAND_OUTPUT:],
            },
            ensure_ascii=False,
        )
        self._log("run_command", arguments, "ok", result)
        return result

    def _resolve_read_path(self, value: object) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ToolError("path is required")
        path = (self.workspace / value).resolve()
        try:
            path.relative_to(self.workspace)
        except ValueError as exc:
            raise ToolError(f"path is outside workspace: {value}") from exc
        if not path.is_file():
            raise ToolError(f"file not found: {value}")
        return path

    def _resolve_write_path(self, value: object) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ToolError("path is required")
        assert self.project_root is not None
        path = (self.project_root / value).resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise ToolError(f"writes are restricted to the project repository: {value}") from exc
        return path

    def _display_path(self, path: Path) -> str:
        for root in (self.project_root, self.workspace):
            if root is not None:
                try:
                    return path.relative_to(root).as_posix()
                except ValueError:
                    continue
        return path.as_posix()

    def _require_permission(self, tool_name: str, summary: str) -> str | None:
        """Return a denial payload when the permission gate rejects the call."""
        if self.permissions.request(tool_name, summary):
            return None
        return json.dumps(
            {"denied": f"用户未批准 {tool_name}: {summary}", "hint": "可在 chat 中用 /auto 开启自动批准"},
            ensure_ascii=False,
        )
