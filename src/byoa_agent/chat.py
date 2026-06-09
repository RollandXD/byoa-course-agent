from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .tools import CourseAgentTools, create_tool_schemas


class RunnableAgent(Protocol):
    def run(self, user_prompt: str, max_turns: int = 8) -> str:
        ...


def render_help() -> str:
    return "\n".join(
        [
            "BYOA Course Agent commands:",
            "/tools   查看工具 schema",
            "/check   检查实验二交付状态",
            "/log     汇总最近工具调用日志",
            "/report  生成报告材料",
            "/demo    运行固定演示流程",
            "/help    查看命令说明",
            "/exit    退出",
        ]
    )


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


class ChatSession:
    def __init__(
        self,
        agent: RunnableAgent | None,
        tools: CourseAgentTools,
        project_root: Path,
        output: list[str] | None = None,
    ) -> None:
        self.agent = agent
        self.tools = tools
        self.project_root = project_root
        self.output = output if output is not None else []
        self.echo = output is None

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
            self.write(json.dumps(create_tool_schemas(), ensure_ascii=False, indent=2))
            return True
        if command == "/check":
            self.write(render_check_result(self.tools.check_submission_readiness({})))
            return True
        if command == "/log":
            self.write(render_tool_log_summary(self.tools.summarize_tool_log({"path": "runs/latest.jsonl", "limit": 10})))
            return True
        if command == "/report":
            self._handle_report()
            return True
        if command == "/demo":
            if self.agent is None:
                self.write("error: /demo requires an initialized DeepSeek agent")
                return True
            self.write(
                self.agent.run(
                    "请运行实验二 BYOA 交互式演示，读取课程要求、检查交付状态、总结工具日志并给出报告建议。"
                )
            )
            return True
        if command.startswith("/"):
            self.write(f"unknown command: {command}\n{render_help()}")
            return True
        if self.agent is None:
            self.write("error: natural language chat requires DEEPSEEK_API_KEY")
            return True
        self.write(self.agent.run(command))
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


def run_chat(session: ChatSession) -> None:
    print("BYOA Course Agent")
    print(render_help())
    while True:
        try:
            line = input("\nyou > ")
        except EOFError:
            print()
            return
        if not session.handle_line(line):
            return
