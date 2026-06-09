from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Protocol

from . import ui
from .tools import AgentToolbox, create_tool_schemas
from .tools.general import BINARY_SUFFIXES


class RunnableSession(Protocol):
    def run_turn(self, user_input: str) -> str:
        ...

    def clear(self) -> None:
        ...

    def context_stats(self) -> dict[str, int]:
        ...

    def compact_now(self) -> dict[str, int]:
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
            "/compact  压缩历史工具输出",
            "/auto     切换写操作自动批准",
            "/context  查看上下文用量",
            "/help     查看命令说明",
            "/exit     退出",
            "",
            "直接输入自然语言即可对话，回答以 Markdown 渲染，工具调用以 ⏺ 行实时显示。",
            "@文件名  把文本文件内容附加进提问，例如：@README.md 帮我精简这份文档",
            "!命令    绕过模型直接执行 shell 命令，例如：!git status",
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

MENTION_RE = re.compile(r"@([\w./一-鿿()（）-]+)")
MAX_MENTION_FILES = 3
MAX_MENTION_CHARS = 4000


class ChatSession:
    def __init__(
        self,
        agent: RunnableSession | None,
        tools: AgentToolbox,
        project_root: Path,
        output: list[str] | None = None,
        display: ui.TurnDisplay | None = None,
    ) -> None:
        self.agent = agent
        self.tools = tools
        self.project_root = project_root
        self.output = output if output is not None else []
        self.echo = output is None
        self.display = display

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
        if command == "/compact":
            if self.agent is None:
                self.write("当前为离线模式，没有对话上下文")
                return True
            stats = self.agent.compact_now()
            self.write(
                f"已压缩 {stats['compacted']} 条工具输出；"
                f"上下文现为 {stats['messages']} 条消息，约 {stats['approx_chars']} 字符"
            )
            return True
        if command == "/context":
            if self.agent is None:
                self.write("当前为离线模式，没有对话上下文")
                return True
            stats = self.agent.context_stats()
            percent = round(100 * stats["approx_chars"] / stats["max_chars"]) if stats.get("max_chars") else 0
            self.write(
                f"上下文：{stats['messages']} 条消息，约 {stats['approx_chars']} 字符（{percent}%）"
            )
            return True
        if command == "/auto":
            gate = self.tools.permissions
            gate.mode = "auto" if gate.mode == "ask" else "ask"
            state = "自动批准" if gate.mode == "auto" else "逐次确认"
            self.write(f"写操作/命令权限已切换为：{state}")
            return True
        if command == "/demo":
            return self._run_agent(DEMO_INSTRUCTION)
        if command.startswith("!"):
            self._run_shell(command[1:].strip())
            return True
        if command.startswith("/"):
            self.write(f"unknown command: {command}\n{render_help()}")
            return True
        return self._run_agent(command)

    def _run_agent(self, prompt: str) -> bool:
        if self.agent is None:
            self.write("error: 自然语言对话需要配置 DEEPSEEK_API_KEY")
            return True
        prompt, notes = self._expand_mentions(prompt)
        for note in notes:
            self.write(note)
        if self.display is not None:
            self.display.begin_turn()
        interrupted = False
        text = ""
        try:
            text = self.agent.run_turn(prompt)
        except KeyboardInterrupt:
            interrupted = True
        finally:
            if self.display is not None:
                self.display.end_turn(self._context_stats_safe(), interrupted=interrupted)
        if interrupted:
            self.write("⨯ 已中断，本轮对话已回滚，可以继续提问")
        elif self.display is None:
            self.write(text)
        return True

    def _context_stats_safe(self) -> dict | None:
        try:
            return self.agent.context_stats() if self.agent is not None else None
        except Exception:
            return None

    def _expand_mentions(self, prompt: str) -> tuple[str, list[str]]:
        """Inline @file mentions: attach the file's text below the prompt."""
        notes: list[str] = []
        attachments: list[str] = []
        seen: set[str] = set()
        for match in MENTION_RE.finditer(prompt):
            if len(attachments) >= MAX_MENTION_FILES:
                break
            relative = match.group(1).rstrip(".,;:!?)")
            if relative in seen:
                continue
            seen.add(relative)
            path = self._resolve_mention(relative)
            if path is None:
                continue
            if path.suffix.lower() in BINARY_SUFFIXES:
                notes.append(f"📎 @{relative} 是二进制文件，请让 agent 用 extract 工具读取")
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            truncated = len(content) > MAX_MENTION_CHARS
            if truncated:
                content = content[:MAX_MENTION_CHARS]
            attachments.append(
                f"[附加文件 {relative}{'（已截断）' if truncated else ''}]\n```\n{content}\n```"
            )
            notes.append(f"📎 已附加 {relative} ({len(content)} 字符)")
        if attachments:
            prompt = prompt + "\n\n" + "\n\n".join(attachments)
        return prompt, notes

    def _resolve_mention(self, relative: str) -> Path | None:
        for base in (self.project_root, self.tools.workspace):
            candidate = (base / relative)
            if candidate.is_file():
                return candidate
        return None

    def _run_shell(self, command: str) -> None:
        """`!cmd` passthrough: the user typed it, so it skips the permission gate."""
        if not command:
            self.write("usage: !<shell command>")
            return
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            self.write(f"error: command timed out after 60s: {command}")
            return
        output = (completed.stdout or "").rstrip()
        errors = (completed.stderr or "").rstrip()
        if output:
            self.write(output)
        if errors:
            self.write(errors)
        self.write(f"(exit {completed.returncode})")

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


def _setup_readline(history_path: Path) -> bool:
    try:
        import readline
    except ImportError:
        return False
    try:
        readline.read_history_file(history_path)
    except OSError:
        pass
    readline.set_history_length(500)
    return True


def _save_history(history_path: Path) -> None:
    try:
        import readline

        readline.write_history_file(history_path)
    except (ImportError, OSError):
        pass


def run_chat(session: ChatSession, banner: str | None = None) -> None:
    color = ui.supports_color()
    history_path = Path.home() / ".byoa_code_history"
    readline_active = _setup_readline(history_path)
    if readline_active and color:
        # \001/\002 mark zero-width escape codes so readline keeps column math right
        prompt = f"\001{ui.BOLD}{ui.GREEN}\002❯ \001{ui.RESET}\002"
    else:
        prompt = ui.paint("❯ ", ui.BOLD + ui.GREEN, color)
    print(banner or "BYOA Code")
    try:
        while True:
            print()
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
        if readline_active:
            _save_history(history_path)
