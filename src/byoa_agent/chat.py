from __future__ import annotations

import json
import signal
from pathlib import Path
from typing import Protocol

from . import ui
from .tools import AgentToolbox, create_tool_schemas


class RunnableSession(Protocol):
    def run_turn(self, user_input: str) -> str:
        ...

    def clear(self) -> None:
        ...

    def context_stats(self) -> dict[str, int]:
        ...


def render_help() -> str:
    return "\n".join(
        [
            "BYOA Code commands:",
            "/tools    查看工具列表",
            "/check    检查实验二交付状态",
            "/log      汇总最近工具调用日志",
            "/report   生成报告材料",
            "/demo     运行固定演示流程",
            "/clear    清空对话上下文",
            "/auto     切换写操作自动批准",
            "/context  查看上下文用量",
            "/help     查看命令说明",
            "/exit     退出",
            "",
            "直接输入自然语言即可与 agent 对话，工具调用会以 ⏺ 行实时显示。",
        ]
    )


def render_tool_list() -> str:
    lines = ["可用工具（DeepSeek Function Calling schema）："]
    for schema in create_tool_schemas():
        function = schema["function"]
        lines.append(f"  {function['name']:<26} {function['description'].split('. ')[0]}")
    return "\n".join(lines)


def render_check_result(raw_json: str) -> str:
    payload = json.loads(raw_json)
    summary = payload["summary"]
    lines = [
        f"BYOA Submission Check: {summary['pass']}/{summary['total']} PASS, "
        f"{summary['warn']} WARN, {summary['fail']} FAIL"
    ]
    for item in payload["checks"]:
        lines.append(f"[{item['status']}] {item['label']} - {item['detail']}")
    return "\n".join(lines)


def render_tool_log_summary(raw_json: str) -> str:
    payload = json.loads(raw_json)
    summary = payload["summary"]
    tools = ", ".join(summary["tools_used"]) or "none"
    lines = [f"Tool Log Summary: {summary['total_calls']} calls, tools={tools}"]
    for call in payload["calls"]:
        lines.append(f"- {call['tool']} {call['arguments']} [{call['status']}]")
        lines.append(f"  evidence: {call['evidence']}")
    if payload.get("message"):
        lines.append(payload["message"])
    return "\n".join(lines)


DEMO_INSTRUCTION = (
    "请运行实验二 BYOA 交互式演示：读取课程要求、检查交付状态、总结工具日志并给出报告建议。"
)


class ChatSession:
    def __init__(
        self,
        agent: RunnableSession | None,
        tools: AgentToolbox,
        project_root: Path,
        output: list[str] | None = None,
        stream_output: bool = False,
    ) -> None:
        self.agent = agent
        self.tools = tools
        self.project_root = project_root
        self.output = output if output is not None else []
        self.echo = output is None
        self.stream_output = stream_output

    def write(self, text: str) -> None:
        self.output.append(text)
        if self.echo:
            print(text)

    def handle_line(self, line: str) -> bool:
        command = line.strip()
        if not command:
            return True
        if command == "/exit":
            self.write("bye")
            return False
        if command == "/help":
            self.write(render_help())
            return True
        if command == "/tools":
            self.write(render_tool_list())
            return True
        if command == "/check":
            self.write(render_check_result(self.tools.check_submission_readiness({})))
            return True
        if command == "/log":
            self.write(
                render_tool_log_summary(
                    self.tools.summarize_tool_log({"path": "runs/latest.jsonl", "limit": 10})
                )
            )
            return True
        if command == "/report":
            self._handle_report()
            return True
        if command == "/clear":
            if self.agent is not None:
                self.agent.clear()
            self.write("已清空对话上下文")
            return True
        if command == "/context":
            if self.agent is None:
                self.write("当前为离线模式，没有对话上下文")
                return True
            stats = self.agent.context_stats()
            self.write(f"上下文：{stats['messages']} 条消息，约 {stats['approx_chars']} 字符")
            return True
        if command == "/auto":
            gate = self.tools.permissions
            gate.mode = "auto" if gate.mode == "ask" else "ask"
            state = "自动批准" if gate.mode == "auto" else "逐次确认"
            self.write(f"写操作/命令权限已切换为：{state}")
            return True
        if command == "/demo":
            return self._run_agent(DEMO_INSTRUCTION)
        if command.startswith("/"):
            self.write(f"unknown command: {command}\n{render_help()}")
            return True
        return self._run_agent(command)

    def _run_agent(self, prompt: str) -> bool:
        if self.agent is None:
            self.write("error: 自然语言对话需要配置 DEEPSEEK_API_KEY")
            return True
        text = self.agent.run_turn(prompt)
        if self.stream_output:
            # streamed chunks were already printed by the on_text callback
            print()
        else:
            self.write(text)
        return True

    def _handle_report(self) -> None:
        try:
            from .reporting import generate_report_materials, save_report_draft
        except ImportError:
            self.write("error: report generation is not available")
            return
        material = generate_report_materials(self.project_root, self.tools)
        path = save_report_draft(self.project_root, material)
        self.write(material)
        self.write(f"[report draft] {path}")


def run_chat(session: ChatSession, banner: str | None = None) -> None:
    previous_sigint = signal.getsignal(signal.SIGINT)

    def handle_sigint(_signum: int, _frame: object) -> None:
        print("\nbye")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    color = ui.supports_color()
    prompt = ui.paint("\n❯ ", ui.BOLD + ui.GREEN, color)
    print(banner or "BYOA Code")
    try:
        while True:
            try:
                line = input(prompt)
            except EOFError:
                print()
                return
            except KeyboardInterrupt:
                print("\nbye")
                return
            if not session.handle_line(line):
                return
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
