from __future__ import annotations

import json
from pathlib import Path

from ..extractors import extract_docx_text as read_docx_text
from ..extractors import extract_pptx_text as read_pptx_text
from .base import REGISTRY, ToolError, tool


class CourseTools:
    """BYOA course skills: read course material formats and audit the submission."""

    @tool(
        "extract_pptx_text",
        "Extract ordered slide text from a PPTX course material file.",
        {"path": {"type": "string", "description": "Workspace-relative PPTX path."}},
        ["path"],
    )
    def extract_pptx_text(self, arguments: dict) -> str:
        path = self._resolve_suffix_path(arguments.get("path"), ".pptx")
        text = read_pptx_text(path)
        self.extracted_context[path.name] = text
        result = json.dumps({"path": path.name, "text": text}, ensure_ascii=False)
        self._log("extract_pptx_text", arguments, "ok", result)
        return result

    @tool(
        "extract_docx_text",
        "Extract paragraph text from a DOCX report or template file.",
        {"path": {"type": "string", "description": "Workspace-relative DOCX path."}},
        ["path"],
    )
    def extract_docx_text(self, arguments: dict) -> str:
        path = self._resolve_suffix_path(arguments.get("path"), ".docx")
        text = read_docx_text(path)
        self.extracted_context[path.name] = text
        result = json.dumps({"path": path.name, "text": text}, ensure_ascii=False)
        self._log("extract_docx_text", arguments, "ok", result)
        return result

    @tool(
        "search_extracted_context",
        "Search text that was previously loaded by the PPTX/DOCX extraction tools.",
        {
            "query": {"type": "string", "description": "Keyword or phrase to search."},
            "limit": {
                "type": "integer",
                "description": "Maximum number of matching snippets to return.",
                "minimum": 1,
                "maximum": 10,
            },
        },
        ["query"],
    )
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
                    matches.append({"source": source, "line": line_number, "text": line})
                    if len(matches) >= limit:
                        break
            if len(matches) >= limit:
                break
        result = json.dumps({"matches": matches}, ensure_ascii=False, indent=2)
        self._log("search_extracted_context", arguments, "ok", result)
        return result

    @tool(
        "check_submission_readiness",
        "Check whether this BYOA project has the repository artifacts required for "
        "Experiment 2 submission.",
    )
    def check_submission_readiness(self, arguments: dict) -> str:
        checks = [
            self._check(
                "readme",
                "README.md exists",
                self._project_path("README.md").is_file(),
                "README documents the agent interface.",
            ),
            self._check(
                "prompts",
                "Prompt files exist",
                self._project_path("prompts/system.md").is_file()
                and self._project_path("prompts/demo.md").is_file(),
                "System and demo prompts are included for grading.",
            ),
            self._check(
                "source",
                "Source package exists",
                self._project_path("src/byoa_agent").is_dir(),
                "Agent implementation is present.",
            ),
            self._check(
                "tests",
                "Unit tests exist",
                self._project_path("tests").is_dir(),
                "Tests can be run with unittest.",
            ),
            self._check(
                "tool_count",
                "At least two tool schemas exist",
                len(REGISTRY) >= 2,
                f"{len(REGISTRY)} tool schemas are available.",
            ),
            self._check(
                "report_draft",
                "Report draft exists",
                self._project_path("reports/experiment2-draft.md").is_file(),
                "Report material is present.",
                warn=True,
            ),
            self._check(
                "tool_log",
                "Tool log directory exists",
                self._project_path("runs").is_dir(),
                "Run chat once to refresh runs/latest.jsonl.",
                warn=True,
            ),
            self._check(
                "template",
                "Experiment 2 template exists",
                (self.workspace / "综合实践（阶段1）-实验2-实验报告模版.docx").is_file(),
                "The official report template is readable.",
                warn=True,
            ),
        ]
        summary = {
            "total": len(checks),
            "pass": sum(1 for item in checks if item["status"] == "PASS"),
            "warn": sum(1 for item in checks if item["status"] == "WARN"),
            "fail": sum(1 for item in checks if item["status"] == "FAIL"),
        }
        result = json.dumps({"summary": summary, "checks": checks}, ensure_ascii=False, indent=2)
        self._log("check_submission_readiness", arguments, "ok", result)
        return result

    @tool(
        "summarize_tool_log",
        "Summarize JSONL tool-call logs into report-friendly execution evidence.",
        {
            "path": {
                "type": "string",
                "description": "Project-relative path to a JSONL tool log such as runs/latest.jsonl.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of calls to include in the summary.",
                "minimum": 1,
                "maximum": 20,
            },
        },
    )
    def summarize_tool_log(self, arguments: dict) -> str:
        raw_path = str(arguments.get("path") or "runs/latest.jsonl")
        limit = int(arguments.get("limit", 10))
        log_path = self._resolve_project_file(raw_path, ".jsonl")
        calls = []
        if not log_path.exists():
            result = json.dumps(
                {
                    "summary": {"total_calls": 0, "shown_calls": 0, "tools_used": [], "status": "WARN"},
                    "calls": [],
                    "message": f"tool log not found: {raw_path}",
                },
                ensure_ascii=False,
                indent=2,
            )
            self._log("summarize_tool_log", arguments, "ok", result)
            return result
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            calls.append(
                {
                    "tool": entry.get("tool"),
                    "arguments": entry.get("arguments", {}),
                    "status": entry.get("status", "unknown"),
                    "evidence": self._evidence_for_tool(str(entry.get("tool", ""))),
                }
            )
        limited = calls[:limit]
        summary = {
            "total_calls": len(calls),
            "shown_calls": len(limited),
            "tools_used": sorted({str(call["tool"]) for call in calls if call.get("tool")}),
            "status": "PASS" if calls else "WARN",
        }
        result = json.dumps({"summary": summary, "calls": limited}, ensure_ascii=False, indent=2)
        self._log("summarize_tool_log", arguments, "ok", result)
        return result

    def _resolve_suffix_path(self, value: object, suffix: str) -> Path:
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

    def _project_path(self, relative: str) -> Path:
        assert self.project_root is not None
        return self.project_root / relative

    def _resolve_project_file(self, value: str, suffix: str) -> Path:
        assert self.project_root is not None
        path = (self.project_root / value).resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise ToolError(f"path is outside project: {value}") from exc
        if path.suffix.lower() != suffix:
            raise ToolError(f"expected a {suffix} file: {value}")
        return path

    @staticmethod
    def _status(condition: bool, warn: bool = False) -> str:
        if condition:
            return "PASS"
        return "WARN" if warn else "FAIL"

    def _check(self, check_id: str, label: str, condition: bool, detail: str, warn: bool = False) -> dict:
        return {
            "id": check_id,
            "label": label,
            "status": self._status(condition, warn=warn),
            "detail": detail,
        }

    @staticmethod
    def _evidence_for_tool(tool_name: str) -> str:
        evidence = {
            "read_file": "Shows the agent reads real files instead of guessing contents.",
            "write_file": "Shows the agent can produce reviewable file artifacts.",
            "edit_file": "Shows the agent performs precise, permission-gated edits.",
            "list_files": "Shows the agent inspects the local workspace and repository.",
            "grep_files": "Shows the agent searches code and documents for evidence.",
            "run_command": "Shows the agent executes and verifies commands such as the test suite.",
            "extract_pptx_text": "Shows the agent reads course PPT context instead of relying on memory.",
            "extract_docx_text": "Shows the agent reads report templates or previous reports.",
            "search_extracted_context": "Shows the agent searches previously loaded course context.",
            "check_submission_readiness": "Shows the agent checks the submission against rubric evidence.",
            "summarize_tool_log": "Shows the agent can explain its tool-use trace.",
        }
        return evidence.get(tool_name, "Shows an external tool call was recorded.")
