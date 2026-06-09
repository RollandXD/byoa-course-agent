from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .config import AgentConfig
from .deepseek import DeepSeekClient
from .permissions import PermissionGate
from .tools import AgentToolbox, ToolError, create_tool_schemas


SYSTEM_PROMPT = """You are BYOA Code, a Claude Code style terminal agent for a BYOA course experiment.
Use local tools to read real files, search the workspace, and verify project state before answering.
When citing course requirements, mention the source file and slide or context when available.
Be concise, practical, and honest about what was inferred from tools. Answer in Chinese.
"""


DEMO_PROMPT = """Run the full BYOA course-task demo.
1. List available PPTX and DOCX files.
2. Read Week 13-15.pptx and find the Experiment 2 requirements.
3. Check submission readiness and summarize the tool log.
4. Produce a concise requirement summary, an implementation checklist,
   3 to 4 screenshot suggestions, and a short Markdown report outline.
"""


COMPACTION_NOTE = json.dumps({"note": "[此前的工具输出已压缩以节省上下文]"}, ensure_ascii=False)


class AgentSession:
    """A persistent multi-turn agent loop: history, tool dispatch, and compaction.

    Unlike a one-shot ask, the session keeps the full message list across user
    turns so the model can refer back to earlier tool results, the way Claude
    Code keeps a conversation alive.
    """

    def __init__(
        self,
        client: DeepSeekClient,
        toolbox: AgentToolbox,
        system_prompt: str = SYSTEM_PROMPT,
        on_text: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
        max_turns: int = 16,
        max_context_chars: int = 120_000,
        stream: bool = True,
    ) -> None:
        self.client = client
        self.toolbox = toolbox
        self.system_prompt = system_prompt
        self.on_text = on_text
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.max_turns = max_turns
        self.max_context_chars = max_context_chars
        self.stream = stream
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        self.last_turn_tool_calls = 0

    def run_turn(self, user_input: str) -> str:
        """Run one user turn. On Ctrl+C the partial turn is rolled back so the
        message list never ends with an unanswered tool call."""
        checkpoint = len(self.messages)
        self.messages.append({"role": "user", "content": user_input})
        self.last_turn_tool_calls = 0
        schemas = create_tool_schemas()
        final_text = ""
        try:
            for _turn in range(self.max_turns):
                message = self._request(schemas)
                self.messages.append(message)
                if message.get("content"):
                    final_text = str(message["content"])
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    break
                for call in tool_calls:
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or "call_0",
                            "content": self._execute(call),
                        }
                    )
            else:
                final_text = final_text or "已达到单轮最大工具调用次数，请把任务拆小后继续。"
        except KeyboardInterrupt:
            del self.messages[checkpoint:]
            raise
        self._compact()
        return final_text

    def clear(self) -> None:
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def context_stats(self) -> dict[str, int]:
        total = sum(len(str(message.get("content") or "")) for message in self.messages)
        return {
            "messages": len(self.messages),
            "approx_chars": total,
            "max_chars": self.max_context_chars,
        }

    def compact_now(self) -> dict[str, int]:
        """Manually compress every old tool output, like Claude Code's /compact."""
        compacted = 0
        for message in self.messages:
            if message.get("role") != "tool":
                continue
            if len(str(message.get("content") or "")) <= len(COMPACTION_NOTE):
                continue
            message["content"] = COMPACTION_NOTE
            compacted += 1
        stats = self.context_stats()
        stats["compacted"] = compacted
        return stats

    def _request(self, schemas: list[dict]) -> dict[str, Any]:
        if self.stream and self.on_text is not None:
            return self.client.chat_stream(self.messages, schemas, self.on_text)
        return self.client.chat(self.messages, schemas)

    def _execute(self, call: dict) -> str:
        tool_name = call["function"]["name"]
        raw_arguments = call["function"].get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments)
            if self.on_tool_call is not None:
                self.on_tool_call(tool_name, arguments)
            content = self.toolbox.dispatch(tool_name, arguments)
        except (json.JSONDecodeError, ToolError) as exc:
            content = json.dumps({"error": str(exc)}, ensure_ascii=False)
        self.last_turn_tool_calls += 1
        if self.on_tool_result is not None:
            self.on_tool_result(tool_name, content)
        return content

    def _compact(self) -> None:
        """Shrink oldest large tool outputs once the context grows past the cap."""
        def total_chars() -> int:
            return sum(len(str(message.get("content") or "")) for message in self.messages)

        if total_chars() <= self.max_context_chars:
            return
        for message in self.messages:
            if message.get("role") != "tool":
                continue
            if len(str(message.get("content") or "")) <= len(COMPACTION_NOTE):
                continue
            message["content"] = COMPACTION_NOTE
            if total_chars() <= self.max_context_chars:
                return


def build_session(
    config: AgentConfig,
    project_root: Path,
    log_path: Path | None = None,
    system_prompt: str = SYSTEM_PROMPT,
    permissions: PermissionGate | None = None,
    on_text: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    stream: bool = True,
) -> AgentSession:
    client = DeepSeekClient(config.api_key, config.base_url, config.model)
    toolbox = AgentToolbox(
        config.workspace,
        log_path=log_path,
        project_root=project_root,
        permissions=permissions,
    )
    return AgentSession(
        client,
        toolbox,
        system_prompt=system_prompt,
        on_text=on_text,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        stream=stream,
    )


def default_run_log_path(project_root: Path) -> Path:
    return project_root / "runs" / "latest.jsonl"


def read_prompt_file(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return fallback
