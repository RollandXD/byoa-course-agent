from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .config import AgentConfig
from .deepseek import DeepSeekClient
from .tools import CourseAgentTools, ToolError, create_tool_schemas


SYSTEM_PROMPT = """You are a single-purpose course task agent for a BYOA experiment.
Your job is to help the student understand and complete Experiment 2.
Use local tools before answering factual questions about course requirements.
When citing course requirements, mention the source file and slide or context when available.
Be concise, practical, and honest about what was inferred from tools.
"""


DEMO_PROMPT = """Run the full BYOA course-task demo.
1. List available PPTX and DOCX files.
2. Read Week 13-15.pptx and find the Experiment 2 requirements.
3. Read the previous experiment report DOCX to identify report style and identity information.
4. Search the loaded context for Bring Your Own Agent and rubric.
5. Produce:
- a concise requirement summary,
- an implementation checklist,
- 3 to 4 screenshot suggestions,
- a short Markdown report draft outline.
"""


class CourseAgent:
    def __init__(
        self,
        config: AgentConfig,
        log_path: Path | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        project_root: Path | None = None,
        tool_observer: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.config = config
        self.client = DeepSeekClient(config.api_key, config.base_url, config.model)
        self.tools = CourseAgentTools(config.workspace, log_path=log_path, project_root=project_root)
        self.system_prompt = system_prompt
        self.tool_observer = tool_observer

    def run(self, user_prompt: str, max_turns: int = 8) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        schemas = create_tool_schemas()
        for _turn in range(max_turns):
            message = self.client.chat(messages, schemas)
            messages.append(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return str(message.get("content") or "")
            for call in tool_calls:
                tool_name = call["function"]["name"]
                raw_arguments = call["function"].get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_arguments)
                    if self.tool_observer is not None:
                        self.tool_observer(tool_name, arguments)
                    content = self.tools.dispatch(tool_name, arguments)
                except (json.JSONDecodeError, ToolError) as exc:
                    content = json.dumps({"error": str(exc)}, ensure_ascii=False)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": content,
                    }
                )
        return "Agent stopped because the maximum tool-call turn limit was reached."


def default_run_log_path(project_root: Path) -> Path:
    return project_root / "runs" / "latest.jsonl"


def read_prompt_file(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return fallback
